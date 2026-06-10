#!/usr/bin/env python3
"""
Testa controle Modbus TCP da garra Schunk Co-act EGP for UR.

O URConnect expõe um servidor Modbus TCP no IP do robô, porta 502.
Registros de controle (holding registers, unidade 1):
  HR 0  — Control Word (write)
  HR 1  — Target position [0.1 mm]
  HR 2  — Speed         [0.1 mm/s]
  HR 3  — Force         [0.1 % de carga nominal]

Control Word bits:
  0x0020 — Grip  (fechar)
  0x0040 — Release (abrir)
  0x0100 — Move to position

Execute:
  python3 cp_406/schunk_egp_test.py --ip 192.168.1.100
"""

import time
import argparse
from pymodbus.client import ModbusTcpClient

ROBOT_IP  = "192.168.1.100"
MODBUS_PORT = 502
UNIT = 1

# addr=1 é o control word gravável (addr=0 é status, só leitura)
CTRL_REG = 1

# candidatos baseados no scan: bit 9=grip, bit 10=release, bit 8=enable
CANDIDATES = [
    ("Grip   0x0200", 0x0200),
    ("Grip   0x0300", 0x0300),
    ("Release 0x0400", 0x0400),
    ("Release 0x0500", 0x0500),
    ("Release 0x0100", 0x0100),
]


def write_cmd(client, cmd, label):
    res = client.write_register(CTRL_REG, cmd)
    rval = client.read_holding_registers(0, count=1)
    status_word = rval.registers[0] if not rval.isError() else "?"
    ok = "OK" if not res.isError() else f"ERRO: {res}"
    print(f"  [{label}]  wrote=0x{cmd:04X}  status=0x{status_word:04X}  → {ok}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", default=ROBOT_IP)
    args = parser.parse_args()

    print(f"Conectando Modbus TCP em {args.ip}:{MODBUS_PORT} ...")
    client = ModbusTcpClient(args.ip, port=MODBUS_PORT)
    if not client.connect():
        print("Falha ao conectar.")
        return
    print("Conectado.\n")

    for label, cmd in CANDIDATES:
        input(f"  ENTER → {label} → ")
        write_cmd(client, cmd, label)
        time.sleep(1.5)

    client.close()
    print("\nDesconectado.")


if __name__ == "__main__":
    main()
