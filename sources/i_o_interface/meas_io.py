"""IOInterface — Estação 2: MEAS (Medição)."""

from typing import Dict, List, Optional
from asyncua import Node
from aiofase.microservice import MicroService
from faaster.extensions.context import SubmodelContext
from faaster.log import get_logger
from .plc_base import PLCIOBase
from .models import Order
from .edge_detector import EdgeDetector, SensorEventHandler, EdgeType

import asyncio
import os


logger = get_logger(__name__)

_PLC_DEVICE = ["2:DeviceSet", "3:plcMeas"]

# xBG_BG2.Q1 e xBG_BG3.Q2 têm ponto no nome — resolvidos via scan em _on_connected
_INPUTS: Dict[str, Optional[str]] = {
    "3:xBG_BG1": "Conveyor/Sensors/BG1_CarrierPresence/Value",
    "3:xSF1":    None,  # botão Start
    "3:xSF4":    None,  # botão Reset
}
_OUTPUTS: Dict[str, Optional[str]] = {
    "3:xQA1_A1":  "Conveyor/Actuators/MB20_BeltMotor/Value",
    "3:xMB1":     "Conveyor/Actuators/Y1_StopperCylinder/Value",
    "3:xBG_PF1":  "Module/Actuators/Q2_SignalLight_Red/Value",
    "3:xBG_PF2":  None,
    "3:xBG_PF3":  "Module/Actuators/Q1_SignalLight_Green/Value",
    "3:xPF1":     None,
    "3:xPF4":     None,
}


class _MeasService(MicroService):
    def __init__(self, ext: "MeasIOInterface") -> None:
        sender   = os.environ.get("AIOFASE_SENDER",   "tcp://0.0.0.0:3000")
        receiver = os.environ.get("AIOFASE_RECEIVER", "tcp://0.0.0.0:4000")
        super().__init__(self, sender, receiver)
        self._ext        = ext
        self.queue_order: asyncio.Queue = asyncio.Queue(maxsize=1)

    @MicroService.action
    async def measurement_push_order(self, service, data: dict) -> None:
        await self.queue_order.put(Order(**data["order"]))

    @MicroService.action
    async def meas_downstream_ready(self, service, data: dict) -> None:
        """Chamado pela IDrill quando está pronta para receber o próximo carrier."""
        self._ext._downstream_ready.set()

    async def _toggle_led(self, node: Node) -> None:
        while True:
            try:
                await self._ext._write_raw_node(node, True)
                await asyncio.sleep(0.5)
                await self._ext._write_raw_node(node, False)
                await asyncio.sleep(0.5)

            except asyncio.CancelledError:
                await self._ext._write_raw_node(node, False)
                break

    @MicroService.task
    async def main_task_process_orders(self) -> None:
        logger.info("meas.orders.loop.start")
        self.request_action("magfront_downstream_ready", {})

        while True:
            order: Order = await self.queue_order.get()
            logger.info("meas.order.start", order_id=order.order_id)

            await self._ext._stopper_det.wait()
            self.request_action("manager_update_has_product", {"has_product": True})
            await self._ext._write("3:xBG_PF2", True)
            await self._ext._write("3:xQA1_A1", False)  # para a esteira para medir

            await asyncio.sleep(1)

            value_high = await self._ext._node_sensor_high.get_value()
            value_low  = await self._ext._node_sensor_low.get_value()
            await self._ext._write("3:xBG_PF2", False)

            if value_low and value_high:
                await self._ext._write("3:xBG_PF3", True)
                # Aguarda IDrill sinalizar que está pronta antes de abrir o stopper
                await self._ext._downstream_ready.wait()
                self._ext._downstream_ready.clear()
                await self._ext._write("3:xMB1", True)
                await asyncio.sleep(2)
                await self._ext._write("3:xMB1", False)
                await self._ext._write("3:xBG_PF3", False)
                self.request_action("manager_update_has_product", {"has_product": False})
                self.request_action("mag_drill_push_order",
                                          {"order": order.model_dump(mode="json")})
                # Sinaliza MagFront que Meas está pronta para o próximo carrier
                self.request_action("magfront_downstream_ready", {})
                logger.info("meas.order.ok", order_id=order.order_id)
                await self._ext._write("3:xQA1_A1", True)

            else:
                await self._ext._write("3:xBG_PF1", True)
                await self._ext._write("3:xQA1_A1", False)
                task_blink = asyncio.create_task(
                    self._toggle_led(self._ext._outputs["3:xPF4"])
                )
                self.request_action("mag_front_stop_conveyor", {"value": False})

                await self._ext._btn_reset_det.wait()
                await self._ext._write("3:xBG_PF1", False)
                await self._ext._write("3:xPF1", True)
                task_blink.cancel()

                await self._ext._btn_start_det.wait()
                await self._ext._write("3:xQA1_A1", True)
                self.request_action("mag_front_stop_conveyor", {"value": True})
                await self._ext._write("3:xPF1", False)
                # Sinaliza MagFront que Meas está pronta (peça rejeitada, ciclo encerrado)
                self.request_action("magfront_downstream_ready", {})

            await asyncio.sleep(1)
            logger.info("meas.order.done", order_id=order.order_id)


class MeasIOInterface(PLCIOBase):
    _PLC_URL_DEFAULT = "opc.tcp://172.21.2.1:4840"
    _PLC_DEVICE      = _PLC_DEVICE
    _INPUTS          = _INPUTS
    _OUTPUTS         = _OUTPUTS

    def __init__(self, context: SubmodelContext) -> None:
        super().__init__(context)
        self._stopper_det:    Optional[EdgeDetector] = None
        self._btn_start_det:  Optional[EdgeDetector] = None
        self._btn_reset_det:  Optional[EdgeDetector] = None
        self._node_sensor_high: Optional[Node] = None
        self._node_sensor_low:  Optional[Node] = None
        self._service = _MeasService(self)

    async def _on_connected(self) -> None:
        stopper_node     = self._inputs["3:xBG_BG1"]
        btn_start_node   = self._inputs["3:xSF1"]
        btn_reset_node   = self._inputs["3:xSF4"]

        self._stopper_det   = EdgeDetector(stopper_node.nodeid,   EdgeType.RISING)
        self._btn_start_det = EdgeDetector(btn_start_node.nodeid, EdgeType.RISING)
        self._btn_reset_det = EdgeDetector(btn_reset_node.nodeid, EdgeType.RISING)

        # nós com ponto no browse-name precisam de scan manual
        children = await self._inp_folder.get_children()
        for child in children:
            name = await child.read_browse_name()
            if name.Name == "xBG_BG2.Q1":
                self._node_sensor_high = child
            elif name.Name == "xBG_BG3.Q2":
                self._node_sensor_low = child

        handler = SensorEventHandler(self._stopper_det)
        handler.add_detect([self._btn_reset_det, self._btn_start_det])
        sub = await self._plc.create_subscription(10, handler)
        await sub.subscribe_data_change(
            [stopper_node, btn_start_node, btn_reset_node]
        )

        await self._write_raw("3:xQA1_A1", True)
        await self._write_raw("3:xMB1",    False)
        for led in ("3:xBG_PF1", "3:xBG_PF2", "3:xBG_PF3", "3:xPF1", "3:xPF4"):
            await self._write_raw(led, False)

    async def _start_service(self) -> None:
        self._tasks.append(asyncio.create_task(self._service.run()))
        logger.info("meas.io_interface.ready",
                    plc=self._plc_url, connected=self._connected)

    async def _write_raw_node(self, node: Node, value: bool) -> None:
        from asyncua.ua import DataValue, Variant, VariantType as UA_VT
        dv = DataValue(Value=Variant(value, UA_VT.Boolean))
        await node.set_data_value(dv)
