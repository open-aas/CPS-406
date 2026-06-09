#!/usr/bin/env python3
"""
Controle interativo do UR5e pelo terminal com suporte a I/O e sincronização com AAS.
Execute a partir da raiz do repositório:
  python3 aas/cp_406/ur5e_control.py
"""

import json
import math
import os
import rtde_control
import rtde_receive
import rtde_io as rtde_io_mod

ROBOT_IP = "192.168.1.100"
AAS_FILE = os.path.join(os.path.dirname(__file__), "station_cobot.json")

DEFAULT_SPEED       = 0.05
DEFAULT_ACCEL       = 0.3
DEFAULT_JOINT_SPEED = 0.3
DEFAULT_JOINT_ACCEL = 0.5

HELP = """
╔════════════════════════════════════════════════════════════════╗
║               Controle Interativo UR5e                         ║
╠══════════════════════╦═════════════════════════════════════════╣
║  MOVIMENTO           ║  I/O                                    ║
║  pos                 ║  io          → estado de todos os I/Os  ║
║  home                ║  dout N 0|1  → saída digital (0-7)      ║
║  movej J1..J6 (graus)║  aout N V    → saída analógica 0-10V    ║
║  movel X Y Z [Rx..Rz]║  tdout N 0|1 → tool digital out (0-1)  ║
║  stop                ║  sync        → salvar estado no AAS     ║
║  speed V             ║                                         ║
║  freedrive / endfree ║  help / quit                            ║
╚══════════════════════╩═════════════════════════════════════════╝
Exemplos:
  movej 0 -90 0 -90 0 0      home canônico
  movel 0.3 -0.2 0.4         mover TCP (mantém orientação)
  dout 2 1                   ativar DO2 (GripperOpen)
  dout 3 1                   ativar DO3 (GripperClose)
  aout 0 5.0                 saída analógica 0 = 5V
  sync                       atualizar station_cobot.json
"""

def deg2rad(d): return d * math.pi / 180
def rad2deg(r): return r * 180 / math.pi


def read_io(rtde_r):
    di_bits = rtde_r.getActualDigitalInputBits()
    do_bits = rtde_r.getActualDigitalOutputBits()
    return {
        "di": di_bits & 0xFF,
        "do": do_bits & 0xFF,
        "tdi": (di_bits >> 16) & 0x3,
        "tdo": (do_bits >> 16) & 0x3,
        "ai0": rtde_r.getStandardAnalogInput0(),
        "ai1": rtde_r.getStandardAnalogInput1(),
        "ao0": rtde_r.getStandardAnalogOutput0(),
        "ao1": rtde_r.getStandardAnalogOutput1(),
        "force": rtde_r.getActualTCPForce(),
    }


def print_io(rtde_r):
    d = read_io(rtde_r)
    di, do_ = d["di"], d["do"]

    DI_LABELS = ["EmergencyStop", "SafeguardStop", "ProgramStart", "ProgramPause",
                 "PalletPresent", "GripperFeedback", "ConveyorReady", "UserDefined"]
    DO_LABELS = ["RobotReady", "CycleComplete", "GripperOpen", "GripperClose",
                 "ReleasePallet", "FaultSignal", "UserDefined6", "UserDefined7"]

    print("\n  ── Entradas Digitais (Controller) ───────────────")
    for i, lbl in enumerate(DI_LABELS):
        print(f"    DI{i} {lbl:<20} {'ON ' if (di>>i)&1 else 'off'}")

    print("\n  ── Saídas Digitais (Controller) ─────────────────")
    for i, lbl in enumerate(DO_LABELS):
        print(f"    DO{i} {lbl:<20} {'ON ' if (do_>>i)&1 else 'off'}")

    print(f"\n  ── Analógico ─────────────────────────────────────")
    print(f"    AI0={d['ai0']:.4f} V   AI1={d['ai1']:.4f} V")
    print(f"    AO0={d['ao0']:.4f} V   AO1={d['ao1']:.4f} V")

    tdi, tdo = d["tdi"], d["tdo"]
    print(f"\n  ── Tool I/O ──────────────────────────────────────")
    print(f"    TDI0(GripperStatus)={'ON' if tdi&1 else 'off'}  "
          f"TDI1={'ON' if (tdi>>1)&1 else 'off'}")
    print(f"    TDO0(GripperCtrl)={'ON' if tdo&1 else 'off'}   "
          f"TDO1={'ON' if (tdo>>1)&1 else 'off'}")

    f = d["force"]
    f_n = math.sqrt(sum(v**2 for v in f[:3]))
    print(f"\n  ── TCP Force: {f_n:.2f} N  "
          f"[Fx={f[0]:.2f} Fy={f[1]:.2f} Fz={f[2]:.2f}]\n")


def sync_aas(rtde_r):
    d = read_io(rtde_r)
    di, do_ = d["di"], d["do"]
    tdi, tdo = d["tdi"], d["tdo"]
    f_n = math.sqrt(sum(v**2 for v in d["force"][:3]))

    with open(AAS_FILE) as f:
        data = json.load(f)

    def set_prop(elements, idshort, value):
        for el in elements:
            if el.get("idShort") == idshort:
                if isinstance(value, bool):
                    el["value"] = str(value).lower()
                else:
                    el["value"] = str(round(value, 4)) if isinstance(value, float) else str(value)
                return True
            if isinstance(el.get("value"), list):
                if set_prop(el["value"], idshort, value):
                    return True
        return False

    for sm in data.get("submodels", []):
        if sm.get("idShort") != "IOInterface":
            continue
        els = sm["submodelElements"]

        di_ids = ["DI0_EmergencyStop", "DI1_SafeguardStop", "DI2_ProgramStart",
                  "DI3_ProgramPause",  "DI4_PalletPresent", "DI5_GripperFeedback",
                  "DI6_ConveyorReady", "DI7_UserDefined"]
        for i, idshort in enumerate(di_ids):
            set_prop(els, idshort, bool((di >> i) & 1))

        do_ids = ["DO0_RobotReady", "DO1_CycleComplete", "DO2_GripperOpen",
                  "DO3_GripperClose", "DO4_ReleasePallet", "DO5_FaultSignal",
                  "DO6_UserDefined",  "DO7_UserDefined"]
        for i, idshort in enumerate(do_ids):
            set_prop(els, idshort, bool((do_ >> i) & 1))

        set_prop(els, "AI0_UserDefined", d["ai0"])
        set_prop(els, "AI1_UserDefined", d["ai1"])
        set_prop(els, "AO0_UserDefined", d["ao0"])
        set_prop(els, "AO1_UserDefined", d["ao1"])
        set_prop(els, "TDI0_GripperStatus", bool(tdi & 1))
        set_prop(els, "TDI1_UserDefined",   bool((tdi >> 1) & 1))
        set_prop(els, "TDO0_GripperControl", bool(tdo & 1))
        set_prop(els, "TDO1_UserDefined",    bool((tdo >> 1) & 1))
        set_prop(els, "TCPForce_N", f_n)

    with open(AAS_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"  AAS sincronizado → {os.path.basename(AAS_FILE)}")
    print(f"  DI=0b{di:08b}  DO=0b{do_:08b}  Force={f_n:.2f}N")


def print_pos(rtde_r):
    pose   = rtde_r.getActualTCPPose()
    joints = rtde_r.getActualQ()
    print(f"\n  TCP:    X={pose[0]:.4f}  Y={pose[1]:.4f}  Z={pose[2]:.4f}"
          f"  Rx={pose[3]:.4f}  Ry={pose[4]:.4f}  Rz={pose[5]:.4f}")
    print(f"  Joints: " + "  ".join(f"J{i+1}={rad2deg(j):.1f}°" for i, j in enumerate(joints)))
    print()


def main():
    print(f"Conectando ao UR5e em {ROBOT_IP} ...")
    try:
        rtde_c   = rtde_control.RTDEControlInterface(ROBOT_IP)
        rtde_r   = rtde_receive.RTDEReceiveInterface(ROBOT_IP)
        rtde_io_ = rtde_io_mod.RTDEIOInterface(ROBOT_IP)
    except Exception as e:
        print(f"Erro: {e}")
        return

    print("Conectado!\n")
    print(HELP)

    speed = DEFAULT_SPEED
    accel = DEFAULT_ACCEL

    while True:
        try:
            line = input("ur5e> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSaindo...")
            break

        if not line:
            continue

        parts = line.split()
        cmd   = parts[0].lower()

        try:
            if cmd in ("quit", "exit", "q"):
                print("Saindo...")
                break

            elif cmd == "help":
                print(HELP)

            elif cmd == "pos":
                print_pos(rtde_r)

            elif cmd == "io":
                print_io(rtde_r)

            elif cmd == "dout":
                if len(parts) < 3:
                    print("  Uso: dout N 0|1  (N=0-7)")
                else:
                    n, v = int(parts[1]), bool(int(parts[2]))
                    rtde_io_.setStandardDigitalOut(n, v)
                    print(f"  DO{n} → {'ON' if v else 'off'}")

            elif cmd == "aout":
                if len(parts) < 3:
                    print("  Uso: aout N V  (N=0-1, V em volts 0.0-10.0)")
                else:
                    n, v = int(parts[1]), float(parts[2])
                    rtde_io_.setAnalogOutputVoltage(n, v)
                    print(f"  AO{n} → {v:.2f} V")

            elif cmd == "tdout":
                if len(parts) < 3:
                    print("  Uso: tdout N 0|1  (N=0-1)")
                else:
                    n, v = int(parts[1]), bool(int(parts[2]))
                    rtde_io_.setToolDigitalOut(n, v)
                    print(f"  TDO{n} → {'ON' if v else 'off'}")

            elif cmd == "sync":
                sync_aas(rtde_r)

            elif cmd == "stop":
                rtde_c.stopL(2.0)
                print("  Parado.")

            elif cmd == "speed":
                if len(parts) < 2:
                    print(f"  Velocidade atual: {speed} m/s")
                else:
                    speed = float(parts[1])
                    print(f"  Velocidade: {speed} m/s")

            elif cmd == "freedrive":
                rtde_c.teachMode()
                print("  Modo guiado ATIVO. Digite 'endfree' para sair.")

            elif cmd == "endfree":
                rtde_c.endTeachMode()
                print("  Modo guiado DESATIVADO.")

            elif cmd == "home":
                joints_rad = [deg2rad(j) for j in [0, -90, 0, -90, 0, 0]]
                print("  Movendo para HOME...")
                rtde_c.moveJ(joints_rad, DEFAULT_JOINT_SPEED, DEFAULT_JOINT_ACCEL)
                print("  Chegou.")
                print_pos(rtde_r)

            elif cmd == "movej":
                if len(parts) < 7:
                    print("  Uso: movej J1 J2 J3 J4 J5 J6  (graus)")
                    continue
                joints_rad = [deg2rad(float(p)) for p in parts[1:7]]
                print(f"  movej {parts[1:7]} ...")
                rtde_c.moveJ(joints_rad, DEFAULT_JOINT_SPEED, DEFAULT_JOINT_ACCEL)
                print("  Chegou.")
                print_pos(rtde_r)

            elif cmd == "movel":
                if len(parts) < 4:
                    print("  Uso: movel X Y Z [Rx Ry Rz]  (metros/rad)")
                    continue
                cur = rtde_r.getActualTCPPose()
                x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                rx, ry, rz = (float(parts[4]), float(parts[5]), float(parts[6])) \
                              if len(parts) >= 7 else (cur[3], cur[4], cur[5])
                print(f"  movel [{x:.3f}, {y:.3f}, {z:.3f}] ...")
                rtde_c.moveL([x, y, z, rx, ry, rz], speed, accel)
                print("  Chegou.")
                print_pos(rtde_r)

            else:
                print(f"  Desconhecido: '{cmd}'. Digite 'help'.")

        except Exception as e:
            print(f"  Erro: {e}")

    rtde_c.disconnect()
    rtde_r.disconnect()
    print("Desconectado.")


if __name__ == "__main__":
    main()
