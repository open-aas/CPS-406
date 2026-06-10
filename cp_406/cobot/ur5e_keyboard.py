#!/usr/bin/env python3
"""
Controle manual do UR5e via teclado (modo junta).
Execute a partir do diretório aas/:
  python3 cp_406/cobot/ur5e_keyboard.py [--ip IP] [--speed V]
"""

import curses
import math
import argparse
import threading
import rtde_control
import rtde_receive
from pymodbus.client import ModbusTcpClient

def gripper_write(mb: ModbusTcpClient, cmd: int):
    if not mb.is_socket_open():
        mb.connect()
    mb.write_register(GRIPPER_REG, cmd)

ROBOT_IP     = "192.168.1.100"
SPEED        = 0.5   # rad/s inicial
ACCEL        = 1.0   # rad/s²
POLL_MS      = 80    # ms — período de polling do curses
GRIPPER_OPEN  = 0x0500   # Schunk EGP Co-act: abrir
GRIPPER_CLOSE = 0x0200   # Schunk EGP Co-act: fechar
GRIPPER_REG   = 1        # holding register do control word

LAYOUT = """\
 ┌─────────────────────────────────────────────────┐
 │         Controle Manual UR5e — Teclado           │
 ├───────────────┬─────────────────────────────────┤
 │  q / a        │  J1  +/−   base                 │
 │  w / s        │  J2  +/−   ombro                │
 │  e / d        │  J3  +/−   cotovelo             │
 │  r / f        │  J4  +/−   pulso 1              │
 │  t / g        │  J5  +/−   pulso 2              │
 │  y / h        │  J6  +/−   pulso 3 (ferramenta) │
 ├───────────────┼─────────────────────────────────┤
 │  o            │  garra abrir  (TDO0=1)          │
 │  c            │  garra fechar (TDO0=0)          │
 ├───────────────┼─────────────────────────────────┤
 │  + / -        │  aumentar / reduzir velocidade  │
 │  0  (zero)    │  ir para HOME                   │
 │  ESC          │  sair                           │
 └───────────────┴─────────────────────────────────┘"""

# direção de cada junta para cada tecla
KEY_VEL = {
    ord('q'): ( 1, 0, 0, 0, 0, 0),
    ord('a'): (-1, 0, 0, 0, 0, 0),
    ord('w'): ( 0, 1, 0, 0, 0, 0),
    ord('s'): ( 0,-1, 0, 0, 0, 0),
    ord('e'): ( 0, 0, 1, 0, 0, 0),
    ord('d'): ( 0, 0,-1, 0, 0, 0),
    ord('r'): ( 0, 0, 0, 1, 0, 0),
    ord('f'): ( 0, 0, 0,-1, 0, 0),
    ord('t'): ( 0, 0, 0, 0, 1, 0),
    ord('g'): ( 0, 0, 0, 0,-1, 0),
    ord('y'): ( 0, 0, 0, 0, 0, 1),
    ord('h'): ( 0, 0, 0, 0, 0,-1),
}

HOME = [j * math.pi / 180 for j in [0, -90, 0, -90, 0, 0]]


def safe_addstr(stdscr, row, col, text):
    h, w = stdscr.getmaxyx()
    if row >= h or col >= w:
        return
    try:
        stdscr.addstr(row, col, text[:w - col - 1])
    except curses.error:
        pass


def redraw(stdscr, rtde_r, speed, gripper_state, msg=""):
    joints = rtde_r.getActualQ()
    pose   = rtde_r.getActualTCPPose()
    stdscr.clear()
    for i, line in enumerate(LAYOUT.splitlines()):
        safe_addstr(stdscr, i, 0, line)
    row = LAYOUT.count('\n') + 2
    safe_addstr(stdscr, row,   0, f"  Velocidade: {speed:.2f} rad/s   Garra: {gripper_state}")
    safe_addstr(stdscr, row+1, 0,
        "  Juntas:  " + "  ".join(
            f"J{i+1}={math.degrees(j):+.1f}°" for i, j in enumerate(joints)
        )
    )
    safe_addstr(stdscr, row+2, 0,
        f"  TCP:     X={pose[0]:+.4f}  Y={pose[1]:+.4f}  Z={pose[2]:+.4f}"
        f"  Rx={pose[3]:+.4f}  Ry={pose[4]:+.4f}  Rz={pose[5]:+.4f}"
    )
    if msg:
        safe_addstr(stdscr, row+4, 0, f"  {msg}")
    stdscr.refresh()


def run(stdscr, rtde_c, rtde_r, mb, speed):
    curses.curs_set(0)
    stdscr.timeout(POLL_MS)
    gripper_state = "---"
    redraw(stdscr, rtde_r, speed, gripper_state)

    while True:
        key = stdscr.getch()

        if key == 27:           # ESC — sair
            rtde_c.stopJ(ACCEL)
            break

        elif key in KEY_VEL:
            step = speed * (POLL_MS / 1000)
            current_q = list(rtde_r.getActualQ())
            target_q  = [q + d * step for q, d in zip(current_q, KEY_VEL[key])]
            rtde_c.moveJ(target_q, speed, ACCEL, asynchronous=True)

        elif key in (ord('+'), ord('=')):
            speed = min(speed + 0.1, 2.0)
            redraw(stdscr, rtde_r, speed, gripper_state, f"Velocidade: {speed:.2f} rad/s")
            continue

        elif key == ord('-'):
            speed = max(speed - 0.1, 0.1)
            redraw(stdscr, rtde_r, speed, gripper_state, f"Velocidade: {speed:.2f} rad/s")
            continue

        elif key == ord('0'):
            rtde_c.stopJ(ACCEL)
            redraw(stdscr, rtde_r, speed, gripper_state, "Movendo para HOME...")
            rtde_c.moveJ(HOME, 0.5, 0.8)

        elif key == ord('o'):
            gripper_write(mb, GRIPPER_OPEN)
            gripper_state = "ABERTA"

        elif key == ord('c'):
            gripper_write(mb, GRIPPER_CLOSE)
            gripper_state = "FECHADA"

        else:
            rtde_c.stopJ(ACCEL)

        redraw(stdscr, rtde_r, speed, gripper_state)

    return speed


def _call_with_timeout(fn, timeout=2.0):
    t = threading.Thread(target=fn, daemon=True)
    t.start()
    t.join(timeout=timeout)


def _cleanup(rtde_c, rtde_r, mb):
    _call_with_timeout(lambda: rtde_c.stopJ(ACCEL))
    _call_with_timeout(rtde_c.disconnect)
    _call_with_timeout(rtde_r.disconnect)
    _call_with_timeout(mb.close)
    print("Desconectado.")


def main():
    parser = argparse.ArgumentParser(description="Controle manual do UR5e via teclado")
    parser.add_argument("--ip",    default=ROBOT_IP, help="IP do robô")
    parser.add_argument("--speed", type=float, default=SPEED, help="Velocidade inicial (rad/s)")
    args = parser.parse_args()

    print(f"Conectando ao UR5e em {args.ip} ...")
    try:
        rtde_c = rtde_control.RTDEControlInterface(args.ip)
        rtde_r = rtde_receive.RTDEReceiveInterface(args.ip)
        mb     = ModbusTcpClient(args.ip, port=502)
        if not mb.connect():
            raise RuntimeError("Falha ao conectar Modbus TCP (garra)")
    except KeyboardInterrupt:
        print("\nInterrompido.")
        return
    except Exception as e:
        print(f"Erro: {e}")
        return

    print("Conectado. Abrindo interface de teclado...")
    try:
        curses.wrapper(run, rtde_c, rtde_r, mb, args.speed)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Erro: {e}")
    finally:
        _cleanup(rtde_c, rtde_r, mb)


if __name__ == "__main__":
    main()
