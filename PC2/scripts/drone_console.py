#!/usr/bin/env python3
"""Drone Control Console - Terminal UI for PX4 drone control via MAVLink."""

import os
import sys
import time
import threading
import signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mavlink_lite import DroneConnection

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"
CLS = "\033[2J\033[H"
HIDE = "\033[?25l"
SHOW = "\033[?25h"

drone = None
running = True
last_cmd_result = ""
last_cmd_time = 0

def draw_bar(value, max_val, width=20, filled="█", empty="░"):
    filled_count = int(value / max_val * width) if max_val > 0 else 0
    filled_count = max(0, min(width, filled_count))
    bar = filled * filled_count + empty * (width - filled_count)
    if value < 30 and max_val == 100:
        color = RED
    elif value < 60 and max_val == 100:
        color = YELLOW
    else:
        color = GREEN
    return f"{color}{bar}{RESET}"

def draw_screen():
    t = drone.get_telemetry()
    out = [CLS]
    out.append(f"{BOLD}{CYAN}╔══════════════════════════════════════════════════════════╗{RESET}\n")
    out.append(f"{BOLD}{CYAN}║          DRONE AUTONOMOUS CONTROL CONSOLE                ║{RESET}\n")
    out.append(f"{BOLD}{CYAN}╚══════════════════════════════════════════════════════════╝{RESET}\n")

    status = f"{GREEN}● CONNECTED{RESET}" if t["connected"] else f"{RED}○ DISCONNECTED{RESET}"
    armed = f"{GREEN}● ARMED{RESET}" if t["armed"] else f"{YELLOW}○ DISARMED{RESET}"
    out.append(f"  Status  : {status}  |  {armed}")
    out.append(f"  Mode    : {BOLD}{t['mode']}{RESET}")
    out.append(f""
)
    out.append(f"  {BOLD}POSITION{RESET}")
    out.append(f"  Lat     : {t['lat']:.6f}")
    out.append(f"  Lon     : {t['lon']:.6f}")
    out.append(f"  Alt     : {t['alt']:.1f} m")
    out.append(f"  Heading : {t['heading']*57.3:.0f}°")
    out.append(f""
)
    out.append(f"  {BOLD}TELEMETRY{RESET}")
    bat = t["battery"]
    if bat >= 0:
        bar = draw_bar(bat, 100)
        out.append(f"  Battery : {bar} {bat:.0f}%")
    out.append(f"  GPS Fix : {'3D' if t['fix_type'] >= 3 else '2D' if t['fix_type'] >= 2 else 'No Fix'}")
    out.append(f"  Sats    : {t['satellites']}")
    out.append(f""
)
    out.append(f"  {BOLD}COMMANDS{RESET}")
    out.append(f"  {GREEN}[1]{RESET} Arm & Takeoff  {GREEN}[3]{RESET} Land     {GREEN}[5]{RESET} Return Home")
    out.append(f"  {GREEN}[2]{RESET} Arm            {GREEN}[4]{RESET} Disarm   {GREEN}[6]{RESET} Set Speed")
    out.append(f"")
    out.append(f"  {YELLOW}[G]{RESET} Goto GPS       {YELLOW}[M]{RESET} Mission  {RED}[Q]{RESET} Quit")
    out.append(f""
)
    global last_cmd_result, last_cmd_time
    if last_cmd_result and time.time() - last_cmd_time < 5:
        out.append(f"  {last_cmd_result}")
    out.append(f"")
    out.append(f"  {DIM}Enter command: {RESET}")
    sys.stdout.write("".join(out))
    sys.stdout.flush()

def cmd(msg, ok=True):
    global last_cmd_result, last_cmd_time
    last_cmd_time = time.time()
    icon = f"{GREEN}✓{RESET}" if ok else f"{RED}✗{RESET}"
    last_cmd_result = f"  {icon} {msg}"

def console_thread():
    global running
    while running:
        draw_screen()
        time.sleep(0.5)

def main():
    global running
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    sys.stdout.write(HIDE)

    if len(sys.argv) > 1:
        host = sys.argv[1]
    else:
        host = "127.0.0.1"
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
    ui = threading.Thread(target=console_thread, daemon=True)
    ui.start()

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
                cmd("Shutting down...")
                break
            elif key == '1':
                cmd("Arming and taking off to 10m...")
                drone.arm()
                time.sleep(1)
                drone.takeoff(10)
                cmd("Takeoff command sent!")
            elif key == '2':
                drone.arm()
                cmd("Arm command sent!")
            elif key == '3':
                drone.land()
                cmd("Land command sent!")
            elif key == '4':
                drone.disarm()
                cmd("Disarm command sent!")
            elif key == '5':
                drone.rtl()
                cmd("Return to Launch sent!")
            elif key.lower() == 'g':
                cmd("Goto: Enter lat,lon,alt (e.g. -6.163,35.752,30)")
                print(f"{CLS}{BOLD}Goto Position{RESET}\nEnter: lat,lon,alt\n> ")
                sys.stdout.flush()
                try:
                    line = sys.stdin.readline().strip()
                    parts = line.split(",")
                    if len(parts) == 3:
                        lat, lon, alt = float(parts[0]), float(parts[1]), float(parts[2])
                        drone.goto_position(lat, lon, alt)
                        cmd(f"Going to {lat},{lon} at {alt}m")
                    else:
                        cmd("Invalid format. Use: lat,lon,alt", False)
                except:
                    cmd("Invalid input", False)
            elif key == '6':
                cmd("Enter speed (m/s): ")
                print(f"{CLS}{BOLD}Set Speed{RESET}\nEnter m/s\n> ")
                sys.stdout.flush()
                try:
                    speed = float(sys.stdin.readline().strip())
                    drone.set_speed(speed)
                    cmd(f"Speed set to {speed} m/s")
                except:
                    cmd("Invalid speed", False)

    except (EOFError, KeyboardInterrupt):
        pass
    finally:
        running = False
        drone.close()
        sys.stdout.write(f"\n{SHOW}")
        print(f"\n{GREEN}Console closed.{RESET}")

if __name__ == "__main__":
    main()
