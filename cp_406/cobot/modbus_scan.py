#!/usr/bin/env python3
"""Escaneia registros Modbus TCP para encontrar endereços válidos."""

import argparse
from pymodbus.client import ModbusTcpClient

ROBOT_IP = "192.168.1.100"

READ_RANGES  = [(0, 20), (256, 290)]
WRITE_RANGES = [(0, 20), (256, 290)]


def scan_readable(client, start, end):
    found = []
    for addr in range(start, end):
        res = client.read_holding_registers(addr, count=1)
        if not res.isError():
            found.append((addr, res.registers[0]))
    return found


def scan_writable(client, start, end):
    writable = []
    for addr in range(start, end):
        res_r = client.read_holding_registers(addr, count=1)
        if res_r.isError():
            continue
        current = res_r.registers[0]
        res_w = client.write_register(addr, current)   # escreve o mesmo valor
        if not res_w.isError():
            writable.append((addr, current))
    return writable


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", default=ROBOT_IP)
    args = parser.parse_args()

    client = ModbusTcpClient(args.ip, port=502)
    if not client.connect():
        print("Falha ao conectar.")
        return

    print(f"Escaneando {args.ip}:502 ...\n")

    print("── Registros legíveis ──────────────────────────")
    for start, end in READ_RANGES:
        for addr, val in scan_readable(client, start, end):
            print(f"  R  addr={addr:5d}  0x{val:04X} ({val})")

    print("\n── Registros graváveis (write sem alterar valor) ──")
    for start, end in WRITE_RANGES:
        for addr, val in scan_writable(client, start, end):
            print(f"  W  addr={addr:5d}  0x{val:04X} ({val})")

    client.close()


if __name__ == "__main__":
    main()
