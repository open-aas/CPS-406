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

ROBOT_IP  = "192.168.1.100"
SPEED           = 0.3
ACCEL           = 0.8
POLL_MS         = 50     # ms — polling do curses
STOP_AFTER      = 0.55   # segundos sem tecla antes de parar
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
 │  + / -        │  aumentar / reduzir velocidade       │
 │  ENTER        │  parar gravação e avançar            │
 │  ESC          │  cancelar e sair                     │
 └───────────────┴──────────────────────────────────────┘"""


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


# ── Fase 1: gravar via teclado ──────────────────────────────────────────────

def record_keyboard(stdscr, rtde_c, rtde_r, speed, hz):
    curses.curs_set(0)
    stdscr.timeout(POLL_MS)

    interval       = 1.0 / hz
    waypoints      = []
    recording      = True
    last_rec       = time.monotonic()
    last_move_time = time.monotonic()
    last_vel       = [0.0] * 6
    stopped        = True

    layout_rows = LAYOUT.count('\n') + 1

    def redraw(msg=""):
        joints = rtde_r.getActualQ()
        stdscr.clear()
        for i, line in enumerate(LAYOUT.splitlines()):
            safe_addstr(stdscr, i, 0, line)
        row = layout_rows + 1
        safe_addstr(stdscr, row,   0,
            f"  Vel: {speed:.2f} rad/s   Pontos gravados: {len(waypoints)}")
        safe_addstr(stdscr, row+1, 0,
            "  Juntas: " + "  ".join(
                f"J{i+1}={math.degrees(j):+.1f}°" for i, j in enumerate(joints)
            ))
        if msg:
            safe_addstr(stdscr, row+3, 0, f"  {msg}")
        stdscr.refresh()

    redraw("Gravando... mova o robô e pressione ENTER para finalizar.")

    while recording:
        now = time.monotonic()
        if now - last_rec >= interval:
            waypoints.append(list(rtde_r.getActualQ()))
            last_rec = now

        key = stdscr.getch()

        if key == 27:           # ESC — cancela
            return None

        elif key in (10, 13):   # ENTER — finaliza gravação
            rtde_c.stopJ(ACCEL)
            recording = False

        elif key in KEY_VEL:
            last_move_time = now
            stopped = False
            q = rtde_r.getActualQ()
            vel = []
            for d, pos in zip(KEY_VEL[key], q):
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
            if vel != last_vel:
                rtde_c.speedJ(vel, ACCEL, 0)
                last_vel = vel

        elif key in (ord('+'), ord('=')):
            speed = min(speed + 0.1, MAX_JOINT_SPEED)

        elif key == ord('-'):
            speed = max(speed - 0.1, 0.1)

        if not stopped and (now - last_move_time) > STOP_AFTER:
            rtde_c.speedStop(ACCEL)
            stopped = True
            last_vel = [0.0] * 6

        redraw()

    return waypoints


# ── Fase 2/3: replay ────────────────────────────────────────────────────────

def replay(rtde_c, waypoints, label):
    if not waypoints:
        return
    print(f"\n  {label}: movendo para posição inicial...")
    rtde_c.moveJ(waypoints[0], 0.5, 0.8)
    print(f"  {label}: reproduzindo {len(waypoints)} pontos ({len(waypoints)/RECORD_HZ:.1f} s)...")

    t0 = time.monotonic()
    for i, q in enumerate(waypoints):
        rtde_c.servoJ(q, 0.0, 0.0, SERVO_T, LOOKAHEAD, GAIN)
        target = (i + 1) * SERVO_T
        sleep  = (t0 + target) - time.monotonic()
        if sleep > 0:
            time.sleep(sleep)

    rtde_c.servoStop()
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
    args = parser.parse_args()

    RECORD_HZ = args.hz
    SERVO_T   = 1.0 / args.hz

    print(f"Conectando ao UR5e em {args.ip} ...")
    try:
        rtde_c = rtde_control.RTDEControlInterface(args.ip)
        rtde_r = rtde_receive.RTDEReceiveInterface(args.ip)
    except Exception as e:
        print(f"Erro: {e}")
        return

    print("Conectado.\n")

    waypoints = None
    try:
        # ── Fase 1: Ensinar ────────────────────────────────────────────────
        print("=== FASE 1: ENSINAR ===")
        print("Abrindo interface de teclado...")
        waypoints = curses.wrapper(record_keyboard, rtde_c, rtde_r, args.speed, args.hz)

        if waypoints is None:
            print("Cancelado pelo usuário.")
            return

        if len(waypoints) < 2:
            print("Trajetória muito curta. Encerrando.")
            return

        print(f"\nGravação concluída: {len(waypoints)} pontos ({len(waypoints)/args.hz:.1f} s).")

        # ── Fase 2: Replicar ───────────────────────────────────────────────
        print("\n=== FASE 2: REPLICAR ===")
        input("Pressione ENTER para replicar a trajetória...")
        replay(rtde_c, waypoints, label="Replicando")

        # ── Fase 3: Espelho ────────────────────────────────────────────────
        print("\n=== FASE 3: ESPELHO ===")
        input("Pressione ENTER para replicar como ESPELHO (J1 negado)...")
        mirrored = [mirror_q(q) for q in waypoints]
        replay(rtde_c, mirrored, label="Espelho")

    except KeyboardInterrupt:
        print("\nInterrompido.")
        _call_with_timeout(lambda: rtde_c.stopJ(ACCEL))
    except Exception as e:
        print(f"Erro: {e}")
        _call_with_timeout(lambda: rtde_c.stopJ(ACCEL))
    finally:
        _call_with_timeout(rtde_c.disconnect)
        _call_with_timeout(rtde_r.disconnect)
        print("Desconectado.")


if __name__ == "__main__":
    main()
