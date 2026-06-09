#!/usr/bin/env python3
"""
Rotina de dança para o cobot UR5e.
Execute a partir da raiz do repositório:
  python3 aas/cp_406/cobot_dance.py [--ip IP] [--loops N]
"""

import math
import argparse
import rtde_control
import rtde_receive
import rtde_io as rtde_io_mod

ROBOT_IP = "192.168.1.100"

def d2r(*angles):
    return [a * math.pi / 180 for a in angles]


# Poses em graus: [J1, J2, J3, J4, J5, J6]
WAYPOINTS = {
    "home":        d2r(  0,  -90,    0,  -90,   0,   0),
    "arms_up":     d2r(  0, -130,  -20,  -30,   0,   0),
    "lean_right":  d2r( 45,  -90,    0,  -90,   0,   0),
    "lean_left":   d2r(-45,  -90,    0,  -90,   0,   0),
    "wave_a":      d2r(  0,  -90,   90,  -90,  90,   0),
    "wave_b":      d2r(  0,  -90,   90,  -90, -90,   0),
    "spin_left":   d2r(  0,  -90,    0,  -90,   0, 180),
    "spin_right":  d2r(  0,  -90,    0,  -90,   0,-180),
    "tilt_left":   d2r(  0,  -90,    0,  -90,  45,   0),
    "tilt_right":  d2r(  0,  -90,    0,  -90, -45,   0),
    "bow_down":    d2r(  0,  -60,   60,  -90,   0,   0),
}

# (pose, velocidade_rad_s, aceleração_rad_s2)
DANCE_SEQUENCE = [
    ("home",       0.5, 0.8),

    # saudação
    ("arms_up",    0.6, 0.8),
    ("home",       0.6, 0.8),
    ("arms_up",    1.0, 1.2),
    ("home",       1.0, 1.2),

    # balança esquerda/direita
    ("lean_right", 0.7, 1.0),
    ("lean_left",  0.7, 1.0),
    ("lean_right", 1.2, 1.5),
    ("lean_left",  1.2, 1.5),
    ("home",       0.5, 0.8),

    # acena (abre/fecha garra nos waypoints wave_*)
    ("wave_a",     0.8, 1.0),
    ("wave_b",     0.8, 1.0),
    ("wave_a",     1.2, 1.5),
    ("wave_b",     1.2, 1.5),
    ("wave_a",     1.5, 2.0),
    ("wave_b",     1.5, 2.0),
    ("home",       0.5, 0.8),

    # gira pulso
    ("spin_left",  1.0, 1.2),
    ("spin_right", 1.0, 1.2),
    ("spin_left",  1.5, 2.0),
    ("spin_right", 1.5, 2.0),
    ("home",       0.5, 0.8),

    # inclina
    ("tilt_left",  0.8, 1.0),
    ("tilt_right", 0.8, 1.0),
    ("tilt_left",  1.2, 1.5),
    ("tilt_right", 1.2, 1.5),
    ("home",       0.5, 0.8),

    # reverência final
    ("bow_down",   0.4, 0.6),
    ("home",       0.4, 0.6),
]


def dance(rtde_c, rtde_io_, loops):
    for loop in range(loops):
        print(f"\n  ♪ Loop {loop + 1}/{loops}")
        for name, speed, accel in DANCE_SEQUENCE:
            print(f"    → {name:<12}  vel={speed:.1f} rad/s")
            rtde_c.moveJ(WAYPOINTS[name], speed, accel)

            if rtde_io_ is None:
                continue

            # sincroniza garra com o aceno
            if name == "wave_a":
                rtde_io_.setStandardDigitalOut(2, True)   # GripperOpen
                rtde_io_.setStandardDigitalOut(3, False)
            elif name == "wave_b":
                rtde_io_.setStandardDigitalOut(2, False)
                rtde_io_.setStandardDigitalOut(3, True)   # GripperClose
            elif name == "home":
                rtde_io_.setStandardDigitalOut(2, False)
                rtde_io_.setStandardDigitalOut(3, False)

    print("\n  ♪ Dança concluída!")


def main():
    parser = argparse.ArgumentParser(description="Rotina de dança para o UR5e")
    parser.add_argument("--ip",    default=ROBOT_IP, help="IP do robô")
    parser.add_argument("--loops", type=int, default=1, help="Número de repetições")
    parser.add_argument("--no-io", action="store_true", help="Desativa controle da garra")
    args = parser.parse_args()

    print(f"Conectando ao UR5e em {args.ip} ...")
    try:
        rtde_c   = rtde_control.RTDEControlInterface(args.ip)
        rtde_r   = rtde_receive.RTDEReceiveInterface(args.ip)
        rtde_io_ = None if args.no_io else rtde_io_mod.RTDEIOInterface(args.ip)
    except Exception as e:
        print(f"Erro ao conectar: {e}")
        return

    print("Conectado! Iniciando dança...\n")

    try:
        dance(rtde_c, rtde_io_, loops=args.loops)
    except KeyboardInterrupt:
        print("\n  Interrompido.")
        rtde_c.stopJ(2.0)
    except Exception as e:
        print(f"  Erro: {e}")
        rtde_c.stopJ(2.0)
    finally:
        rtde_c.disconnect()
        rtde_r.disconnect()
        print("Desconectado.")


if __name__ == "__main__":
    main()
