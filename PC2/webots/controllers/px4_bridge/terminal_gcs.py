#!/usr/bin/env python3
"""Terminal GCS — connect to px4_bridge and control drone from keyboard."""

import os, sys, socket, time, threading, math

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', '..', '..', 'venv', 'lib',
                                'python3.12', 'site-packages'))
from pymavlink.dialects.v20 import common as mavlink

BRIDGE = ("127.0.0.1", 14550)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(0.5)

mav = mavlink.MAVLink(None, srcSystem=255, srcComponent=0)

running = True
telemetry = {
    "alt": 0, "lat": 0, "lon": 0, "hdx": 0, "hdg": 0,
    "vx": 0, "vy": 0, "vz": 0, "armed": False, "mode": "?"
}

def send_cmd(cmd_id, p1=0, p2=0, p3=0, p4=0, p5=0.0, p6=0.0, p7=0.0):
    pkt = mav.command_long_encode(1, 1, cmd_id, 0, p1, p2, p3, p4, p5, p6, p7).pack(mav)
    sock.sendto(pkt, BRIDGE)

def recv_loop():
    global telemetry
    while running:
        try:
            data, addr = sock.recvfrom(4096)
            if addr != BRIDGE:
                continue
            for b in data:
                msg = mav.parse_char(bytes([b]))
                if msg is None:
                    continue
                t = msg.get_type()
                if t == "HEARTBEAT":
                    telemetry["armed"] = bool(msg.base_mode & 128)
                elif t == "GLOBAL_POSITION_INT":
                    telemetry["lat"] = msg.lat / 1e7
                    telemetry["lon"] = msg.lon / 1e7
                    telemetry["alt"] = msg.relative_alt / 1000.0
                    telemetry["hdg"] = msg.hdg / 100.0
                elif t == "GPS_RAW_INT":
                    telemetry["lat"] = msg.lat / 1e7
                    telemetry["lon"] = msg.lon / 1e7
                    telemetry["alt"] = msg.alt / 1000.0
                elif t == "GLOBAL_POSITION_INT":
                    telemetry["vx"] = msg.vx / 100.0
                    telemetry["vy"] = msg.vy / 100.0
                    telemetry["vz"] = msg.vz / 100.0
        except socket.timeout:
            pass
        except:
            pass

def display():
    t = telemetry
    print("\033[2J\033[H", end="")
    print("=" * 50)
    print("  DRONE TERMINAL GCS")
    print("=" * 50)
    armed = "\033[92mARMED\033[0m" if t["armed"] else "\033[91mDISARMED\033[0m"
    print(f"  Status: {armed}")
    alt = t.get("alt", 0)
    alt_color = "\033[92m" if alt > 0.5 else "\033[93m"
    print(f"  Alt:    {alt_color}{alt:.2f}m\033[0m")
    print(f"  Pos:    {t.get('lat',0):.6f}, {t.get('lon',0):.6f}")
    print(f"  Vel:    {t.get('vx',0):.2f} {t.get('vy',0):.2f} {t.get('vz',0):.2f} m/s")
    print(f"  Hdg:    {t.get('hdg',0):.0f} deg")
    print("-" * 50)
    print("  Commands:")
    print("    \033[1ma\033[0m  ARM")
    print("    \033[1md\033[0m  DISARM")
    print("    \033[1mt\033[0m  TAKEOFF (to 2m)")
    print("    \033[1ml\033[0m  LAND")
    print("    \033[1mr\033[0m  RTL")
    print("    \033[1ms\033[0m  STATUS")
    print("    \033[1mq\033[0m  QUIT")
    print("-" * 50)

def main():
    global running
    print(f"Connecting to bridge at {BRIDGE[0]}:{BRIDGE[1]}...")
    # Send empty datagram to register as GCS
    sock.sendto(b"", BRIDGE)
    time.sleep(0.2)
    # Send heartbeat as GCS
    hb = mav.heartbeat_encode(
        mavlink.MAV_TYPE_GCS, mavlink.MAV_AUTOPILOT_INVALID,
        0, 0, mavlink.MAV_STATE_ACTIVE
    ).pack(mav)
    sock.sendto(hb, BRIDGE)

    t = threading.Thread(target=recv_loop, daemon=True)
    t.start()

    time.sleep(0.5)
    display()

    while running:
        try:
            cmd = input("\n> ").strip().lower()
        except EOFError:
            break

        if cmd == "q":
            print("Quitting.")
            running = False
            break
        elif cmd == "a":
            send_cmd(mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 1)
            print("\033[92mARM command sent\033[0m")
            for _ in range(12):
                if telemetry["armed"]:
                    print("\033[92m✓ Drone ARMED\033[0m")
                    break
                time.sleep(0.25)
            else:
                print("\033[93m⚠ ARM command sent, waiting for confirmation...\033[0m")
        elif cmd == "d":
            send_cmd(mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0)
            print("\033[93mDISARM command sent\033[0m")
            for _ in range(12):
                if not telemetry["armed"]:
                    print("\033[93m✓ Drone DISARMED\033[0m")
                    break
                time.sleep(0.25)
            else:
                print("\033[93m⚠ DISARM sent, waiting for confirmation...\033[0m")
        elif cmd == "t":
            send_cmd(mavlink.MAV_CMD_NAV_TAKEOFF, 0, 0, 0, 0, 0, 0, 2.0)
            print("\033[92mTAKEOFF command sent (2m)\033[0m")
            time.sleep(1.0)
        elif cmd == "l":
            send_cmd(mavlink.MAV_CMD_NAV_LAND)
            print("\033[93mLAND command sent\033[0m")
            time.sleep(0.5)
        elif cmd == "r":
            send_cmd(mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH)
            print("\033[93mRTL command sent\033[0m")
            time.sleep(0.5)
        elif cmd == "s":
            display()
            continue
        else:
            print(f"Unknown: {cmd}")
            print("  a=arm  d=disarm  t=takeoff  l=land  r=rtl  s=status  q=quit")

        time.sleep(0.1)
        display()

    sock.close()

if __name__ == "__main__":
    main()
