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


class MagBackMicroservice(MicroService):
    def __init__(self, url: str):
        super().__init__(self, 'tcp://0.0.0.0:3000', 'tcp://0.0.0.0:4000')
        self.queue_order = asyncio.Queue()
        self.client = Client(url)

    async def set_value(self, node: Node, value: bool):
        dv = DataValue(Value=Variant(value, VariantType=VariantType.Boolean))
        await node.set_data_value(dv)

    async def init(self):
        await self.client.connect()
        objects_node = self.client.get_objects_node()

        inputs = await objects_node.get_child(['2:DeviceSet', '3:plcMagBack', '3:Inputs'])
        outputs = await objects_node.get_child(['2:DeviceSet', '3:plcMagBack', '3:Outputs'])

        self.node_enable_feeder = await outputs.get_child([f'3:xCL_MB1'])
        self.node_feeder = await outputs.get_child('3:xCL_MB2')
        self.node_bottom_support = await outputs.get_child('3:xCL_MB3')
        self.node_upper_support = await outputs.get_child('3:xCL_MB4')
        self.node_engine_conveyor = await outputs.get_child('3:xQA1_A1')
        self.node_stopper = await outputs.get_child('3:xMB1')

        self.node_sensor_stoppper = await inputs.get_child('3:xCL_BG7')
        self.stopper_edge_detector = EdgeDetector(self.node_sensor_stoppper.nodeid, EdgeType.RISING)

        handler = SensorEventHandler(self.stopper_edge_detector)
        sub = await self.client.create_subscription(10, handler)
        await sub.subscribe_data_change(self.node_sensor_stoppper)

        # await self.set_value(self.node_stopper, True)
        await self.set_value(self.node_enable_feeder, True),
        await self.set_value(self.node_feeder, False),
        await self.set_value(self.node_bottom_support, True),
        await self.set_value(self.node_upper_support, True),
        await self.set_value(self.node_engine_conveyor, True)

    @MicroService.action
    async def mag_back_push_order(self, service: str, data: dict):
        await self.queue_order.put(Order(**data['order']))

    @MicroService.task
    async def task_process_orders(self):
        logger.info("Start processing orders in Mag Back Microservice")

        while True:
            order: Order = await self.queue_order.get()
            logger.info(f"Processing order {order.order_id} for product {order.product}")

            # espera a borda de subida do sensor de stopper
            await self.stopper_edge_detector.wait()
            await self.request_action('manager_update_has_product', {'has_product': True})
            await self.set_value(self.node_engine_conveyor, False)
            await asyncio.sleep(0.5)
            self.stopper_edge_detector.set_enable(False)

            # inicia o ciclo de inserção
            await self.set_value(self.node_feeder, True)
            await asyncio.sleep(0.5)

            # libera o de cima
            await self.set_value(self.node_upper_support, False)
            await asyncio.sleep(0.5)
            await self.set_value(self.node_upper_support, True)
            await asyncio.sleep(0.5)

            # libera de baixo
            await self.set_value(self.node_bottom_support, False)
            await asyncio.sleep(0.5)
            await self.set_value(self.node_bottom_support, True)
            await asyncio.sleep(0.5)

            # troca a borda do sensor
            self.stopper_edge_detector.set_trigger(EdgeType.FALLING)

            # libera a base
            await self.set_value(self.node_feeder, False)
            await asyncio.sleep(0.5)
            await self.set_value(self.node_engine_conveyor, True)
            await self.set_value(self.node_stopper, True)
            self.stopper_edge_detector.set_enable(True)

            # espera a borda de descida do sensor
            await self.stopper_edge_detector.wait()

            await self.set_value(self.node_stopper, False)
            self.stopper_edge_detector.set_trigger(EdgeType.RISING)
            await self.request_action('manager_update_has_product', {'has_product': False})
            await self.request_action('mag_press_push_order', {'order': order.model_dump(mode='json')})

            logger.info(f"Finished processing order {order.order_id}")
            await asyncio.sleep(1)


async def main(args):
    mag_back_service = MagBackMicroservice(args.url)
    await mag_back_service.init()
    await mag_back_service.run()


if __name__ == '__main__':
    parser = ArgumentParser(description="The client service to connect and control PLC Mag Back")
    parser.add_argument("--url", type=str, default="opc.tcp://172.21.6.1:4840", help="The OPC UA server URL")

    args = parser.parse_args()

    asyncio.run(main(args))
