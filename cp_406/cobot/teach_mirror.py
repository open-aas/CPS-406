#!/usr/bin/env python3
"""
Ensina uma trajetória via teclado e replica como espelho.

Fases:
  1. ENSINAR  — controle por teclado; ENTER para parar a gravação.
  2. REPLICAR — robô refaz a trajetória gravada via servoJ.
  3. ESPELHO  — robô refaz com J1 espelhado (direita ↔ esquerda).

Execute a partir de aas/:
  python3 cp_406/cobot/teach_mirror.py [--ip IP] [--hz HZ] [--speed V]
"""

import curses
import math
import time
import argparse
import threading
import rtde_control
import rtde_receive
from pymodbus.client import ModbusTcpClient

ROBOT_IP   = "192.168.1.100"
SPEED           = 0.3
ACCEL           = 0.8
DT              = 1.0 / 125  # período do loop de gravação (125 Hz)
STOP_AFTER      = 0.55       # segundos sem tecla antes de parar
MAX_JOINT_SPEED = 3.3    # rad/s — safety.conf maxJointSpeed (3.3416 rad/s ≈ 191°/s)
MIN_JOINT_POS   = math.radians(-363.0)
MAX_JOINT_POS   = math.radians( 363.0)
JOINT_MARGIN    = math.radians(   5.0)

SAFETY_PLANES = [
    ( 0.7357, -0.6770,  0.0130, 0.354),
    ( 0.0239, -0.0417,  0.9988, 0.164),
]
PLANE_MARGIN    = 0.05
PLANE_LOOKAHEAD = 0.08
RECORD_HZ      = 20   # Hz de amostragem durante gravação
SERVO_T   = 1.0 / RECORD_HZ
LOOKAHEAD = 0.1
GAIN      = 300

GRIPPER_OPEN  = 0x0500
GRIPPER_CLOSE = 0x0200
GRIPPER_REG   = 1

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

LAYOUT = """\
 ┌──────────────────────────────────────────────────────┐
 │         FASE 1 — Ensinar Trajetória (Teclado)         │
 ├───────────────┬──────────────────────────────────────┤
 │  q / a        │  J1  +/−   base                      │
 │  w / s        │  J2  +/−   ombro                     │
 │  e / d        │  J3  +/−   cotovelo                  │
 │  r / f        │  J4  +/−   pulso 1                   │
 │  t / g        │  J5  +/−   pulso 2                   │
 │  y / h        │  J6  +/−   pulso 3 (ferramenta)      │
 ├───────────────┼──────────────────────────────────────┤
 │  o            │  garra abrir                         │
 │  c            │  garra fechar                        │
 ├───────────────┼──────────────────────────────────────┤
 │  + / -        │  aumentar / reduzir velocidade       │
 │  ENTER        │  parar gravação e avançar            │
 │  ESC          │  cancelar e sair                     │
 └───────────────┴──────────────────────────────────────┘"""


def gripper_write(mb, cmd):
    if mb is None:
        return
    try:
        if not mb.is_socket_open():
            mb.connect()
        mb.write_register(GRIPPER_REG, cmd)
    except Exception:
        mb.close()
        mb.connect()
        mb.write_register(GRIPPER_REG, cmd)


def _min_plane_dist(pose):
    return min(a*pose[0] + b*pose[1] + c*pose[2] + d for a, b, c, d in SAFETY_PLANES)


def safe_addstr(stdscr, row, col, text):
    h, w = stdscr.getmaxyx()
    if row >= h or col >= w:
        return
    try:
        stdscr.addstr(row, col, text[:w - col - 1])
    except curses.error:
        pass


def mirror_q(q):
    m = list(q)
    m[0] = -m[0]
    return m


def _call_with_timeout(fn, timeout=2.0):
    t = threading.Thread(target=fn, daemon=True)
    t.start()
    t.join(timeout=timeout)


# ── Fase 1: gravar via teclado (125 Hz — padrão initPeriod/waitPeriod) ────────

def record_keyboard(stdscr, rtde_c, rtde_r, mb, initial_speed, hz):
    curses.curs_set(0)
    stdscr.timeout(0)           # non-blocking, igual ao ur5e_keyboard

    interval       = 1.0 / hz
    waypoints      = []
    gripper_states = []         # True=aberta, False=fechada, None=desconhecida
    gripper_open   = None
    last_rec       = time.monotonic()
    last_key_time  = 0.0
    current_dir    = [0.0] * 6
    jogging        = False
    redraw_counter = 0
    speed          = initial_speed

    layout_rows = LAYOUT.count('\n') + 1

    def redraw(msg=""):
        joints   = rtde_r.getActualQ()
        pose     = rtde_r.getActualTCPPose()
        dur      = len(waypoints) / hz if waypoints else 0.0
        g_label  = ("ABERTA" if gripper_open else "FECHADA") if gripper_open is not None else "---"
        stdscr.clear()
        for i, line in enumerate(LAYOUT.splitlines()):
            safe_addstr(stdscr, i, 0, line)
        row = layout_rows + 1
        safe_addstr(stdscr, row, 0,
            f"  Vel: {speed:.2f} rad/s   Garra: {g_label}   "
            f"Pontos: {len(waypoints)}  ({dur:.1f} s)")
        safe_addstr(stdscr, row+1, 0,
            "  Juntas: " + "  ".join(
                f"J{i+1}={math.degrees(j):+.1f}°" for i, j in enumerate(joints)))
        safe_addstr(stdscr, row+2, 0,
            f"  TCP:  X={pose[0]:+.3f}  Y={pose[1]:+.3f}  Z={pose[2]:+.3f}")
        if msg:
            safe_addstr(stdscr, row+4, 0, f"  {msg}")
        stdscr.refresh()

    redraw("Gravando... mova o robô. ENTER = finalizar  ESC = cancelar")

    try:
        while True:
            t_start = rtde_c.initPeriod()
            now     = time.monotonic()
            key     = stdscr.getch()

            # ── Sample (juntas + estado da garra) ────────────────────────
            if now - last_rec >= interval:
                waypoints.append(list(rtde_r.getActualQ()))
                gripper_states.append(gripper_open)
                last_rec = now

            # ── Teclas ──────────────────────────────────────────────────
            if key == 27:                     # ESC — cancela
                rtde_c.speedStop(ACCEL)
                return None

            elif key in (10, 13):             # ENTER — finaliza
                rtde_c.speedStop(ACCEL)
                break

            elif key in KEY_VEL:
                last_key_time = now
                current_dir   = list(KEY_VEL[key])
                jogging       = True

            elif key == ord('o'):
                gripper_write(mb, GRIPPER_OPEN)
                gripper_open = True

            elif key == ord('c'):
                gripper_write(mb, GRIPPER_CLOSE)
                gripper_open = False

            elif key in (ord('+'), ord('=')):
                speed = min(speed + 0.1, MAX_JOINT_SPEED)

            elif key == ord('-'):
                speed = max(speed - 0.1, 0.1)

            # ── Timeout de parada ────────────────────────────────────────
            if jogging and (now - last_key_time) > STOP_AFTER:
                rtde_c.speedStop(ACCEL)
                jogging     = False
                current_dir = [0.0] * 6

            # ── speedJ + safety por junta ────────────────────────────────
            if jogging:
                q = rtde_r.getActualQ()
                vel = []
                for d, pos in zip(current_dir, q):
                    v = d * speed
                    if v > 0 and pos > MAX_JOINT_POS - JOINT_MARGIN:
                        v = 0.0
                    elif v < 0 and pos < MIN_JOINT_POS + JOINT_MARGIN:
                        v = 0.0
                    vel.append(v)

                pose_now = rtde_r.getActualTCPPose()
                dist_now = _min_plane_dist(pose_now)
                if dist_now < PLANE_MARGIN:
                    for i in range(6):
                        if vel[i] == 0.0:
                            continue
                        q_chk = list(q)
                        q_chk[i] += vel[i] * PLANE_LOOKAHEAD
                        pose_chk = rtde_c.getForwardKinematics(q_chk)
                        if _min_plane_dist(list(pose_chk)) < dist_now:
                            vel[i] = 0.0

                rtde_c.speedJ(vel, ACCEL, DT)

            # ── Redraw ~5 Hz ─────────────────────────────────────────────
            redraw_counter += 1
            if redraw_counter >= 25:
                redraw()
                redraw_counter = 0

            rtde_c.waitPeriod(t_start)

    finally:
        if jogging:
            rtde_c.speedStop(ACCEL)

    return waypoints, gripper_states


# ── Fase 2/3: replay ────────────────────────────────────────────────────────

def replay(rtde_c, rtde_r, mb, waypoints, gripper_states, label):
    if not waypoints:
        return
    total = len(waypoints)
    dur   = total * SERVO_T

    print(f"\n  {label}: movendo para posição inicial...")
    rtde_c.moveJ(waypoints[0], 0.5, 0.8)
    print(f"  {label}: {total} pontos  ({dur:.1f} s)  — Ctrl+C para cancelar")

    t0           = time.monotonic()
    prev_gripper = None     # envia comando apenas quando o estado muda

    try:
        for i, (q, g) in enumerate(zip(waypoints, gripper_states)):
            rtde_c.servoJ(q, 0.0, 0.0, SERVO_T, LOOKAHEAD, GAIN)

            # aciona garra se estado mudou
            if g is not None and g != prev_gripper:
                gripper_write(mb, GRIPPER_OPEN if g else GRIPPER_CLOSE)
                prev_gripper = g

            # progresso a cada segundo
            if i % max(1, int(1.0 / SERVO_T)) == 0:
                elapsed = time.monotonic() - t0
                pct     = 100 * i // total
                print(f"\r    {pct:3d}%  {elapsed:.1f}/{dur:.1f} s", end="", flush=True)

            target = (i + 1) * SERVO_T
            sleep  = (t0 + target) - time.monotonic()
            if sleep > 0:
                time.sleep(sleep)

    except KeyboardInterrupt:
        pass

    rtde_c.servoStop()
    print(f"\r    100%  {dur:.1f}/{dur:.1f} s")
    print(f"  {label} concluído.")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    global SERVO_T, RECORD_HZ

    parser = argparse.ArgumentParser(
        description="Ensina trajetória via teclado e replica como espelho"
    )
    parser.add_argument("--ip",    default=ROBOT_IP)
    parser.add_argument("--hz",    type=int,   default=RECORD_HZ,
                        help=f"Taxa de amostragem Hz (padrão {RECORD_HZ})")
    parser.add_argument("--speed", type=float, default=SPEED,
                        help=f"Velocidade inicial rad/s (padrão {SPEED})")
    parser.add_argument("--no-io", action="store_true",
                        help="Desativa controle da garra (sem Modbus TCP)")
    args = parser.parse_args()

    RECORD_HZ = args.hz
    SERVO_T   = 1.0 / args.hz

    print(f"Conectando ao UR5e em {args.ip} ...")
    try:
        rtde_c = rtde_control.RTDEControlInterface(args.ip)
        rtde_r = rtde_receive.RTDEReceiveInterface(args.ip)
        mb = None
        if not args.no_io:
            mb = ModbusTcpClient(args.ip, port=502)
            if not mb.connect():
                print("  Aviso: falha ao conectar Modbus TCP (garra desativada)")
                mb = None
    except Exception as e:
        print(f"Erro: {e}")
        return

    print("Conectado.\n")

    waypoints = gripper_states = None
    try:
        # ── Fase 1: Ensinar ────────────────────────────────────────────────
        print("=== FASE 1: ENSINAR ===")
        print("Abrindo interface de teclado...")
        result = curses.wrapper(record_keyboard, rtde_c, rtde_r, mb, args.speed, args.hz)

        if result is None:
            print("Cancelado pelo usuário.")
            return

        waypoints, gripper_states = result

        if len(waypoints) < 2:
            print("Trajetória muito curta. Encerrando.")
            return

        print(f"\nGravação concluída: {len(waypoints)} pontos ({len(waypoints)/args.hz:.1f} s).")

        # ── Fase 2: Replicar ───────────────────────────────────────────────
        print("\n=== FASE 2: REPLICAR ===")
        input("Pressione ENTER para replicar a trajetória...")
        replay(rtde_c, rtde_r, mb, waypoints, gripper_states, label="Replicando")

        # ── Fase 3: Espelho ────────────────────────────────────────────────
        print("\n=== FASE 3: ESPELHO ===")
        input("Pressione ENTER para replicar como ESPELHO (J1 negado)...")
        mirrored = [mirror_q(q) for q in waypoints]
        replay(rtde_c, rtde_r, mb, mirrored, gripper_states, label="Espelho")

    except KeyboardInterrupt:
        print("\nInterrompido.")
        _call_with_timeout(lambda: rtde_c.stopJ(ACCEL))
    except Exception as e:
        print(f"Erro: {e}")
        _call_with_timeout(lambda: rtde_c.stopJ(ACCEL))
    finally:
        _call_with_timeout(rtde_c.disconnect)
        _call_with_timeout(rtde_r.disconnect)
        if mb:
            _call_with_timeout(mb.close)
        print("Desconectado.")


if __name__ == "__main__":
    main()
