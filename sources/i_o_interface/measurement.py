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


class MeasurementMicroservice(MicroService):
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

        inputs = await objects_node.get_child(['2:DeviceSet', '3:plcMeas', '3:Inputs'])
        outputs = await objects_node.get_child(['2:DeviceSet', '3:plcMeas', '3:Outputs'])

        self.node_engine_conveyor = await outputs.get_child('3:xQA1_A1')
        self.node_stopper = await outputs.get_child('3:xMB1')
        self.node_led_red = await outputs.get_child('3:xBG_PF1')
        self.node_led_orange = await outputs.get_child('3:xBG_PF2')
        self.node_led_green = await outputs.get_child('3:xBG_PF3')

        self.node_sensor_stoppper = await inputs.get_child('3:xBG_BG1')
        self.stopper_edge_detector = EdgeDetector(self.node_sensor_stoppper.nodeid, EdgeType.RISING)

        self.node_btn_start = await inputs.get_child('3:xSF1')
        self.btn_start_detector = EdgeDetector(self.node_btn_start.nodeid, EdgeType.RISING)
        self.node_led_btn_start = await outputs.get_child('3:xPF1')

        self.node_btn_reset = await inputs.get_child('3:xSF4')
        self.btn_reset_detector = EdgeDetector(self.node_btn_reset.nodeid, EdgeType.RISING)
        self.node_led_btn_reset = await outputs.get_child('3:xPF4')

        children = await inputs.get_children()

        for child in children:
            name = await child.read_browse_name()

            if name.Name == 'xBG_BG2.Q1':
                self.node_sensor_high = child

            elif name.Name == 'xBG_BG3.Q2':
                self.node_sensor_low = child

        handler = SensorEventHandler(self.stopper_edge_detector)
        handler.add_detect([self.btn_reset_detector, self.btn_start_detector])
        sub = await self.client.create_subscription(10, handler)
        await sub.subscribe_data_change([self.node_sensor_stoppper, self.node_btn_start, self.node_btn_reset])

        await self.set_value(self.node_engine_conveyor, True)
        await self.set_value(self.node_stopper, False)
        await self.set_value(self.node_led_red, False)
        await self.set_value(self.node_led_orange, False)
        await self.set_value(self.node_led_green, False)
        await self.set_value(self.node_led_btn_reset, False)
        await self.set_value(self.node_led_btn_start, False)

    async def task_toggle_led(self, node):
        while True:
            try:
                await self.set_value(node, True)
                await asyncio.sleep(0.5)
                await self.set_value(node, False)
                await asyncio.sleep(0.5)

            except asyncio.CancelledError:
                await self.set_value(node, False)
                break

    @MicroService.action
    async def measurement_push_order(self, service: str, data: dict):
        await self.queue_order.put(Order(**data['order']))

    @MicroService.task
    async def main_task_process_orders(self):
        logger.info("Start processing orders in Measurement Microservice")

        while True:
            order: Order = await self.queue_order.get()
            logger.info(f"Processing order {order.order_id} for product {order.product}")

            # espera a borda de subida do sensor de stopper
            await self.stopper_edge_detector.wait()
            await self.request_action('manager_update_has_product', {'has_product': True})
            await self.set_value(self.node_led_orange, True)

            await asyncio.sleep(1)

            # mede a posição da peça
            value_high = await self.node_sensor_high.get_value()
            value_low = await self.node_sensor_low.get_value()
            await self.set_value(self.node_led_orange, False)

            if value_low and value_high:
                await self.set_value(self.node_led_green, True)
                await self.set_value(self.node_stopper, True)
                await asyncio.sleep(2)

                await self.set_value(self.node_stopper, False)
                await self.set_value(self.node_led_green, False)
                await self.request_action('manager_update_has_product', {'has_product': False})
                await self.request_action('mag_drill_push_order', {'order': order.model_dump(mode='json')})
                logger.info(f"Finished processing order {order.order_id}")

            else:
                await self.set_value(self.node_led_red, True)
                await self.set_value(self.node_engine_conveyor, False)

                # para a esteira anterior parar
                task_toogle_led = asyncio.create_task(self.task_toggle_led(self.node_led_btn_reset))
                await self.request_action('mag_front_stop_conveyor', {'value': False})

                # espera o apertar reset
                await self.btn_reset_detector.wait()
                await self.set_value(self.node_led_red, False)
                await self.set_value(self.node_led_btn_start, True)
                task_toogle_led.cancel()

                await self.btn_start_detector.wait()
                await self.set_value(self.node_engine_conveyor, True)
                await self.request_action('mag_front_stop_conveyor', {'value': True})
                await self.set_value(self.node_led_btn_start, False)

            await asyncio.sleep(1)

        # print(f"Finished processing order {order.order_id}")


async def main(args):
    measurement_service = MeasurementMicroservice(args.url)
    await measurement_service.init()
    await measurement_service.run()


if __name__ == '__main__':
    parser = ArgumentParser(description="The client service to connect and control PLC Measurement")
    parser.add_argument("--url", type=str, default="opc.tcp://172.21.2.1:4840", help="The OPC UA server URL")

    args = parser.parse_args()

    asyncio.run(main(args))
