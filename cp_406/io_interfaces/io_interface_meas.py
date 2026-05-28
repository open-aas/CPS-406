"""
IOInterface extension — MEAS (Estação 2: Medição)

Conecta ao PLC em 172.21.2.1:4840, lê os sensores de altura da peça,
decide OK/NOK e aciona o protocolo de reset por operador se necessário.

Env vars:
  PLC_URL    opc.tcp://172.21.2.1:4840  (override)
  MQTT_HOST  broker MQTT                (default: localhost)
  MQTT_PORT  porta do broker            (default: 1883)
"""

import asyncio
import json
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
_PLC_URL    = "opc.tcp://172.21.2.1:4840"
_PLC_DEVICE = ["2:DeviceSet", "3:plcMeas"]
_MQTT_SELF  = "cp406/orders/MEAS"
_MQTT_NEXT  = "cp406/orders/IDRILL"

_INPUTS: Dict[str, Optional[str]] = {
    "3:xBG_BG1": "Conveyor/Sensors/BG1_CarrierPresence",
    # sensores de altura e botões resolvidos dinamicamente via get_children()
}
_OUTPUTS: Dict[str, Optional[str]] = {
    "3:xQA1_A1":  "Conveyor/Actuators/MB20_BeltMotor",
    "3:xMB1":     "Conveyor/Actuators/Y1_StopperCylinder",
    "3:xBG_PF1":  "Module/Actuators/Q2_SignalLight_Red",
    "3:xBG_PF2":  None,   # LED laranja (sem nó AAS correspondente)
    "3:xBG_PF3":  "Module/Actuators/Q1_SignalLight_Green",
    "3:xPF1":     None,   # LED botão start
    "3:xPF4":     None,   # LED botão reset
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
                logger.warning("meas.mirror.error", node=nid, error=str(exc))
        det = self._detectors.get(nid)
        if det:
            det.update(int(val), nid)

    async def event_notification(self, event) -> None:
        pass


class IOInterface(ISubmodelExtension):
    """IOInterface — Estação 2 MEAS (Medição e classificação)."""

    def __init__(self, context: SubmodelContext) -> None:
        self._ctx       = context
        self._plc_url   = os.environ.get("PLC_URL", _PLC_URL)
        self._mqtt_host = os.environ.get("MQTT_HOST", "localhost")
        self._mqtt_port = int(os.environ.get("MQTT_PORT", "1883"))

        self._plc: Optional[Client]      = None
        self._mqtt: Optional[MQTTClient] = None
        self._tasks: List[asyncio.Task]  = []
        self._orders: asyncio.Queue      = asyncio.Queue()

        self._inputs:   Dict[str, Node]          = {}
        self._outputs:  Dict[str, Node]          = {}
        self._id_meta:  Dict[str, NodeMetadata]  = {}
        self._detectors: Dict[str, EdgeDetector] = {}

    async def init(self) -> None:
        # ── PLC ──────────────────────────────────────────────────────────
        self._plc = Client(self._plc_url)
        await self._plc.connect()
        logger.info("meas.plc.connected", url=self._plc_url)

        objects = self._plc.get_objects_node()
        device  = await objects.get_child(_PLC_DEVICE)
        inp_f   = await device.get_child("3:Inputs")
        out_f   = await device.get_child("3:Outputs")

        handler = _SyncHandler(self._ctx, self._id_meta)

        # nós de entrada declarados
        for name, aas_path in _INPUTS.items():
            node = await inp_f.get_child(name)
            self._inputs[name] = node
            if aas_path:
                meta = self._ctx.get_node(aas_path)
                if meta:
                    self._id_meta[str(node.nodeid)] = meta

        # sensores de altura e botões descobertos via get_children
        _extra = {"xBG_BG2.Q1", "xBG_BG3.Q2", "xSF1", "xSF4"}
        for child in await inp_f.get_children():
            bn = await child.read_browse_name()
            if bn.Name in _extra:
                self._inputs[f"3:{bn.Name}"] = child

        # nós de saída
        for name in _OUTPUTS:
            self._outputs[name] = await out_f.get_child(name)

        # edge detector: stopper
        stopper = self._inputs["3:xBG_BG1"]
        det_stopper = EdgeDetector(stopper.nodeid, EdgeType.RISING)
        self._detectors["stopper"] = det_stopper
        handler.register(str(stopper.nodeid), det_stopper)

        # edge detectors: botões
        for key, det_name in [("3:xSF1", "btn_start"), ("3:xSF4", "btn_reset")]:
            node = self._inputs.get(key)
            if node:
                det = EdgeDetector(node.nodeid, EdgeType.RISING)
                self._detectors[det_name] = det
                handler.register(str(node.nodeid), det)

        sub = await self._plc.create_subscription(10, handler)
        nodes_to_sub = [
            self._inputs[k] for k in ("3:xBG_BG1", "3:xSF1", "3:xSF4")
            if k in self._inputs
        ]
        await sub.subscribe_data_change(nodes_to_sub)

        # estado inicial
        await self._write("3:xQA1_A1", True)
        await self._write("3:xMB1", False)
        for led in ("3:xBG_PF1", "3:xBG_PF2", "3:xBG_PF3", "3:xPF1", "3:xPF4"):
            await self._write(led, False)

        # ── MQTT ─────────────────────────────────────────────────────────
        self._mqtt = MQTTClient("faaster-meas")
        self._mqtt.on_message = self._on_order
        await self._mqtt.connect(self._mqtt_host, self._mqtt_port)
        self._mqtt.subscribe(_MQTT_SELF, qos=1)
        logger.info("meas.mqtt.subscribed", topic=_MQTT_SELF)

        self._tasks.append(asyncio.create_task(self._process_orders()))
        logger.info("meas.io_interface.ready")

    async def stop(self) -> None:
        for t in self._tasks:
            t.cancel()
        if self._mqtt:
            await self._mqtt.disconnect()
        if self._plc:
            await self._plc.disconnect()

    # ── MQTT ──────────────────────────────────────────────────────────────

    def _on_order(self, client, topic, payload, qos, properties) -> None:
        try:
            self._orders.put_nowait(json.loads(payload))
        except Exception as exc:
            logger.error("meas.order.parse_error", error=str(exc))

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

    async def _toggle_led(self, name: str) -> None:
        try:
            while True:
                await self._write(name, True)
                await asyncio.sleep(0.5)
                await self._write(name, False)
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            await self._write(name, False)

    # ── Processamento de pedidos ──────────────────────────────────────────

    async def _process_orders(self) -> None:
        logger.info("meas.orders.loop.start")
        while True:
            order = await self._orders.get()
            logger.info("meas.order.start", order_id=order.get("order_id"))
            await self._cycle(order)
            logger.info("meas.order.done",  order_id=order.get("order_id"))

    async def _cycle(self, order: dict) -> None:
        stopper    = self._detectors["stopper"]
        btn_reset  = self._detectors.get("btn_reset")
        btn_start  = self._detectors.get("btn_start")
        high_node  = self._inputs.get("3:xBG_BG2.Q1")
        low_node   = self._inputs.get("3:xBG_BG3.Q2")

        # aguarda portador chegar
        await stopper.wait()
        await self._write("3:xBG_PF2", True)   # LED laranja → medindo
        await asyncio.sleep(1)

        # lê sensores de altura
        val_high = await high_node.get_value() if high_node else False
        val_low  = await low_node.get_value()  if low_node  else False
        await self._write("3:xBG_PF2", False)

        if val_low and val_high:
            # peça OK → avança
            await self._write("3:xBG_PF3", True)
            await self._write("3:xMB1", True)
            await asyncio.sleep(2)
            await self._write("3:xMB1", False)
            await self._write("3:xBG_PF3", False)
            self._mqtt.publish(_MQTT_NEXT, json.dumps(order).encode(), qos=1)
            logger.info("meas.order.forwarded", to="IDRILL",
                        order_id=order.get("order_id"))
        else:
            # peça NOK → aguarda intervenção do operador
            logger.warning("meas.order.nok", order_id=order.get("order_id"))
            await self._write("3:xBG_PF1", True)   # LED vermelho
            await self._write("3:xQA1_A1", False)   # para esteira anterior
            toggle = asyncio.create_task(self._toggle_led("3:xPF4"))

            if btn_reset:
                await btn_reset.wait()
            toggle.cancel()
            await self._write("3:xBG_PF1", False)

            if btn_start:
                await self._write("3:xPF1", True)
                await btn_start.wait()
                await self._write("3:xPF1", False)

            await self._write("3:xQA1_A1", True)

        await asyncio.sleep(1)
