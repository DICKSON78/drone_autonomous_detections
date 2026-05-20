#!/usr/bin/env python3
"""Minimal MAVLink v2 protocol implementation for drone control."""

import socket
import struct
import time
import threading

CRC_EXTRA = {
    0: 50,      # HEARTBEAT
    24: 24,     # GPS_RAW_INT
    30: 39,     # ATTITUDE
    32: 185,    # LOCAL_POSITION_NED
    76: 152,    # COMMAND_LONG
    147: 154,   # BATTERY_STATUS
}

MAV_CMD = {
    "COMPONENT_ARM_DISARM": 400,
    "NAV_TAKEOFF": 22,
    "NAV_LAND": 21,
    "NAV_RETURN_TO_LAUNCH": 20,
    "NAV_WAYPOINT": 16,
    "DO_CHANGE_SPEED": 178,
    "NAV_DELAY": 93,
    "CONDITION_DELAY": 67,
}

MAV_MODE_FLAG = {
    "SAFETY_ARMED": 128,
    "MANUAL": 1,
    "GUIDED": 4,
    "AUTO": 8,
    "STABILIZE": 2,
}

MAV_STATE = {
    "UNINIT": 0,
    "BOOT": 1,
    "CALIBRATING": 2,
    "STANDBY": 3,
    "ACTIVE": 4,
    "CRITICAL": 5,
    "EMERGENCY": 6,
    "POWEROFF": 7,
    "FLIGHT_TERMINATION": 8,
}

MAV_TYPE = {
    "QUADROTOR": 2,
    "HEXAROTOR": 3,
    "OCTOROTOR": 4,
    "GCS": 6,
}

class CRC16:
    def __init__(self):
        self.crc = 0xFFFF

    def accumulate(self, data):
        for byte in data:
            self._add_byte(byte)

    def _add_byte(self, b):
        self.crc ^= b << 8
        for _ in range(8):
            if self.crc & 0x8000:
                self.crc = (self.crc << 1) ^ 0x1021
            else:
                self.crc <<= 1
            self.crc &= 0xFFFF
        self.crc &= 0xFFFF

class MAVLink:
    def __init__(self, source_system=255, source_component=0):
        self.seq = 0
        self.source_system = source_system
        self.source_component = source_component
        self.target_system = 1
        self.target_component = 1

    def _crc_calculate(self, msg_id, payload):
        crc = CRC16()
        crc.accumulate(payload)
        extra = CRC_EXTRA.get(msg_id, 0)
        crc.accumulate(bytes([extra]))
        return struct.pack('<H', crc.crc)

    def _make_header(self, msg_id, payload_len):
        header = struct.pack('<BBBBBBB',
            0xFD,
            payload_len,
            0, 0,
            self.seq & 0xFF,
            self.source_system,
            self.source_component
        )
        header += struct.pack('<I', msg_id)[:3]
        self.seq += 1
        return header

    def encode_command_long(self, command, param1=0, param2=0, param3=0,
                            param4=0, param5=0, param6=0, param7=0):
        payload = struct.pack('<BBHBfffffff',
            self.target_system, self.target_component,
            command, 0,
            param1, param2, param3, param4,
            param5, param6, param7
        )
        header = self._make_header(76, len(payload))
        crc = self._crc_calculate(76, payload)
        return header + payload + crc

    def encode_heartbeat(self):
        payload = struct.pack('<IBBBBB',
            0,
            MAV_TYPE["GCS"],
            0,
            0,
            MAV_STATE["ACTIVE"],
            3
        )
        header = self._make_header(0, len(payload))
        crc = self._crc_calculate(0, payload)
        return header + payload + crc

    @staticmethod
    def decode_message(data):

        if len(data) < 10:
            return None
        if data[0] != 0xFD:
            return None

        payload_len = data[1]
        msg_id = struct.unpack('<I', data[7:10] + b'\x00')[0]
        payload = data[10:10 + payload_len]

        msg = {"id": msg_id, "payload": payload}

        if msg_id == 0 and len(payload) >= 9:
            fields = struct.unpack('<IBBBBB', payload[:9])
            msg["custom_mode"] = fields[0]
            msg["type"] = fields[1]
            msg["autopilot"] = fields[2]
            msg["base_mode"] = fields[3]
            msg["system_status"] = fields[4]
            msg["mavlink_version"] = fields[5] if len(payload) > 9 else 0
            msg["name"] = "HEARTBEAT"
            msg["armed"] = bool(fields[3] & 128)
            msg["mode"] = fields[3] & 0x7F

        elif msg_id == 24 and len(payload) >= 30:
            fields = struct.unpack('<QiiHHHHBB', payload[:30])
            msg["name"] = "GPS_RAW_INT"
            msg["lat"] = fields[1] / 1e7
            msg["lon"] = fields[2] / 1e7
            msg["alt"] = fields[3] / 1e3
            msg["fix_type"] = fields[8]
            msg["satellites"] = fields[9]

        elif msg_id == 147 and len(payload) >= 31:
            msg["name"] = "BATTERY_STATUS"
            # BATTERY_STATUS: function(1), id(1), temperature(2), voltages(10x2), current(2), current_consumed(4), energy_consumed(4), battery_remaining(1)
            msg["function"] = payload[0]
            msg["id"] = payload[1]
            temp_bytes = struct.unpack('<h', payload[2:4])[0]
            msg["temperature"] = temp_bytes / 100.0 if temp_bytes != 0x7FFF else 0
            voltages = []
            for i in range(10):
                v = struct.unpack('<H', payload[4 + i*2:6 + i*2])[0]
                voltages.append(v / 1000.0 if v != 0xFFFF else 0)
            msg["voltages"] = voltages
            msg["current"] = struct.unpack('<h', payload[24:26])[0] / 100.0
            msg["current_consumed"] = struct.unpack('<I', payload[26:30])[0]
            msg["remaining"] = payload[30] if len(payload) > 30 else -1

        elif msg_id == 1 and len(payload) >= 31:
            # SYS_STATUS: onboard_control_sensors_present, onboard_control_sensors_enabled, onboard_control_sensors_health, load, voltage_current, remaining, drop_rate_comm, errors_comm, errors_count1, errors_count2, errors_count3, errors_count4, battery_remaining
            msg["name"] = "SYS_STATUS"
            msg["voltage"] = struct.unpack('<H', payload[10:12])[0] / 1000.0
            msg["current"] = struct.unpack('<h', payload[12:14])[0] / 100.0
            msg["remaining"] = payload[14]
            msg["battery"] = payload[14]
            msg["drop_rate_comm"] = struct.unpack('<H', payload[15:17])[0]
            msg["errors_comm"] = struct.unpack('<H', payload[17:19])[0]

        elif msg_id == 33 and len(payload) >= 28:
            # GLOBAL_POSITION_INT: time_boot_ms, lat, lon, alt, alt_relative, vx, vy, vz, hdg
            msg["name"] = "GLOBAL_POSITION_INT"
            msg["lat"] = struct.unpack('<i', payload[4:8])[0] / 1e7
            msg["lon"] = struct.unpack('<i', payload[8:12])[0] / 1e7
            msg["alt"] = struct.unpack('<i', payload[12:16])[0] / 1000.0
            msg["alt_relative"] = struct.unpack('<i', payload[16:20])[0] / 1000.0
            msg["hdg"] = struct.unpack('<H', payload[26:28])[0] / 100.0

        elif msg_id == 29 and len(payload) >= 20:
            # VFR_HUD: airspeed, groundspeed, heading, throttle, alt, climb
            msg["name"] = "VFR_HUD"
            msg["airspeed"] = struct.unpack('<f', payload[0:4])[0]
            msg["groundspeed"] = struct.unpack('<f', payload[4:8])[0]
            msg["heading"] = struct.unpack('<H', payload[8:10])[0]
            msg["throttle"] = struct.unpack('<H', payload[10:12])[0]
            msg["alt"] = struct.unpack('<f', payload[12:16])[0]
            msg["climb"] = struct.unpack('<f', payload[16:20])[0]

        elif msg_id == 141 and len(payload) >= 24:
            # ALTITUDE: altitude_monotonic, altitude_amsl, altitude_local, altitude_relative, altitude_terrain, altitude_bottom, clearance
            msg["name"] = "ALTITUDE"
            msg["alt_amsl"] = struct.unpack('<f', payload[4:8])[0]
            msg["alt_local"] = struct.unpack('<f', payload[8:12])[0]
            msg["alt_relative"] = struct.unpack('<f', payload[12:16])[0]
            msg["alt_terrain"] = struct.unpack('<f', payload[16:20])[0]

        elif msg_id == 30 and len(payload) >= 28:
            fields = struct.unpack('<Iffffff', payload[:28])
            msg["name"] = "ATTITUDE"
            msg["roll"] = fields[1]
            msg["pitch"] = fields[2]
            msg["yaw"] = fields[3]

        elif msg_id == 32 and len(payload) >= 28:
            fields = struct.unpack('<Iffffff', payload[:28])
            msg["name"] = "LOCAL_POSITION_NED"
            msg["x"] = fields[1]
            msg["y"] = fields[2]
            msg["z"] = fields[3]
            msg["vx"] = fields[4]
            msg["vy"] = fields[5]
            msg["vz"] = fields[6]

        return msg


class DroneConnection:
    def __init__(self, udp_target=("127.0.0.1", 14550)):
        self.udp_target = udp_target
        self.sock = None
        self.mav = MAVLink()
        self.running = False
        self.telemetry = {
            "connected": False,
            "armed": False,
            "lat": 0.0, "lon": 0.0, "alt": 0.0,
            "battery": -1, "voltage": 0.0, "heading": 0.0,
            "satellites": 0, "fix_type": 0,
            "mode": "UNKNOWN",
            "roll": 0.0, "pitch": 0.0,
            "vel_x": 0.0, "vel_y": 0.0, "vel_z": 0.0,
        }
        self._lock = threading.Lock()
        self._listener = None

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(1.0)
        self.sock.bind(("0.0.0.0", 14555))
        self.sock.connect(self.udp_target)
        self.running = True
        self._listener = threading.Thread(target=self._listen, daemon=True)
        self._listener.start()
        return True

    def _listen(self):
        hb_counter = 0
        while self.running:
            try:
                self.sock.sendall(self.mav.encode_heartbeat())
                hb_counter += 1
            except:
                pass
            try:
                while True:
                    data, addr = self.sock.recvfrom(4096)
                    msg = MAVLink.decode_message(data)
                    if msg:
                        self._process_message(msg)
            except socket.timeout:
                pass
            except:
                pass
            time.sleep(0.5 if hb_counter % 2 == 0 else 0.1)

    def _process_message(self, msg):
        with self._lock:
            self.telemetry["connected"] = True
            if msg.get("name") == "HEARTBEAT":
                self.telemetry["armed"] = msg.get("armed", False)
                custom_mode = msg.get("custom_mode", 0)
                main_mode = custom_mode & 0xFF  # PX4: bits 0-7 = main_mode
                mode_map = {0: "MANUAL", 1: "ALTCTL", 2: "POSCTL",
                           3: "AUTO", 4: "ACRO", 5: "OFFBOARD",
                           6: "STABILIZED", 7: "RATTITUDE",
                           8: "AUTO.LOITER", 9: "AUTO.RTL",
                           10: "AUTO.LAND", 11: "AUTO.TAKEOFF"}
                self.telemetry["mode"] = mode_map.get(main_mode, f"CUSTOM({main_mode})")
            elif msg.get("name") == "GPS_RAW_INT":
                self.telemetry["lat"] = msg.get("lat", 0)
                self.telemetry["lon"] = msg.get("lon", 0)
                self.telemetry["alt"] = msg.get("alt", 0)
                self.telemetry["fix_type"] = msg.get("fix_type", 0)
                self.telemetry["satellites"] = msg.get("satellites", 0)
            elif msg.get("name") == "GLOBAL_POSITION_INT":
                self.telemetry["lat"] = msg.get("lat", 0)
                self.telemetry["lon"] = msg.get("lon", 0)
                if msg.get("alt_relative", 0) != 0:
                    self.telemetry["alt"] = msg.get("alt_relative", 0)
                elif msg.get("alt", 0) != 0:
                    self.telemetry["alt"] = msg.get("alt", 0)
                self.telemetry["heading"] = msg.get("hdg", 0)
            elif msg.get("name") == "VFR_HUD":
                if msg.get("alt", 0) != 0:
                    self.telemetry["alt"] = msg.get("alt", 0)
                self.telemetry["heading"] = msg.get("heading", 0)
            elif msg.get("name") == "ALTITUDE":
                if msg.get("alt_relative", 0) != 0:
                    self.telemetry["alt"] = msg.get("alt_relative", 0)
            elif msg.get("name") == "BATTERY_STATUS":
                self.telemetry["battery"] = msg.get("remaining", -1)
                self.telemetry["voltage"] = sum(v for v in msg.get("voltages", [0]*10) if v > 0) / max(1, sum(1 for v in msg.get("voltages", [0]*10) if v > 0))
            elif msg.get("name") == "SYS_STATUS":
                if msg.get("battery") is not None:
                    self.telemetry["battery"] = msg.get("battery", -1)
                self.telemetry["voltage"] = msg.get("voltage", 0)
            elif msg.get("name") == "ATTITUDE":
                self.telemetry["heading"] = msg.get("yaw", 0)
                self.telemetry["roll"] = msg.get("roll", 0)
                self.telemetry["pitch"] = msg.get("pitch", 0)
            elif msg.get("name") == "LOCAL_POSITION_NED":
                self.telemetry["vel_x"] = msg.get("vx", 0)
                self.telemetry["vel_y"] = msg.get("vy", 0)
                self.telemetry["vel_z"] = msg.get("vz", 0)

    def get_telemetry(self):
        with self._lock:
            return dict(self.telemetry)

    def _send_raw_heartbeat(self):
        if not self.sock:
            return False
        try:
            self.sock.sendall(self.mav.encode_heartbeat())
            return True
        except:
            return False

    def _send_command(self, command_id, param1=0, param2=0, param3=0,
                      param4=0, param5=0, param6=0, param7=0):
        if not self.sock:
            return False
        packet = self.mav.encode_command_long(command_id, param1, param2,
                                              param3, param4, param5, param6, param7)
        try:
            self.sock.sendall(packet)
            return True
        except:
            return False

    def arm(self):
        return self._send_command(MAV_CMD["COMPONENT_ARM_DISARM"], 1)

    def disarm(self):
        return self._send_command(MAV_CMD["COMPONENT_ARM_DISARM"], 0)

    def takeoff(self, altitude=10):
        return self._send_command(MAV_CMD["NAV_TAKEOFF"], 0, 0, 0, 0, 0, 0, altitude)

    def land(self):
        return self._send_command(MAV_CMD["NAV_LAND"])

    def rtl(self):
        return self._send_command(MAV_CMD["NAV_RETURN_TO_LAUNCH"])

    def goto_position(self, lat, lon, alt):
        return self._send_command(MAV_CMD["NAV_WAYPOINT"], 0, 0, 0, 0, lat, lon, alt)

    def set_speed(self, speed_ms):
        return self._send_command(MAV_CMD["DO_CHANGE_SPEED"], 0, speed_ms, -1, 0)

    def close(self):
        self.running = False
        if self._listener:
            self._listener.join(timeout=2)
        if self.sock:
            self.sock.close()
