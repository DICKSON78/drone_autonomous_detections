#!/usr/bin/env python3
"""Mission Drone Controller — MAVLink-based autonomous flight control."""

import os, sys, time, json, signal, yaml
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mavlink_lite import DroneConnection

GREEN = "\033[92m"; YELLOW = "\033[93m"; RED = "\033[91m"
CYAN = "\033[96m"; BOLD = "\033[1m"; DIM = "\033[2m"
RESET = "\033[0m"

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "config", "mission_drone_config.yaml")

CONFIG = {
    "drone": {"mass": 1.5, "max_speed": 20, "cruise_speed": 8},
    "flight": {"default_altitude": 25, "hover_time_at_waypoint": 2.0,
               "waypoint_acceptance_radius": 1.0},
    "mission": {"enable_return_to_home": True, "low_battery_threshold": 15,
                "auto_land_on_battery_critical": True, "battery_critical_threshold": 5},
    "safety": {"geofence_radius": 500, "max_altitude": 100},
}

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH) as f:
                user_cfg = yaml.safe_load(f) or {}
            for section in CONFIG:
                if section in user_cfg and isinstance(user_cfg[section], dict):
                    CONFIG[section].update(user_cfg[section])
        except Exception as e:
            print(f"  {YELLOW}[WARN] Config load failed: {e}{RESET}")

load_config()

SURVEILLANCE_WAYPOINTS = [
    [0, 0, CONFIG["flight"]["default_altitude"]],
    [50, 0, CONFIG["flight"]["default_altitude"]],
    [50, 50, CONFIG["flight"]["default_altitude"]],
    [0, 50, CONFIG["flight"]["default_altitude"]],
    [-50, 50, CONFIG["flight"]["default_altitude"]],
    [-50, 0, CONFIG["flight"]["default_altitude"]],
    [-50, -50, CONFIG["flight"]["default_altitude"]],
    [0, -50, CONFIG["flight"]["default_altitude"]],
    [50, -50, CONFIG["flight"]["default_altitude"]],
    [0, 0, CONFIG["flight"]["default_altitude"]],
]

class DroneState:
    DISARMED = 0; ARMED = 1; FLYING = 2; HOVERING = 3
    LANDING = 4; RETURNING_HOME = 5; MISSION_COMPLETE = 6

STATE_NAMES = {0: "DISARMED", 1: "ARMED", 2: "FLYING", 3: "HOVERING",
               4: "LANDING", 5: "RETURNING_HOME", 6: "MISSION COMPLETE"}

class MissionDrone:
    def __init__(self, host="127.0.0.1", port=14550):
        self.host = host
        self.port = port
        self.drone = None
        self.state = DroneState.DISARMED
        self.home_position = None
        self.current_waypoint_idx = 0
        self.waypoints = []
        self.mission_active = False
        self.running = True
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _handle_signal(self, sig, frame):
        print(f"\n  {YELLOW}Shutting down...{RESET}")
        self.running = False
        if self.drone:
            self.drone.close()
        sys.exit(0)

    def connect(self):
        self.drone = DroneConnection((self.host, self.port))
        self.drone.connect()
        print(f"  Connecting to drone at {self.host}:{self.port}...")
        for i in range(10):
            t = self.drone.get_telemetry()
            if t["connected"]:
                print(f"  {GREEN}Connected!{RESET}")
                return True
            time.sleep(1)
        print(f"  {RED}Connection timeout{RESET}")
        return False

    def get_telemetry(self):
        if not self.drone:
            return None
        t = self.drone.get_telemetry()
        t["state"] = self.state
        t["state_name"] = STATE_NAMES.get(self.state, "UNKNOWN")
        return t

    def arm(self):
        if self.state != DroneState.DISARMED:
            return True
        if not self.drone:
            return False
        self.drone.arm()
        for i in range(5):
            time.sleep(1)
            t = self.drone.get_telemetry()
            if t["armed"]:
                self.state = DroneState.ARMED
                print(f"  {GREEN}Drone ARMED ✓{RESET}")
                return True
        print(f"  {RED}Arm command sent but not confirmed{RESET}")
        return False

    def disarm(self):
        if not self.drone:
            return False
        self.drone.disarm()
        self.state = DroneState.DISARMED
        print(f"  Drone disarmed")
        return True

    def takeoff(self, altitude=None):
        if altitude is None:
            altitude = CONFIG["flight"]["default_altitude"]
        if not self.drone:
            return False
        self.arm()
        print(f"  Taking off to {altitude}m...")
        self.drone.takeoff(altitude)
        self.state = DroneState.FLYING
        for i in range(15):
            time.sleep(1.5)
            t = self.drone.get_telemetry()
            print(f"  Altitude: {t['alt']:.1f}m")
            if t["alt"] >= altitude * 0.8:
                print(f"  {GREEN}Reached {altitude}m ✓{RESET}")
                return True
        return True

    def land(self):
        if not self.drone:
            return False
        self.state = DroneState.LANDING
        print(f"  Landing...")
        self.drone.land()
        for i in range(15):
            time.sleep(1)
            t = self.drone.get_telemetry()
            print(f"  Altitude: {t['alt']:.1f}m")
            if t["alt"] < 1:
                print(f"  {GREEN}Landed ✓{RESET}")
                self.state = DroneState.DISARMED
                return True
        return True

    def return_to_home(self):
        if not self.drone or not self.home_position:
            return False
        self.state = DroneState.RETURNING_HOME
        print(f"  Returning to home...")
        self.drone.goto_position(
            self.home_position[0], self.home_position[1], self.home_position[2])
        for i in range(30):
            time.sleep(1)
            t = self.drone.get_telemetry()
            lat_dist = (t["lat"] - self.home_position[0]) * 111000
            lon_dist = (t["lon"] - self.home_position[1]) * 111000 * np.cos(np.radians(t["lat"]))
            dist = np.sqrt(lat_dist**2 + lon_dist**2)
            print(f"  Distance to home: {dist:.1f}m")
            if dist < 3:
                print(f"  {GREEN}At home position ✓{RESET}")
                return True
        return True

    def go_to_waypoint(self, waypoint):
        if not self.drone:
            return False
        local_x, local_y, alt = waypoint
        t = self.drone.get_telemetry()
        home_lat, home_lon = self.home_position[0], self.home_position[1]
        lat_offset = local_y / 111000
        lon_offset = local_x / (111000 * np.cos(np.radians(home_lat)))
        target_lat = home_lat + lat_offset
        target_lon = home_lon + lon_offset
        print(f"  Going to waypoint ({local_x:.0f}, {local_y:.0f}, {alt:.0f}m)...")
        self.drone.goto_position(target_lat, target_lon, alt)
        acceptance = CONFIG["flight"]["waypoint_acceptance_radius"]
        for i in range(30):
            time.sleep(1.5)
            t = self.drone.get_telemetry()
            lat_dist = (t["lat"] - target_lat) * 111000
            lon_dist = (t["lon"] - target_lon) * 111000 * np.cos(np.radians(t["lat"]))
            dist = np.sqrt(lat_dist**2 + lon_dist**2)
            alt_diff = abs(t["alt"] - alt)
            print(f"  Distance: {dist:.1f}m, Alt diff: {alt_diff:.1f}m")
            if dist < acceptance and alt_diff < 3:
                print(f"  {GREEN}Waypoint reached ✓{RESET}")
                return True
            if not self.running:
                return False
        print(f"  {YELLOW}Waypoint timeout, continuing...{RESET}")
        return True

    def execute_mission(self, waypoints=None):
        if waypoints is None:
            waypoints = SURVEILLANCE_WAYPOINTS
        self.waypoints = waypoints
        self.mission_active = True
        t = self.drone.get_telemetry()
        self.home_position = (t["lat"], t["lon"], t["alt"])
        print(f"\n  {CYAN}{BOLD}Starting mission with {len(waypoints)} waypoints{RESET}")
        print(f"  Home: {self.home_position[0]:.6f}, {self.home_position[1]:.6f}\n")
        self.takeoff()
        self.state = DroneState.FLYING
        for idx, wp in enumerate(waypoints[1:], 1):
            if not self.running:
                break
            self.current_waypoint_idx = idx
            print(f"\n  {BOLD}Waypoint {idx}/{len(waypoints)-1}{RESET}")
            self.go_to_waypoint(wp)
            self.state = DroneState.HOVERING
            hover_time = CONFIG["flight"]["hover_time_at_waypoint"]
            for _ in range(int(hover_time)):
                if not self.running:
                    break
                time.sleep(1)
            self.state = DroneState.FLYING
            battery = self.drone.get_telemetry().get("battery", 100)
            if battery >= 0 and battery < CONFIG["mission"]["low_battery_threshold"]:
                print(f"\n  {RED}{BOLD}Low battery ({battery}%)! Returning home{RESET}")
                break
        if CONFIG["mission"]["enable_return_to_home"]:
            self.return_to_home()
            self.land()
        self.state = DroneState.MISSION_COMPLETE
        self.mission_active = False
        print(f"\n  {GREEN}{BOLD}Mission complete! ✓{RESET}")

    def hover(self, duration=5):
        self.state = DroneState.HOVERING
        print(f"  Hovering for {duration}s...")
        for i in range(int(duration)):
            if not self.running:
                break
            t = self.drone.get_telemetry()
            print(f"  Hovering... Alt: {t['alt']:.1f}m")
            time.sleep(1)
        self.state = DroneState.FLYING

    def close(self):
        if self.drone:
            self.drone.close()

    def print_status(self):
        t = self.drone.get_telemetry()
        armed = f"{GREEN}ARMED{RESET}" if t["armed"] else f"{YELLOW}DISARMED{RESET}"
        print(f"\n  {CYAN}{BOLD}┌─ Drone Status ─────────────────────┐{RESET}")
        print(f"  {CYAN}│{RESET}  State:  {STATE_NAMES.get(self.state, '?')}")
        print(f"  {CYAN}│{RESET}  Armed:  {armed}")
        print(f"  {CYAN}│{RESET}  Mode:   {t['mode']}")
        print(f"  {CYAN}│{RESET}  Alt:    {t['alt']:.1f}m")
        print(f"  {CYAN}│{RESET}  Bat:    {t['battery']}%")
        print(f"  {CYAN}│{RESET}  GPS:    {t['lat']:.4f}, {t['lon']:.4f}")
        print(f"  {CYAN}│{RESET}  Speed:  {t.get('vel_x', 0):.1f} m/s")
        print(f"  {CYAN}│{RESET}  WP:     {self.current_waypoint_idx}/{len(self.waypoints)-1 if self.waypoints else 0}")
        print(f"  {CYAN}└────────────────────────────────────────┘{RESET}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Mission Drone Controller")
    parser.add_argument("host", nargs="?", default="127.0.0.1", help="Drone UDP host")
    parser.add_argument("port", nargs="?", type=int, default=14550, help="Drone UDP port")
    parser.add_argument("--alt", type=float, default=None, help="Takeoff altitude")
    parser.add_argument("--mission", action="store_true", help="Run surveillance mission")
    args = parser.parse_args()

    drone = MissionDrone(args.host, args.port)
    if not drone.connect():
        sys.exit(1)

    if args.mission:
        if args.alt:
            CONFIG["flight"]["default_altitude"] = args.alt
            SURVEILLANCE_WAYPOINTS[0][2] = args.alt
            for wp in SURVEILLANCE_WAYPOINTS:
                wp[2] = args.alt
        print(f"\n  {CYAN}{BOLD}╔══════════════════════════════════════╗{RESET}")
        print(f"  {CYAN}{BOLD}║   SURVEILLANCE MISSION STARTING...  ║{RESET}")
        print(f"  {CYAN}{BOLD}╚══════════════════════════════════════╝{RESET}\n")
        drone.execute_mission()
    else:
        print(f"  {YELLOW}Connected. Use --mission to start auto mission.{RESET}")
        drone.print_status()
        drone.close()

if __name__ == "__main__":
    main()
