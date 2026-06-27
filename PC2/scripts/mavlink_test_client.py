#!/usr/bin/env python3
import socket
import time
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'venv', 'lib',
                                  'python3.12', 'site-packages'))
from pymavlink.dialects.v20 import common as mavlink

mav = mavlink.MAVLink(None, srcSystem=255, srcComponent=1)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

BRIDGE_IP = "127.0.0.1"
BRIDGE_PORT = 14550

sock.sendto(b"", (BRIDGE_IP, BRIDGE_PORT))

def send_heartbeat():
    hb = mav.heartbeat_encode(
        mavlink.MAV_TYPE_GCS, mavlink.MAV_AUTOPILOT_INVALID,
        0, 0, mavlink.MAV_STATE_ACTIVE
    ).pack(mav)
    sock.sendto(hb, (BRIDGE_IP, BRIDGE_PORT))

def send_arm(arm=True):
    cmd = mav.command_long_encode(
        1, 1,
        mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
        0, 1 if arm else 0, 0, 0, 0, 0, 0, 0
    ).pack(mav)
    sock.sendto(cmd, (BRIDGE_IP, BRIDGE_PORT))

def send_takeoff(alt=10):
    cmd = mav.command_long_encode(
        1, 1,
        mavlink.MAV_CMD_NAV_TAKEOFF,
        0, 0, 0, 0, 0, 0, 0, alt
    ).pack(mav)
    sock.sendto(cmd, (BRIDGE_IP, BRIDGE_PORT))

def recv_all(timeout=5):
    sock.settimeout(timeout)
    data = b""
    try:
        while True:
            chunk, addr = sock.recvfrom(65535)
            data += chunk
    except socket.timeout:
        pass
    return data

print("[TEST] Connecting to bridge at 127.0.0.1:14550...")
sock.sendto(b"", (BRIDGE_IP, BRIDGE_PORT))
time.sleep(0.5)

send_heartbeat()
print("[TEST] Sent HEARTBEAT (registering as GCS)")
time.sleep(1)

print("[TEST] Receiving telemetry...")
data = recv_all(timeout=3)
print(f"[TEST] Received {len(data)} bytes")

if data:
    for b in data:
        msg = mav.parse_char(bytes([b]))
        if msg:
            t = msg.get_type()
            if t == "HEARTBEAT":
                print(f"  HEARTBEAT: type={msg.type} autopilot={msg.autopilot} state={msg.system_status}")
            elif t == "GPS_RAW_INT":
                print(f"  GPS: lat={msg.lat/1e7:.6f} lon={msg.lon/1e7:.6f} alt={msg.alt/1e3:.1f}m")
            elif t == "GLOBAL_POSITION_INT":
                print(f"  POS: lat={msg.lat/1e7:.6f} lon={msg.lon/1e7:.6f} rel_alt={msg.relative_alt/1e3:.1f}m")
            elif t == "ATTITUDE":
                print(f"  ATT: roll={msg.roll:.2f} pitch={msg.pitch:.2f} yaw={msg.yaw:.2f}")
            elif t == "VFR_HUD":
                print(f"  VFR: alt={msg.alt:.1f}m heading={msg.heading:.0f}deg")

print()
print("[TEST] Sending ARM command...")
send_arm(True)
time.sleep(1)

print("[TEST] Sending TAKEOFF (alt=10m)...")
send_takeoff(10)
time.sleep(2)

data = recv_all(timeout=3)
print(f"[TEST] After commands, received {len(data)} bytes")
if data:
    for b in data:
        msg = mav.parse_char(bytes([b]))
        if msg:
            t = msg.get_type()
            if t == "HEARTBEAT":
                armed = msg.base_mode & 128
                print(f"  HEARTBEAT: armed={bool(armed)} state={msg.system_status}")
            elif t == "STATUSTEXT":
                print(f"  STATUS: {msg.text}")

print()
print("[TEST] Done")
