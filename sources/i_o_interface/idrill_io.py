"""
IOInterface — Estação 3: iDRILL (Furadeira CPS).

Gerencia dois PLCs:
  - Conveyor (plciDrill, 172.21.3.1) — esteira + stopper — via PLCIOBase
  - CPS      (CECC-LK,  172.21.3.2) — eixos X/Z + brocas — cliente secundário

A coordenação intra-estação (conveyor aguarda CPS terminar) é feita via
asyncio.Future, sem passar pelo aiofase.
"""

from typing import Dict, List, Optional
from asyncua import Client, Node
from aiofase.microservice import MicroService
from faaster.extensions.context import SubmodelContext
from faaster.log import get_logger
from .plc_base import PLCIOBase
from .models import Order
from .edge_detector import EdgeDetector, SensorEventHandler, EdgeType

import asyncio
import os


logger = get_logger(__name__)

_PLC_DEVICE = ["2:DeviceSet", "3:plciDrill"]

_INPUTS: Dict[str, Optional[str]] = {
    "3:xBG1_BCD0": "Conveyor/Sensors/BG1_CarrierPresence/Value",
}
_OUTPUTS: Dict[str, Optional[str]] = {
    "3:xQA1_A1": "Conveyor/Actuators/MB20_BeltMotor/Value",
    "3:xMB1":    "Conveyor/Actuators/Y1_StopperCylinder/Value",
}

_CPS_URL_DEFAULT = "opc.tcp://172.21.3.2:4840"


async def _find_child(root: Node, name: str) -> Optional[Node]:
    """Busca um filho pelo browse-name sem namespace (usado na árvore CECC-LK)."""
    for child in await root.get_children():
        bn = (await child.read_browse_name()).Name
        if bn == name:
            return child
    return None


async def _navigate(root: Node, path: List[str]) -> Optional[Node]:
    """Navega por uma lista de browse-names sem namespace."""
    node = root
    for name in path:
        node = await _find_child(node, name)
        if node is None:
            return None
    return node


class _IDrillService(MicroService):
    def __init__(self, ext: "IDrillIOInterface") -> None:
        sender   = os.environ.get("AIOFASE_SENDER",   "tcp://0.0.0.0:3000")
        receiver = os.environ.get("AIOFASE_RECEIVER", "tcp://0.0.0.0:4000")
        super().__init__(self, sender, receiver)
        self._ext        = ext
        self.queue_order: asyncio.Queue = asyncio.Queue(maxsize=1)

    @MicroService.action
    async def mag_drill_push_order(self, service, data: dict) -> None:
        await self.queue_order.put(Order(**data["order"]))

    @MicroService.action
    async def idrill_downstream_ready(self, service, data: dict) -> None:
        """Chamado pela MagBack quando está pronta para receber o próximo carrier."""
        self._ext._downstream_ready.set()

    @MicroService.task
    async def task_process_order(self) -> None:
        logger.info("idrill.orders.loop.start")
        self.request_action("meas_downstream_ready", {})

        while True:
            order = await self.queue_order.get()
            logger.info("idrill.order.start", order_id=order.order_id)

            self._ext._stopper_det.set_enable(True)
            await self._ext._stopper_det.wait()
            self.request_action("manager_update_has_product", {"has_product": True})
            await self._ext._write("3:xQA1_A1", False)
            await asyncio.sleep(0.5)

            # dispara ciclo CPS e aguarda conclusão via Future
            self._ext._drill_future = asyncio.get_event_loop().create_future()
            asyncio.create_task(self._ext._drill_cycle())
            await self._ext._drill_future
            await asyncio.sleep(0.5)

            # Aguarda MagBack sinalizar que está pronta antes de liberar o carrier
            await self._ext._downstream_ready.wait()
            self._ext._downstream_ready.clear()

            await self._ext._write("3:xMB1",    True)
            await self._ext._write("3:xQA1_A1", True)
            await asyncio.sleep(2)
            await self._ext._write("3:xMB1", False)

            self.request_action("manager_update_has_product", {"has_product": False})
            self.request_action("mag_back_push_order",{"order": order.model_dump(mode="json")})
            # Sinaliza Meas que IDrill está pronta para o próximo carrier
            self.request_action("meas_downstream_ready", {})
            logger.info("idrill.order.done", order_id=order.order_id)


class IDrillIOInterface(PLCIOBase):
    _PLC_URL_DEFAULT = "opc.tcp://172.21.3.1:4840"
    _PLC_DEVICE      = _PLC_DEVICE
    _INPUTS          = _INPUTS
    _OUTPUTS         = _OUTPUTS

    def __init__(self, context: SubmodelContext) -> None:
        super().__init__(context)
        self._stopper_det: Optional[EdgeDetector] = None

        # cliente CPS (CECC-LK)
        self._cps_url     = os.environ.get("CPS_PLC_URL", _CPS_URL_DEFAULT)
        self._cps_client: Optional[Client] = None
        self._cps_connected = False

        # nós do CPS
        self._cps_move_x_left:       Optional[Node] = None
        self._cps_move_x_right:      Optional[Node] = None
        self._cps_drilling_1:        Optional[Node] = None
        self._cps_drilling_2:        Optional[Node] = None
        self._cps_move_z_up:         Optional[Node] = None
        self._cps_move_z_down:       Optional[Node] = None
        self._cps_break_z:           Optional[Node] = None

        # detectores de limite CPS
        self._cps_left_det:   Optional[EdgeDetector] = None
        self._cps_right_det:  Optional[EdgeDetector] = None
        self._cps_upper_det:  Optional[EdgeDetector] = None
        self._cps_bottom_det: Optional[EdgeDetector] = None

        self._drill_future: Optional[asyncio.Future] = None
        self._service = _IDrillService(self)

    # ── PLCIOBase hooks ───────────────────────────────────────────────────────

    async def _on_connected(self) -> None:
        stopper          = self._inputs["3:xBG1_BCD0"]
        self._stopper_det = EdgeDetector(stopper.nodeid, EdgeType.RISING, enable=False)
        handler = SensorEventHandler(self._stopper_det)
        sub = await self._plc.create_subscription(10, handler)
        await sub.subscribe_data_change([stopper])

        await self._write_raw("3:xQA1_A1", True)
        await self._write_raw("3:xMB1",    False)

        try:
            await self._connect_cps()
        except Exception as exc:
            logger.warning("idrill.cps.connect_failed",
                           cps=self._cps_url, error=str(exc))

    async def _start_service(self) -> None:
        self._tasks.append(asyncio.create_task(self._service.run()))
        logger.info(
            "idrill.io_interface.ready",
            plc=self._plc_url, connected=self._connected, cps=self._cps_url, cps_connected=self._cps_connected
        )

    async def stop(self) -> None:
        await super().stop()
        if self._cps_client and self._cps_connected:
            try:
                await self._cps_client.disconnect()
            except Exception:
                pass

    # ── CPS (CECC-LK) ─────────────────────────────────────────────────────────

    async def _connect_cps(self) -> None:
        if self._cps_client is not None:
            try:
                await self._cps_client.disconnect()
            except Exception:
                pass

        self._cps_client    = Client(self._cps_url)
        self._cps_connected = False
        await self._cps_client.connect()

        objects    = self._cps_client.get_objects_node()
        station_io = await _navigate(objects, ["CECC-LK", "Application", "Station_IO"])
        if station_io is None:
            raise RuntimeError("CPS: Station_IO não encontrado")

        self._cps_move_x_left  = await _find_child(station_io, "xMB1_opcua")
        self._cps_move_x_right = await _find_child(station_io, "xMB2_opcua")
        self._cps_drilling_1   = await _find_child(station_io, "xMA3_opcua")
        self._cps_drilling_2   = await _find_child(station_io, "xMA4_opcua")
        self._cps_move_z_up    = await _find_child(station_io, "xMB5_opcua")
        self._cps_move_z_down  = await _find_child(station_io, "xMB6_opcua")
        self._cps_break_z      = await _find_child(station_io, "xMB7_opcua")

        node_left   = await _find_child(station_io, "xBG1")
        node_right  = await _find_child(station_io, "xBG2")
        node_upper  = await _find_child(station_io, "xBG5")
        node_bottom = await _find_child(station_io, "xBG6")

        self._cps_left_det   = EdgeDetector(node_left.nodeid,   EdgeType.RISING, enable=False)
        self._cps_right_det  = EdgeDetector(node_right.nodeid,  EdgeType.RISING, enable=False)
        self._cps_upper_det  = EdgeDetector(node_upper.nodeid,  EdgeType.RISING, enable=False)
        self._cps_bottom_det = EdgeDetector(node_bottom.nodeid, EdgeType.RISING, enable=False)

        handler = SensorEventHandler(self._cps_upper_det)
        handler.add_detect([self._cps_bottom_det, self._cps_left_det, self._cps_right_det])
        sub = await self._cps_client.create_subscription(10, handler)
        await sub.subscribe_data_change([node_upper, node_bottom, node_left, node_right])

        # ativa detectores e homing inicial
        for det in (self._cps_left_det, self._cps_right_det, self._cps_upper_det, self._cps_bottom_det):
            det.set_enable(True)

        await self._cps_set("cps_drilling_1", False)
        await self._cps_set("cps_drilling_2", False)
        await asyncio.sleep(0.5)
        await self._cps_set("cps_break_z",    True)
        await asyncio.sleep(0.5)
        await self._cps_set("cps_move_x_left",  False)
        await self._cps_set("cps_move_x_right", True)
        await asyncio.sleep(0.5)
        await self._cps_set("cps_move_z_up",   True)
        await self._cps_set("cps_move_z_down", False)
        await asyncio.sleep(0.5)

        self._cps_connected = True
        logger.info("idrill.cps.connected", url=self._cps_url)

    async def _cps_set(self, attr: str, value: bool) -> None:
        from asyncua.ua import DataValue, Variant, VariantType as UA_VT
        node: Optional[Node] = getattr(self, f"_{attr}", None)
        if node is None: return

        dv = DataValue(Value=Variant(value, UA_VT.Boolean))
        await node.set_data_value(dv)

    # ── Ciclo de furação (CPS) ────────────────────────────────────────────────

    async def _drill_cycle(self) -> None:
        """Executa o ciclo completo de furação nos dois pontos e resolve _drill_future."""
        try:
            await self._drill_point()
            await self._drill_point(right=True)
        finally:
            if self._drill_future and not self._drill_future.done():
                self._drill_future.set_result(True)

    async def _drill_point(self, right: bool = False) -> None:
        """Perfura em um ponto: move X → desce Z → fura → sobe Z."""
        if right:
            self._cps_right_det.set_enable(False)
            await self._cps_set("cps_move_x_left",  False)
            await self._cps_set("cps_move_x_right", True)
            self._cps_right_det.set_enable(True)
            await self._cps_right_det.wait()
        else:
            await self._cps_set("cps_move_x_left",  True)
            await self._cps_set("cps_move_x_right", False)
            await self._cps_left_det.wait()

        await asyncio.sleep(0.5)

        await self._cps_set("cps_move_z_up",   False)
        await self._cps_set("cps_move_z_down", True)
        await self._cps_bottom_det.wait()
        await asyncio.sleep(0.5)

        await self._cps_set("cps_drilling_1", True)
        await self._cps_set("cps_drilling_2", True)
        await asyncio.sleep(5)
        await self._cps_set("cps_drilling_1", False)
        await self._cps_set("cps_drilling_2", False)
        await asyncio.sleep(0.5)

        await self._cps_set("cps_move_z_up",   True)
        await self._cps_set("cps_move_z_down", False)
        await self._cps_upper_det.wait()
        await asyncio.sleep(0.5)
