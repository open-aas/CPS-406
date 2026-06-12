from typing import List, Optional
from argparse import ArgumentParser
from aiofase import MicroService
from asyncua import Client, Node
from asyncua.ua import DataValue, VariantType, Variant
from edge_detector import EdgeDetector, EdgeType, SensorEventHandler
from models import Order, Product

import asyncio
import structlog

logger = structlog.getLogger(__name__)


class MagDrillMicroservice(MicroService):
    def __init__(self, url: str):
        super().__init__(self, 'tcp://0.0.0.0:3000', 'tcp://0.0.0.0:4000')
        self.queue_order = asyncio.Queue()
        self.client = Client(url)
        self.future_drill_complete = asyncio.Future()

    async def set_value(self, node: Node, value: bool):
        dv = DataValue(Value=Variant(value, VariantType=VariantType.Boolean))
        await node.set_data_value(dv)

    @MicroService.action
    async def mag_drill_push_order(self, service: str, data: dict):
        await self.queue_order.put(Order(**data['order']))

    @MicroService.action
    async def on_drill_complete(self, service: str, data: dict):
        logger.info("Upper Drill complete")
        self.future_drill_complete.set_result(True)

    async def init(self):
        await self.client.connect()
        objects_node = self.client.get_objects_node()

        outputs = await objects_node.get_child(['2:DeviceSet', '3:plciDrill', '3:Outputs'])
        inputs = await objects_node.get_child(['2:DeviceSet', '3:plciDrill', '3:Inputs'])

        self.node_engine_conveyor = await outputs.get_child('3:xQA1_A1')
        self.node_stopper = await outputs.get_child('3:xMB1')

        self.node_sensor_stoppper = await inputs.get_child('3:xBG1_BCD0')
        self.stopper_edge_detector = EdgeDetector(self.node_sensor_stoppper.nodeid, EdgeType.RISING)
        self.stopper_edge_detector.set_enable(False)

        handler = SensorEventHandler(self.stopper_edge_detector)
        sub = await self.client.create_subscription(10, handler)
        await sub.subscribe_data_change(self.node_sensor_stoppper)

        await self.set_value(self.node_engine_conveyor, True)
        await self.set_value(self.node_stopper, False)

    @MicroService.task
    async def task_process_order(self):
        logger.info("Start processing orders in Mag Drill Microservice")

        while True:
            order: Order = await self.queue_order.get()
            logger.info(f"Processing order {order.order_id} for product {order.product}")
            self.stopper_edge_detector.set_enable(True)

            # espera a borda de subida do sensor de stopper
            await self.stopper_edge_detector.wait()
            await self.request_action('manager_update_has_product', {'has_product': True})
            await self.set_value(self.node_engine_conveyor, False)
            await asyncio.sleep(0.5)

            # avisa a drill para iniciar a furação e aguarda o estado
            await self.request_action('mag_upper_drill_push_order', {'order': order.model_dump(mode='json')})
            await self.future_drill_complete
            self.future_drill_complete = asyncio.Future()
            await asyncio.sleep(0.5)

            # libera a trava
            await self.set_value(self.node_stopper, True)
            await self.set_value(self.node_engine_conveyor, True)

            # levanta a trava
            await asyncio.sleep(2)
            await self.set_value(self.node_stopper, False)

            await self.request_action('manager_update_has_product', {'has_product': False})
            await self.request_action('mag_back_push_order', {'order': order.model_dump(mode='json')})
            logger.info(f"Finished processing order {order.order_id}")


async def main(args):
    measurement_service = MagDrillMicroservice(args.url)
    await measurement_service.init()
    await measurement_service.run()


if __name__ == '__main__':
    parser = ArgumentParser(description="The client service to connect and control PLC Drill")
    parser.add_argument("--url", type=str, default="opc.tcp://172.21.3.1:4840", help="The OPC UA server URL")

    args = parser.parse_args()

    asyncio.run(main(args))
