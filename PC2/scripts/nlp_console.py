#!/usr/bin/env python3
"""NLP Drone Console — Natural language control for PX4 drone via MAVLink."""

import os, sys, time, threading, signal, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mavlink_lite import DroneConnection

RED = "\033[91m"; GREEN = "\033[92m"; YELLOW = "\033[93m"
BLUE = "\033[94m"; CYAN = "\033[96m"; BOLD = "\033[1m"; DIM = "\033[2m"
RESET = "\033[0m"; CLS = "\033[2J\033[H"

drone = None; running = True; last_msg = ""; last_msg_time = 0
cmd_history = []; known_locations = {}

# Dodoma landmarks
known_locations = {
    "base": (-6.1629, 35.7516, 1120), "home": (-6.1629, 35.7516, 1120),
    "bunge": (-6.1610, 35.7528, 1120), "parliament": (-6.1610, 35.7528, 1120),
    "hospital": (-6.1645, 35.7500, 1120), "market": (-6.1635, 35.7505, 1120),
    "bank": (-6.1635, 35.7510, 1120), "mall": (-6.1625, 35.7500, 1120),
    "roundabout": (-6.1629, 35.7516, 1120), "center": (-6.1629, 35.7516, 1120),
    "park": (-6.1630, 35.7520, 1120), "garden": (-6.1630, 35.7520, 1120),
    "gov building": (-6.1640, 35.7505, 1120), "government": (-6.1640, 35.7505, 1120),
    "forest": (-6.1600, 35.7550, 1120), "river": (-6.1650, 35.7490, 1120),
}

def loc_str(loc):
    return f"{loc[0]:.4f}, {loc[1]:.4f}"

def msg(text, ok=True):
    global last_msg, last_msg_time
    last_msg_time = time.time()
    icon = f"{GREEN}✓{RESET}" if ok else f"{RED}✗{RESET}"
    last_msg = f"{icon} {text}"

def telemetry_thread():
    while running:
        if drone:
            t = drone.get_telemetry()
            sys.stdout.write(f"{CLS}")
            sys.stdout.write(f"{BOLD}{CYAN}╔══════════════════════════════════════════════════════╗{RESET}\n")
            sys.stdout.write(f"{BOLD}{CYAN}║      NLP DRONE CONSOLE — Natural Language Control     ║{RESET}\n")
            sys.stdout.write(f"{BOLD}{CYAN}╚══════════════════════════════════════════════════════╝{RESET}\n\n")
            status = f"{GREEN}● CONNECTED{RESET}" if t["connected"] else f"{RED}○ DISCONNECTED{RESET}"
            armed = f"{GREEN}● ARMED{RESET}" if t["armed"] else f"{YELLOW}○ DISARMED{RESET}"
            sys.stdout.write(f"  {status}  |  {armed}  |  {BOLD}{t['mode']}{RESET}\n")
            speed = t.get('speed', 0)
            sys.stdout.write(f"  Alt: {t['alt']:.1f}m  |  Head: {t['heading']*57.3:.0f}°  |  Speed: {speed:.1f}m/s\n")
            bat = t["battery"]
            if bat >= 0:
                bar = "█" * max(0, min(20, int(bat/5))) + "░" * max(0, 20 - int(bat/5))
                sys.stdout.write(f"  Bat: {bar} {bat:.0f}%\n")
            sys.stdout.write(f"\n")
            global last_msg, last_msg_time
            if last_msg and time.time() - last_msg_time < 8:
                sys.stdout.write(f"  {last_msg}\n\n")
            sys.stdout.write(f"{BOLD}Examples:{RESET}\n")
            sys.stdout.write(f"  \"take off to 20m\", \"land\", \"fly to bunge parliament\"\n")
            sys.stdout.write(f"  \"go forward 30 meters\", \"turn right\", \"climb to 50\"\n")
            sys.stdout.write(f"  \"fly to -6.161, 35.753\", \"speed 15\", \"return home\"\n")
            sys.stdout.write(f"\n{BOLD}Known:{RESET} " + ", ".join(sorted(known_locations.keys())))
            sys.stdout.write(f"\n\n  {BOLD}> {RESET}")
            sys.stdout.flush()
        time.sleep(0.5)

def parse_nlp(text):
    """Parse natural language into a drone action."""
    text_lower = text.lower().strip()
    if not text_lower:
        return None

    # Location lookup
    def find_location(t):
        for name, loc in known_locations.items():
            if name in t:
                return loc
        # Try GPS coordinates
        import re
        gps = re.findall(r'-?\d+\.\d+', t)
        if len(gps) >= 2:
            alt = float(gps[2]) if len(gps) >= 3 else 30
            return (float(gps[0]), float(gps[1]), alt)
        return None

    # Extract numbers
    import re
    nums = [float(n) for n in re.findall(r'\d+\.?\d*', text_lower)]
    alt = 0
    speed = 0
    distance = 0
    for n in nums:
        if n < 500:
            if 'speed' in text_lower or 'fast' in text_lower or 'slow' in text_lower:
                speed = n
            elif 'alt' in text_lower or 'height' in text_lower or 'climb' in text_lower or 'descend' in text_lower:
                alt = n
            elif 'meter' in text_lower or 'metre' in text_lower or 'm ' in text_lower or 'm.' in text_lower:
                distance = n
            else:
                alt = n  # default number likely altitude

    # === COMMANDS ===
    if any(w in text_lower for w in ['takeoff', 'take off', 'take-off']):
        a = alt if alt > 0 else 15
        return ('takeoff', a)

    if text_lower in ['land', 'land now', 'come down', 'touch down']:
        return ('land',)

    if any(w in text_lower for w in ['return home', 'return to base', 'go home', 'rtl', 'come back']):
        return ('rtl',)

    if any(w in text_lower for w in ['disarm', 'shut down', 'power off']):
        return ('disarm',)

    if any(w in text_lower for w in ['arm']):
        return ('arm',)

    if any(w in text_lower for w in ['speed', 'faster', 'slower']):
        s = speed if speed > 0 else 10
        return ('speed', s)

    if any(w in text_lower for w in ['mission', 'auto', 'automatic']):
        return ('mission',)

    if any(w in text_lower for w in ['hover', 'hold', 'stop', 'pause']):
        return ('hover',)

    if any(w in text_lower for w in ['emergency', 'kill', 'stop now']):
        return ('emergency',)

    if any(w in text_lower for w in ['climb', 'ascend', 'go up', 'increase alt']):
        a = alt if alt > 0 else 10
        return ('climb', a)

    if any(w in text_lower for w in ['descend', 'go down', 'lower']):
        a = alt if alt > 0 else 5
        return ('descend', a)

    # Directional movement
    if any(w in text_lower for w in ['forward', 'ahead']):
        d = distance if distance > 0 else 20
        return ('forward', d)

    if any(w in text_lower for w in ['backward', 'back', 'reverse']):
        d = distance if distance > 0 else 20
        return ('backward', d)

    if any(w in text_lower for w in ['left']):
        d = distance if distance > 0 else 10
        return ('left', d)

    if any(w in text_lower for w in ['right']):
        d = distance if distance > 0 else 10
        return ('right', d)

    if any(w in text_lower for w in ['turn left', 'rotate left']):
        return ('turn_left',)

    if any(w in text_lower for w in ['turn right', 'rotate right']):
        return ('turn_right',)

    if any(w in text_lower for w in ['turn around', 'rotate 180']):
        return ('turn_around',)

    # Goto location
    loc = find_location(text_lower)
    if loc:
        return ('goto', loc[0], loc[1], loc[2])

    # Goto coordinates
    if 'fly to' in text_lower or 'go to' in text_lower or 'navigate' in text_lower:
        return ('goto', -6.1629, 35.7516, alt if alt > 0 else 30)

    return None

def execute_action(action):
    if not drone:
        msg("No drone connection", False)
        return
    try:
        cmd = action[0]
        if cmd == 'takeoff':
            drone.arm()
            time.sleep(0.5)
            drone.takeoff(action[1])
            msg(f"Takeoff to {action[1]}m")
        elif cmd == 'land':
            drone.land()
            msg("Landing")
        elif cmd == 'rtl':
            drone.rtl()
            msg("Returning to launch")
        elif cmd == 'arm':
            drone.arm()
            msg("Armed")
        elif cmd == 'disarm':
            drone.disarm()
            msg("Disarmed")
        elif cmd == 'speed':
            drone.set_speed(action[1])
            msg(f"Speed set to {action[1]} m/s")
        elif cmd == 'hover':
            drone.set_position(0, 0, 0)
            msg("Hovering")
        elif cmd == 'goto':
            drone.goto_position(action[1], action[2], action[3])
            msg(f"Navigating to {action[1]:.4f}, {action[2]:.4f}")
        elif cmd == 'climb':
            t = drone.get_telemetry()
            drone.goto_position(t['lat'], t['lon'], t['alt'] + action[1])
            msg(f"Climbing {action[1]}m")
        elif cmd == 'descend':
            t = drone.get_telemetry()
            target = max(5, t['alt'] - action[1])
            drone.goto_position(t['lat'], t['lon'], target)
            msg(f"Descending {action[1]}m")
        elif cmd == 'forward':
            t = drone.get_telemetry()
            h = t['heading']
            import math
            lat = t['lat'] + (action[1] * math.cos(h)) / 111320
            lon = t['lon'] + (action[1] * math.sin(h)) / (111320 * math.cos(math.radians(t['lat'])))
            drone.goto_position(lat, lon, t['alt'])
            msg(f"Moving forward {action[1]}m")
        elif cmd == 'emergency':
            drone.land()
            msg("EMERGENCY - Landing!")
        else:
            msg(f"Unknown command: {cmd}", False)
    except Exception as e:
        msg(f"Error: {e}", False)

def main():
    global running, drone
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))

    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 14540

    print(f"{CLS}{BOLD}Connecting to drone at {host}:{port}...{RESET}")
    drone = DroneConnection(udp_target=(host, port))
    try:
        drone.connect()
    except Exception as e:
        print(f"{RED}Connection failed: {e}{RESET}")
        return

    print(f"{GREEN}Connected!{RESET}")
    time.sleep(2)
    ui = threading.Thread(target=telemetry_thread, daemon=True)
    ui.start()
    time.sleep(0.5)

    try:
        while running:
            try:
                line = input().strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not line:
                continue
            if line.lower() in ['quit', 'exit', 'q']:
                break
            cmd_history.append(line)
            action = parse_nlp(line)
            if action:
                execute_action(action)
            else:
                msg(f"Command not understood. Try: takeoff, land, fly to bunge", False)
    except:
        pass
    finally:
        running = False
        if drone:
            drone.close()
        print(f"\n{GREEN}Console closed.{RESET}")

if __name__ == "__main__":
    main()
