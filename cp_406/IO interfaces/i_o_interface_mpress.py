"""
IOInterface extension — MPRESS (Estação 5: Prensa Pneumática)

Controla o músculo pneumático que prensa a tampa traseira sobre a frontal.
PLC: 172.21.7.1:4840, device: plcPress.

Env vars:
  PLC_URL    opc.tcp://172.21.7.1:4840  (override)
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
_PLC_URL    = "opc.tcp://172.21.7.1:4840"
_PLC_DEVICE = ["2:DeviceSet", "3:plcPress"]
_MQTT_SELF  = "cp406/orders/MPRESS"
# MPRESS é a última estação do fluxo de pedidos (OUTPUT é autônomo)

# browse-name PLC → path relativo no submodelo IOInterface  (None = sem espelho AAS)
_INPUTS: Dict[str, Optional[str]] = {
    "3:xBG1":    "Conveyor/Sensors/BG1_CarrierPresence",
    "3:xHL_BG8": "Module/Sensors/B3_WorkpiecePresent",
}
_OUTPUTS: Dict[str, Optional[str]] = {
    "3:xQA1_A1": "Conveyor/Actuators/MB20_BeltMotor",
    "3:xMB1":    "Conveyor/Actuators/Y1_StopperCylinder",
    "3:xHL_MB1": "Module/Actuators/Y2_ClampCylinder",    # cilindro de fixação (sobe)
    "3:xHL_MB2": "Module/Actuators/Y1_PneumaticMuscle",  # músculo pneumático (desce/prensa)
}


class _SyncHandler:
    """Subscription asyncua: espelha mudanças PLC → nós AAS e aciona EdgeDetectors."""

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
                logger.warning("mpress.mirror.error", node=nid, error=str(exc))
        det = self._detectors.get(nid)
        if det:
            det.update(int(val), nid)

    async def event_notification(self, event) -> None:
        pass


class IOInterface(ISubmodelExtension):
    """
    IOInterface — Estação 5 MPRESS (Prensa Pneumática com músculo fluidic).
    Carregada automaticamente pelo faaster para o submodelo IOInterface.
    """

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
        logger.info("mpress.plc.connected", url=self._plc_url)

        objects = self._plc.get_objects_node()
        device  = await objects.get_child(_PLC_DEVICE)
        inp_f   = await device.get_child("3:Inputs")
        out_f   = await device.get_child("3:Outputs")

        handler = _SyncHandler(self._ctx, self._id_meta)

        # resolver nós de entrada + construir mapa de espelhamento
        for name, aas_path in _INPUTS.items():
            node = await inp_f.get_child(name)
            self._inputs[name] = node
            if aas_path:
                meta = self._ctx.get_node(aas_path)
                if meta:
                    self._id_meta[str(node.nodeid)] = meta

        # resolver nós de saída
        for name in _OUTPUTS:
            self._outputs[name] = await out_f.get_child(name)

        # edge detector: portador no stopper
        stopper_node = self._inputs["3:xBG1"]
        det_stopper = EdgeDetector(stopper_node.nodeid, EdgeType.RISING)
        self._detectors["stopper"] = det_stopper
        handler.register(str(stopper_node.nodeid), det_stopper)

        # edge detector: peça saiu (borda de descida — peça deixa o sensor)
        piece_node = self._inputs["3:xHL_BG8"]
        det_piece = EdgeDetector(piece_node.nodeid, EdgeType.FALLING)
        self._detectors["has_piece"] = det_piece
        handler.register(str(piece_node.nodeid), det_piece)

        sub = await self._plc.create_subscription(10, handler)
        await sub.subscribe_data_change(list(self._inputs.values()))

        # estado inicial: prensa aberta, esteira ligada
        await self._write("3:xMB1",    False)
        await self._write("3:xHL_MB1", True)   # fixação sobe (desbloqueada)
        await self._write("3:xHL_MB2", False)  # músculo retraído
        await self._write("3:xQA1_A1", True)

        # ── MQTT ─────────────────────────────────────────────────────────
        self._mqtt = MQTTClient("faaster-mpress")
        self._mqtt.on_message = self._on_order
        await self._mqtt.connect(self._mqtt_host, self._mqtt_port)
        self._mqtt.subscribe(_MQTT_SELF, qos=1)
        logger.info("mpress.mqtt.subscribed", topic=_MQTT_SELF)

        self._tasks.append(asyncio.create_task(self._process_orders()))
        logger.info("mpress.io_interface.ready")

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
            logger.error("mpress.order.parse_error", error=str(exc))

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

    async def _press(self) -> None:
        """Desce o músculo pneumático (prensa a tampa traseira)."""
        await self._write("3:xHL_MB1", False)  # fixação abaixa
        await self._write("3:xHL_MB2", True)   # músculo contrai → prensa

    async def _unpress(self) -> None:
        """Sobe o músculo pneumático (abre a prensa)."""
        await self._write("3:xHL_MB1", True)   # fixação sobe
        await self._write("3:xHL_MB2", False)  # músculo relaxa

    # ── Processamento de pedidos ──────────────────────────────────────────

    async def _process_orders(self) -> None:
        logger.info("mpress.orders.loop.start")
        while True:
            order = await self._orders.get()
            logger.info("mpress.order.start", order_id=order.get("order_id"))
            await self._cycle(order)
            logger.info("mpress.order.done",  order_id=order.get("order_id"))

    async def _cycle(self, order: dict) -> None:
        stopper   = self._detectors["stopper"]
        has_piece = self._detectors.get("has_piece")

        # aguarda portador chegar ao stopper
        await stopper.wait()
        await self._write("3:xQA1_A1", False)
        await asyncio.sleep(1)

        # prensa: desce e sobe o músculo pneumático
        await self._press()
        await asyncio.sleep(1)
        await self._unpress()
        await asyncio.sleep(1)

        # libera portador
        await self._write("3:xQA1_A1", True)
        await self._write("3:xMB1",    True)

        # aguarda peça pronta sair do sensor
        if has_piece:
            await has_piece.wait()
        else:
            await asyncio.sleep(3)

        await self._write("3:xMB1", False)
        logger.info("mpress.cycle.complete", order_id=order.get("order_id"))
        # MPRESS é a última estação: peça finalizada — sem encaminhamento MQTT
