#!/usr/bin/env python3
"""
Testa cada saída digital que pode controlar a garra.
Execute:
  python3 cp_406/gripper_test.py --ip 192.168.1.100
"""

import time
import argparse
import rtde_receive
import rtde_io as rtde_io_mod

ROBOT_IP = "192.168.1.100"

TESTS = [
    ("DO2",  "setStandardDigitalOut",  2),
    ("DO3",  "setStandardDigitalOut",  3),
    ("TDO0", "setToolDigitalOut",      0),
    ("TDO1", "setToolDigitalOut",      1),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", default=ROBOT_IP)
    args = parser.parse_args()

    print(f"Conectando em {args.ip} ...")
    rtde_r   = rtde_receive.RTDEReceiveInterface(args.ip)
    rtde_io_ = rtde_io_mod.RTDEIOInterface(args.ip)
    print("Conectado.\n")

    for name, method, pin in TESTS:
        fn = getattr(rtde_io_, method)

        input(f"  [{name}] Pressione ENTER para ativar → ")
        fn(pin, True)
        time.sleep(1.5)

        input(f"  [{name}] Pressione ENTER para desativar → ")
        fn(pin, False)
        time.sleep(0.5)

        resp = input(f"  [{name}] A garra se moveu? (s/n) → ").strip().lower()
        if resp == "s":
            print(f"\n  Garra controlada por: {name}  (método: {method}, pin: {pin})\n")
            rtde_r.disconnect()
            return

    print("\n  Nenhuma saída testada moveu a garra.")
    print("  Possível: Robotiq via Modbus ou URCap — informe o modelo da garra.")
    rtde_r.disconnect()


if __name__ == "__main__":
    main()
