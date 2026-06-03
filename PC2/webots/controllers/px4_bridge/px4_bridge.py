#!/usr/bin/env python3
"""MAVLink bridge controller for Webots drone.
Acts as a PX4-compatible MAVLink endpoint, translating between
Webots drone API and the MAVLink protocol used by the project's Python scripts.

Runs inside Webots as the drone's controller.
Opens UDP port 14550 to receive commands from mavlink_lite.py and other scripts.
"""

import socket
import struct
import time
import threading
import math
import sys
import os
import traceback

# Import Webots controller API FIRST, before path manipulation
from controller import Robot, GPS, InertialUnit, Gyro, Camera

# Then add scripts path for other imports if needed
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'scripts'))

CRC_EXTRA = {0: 50, 24: 24, 30: 39, 32: 185, 33: 40, 76: 152, 147: 154, 29: 22, 1: 0, 141: 34}

MAV_CMD = {
    "COMPONENT_ARM_DISARM": 400,
    "NAV_TAKEOFF": 22,
    "NAV_LAND": 21,
    "NAV_RETURN_TO_LAUNCH": 20,
    "NAV_WAYPOINT": 16,
    "DO_CHANGE_SPEED": 178,
}

MAV_MODE_FLAG_ARMED = 128
MAV_STATE_ACTIVE = 4
MAV_TYPE_QUADROTOR = 2

GCS_SYS_ID = 255
GCS_COMP_ID = 0
DRONE_SYS_ID = 1
DRONE_COMP_ID = 1

HOME_LAT = -6.1630
HOME_LON = 35.7516
HOME_ALT = 1120.0


def clamp(val, lo, hi):
    return max(lo, min(hi, val))


def latlon_add_m(lat, lon, dn, de):
    dlat = dn / 111111.0
    dlon = de / (111111.0 * math.cos(math.radians(lat + dlat / 2)))
    return lat + dlat, lon + dlon


def latlon_diff_m(lat1, lon1, lat2, lon2):
    dn = (lat2 - lat1) * 111111.0
    de = (lon2 - lon1) * 111111.0 * math.cos(math.radians((lat1 + lat2) / 2))
    return dn, de


class CRC16:
    def __init__(self):
        self.crc = 0xFFFF

    def accumulate(self, data):
        for byte in data:
            self.crc ^= byte << 8
            for _ in range(8):
                if self.crc & 0x8000:
                    self.crc = (self.crc << 8) ^ 0x1021
                else:
                    self.crc <<= 1
                self.crc &= 0xFFFF
            self.crc &= 0xFFFF

    def digest(self):
        return struct.pack('<H', self.crc)


def mavlink_crc(msg_id, payload):
    crc = CRC16()
    crc.accumulate(payload)
    extra = CRC_EXTRA.get(msg_id, 0)
    crc.accumulate(bytes([extra]))
    return crc.digest()


def encode_mavlink(msg_id, payload, seq=0):
    length = len(payload)
    hdr = struct.pack('<BBBBBBB', 0xFD, length, 0, 0, seq & 0xFF, GCS_SYS_ID, GCS_COMP_ID)
    hdr += struct.pack('<I', msg_id)[:3]
    crc = mavlink_crc(msg_id, payload)
    return hdr + payload + crc


def encode_heartbeat(armed=False, mode=0, system_status=MAV_STATE_ACTIVE):
    base_mode = mode | (MAV_MODE_FLAG_ARMED if armed else 0)
    payload = struct.pack('<IBBBBB', 0, MAV_TYPE_QUADROTOR, 0, base_mode, system_status, 3)
    return encode_mavlink(0, payload)


def encode_gps_raw_int(lat, lon, alt, fix_type=3, satellites=10):
    payload = struct.pack('<QiiiiHHBB', 0, int(lat * 1e7), int(lon * 1e7), int(alt * 1000),
                          int(alt * 1000), 0, 0, fix_type, satellites)
    return encode_mavlink(24, payload)


def encode_global_position_int(lat, lon, alt, alt_rel, hdg=0):
    payload = struct.pack('<IiiiiiiiH', 0, int(lat * 1e7), int(lon * 1e7),
                          int(alt * 1000), int(alt_rel * 1000), 0, 0, 0, int(hdg * 100))
    return encode_mavlink(33, payload)


def encode_attitude(roll, pitch, yaw):
    payload = struct.pack('<Iffffff', 0, roll, pitch, yaw, 0, 0, 0)
    return encode_mavlink(30, payload)


def encode_battery_status(voltage=12.5, current=0.0, remaining=100):
    bat_id = 0
    function = 1
    temperature = 0x7FFF
    voltages = [int(voltage * 1000 / 4)] * 4 + [0xFFFF] * 6
    payload = struct.pack('<BBh' + 'H' * 10 + 'hIIB',
                          function, bat_id, temperature,
                          *voltages,
                          int(current * 100), 0, 0, remaining)
    return encode_mavlink(147, payload)


def encode_vfr_hud(airspeed=0, groundspeed=0, heading=0, throttle=0, alt=0, climb=0):
    payload = struct.pack('<ffHHff', airspeed, groundspeed, int(heading), int(throttle), alt, climb)
    return encode_mavlink(29, payload)


def encode_local_position_ned(x, y, z, vx=0, vy=0, vz=0):
    payload = struct.pack('<Iffffff', 0, x, y, z, vx, vy, vz)
    return encode_mavlink(32, payload)


def encode_sys_status(voltage=12.5, current=0.0, remaining=100):
    payload = struct.pack('<IIIIhHHHHHHb',
                          0, 0, 0, 0,
                          int(voltage * 1000),
                          int(current * 100),
                          remaining, 0, 0, 0, 0, 0)
    return encode_mavlink(1, payload)


def decode_mavlink(data):
    if len(data) < 12 or data[0] != 0xFD:
        return None
    length = data[1]
    msg_id = struct.unpack('<I', data[7:10] + b'\x00')[0]
    payload = data[10:10 + length]
    return {'id': msg_id, 'payload': payload, 'length': length}


def parse_command_long(payload):
    if len(payload) < 33:
        return None
    fields = struct.unpack('<BBHBfffffff', payload[:33])
    return {
        'command': fields[2],
        'param1': fields[4],
        'param2': fields[5],
        'param3': fields[6],
        'param4': fields[7],
        'param5': fields[8],
        'param6': fields[9],
        'param7': fields[10],
    }


class MavicBridge(Robot):
    K_VERTICAL_THRUST = 68.5
    K_VERTICAL_OFFSET = 0.6
    K_VERTICAL_P = 15.0
    K_VERTICAL_D = 3.0
    K_VERTICAL_GAIN = 3.0
    TAKEOFF_BOOST = 120.0
    TAKEOFF_BOOST_DURATION = 3.0
    K_ROLL_P = 50.0
    K_PITCH_P = 30.0
    MAX_YAW_DISTURBANCE = 0.4
    MAX_PITCH_DISTURBANCE = -1
    TARGET_PRECISION = 0.8
    MOTOR_MAX = 200

    def __init__(self):
        Robot.__init__(self)
        self.time_step = int(self.getBasicTimeStep())
        self.camera = self.getDevice("camera")
        self.camera.enable(self.time_step)
        self.imu = self.getDevice("inertial unit")
        self.imu.enable(self.time_step)
        self.gps = self.getDevice("gps")
        self.gps.enable(self.time_step)
        self.gyro = self.getDevice("gyro")
        self.gyro.enable(self.time_step)

        self.front_left_motor = self.getDevice("front left propeller")
        self.front_right_motor = self.getDevice("front right propeller")
        self.rear_left_motor = self.getDevice("rear left propeller")
        self.rear_right_motor = self.getDevice("rear right propeller")
        self.camera_pitch_motor = self.getDevice("camera pitch")
        self.camera_pitch_motor.setPosition(0.7)

        for motor in [self.front_left_motor, self.front_right_motor,
                      self.rear_left_motor, self.rear_right_motor]:
            motor.setPosition(float('inf'))
            motor.setVelocity(1)

        self.armed = False
        self.flight_mode = "STABILIZED"
        self.target_lat = HOME_LAT
        self.target_lon = HOME_LON
        self.target_alt = 0
        self.target_yaw = 0
        self.home_lat = HOME_LAT
        self.home_lon = HOME_LON
        self.home_alt = HOME_ALT
        self.roll = self.pitch = self.yaw = 0
        self.x = self.y = self.z = 0
        self.gps_lat = HOME_LAT
        self.gps_lon = HOME_LON
        self.gps_alt = 0
        self.roll_accel = self.pitch_accel = 0
        self.vel_x = self.vel_y = self.vel_z = 0
        self.mav_seq = 0
        self._in_air = False

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.settimeout(0.01)
        self.sock.bind(('0.0.0.0', 14550))

        self.clients = set()
        self.last_heartbeat = 0
        self.last_telemetry = 0
        self.cmd_roll = 0
        self.cmd_pitch = 0
        self.cmd_yaw = 0
        self.cmd_throttle = 0
        self._takeoff_boost_until = 0.0

        print("[BRIDGE] Mavic Bridge controller started on UDP :14550")

    def send_to_clients(self, packet):
        for addr in list(self.clients):
            try:
                self.sock.sendto(packet, addr)
            except:
                self.clients.discard(addr)

    def handle_command(self, cmd):
        cid = cmd['command']
        p1 = cmd['param1']
        p7 = cmd['param7']
        p5 = cmd['param5']
        p6 = cmd['param6']

        if cid == 400:
            self.armed = (p1 == 1.0)
            print(f"[BRIDGE] {'ARM' if self.armed else 'DISARM'}")
            if self.armed and not self._in_air:
                self._in_air = True
                self.target_alt = self.z + 2
                self._takeoff_boost_until = time.time() + self.TAKEOFF_BOOST_DURATION

        elif cid == 22:
            print(f"[BRIDGE] TAKEOFF to {p7}m")
            self.armed = True
            self._in_air = True
            self.target_alt = p7 if p7 > 0 else 10
            self._takeoff_boost_until = time.time() + self.TAKEOFF_BOOST_DURATION

        elif cid == 21:
            print("[BRIDGE] LAND")
            self._in_air = False
            self.target_alt = -0.1

        elif cid == 20:
            print("[BRIDGE] RETURN TO LAUNCH")
            self.target_lat = self.home_lat
            self.target_lon = self.home_lon
            self.target_alt = 15

        elif cid == 16:
            if p5 != 0 and p6 != 0:
                print(f"[BRIDGE] GOTO {p5:.6f}, {p6:.6f}, {p7:.1f}")
                self.target_lat = p5
                self.target_lon = p6
                self.target_alt = p7 if p7 > 0 else 15

        elif cid == 178:
            print(f"[BRIDGE] Set speed: {p2} m/s")

    def process_mavlink(self, data, addr):
        self.clients.add(addr)
        msg = decode_mavlink(data)
        if msg is None:
            return

        if msg['id'] == 0:
            pass
        elif msg['id'] == 76:
            cmd = parse_command_long(msg['payload'])
            if cmd:
                self.handle_command(cmd)

    def update_sensors(self):
        self.roll, self.pitch, self.yaw = self.imu.getRollPitchYaw()
        gps_vals = self.gps.getValues()
        self.x, self.y, self.z = gps_vals
        self.gps_lat, self.gps_lon = latlon_add_m(self.home_lat, self.home_lon, self.x, self.y)
        self.gps_alt = self.home_alt + self.z
        gyro_vals = self.gyro.getValues()
        self.roll_accel, self.pitch_accel, _ = gyro_vals

        dt = self.time_step / 1000.0
        self.vel_x = (gps_vals[0] - getattr(self, '_prev_x', gps_vals[0])) / dt if dt > 0 else 0
        self.vel_y = (gps_vals[1] - getattr(self, '_prev_y', gps_vals[1])) / dt if dt > 0 else 0
        self.vel_z = (gps_vals[2] - getattr(self, '_prev_z', gps_vals[2])) / dt if dt > 0 else 0
        self._prev_x, self._prev_y, self._prev_z = gps_vals

    def run_control_loop(self):
        target_alt = self.target_alt
        altitude = self.z

        d_lat = self.target_lat - self.gps_lat
        d_lon = self.target_lon - self.gps_lon
        n = d_lat * 111111.0
        e = d_lon * 111111.0 * math.cos(math.radians(self.gps_lat))

        dn = n * math.cos(self.yaw) + e * math.sin(self.yaw)
        de = -n * math.sin(self.yaw) + e * math.cos(self.yaw)

        yaw_disturbance = clamp(self.MAX_YAW_DISTURBANCE * math.atan2(de, dn) / math.pi, -0.3, 0.3)

        if abs(dn) < self.TARGET_PRECISION and abs(de) < self.TARGET_PRECISION:
            yaw_disturbance = 0

        pitch_disturbance = clamp(math.log10(max(abs(math.atan2(de, dn)), 0.1)) * 2, -0.5, 0.3) if abs(dn) > 0.5 or abs(de) > 0.5 else 0
        if abs(dn) < 0.5 and abs(de) < 0.5:
            pitch_disturbance = 0

        diff_alt = target_alt - altitude
        clamped_diff = clamp(diff_alt + self.K_VERTICAL_OFFSET, -1, 1)
        vertical_input = self.K_VERTICAL_P * pow(clamped_diff, 3.0)

        velocity_damping = -self.K_VERTICAL_D * clamp(self.vel_z, -3, 3)
        vertical_input += velocity_damping

        if not self.armed:
            vertical_input = -self.K_VERTICAL_THRUST * 0.8

        # Landing: velocity-controlled descent at 0.5 m/s
        if self.armed and self._in_air is False and target_alt < 0.1:
            descent_rate = 0.5 if altitude > 1.0 else 0.3
            vel_error = -descent_rate - self.vel_z
            vertical_input = vel_error * 5.0
            if altitude < 0.12:
                vertical_input = -self.K_VERTICAL_THRUST * 0.95

        if time.time() < self._takeoff_boost_until:
            vertical_input += self.TAKEOFF_BOOST

        roll_input = self.K_ROLL_P * clamp(self.roll, -1, 1) + self.roll_accel
        pitch_input = self.K_PITCH_P * clamp(self.pitch, -1, 1) + self.pitch_accel

        fl = self.K_VERTICAL_THRUST + vertical_input - yaw_disturbance + pitch_input - roll_input
        fr = self.K_VERTICAL_THRUST + vertical_input + yaw_disturbance + pitch_input + roll_input
        rl = self.K_VERTICAL_THRUST + vertical_input + yaw_disturbance - pitch_input - roll_input
        rr = self.K_VERTICAL_THRUST + vertical_input - yaw_disturbance - pitch_input + roll_input

        mm = self.MOTOR_MAX
        self.front_left_motor.setVelocity(clamp(fl, 0, mm))
        self.front_right_motor.setVelocity(clamp(-fr, -mm, 0))
        self.rear_left_motor.setVelocity(clamp(-rl, -mm, 0))
        self.rear_right_motor.setVelocity(clamp(rr, 0, mm))

    def run(self):
        print("[BRIDGE] Starting Webots MAVLink bridge...")
        while self.step(self.time_step) != -1:
            now = time.time()
            self.update_sensors()

            try:
                while True:
                    data, addr = self.sock.recvfrom(4096)
                    self.process_mavlink(data, addr)
            except socket.timeout:
                pass
            except BlockingIOError:
                pass

            self.run_control_loop()

            if now - self.last_heartbeat > 0.5:
                hb = encode_heartbeat(armed=self.armed, mode=4 if self.armed else 0)
                self.send_to_clients(hb)
                self.last_heartbeat = now

            if now - self.last_telemetry > 0.2:
                self.send_to_clients(encode_gps_raw_int(self.gps_lat, self.gps_lon, self.gps_alt))
                self.send_to_clients(encode_global_position_int(self.gps_lat, self.gps_lon, self.gps_alt, self.z))
                self.send_to_clients(encode_attitude(self.roll, self.pitch, self.yaw))
                self.send_to_clients(encode_battery_status(12.5, 0, 95))
                self.send_to_clients(encode_vfr_hud(0, 0, math.degrees(self.yaw) % 360, 50, self.z, 0))
                self.send_to_clients(encode_local_position_ned(self.x, self.y, -self.z, self.vel_x, self.vel_y, self.vel_z))
                self.send_to_clients(encode_sys_status(12.5, 0, 95))
                self.last_telemetry = now


try:
    robot = MavicBridge()
    robot.run()
except Exception as e:
    print(f"[BRIDGE] FATAL: {e}", flush=True)
    traceback.print_exc()
    sys.exit(1)
