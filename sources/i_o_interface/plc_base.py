"""
PLCIOBase — infraestrutura comum para extensões IOInterface de estação única.

Gerencia ciclo de vida da conexão OPC UA (connect, watchdog, disconnect),
resolução de nós (_INPUTS / _OUTPUTS) e espelhamento AAS em cada escrita.

Subclasses devem definir atributos de classe:
    _PLC_URL_DEFAULT  — endpoint padrão (override via env PLC_URL)
    _PLC_DEVICE       — caminho de browse-names do ObjectsNode até o PLC
    _INPUTS           — {browse_name: aas_path|None}  (pasta Inputs)
    _OUTPUTS          — {browse_name: aas_path|None}  (pasta Outputs)

Subclasses podem sobrescrever:
    _on_connected()   — EdgeDetectors, subscriptions, estado inicial das saídas
    _start_service()  — iniciar tasks do aiofase MicroService
"""

import asyncio
import os
from typing import ClassVar, Dict, List, Optional

from asyncua import Client, Node
from asyncua.ua import DataValue, Variant, VariantType as UA_VT

from faaster.extensions.interfaces import ISubmodelExtension
from faaster.extensions.context import SubmodelContext
from faaster.parser.node_registry import NodeMetadata
from faaster.log import get_logger

logger = get_logger(__name__)

_RECONNECT_DELAY = float(os.environ.get("RECONNECT_DELAY", "5"))


class PLCIOBase(ISubmodelExtension):
    _PLC_URL_DEFAULT: ClassVar[str] = "opc.tcp://0.0.0.0:4840"
    _PLC_DEVICE:      ClassVar[List[str]] = []
    _INPUTS:          ClassVar[Dict[str, Optional[str]]] = {}
    _OUTPUTS:         ClassVar[Dict[str, Optional[str]]] = {}

    def __init__(self, context: SubmodelContext) -> None:
        self._ctx       = context
        self._plc_url   = os.environ.get("PLC_URL", self._PLC_URL_DEFAULT)
        self._plc: Optional[Client] = None
        self._connected = False
        self._tasks: List[asyncio.Task] = []
        self._inputs:  Dict[str, Node]         = {}
        self._outputs: Dict[str, Node]         = {}
        self._id_meta: Dict[str, NodeMetadata] = {}
        self._inp_folder: Optional[Node] = None
        self._out_folder: Optional[Node] = None
        # Sinalizado pela estação downstream quando está pronta para receber
        # o próximo carrier. Inicia como set() para que o primeiro pedido flua.
        self._downstream_ready: asyncio.Event = asyncio.Event()
        self._downstream_ready.set()

    # ── ISubmodelExtension ────────────────────────────────────────────────────

    async def init(self) -> None:
        try:
            await self._connect_plc()
        except Exception as exc:
            logger.warning("plc.first_connect_failed",
                           plc=self._plc_url, error=str(exc),
                           retry_in=_RECONNECT_DELAY)
        self._tasks.append(asyncio.create_task(self._plc_watchdog()))
        await self._start_service()

    async def stop(self) -> None:
        for t in self._tasks:
            t.cancel()
        if self._plc and self._connected:
            try:
                await self._plc.disconnect()
            except Exception:
                pass

    # ── Hooks (override in subclass) ──────────────────────────────────────────

    async def _start_service(self) -> None:
        """Inicia aiofase MicroService. Chamado uma vez após init()."""
        pass

    async def _on_connected(self) -> None:
        """
        Chamado após resolução dos nós. Subclasse deve:
          - construir EdgeDetector(s) a partir de self._inputs
          - criar subscription asyncua
          - escrever estado inicial das saídas via _write_raw()
        """
        pass

    # ── OPC UA: conexão + watchdog ────────────────────────────────────────────

    async def _plc_watchdog(self) -> None:
        while True:
            await asyncio.sleep(_RECONNECT_DELAY)
            if not self._connected:
                logger.info("plc.reconnecting", plc=self._plc_url)
                try:
                    await self._connect_plc()
                    logger.info("plc.reconnected", plc=self._plc_url)
                except Exception as exc:
                    logger.warning("plc.reconnect_failed",
                                   plc=self._plc_url, error=str(exc),
                                   retry_in=_RECONNECT_DELAY)

    async def _connect_plc(self) -> None:
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

        objects = self._plc.get_objects_node()
        device  = await objects.get_child(self._PLC_DEVICE)
        inp_f   = await device.get_child("3:Inputs")
        out_f   = await device.get_child("3:Outputs")
        self._inp_folder = inp_f
        self._out_folder = out_f

        for name, aas_path in self._INPUTS.items():
            node = await inp_f.get_child(name)

            self._inputs[name] = node
            if aas_path:
                meta = self._ctx.get_node(aas_path)
                if meta:
                    self._id_meta[str(node.nodeid)] = meta

        for name in self._OUTPUTS:
            self._outputs[name] = await out_f.get_child(name)

        await self._on_connected()
        self._connected = True
        logger.info("plc.connected", url=self._plc_url)

    # ── Write helpers ─────────────────────────────────────────────────────────

    async def _write_raw(self, name: str, value: bool) -> None:
        """Escreve no nó PLC sem verificar _connected. Seguro em _on_connected."""
        node = self._outputs.get(name)
        
        if node is None:
            return
        
        dv = DataValue(Value=Variant(value, UA_VT.Boolean))
        await node.set_data_value(dv)

    async def _write(self, name: str, value: bool) -> None:
        """Escreve no PLC e espelha no AAS. Marca desconectado em falha."""
        if not self._connected:
            logger.warning("plc.write.skipped.disconnected", name=name)
            return
        
        try:
            await self._write_raw(name, value)
        
        except Exception as exc:
            logger.error("plc.write.failed", name=name, value=value, error=str(exc))
            self._connected = False
            return

        aas_path = self._OUTPUTS.get(name)
        
        if aas_path:
            meta = self._ctx.get_node(aas_path)
            if meta:
                try:
                    await self._ctx.address_space.set_value(meta.node, value)
                except Exception as exc:
                    logger.warning("plc.aas_mirror.error",
                                   path=aas_path, error=str(exc))
