#!/usr/bin/env python3
"""Drone Console v2 — Numbered menu + GCS heartbeat + YOLO detection."""

import os, sys, time, threading, signal, math, json, urllib.request, urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mavlink_lite import DroneConnection

RED = "\033[91m"; GREEN = "\033[92m"; YELLOW = "\033[93m"
BLUE = "\033[94m"; CYAN = "\033[96m"; BOLD = "\033[1m"; DIM = "\033[2m"
RESET = "\033[0m"; CLS = "\033[2J\033[H"; HIDE = "\033[?25l"; SHOW = "\033[?25h"

drone = None; running = True; last_msg = ""; last_msg_time = 0
gcs_heartbeat_active = True

OBJECT_DETECTION_URL = "http://object-detection:8002/detect"
WAYPOINTS = []

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

def draw_screen():
    t = drone.get_telemetry()
    out = [CLS]
    out.append(f"{BOLD}{CYAN}╔══════════════════════════════════════════════════════════╗{RESET}\n")
    out.append(f"{BOLD}{CYAN}║        DRONE CONSOLE v2 — Numbered Commands              ║{RESET}\n")
    out.append(f"{BOLD}{CYAN}╚══════════════════════════════════════════════════════════╝{RESET}\n")
    status = f"{GREEN}● CONNECTED{RESET}" if t["connected"] else f"{RED}○ DISCONNECTED{RESET}"
    armed = f"{GREEN}● ARMED{RESET}" if t["armed"] else f"{YELLOW}○ DISARMED{RESET}"
    hb = f"{GREEN}● HB{RESET}" if gcs_heartbeat_active else f"{RED}○ HB OFF{RESET}"
    out.append(f"  {status}  |  {armed}  |  {hb}  |  Mode: {BOLD}{t['mode']}{RESET}\n")
    out.append(f"  Lat: {t['lat']:.6f}  Lon: {t['lon']:.6f}  Alt: {t['alt']:.1f}m\n")
    out.append(f"  Heading: {t['heading']*57.3:.0f}°  |  GPS: {t['fix_type']}D ({t['satellites']} sats)\n")
    bat = t["battery"]
    if bat >= 0:
        out.append(f"  Battery: {draw_bar(bat, 100)} {bat:.0f}%\n")
    out.append(f"\n  {BOLD}─── COMMANDS ───{RESET}\n")
    out.append(f"  {GREEN}[1]{RESET} Arm & Takeoff (10m)   {GREEN}[5]{RESET} Land\n")
    out.append(f"  {GREEN}[2]{RESET} Arm only              {GREEN}[6]{RESET} Disarm\n")
    out.append(f"  {GREEN}[3]{RESET} Takeoff (alt m)       {GREEN}[7]{RESET} Return to Launch\n")
    out.append(f"  {GREEN}[4]{RESET} Set Speed (m/s)       {GREEN}[8]{RESET} Hover/Hold\n")
    out.append(f"  {YELLOW}[G]{RESET} Goto GPS (lat,lon,alt) {CYAN}[Y]{RESET} YOLO Detect\n")
    out.append(f"  {BLUE}[M]{RESET} Run Mission (4 WPs)     {BLUE}[W]{RESET} Set Waypoint\n")
    out.append(f"  {RED}[Q]{RESET} Quit\n")
    if len(WAYPOINTS) > 0:
        out.append(f"  {DIM}WPs: {len(WAYPOINTS)} set{RESET}\n")
    global last_msg, last_msg_time
    if last_msg and time.time() - last_msg_time < 8:
        out.append(f"  {last_msg}\n")
    out.append(f"\n  {BOLD}Enter command: {RESET}")
    sys.stdout.write("".join(out))
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

def yolo_detect():
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
    set_msg(f"Running {len(wps)} waypoint mission...")
    for i, (wlat, wlon, walt) in enumerate(wps, 1):
        drone.goto_position(wlat, wlon, walt)
        time.sleep(4)
        for _ in range(20):
            t = drone.get_telemetry()
            dist = math.hypot(t["lat"] - wlat, t["lon"] - wlon) * 111000
            if dist < 3:
                break
            time.sleep(1)
        set_msg(f"WP {i}/{len(wps)} reached")
    set_msg("Mission complete!")

def main():
    global running
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    sys.stdout.write(HIDE)

    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 14540

    global drone
    drone = DroneConnection(udp_target=(host, port))
    print(f"{CLS}{BOLD}Connecting to drone at {host}:{port}...{RESET}")
    try:
        drone.connect()
        print(f"{GREEN}Connected!{RESET}")
    except Exception as e:
        print(f"{RED}Connection failed: {e}{RESET}")
        sys.stdout.write(SHOW)
        return

    time.sleep(2)
    threading.Thread(target=gcs_heartbeat_loop, daemon=True).start()
    threading.Thread(target=ui_loop, daemon=True).start()

    try:
        while running:
            draw_screen()
            try:
                key = sys.stdin.read(1)
            except:
                break
            if not key:
                break

            if key.lower() == 'q':
                set_msg("Shutting down...")
                break
            elif key == '1':
                set_msg("Arming & takeoff to 10m...")
                drone.arm()
                time.sleep(1)
                drone.takeoff(10)
            elif key == '2':
                drone.arm()
                set_msg("Arm command sent")
            elif key == '3':
                set_msg("Enter altitude (m):")
                print(f"{CLS}{BOLD}Takeoff altitude (m):{RESET}\n> ")
                sys.stdout.flush()
                try:
                    a = float(sys.stdin.readline().strip())
                    drone.takeoff(a)
                    set_msg(f"Takeoff to {a}m")
                except:
                    set_msg("Invalid altitude", False)
            elif key == '4':
                set_msg("Enter speed (m/s):")
                print(f"{CLS}{BOLD}Speed (m/s):{RESET}\n> ")
                sys.stdout.flush()
                try:
                    s = float(sys.stdin.readline().strip())
                    drone.set_speed(s)
                    set_msg(f"Speed = {s} m/s")
                except:
                    set_msg("Invalid speed", False)
            elif key == '5':
                drone.land()
                set_msg("Landing")
            elif key == '6':
                drone.disarm()
                set_msg("Disarmed")
            elif key == '7':
                drone.rtl()
                set_msg("Return to Launch")
            elif key == '8':
                t = drone.get_telemetry()
                drone.goto_position(t["lat"], t["lon"], t["alt"])
                set_msg("Hovering at current position")
            elif key.lower() == 'g':
                set_msg("Enter: lat,lon,alt")
                print(f"{CLS}{BOLD}Goto Position{RESET}\nformat: lat,lon,alt\n> ")
                sys.stdout.flush()
                try:
                    parts = sys.stdin.readline().strip().split(",")
                    if len(parts) == 3:
                        la, lo, a = float(parts[0]), float(parts[1]), float(parts[2])
                        drone.goto_position(la, lo, a)
                        set_msg(f"Going to {la:.4f},{lo:.4f} at {a}m")
                    else:
                        set_msg("Use: lat,lon,alt", False)
                except:
                    set_msg("Invalid input", False)
            elif key.lower() == 'y':
                set_msg("Running YOLO detection...")
                threading.Thread(target=yolo_detect, daemon=True).start()
            elif key.lower() == 'm':
                threading.Thread(target=run_mission, daemon=True).start()
            elif key.lower() == 'w':
                t = drone.get_telemetry()
                WAYPOINTS.append((t["lat"], t["lon"], t["alt"]))
                set_msg(f"WP {len(WAYPOINTS)}: {t['lat']:.4f},{t['lon']:.4f}")

    except (EOFError, KeyboardInterrupt):
        pass
    finally:
        running = False
        drone.close()
        sys.stdout.write(f"\n{SHOW}")
        print(f"\n{GREEN}Console closed.{RESET}")

if __name__ == "__main__":
    main()
