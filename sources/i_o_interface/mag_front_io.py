"""IOInterface — Estação 1: MAGFRONT (Magazine Frontal)."""

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

_PLC_DEVICE = ["2:DeviceSet", "3:plcMagFront"]

_INPUTS: Dict[str, Optional[str]] = {
    "3:xCL_BG7": "Conveyor/Sensors/BG1_CarrierPresence/Value",
}
_OUTPUTS: Dict[str, Optional[str]] = {
    "3:xQA1_A1": "Conveyor/Actuators/MB20_BeltMotor/Value",
    "3:xMB1":    "Conveyor/Actuators/Y1_StopperCylinder/Value",
    "3:xCL_MB1": None,
    "3:xCL_MB2": "Module/Actuators/Y1_PushCylinder/Value",
    "3:xCL_MB3": "Module/Actuators/Y2_MagazineAdvance/Value",
    "3:xCL_MB4": "Module/Actuators/Y2_MagazineAdvance/Value",
}


class _MagFrontService(MicroService):
    def __init__(self, ext: "MagFrontIOInterface") -> None:
        sender   = os.environ.get("AIOFASE_SENDER",   "tcp://0.0.0.0:3000")
        receiver = os.environ.get("AIOFASE_RECEIVER", "tcp://0.0.0.0:4000")
        super().__init__(self, sender, receiver)
        self._ext        = ext
        self.queue_order: asyncio.Queue = asyncio.Queue(maxsize=1)

    @MicroService.action
    async def mag_front_stop_conveyor(self, service, data: dict) -> None:
        await self._ext._write("3:xQA1_A1", data["value"])

    @MicroService.action
    async def mag_front_push_order(self, service, data: dict) -> None:
        await self.queue_order.put(Order(**data))

    @MicroService.action
    async def magfront_downstream_ready(self, service, data: dict) -> None:
        """Chamado pela Meas quando está pronta para receber o próximo carrier."""
        self._ext._downstream_ready.set()

    @MicroService.task
    async def task_process_orders(self) -> None:
        logger.info("magfront.orders.loop.start")
        while True:
            order = await self.queue_order.get()
            logger.info("magfront.order.start", order_id=order.order_id)
            await self._ext._cycle(order, self)
            logger.info("magfront.order.done", order_id=order.order_id)


class MagFrontIOInterface(PLCIOBase):
    _PLC_URL_DEFAULT = "opc.tcp://172.21.1.1:4840"
    _PLC_DEVICE      = _PLC_DEVICE
    _INPUTS          = _INPUTS
    _OUTPUTS         = _OUTPUTS

    def __init__(self, context: SubmodelContext) -> None:
        super().__init__(context)
        self._detector: Optional[EdgeDetector]       = None
        self._handler:  Optional[SensorEventHandler] = None
        self._service   = _MagFrontService(self)

    async def _on_connected(self) -> None:
        stopper          = self._inputs["3:xCL_BG7"]
        self._detector   = EdgeDetector(stopper.nodeid, EdgeType.RISING)
        self._handler    = SensorEventHandler(self._detector)
        sub = await self._plc.create_subscription(10, self._handler)
        await sub.subscribe_data_change(list(self._inputs.values()))

        await self._write_raw("3:xCL_MB1", True)
        await self._write_raw("3:xCL_MB2", False)
        await self._write_raw("3:xCL_MB3", True)
        await self._write_raw("3:xCL_MB4", True)
        await self._write_raw("3:xQA1_A1", True)

    async def _start_service(self) -> None:
        self._tasks.append(asyncio.create_task(self._service.run()))
        logger.info("magfront.io_interface.ready",
                    plc=self._plc_url, connected=self._connected)

    async def _cycle(self, order: Order, service: _MagFrontService) -> None:
        det = self._detector
        await self._write("3:xMB1", False)

        await det.wait()
        service.request_action("out_update_magfront_state", {"has_carrier": True})
        service.request_action("manager_update_has_product", {"has_product": True})

        await self._write("3:xQA1_A1", False)
        await asyncio.sleep(0.5)
        det.set_enable(False)

        await self._write("3:xCL_MB2", True)
        await asyncio.sleep(0.5)

        await self._write("3:xCL_MB4", False)
        await asyncio.sleep(0.5)
        await self._write("3:xCL_MB4", True)
        await asyncio.sleep(0.5)

        await self._write("3:xCL_MB3", False)
        await asyncio.sleep(0.5)
        await self._write("3:xCL_MB3", True)
        await asyncio.sleep(0.5)

        det.set_trigger(EdgeType.FALLING)

        # Aguarda Meas sinalizar que está pronta antes de liberar o carrier
        await self._downstream_ready.wait()
        self._downstream_ready.clear()

        await self._write("3:xQA1_A1", True)
        await self._write("3:xMB1",    True)

        det.set_enable(True)
        await det.wait()

        await self._write("3:xMB1",    False)
        service.request_action("out_update_magfront_state", {"has_carrier": False})
        det.set_trigger(EdgeType.RISING)
        await self._write("3:xCL_MB2", True)
        await asyncio.sleep(1)

        logger.info("magfront.order.finished", order_id=order.order_id)
        service.request_action("manager_update_has_product", {"has_product": False})
        service.request_action("measurement_push_order",{"order": order.model_dump(mode="json")})
