#!/usr/bin/env python3
"""
Diagnóstico interativo da garra Schunk EGP via Modbus TCP.
Lê registradores de status e permite testar comandos manualmente.

Uso:
  python3 cp_406/cobot/gripper_probe.py [--ip IP]
"""
import argparse
import time
from pymodbus.client import ModbusTcpClient

ROBOT_IP    = "192.168.1.100"
GRIPPER_IP  = "172.21.0.210"
PORT        = 502


def read_regs(mb, start=0, count=10):
    r = mb.read_holding_registers(start, count)
    if r.isError():
        print(f"  Erro ao ler reg {start}–{start+count-1}: {r}")
        return []
    return list(r.registers)


def write_reg(mb, reg, value):
    r = mb.write_register(reg, value)
    if r.isError():
        print(f"  Erro ao escrever reg={reg} val=0x{value:04X}: {r}")
        return False
    return True


def dump(mb):
    print("\n  ── Holding Registers 0–15 ──────────────────────────")
    vals = read_regs(mb, start=0, count=16)
    for i, v in enumerate(vals):
        print(f"    reg[{i:2d}]  0x{v:04X}  ({v:5d})")
    print()


def main():
    parser = argparse.ArgumentParser(description="Diagnóstico Modbus da garra Schunk EGP")
    parser.add_argument("--ip", default=GRIPPER_IP)
    args = parser.parse_args()

    print(f"Conectando Modbus TCP a {args.ip}:502 ...")
    mb = ModbusTcpClient(args.ip, port=PORT)
    if not mb.connect():
        print("Falha na conexão.")
        return
    print("Conectado.\n")

    print("Leitura inicial dos registradores:")
    dump(mb)

    print("Comandos disponíveis:")
    print("  r            — relê os registradores")
    print("  w REG VAL    — escreve VAL (hex ou dec) em REG")
    print("  open         — comando conhecido: reg1=0x0500 (abrir)")
    print("  close        — comando conhecido: reg1=0x0200 (fechar/GRIP)")
    print("  pos N        — escreve reg1=0x0300 + reg2=N (MOVE_TO_POSITION)")
    print("  seq          — varre posições 0..1000 em passos de 100")
    print("  q / quit     — sair\n")

    while True:
        try:
            line = input("gripper> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not line:
            continue

        parts = line.split()
        cmd   = parts[0].lower()

        if cmd in ("q", "quit"):
            break

        elif cmd == "r":
            dump(mb)

        elif cmd == "open":
            ok = write_reg(mb, 1, 0x0500)
            print(f"  reg[1] ← 0x0500  {'OK' if ok else 'ERRO'}")
            time.sleep(0.5)
            dump(mb)

        elif cmd == "close":
            ok = write_reg(mb, 1, 0x0200)
            print(f"  reg[1] ← 0x0200  {'OK' if ok else 'ERRO'}")
            time.sleep(1.0)
            dump(mb)

        elif cmd == "pos" and len(parts) == 2:
            try:
                pos = int(parts[1])
            except ValueError:
                print("  Uso: pos N  (N inteiro)")
                continue
            print(f"  MOVE_TO_POSITION: reg[1]=0x0300  reg[2]={pos}")
            write_reg(mb, 1, 0x0300)
            write_reg(mb, 2, pos)
            time.sleep(1.5)
            dump(mb)

        elif cmd == "w" and len(parts) == 3:
            try:
                reg = int(parts[1])
                val = int(parts[2], 0)   # aceita 0x... ou decimal
            except ValueError:
                print("  Uso: w REG VAL  (VAL pode ser 0xHEX ou decimal)")
                continue
            ok = write_reg(mb, reg, val)
            print(f"  reg[{reg}] ← 0x{val:04X}  {'OK' if ok else 'ERRO'}")
            time.sleep(0.3)
            dump(mb)

        elif cmd == "seq":
            print("  Varrendo posições 0..1000 — observe o movimento da garra")
            for pos in range(0, 1001, 100):
                print(f"    pos={pos}", end="  ", flush=True)
                write_reg(mb, 1, 0x0300)
                write_reg(mb, 2, pos)
                time.sleep(1.2)
                vals = read_regs(mb, 0, 4)
                print("  regs:", [f"0x{v:04X}" for v in vals])
            print()

        else:
            print("  Comando não reconhecido. Digite r, w, open, close, pos N, seq ou q.")

    mb.close()
    print("Desconectado.")


if __name__ == "__main__":
    main()
