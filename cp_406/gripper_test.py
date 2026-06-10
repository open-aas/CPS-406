#!/usr/bin/env python3
"""
Testa abertura e fechamento da garra Schunk Co-act EGP via Modbus TCP.
Resultado confirmado: reg=1, open=0x0500, close=0x0200.
Execute:
  python3 cp_406/gripper_test.py --ip 192.168.1.100
"""

import time
import argparse
from pymodbus.client import ModbusTcpClient

ROBOT_IP      = "192.168.1.100"
GRIPPER_OPEN  = 0x0500
GRIPPER_CLOSE = 0x0200
GRIPPER_REG   = 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", default=ROBOT_IP)
    args = parser.parse_args()

    client = ModbusTcpClient(args.ip, port=502)
    if not client.connect():
        print("Falha ao conectar Modbus TCP.")
        return
    print("Conectado.\n")

    for label, cmd in [("Abrir", GRIPPER_OPEN), ("Fechar", GRIPPER_CLOSE),
                       ("Abrir", GRIPPER_OPEN)]:
        input(f"  ENTER → {label} → ")
        client.write_register(GRIPPER_REG, cmd)
        status = client.read_holding_registers(0, count=1)
        sw = status.registers[0] if not status.isError() else "?"
        print(f"  status=0x{sw:04X}")
        time.sleep(1.5)

    client.close()
    print("Desconectado.")


if __name__ == "__main__":
    main()
