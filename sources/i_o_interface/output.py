from argparse import ArgumentParser
from aiofase.microservice import MicroService
from asyncua import Client, Node
from asyncua.ua import DataValue, VariantType, Variant

import asyncio

from edge_detector import SensorEventHandler, EdgeDetector, EdgeType


class Output(MicroService):
    def __init__(self, url):
        super().__init__(
            self, sender_endpoint='tcp://0.0.0.0:3000', receiver_endpoint='tcp://0.0.0.0:4000'
        )
        self.client = Client(url)

    async def set_value(self, node: Node, value: bool):
        dv = DataValue(Value=Variant(value, VariantType=VariantType.Boolean))
        await node.set_data_value(dv)

    async def init(self):
        await self.client.connect()
        objects_node = self.client.get_objects_node()

        inputs = await objects_node.get_child(['2:DeviceSet', '3:plcOut', '3:Inputs'])
        outputs = await objects_node.get_child(['2:DeviceSet', '3:plcOut', '3:Outputs'])

        self.engine_enable = await outputs.get_child([f'3:xKF1_DI10'])
        self.engine_left = await outputs.get_child([f'3:xKF1_DI1'])
        self.engine_right = await outputs.get_child([f'3:xKF1_DI2'])
        self.engine_trigger = await outputs.get_child([f'3:xKF1_DI6'])

        self.node_claw_upper = await outputs.get_child([f'3:xGM_MB1'])
        self.node_claw_lower = await outputs.get_child([f'3:xGM_MB2'])
        self.node_claw_enable = await outputs.get_child([f'3:xGM_MB3'])
        self.node_claw_open = await outputs.get_child([f'3:xGM_MB4'])

        self.node_engine_ismoving = await inputs.get_child([f'3:xKF1_DO0'])
        self.engine_ismoving_detector = EdgeDetector(self.node_engine_ismoving.nodeid, EdgeType.RISING, enable=False)

        self.node_engine_ready = await inputs.get_child([f'3:xKF1_DO10'])
        self.engine_ready_detector = EdgeDetector(self.node_engine_ready.nodeid, EdgeType.RISING)

        self.node_engine_reference = await inputs.get_child(['3:xKF1_DO9'])

        handler = SensorEventHandler(self.engine_ismoving_detector)
        handler.add_detect(self.engine_ready_detector)

        sub = await self.client.create_subscription(10, handler)
        await sub.subscribe_data_change([self.node_engine_ismoving, self.node_engine_ready])

        await self.set_value(self.node_claw_enable, True)
        await self.claw_upper()

    @MicroService.task
    async def task_process_order(self):
        # await self.engine_ready()
        # await self.move_home()
        # await asyncio.sleep(5)

        while True:
            await self.engine_ready()
            await self.move_left()
            await asyncio.sleep(5)

            await self.engine_ready()
            await self.move_right()
            await asyncio.sleep(5)

            await self.engine_ready()
            await self.move_home()
            await asyncio.sleep(5)
            # await self.engine_ready()

    async def engine_ready(self):
        while True:
            engine_reference = await self.node_engine_reference.get_value()
            engine_ready = await self.node_engine_ready.get_value()
            engine_motion_complete = await self.node_engine_ismoving.get_value()

            if engine_reference and engine_ready and engine_motion_complete:
                print('motor pronto ....')
                break

            print(f'esperando o motor ficar pronto: {engine_reference}, {engine_ready}')
            await asyncio.sleep(0.1)

        await asyncio.sleep(1)

    async def trigger_engine(self):
        """
            Trigga o sinal para o motor se mover
        """
        await self.set_value(self.engine_trigger, True)
        await asyncio.sleep(0.1)
        await self.set_value(self.engine_trigger, False)

    async def engine_motion_monitor(self):
        while True:
            # espera o motor começar a se mover, enquanto ele nao se mover, fica triggando o sinal
            await self.trigger_engine()
            engine_motion_complete = await self.node_engine_ismoving.get_value()
            if engine_motion_complete == 0:
                print('motor começou a se mover')
                break

        print('esperando o motor parar')
        await self.engine_ismoving_detector.wait()
        print('motor parou')

    async def move_left(self):
        print('movendo para a esquerda')
        self.engine_ismoving_detector.set_enable(True)
        await self.set_value(self.engine_enable, True)
        await self.set_value(self.engine_left, True)
        await self.set_value(self.engine_right, False)
        await self.engine_motion_monitor()

    async def move_home(self):
        print('movendo para a posição home')
        self.engine_ismoving_detector.set_enable(True)
        await self.set_value(self.engine_enable, True)
        await self.set_value(self.engine_left, True)
        await self.set_value(self.engine_right, True)
        await self.engine_motion_monitor()

    async def move_right(self):
        print('movendo para a direita')
        self.engine_ismoving_detector.set_enable(True)
        await self.set_value(self.engine_enable, True)
        await self.set_value(self.engine_left, False)
        await self.set_value(self.engine_right, True)

        await self.engine_motion_monitor()

    async def claw_upper(self):
        await self.set_value(self.node_claw_open, False)
        await asyncio.sleep(1)
        await self.set_value(self.node_claw_lower, False)
        await self.set_value(self.node_claw_upper, True)
        await asyncio.sleep(1)

    async def claw_lower(self):
        await self.set_value(self.node_claw_open, True)
        await asyncio.sleep(1)
        await self.set_value(self.node_claw_upper, False)
        await self.set_value(self.node_claw_lower, True)
        await asyncio.sleep(1)


async def main(args):
    mag_front_service = Output(args.url)
    await mag_front_service.init()
    await mag_front_service.run()


if __name__ == '__main__':
    parser = ArgumentParser(description="The client service to connect and control PLC Output")
    parser.add_argument("--url", type=str, default="opc.tcp://172.21.10.1:4840", help="The OPC UA server URL")

    args = parser.parse_args()

    asyncio.run(main(args))
