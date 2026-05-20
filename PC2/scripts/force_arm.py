#!/usr/bin/env python3
"""Debug MAVLink communication and force-arm the drone."""
import socket, struct, time, sys

SYS_ID = 255
COMP_ID = 240
TARGET_SYS = 1
TARGET_COMP = 1

CRC_EXTRA = {
    0: 50,    # HEARTBEAT
    23: 168,  # PARAM_SET
    76: 152,  # COMMAND_LONG
}

def crc16_accumulate(data, crc=0xFFFF):
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc

def encode_v2(msgid, payload, seq=0):
    """Encode MAVLink v2 packet."""
    header = struct.pack('<BBBBBBB', 0xFD, len(payload), 0, 0, seq & 0xFF, SYS_ID, COMP_ID)
    header += struct.pack('<I', msgid)[:3]
    # CRC = crc16(header[1:] + payload + crc_extra)
    full = header[1:] + payload + bytes([CRC_EXTRA.get(msgid, 0)])
    crc = crc16_accumulate(full)
    return header + payload + struct.pack('<H', crc)

def make_heartbeat():
    payload = struct.pack('<BBBIBB', 6, 0, 0, 0, 4, 3)
    return encode_v2(0, payload)

def make_param_set(param_id, value):
    param_bytes = param_id.encode().ljust(16, b'\x00')[:16]
    payload = struct.pack('<BB', TARGET_SYS, TARGET_COMP) + param_bytes + struct.pack('<fB', float(value), 9)
    return encode_v2(23, payload)

def make_command_long(command, p1=0, p2=0, p3=0, p4=0, p5=0, p6=0, p7=0):
    payload = struct.pack('<BBHBfffffff',
        TARGET_SYS, TARGET_COMP, command, 0,
        p1, p2, p3, p4, p5, p6, p7)
    return encode_v2(76, payload)

def decode_mavlink(data):
    if len(data) < 12: return None
    if data[0] == 0xFE:
        # MAVLink v1
        payload_len = data[1]
        msgid = data[5]
        payload = data[6:6+payload_len]
    elif data[0] == 0xFD:
        payload_len = data[1]
        msgid = struct.unpack('<I', data[7:10] + b'\x00')[0]
        payload = data[10:10+payload_len]
    else:
        return None
    return {'id': msgid, 'payload': payload}

def parse_heartbeat(payload):
    if len(payload) < 9: return None
    fields = struct.unpack('<BBBIBB', payload[:9])
    return {
        'type': fields[0],
        'autopilot': fields[1],
        'base_mode': fields[2],
        'custom_mode': fields[3],
        'status': fields[4],
        'armed': bool(fields[2] & 128),
    }

print(f"Binding 0.0.0.0:14558, connecting to 127.0.0.1:14550", flush=True)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(2)
sock.bind(('0.0.0.0', 14558))
# Don't connect - use sendto/recvfrom
target = ('127.0.0.1', 14550)

def send(packet):
    sock.sendto(packet, target)

def recv_all(timeout=1.5):
    msgs = []
    orig = sock.gettimeout()
    sock.settimeout(timeout)
    try:
        while True:
            data, addr = sock.recvfrom(65535)
            msg = decode_mavlink(data)
            if msg:
                msgs.append((msg, data, addr))
    except socket.timeout:
        pass
    sock.settimeout(orig)
    return msgs

# Send heartbeats and see what comes back
print("\n--- Phase 1: Heartbeat exchange ---")
for i in range(5):
    send(make_heartbeat())
    time.sleep(0.2)

msgs = recv_all(2)
print(f"Received {len(msgs)} messages:")
for msg, raw, addr in msgs:
    if msg['id'] == 0:
        hb = parse_heartbeat(msg['payload'])
        if hb:
            print(f"  HEARTBEAT: sysid={raw[5]} compid={raw[6]} armed={hb['armed']} mode={hb['custom_mode']} base={hb['base_mode']:#x}")
    elif msg['id'] == 147:
        print(f"  BATTERY_STATUS: len={len(msg['payload'])}")
    elif msg['id'] == 1:
        print(f"  SYS_STATUS: len={len(msg['payload'])}")
    else:
        print(f"  msgid={msg['id']} len={len(raw)} from={addr}")

if not msgs:
    print("  No response! Trying alternative UDP path...")
    # Maybe PX4 is sending to 18570 not 14550?
    # Check if there's another port we should listen on
    print("  Trying to send to container directly...")
    sock2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock2.settimeout(2)
    sock2.bind(('0.0.0.0', 14559))
    sock2.sendto(make_heartbeat(), ('172.18.0.2', 18570))
    time.sleep(1)
    try:
        data, addr = sock2.recvfrom(65535)
        msg = decode_mavlink(data)
        if msg:
            print(f"  Got response from {addr}: msgid={msg['id']}")
    except socket.timeout:
        print("  No response on direct path either")
    sock2.close()
    sys.exit(1)

# Check if armed
for msg, raw, addr in msgs:
    if msg['id'] == 0:
        hb = parse_heartbeat(msg['payload'])
        if hb and hb['armed']:
            print("*** DRONE IS ALREADY ARMED ***")
            sys.exit(0)

print("\n--- Phase 2: Set COM_ARM_WO_GPS=1 ---")
send(make_heartbeat())
time.sleep(0.2)
param_pkt = make_param_set('COM_ARM_WO_GPS', 1.0)
print(f"  PARAM_SET packet ({len(param_pkt)} bytes), hex: {param_pkt[:20].hex()}...")
send(param_pkt)
time.sleep(0.5)
send(make_heartbeat())
time.sleep(0.5)

msgs = recv_all(2)
print(f"  Got {len(msgs)} responses:")
for msg, raw, addr in msgs:
    if msg['id'] == 0:
        hb = parse_heartbeat(msg['payload'])
        if hb:
            print(f"    HEARTBEAT: armed={hb['armed']} mode={hb['custom_mode']}")
    elif msg['id'] == 76:
        print(f"    COMMAND_ACK: payload_hex={msg['payload'][:8].hex()}")
    elif msg['id'] == 23:
        print(f"    PARAM_VALUE: payload_hex={msg['payload'][:20].hex()}")
    else:
        print(f"    msgid={msg['id']} len={len(raw)}")

print("\n--- Phase 3: Sending force arm ---")
send(make_heartbeat())
time.sleep(0.2)
arm_pkt = make_command_long(400, 1.0, 21196.0)
print(f"  Force-arm packet ({len(arm_pkt)} bytes)")
send(arm_pkt)
time.sleep(0.5)
send(make_heartbeat())
time.sleep(1)

msgs = recv_all(2)
print(f"  Got {len(msgs)} responses:")
for msg, raw, addr in msgs:
    if msg['id'] == 0:
        hb = parse_heartbeat(msg['payload'])
        if hb:
            print(f"    HEARTBEAT: armed={hb['armed']} mode={hb['custom_mode']}")
    elif msg['id'] == 76:
        fields = struct.unpack('<BBHBB', msg['payload'][:7])
        print(f"    COMMAND_ACK: command={fields[2]} result={fields[3]}")
    else:
        print(f"    msgid={msg['id']} len={len(raw)}")

# Check final state
print(f"\n--- Final heartbeat check ---")
send(make_heartbeat())
time.sleep(1)
msgs = recv_all(1.5)
for msg, raw, addr in msgs:
    if msg['id'] == 0:
        hb = parse_heartbeat(msg['payload'])
        if hb:
            print(f"  Armed: {hb['armed']}  Mode: {hb['custom_mode']}")

sock.close()
