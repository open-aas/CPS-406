#!/usr/bin/env python3
"""Testa qual sinal fecha a garra (assumindo que TDO0=True abre)."""

import time
import argparse
import rtde_io as rtde_io_mod

ROBOT_IP = "192.168.1.100"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", default=ROBOT_IP)
    args = parser.parse_args()

    rtde_io_ = rtde_io_mod.RTDEIOInterface(args.ip)
    print("Conectado.\n")

    print("1. Abrindo garra (TDO0=True)...")
    rtde_io_.setToolDigitalOut(0, True)
    time.sleep(1.5)

    print("\nTestando candidatos para fechar:\n")

    candidates = [
        ("TDO0=False",  lambda: rtde_io_.setToolDigitalOut(0, False)),
        ("TDO1=True",   lambda: rtde_io_.setToolDigitalOut(1, True)),
    ]

    for label, fn in candidates:
        input(f"  [{label}] ENTER para testar → ")
        fn()
        time.sleep(1.5)
        resp = input(f"  [{label}] Fechou? (s/n) → ").strip().lower()
        if resp == "s":
            print(f"\n  Garra fecha com: {label}\n")
            return
        # reabre para próximo teste
        rtde_io_.setToolDigitalOut(0, True)
        time.sleep(1.0)

    print("\n  Nenhum candidato funcionou — verifique o modelo da garra.")

if __name__ == "__main__":
    main()
