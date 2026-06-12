from typing import List, Optional
from aiofase import MicroService
from asyncua import Client
from asyncua.ua import DataValue, VariantType, Variant
from asyncua import Node
from edge_detector import EdgeDetector, SensorEventHandler, EdgeType
from models import Order, Product

import asyncio
import structlog

logger = structlog.getLogger(__name__)


class MagUpperDrillMicroservice(MicroService):
    def __init__(self, url: str):
        super().__init__(self, 'tcp://0.0.0.0:3000', 'tcp://0.0.0.0:4000')
        self.queue_order = asyncio.Queue()
        self.client = Client(url)

    async def set_value(self, node: Node, value: bool):
        dv = DataValue(Value=Variant(value, VariantType=VariantType.Boolean))
        await node.set_data_value(dv)

    async def get_children(self, root: Node, path: List[str]) -> Optional[Node]:
        for p in path:
            children = await root.get_children()

            for i, child in enumerate(children):
                name = (await child.read_browse_name()).Name

                if name == p:
                    root = child
                    break

                if i == len(children) - 1:
                    return None

        return root

    async def init(self):
        await self.client.connect()
        objects_node = self.client.get_objects_node()
        inputs = outputs = await self.get_children(objects_node, ['CECC-LK', 'Application', 'Station_IO'])

        if inputs:
            self.move_x_left = await self.get_children(outputs, ['xMB1_opcua'])
            self.move_x_right = await self.get_children(outputs, ['xMB2_opcua'])
            self.drilling_1 = await self.get_children(outputs, ['xMA3_opcua'])
            self.drilling_2 = await self.get_children(outputs, ['xMA4_opcua'])
            self.move_drilling_upper = await self.get_children(outputs, ['xMB5_opcua'])
            self.move_drilling_lower = await self.get_children(outputs, ['xMB6_opcua'])
            self.break_z = await self.get_children(outputs, ['xMB7_opcua'])

            self.node_upper_limit = await self.get_children(inputs, ['xBG5'])
            self.node_bottom_limit = await self.get_children(inputs, ['xBG6'])

            self.node_left_limit = await self.get_children(inputs, ['xBG1'])
            self.node_right_limit = await self.get_children(inputs, ['xBG2'])

            self.limit_upper_detector = EdgeDetector(self.node_upper_limit.nodeid, EdgeType.RISING, enable=False)
            self.limit_bottom_detector = EdgeDetector(self.node_bottom_limit.nodeid, EdgeType.RISING, enable=False)
            self.limit_left_detector = EdgeDetector(self.node_left_limit.nodeid, EdgeType.RISING, enable=False)
            self.limit_right_detector = EdgeDetector(self.node_right_limit.nodeid, EdgeType.RISING, enable=False)

            # cria os sensor event
            handler = SensorEventHandler(self.limit_upper_detector)
            handler.add_detect([self.limit_bottom_detector, self.limit_left_detector, self.limit_right_detector])
            sub = await self.client.create_subscription(10, handler)
            await sub.subscribe_data_change(
                [self.node_upper_limit, self.node_bottom_limit, self.node_left_limit, self.node_right_limit])

            # desliga os motores
            await self.set_value(self.drilling_1, False)
            await self.set_value(self.drilling_2, False)
            await asyncio.sleep(0.5)

            # libera a trava
            await self.set_value(self.break_z, True)
            await asyncio.sleep(0.5)

            # move o X para o inicio
            await self.set_value(self.move_x_left, False)
            await self.set_value(self.move_x_right, True)
            await asyncio.sleep(0.5)

            # move o Z para cima
            await self.set_value(self.move_drilling_upper, True)
            await self.set_value(self.move_drilling_lower, False)
            await asyncio.sleep(0.5)

            return

        logger.error('not found inputs nodes')

    @MicroService.action
    async def mag_upper_drill_push_order(self, service: str, data: dict):
        await self.queue_order.put(Order(**data['order']))

    @MicroService.task
    async def task_process_orders(self):
        self.limit_upper_detector.set_enable(True)
        self.limit_bottom_detector.set_enable(True)
        self.limit_left_detector.set_enable(True)
        self.limit_right_detector.set_enable(True)
        logger.info("Start processing orders in Mag Upper Drill Microservice")

        while True:
            order: Order = await self.queue_order.get()
            logger.info(f"Processing order {order.order_id} for product {order.product}")

            # move para a esquerda
            await self.set_value(self.move_x_left, True)
            await self.set_value(self.move_x_right, False)
            await self.limit_left_detector.wait()
            await asyncio.sleep(0.5)

            # baixa
            await self.set_value(self.move_drilling_upper, False)
            await self.set_value(self.move_drilling_lower, True)
            await self.limit_bottom_detector.wait()
            await asyncio.sleep(0.5)

            # liga os motores
            await self.set_value(self.drilling_1, True)
            await self.set_value(self.drilling_2, True)

            # simular 5 segundos de furação
            await asyncio.sleep(5)

            # desliga os motores
            await self.set_value(self.drilling_1, False)
            await self.set_value(self.drilling_2, False)
            await asyncio.sleep(0.5)

            # levanta
            await self.set_value(self.move_drilling_upper, True)
            await self.set_value(self.move_drilling_lower, False)
            await self.limit_upper_detector.wait()
            await asyncio.sleep(0.5)

            # move para a direita
            self.limit_right_detector.set_enable(False)
            await self.set_value(self.move_x_left, False)
            await self.set_value(self.move_x_right, True)
            self.limit_right_detector.set_enable(True)
            await self.limit_right_detector.wait()
            await asyncio.sleep(0.5)

            # baixa
            await self.set_value(self.move_drilling_upper, False)
            await self.set_value(self.move_drilling_lower, True)
            await self.limit_bottom_detector.wait()
            await asyncio.sleep(0.5)

            # liga os motores
            await self.set_value(self.drilling_1, True)
            await self.set_value(self.drilling_2, True)

            # simular 5 segundos de furação
            await asyncio.sleep(5)

            # desliga os motores
            await self.set_value(self.drilling_1, False)
            await self.set_value(self.drilling_2, False)
            await asyncio.sleep(0.5)

            # levanta
            await self.set_value(self.move_drilling_upper, True)
            await self.set_value(self.move_drilling_lower, False)
            await self.limit_upper_detector.wait()
            await asyncio.sleep(0.5)

            await self.request_action('on_drill_complete', {})
            logger.info(f"Finished processing order {order.order_id}")


async def main(args):
    mag_upper_drill_microservice = MagUpperDrillMicroservice(args.url)
    await mag_upper_drill_microservice.init()
    await mag_upper_drill_microservice.run()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Mag Upper Drill Microservice")
    parser.add_argument(
        "--url",
        type=str,
        default="opc.tcp://172.21.3.2:4840",
        help="OPC UA server URL",
    )
    args = parser.parse_args()
    asyncio.run(main(args))
