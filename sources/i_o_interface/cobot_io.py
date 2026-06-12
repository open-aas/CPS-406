"""IOInterface — Estação COBOT (UR5e + Schunk EGP).

Diferente das estações PLC, o cobot usa dois canais de comunicação:
  - RTDE (172.21.0.210:30004): leitura periódica de juntas, TCP, DI/DO e status
  - Modbus TCP (172.21.0.210:502): controle da garra Schunk EGP (reg 0–3)

Env vars:
  ROBOT_IP          172.21.0.210    (IP do UR5e)
  RTDE_POLL_HZ      10              (frequência de espelhamento para o AAS)
  RECONNECT_DELAY   5               (segundos entre retentativas)
"""

import asyncio
import os
from typing import List, Optional

import rtde_receive
from pymodbus.client import ModbusTcpClient
from asyncua.ua import Variant, VariantType as UA_VT

from aiofase.microservice import MicroService
from faaster.extensions.interfaces import ISubmodelExtension
from faaster.extensions.context import SubmodelContext
from faaster.log import get_logger

logger = get_logger(__name__)

_ROBOT_IP_DEFAULT = "172.21.0.210"
_RTDE_POLL_HZ     = float(os.environ.get("RTDE_POLL_HZ",     "10"))
_RECONNECT_DELAY  = float(os.environ.get("RECONNECT_DELAY",   "5"))

# ── AAS path map (relativo ao submodelo IOInterface, sufixo /Value) ───────────

_Q_PATHS  = [f"Robot/JointState/ActualQ_J{i+1}/Value"  for i in range(6)]
_QD_PATHS = [f"Robot/JointState/ActualQd_J{i+1}/Value" for i in range(6)]

_POSE_KEYS  = ["X", "Y", "Z", "Rx", "Ry", "Rz"]
_POSE_PATHS = [f"Robot/TCPPose/{k}/Value"   for k in _POSE_KEYS]

_FORCE_KEYS  = ["Fx", "Fy", "Fz", "Tx", "Ty", "Tz"]
_FORCE_PATHS = [f"Robot/TCPForce/{k}/Value" for k in _FORCE_KEYS]

_DI_NAMES = [
    "DI0_EmergencyStop", "DI1_SafeguardStop", "DI2_ReducedMode",
    "DI3_OperationalMode", "DI4_UserDefined",  "DI5_UserDefined",
    "DI6_UserDefined",    "DI7_UserDefined",
]
_DO_NAMES = [
    "DO0_RobotReady",   "DO1_ProgramRunning", "DO2_CycleComplete",
    "DO3_FaultSignal",  "DO4_UserDefined",     "DO5_UserDefined",
    "DO6_UserDefined",  "DO7_UserDefined",
]
_DI_PATHS = [f"Robot/DigitalInputs/{n}/Value"  for n in _DI_NAMES]
_DO_PATHS = [f"Robot/DigitalOutputs/{n}/Value" for n in _DO_NAMES]

_STATUS_PATHS = {
    "RobotMode":       "Robot/Status/RobotMode/Value",
    "SafetyMode":      "Robot/Status/SafetyMode/Value",
    "ProgramRunning":  "Robot/Status/ProgramRunning/Value",
    "SpeedScaling":    "Robot/Status/SpeedScaling/Value",
    "RuntimeState":    "Robot/Status/RuntimeState/Value",
}

_GRIPPER_FEEDBACK_PATH = "Gripper/PositionFeedback/Value"
_GRIPPER_TARGET_PATH   = "Gripper/TargetPosition/Value"

# ── Gripper: protocolo Modbus (MOVE_TO_POSITION) ──────────────────────────────

GRIPPER_OPEN_POS  = 400   # reg[2] write — totalmente aberto
GRIPPER_CLOSE_POS = 0     # reg[2] write — totalmente fechado


# ── aiofase MicroService ──────────────────────────────────────────────────────

class _CobotService(MicroService):
    def __init__(self, ext: "CobotIOInterface") -> None:
        sender   = os.environ.get("AIOFASE_SENDER",   "tcp://0.0.0.0:3000")
        receiver = os.environ.get("AIOFASE_RECEIVER", "tcp://0.0.0.0:4000")
        super().__init__(self, sender, receiver)
        self._ext        = ext
        self.queue_order = asyncio.Queue(maxsize=1)

    @MicroService.action
    async def cobot_push_order(self, service, data: dict) -> None:
        """Recebe um pedido para execução pelo cobot."""
        await self.queue_order.put(data)

    @MicroService.action
    async def cobot_gripper_open(self, service, data: dict) -> None:
        """Abre a garra Schunk EGP (MOVE_TO_POSITION 400)."""
        await self._ext._gripper_move(GRIPPER_OPEN_POS)

    @MicroService.action
    async def cobot_gripper_close(self, service, data: dict) -> None:
        """Fecha a garra Schunk EGP (MOVE_TO_POSITION 0)."""
        await self._ext._gripper_move(GRIPPER_CLOSE_POS)

    @MicroService.task
    async def task_process_orders(self) -> None:
        logger.info("cobot.orders.loop.start")
        while True:
            order = await self.queue_order.get()
            logger.info("cobot.order.start", order=order)
            await self._ext._cycle(order, self)
            logger.info("cobot.order.done", order=order)


# ── CobotIOInterface ──────────────────────────────────────────────────────────

class CobotIOInterface(ISubmodelExtension):
    """
    IOInterface do cobot UR5e.

    Conecta via RTDE para leitura de estado e via Modbus TCP para controle
    da garra Schunk EGP. Espelha os dados no AAS a cada 1/RTDE_POLL_HZ segundos.
    """

    def __init__(self, context: SubmodelContext) -> None:
        self._ctx      = context
        self._ip       = os.environ.get("ROBOT_IP", _ROBOT_IP_DEFAULT)
        self._rtde_r:  Optional[rtde_receive.RTDEReceiveInterface] = None
        self._mb:      Optional[ModbusTcpClient]                   = None
        self._connected = False
        self._tasks: List[asyncio.Task] = []
        self._service  = _CobotService(self)

    # ── ISubmodelExtension ────────────────────────────────────────────────────

    async def init(self) -> None:
        try:
            await self._connect()
        except Exception as exc:
            logger.warning("cobot.first_connect_failed",
                           ip=self._ip, error=str(exc),
                           retry_in=_RECONNECT_DELAY)
        self._tasks.append(asyncio.create_task(self._watchdog()))
        self._tasks.append(asyncio.create_task(self._service.run()))
        logger.info("cobot.io_interface.ready",
                    ip=self._ip, connected=self._connected)

    async def stop(self) -> None:
        for t in self._tasks:
            t.cancel()
        loop = asyncio.get_event_loop()
        if self._rtde_r:
            try:
                await loop.run_in_executor(None, self._rtde_r.disconnect)
            except Exception:
                pass
        if self._mb:
            try:
                self._mb.close()
            except Exception:
                pass

    # ── Conexão + watchdog ────────────────────────────────────────────────────

    async def _connect(self) -> None:
        loop = asyncio.get_event_loop()

        if self._rtde_r:
            try:
                await loop.run_in_executor(None, self._rtde_r.disconnect)
            except Exception:
                pass

        if self._mb:
            try:
                self._mb.close()
            except Exception:
                pass

        self._connected = False

        self._rtde_r = await loop.run_in_executor(
            None,
            lambda: rtde_receive.RTDEReceiveInterface(self._ip),
        )

        self._mb = ModbusTcpClient(self._ip, port=502)
        await loop.run_in_executor(None, self._mb.connect)

        self._connected = True
        self._tasks.append(asyncio.create_task(self._poll_loop()))
        logger.info("cobot.connected", ip=self._ip)

    async def _watchdog(self) -> None:
        while True:
            await asyncio.sleep(_RECONNECT_DELAY)
            if not self._connected:
                logger.info("cobot.reconnecting", ip=self._ip)
                try:
                    await self._connect()
                    logger.info("cobot.reconnected", ip=self._ip)
                except Exception as exc:
                    logger.warning("cobot.reconnect_failed",
                                   ip=self._ip, error=str(exc))

    # ── Polling RTDE → AAS ────────────────────────────────────────────────────

    async def _poll_loop(self) -> None:
        interval = 1.0 / _RTDE_POLL_HZ
        loop     = asyncio.get_event_loop()
        while self._connected:
            try:
                await self._mirror_robot(loop)
                await self._mirror_gripper(loop)
            except Exception as exc:
                logger.error("cobot.poll.error", error=str(exc))
                self._connected = False
                return
            await asyncio.sleep(interval)

    async def _mirror_robot(self, loop: asyncio.AbstractEventLoop) -> None:
        r = self._rtde_r

        actual_q   = await loop.run_in_executor(None, r.getActualQ)
        actual_qd  = await loop.run_in_executor(None, r.getActualQd)
        tcp_pose   = await loop.run_in_executor(None, r.getActualTCPPose)
        tcp_force  = await loop.run_in_executor(None, r.getActualTCPForce)
        di_bits    = await loop.run_in_executor(None, r.getActualDigitalInputBits)
        do_bits    = await loop.run_in_executor(None, r.getActualDigitalOutputBits)
        robot_mode = await loop.run_in_executor(None, r.getRobotMode)
        safe_mode  = await loop.run_in_executor(None, r.getSafetyMode)
        runtime    = await loop.run_in_executor(None, r.getRuntimeState)
        prog_run   = (runtime == 2)  # 2 = Playing

        for path, val in zip(_Q_PATHS, actual_q):
            await self._set(path, float(val))
        for path, val in zip(_QD_PATHS, actual_qd):
            await self._set(path, float(val))
        for path, val in zip(_POSE_PATHS, tcp_pose):
            await self._set(path, float(val))
        for path, val in zip(_FORCE_PATHS, tcp_force):
            await self._set(path, float(val))

        for i, path in enumerate(_DI_PATHS):
            await self._set(path, bool((di_bits >> i) & 1))
        for i, path in enumerate(_DO_PATHS):
            await self._set(path, bool((do_bits >> i) & 1))

        await self._set(_STATUS_PATHS["RobotMode"],      int(robot_mode))
        await self._set(_STATUS_PATHS["SafetyMode"],     int(safe_mode))
        await self._set(_STATUS_PATHS["ProgramRunning"], bool(prog_run))
        await self._set(_STATUS_PATHS["RuntimeState"],   int(runtime))

        try:
            speed = await loop.run_in_executor(None, r.getTargetSpeedFraction)
            await self._set(_STATUS_PATHS["SpeedScaling"], float(speed))
        except Exception:
            pass

    async def _mirror_gripper(self, loop: asyncio.AbstractEventLoop) -> None:
        try:
            res = await loop.run_in_executor(
                None, lambda: self._mb.read_holding_registers(1, count=1)
            )
            if not res.isError():
                await self._set(_GRIPPER_FEEDBACK_PATH, int(res.registers[0]))
        except Exception as exc:
            logger.debug("cobot.gripper.read_failed", error=str(exc))

    # ── Gripper write ─────────────────────────────────────────────────────────

    async def _gripper_move(self, pos: int) -> None:
        """MOVE_TO_POSITION: reg[1]=0x0300 + reg[2]=pos."""
        if not self._connected or self._mb is None:
            logger.warning("cobot.gripper.not_connected")
            return
        loop = asyncio.get_event_loop()
        try:
            if not self._mb.is_socket_open():
                await loop.run_in_executor(None, self._mb.connect)
            await loop.run_in_executor(None, lambda: self._mb.write_register(1, 0x0300))
            await loop.run_in_executor(None, lambda: self._mb.write_register(2, pos))
            await self._set(_GRIPPER_TARGET_PATH, pos)
            logger.info("cobot.gripper.move", pos=pos)
        except Exception as exc:
            logger.error("cobot.gripper.write_failed", pos=pos, error=str(exc))

    # ── AAS mirror helper ─────────────────────────────────────────────────────

    async def _set(self, path: str, value) -> None:
        meta = self._ctx.get_node(path)
        if meta:
            try:
                # xs:float AAS properties are OPC UA Float (32-bit, type 10);
                # Python float is Double (64-bit, type 11) — wrap explicitly.
                if isinstance(value, float):
                    value = Variant(value, UA_VT.Float)
                await self._ctx.address_space.set_value(meta.node, value)
            except Exception as exc:
                logger.debug("cobot.aas_mirror.error", path=path, error=str(exc))

    # ── Ciclo de produção ─────────────────────────────────────────────────────

    async def _cycle(self, order: dict, service: _CobotService) -> None:
        """
        Ciclo de produção do cobot. Expandir conforme a integração com
        o teach_mirror.py ou outra rotina programada.
        """
        logger.info("cobot.cycle.start", order=order)
        # placeholder — implementar trajetória e integração com CCInstance
        await asyncio.sleep(0)
        logger.info("cobot.cycle.done", order=order)
