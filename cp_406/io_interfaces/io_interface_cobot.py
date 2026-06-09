"""
IOInterface extension — COBOT (Estação 7: Universal Robots UR5e)

O UR5e expõe seu próprio servidor OPC UA na porta 4840 com nós
RTDE-mapeados (namespace 2). Esta extensão:

  1. Conecta ao servidor OPC UA do UR5e
  2. Subscreve a scalars (modo, safety, program running, I/O bits)
  3. Poleia o array de força TCP periodicamente
  4. Decodifica bit-fields de DI/DO e espelha cada bit no AAS IOInterface
  5. Emite alertas de segurança quando SafetyMode ≠ NORMAL

Diferenças em relação às estações PLC (1–6):
  • Não há fila de pedidos — o robô opera de forma autônoma via URScript
  • I/Os são bit-fields inteiros, não nós booleanos individuais
  • TCPForce é um array [Fx, Fy, Fz, Tx, Ty, Tz]; a extensão calcula ‖F‖
  • RobotMode e SafetyMode são inteiros convertidos para strings AAS

Nós OPC UA utilizados (CB5, PolyScopeX SW5.x, namespace 2):
  ns=2;s=RTDE.RobotMode
  ns=2;s=RTDE.SafetyMode
  ns=2;s=RTDE.IsProgramRunning
  ns=2;s=RTDE.ActualTCPForce          ← array float[6]
  ns=2;s=RTDE.ActualDigitalInputBits  ← uint64 bit-field
  ns=2;s=RTDE.ActualDigitalOutputBits ← uint64 bit-field
  ns=2;s=RTDE.StandardAnalogInput0/1
  ns=2;s=RTDE.ToolAnalogInput0
  ns=2;s=RTDE.ToolDigitalInputBits    ← uint64 (bits 0-1 = TDI0/TDI1)
  ns=2;s=RTDE.ToolDigitalOutputBits   ← uint64 (bits 0-1 = TDO0/TDO1)

Env vars:
  PLC_URL    opc.tcp://[ur5e-ip]:4840  (default: opc.tcp://172.21.5.1:4840)
  MQTT_HOST  broker MQTT               (default: localhost)
  POLL_HZ    frequência de polling TCP Force em Hz (default: 10)
"""

import asyncio
import math
import os
from typing import Dict, List, Optional, Tuple

from asyncua import Client, Node
import structlog

from faaster.extensions.interfaces import ISubmodelExtension
from faaster.extensions.context import SubmodelContext
from faaster.parser.node_registry import NodeMetadata

logger = structlog.getLogger(__name__)

# ── Constantes da estação ──────────────────────────────────────────────────
_PLC_URL  = "opc.tcp://172.21.5.1:4840"   # UR5e OPC UA server
_POLL_HZ  = 10                             # Hz para polling do TCP force array

# ── Mapeamento RobotMode (int → string AAS) ─────────────────────────────────
_ROBOT_MODE: Dict[int, str] = {
    -1: "NO_CONTROLLER",
     0: "DISCONNECTED",
     1: "CONFIRM_SAFETY",
     2: "BOOTING",
     3: "POWER_OFF",
     4: "POWER_ON",
     5: "IDLE",
     6: "BACKDRIVE",
     7: "RUNNING",
     8: "UPDATING_FIRMWARE",
}

# ── Mapeamento SafetyMode (int → string AAS) ─────────────────────────────────
_SAFETY_MODE: Dict[int, str] = {
    1:  "NORMAL",
    2:  "REDUCED",
    3:  "PROTECTIVE_STOP",
    4:  "RECOVERY",
    5:  "SAFEGUARD_STOP",
    6:  "SYSTEM_EMERGENCY_STOP",
    7:  "ROBOT_EMERGENCY_STOP",
    8:  "VIOLATION",
    9:  "FAULT",
    10: "AUTO_MODE_SAFEGUARD_STOP",
}

# ── Nós OPC UA do UR5e que são scalars (suportam subscription) ──────────────
# "alias": ("ns=2;s=RTDE.NodeName", tipo_python)
_UR_SCALARS: Dict[str, Tuple[str, type]] = {
    "robot_mode":     ("ns=2;s=RTDE.RobotMode",               int),
    "safety_mode":    ("ns=2;s=RTDE.SafetyMode",              int),
    "program_run":    ("ns=2;s=RTDE.IsProgramRunning",        bool),
    "di_bits":        ("ns=2;s=RTDE.ActualDigitalInputBits",  int),
    "do_bits":        ("ns=2;s=RTDE.ActualDigitalOutputBits", int),
    "ai0":            ("ns=2;s=RTDE.StandardAnalogInput0",    float),
    "ai1":            ("ns=2;s=RTDE.StandardAnalogInput1",    float),
    "tdi_bits":       ("ns=2;s=RTDE.ToolDigitalInputBits",    int),
    "tdo_bits":       ("ns=2;s=RTDE.ToolDigitalOutputBits",   int),
    "tai0":           ("ns=2;s=RTDE.ToolAnalogInput0",        float),
}

# Node OPC UA do array de força TCP (polled, não subscribed)
_TCP_FORCE_NODE = "ns=2;s=RTDE.ActualTCPForce"   # float[6]: Fx Fy Fz Tx Ty Tz

# ── Mapa: alias → caminho AAS relativo ao submodelo IOInterface ─────────────
# Bit-fields são expandidos dinamicamente; aqui ficam só os scalars diretos.
_AAS_PATHS: Dict[str, str] = {
    "robot_mode":  "RobotState/RobotMode",
    "safety_mode": "RobotState/SafetyMode",
    "program_run": "RobotState/ProgramRunning",
    "ai0":         "ControllerIO/AnalogInputs/AI0_UserDefined",
    "ai1":         "ControllerIO/AnalogInputs/AI1_UserDefined",
    "tai0":        "ToolIO/TAI0_ForceFeedback",
}

# Mapa bit → AAS path para os DI (ControllerIO)
_DI_AAS: Dict[int, str] = {
    0: "ControllerIO/DigitalInputs/DI0_EmergencyStop",
    1: "ControllerIO/DigitalInputs/DI1_SafeguardStop",
    2: "ControllerIO/DigitalInputs/DI2_ProgramStart",
    3: "ControllerIO/DigitalInputs/DI3_ProgramPause",
    4: "ControllerIO/DigitalInputs/DI4_PalletPresent",
    5: "ControllerIO/DigitalInputs/DI5_GripperFeedback",
    6: "ControllerIO/DigitalInputs/DI6_ConveyorReady",
    7: "ControllerIO/DigitalInputs/DI7_UserDefined",
}

# Mapa bit → AAS path para os DO (ControllerIO)
_DO_AAS: Dict[int, str] = {
    0: "ControllerIO/DigitalOutputs/DO0_RobotReady",
    1: "ControllerIO/DigitalOutputs/DO1_CycleComplete",
    2: "ControllerIO/DigitalOutputs/DO2_UserDefined",
    3: "ControllerIO/DigitalOutputs/DO3_UserDefined",
    4: "ControllerIO/DigitalOutputs/DO4_ReleasePallet",
    5: "ControllerIO/DigitalOutputs/DO5_FaultSignal",
    6: "ControllerIO/DigitalOutputs/DO6_UserDefined",
    7: "ControllerIO/DigitalOutputs/DO7_UserDefined",
}

# Mapa bit → AAS path para os Tool DI/DO
_TDI_AAS: Dict[int, str] = {
    0: "ToolIO/TDI0_GripperStatus",
    1: "ToolIO/TDI1_UserDefined",
}
_TDO_AAS: Dict[int, str] = {
    0: "ToolIO/TDO0_GripperControl",
    1: "ToolIO/TDO1_UserDefined",
}


class _URSyncHandler:
    """
    Subscription handler do asyncua para o servidor OPC UA do UR5e.
    Recebe notificações de mudança de valor e espelha no AAS.
    """

    def __init__(self, ctx: SubmodelContext, nodes: Dict[str, Node]):
        self._ctx   = ctx
        self._nodes = nodes  # alias → asyncua.Node
        # cache do valor anterior de di_bits / do_bits para detectar mudanças de bit
        self._prev: Dict[str, int] = {"di_bits": -1, "do_bits": -1,
                                      "tdi_bits": -1, "tdo_bits": -1}

    async def datachange_notification(self, node: Node, val, data) -> None:
        # identifica qual alias disparou
        nid = str(node.nodeid)
        alias = next((a for a, n in self._nodes.items()
                      if str(n.nodeid) == nid), None)
        if alias is None:
            return

        await self._dispatch(alias, val)

    async def _dispatch(self, alias: str, val) -> None:
        """Roteia o valor bruto para o nó AAS correto."""

        if alias == "robot_mode":
            text = _ROBOT_MODE.get(int(val), f"UNKNOWN({val})")
            await self._set_aas("RobotState/RobotMode", text)
            if int(val) not in (5, 7):   # não é IDLE nem RUNNING
                logger.warning("cobot.robot_mode.abnormal", mode=text)

        elif alias == "safety_mode":
            text = _SAFETY_MODE.get(int(val), f"UNKNOWN({val})")
            await self._set_aas("RobotState/SafetyMode", text)
            if int(val) != 1:            # não é NORMAL
                logger.warning("cobot.safety.alert", mode=text)

        elif alias == "program_run":
            await self._set_aas("RobotState/ProgramRunning", bool(val))

        elif alias in ("ai0", "ai1", "tai0"):
            aas_path = _AAS_PATHS[alias]
            await self._set_aas(aas_path, float(val))

        elif alias == "di_bits":
            await self._mirror_bits(int(val), "di_bits", _DI_AAS)

        elif alias == "do_bits":
            await self._mirror_bits(int(val), "do_bits", _DO_AAS)

        elif alias == "tdi_bits":
            await self._mirror_bits(int(val), "tdi_bits", _TDI_AAS)

        elif alias == "tdo_bits":
            await self._mirror_bits(int(val), "tdo_bits", _TDO_AAS)

    async def _mirror_bits(self, bits: int, key: str,
                           bit_map: Dict[int, str]) -> None:
        """Expande bit-field e escreve cada bit no AAS se mudou."""
        prev = self._prev.get(key, -1)
        if bits == prev:
            return
        self._prev[key] = bits
        changed = bits ^ prev if prev >= 0 else (2 ** len(bit_map)) - 1
        for bit, aas_path in bit_map.items():
            if (changed >> bit) & 1:
                await self._set_aas(aas_path, bool((bits >> bit) & 1))

    async def _set_aas(self, path: str, value) -> None:
        meta = self._ctx.get_node(path)
        if meta is None:
            return
        try:
            await self._ctx.address_space.set_value(meta.node, value)
        except Exception as exc:
            logger.warning("cobot.aas.set_error", path=path, error=str(exc))

    async def event_notification(self, event) -> None:
        pass


class IOInterface(ISubmodelExtension):
    """
    IOInterface — Estação 7 COBOT (Universal Robots UR5e).

    Espelha o estado do robô (modo, safety, I/O, força TCP) nos nós AAS.
    Não implementa fila de pedidos: o UR5e opera via URScript autônomo.
    """

    def __init__(self, context: SubmodelContext) -> None:
        self._ctx      = context
        self._plc_url  = os.environ.get("PLC_URL", _PLC_URL)
        self._poll_hz  = float(os.environ.get("POLL_HZ", str(_POLL_HZ)))

        self._plc: Optional[Client]     = None
        self._tasks: List[asyncio.Task] = []

        # asyncua Node references (alias → Node)
        self._ur_nodes: Dict[str, Node] = {}
        self._tcp_force_node: Optional[Node] = None

    async def init(self) -> None:
        # ── Conecta ao servidor OPC UA do UR5e ───────────────────────────
        self._plc = Client(self._plc_url)
        await self._plc.connect()
        logger.info("cobot.plc.connected", url=self._plc_url)

        # ── Resolve nós RTDE ─────────────────────────────────────────────
        for alias, (node_id_str, _) in _UR_SCALARS.items():
            try:
                self._ur_nodes[alias] = self._plc.get_node(node_id_str)
            except Exception as exc:
                logger.warning("cobot.node.resolve_failed",
                               alias=alias, node=node_id_str, error=str(exc))

        try:
            self._tcp_force_node = self._plc.get_node(_TCP_FORCE_NODE)
        except Exception as exc:
            logger.warning("cobot.tcp_force.resolve_failed", error=str(exc))

        # ── Subscription para scalars ─────────────────────────────────────
        handler = _URSyncHandler(self._ctx, self._ur_nodes)
        sub = await self._plc.create_subscription(100, handler)
        if self._ur_nodes:
            await sub.subscribe_data_change(list(self._ur_nodes.values()))
            logger.info("cobot.subscribed", n_nodes=len(self._ur_nodes))

        # ── Polling para TCP Force (array, não funciona bem em subscription) ─
        self._tasks.append(asyncio.create_task(self._poll_tcp_force()))
        logger.info("cobot.io_interface.ready")

    async def stop(self) -> None:
        for t in self._tasks:
            t.cancel()
        if self._plc:
            await self._plc.disconnect()

    # ── Polling do TCP Force ──────────────────────────────────────────────────

    async def _poll_tcp_force(self) -> None:
        """
        Lê periodicamente o array [Fx, Fy, Fz, Tx, Ty, Tz] e calcula ‖F‖.
        Escreve o valor escalar em RobotState/TCPForce_N.
        """
        interval = 1.0 / self._poll_hz
        tcp_node = self._ctx.get_node("RobotState/TCPForce_N")
        logger.info("cobot.tcp_force.polling.start", hz=self._poll_hz)

        while True:
            try:
                if self._tcp_force_node is not None:
                    force_vec = await self._tcp_force_node.get_value()
                    # force_vec é lista de 6 floats: Fx Fy Fz Tx Ty Tz
                    if force_vec and len(force_vec) >= 3:
                        tcp_force_n = math.sqrt(
                            sum(f ** 2 for f in force_vec[:3])
                        )
                        if tcp_node:
                            await self._ctx.address_space.set_value(
                                tcp_node.node, float(tcp_force_n)
                            )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("cobot.tcp_force.poll_error", error=str(exc))

            await asyncio.sleep(interval)
