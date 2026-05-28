"""
IOInterface extension — OUT (Estação 6: Saída / Robô de Garra)

Controla o eixo linear (motor KF1) e a garra (GM) da estação de saída.
Opera de forma autônoma (sem fila de pedidos): move continuamente
esquerda ↔ direita para transferir peças acabadas.

PLC: 172.21.10.1:4840, device: plcOut.

Env vars:
  PLC_URL    opc.tcp://172.21.10.1:4840  (override)
  MQTT_HOST  broker MQTT                 (default: localhost)
"""

import asyncio
import os
from typing import Dict, List, Optional

from asyncua import Client, Node
from asyncua.ua import DataValue, Variant, VariantType as UA_VT
from gmqtt import Client as MQTTClient
import structlog

from edge_detector import EdgeDetector, EdgeType
from faaster.extensions.interfaces import ISubmodelExtension
from faaster.extensions.context import SubmodelContext
from faaster.parser.node_registry import NodeMetadata

logger = structlog.getLogger(__name__)

# ── Constantes da estação ──────────────────────────────────────────────────
_PLC_URL    = "opc.tcp://172.21.10.1:4840"
_PLC_DEVICE = ["2:DeviceSet", "3:plcOut"]

_INPUTS: Dict[str, Optional[str]] = {
    "3:xKF1_DO10": "Module/Sensors/B5_ArmHome",
    "3:xKF1_DO0":  "Module/Sensors/B3_ArmUp",
    "3:xKF1_DO9":  None,   # sinal de referência do motor (uso interno)
}
_OUTPUTS: Dict[str, Optional[str]] = {
    "3:xKF1_DI10": "Module/Actuators/Y3_ArmHorizontal",  # enable motor
    "3:xKF1_DI1":  None,   # direção esquerda (compartilha nó AAS com DI10)
    "3:xKF1_DI2":  None,   # direção direita
    "3:xKF1_DI6":  None,   # trigger de movimento
    "3:xGM_MB1":   "Module/Actuators/Y2_ArmVertical",    # garra sobe
    "3:xGM_MB2":   None,   # garra desce (compartilha nó AAS com MB1)
    "3:xGM_MB3":   None,   # enable garra
    "3:xGM_MB4":   "Module/Actuators/Y1_Gripper",        # garra abre/fecha
}


class _SyncHandler:
    def __init__(self, ctx: SubmodelContext, mapping: Dict[str, NodeMetadata]):
        self._ctx = ctx
        self._mapping = mapping
        self._detectors: Dict[str, EdgeDetector] = {}

    def register(self, node_id: str, det: EdgeDetector) -> None:
        self._detectors[node_id] = det

    async def datachange_notification(self, node: Node, val, data) -> None:
        nid = str(node.nodeid)
        meta = self._mapping.get(nid)
        if meta:
            try:
                await self._ctx.address_space.set_value(meta.node, bool(val))
            except Exception as exc:
                logger.warning("out.mirror.error", node=nid, error=str(exc))
        det = self._detectors.get(nid)
        if det:
            det.update(int(val), nid)

    async def event_notification(self, event) -> None:
        pass


class IOInterface(ISubmodelExtension):
    """IOInterface — Estação 6 OUT (Saída autônoma: eixo linear + garra)."""

    def __init__(self, context: SubmodelContext) -> None:
        self._ctx       = context
        self._plc_url   = os.environ.get("PLC_URL", _PLC_URL)
        self._mqtt_host = os.environ.get("MQTT_HOST", "localhost")
        self._mqtt_port = int(os.environ.get("MQTT_PORT", "1883"))

        self._plc: Optional[Client]      = None
        self._mqtt: Optional[MQTTClient] = None
        self._tasks: List[asyncio.Task]  = []

        self._inputs:   Dict[str, Node]          = {}
        self._outputs:  Dict[str, Node]          = {}
        self._id_meta:  Dict[str, NodeMetadata]  = {}
        self._detectors: Dict[str, EdgeDetector] = {}

    async def init(self) -> None:
        # ── PLC ──────────────────────────────────────────────────────────
        self._plc = Client(self._plc_url)
        await self._plc.connect()
        logger.info("out.plc.connected", url=self._plc_url)

        objects = self._plc.get_objects_node()
        device  = await objects.get_child(_PLC_DEVICE)
        inp_f   = await device.get_child("3:Inputs")
        out_f   = await device.get_child("3:Outputs")

        handler = _SyncHandler(self._ctx, self._id_meta)

        for name, aas_path in _INPUTS.items():
            node = await inp_f.get_child(name)
            self._inputs[name] = node
            if aas_path:
                meta = self._ctx.get_node(aas_path)
                if meta:
                    self._id_meta[str(node.nodeid)] = meta

        for name in _OUTPUTS:
            self._outputs[name] = await out_f.get_child(name)

        # edge detectors para estado do motor
        for key, det_name, trigger in [
            ("3:xKF1_DO0",  "ismoving", EdgeType.FALLING),
            ("3:xKF1_DO10", "ready",    EdgeType.RISING),
        ]:
            node = self._inputs.get(key)
            if node:
                det = EdgeDetector(node.nodeid, trigger)
                self._detectors[det_name] = det
                handler.register(str(node.nodeid), det)

        sub = await self._plc.create_subscription(10, handler)
        await sub.subscribe_data_change(list(self._inputs.values()))

        # inicializa garra na posição superior
        await self._write("3:xGM_MB3", True)   # enable garra
        await self._claw_upper()

        self._tasks.append(asyncio.create_task(self._run()))
        logger.info("out.io_interface.ready")

    async def stop(self) -> None:
        for t in self._tasks:
            t.cancel()
        if self._plc:
            await self._plc.disconnect()

    # ── Escrita PLC + espelho AAS ─────────────────────────────────────────

    async def _write(self, name: str, value: bool) -> None:
        node = self._outputs.get(name)
        if node is None:
            return
        await node.set_data_value(DataValue(Value=Variant(value, UA_VT.Boolean)))
        aas_path = _OUTPUTS.get(name)
        if aas_path:
            meta = self._ctx.get_node(aas_path)
            if meta:
                await self._ctx.address_space.set_value(meta.node, value)

    # ── Ciclo autônomo ────────────────────────────────────────────────────

    async def _run(self) -> None:
        """Loop autônomo: esquerda → direita → esquerda → ..."""
        logger.info("out.autonomous.loop.start")
        while True:
            await self._wait_ready()
            await self._move_left()
            await asyncio.sleep(5)

            await self._wait_ready()
            await self._move_right()
            await asyncio.sleep(5)

    async def _wait_ready(self) -> None:
        """Aguarda motor em posição de referência e parado."""
        ref  = self._inputs.get("3:xKF1_DO9")
        mov  = self._inputs.get("3:xKF1_DO0")
        while True:
            ok_ref = await ref.get_value() if ref else True
            ok_mov = await mov.get_value() if mov else True
            if ok_ref and ok_mov:
                break
            await asyncio.sleep(1)

    async def _move_left(self) -> None:
        det = self._detectors.get("ismoving")
        await self._write("3:xKF1_DI10", True)
        await self._write("3:xKF1_DI1",  True)
        await self._write("3:xKF1_DI2",  False)
        await self._write("3:xKF1_DI6",  True)
        await asyncio.sleep(5)
        await self._write("3:xKF1_DI6",  False)
        if det:
            await det.wait()
        await self._clear_motor()
        logger.debug("out.moved_left")

    async def _move_right(self) -> None:
        det = self._detectors.get("ismoving")
        await self._write("3:xKF1_DI10", True)
        await self._write("3:xKF1_DI1",  False)
        await self._write("3:xKF1_DI2",  True)
        await self._write("3:xKF1_DI6",  True)
        await asyncio.sleep(5)
        await self._write("3:xKF1_DI6",  False)
        if det:
            await det.wait()
        await self._clear_motor()
        logger.debug("out.moved_right")

    async def _clear_motor(self) -> None:
        await self._write("3:xKF1_DI10", False)
        await self._write("3:xKF1_DI1",  False)
        await self._write("3:xKF1_DI2",  False)

    async def _claw_upper(self) -> None:
        await self._write("3:xGM_MB4", False)   # fecha garra
        await asyncio.sleep(1)
        await self._write("3:xGM_MB2", False)   # garra desce OFF
        await self._write("3:xGM_MB1", True)    # garra sobe
        await asyncio.sleep(1)

    async def _claw_lower(self) -> None:
        await self._write("3:xGM_MB4", True)    # abre garra
        await asyncio.sleep(1)
        await self._write("3:xGM_MB1", False)   # garra sobe OFF
        await self._write("3:xGM_MB2", True)    # garra desce
        await asyncio.sleep(1)
