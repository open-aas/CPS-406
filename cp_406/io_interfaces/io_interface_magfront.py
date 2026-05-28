"""
IOInterface extension — MAGFRONT (Estação 1: Magazine Frontal)

Refatoração do mag_front.py do smart-factory para o faaster:

  • Comunicação inter-serviço via aiofase (mesmo padrão do original)
  • Retry automático de conexão OPC UA (watchdog task)
  • Espelhamento PLC → AAS em cada leitura/escrita
  • Paridade funcional total com mag_front.py

Env vars:
  PLC_URL           opc.tcp://172.21.1.1:4840   (override do IP do PLC)
  AIOFASE_SENDER    tcp://0.0.0.0:3000           (ZMQ endpoint de envio)
  AIOFASE_RECEIVER  tcp://0.0.0.0:4000           (ZMQ endpoint de recepção)
  RECONNECT_DELAY   5                            (segundos entre retentativas)
"""

import asyncio
import enum
import os
from datetime import datetime
from typing import Dict, List, Optional

import pydantic
import structlog
from asyncua import Client, Node
from asyncua.ua import DataValue, Variant, VariantType as UA_VT
from aiofase.microservice import MicroService

from edge_detector import EdgeDetector, SensorEventHandler, EdgeType
from faaster.extensions.interfaces import ISubmodelExtension
from faaster.extensions.context import SubmodelContext
from faaster.parser.node_registry import NodeMetadata

logger = structlog.getLogger(__name__)

# ── Constantes ────────────────────────────────────────────────────────────────
_PLC_URL         = "opc.tcp://172.21.1.1:4840"
_PLC_DEVICE      = ["2:DeviceSet", "3:plcMagFront"]
_RECONNECT_DELAY = float(os.environ.get("RECONNECT_DELAY", "5"))

# browse-name PLC → path AAS relativo ao submodelo IOInterface
_INPUTS: Dict[str, Optional[str]] = {
    "3:xCL_BG7": "Conveyor/Sensors/BG1_CarrierPresence",
}
_OUTPUTS: Dict[str, Optional[str]] = {
    "3:xQA1_A1": "Conveyor/Actuators/MB20_BeltMotor",
    "3:xMB1":    "Conveyor/Actuators/Y1_StopperCylinder",
    "3:xCL_MB1": None,                              # enable feeder (só controle)
    "3:xCL_MB2": "Module/Actuators/Y1_PushCylinder",
    "3:xCL_MB3": "Module/Actuators/Y2_MagazineAdvance",
    "3:xCL_MB4": "Module/Actuators/Y2_MagazineAdvance",
}


# ── Modelos pydantic (espelho do smart-factory/src/models/order.py) ───────────
# Definidos inline para evitar dependência de cross-repo.

class ProductType(enum.IntEnum):
    single     = 1
    industrial = 2
    complete   = 3


class Product(pydantic.BaseModel):
    id:           Optional[int] = pydantic.Field(default=None)
    product_id:   str
    product_type: ProductType
    product_name: Optional[str] = None
    defect:       bool = False

    @pydantic.model_validator(mode="after")
    def _set_name(self) -> "Product":
        names = {
            ProductType.single:     "Produto Simples (Base + Medição)",
            ProductType.industrial: "Produto Industrial (Base + Furo)",
            ProductType.complete:   "Produto Completo (Base + Furo + Tampa)",
        }
        self.product_name = names.get(self.product_type, "Desconhecido")
        return self


class Order(pydantic.BaseModel):
    id:         Optional[int] = pydantic.Field(default=None)
    order_id:   str
    product:    Product
    quantity:   int
    production: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ── Subscription handler (PLC → AAS mirror + EdgeDetectors) ──────────────────

class _SyncHandler:
    """
    Recebe notificações asyncua e:
      1. Espelha o valor no nó AAS correspondente
      2. Aciona EdgeDetectors registrados para detecção de borda
    """

    def __init__(self, ctx: SubmodelContext, mapping: Dict[str, NodeMetadata]):
        self._ctx     = ctx
        self._mapping = mapping          # nodeid_str → NodeMetadata AAS
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
                logger.warning("magfront.mirror.error", node=nid, error=str(exc))

        det = self._detectors.get(nid)
        if det:
            det.update(int(val), nid)

    async def event_notification(self, event) -> None:
        pass


# ── aiofase MicroService (inter-serviço) ──────────────────────────────────────

class _MagFrontService(MicroService):
    """
    Microservice aiofase para MAGFRONT.

    Registra as ações mag_front_push_order e mag_front_stop_conveyor,
    e inicia a task de processamento de pedidos — exatamente como no
    MagFrontMicroservice original do smart-factory.

    A lógica de ciclo é delegada para IOInterface._cycle() que tem
    acesso ao address_space do faaster para espelhar no AAS.
    """

    def __init__(self, ext: "IOInterface") -> None:
        sender   = os.environ.get("AIOFASE_SENDER",   "tcp://0.0.0.0:3000")
        receiver = os.environ.get("AIOFASE_RECEIVER", "tcp://0.0.0.0:4000")
        super().__init__(self, sender, receiver)
        self._ext        = ext
        self.queue_order: asyncio.Queue = asyncio.Queue()

    # ── Ações aiofase ──────────────────────────────────────────────────────

    @MicroService.action
    async def mag_front_stop_conveyor(self, service, data: dict) -> None:
        """Chamada pelo serviço de medição quando há peça NOK."""
        value = data["value"]
        await self._ext._write("3:xQA1_A1", value)

    @MicroService.action
    async def mag_front_push_order(self, service, data: dict) -> None:
        """Recebe um pedido do manager e coloca na fila de processamento."""
        order = Order(**data)
        await self.queue_order.put(order)

    # ── Task aiofase ───────────────────────────────────────────────────────

    @MicroService.task
    async def task_process_orders(self) -> None:
        """
        Loop principal de processamento — fiel ao original mag_front.py.
        Aguarda pedido na fila e executa o ciclo de inserção.
        """
        logger.info("magfront.orders.loop.start")
        while True:
            order = await self.queue_order.get()
            logger.info("magfront.order.start", order_id=order.order_id)

            await self._ext._cycle(order, self)

            logger.info("magfront.order.done", order_id=order.order_id)


# ── Faaster extension principal ───────────────────────────────────────────────

class IOInterface(ISubmodelExtension):
    """
    IOInterface — Estação 1 MAGFRONT.

    Integra o MagFrontMicroservice (aiofase) ao faaster:
      • Watchdog reconecta o OPC UA automaticamente em caso de falha
      • Cada escrita no PLC espelha o valor no nó AAS correspondente
      • As ações aiofase (push_order, stop_conveyor) funcionam igual
        ao smart-factory original
    """

    def __init__(self, context: SubmodelContext) -> None:
        self._ctx     = context
        self._plc_url = os.environ.get("PLC_URL", _PLC_URL)

        self._plc: Optional[Client]  = None
        self._connected: bool        = False
        self._tasks: List[asyncio.Task] = []

        # Nós OPC UA resolvidos após conexão
        self._inputs:   Dict[str, Node]         = {}
        self._outputs:  Dict[str, Node]         = {}
        self._id_meta:  Dict[str, NodeMetadata] = {}
        self._handler:  Optional[_SyncHandler]  = None
        self._detector: Optional[EdgeDetector]  = None   # stopper

        # Microservice aiofase (criado aqui, iniciado em init())
        self._service: _MagFrontService = _MagFrontService(self)

    # ── ISubmodelExtension ────────────────────────────────────────────────────

    async def init(self) -> None:
        # 1. Conecta ao PLC (primeira tentativa; watchdog cuida das seguintes)
        try:
            await self._connect_plc()
        except Exception as exc:
            logger.warning("magfront.plc.first_connect_failed",
                           error=str(exc),
                           retry_in=_RECONNECT_DELAY)

        # 2. Watchdog de reconexão OPC UA
        self._tasks.append(asyncio.create_task(self._plc_watchdog()))

        # 3. Inicia o microservice aiofase (run() é blocking via task)
        self._tasks.append(asyncio.create_task(self._service.run()))

        logger.info("magfront.io_interface.ready",
                    plc=self._plc_url,
                    connected=self._connected)

    async def stop(self) -> None:
        for t in self._tasks:
            t.cancel()
        if self._plc and self._connected:
            try:
                await self._plc.disconnect()
            except Exception:
                pass

    # ── OPC UA: conexão + watchdog ────────────────────────────────────────────

    async def _plc_watchdog(self) -> None:
        """
        Verifica a cada _RECONNECT_DELAY segundos se o PLC está conectado.
        Em caso de desconexão, tenta reconectar e recria os nós e subscription.
        """
        while True:
            await asyncio.sleep(_RECONNECT_DELAY)
            if not self._connected:
                logger.info("magfront.plc.reconnecting")
                try:
                    await self._connect_plc()
                    logger.info("magfront.plc.reconnected")
                except Exception as exc:
                    logger.warning("magfront.plc.reconnect_failed",
                                   error=str(exc),
                                   retry_in=_RECONNECT_DELAY)

    async def _connect_plc(self) -> None:
        """
        Estabelece conexão com o PLC, resolve todos os nós e cria a
        subscription asyncua para espelhamento contínuo no AAS.
        """
        # fecha conexão antiga se existir
        if self._plc is not None:
            try:
                await self._plc.disconnect()
            except Exception:
                pass

        self._plc       = Client(self._plc_url)
        self._inputs    = {}
        self._outputs   = {}
        self._id_meta   = {}
        self._connected = False

        await self._plc.connect()

        objects  = self._plc.get_objects_node()
        device   = await objects.get_child(_PLC_DEVICE)
        inp_f    = await device.get_child("3:Inputs")
        out_f    = await device.get_child("3:Outputs")

        self._handler = _SyncHandler(self._ctx, self._id_meta)

        # resolve nós de entrada
        for name, aas_path in _INPUTS.items():
            node = await inp_f.get_child(name)
            self._inputs[name] = node
            if aas_path:
                meta = self._ctx.get_node(aas_path)
                if meta:
                    self._id_meta[str(node.nodeid)] = meta

        # resolve nós de saída
        for name in _OUTPUTS:
            self._outputs[name] = await out_f.get_child(name)

        # edge detector do sensor de stopper
        stopper = self._inputs["3:xCL_BG7"]
        self._detector = EdgeDetector(stopper.nodeid, EdgeType.RISING)
        self._handler.register(str(stopper.nodeid), self._detector)

        sub = await self._plc.create_subscription(10, self._handler)
        await sub.subscribe_data_change(list(self._inputs.values()))

        # estado inicial dos atuadores (igual ao mag_front.py original)
        await self._write_raw("3:xCL_MB1", True)   # enable feeder
        await self._write_raw("3:xCL_MB2", False)  # feeder recolhido
        await self._write_raw("3:xCL_MB3", True)   # suporte inferior
        await self._write_raw("3:xCL_MB4", True)   # suporte superior
        await self._write_raw("3:xQA1_A1", True)   # esteira ligada

        self._connected = True
        logger.info("magfront.plc.connected", url=self._plc_url)

    # ── PLC write helpers ─────────────────────────────────────────────────────

    async def _write_raw(self, name: str, value: bool) -> None:
        """Escreve diretamente no nó PLC sem verificar _connected (usado em _connect_plc)."""
        node = self._outputs.get(name)
        if node is None:
            return
        dv = DataValue(Value=Variant(value, UA_VT.Boolean))
        await node.set_data_value(dv)

    async def _write(self, name: str, value: bool) -> None:
        """
        Escreve no PLC e espelha o valor no nó AAS correspondente.
        Em caso de falha OPC UA marca _connected = False para acionar
        o watchdog de reconexão.
        """
        if not self._connected:
            logger.warning("magfront.write.skipped.disconnected", name=name)
            return
        try:
            await self._write_raw(name, value)
        except Exception as exc:
            logger.error("magfront.write.failed",
                         name=name, value=value, error=str(exc))
            self._connected = False   # watchdog reconectará
            return

        # espelha no AAS
        aas_path = _OUTPUTS.get(name)
        if aas_path:
            meta = self._ctx.get_node(aas_path)
            if meta:
                try:
                    await self._ctx.address_space.set_value(meta.node, value)
                except Exception as exc:
                    logger.warning("magfront.aas_mirror.error",
                                   path=aas_path, error=str(exc))

    # ── Ciclo de produção (fiel ao task_process_orders do mag_front.py) ───────

    async def _cycle(self, order: Order, service: _MagFrontService) -> None:
        """
        Executa o ciclo completo de inserção de peça no magazine.
        Preserva a lógica e a ordem exata de operações do original.
        """
        det = self._detector
        if det is None:
            logger.error("magfront.cycle.no_detector")
            return

        # ── aguarda borda de subida: portador chegou ao stopper ────────────
        await det.wait()
        await service.request_action("manager_update_has_product",
                                     {"has_product": True})
        await self._write("3:xQA1_A1", False)      # para esteira
        await asyncio.sleep(0.5)
        det.set_enable(False)

        # ── ciclo de inserção da peça ──────────────────────────────────────
        await self._write("3:xCL_MB2", True)       # empurrador avança
        await asyncio.sleep(0.5)

        # libera suporte superior
        await self._write("3:xCL_MB4", False)
        await asyncio.sleep(0.5)
        await self._write("3:xCL_MB4", True)
        await asyncio.sleep(0.5)

        # libera suporte inferior
        await self._write("3:xCL_MB3", False)
        await asyncio.sleep(0.5)
        await self._write("3:xCL_MB3", True)
        await asyncio.sleep(0.5)

        # ── troca borda: aguarda portador sair do stopper ──────────────────
        det.set_trigger(EdgeType.FALLING)

        await self._write("3:xQA1_A1", True)       # liga esteira
        await self._write("3:xMB1",    True)       # stopper libera
        det.set_enable(True)

        await det.wait()                            # borda de descida

        await self._write("3:xMB1",    False)      # stopper retrai
        det.set_trigger(EdgeType.RISING)
        await self._write("3:xCL_MB2", True)       # empurrador retorna
        await asyncio.sleep(1)

        # ── encaminha pedido para o próximo serviço ────────────────────────
        logger.info("magfront.order.finished", order_id=order.order_id)
        await service.request_action("manager_update_has_product",
                                     {"has_product": False})
        await service.request_action("measurement_push_order",
                                     {"order": order.model_dump(mode="json")})
