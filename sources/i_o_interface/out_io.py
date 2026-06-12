"""IOInterface — Estação 6: OUT (Saída com braço gantry + CMMS-ST).

Todos os sinais passam pelo plcout (172.21.10.1):
  - Esteira/stopper : xQA1_A1, xMB1, xBG1
  - Z-axis          : xGM_MB1 (subir), xGM_MB2 (descer)
  - Garra           : xGM_MB3 (enable), xGM_MB4 (True = abrir)
  - Eixo X / CMMS-ST: xKF1_DI10 (enable), xKF1_DI1/DI2 (posição), xKF1_DI6 (start)
  - Feedback motor  : xKF1_DO0 (1=parado/0=em movimento), xKF1_DO9 (reference), xKF1_DO10 (ready)
  - Sensores braço  : xGM_BG1 (Z topo), xGM_BG2 (Z baixo), xGM_BG3 (garra fechada)
  - Sensores slides : xGM_BG4 (slide esq.), xGM_BG5 (slide dir.)

Posições do eixo X:
  - Position.HOME   (0): DI1=0, DI2=0
  - Position.LEFT   (1): DI1=1, DI2=0
  - Position.RIGHT  (2): DI1=0, DI2=1
  - Position.CENTER (3): DI1=1, DI2=1  ← posição de coleta (acima da esteira)
"""

from typing import Dict, Optional
from aiofase.microservice import MicroService
from faaster.extensions.context import SubmodelContext
from faaster.log import get_logger
from .plc_base import PLCIOBase
from .models import Order
from .edge_detector import EdgeDetector, SensorEventHandler, EdgeType
from enum import IntEnum

import asyncio
import os


logger = get_logger(__name__)

_PLC_DEVICE = ["2:DeviceSet", "3:plcOut"]

_INPUTS: Dict[str, Optional[str]] = {
    "3:xBG1":     "Conveyor/Sensors/BG1_CarrierPresence/Value",
    "3:xGM_BG1":  "Module/Sensors/B3_ArmUp/Value",
    "3:xGM_BG2":  "Module/Sensors/B4_ArmDown/Value",
    "3:xGM_BG3":  "Module/Sensors/B2_GripperClosed/Value",
    "3:xGM_BG4":  None,   # slide 1 (esquerdo) ocupado
    "3:xGM_BG5":  None,   # slide 2 (direito) ocupado
    "3:xKF1_DO0":  None,  # motion complete (1=parado, 0=em movimento)
    "3:xKF1_DO9":  None,  # motor reference
    "3:xKF1_DO10": None,  # motor ready
}

_OUTPUTS: Dict[str, Optional[str]] = {
    "3:xQA1_A1":   "Conveyor/Actuators/MB20_BeltMotor/Value",
    "3:xMB1":      "Conveyor/Actuators/Y1_StopperCylinder/Value",
    "3:xGM_MB1":   "Module/Actuators/Y2_ArmVertical/Value",    # True = subir Z
    "3:xGM_MB2":   None,                                        # True = descer Z
    "3:xGM_MB3":   "Module/Actuators/Y1_Gripper/Value",        # claw enable
    "3:xGM_MB4":   None,                                        # True = abrir garra
    "3:xKF1_DI10": None,                                        # controller enable
    "3:xKF1_DI1":  "Module/Actuators/Y4_SlideSelector/Value",  # select bit 0
    "3:xKF1_DI2":  None,                                        # select bit 1
    "3:xKF1_DI6":  None,                                        # start movement
}


class Position(IntEnum):
    HOME   = 0  # DI1=0, DI2=0
    LEFT   = 1  # DI1=1, DI2=0
    RIGHT  = 2  # DI1=0, DI2=1
    CENTER = 3  # DI1=1, DI2=1 — posição de coleta (acima da esteira)


class _OutService(MicroService):
    def __init__(self, ext: "OutIOInterface") -> None:
        sender   = os.environ.get("AIOFASE_SENDER",   "tcp://0.0.0.0:3000")
        receiver = os.environ.get("AIOFASE_RECEIVER", "tcp://0.0.0.0:4000")
        super().__init__(self, sender, receiver)
        self._ext = ext
        self.queue_order: asyncio.Queue = asyncio.Queue(maxsize=1)

    @MicroService.action
    async def out_push_order(self, service, data: dict) -> None:
       await self.queue_order.put(Order(**data["order"]))

    @MicroService.action
    async def out_update_magfront_state(self, service, data: dict) -> None:
        """Chamado pela MagFront quando um carrier chega ou sai do seu sensor."""
        if data["has_carrier"]:
            self._ext._magfront_clear.clear()
        else:
            self._ext._magfront_clear.set()

    @MicroService.task
    async def task_process_orders(self) -> None:
        logger.info("out.orders.loop.start")
        while True:
            order = await self.queue_order.get()
            logger.info("out.order.start", order_id=order.order_id)
            await self._ext._cycle(order, self)
            logger.info("out.order.done", order_id=order.order_id)


class OutIOInterface(PLCIOBase):
    _PLC_URL_DEFAULT = "opc.tcp://172.21.10.1:4840"
    _PLC_DEVICE      = _PLC_DEVICE
    _INPUTS          = _INPUTS
    _OUTPUTS         = _OUTPUTS

    def __init__(self, context: SubmodelContext) -> None:
        super().__init__(context)
        self._carrier_det:         Optional[EdgeDetector] = None
        self._z_top_det:           Optional[EdgeDetector] = None
        self._z_bottom_det:        Optional[EdgeDetector] = None
        self._grip_det:            Optional[EdgeDetector] = None
        self._engine_ismoving_det: Optional[EdgeDetector] = None
        self._engine_ready_det:    Optional[EdgeDetector] = None
        self._magfront_clear: asyncio.Event = asyncio.Event()
        self._magfront_clear.set()  # começa livre — primeira peça pode fluir
        self._service = _OutService(self)

    # ── PLCIOBase hooks ────────────────────────────────────────────────────────

    async def _on_connected(self) -> None:
        carrier_node  = self._inputs["3:xBG1"]
        z_top_node    = self._inputs["3:xGM_BG1"]
        z_bottom_node = self._inputs["3:xGM_BG2"]
        grip_node     = self._inputs["3:xGM_BG3"]
        ismoving_node = self._inputs["3:xKF1_DO0"]
        ready_node    = self._inputs["3:xKF1_DO10"]

        self._carrier_det         = EdgeDetector(carrier_node.nodeid,  EdgeType.RISING, enable=True)
        self._z_top_det           = EdgeDetector(z_top_node.nodeid,    EdgeType.RISING, enable=False)
        self._z_bottom_det        = EdgeDetector(z_bottom_node.nodeid, EdgeType.RISING, enable=False)
        self._grip_det            = EdgeDetector(grip_node.nodeid,     EdgeType.RISING, enable=False)
        self._engine_ismoving_det = EdgeDetector(ismoving_node.nodeid, EdgeType.RISING, enable=False)
        self._engine_ready_det    = EdgeDetector(ready_node.nodeid,    EdgeType.RISING)

        handler = SensorEventHandler(self._carrier_det)
        handler.add_detect([
            self._z_top_det, self._z_bottom_det, self._grip_det, self._engine_ismoving_det, self._engine_ready_det,
        ])
        sub = await self._plc.create_subscription(10, handler)
        await sub.subscribe_data_change([
            carrier_node, z_top_node, z_bottom_node, grip_node,
            ismoving_node, ready_node,
        ])

        await self._write_raw("3:xQA1_A1",   True)
        await self._write_raw("3:xMB1",      False)
        await self._write_raw("3:xGM_MB3",   True)      # habilitar atuador da garra
        await self._write_raw("3:xGM_MB4",   True)      # garra aberta
        await self._write_raw("3:xGM_MB1",   True)      # Z subir
        await self._write_raw("3:xGM_MB2",   False)
        await self._write_raw("3:xKF1_DI10", True)      # controller enable
        await asyncio.sleep(0.5)
        await self._arm_home()
        await self._arm_move(Position.CENTER)
        self._service.request_action("mpress_downstream_ready", {})

    async def _start_service(self) -> None:
        self._tasks.append(asyncio.create_task(self._service.run()))
        logger.info("out.io_interface.ready", plc=self._plc_url, connected=self._connected)

    # ── Motor helpers ──────────────────────────────────────────────────────────

    async def _engine_ready(self) -> None:
        while True:
            reference = await self._inputs["3:xKF1_DO9"].get_value()
            ready     = await self._inputs["3:xKF1_DO10"].get_value()
            ismoving  = await self._inputs["3:xKF1_DO0"].get_value()

            if reference and ready and ismoving:
                logger.debug("out.engine.ready")
                break

            logger.debug("out.engine.waiting", reference=reference, ready=ready, ismoving=ismoving)
            await asyncio.sleep(0.1)

        await asyncio.sleep(1)

    async def _engine_motion_monitor(self) -> None:
        while True:
            await self._write_raw("3:xKF1_DI6", True)
            await asyncio.sleep(0.1)
            await self._write_raw("3:xKF1_DI6", False)
            ismoving = await self._inputs["3:xKF1_DO0"].get_value()
            if ismoving == 0:
                logger.debug("out.engine.moving")
                break
            await asyncio.sleep(0.05)

        logger.debug("out.engine.waiting_stop")
        await self._engine_ismoving_det.wait()
        self._engine_ismoving_det.set_enable(False)
        logger.debug("out.engine.stopped")

    # ── Helpers de movimento ───────────────────────────────────────────────────

    async def _arm_home(self) -> None:
        logger.debug("out.arm.home.start")
        self._engine_ismoving_det.set_enable(True)
        await self._engine_ready()
        await self._write_raw("3:xKF1_DI1", False)   # CENTER = DI1=1, DI2=1
        await self._write_raw("3:xKF1_DI2", False)
        await self._engine_motion_monitor()
        logger.debug("out.arm.home.done")

    async def _arm_move(self, pos: int) -> None:
        self._engine_ismoving_det.set_enable(True)
        di1 = pos in (Position.LEFT, Position.CENTER)
        di2 = pos in (Position.RIGHT, Position.CENTER)
        logger.debug("out.arm.move.start", pos=pos, di1=di1, di2=di2)
        await self._engine_ready()
        await self._write_raw("3:xKF1_DI1", di1)
        await self._write_raw("3:xKF1_DI2", di2)
        await self._engine_motion_monitor()
        logger.debug("out.arm.move.done", pos=pos)

    async def _z_down(self) -> None:
        logger.debug("out.z.down.start")
        self._z_bottom_det.set_enable(True)
        await self._write("3:xGM_MB1", False)
        await self._write("3:xGM_MB2", True)
        await asyncio.sleep(0.5)
        print("esperando chegar no z bottom....")
        await self._z_bottom_det.wait()
        # self._z_bottom_det.set_enable(False)
        logger.debug("out.z.down.done")

    async def _z_up(self) -> None:
        logger.debug("out.z.up.start")
        self._z_top_det.set_enable(True)
        await self._write("3:xGM_MB1", True)
        await self._write("3:xGM_MB2", False)
        await asyncio.sleep(0.5)
        print("esperando chegar no z top....")
        await self._z_top_det.wait()
        # self._z_top_det.set_enable(False)
        logger.debug("out.z.up.done")

    async def _gripper_close(self) -> None:
        logger.debug("out.gripper.close.start")
        # self._grip_det.set_trigger(EdgeType.FALLING)
        # self._grip_det.set_enable(True)
        await self._write("3:xGM_MB4", False)
        # await self._grip_det.wait()
        # self._grip_det.set_enable(False)
        await asyncio.sleep(0.5)
        logger.debug("out.gripper.close.done")

    async def _gripper_open(self) -> None:
        logger.debug("out.gripper.open")
        await self._write("3:xGM_MB4", True)
        await asyncio.sleep(0.5)

    async def _wait_slide_empty(self) -> Position:
        slide_left_node  = self._inputs["3:xGM_BG4"]
        slide_right_node = self._inputs["3:xGM_BG5"]

        logger.info("out.waiting_slide_empty")

        while True:
            left_occupied  = await slide_left_node.get_value()
            right_occupied = await slide_right_node.get_value()

            if not left_occupied:
                logger.warning("out.slide.left_free", slide=Position.LEFT)
                return Position.LEFT
            
            if not right_occupied:
                logger.warning("out.slide.right_free", slide=Position.RIGHT)
                return Position.RIGHT

            await asyncio.sleep(0.3)

    async def _check_empty_slide(self) -> int:
        # TODO: mapear nodes dos sensores de ocupação dos slides
        slide_left_node  = self._inputs["3:xGM_BG4"]
        slide_right_node = self._inputs["3:xGM_BG5"]
        
        left_occupied  = await slide_left_node.get_value()
        right_occupied = await slide_right_node.get_value()
        
        if not left_occupied:
            return Position.LEFT
        
        if not right_occupied:
            return Position.RIGHT
        
        logger.warning("out.slides.both_occupied")
        return await self._wait_slide_empty()

    # ── Ciclo de deposição ─────────────────────────────────────────────────────

    async def _cycle(self, order: Order, service: _OutService) -> None:
        # Verifica slot ANTES de baixar o stopper. Se ambos os slides estiverem
        # cheios, Out bloqueia aqui enquanto o carrier vindo da MPress fica retido
        # fisicamente no stopper — esse é o "slot virtual na garra".
        await self._write("3:xMB1", False)  # baixa stopper para receber carrier
        det = self._carrier_det

        await det.wait()
        service.request_action("manager_update_has_product", {"has_product": True})

        await self._write("3:xQA1_A1", False)
        await asyncio.sleep(0.5)
        det.set_enable(False)

        # home → abre garra → desce → fecha (pega peça) → sobe
        # await self._arm_move(Position.CENTER)
        await self._gripper_open()
        await self._z_down()
        await self._gripper_close()
        await self._z_up()

        # deposita no slot verificado no início do ciclo
        target = await self._check_empty_slide()
        logger.info("out.arm.move_to_slide", slide=target)
        await self._write_raw("3:xKF1_DI10", True)
        await self._wait_output_state("3:xKF1_DI10", True)
        await self._arm_move(target)
        await self._gripper_open()
        await asyncio.sleep(1.0)   # aguarda peça cair no slide

        # fecha garra (vazia) e move para direita para reiniciar ciclo
        await self._gripper_close()
        await self._arm_move(Position.CENTER)
        # await self._arm_move(Position.RIGHT)

        # libera carrier e reinicia esteira
        det.set_trigger(EdgeType.FALLING)
        await self._write("3:xQA1_A1", True)
        await self._wait_output_state("3:xQA1_A1", True)
        await asyncio.sleep(0.5)
        await self._write("3:xMB1",    True)
        await self._wait_output_state("3:xMB1", True)

        det.set_enable(True)
        await det.wait()

        await self._write("3:xMB1",    False)
        await self._wait_output_state("3:xMB1", False)

        det.set_trigger(EdgeType.RISING)
        await asyncio.sleep(1)

        service.request_action("manager_update_has_product", {"has_product": False})
        logger.info("out.order.finished", order_id=order.order_id, slide=int(target))
        await asyncio.sleep(0.5)

        # Sinaliza MPress logo após o carrier sair — sem aguardar verificação de slot.
        # O próximo carrier ficará retido no stopper de Out enquanto _check_empty_slide()
        # (início do próximo ciclo) estiver bloqueado, garantindo o slot virtual.
        # Aguarda MagFront confirmar que não tem base retida antes de liberar MPress.
        await self._magfront_clear.wait()
        service.request_action("mpress_downstream_ready", {})

    async def _wait_output_state(self, node_name: str, expected_value: bool) -> None:
        node = self._outputs[node_name]
        print(f"Esperando {node_name} ser {expected_value}...")

        while True:
            try:
                value = await node.get_value()
            
                if value == expected_value:
                    break
                
                await self._write(node_name, expected_value)

            except Exception as e:
                logger.error("out.wait_output_state.error", node=node_name, error=str(e))

            finally:
                await asyncio.sleep(0.3)
