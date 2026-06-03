#!/usr/bin/env python3
"""
PC4 — Drone Terminal CLI
Interactive terminal to control the drone via REST API (PC1) or direct MAVLink.
Integrates with PC4 TTS for audio feedback.

Usage:
  python drone_cli.py                          # Interactive mode (REST API)
  python drone_cli.py --mavlink 192.168.1.12   # Direct MAVLink mode
  python drone_cli.py --cmd "takeoff 10"       # Single command mode
  python drone_cli.py --cmd "fly to base"      # Single NLP command
"""

import argparse
import json
import math
import os
import random
import re
import signal
import sys
import threading
import time
from datetime import datetime
from typing import Optional

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'PC2', 'scripts'))
try:
    from mavlink_lite import DroneConnection
    HAS_MAVLINK = True
except ImportError:
    HAS_MAVLINK = False

RED = "\033[91m"; GREEN = "\033[92m"; YELLOW = "\033[93m"
BLUE = "\033[94m"; CYAN = "\033[96m"; MAGENTA = "\033[95m"
BOLD = "\033[1m"; DIM = "\033[2m"; RESET = "\033[0m"
CLS = "\033[2J\033[H"; HIDE = "\033[?25l"; SHOW = "\033[?25h"

# ── Dodoma landmarks ──────────────────────────────────────────────────────────
KNOWN_LOCATIONS = {
    "base":       (-6.1629, 35.7516, 1120), "home":      (-6.1629, 35.7516, 1120),
    "bunge":      (-6.1610, 35.7528, 1120), "parliament":(-6.1610, 35.7528, 1120),
    "hospital":   (-6.1645, 35.7500, 1120), "market":    (-6.1635, 35.7505, 1120),
    "bank":       (-6.1635, 35.7510, 1120), "mall":      (-6.1625, 35.7500, 1120),
    "park":       (-6.1630, 35.7520, 1120), "garden":    (-6.1630, 35.7520, 1120),
    "forest":     (-6.1600, 35.7550, 1120), "river":     (-6.1650, 35.7490, 1120),
    "roundabout": (-6.1629, 35.7516, 1120), "center":    (-6.1629, 35.7516, 1120),
    "university": (-6.1580, 35.7600, 1120), "airport":   (-6.1780, 35.7550, 1120),
}


class Telemetry:
    def __init__(self):
        self.connected = False
        self.armed = False
        self.lat = -6.1629
        self.lon = 35.7516
        self.alt = 0.0
        self.heading = 0.0
        self.battery = 95.0
        self.fix_type = 3
        self.satellites = 10
        self.mode = "STABILIZED"
        self.roll = 0.0
        self.pitch = 0.0
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.vel_z = 0.0


class DroneCLI:
    def __init__(self, args):
        self.args = args
        self.running = True
        self.last_msg = ""
        self.last_msg_time = 0
        self.cmd_history: list[str] = []
        self.mav: Optional[DroneConnection] = None
        self.telemetry = Telemetry()
        self.host = args.host
        self.port = args.port
        self.rest_api = f"http://{args.api_host}:{args.api_port}"
        self.tts_api = f"http://{args.tts_host}:{args.tts_port}"
        self.in_air = False

    # ── Messaging ─────────────────────────────────────────────────────────────

    def log(self, text: str, ok: bool = True):
        self.last_msg_time = time.time()
        icon = f"{GREEN}\u2713{RESET}" if ok else f"{RED}\u2717{RESET}"
        self.last_msg = f"  {icon} {text}"

    def say(self, text: str, priority: str = "normal"):
        if not HAS_REQUESTS:
            return
        try:
            requests.post(
                f"{self.tts_api}/speak",
                json={"message": text, "priority": priority},
                timeout=3,
            )
        except Exception:
            pass

    # ── REST API mode ─────────────────────────────────────────────────────────

    def _api_post(self, endpoint: str, data: dict) -> dict:
        if not HAS_REQUESTS:
            return {"error": "requests module not available"}
        try:
            r = requests.post(f"{self.rest_api}{endpoint}", json=data, timeout=10)
            return r.json() if r.ok else {"error": r.text}
        except requests.ConnectionError:
            return {"error": f"Cannot connect to {self.rest_api}"}
        except Exception as e:
            return {"error": str(e)}

    def _api_get(self, endpoint: str) -> dict:
        if not HAS_REQUESTS:
            return {"error": "requests module not available"}
        try:
            r = requests.get(f"{self.rest_api}{endpoint}", timeout=5)
            return r.json() if r.ok else {"error": r.text}
        except Exception:
            return {"error": "connection failed"}

    def rest_send_command(self, text: str) -> dict:
        data = {"text": text, "user_id": "pc4-cli"}
        result = self._api_post("/parse-command", data)
        if "error" in result:
            result = self._api_post("/parse", {"text": text})
        return result

    def rest_get_status(self) -> dict:
        return self._api_get("/status")

    # ── Demo mode ─────────────────────────────────────────────────────────────

    def _demo_connect(self) -> bool:
        self.telemetry.connected = True
        self.log(f"DEMO mode — simulated drone at {self.host}:{self.port}")
        threading.Thread(target=self._demo_telemetry_loop, daemon=True).start()
        return True

    def _demo_telemetry_loop(self):
        while self.running:
            t = self.telemetry
            if t.connected and t.armed and not self.in_air:
                self.in_air = True
                t.alt = 1.0
                t.mode = "AUTO.TAKEOFF"
            if self.in_air:
                t.alt = min(t.alt + 0.3, 15.0)
                if t.alt >= 14.9 and t.mode == "AUTO.TAKEOFF":
                    t.mode = "AUTO"
            time.sleep(0.3)

    def _demo_execute(self, action: tuple):
        cmd = action[0]
        t = self.telemetry
        if cmd == "takeoff":
            t.armed = True
            self.in_air = True
            t.alt = 1.0
            t.mode = "AUTO.TAKEOFF"
            self.log(f"DEMO takeoff to {action[1] if len(action)>1 else 15}m")
            self.say("Taking off")
        elif cmd == "land":
            t.alt = 0.0
            self.in_air = False
            t.armed = False
            t.mode = "STABILIZED"
            self.log("DEMO landing")
            self.say("Landing")
        elif cmd == "arm":
            t.armed = True
            self.log("DEMO armed")
        elif cmd == "disarm":
            t.armed = False
            self.log("DEMO disarmed")
        elif cmd == "rtl":
            t.lat, t.lon = -6.1629, 35.7516
            t.alt = 0.0
            self.in_air = False
            self.log("DEMO returning to launch")
            self.say("Returning to base")
        elif cmd == "goto":
            t.lat, t.lon = action[1], action[2]
            t.alt = action[3] if len(action) > 3 else 30
            self.log(f"DEMO going to {action[1]:.4f}, {action[2]:.4f}")
            self.say("Navigating to destination")
        elif cmd in ("forward", "backward", "left", "right"):
            d = action[1] if len(action) > 1 else 10
            heading = {"forward": 0, "backward": math.pi, "left": -math.pi/2, "right": math.pi/2}[cmd]
            t.lat += (d * math.cos(heading + t.heading)) / 111320 + random.uniform(-0.00001, 0.00001)
            t.lon += (d * math.sin(heading + t.heading)) / (111320 * math.cos(math.radians(t.lat))) + random.uniform(-0.00001, 0.00001)
            self.log(f"DEMO moving {cmd} {d}m")
        elif cmd == "climb":
            t.alt += action[1] if len(action) > 1 else 10
            self.log(f"DEMO climbing")
        elif cmd == "descend":
            t.alt = max(0, t.alt - (action[1] if len(action) > 1 else 5))
            self.log(f"DEMO descending")
        elif cmd == "speed":
            self.log(f"DEMO speed set to {action[1]} m/s")
        elif cmd == "hover":
            self.log("DEMO hovering")
        elif cmd == "emergency":
            t.alt = 0.0
            self.in_air = False
            t.armed = False
            self.log("DEMO EMERGENCY landing!")
            self.say("Emergency landing", "emergency")

    # ── MAVLink mode ──────────────────────────────────────────────────────────

    def mavlink_connect(self) -> bool:
        if not HAS_MAVLINK:
            self.log("mavlink_lite not found -- install or use --api mode", False)
            return False
        self.mav = DroneConnection(udp_target=(self.host, self.port))
        try:
            self.mav.connect()
            time.sleep(1)
            self.log(f"MAVLink connected to {self.host}:{self.port}")
            return True
        except Exception as e:
            self.log(f"MAVLink failed: {e}", False)
            self.mav = None
            return False

    def mavlink_command(self, cmd: str, *args):
        if not self.mav:
            self.log("Not connected", False)
            return
        try:
            if cmd == "takeoff":
                alt = args[0] if args else 10
                self.mav.arm(); time.sleep(0.5)
                self.mav.takeoff(alt)
                self.log(f"Takeoff to {alt}m")
                self.say(f"Taking off to {alt} meters")
            elif cmd == "land":
                self.mav.land()
                self.log("Landing")
                self.say("Landing")
            elif cmd == "arm":
                self.mav.arm()
                self.log("Armed")
            elif cmd == "disarm":
                self.mav.disarm()
                self.log("Disarmed")
            elif cmd == "rtl":
                self.mav.rtl()
                self.log("Returning to launch")
                self.say("Returning to launch")
            elif cmd == "speed":
                s = args[0] if args else 10
                self.mav.set_speed(s)
                self.log(f"Speed set to {s} m/s")
            elif cmd == "goto":
                lat, lon, alt = args[0], args[1], args[2] if len(args) > 2 else 30
                self.mav.goto_position(lat, lon, alt)
                self.log(f"Going to {lat:.4f}, {lon:.4f} at {alt}m")
                self.say(f"Navigating to destination")
            elif cmd == "climb":
                t = self.mav.get_telemetry()
                d = args[0] if args else 10
                self.mav.goto_position(t["lat"], t["lon"], t["alt"] + d)
                self.log(f"Climbing {d}m")
            elif cmd == "descend":
                t = self.mav.get_telemetry()
                d = args[0] if args else 5
                target = max(2, t["alt"] - d)
                self.mav.goto_position(t["lat"], t["lon"], target)
                self.log(f"Descending {d}m")
            elif cmd == "forward":
                t = self.mav.get_telemetry()
                d = args[0] if args else 20
                h = t["heading"]
                lat = t["lat"] + (d * math.cos(h)) / 111320
                lon = t["lon"] + (d * math.sin(h)) / (111320 * math.cos(math.radians(t["lat"])))
                self.mav.goto_position(lat, lon, t["alt"])
                self.log(f"Moving forward {d}m")
            elif cmd == "backward":
                t = self.mav.get_telemetry()
                d = args[0] if args else 20
                h = t["heading"] + math.pi
                lat = t["lat"] + (d * math.cos(h)) / 111320
                lon = t["lon"] + (d * math.sin(h)) / (111320 * math.cos(math.radians(t["lat"])))
                self.mav.goto_position(lat, lon, t["alt"])
                self.log(f"Moving backward {d}m")
            elif cmd == "left":
                t = self.mav.get_telemetry()
                d = args[0] if args else 10
                h = t["heading"] - math.pi / 2
                lat = t["lat"] + (d * math.cos(h)) / 111320
                lon = t["lon"] + (d * math.sin(h)) / (111320 * math.cos(math.radians(t["lat"])))
                self.mav.goto_position(lat, lon, t["alt"])
                self.log(f"Moving left {d}m")
            elif cmd == "right":
                t = self.mav.get_telemetry()
                d = args[0] if args else 10
                h = t["heading"] + math.pi / 2
                lat = t["lat"] + (d * math.cos(h)) / 111320
                lon = t["lon"] + (d * math.sin(h)) / (111320 * math.cos(math.radians(t["lat"])))
                self.mav.goto_position(lat, lon, t["alt"])
                self.log(f"Moving right {d}m")
            else:
                self.log(f"Unknown MAVLink command: {cmd}", False)
        except Exception as e:
            self.log(f"Command error: {e}", False)

    # ── NLP parsing ───────────────────────────────────────────────────────────

    def parse_command(self, text: str) -> Optional[tuple]:
        text_lower = text.lower().strip()
        if not text_lower:
            return None

        nums = [float(n) for n in re.findall(r"\d+\.?\d*", text_lower)]
        alt = 0; speed = 0; distance = 0
        for n in nums:
            if n < 500:
                if "speed" in text_lower or "fast" in text_lower:
                    speed = n
                elif "alt" in text_lower or "height" in text_lower or "climb" in text_lower or "descend" in text_lower:
                    alt = n
                elif "meter" in text_lower or "metre" in text_lower:
                    distance = n
                else:
                    alt = n

        def find_location(t):
            for name, loc in KNOWN_LOCATIONS.items():
                if name in t:
                    return loc
            gps = re.findall(r"-?\d+\.\d+", t)
            if len(gps) >= 2:
                a = float(gps[2]) if len(gps) >= 3 else 30
                return (float(gps[0]), float(gps[1]), a)
            return None

        if any(w in text_lower for w in ["emergency", "kill", "stop now"]):
            return ("emergency",)
        if any(w in text_lower for w in ["takeoff", "take off", "take-off", "launch"]):
            a = alt or distance or 15
            return ("takeoff", a)
        if any(w in text_lower for w in ["land", "come down", "touch down"]):
            return ("land",)
        if any(w in text_lower for w in ["return home", "return to base", "go home", "rtl", "come back"]):
            return ("rtl",)
        if text_lower in ("disarm", "shut down", "power off"):
            return ("disarm",)
        if any(w in text_lower for w in ["arm"]):
            return ("arm",)
        if any(w in text_lower for w in ["speed", "faster", "slower"]):
            return ("speed", speed if speed > 0 else 10)
        if any(w in text_lower for w in ["hover", "hold", "stop", "pause"]):
            return ("hover",)
        if any(w in text_lower for w in ["climb", "ascend", "go up"]):
            return ("climb", alt if alt > 0 else 10)
        if any(w in text_lower for w in ["descend", "go down", "lower"]):
            return ("descend", alt if alt > 0 else 5)
        if any(w in text_lower for w in ["forward", "ahead"]):
            return ("forward", distance if distance > 0 else 20)
        if any(w in text_lower for w in ["backward", "back", "reverse"]):
            return ("backward", distance if distance > 0 else 20)
        if any(w in text_lower for w in ["left"]) and "right" not in text_lower:
            return ("left", distance if distance > 0 else 10)
        if any(w in text_lower for w in ["right"]) and "left" not in text_lower:
            return ("right", distance if distance > 0 else 10)

        loc = find_location(text_lower)
        if loc:
            return ("goto", loc[0], loc[1], loc[2])

        if "fly to" in text_lower or "go to" in text_lower or "navigate" in text_lower:
            return ("goto", -6.1629, 35.7516, alt if alt > 0 else 30)

        return None

    # ── Execute command ───────────────────────────────────────────────────────

    def execute(self, action: tuple):
        if not action:
            self.log("Command not understood. Try: takeoff 10, land, fly to base", False)
            return

        cmd = action[0]
        if self.args.demo:
            self._demo_execute(action)
        elif self.args.mavlink:
            self.mavlink_command(cmd, *action[1:])
        else:
            self._rest_execute(action)

    def _rest_execute(self, action: tuple):
        cmd = action[0]
        if cmd == "takeoff":
            alt = action[1] if len(action) > 1 else 15
            self.rest_send_command(f"takeoff to {alt} meters")
            self.log(f"Takeoff to {alt}m")
            self.say(f"Taking off to {alt} meters")
        elif cmd == "land":
            self.rest_send_command("land")
            self.log("Landing")
            self.say("Landing")
        elif cmd == "rtl":
            self.rest_send_command("return to launch")
            self.log("Returning to launch")
            self.say("Returning to launch")
        elif cmd == "arm":
            self.rest_send_command("arm")
            self.log("Armed")
        elif cmd == "disarm":
            self.rest_send_command("disarm")
            self.log("Disarmed")
        elif cmd == "forward":
            d = action[1] if len(action) > 1 else 20
            self.rest_send_command(f"go forward {d} meters")
            self.log(f"Moving forward {d}m")
        elif cmd == "backward":
            d = action[1] if len(action) > 1 else 20
            self.rest_send_command(f"go back {d} meters")
            self.log(f"Moving backward {d}m")
        elif cmd == "left":
            d = action[1] if len(action) > 1 else 10
            self.rest_send_command(f"go left {d} meters")
            self.log(f"Moving left {d}m")
        elif cmd == "right":
            d = action[1] if len(action) > 1 else 10
            self.rest_send_command(f"go right {d} meters")
            self.log(f"Moving right {d}m")
        elif cmd == "climb":
            d = action[1] if len(action) > 1 else 10
            self.rest_send_command(f"climb to altitude {d} meters")
            self.log(f"Climbing {d}m")
        elif cmd == "descend":
            d = action[1] if len(action) > 1 else 5
            self.rest_send_command(f"descend {d} meters")
            self.log(f"Descending {d}m")
        elif cmd == "speed":
            s = action[1] if len(action) > 1 else 10
            self.rest_send_command(f"set speed to {s}")
            self.log(f"Speed set to {s} m/s")
        elif cmd == "goto":
            lat, lon = action[1], action[2]
            a = action[3] if len(action) > 3 else 30
            self.rest_send_command(f"fly to {lat}, {lon} at {a} meters")
            self.log(f"Going to {lat:.4f}, {lon:.4f} at {a}m")
            self.say(f"Navigating to destination")
        elif cmd == "hover":
            self.rest_send_command("hover")
            self.log("Hovering")
        elif cmd == "emergency":
            self.rest_send_command("emergency land")
            self.log("EMERGENCY - Landing!")
            self.say("Emergency landing", "emergency")
        else:
            self.log(f"Unknown command: {cmd}", False)

    # ── Display ───────────────────────────────────────────────────────────────

    def _draw_bar(self, value: float, max_val: float, width: int = 20) -> str:
        filled = max(0, min(width, int(value / max_val * width))) if max_val > 0 else 0
        bar = "\u2588" * filled + "\u2591" * (width - filled)
        color = RED if value < 30 else YELLOW if value < 60 else GREEN
        return f"{color}{bar}{RESET}"

    def _read_telemetry(self):
        if self.args.demo:
            return self.telemetry
        if self.args.mavlink and self.mav:
            t = self.mav.get_telemetry()
            self.telemetry.connected = t["connected"]
            self.telemetry.armed = t["armed"]
            self.telemetry.lat = t["lat"]
            self.telemetry.lon = t["lon"]
            self.telemetry.alt = t["alt"]
            self.telemetry.heading = t["heading"]
            self.telemetry.battery = t["battery"]
            self.telemetry.fix_type = t["fix_type"]
            self.telemetry.satellites = t["satellites"]
            self.telemetry.mode = t["mode"]
            self.telemetry.roll = t["roll"]
            self.telemetry.pitch = t["pitch"]
            return self.telemetry
        if not self.args.mavlink:
            status = self.rest_get_status()
            if "latitude" in status:
                self.telemetry.connected = True
                self.telemetry.lat = status.get("latitude", self.telemetry.lat)
                self.telemetry.lon = status.get("longitude", self.telemetry.lon)
                self.telemetry.alt = status.get("altitude", self.telemetry.alt)
                self.telemetry.armed = status.get("armed", False)
                if "battery" in status:
                    self.telemetry.battery = status.get("battery", 95)
        return self.telemetry

    def draw_screen(self):
        out = [CLS]
        if self.args.demo:
            mode_str = f"{YELLOW}DEMO{RESET}"
        elif self.args.mavlink:
            mode_str = f"{MAGENTA}MAVLink{RESET}"
        else:
            mode_str = f"{BLUE}REST API{RESET}"
        out.append(f"{BOLD}{CYAN}\u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557{RESET}\n")
        out.append(f"{BOLD}{CYAN}\u2551          DRONE TERMINAL CLI  ({mode_str})          \u2551{RESET}\n")
        out.append(f"{BOLD}{CYAN}\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255b{RESET}\n")

        t = self._read_telemetry()
        status = f"{GREEN}\u25cf CONNECTED{RESET}" if t.connected else f"{RED}\u25cb DISCONNECTED{RESET}"
        armed = f"{GREEN}\u25cf ARMED{RESET}" if t.armed else f"{YELLOW}\u25cb DISARMED{RESET}"
        air = f"{GREEN}\u25cf IN AIR{RESET}" if self.in_air else f"{DIM}\u25cb ON GROUND{RESET}"
        out.append(f"  {BOLD}Status:{RESET}   {status}  |  {armed}  |  {air}  |  {BOLD}{t.mode}{RESET}\n")
        out.append(f"  {BOLD}Position:{RESET}  {t.lat:.6f}, {t.lon:.6f}\n")
        out.append(f"  {BOLD}Altitude:{RESET}  {t.alt:.1f} m     {BOLD}Heading:{RESET} {t.heading*57.3:.0f}\u00b0\n")
        if t.battery >= 0:
            bar = self._draw_bar(t.battery, 100)
            out.append(f"  {BOLD}Battery:{RESET}  {bar} {t.battery:.0f}%\n")
        out.append(f"  {BOLD}GPS:{RESET}      {'3D' if t.fix_type >= 3 else '2D' if t.fix_type >= 2 else 'No Fix'}  |  {t.satellites} sats\n")

        out.append(f"\n")
        if self.last_msg and time.time() - self.last_msg_time < 8:
            out.append(f"  {self.last_msg}\n\n")

        out.append(f"  {BOLD}{CYAN}Commands:{RESET}\n")
        out.append(f"    {GREEN}takeoff [alt]{RESET}   {GREEN}land{RESET}           {GREEN}rtl{RESET}\n")
        out.append(f"    {GREEN}forward <m>{RESET}     {GREEN}back <m>{RESET}       {GREEN}left/right <m>{RESET}\n")
        out.append(f"    {GREEN}climb <m>{RESET}       {GREEN}descend <m>{RESET}    {GREEN}speed <m/s>{RESET}\n")
        out.append(f"    {GREEN}goto <lat> <lon>{RESET}                           {GREEN}arm/disarm{RESET}\n")
        out.append(f"    {YELLOW}\"fly to bunge\"{RESET}   {YELLOW}\"take off to 20m\"{RESET}   {YELLOW}\"go forward 30\"{RESET}\n")
        out.append(f"  {DIM}Known locations:{RESET} " + ", ".join(sorted(KNOWN_LOCATIONS.keys())) + "\n")
        out.append(f"\n")
        out.append(f"  {BOLD}> {RESET}")
        sys.stdout.write("".join(out))
        sys.stdout.flush()

    # ── Interactive mode ──────────────────────────────────────────────────────

    def _interactive_loop(self):
        signal.signal(signal.SIGINT, lambda s, f: self._shutdown())
        sys.stdout.write(HIDE)
        time.sleep(0.5)

        if self.args.demo:
            self._demo_connect()
        elif self.args.mavlink:
            self.mavlink_connect()

        ui = threading.Thread(target=self._ui_refresh, daemon=True)
        ui.start()
        time.sleep(0.5)

        try:
            while self.running:
                self.draw_screen()
                try:
                    line = sys.stdin.readline().strip()
                except (EOFError, KeyboardInterrupt):
                    break
                if not line:
                    continue
                if line.lower() in ("quit", "exit", "q"):
                    break
                if line.lower() in ("help", "h", "?"):
                    self._show_help()
                    time.sleep(2)
                    continue
                if line.lower() in ("status", "st"):
                    continue
                if line.lower().startswith("say "):
                    msg_text = line[4:]
                    self.say(msg_text)
                    self.log(f"TTS: {msg_text}")
                    continue

                self.cmd_history.append(line)
                action = self.parse_command(line)
                if action:
                    self.execute(action)
                else:
                    self.log("Command not understood. Type 'help'.", False)
        except Exception:
            pass
        finally:
            self._shutdown()

    def _ui_refresh(self):
        while self.running:
            if self.args.mavlink and self.mav:
                pass
            time.sleep(1.0)

    def _show_help(self):
        sys.stdout.write(f"{CLS}")
        sys.stdout.write(f"{BOLD}{CYAN}DRONE CLI HELP{RESET}\n\n")
        sys.stdout.write(f"{BOLD}STRUCTURED COMMANDS:{RESET}\n")
        sys.stdout.write(f"  takeoff [alt]   \u2014 Arm and take off (default 15m)\n")
        sys.stdout.write(f"  land            \u2014 Land at current position\n")
        sys.stdout.write(f"  rtl / return    \u2014 Return to launch point\n")
        sys.stdout.write(f"  arm / disarm    \u2014 Arm or disarm motors\n")
        sys.stdout.write(f"  forward <m>     \u2014 Move forward N meters\n")
        sys.stdout.write(f"  back <m>        \u2014 Move backward N meters\n")
        sys.stdout.write(f"  left / right <m>\u2014 Move laterally N meters\n")
        sys.stdout.write(f"  climb / descend <m> \u2014 Change altitude\n")
        sys.stdout.write(f"  speed <m/s>     \u2014 Set cruise speed\n")
        sys.stdout.write(f"  goto <lat> <lon> [alt] \u2014 Fly to GPS coordinate\n")
        sys.stdout.write(f"  hover / stop    \u2014 Hold position\n")
        sys.stdout.write(f"  emergency       \u2014 Land immediately\n")
        sys.stdout.write(f"  say <text>      \u2014 Speak via TTS\n\n")
        sys.stdout.write(f"{BOLD}NATURAL LANGUAGE:{RESET}\n")
        sys.stdout.write(f"  \"take off to 20 meters\"\n")
        sys.stdout.write(f"  \"fly to bunge parliament\"\n")
        sys.stdout.write(f"  \"go forward 30 meters\"\n")
        sys.stdout.write(f"  \"return to base\"\n")
        sys.stdout.write(f"  \"climb to 50 meters\"\n")
        sys.stdout.write(f"  \"go to -6.161, 35.753 at 40m\"\n\n")
        sys.stdout.write(f"{BOLD}MODE:{RESET} ")
        if self.args.mavlink:
            sys.stdout.write(f"Direct MAVLink to {self.host}:{self.port}\n")
        else:
            sys.stdout.write(f"REST API at {self.rest_api}\n")
        sys.stdout.write(f"{BOLD}TTS:{RESET}      {self.tts_api}/speak\n\n")
        sys.stdout.write(f"Press Enter to return...")
        sys.stdout.flush()
        try:
            sys.stdin.readline()
        except EOFError:
            pass

    def _shutdown(self):
        self.running = False
        if self.mav:
            try:
                self.mav.close()
            except Exception:
                pass
        sys.stdout.write(f"\n{SHOW}")
        print(f"\n{GREEN}Drone CLI closed.{RESET}")

    # ── Single-command mode ───────────────────────────────────────────────────

    def run_single(self, cmd_text: str):
        if self.args.demo:
            self._demo_connect()
        elif self.args.mavlink:
            self.mavlink_connect()
            time.sleep(1)
        action = self.parse_command(cmd_text)
        if action:
            self.execute(action)
            if self.args.mavlink:
                time.sleep(2)
            if self.args.demo:
                time.sleep(3)
            print(f"{GREEN}Command executed.{RESET}    {self.last_msg}")
        else:
            print(f"{RED}Command not understood.{RESET}")
        if self.mav:
            self.mav.close()


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="PC4 Drone Terminal CLI")
    parser.add_argument("--api-host", default="127.0.0.1", help="PC1 command parser host")
    parser.add_argument("--api-port", type=int, default=8000, help="PC1 command parser port")
    parser.add_argument("--tts-host", default="127.0.0.1", help="PC4 TTS service host")
    parser.add_argument("--tts-port", type=int, default=8005, help="PC4 TTS service port")
    parser.add_argument("--host", default="127.0.0.1", help="Drone MAVLink host")
    parser.add_argument("--port", type=int, default=14550, help="Drone MAVLink port")
    parser.add_argument("--mavlink", action="store_true", help="Use direct MAVLink instead of REST API")
    parser.add_argument("--demo", action="store_true", help="Demo mode — simulated drone, no real connection needed")
    parser.add_argument("--cmd", help="Single command mode, e.g. --cmd 'takeoff 10'")
    args = parser.parse_args()

    cli = DroneCLI(args)

    if args.cmd:
        cli.run_single(args.cmd)
    else:
        cli._interactive_loop()


if __name__ == "__main__":
    main()
