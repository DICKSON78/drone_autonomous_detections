#!/usr/bin/env python3
"""Drone Console v2 — Numbered menu + GCS heartbeat + YOLO detection."""

import os, sys, time, threading, signal, math, json, urllib.request, urllib.error
import termios, tty, atexit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mavlink_lite import DroneConnection

RED = "\033[91m"; GREEN = "\033[92m"; YELLOW = "\033[93m"
BLUE = "\033[94m"; CYAN = "\033[96m"; BOLD = "\033[1m"; DIM = "\033[2m"
RESET = "\033[0m"; CLS = "\033[2J\033[H"; HIDE = "\033[?25l"; SHOW = "\033[?25h"

drone = None; running = True; last_msg = ""; last_msg_time = 0
gcs_heartbeat_active = True
state_machine = "IDLE"
avoidance_enabled = False
avoidance_thread = None
old_termios = None
stdout_lock = threading.Lock()

OBJECT_DETECTION_URL = "http://object-detection:8002/detect"
WAYPOINTS = []

STATE_NAMES = {0: "IDLE", 1: "TAKEOFF", 2: "NAVIGATING", 3: "APPROACHING",
               4: "HOVERING", 5: "LANDING", 6: "LANDED", 7: "RETURNING_HOME",
               8: "MISSION", 9: "AVOIDANCE"}

def set_msg(text, ok=True):
    global last_msg, last_msg_time
    last_msg_time = time.time()
    icon = f"{GREEN}✓{RESET}" if ok else f"{RED}✗{RESET}"
    last_msg = f"{icon} {text}"

def draw_bar(value, max_val, width=20):
    filled = int(value / max_val * width) if max_val > 0 else 0
    filled = max(0, min(width, filled))
    f = "█" * filled; e = "░" * (width - filled)
    color = RED if value < 30 else YELLOW if value < 60 else GREEN
    return f"{color}{f}{e}{RESET}"

def setup_terminal():
    global old_termios
    fd = sys.stdin.fileno()
    old_termios = termios.tcgetattr(fd)
    tty.setcbreak(fd)

def restore_terminal():
    global old_termios
    if old_termios is not None:
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, old_termios)

def draw_screen():
    with stdout_lock:
        t = drone.get_telemetry()
        out = []
        out.append("\033[1;1H\033[2K")
        out.append(f"{BOLD}{CYAN}╔══════════════════════════════════════════════════════════╗{RESET}")
        out.append("\033[2;1H\033[2K")
        out.append(f"{BOLD}{CYAN}║        DRONE CONSOLE v2 — Numbered Commands              ║{RESET}")
        out.append("\033[3;1H\033[2K")
        out.append(f"{BOLD}{CYAN}╚══════════════════════════════════════════════════════════╝{RESET}")
        out.append("\033[4;1H\033[2K")
        status = f"{GREEN}● CONNECTED{RESET}" if t["connected"] else f"{RED}○ DISCONNECTED{RESET}"
        armed = f"{GREEN}● ARMED{RESET}" if t["armed"] else f"{YELLOW}○ DISARMED{RESET}"
        hb_st = f"{GREEN}● HB{RESET}" if gcs_heartbeat_active else f"{RED}○ HB OFF{RESET}"
        out.append(f"  {status}  |  {armed}  |  {hb_st}  |  {CYAN}State: {state_machine}{RESET}  |  Mode: {t['mode']}")
        out.append("\033[5;1H\033[2K")
        out.append(f"  Lat: {t['lat']:.6f}  Lon: {t['lon']:.6f}  Alt: {t['alt']:.1f}m")
        out.append("\033[6;1H\033[2K")
        out.append(f"  Heading: {t['heading']*57.3:.0f}°  |  GPS: {t['fix_type']}D ({t['satellites']} sats)")
        out.append("\033[7;1H\033[2K")
        bat = t["battery"]
        if bat >= 0:
            out.append(f"  Battery: {draw_bar(bat, 100)} {bat:.0f}%")
        else:
            out.append(f"  Battery: N/A")
        out.append("\033[8;1H\033[2K")
        out.append("\033[9;1H\033[2K")
        out.append(f"  {BOLD}─── ACTIONS ───{RESET}")
        cmd_lines = [
            f"  {GREEN}[1]{RESET} Takeoff      {GREEN}[3]{RESET} Go to GPS    {GREEN}[5]{RESET} Arm      {GREEN}[7]{RESET} Hover",
            f"  {GREEN}[2]{RESET} Land         {GREEN}[4]{RESET} Navigate to  {GREEN}[6]{RESET} Disarm   {GREEN}[8]{RESET} Return Home",
            f"",
            f"  {YELLOW}[Y]{RESET} YOLO  {YELLOW}[A]{RESET} Avoid: {'ON ' if avoidance_enabled else 'OFF'}  {YELLOW}[M]{RESET} Mission  {YELLOW}[G]{RESET} Set Speed  {RED}[Q]{RESET} Quit",
        ]
        for i, line in enumerate(cmd_lines):
            out.append(f"\033[{10+i};1H\033[2K{line}")
        out.append("\033[14;1H\033[2K")
        global last_msg, last_msg_time
        if last_msg and time.time() - last_msg_time < 8:
            out.append(f"  {last_msg}")
        else:
            out.append(f"  Waypoints: {len(WAYPOINTS)} set")
        out.append("\033[15;1H\033[2K")
        out.append(f"  {DIM}Avoidance thread: {'RUNNING' if avoidance_enabled else 'OFF'}{RESET}")
        out.append("\033[16;1H\033[2K")
        sys.stdout.write("".join(out))
        sys.stdout.flush()

def show_prompt():
    with stdout_lock:
        sys.stdout.write("\033[19;1H\033[2K  Enter command: \033[19;18H")
        sys.stdout.flush()

def show_sub_prompt(text):
    with stdout_lock:
        sys.stdout.write(f"\033[20;1H\033[2K  {text} ")
        sys.stdout.flush()

def clear_sub_prompt():
    with stdout_lock:
        sys.stdout.write("\033[20;1H\033[2K")
        sys.stdout.flush()

def gcs_heartbeat_loop():
    global gcs_heartbeat_active
    while running:
        try:
            drone._send_raw_heartbeat()
            gcs_heartbeat_active = True
        except:
            gcs_heartbeat_active = False
        time.sleep(0.5)

def ui_loop():
    while running:
        draw_screen()
        time.sleep(0.5)

def yolo_detect_single():
    try:
        import cv2
        cap = cv2.VideoCapture("udp://127.0.0.1:5600", cv2.CAP_FFMPEG)
        ret, frame = cap.read()
        cap.release()
        if not ret:
            set_msg("No camera frame available", False)
            return
        _, img_encoded = cv2.imencode('.jpg', frame)
        img_bytes = img_encoded.tobytes()
        req = urllib.request.Request(
            OBJECT_DETECTION_URL,
            data=img_bytes,
            headers={'Content-Type': 'image/jpeg'},
            method='POST'
        )
        resp = urllib.request.urlopen(req, timeout=5)
        result = json.loads(resp.read())
        dets = result.get('detections', [])
        if dets:
            for d in dets:
                set_msg(f"Detected: class={d.get('class_id')} conf={d.get('confidence'):.2f}")
        else:
            set_msg("No objects detected")
    except ImportError:
        set_msg("OpenCV not installed, skipping YOLO", False)
    except Exception as e:
        set_msg(f"YOLO error: {e}", False)

def yolo_continuous():
    global avoidance_enabled
    try:
        import cv2
    except ImportError:
        return
    cap = None
    try:
        cap = cv2.VideoCapture("udp://127.0.0.1:5600", cv2.CAP_FFMPEG)
        while running:
            if not avoidance_enabled:
                time.sleep(0.5)
                continue
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.1)
                continue
            _, img_encoded = cv2.imencode('.jpg', frame)
            try:
                req = urllib.request.Request(
                    OBJECT_DETECTION_URL,
                    data=img_encoded.tobytes(),
                    headers={'Content-Type': 'image/jpeg'},
                    method='POST'
                )
                resp = urllib.request.urlopen(req, timeout=2)
                result = json.loads(resp.read())
                detections = result.get('detections', [])
                if detections:
                    img_w = frame.shape[1]
                    for d in detections:
                        bbox = d.get('bbox', [0, 0, 0, 0])
                        cx = (bbox[0] + bbox[2]) / 2
                        rel_x = cx / img_w
                        if rel_x < 0.3:
                            set_msg(f"Obstacle LEFT → strafe right")
                            drone.strafe('right', 3)
                        elif rel_x > 0.7:
                            set_msg(f"Obstacle RIGHT → strafe left")
                            drone.strafe('left', 3)
                        else:
                            set_msg(f"Obstacle CENTER → ascend")
                            drone.strafe('up', 2)
            except:
                pass
            time.sleep(0.2)
    finally:
        if cap is not None:
            cap.release()

def run_mission():
    t = drone.get_telemetry()
    lat, lon, alt = t["lat"], t["lon"], t["alt"]
    if alt < 5:
        set_msg("Takeoff first before mission", False)
        return
    radius = 0.0006
    wps = [
        (lat + radius, lon, alt),
        (lat, lon + radius, alt),
        (lat - radius, lon, alt),
        (lat, lon - radius, alt),
        (lat + radius, lon, alt),
    ]
    run_mission_args(wps)

def run_mission_args(wps):
    set_msg(f"Running {len(wps)} waypoint mission...")
    for i, (wlat, wlon, walt) in enumerate(wps, 1):
        drone.goto_position(wlat, wlon, walt)
        time.sleep(4)
        for _ in range(20):
            t = drone.get_telemetry()
            lat_dist = (t["lat"] - wlat) * 111000
            lon_dist = (t["lon"] - wlon) * 111000 * math.cos(math.radians((t["lat"] + wlat) / 2))
            dist = math.hypot(lat_dist, lon_dist)
            if dist < 3:
                break
            time.sleep(1)
        set_msg(f"WP {i}/{len(wps)} reached")
    set_msg("Mission complete!")

def navigate_to_thread(la, lo, a):
    global state_machine
    t = drone.get_telemetry()

    # If on ground, arm and take off directly to user's target altitude
    if t["alt"] < 2:
        state_machine = "TAKEOFF"
        set_msg(f"Taking off to {a}m...")
        drone.arm()
        time.sleep(1)
        drone.takeoff(a)
        for _ in range(60):
            time.sleep(0.5)
            t = drone.get_telemetry()
            if t["alt"] > 3:
                break
        else:
            set_msg("Takeoff failed — aborting goto", False)
            state_machine = "IDLE"
            return
        # Wait a bit more to reach target altitude
        for _ in range(40):
            time.sleep(0.5)
            t = drone.get_telemetry()
            if abs(t["alt"] - a) < 2:
                break

    elif abs(t["alt"] - a) > 3:
        state_machine = "TAKEOFF" if a > t["alt"] else "LANDING"
        set_msg(f"{'Climbing' if a > t['alt'] else 'Descending'} to {a}m...")
        drone.goto_position(t["lat"], t["lon"], a)
        for _ in range(40):
            time.sleep(0.5)
            t = drone.get_telemetry()
            if abs(t["alt"] - a) < 2:
                break

    # Navigate to target lat/lon at target altitude
    state_machine = "NAVIGATING"
    set_msg(f"Navigating to {la:.4f},{lo:.4f} at {a}m...")
    drone.goto_position(la, lo, a)

    for step in range(600):
        t = drone.get_telemetry()
        lat_dist = (t["lat"] - la) * 111000
        lon_dist = (t["lon"] - lo) * 111000 * math.cos(math.radians((t["lat"] + la) / 2))
        dist = math.hypot(lat_dist, lon_dist)
        alt_err = abs(t["alt"] - a)

        if dist < 2 and alt_err < 3:
            state_machine = "HOVERING"
            set_msg(f"Target reached! ({dist:.1f}m, alt err {alt_err:.1f}m)")
            return

        state_machine = "APPROACHING" if dist < 10 else "NAVIGATING"

        if step % 6 == 0:
            drone.goto_position(la, lo, a)

        time.sleep(0.3)

    state_machine = "HOVERING"
    set_msg("Navigate timeout — check coordinates", False)

def smooth_land():
    global state_machine
    state_machine = "LANDING"
    t = drone.get_telemetry()
    set_msg(f"Landing from {t['alt']:.1f}m...")
    drone.land()
    landed = False
    for _ in range(80):
        time.sleep(0.3)
        t = drone.get_telemetry()
        if t["alt"] < 0.15:
            landed = True
            break
    if landed:
        drone.disarm()
        state_machine = "LANDED"
        set_msg("Landed ✓")
    else:
        state_machine = "HOVERING"
        set_msg("Land timeout — check drone state", False)

def main():
    global running, state_machine, avoidance_enabled, avoidance_thread
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    sys.stdout.write(HIDE)
    setup_terminal()
    atexit.register(restore_terminal)

    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 14550

    global drone
    drone = DroneConnection(udp_target=(host, port))
    print(f"{CLS}{BOLD}Connecting to drone at {host}:{port}...{RESET}")
    try:
        drone.connect()
        print(f"{GREEN}Connected!{RESET}")
    except Exception as e:
        print(f"{RED}Connection failed: {e}{RESET}")
        restore_terminal()
        sys.stdout.write(SHOW)
        return

    time.sleep(0.5)
    threading.Thread(target=ui_loop, daemon=True).start()
    avoidance_thread = threading.Thread(target=yolo_continuous, daemon=True)
    avoidance_thread.start()

    show_prompt()
    try:
        while running:
            try:
                key = sys.stdin.read(1)
            except:
                break
            if not key:
                break

            if key == 'q' or key == 'Q':
                break

            elif key == '1':
                show_sub_prompt("Takeoff altitude (m) [10]:")
                try:
                    line = sys.stdin.readline().strip()
                    a = float(line) if line else 10
                    clear_sub_prompt()
                    state_machine = "TAKEOFF"
                    drone.arm()
                    time.sleep(0.3)
                    drone.takeoff(a)
                    state_machine = "HOVERING"
                    set_msg(f"Takeoff to {a}m")
                except:
                    clear_sub_prompt()
                    set_msg("Invalid altitude", False)

            elif key == '2':
                threading.Thread(target=smooth_land, daemon=True).start()
                set_msg("Landing...")

            elif key == '3':
                show_sub_prompt("Enter latitude:")
                try:
                    la = float(sys.stdin.readline().strip())
                    show_sub_prompt("Enter longitude:")
                    lo = float(sys.stdin.readline().strip())
                    show_sub_prompt("Enter altitude (m) [15]:")
                    line = sys.stdin.readline().strip()
                    a = float(line) if line else 15
                    clear_sub_prompt()
                    set_msg(f"Navigating to {la:.4f},{lo:.4f} at {a}m...")
                    threading.Thread(target=navigate_to_thread, args=(la, lo, a), daemon=True).start()
                except:
                    clear_sub_prompt()
                    set_msg("Invalid coordinate", False)

            elif key == '4':
                show_sub_prompt("Target latitude:")
                try:
                    la = float(sys.stdin.readline().strip())
                    show_sub_prompt("Target longitude:")
                    lo = float(sys.stdin.readline().strip())
                    show_sub_prompt("Target altitude (m) [15]:")
                    line = sys.stdin.readline().strip()
                    a = float(line) if line else 15
                    clear_sub_prompt()
                    set_msg(f"Navigating to {la:.4f},{lo:.4f} at {a}m...")
                    threading.Thread(target=navigate_to_thread, args=(la, lo, a), daemon=True).start()
                except:
                    clear_sub_prompt()
                    set_msg("Invalid target", False)

            elif key == '5':
                drone.arm()
                state_machine = "HOVERING"
                set_msg("Arm command sent")

            elif key == '6':
                drone.disarm()
                state_machine = "IDLE"
                set_msg("Disarmed")

            elif key == '7':
                t = drone.get_telemetry()
                drone.goto_position(t["lat"], t["lon"], t["alt"])
                state_machine = "HOVERING"
                set_msg("Hovering at current position")

            elif key == '8':
                drone.rtl()
                state_machine = "RETURNING_HOME"
                set_msg("Return to Launch")

            elif key.lower() == 'y':
                set_msg("Running YOLO detection...")
                threading.Thread(target=yolo_detect_single, daemon=True).start()

            elif key.lower() == 'a':
                avoidance_enabled = not avoidance_enabled
                set_msg(f"Avoidance {'ENABLED' if avoidance_enabled else 'DISABLED'}")

            elif key.lower() == 'm':
                show_sub_prompt("Number of waypoints:")
                try:
                    n = int(sys.stdin.readline().strip())
                    clear_sub_prompt()
                    if n < 1:
                        set_msg("Need at least 1 waypoint", False)
                        show_prompt()
                        continue
                    wps = []
                    for i in range(n):
                        show_sub_prompt(f"WP {i+1} latitude:")
                        la = float(sys.stdin.readline().strip())
                        show_sub_prompt(f"WP {i+1} longitude:")
                        lo = float(sys.stdin.readline().strip())
                        show_sub_prompt(f"WP {i+1} altitude (m) [15]:")
                        line = sys.stdin.readline().strip()
                        a = float(line) if line else 15
                        wps.append((la, lo, a))
                    clear_sub_prompt()
                    set_msg(f"Running {len(wps)} waypoint mission...")
                    threading.Thread(target=run_mission_args, args=(wps,), daemon=True).start()
                except:
                    clear_sub_prompt()
                    set_msg("Invalid mission input", False)

            elif key.lower() == 'g':
                show_sub_prompt("Speed (m/s):")
                try:
                    s = float(sys.stdin.readline().strip())
                    clear_sub_prompt()
                    drone.set_speed(s)
                    set_msg(f"Speed = {s} m/s")
                except:
                    clear_sub_prompt()
                    set_msg("Invalid speed", False)

            show_prompt()

    except (EOFError, KeyboardInterrupt):
        pass
    finally:
        running = False
        drone.close()
        restore_terminal()
        sys.stdout.write(f"\n{SHOW}")
        print(f"\n{GREEN}Console closed.{RESET}")

if __name__ == "__main__":
    main()