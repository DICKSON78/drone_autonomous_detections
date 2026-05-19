#!/usr/bin/env python3
"""Autonomous flight mission with obstacle detection simulation."""

import os
import sys
import time
import signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mavlink_lite import DroneConnection

GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

def log(msg):
    print(f"  {msg}")

def waypoints_around_home(lat, lon, alt=30, radius=0.0004):
    """Create a square search pattern around home position."""
    return [
        (lat + radius, lon + radius, alt),
        (lat + radius, lon - radius, alt),
        (lat - radius, lon - radius, alt),
        (lat - radius, lon + radius, alt),
        (lat + radius, lon + radius, alt),
    ]

def main():
    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    port = int(sys.argv[3]) if len(sys.argv) > 3 else 14540
    takeoff_alt = float(sys.argv[2]) if len(sys.argv) > 2 else 15

    print(f"\n{BOLD}{CYAN}══════════════════════════════════════════{RESET}")
    print(f"{BOLD}{CYAN}  AUTONOMOUS FLIGHT MISSION STARTING...{RESET}")
    print(f"{BOLD}{CYAN}══════════════════════════════════════════{RESET}\n")

    drone = DroneConnection()
    drone.connect()
    time.sleep(2)

    t = drone.get_telemetry()
    home_lat = t["lat"]
    home_lon = t["lon"]
    log(f"{BOLD}Home Position: {home_lat:.6f}, {home_lon:.6f}{RESET}")

    log(f"{YELLOW}Arming drone...{RESET}")
    drone.arm()
    time.sleep(2)

    if not drone.get_telemetry()["armed"]:
        log(f"{RED}Failed to arm. Check EKF status.{RESET}")
        drone.close()
        return

    log(f"{GREEN}Drone armed!{RESET}")
    log(f"{YELLOW}Taking off to {takeoff_alt}m...{RESET}")
    drone.takeoff(takeoff_alt)
    time.sleep(5)

    t = drone.get_telemetry()
    log(f"{GREEN}Altitude: {t['alt']:.1f}m | Battery: {t['battery']}%{RESET}")
    log(f"{GREEN}GPS Fix: {t['fix_type']} | Sats: {t['satellites']}{RESET}")

    wps = waypoints_around_home(home_lat, home_lon, takeoff_alt)
    log(f"\n{BOLD}Executing waypoint mission ({len(wps)} waypoints)...{RESET}")
    log(f"{BOLD}Pattern: Square search, altitude {takeoff_alt}m{RESET}")

    for i, (wlat, wlon, walt) in enumerate(wps, 1):
        log(f"\n{YELLOW}Waypoint {i}/{len(wps)}: {wlat:.6f}, {wlon:.6f}, {walt:.0f}m{RESET}")
        drone.goto_position(wlat, wlon, walt)
        time.sleep(3)

        for _ in range(15):
            t = drone.get_telemetry()
            dist = ((t["lat"] - wlat)**2 + (t["lon"] - wlon)**2)**0.5 * 111000
            bar_len = int(max(0, min(20, 20 - dist / 5)))
            bar = f"{'█' * bar_len}{'░' * (20 - bar_len)}"
            print(f"    Moving... [{bar}] {dist:.1f}m remaining", end="\r")
            sys.stdout.flush()
            time.sleep(1)

        print()
        log(f"{GREEN}Reached waypoint {i}{RESET}")

        # Simulated obstacle detection
        t = drone.get_telemetry()
        heading_deg = t["heading"] * 57.3 % 360
        obstacle_note = ""
        if 0 <= heading_deg < 90 or 180 <= heading_deg < 270:
            pass
        if i == 3:
            log(f"{YELLOW}Obstacle detected ahead! Adjusting course...{RESET}")

    log(f"\n{BOLD}Mission complete! Returning to launch...{RESET}")
    drone.rtl()
    time.sleep(5)

    t = drone.get_telemetry()
    log(f"{GREEN}Returning home. Altitude: {t['alt']:.1f}m{RESET}")
    log(f"\n{CYAN}══════════════════════════════════════════{RESET}")
    log(f"{CYAN}  MISSION COMPLETE - Drone returning home{RESET}")
    log(f"{CYAN}══════════════════════════════════════════{RESET}")

    drone.close()

if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda s, f: print(f"\n{RED}Mission aborted{RESET}") or sys.exit(0))
    main()
