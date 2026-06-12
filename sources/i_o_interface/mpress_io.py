"""IOInterface — Estação 5: MPRESS (Prensa Pneumática)."""

import asyncio
import os
from typing import Dict, Optional

from aiofase.microservice import MicroService

from faaster.extensions.context import SubmodelContext
from faaster.log import get_logger

from .plc_base import PLCIOBase
from .models import Order
from .edge_detector import EdgeDetector, SensorEventHandler, EdgeType

logger = get_logger(__name__)

_PLC_DEVICE = ["2:DeviceSet", "3:plcPress"]

_INPUTS: Dict[str, Optional[str]] = {
    "3:xBG1":    "Conveyor/Sensors/BG1_CarrierPresence/Value",
    "3:xHL_BG8": None,  # sensor has_piece
}
_OUTPUTS: Dict[str, Optional[str]] = {
    "3:xQA1_A1": "Conveyor/Actuators/MB20_BeltMotor/Value",
    "3:xMB1":    "Conveyor/Actuators/Y1_StopperCylinder/Value",
    "3:xHL_MB1": None,  # cilindro cima  (muscle press up)
    "3:xHL_MB2": None,  # cilindro baixo (muscle press down)
}


class _MPressService(MicroService):
    def __init__(self, ext: "MPressIOInterface") -> None:
        sender   = os.environ.get("AIOFASE_SENDER",   "tcp://0.0.0.0:3000")
        receiver = os.environ.get("AIOFASE_RECEIVER", "tcp://0.0.0.0:4000")
        super().__init__(self, sender, receiver)
        self._ext        = ext
        self.queue_order: asyncio.Queue = asyncio.Queue(maxsize=1)

    @MicroService.action
    async def mag_press_push_order(self, service, data: dict) -> None:
        await self.queue_order.put(Order(**data["order"]))

    @MicroService.action
    async def mpress_downstream_ready(self, service, data: dict) -> None:
        """Chamado pela Out quando há slot disponível e está pronta para receber."""
        self._ext._downstream_ready.set()

    @MicroService.task
    async def task_process_orders(self) -> None:
        logger.info("mpress.orders.loop.start")
        while True:
            order = await self.queue_order.get()
            logger.info("mpress.order.start", order_id=order.order_id)
            await self._ext._cycle(order, self)
            logger.info("mpress.order.done", order_id=order.order_id)


class MPressIOInterface(PLCIOBase):
    _PLC_URL_DEFAULT = "opc.tcp://172.21.7.1:4840"
    _PLC_DEVICE      = _PLC_DEVICE
    _INPUTS          = _INPUTS
    _OUTPUTS         = _OUTPUTS

    def __init__(self, context: SubmodelContext) -> None:
        super().__init__(context)
        self._stopper_det:   Optional[EdgeDetector] = None
        self._has_piece_det: Optional[EdgeDetector] = None
        self._service = _MPressService(self)

    async def _on_connected(self) -> None:
        stopper_node   = self._inputs["3:xBG1"]
        has_piece_node = self._inputs["3:xHL_BG8"]

        self._stopper_det   = EdgeDetector(stopper_node.nodeid,   EdgeType.RISING)
        self._has_piece_det = EdgeDetector(has_piece_node.nodeid, EdgeType.FALLING)

        handler = SensorEventHandler(self._stopper_det)
        handler.add_detect(self._has_piece_det)
        sub = await self._plc.create_subscription(10, handler)
        await sub.subscribe_data_change([stopper_node, has_piece_node])

        await self._write_raw("3:xMB1",    False)
        await self._write_raw("3:xHL_MB1", True)
        await self._write_raw("3:xQA1_A1", True)
        self._service.request_action("magback_downstream_ready", {})

    async def _start_service(self) -> None:
        self._tasks.append(asyncio.create_task(self._service.run()))
        logger.info("mpress.io_interface.ready",
                    plc=self._plc_url, connected=self._connected)

    async def _press(self) -> None:
        await self._write("3:xHL_MB1", False)
        await self._write("3:xHL_MB2", True)

    async def _unpress(self) -> None:
        await self._write("3:xHL_MB1", True)
        await self._write("3:xHL_MB2", False)

    async def _cycle(self, order: Order, service: _MPressService) -> None:
        await self._stopper_det.wait()
        service.request_action("manager_update_has_product", {"has_product": True})
        await self._write("3:xQA1_A1", False)

        await asyncio.sleep(1)
        await self._press()
        await asyncio.sleep(1)
        await self._unpress()
        await asyncio.sleep(1)

        # Aguarda Out sinalizar que há slot disponível antes de liberar o carrier
        await self._downstream_ready.wait()
        self._downstream_ready.clear()

        await self._write("3:xQA1_A1", True)
        await self._write("3:xMB1",    True)

        await self._has_piece_det.wait()

        await self._write("3:xMB1", False)
        service.request_action("manager_update_has_product", {"has_product": False})
        service.request_action("out_push_order", {"order": order.model_dump(mode="json")})
        # Sinaliza MagBack que MPress está pronta para o próximo carrier
        service.request_action("magback_downstream_ready", {})
        logger.info("mpress.order.finished", order_id=order.order_id)

        await asyncio.sleep(1)
