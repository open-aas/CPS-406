from argparse import ArgumentParser
from aiofase.microservice import MicroService
from datetime import datetime
from asyncua import Client, Node
from asyncua.ua import DataValue, VariantType, Variant
from edge_detector import EdgeDetector, SensorEventHandler, EdgeType
from models import Order, Product

import asyncio
import structlog

logger = structlog.getLogger(__name__)


class MagPressMicroservice(MicroService):
    def __init__(self, url: str):
        super().__init__(self, 'tcp://0.0.0.0:3000', 'tcp://0.0.0.0:4000')
        self.queue_order = asyncio.Queue()
        self.client = Client(url)

    async def set_value(self, node: Node, value: bool):
        dv = DataValue(Value=Variant(value, VariantType=VariantType.Boolean))
        await node.set_data_value(dv)

    @MicroService.action
    async def mag_press_push_order(self, service: str, data: dict):
        await self.queue_order.put(Order(**data['order']))

    async def press(self):
        await self.set_value(self.node_cilider_up, False)
        await self.set_value(self.node_cilider_down, True)

    async def unpress(self):
        await self.set_value(self.node_cilider_up, True)
        await self.set_value(self.node_cilider_down, False)

    async def init(self):
        await self.client.connect()
        objects_node = self.client.get_objects_node()

        inputs = await objects_node.get_child(['2:DeviceSet', '3:plcPress', '3:Inputs'])
        outputs = await objects_node.get_child(['2:DeviceSet', '3:plcPress', '3:Outputs'])

        # self.node_enable_feeder = await outputs.get_child([f'3:xCL_MB1'])
        # self.node_feeder = await outputs.get_child('3:xCL_MB2')
        # self.node_bottom_support = await outputs.get_child('3:xCL_MB3')
        # self.node_upper_support = await outputs.get_child('3:xCL_MB4')
        self.node_engine_conveyor = await outputs.get_child('3:xQA1_A1')
        self.node_stopper = await outputs.get_child('3:xMB1')
        self.node_cilider_up = await outputs.get_child('3:xHL_MB1')
        self.node_cilider_down = await outputs.get_child('3:xHL_MB2')

        self.node_sensor_stoppper = await inputs.get_child('3:xBG1')
        self.stopper_edge_detector = EdgeDetector(self.node_sensor_stoppper.nodeid, EdgeType.RISING)

        self.node_sensor_has_piece = await inputs.get_child('3:xHL_BG8')
        self.has_piece_edge_detector = EdgeDetector(self.node_sensor_has_piece.nodeid, EdgeType.FALLING)

        handler = SensorEventHandler(self.stopper_edge_detector)
        handler.add_detect(self.has_piece_edge_detector)
        sub = await self.client.create_subscription(10, handler)
        await sub.subscribe_data_change([self.node_sensor_stoppper, self.node_sensor_has_piece])

        await self.set_value(self.node_stopper, False)
        await self.set_value(self.node_cilider_up, True),
        await self.set_value(self.node_engine_conveyor, True)

    @MicroService.task
    async def task_process_orders(self):
        logger.info("Start processing orders in Mag Press Microservice")

        while True:
            order: Order = await self.queue_order.get()
            logger.info(f"Processing order {order.order_id} for product {order.product}")

            await self.stopper_edge_detector.wait()
            await self.request_action('manager_update_has_product', {'has_product': True})
            await self.set_value(self.node_engine_conveyor, False)

            await asyncio.sleep(1)
            await self.press()
            await asyncio.sleep(1)
            await self.unpress()
            await asyncio.sleep(1)

            await self.set_value(self.node_engine_conveyor, True)
            await self.set_value(self.node_stopper, True)

            await self.has_piece_edge_detector.wait()

            await self.set_value(self.node_stopper, False)
            await self.request_action('manager_update_has_product', {'has_product': False})
            logger.info(f"Finished processing order {order.order_id}")

            await asyncio.sleep(1)


async def main(args):
    mag_press_service = MagPressMicroservice(args.url)
    await mag_press_service.init()
    await mag_press_service.run()


if __name__ == '__main__':
    parser = ArgumentParser(description="The client service to connect and control PLC Mag Press")
    parser.add_argument("--url", type=str, default="opc.tcp://172.21.7.1:4840", help="The OPC UA server URL")

    args = parser.parse_args()

    asyncio.run(main(args))
