#!/usr/bin/env python3
"""
Minimal MAVLink v2 protocol implementation for drone control.

Key fixes vs original:
  - goto_position uses COMMAND_LONG with NAV_WAYPOINT (msg 76, cmd 16)
    so it works in GUIDED mode.  msg 86 requires OFFBOARD mode in PX4,
    which we don't use after takeoff.
  - encode_heartbeat restored properly.
"""

import socket
import struct
import time
import threading
import math

# ── CRC extras (per MAVLink spec) ────────────────────────────────────────────
CRC_EXTRA = {
    0:   50,   # HEARTBEAT
    24:  24,   # GPS_RAW_INT
    29:  11,   # VFR_HUD
    30:  39,   # ATTITUDE
    32: 185,   # LOCAL_POSITION_NED
    33: 104,   # GLOBAL_POSITION_INT
    76: 152,   # COMMAND_LONG
    86:   5,   # SET_POSITION_TARGET_GLOBAL_INT
   141: 113,   # ALTITUDE
   147: 154,   # BATTERY_STATUS
}

# ── MAVLink command IDs ───────────────────────────────────────────────────────
MAV_CMD = {
    "COMPONENT_ARM_DISARM":  400,
    "NAV_TAKEOFF":            22,
    "NAV_LAND":               21,
    "NAV_RETURN_TO_LAUNCH":   20,
    "NAV_WAYPOINT":           16,
    "DO_REPOSITION":          51,
    "DO_CHANGE_SPEED":       178,
    "DO_SET_MODE":           176,
    "CONDITION_YAW":         115,
}

# ── MAVLink frame types ───────────────────────────────────────────────────────
MAV_FRAME = {
    "GLOBAL": 0,
    "GLOBAL_RELATIVE_ALT": 3,  # alt relative to home (AGL)
}

MAV_MODE_FLAG = {"SAFETY_ARMED": 128, "MANUAL": 1, "GUIDED": 4,
                 "AUTO": 8, "STABILIZE": 2}
MAV_STATE     = {"UNINIT": 0, "BOOT": 1, "CALIBRATING": 2, "STANDBY": 3,
                 "ACTIVE": 4, "CRITICAL": 5, "EMERGENCY": 6, "POWEROFF": 7}
MAV_TYPE      = {"QUADROTOR": 2, "HEXAROTOR": 3, "OCTOROTOR": 4, "GCS": 6}


# ── CRC-16/MCRF4XX ───────────────────────────────────────────────────────────
class CRC16:
    def __init__(self):
        self.crc = 0xFFFF

    def accumulate(self, data: bytes):
        for b in data:
            self.crc ^= b << 8
            for _ in range(8):
                if self.crc & 0x8000:
                    self.crc = (self.crc << 1) ^ 0x1021
                else:
                    self.crc <<= 1
                self.crc &= 0xFFFF


# ── MAVLink encoder ───────────────────────────────────────────────────────────
class MAVLink:
    def __init__(self, source_system=255, source_component=0):
        self.seq = 0
        self.source_system    = source_system
        self.source_component = source_component
        self.target_system    = 1
        self.target_component = 1

    # ── internal helpers ──────────────────────────────────────────────────────
    def _crc(self, msg_id: int, payload: bytes) -> bytes:
        c = CRC16()
        c.accumulate(payload)
        c.accumulate(bytes([CRC_EXTRA.get(msg_id, 0)]))
        return struct.pack('<H', c.crc)

    def _header(self, msg_id: int, payload_len: int) -> bytes:
        h = struct.pack('<BBBBBBB',
            0xFD, payload_len, 0, 0,
            self.seq & 0xFF,
            self.source_system,
            self.source_component)
        h += struct.pack('<I', msg_id)[:3]
        self.seq = (self.seq + 1) & 0xFF
        return h

    def _packet(self, msg_id: int, payload: bytes) -> bytes:
        h = self._header(msg_id, len(payload))
        return h + payload + self._crc(msg_id, payload)

    # ── HEARTBEAT (msg 0) ─────────────────────────────────────────────────────
    def encode_heartbeat(self) -> bytes:
        payload = struct.pack('<IBBBBB',
            0,                      # custom_mode
            MAV_TYPE["GCS"],        # type
            0,                      # autopilot
            0,                      # base_mode
            MAV_STATE["ACTIVE"],    # system_status
            3)                      # mavlink_version
        return self._packet(0, payload)

    # ── COMMAND_LONG (msg 76) ─────────────────────────────────────────────────
    def encode_command_long(self, command,
                            p1=0.0, p2=0.0, p3=0.0, p4=0.0,
                            p5=0.0, p6=0.0, p7=0.0) -> bytes:
        payload = struct.pack('<BBHBfffffff',
            self.target_system, self.target_component,
            command, 0,
            float(p1), float(p2), float(p3), float(p4),
            float(p5), float(p6), float(p7))
        return self._packet(76, payload)

    # ── SET_POSITION_TARGET_GLOBAL_INT (msg 86) ───────────────────────────────
    def encode_set_position_target(self, lat: float, lon: float, alt: float,
                                    yaw_deg: float = None,
                                    frame: int = MAV_FRAME["GLOBAL_RELATIVE_ALT"]) -> bytes:
        """
        MAVLink 2 wire format — fields ordered by byte-size descending.

        type_mask bits (1 = ignore):
          bits 0-2: pos x,y,z     bits 3-5: vel vx,vy,vz
          bits 6-8: acc afx,afy,afz  bit 9: force
          bit 10: yaw              bit 11: yaw_rate
        """
        if yaw_deg is not None:
            type_mask = 0x0DF8   # use pos(0-2) + yaw(10), ignore vel(3-5)+acc(6-8)+yaw_rate(11)
            yaw_rad = math.radians(yaw_deg % 360)
        else:
            type_mask = 0x0FF8   # use pos(0-2), ignore everything else
            yaw_rad = 0.0

        lat_int = int(lat * 1e7)
        lon_int = int(lon * 1e7)

        payload = struct.pack('<Iii', 0, lat_int, lon_int)           # time_boot_ms, lat, lon
        payload += struct.pack('<f', float(alt))                      # alt
        payload += struct.pack('<fff', 0.0, 0.0, 0.0)                # vx, vy, vz
        payload += struct.pack('<fff', 0.0, 0.0, 0.0)                # afx, afy, afz
        payload += struct.pack('<ff', yaw_rad, 0.0)                  # yaw, yaw_rate
        payload += struct.pack('<H', type_mask)                      # type_mask
        payload += struct.pack('<BBB',
            self.target_system,
            self.target_component,
            frame)                                                   # target_sys, comp, frame
        return self._packet(86, payload)

    # ── decode ────────────────────────────────────────────────────────────────
    @staticmethod
    def decode_message(data: bytes):
        if len(data) < 10 or data[0] != 0xFD:
            return None
        payload_len = data[1]
        msg_id  = struct.unpack('<I', data[7:10] + b'\x00')[0]
        payload = data[10:10 + payload_len]
        msg = {"id": msg_id, "payload": payload}

        if msg_id == 0 and len(payload) >= 9:
            f = struct.unpack('<IBBBBB', payload[:9])
            msg.update(name="HEARTBEAT", custom_mode=f[0], type=f[1],
                       autopilot=f[2], base_mode=f[3], system_status=f[4],
                       mavlink_version=f[5] if len(payload) > 9 else 0,
                       armed=bool(f[3] & 128))
            main_mode = f[0] & 0xFF
            mode_map = {0:"MANUAL",1:"ALTCTL",2:"POSCTL",3:"AUTO",4:"ACRO",
                        5:"OFFBOARD",6:"STABILIZED",7:"RATTITUDE",
                        8:"AUTO.LOITER",9:"AUTO.RTL",10:"AUTO.LAND",11:"AUTO.TAKEOFF"}
            msg["mode"] = mode_map.get(main_mode, f"CUSTOM({main_mode})")

        elif msg_id == 24 and len(payload) >= 30:
            f = struct.unpack('<QiiiHHHHBB', payload[:30])
            msg.update(name="GPS_RAW_INT", lat=f[1]/1e7, lon=f[2]/1e7,
                       alt=f[3]/1e3, eph=f[4], epv=f[5], vel=f[6],
                       cog=f[7], fix_type=f[8], satellites=f[9])

        elif msg_id == 33 and len(payload) >= 28:
            msg.update(name="GLOBAL_POSITION_INT",
                       lat=struct.unpack('<i', payload[4:8])[0] / 1e7,
                       lon=struct.unpack('<i', payload[8:12])[0] / 1e7,
                       alt=struct.unpack('<i', payload[12:16])[0] / 1000.0,
                       alt_relative=struct.unpack('<i', payload[16:20])[0] / 1000.0,
                       hdg=struct.unpack('<H', payload[26:28])[0] / 100.0)

        elif msg_id == 29 and len(payload) >= 20:
            msg.update(name="VFR_HUD",
                       airspeed=struct.unpack('<f', payload[0:4])[0],
                       groundspeed=struct.unpack('<f', payload[4:8])[0],
                       heading=struct.unpack('<h', payload[8:10])[0],
                       throttle=struct.unpack('<H', payload[10:12])[0],
                       alt=struct.unpack('<f', payload[12:16])[0],
                       climb=struct.unpack('<f', payload[16:20])[0])

        elif msg_id == 141 and len(payload) >= 24:
            msg.update(name="ALTITUDE",
                       alt_amsl=struct.unpack('<f', payload[4:8])[0],
                       alt_local=struct.unpack('<f', payload[8:12])[0],
                       alt_relative=struct.unpack('<f', payload[12:16])[0],
                       alt_terrain=struct.unpack('<f', payload[16:20])[0])

        elif msg_id == 30 and len(payload) >= 28:
            f = struct.unpack('<Iffffff', payload[:28])
            msg.update(name="ATTITUDE", roll=f[1], pitch=f[2], yaw=f[3])

        elif msg_id == 32 and len(payload) >= 28:
            f = struct.unpack('<Iffffff', payload[:28])
            msg.update(name="LOCAL_POSITION_NED",
                       x=f[1], y=f[2], z=f[3], vx=f[4], vy=f[5], vz=f[6])

        elif msg_id == 147 and len(payload) >= 31:
            voltages = [struct.unpack('<H', payload[4+i*2:6+i*2])[0]/1000.0
                        for i in range(10)]
            msg.update(name="BATTERY_STATUS",
                       voltages=voltages,
                       current=struct.unpack('<h', payload[24:26])[0]/100.0,
                       remaining=payload[30])

        elif msg_id == 1 and len(payload) >= 15:
            msg.update(name="SYS_STATUS",
                       voltage=struct.unpack('<H', payload[10:12])[0]/1000.0,
                       current=struct.unpack('<h', payload[12:14])[0]/100.0,
                       battery=payload[14])

        return msg


# ── DroneConnection ───────────────────────────────────────────────────────────
class DroneConnection:
    def __init__(self, udp_target=("127.0.0.1", 14550), bind_port=14555):
        self.udp_target = udp_target
        self.bind_port  = bind_port
        self.sock       = None
        self.mav        = MAVLink()
        self.running    = False
        self.telemetry  = {
            "connected": False, "armed": False,
            "lat": 0.0, "lon": 0.0, "alt": 0.0,
            "battery": -1, "voltage": 0.0, "heading": 0.0,
            "satellites": 0, "fix_type": 0,
            "mode": "UNKNOWN", "speed": 0.0,
            "roll": 0.0, "pitch": 0.0,
            "vel_x": 0.0, "vel_y": 0.0, "vel_z": 0.0,
        }
        self._lock     = threading.Lock()
        self._listener = None

    # ── connect / listen ──────────────────────────────────────────────────────
    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(1.0)
        self.sock.bind(("0.0.0.0", self.bind_port))
        self.sock.connect(self.udp_target)
        self.running   = True
        self._listener = threading.Thread(target=self._listen, daemon=True)
        self._listener.start()
        return True

    def _listen(self):
        hb_tick = 0
        while self.running:
            try:
                with self._lock:
                    self.sock.sendall(self.mav.encode_heartbeat())
                hb_tick += 1
            except Exception:
                pass
            try:
                while True:
                    data, _ = self.sock.recvfrom(4096)
                    msg = MAVLink.decode_message(data)
                    if msg:
                        self._process(msg)
            except socket.timeout:
                pass
            except Exception:
                pass
            time.sleep(0.5 if hb_tick % 2 == 0 else 0.1)

    def _process(self, msg):
        with self._lock:
            t = self.telemetry
            t["connected"] = True
            name = msg.get("name", "")

            if name == "HEARTBEAT":
                t["armed"] = msg.get("armed", False)
                t["mode"]  = msg.get("mode", "UNKNOWN")

            elif name in ("GPS_RAW_INT",):
                t["lat"]        = msg.get("lat", t["lat"])
                t["lon"]        = msg.get("lon", t["lon"])
                t["alt"]        = msg.get("alt", t["alt"])
                t["fix_type"]   = msg.get("fix_type", 0)
                t["satellites"] = msg.get("satellites", 0)

            elif name == "GLOBAL_POSITION_INT":
                t["lat"]     = msg.get("lat", t["lat"])
                t["lon"]     = msg.get("lon", t["lon"])
                # prefer alt_relative (AGL) over AMSL
                rel = msg.get("alt_relative", 0)
                t["alt"]     = rel if rel != 0 else msg.get("alt", t["alt"])
                # hdg is in centidegrees → radians
                hdg = msg.get("hdg", None)
                if hdg is not None:
                    t["heading"] = math.radians(hdg)

            elif name == "VFR_HUD":
                if msg.get("alt", 0) != 0:
                    t["alt"] = msg["alt"]
                # heading is in degrees → radians
                hdg = msg.get("heading", None)
                if hdg is not None:
                    t["heading"] = math.radians(hdg)
                t["speed"]   = msg.get("groundspeed", 0)

            elif name == "ALTITUDE":
                rel = msg.get("alt_relative", 0)
                if rel != 0:
                    t["alt"] = rel

            elif name == "ATTITUDE":
                t["heading"] = msg.get("yaw", t["heading"])  # already radians
                t["roll"]    = msg.get("roll", 0)
                t["pitch"]   = msg.get("pitch", 0)

            elif name == "LOCAL_POSITION_NED":
                t["vel_x"] = msg.get("vx", 0)
                t["vel_y"] = msg.get("vy", 0)
                t["vel_z"] = msg.get("vz", 0)

            elif name == "BATTERY_STATUS":
                t["battery"] = msg.get("remaining", -1)
                vs = [v for v in msg.get("voltages", []) if v > 0]
                t["voltage"] = sum(vs) / len(vs) if vs else 0

            elif name == "SYS_STATUS":
                if msg.get("battery") is not None:
                    t["battery"] = msg["battery"]
                t["voltage"] = msg.get("voltage", t["voltage"])

    def get_telemetry(self):
        with self._lock:
            return dict(self.telemetry)

    # ── raw send helpers ──────────────────────────────────────────────────────
    def _send_raw_heartbeat(self):
        if not self.sock:
            return False
        try:
            with self._lock:
                self.sock.sendall(self.mav.encode_heartbeat())
            return True
        except Exception:
            return False

    def _send_command(self, cmd_id,
                      p1=0.0, p2=0.0, p3=0.0, p4=0.0,
                      p5=0.0, p6=0.0, p7=0.0) -> bool:
        if not self.sock:
            return False
        pkt = self.mav.encode_command_long(cmd_id, p1, p2, p3, p4, p5, p6, p7)
        try:
            with self._lock:
                self.sock.sendall(pkt)
            return True
        except Exception:
            return False

    # ── flight commands ───────────────────────────────────────────────────────
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

    def set_speed(self, speed_ms):
        return self._send_command(MAV_CMD["DO_CHANGE_SPEED"], 0, speed_ms, -1, 0)

    # ── yaw command ───────────────────────────────────────────────────────────
    def set_yaw(self, yaw_deg: float, relative: bool = False, speed: float = 45.0):
        """
        Rotate to absolute heading (relative=False) or rotate by angle (relative=True).
        speed: yaw rate in deg/s (default 45, was 20 for faster turns)
        """
        return self._send_command(
            MAV_CMD["CONDITION_YAW"],
            float(yaw_deg % 360),   # p1 = target angle deg
            speed,                  # p2 = yaw speed deg/s (increased for faster turns)
            -1.0,                    # p3 = direction (-1=auto, shortest path)
            1.0 if relative else 0.0  # p4 = 0=absolute, 1=relative
        )

    def goto_with_yaw(self, lat: float, lon: float, alt: float):
        """
        Turn to face the target first, then go there — much faster response.
        Computes bearing from current position to target and yaws before moving.
        """
        t = self.get_telemetry()
        dlat = lat - t["lat"]
        dlon = lon - t["lon"]
        bearing = math.degrees(math.atan2(dlon * math.cos(math.radians(t["lat"])), dlat))
        bearing = (bearing + 360) % 360
        self.set_yaw(bearing)
        time.sleep(0.1)
        return self.goto_position(lat, lon, alt)

    # ── goto position  (COMMAND_LONG → NAV_WAYPOINT) ─────────────────────────
    def goto_position(self, lat: float, lon: float, alt: float,
                      use_relative_alt: bool = True) -> bool:
        """
        Fly to GPS position via COMMAND_LONG with NAV_WAYPOINT (cmd 16).

        Works in GUIDED mode (set by NAV_TAKEOFF). PX4 ignores msg 86 unless
        in OFFBOARD mode, so we use COMMAND_LONG which is accepted in GUIDED.
        Sends 3x for reliability.
        """
        ok = True
        for _ in range(3):
            ok = self._send_command(
                MAV_CMD["NAV_WAYPOINT"],
                0,              # p1 = hold time (sec)
                0,              # p2 = acceptance radius
                0,              # p3 = 0 (pass through)
                1.0 if use_relative_alt else 0.0,  # p4 = 0=abs, 1=rel alt
                float(lat), float(lon), float(alt),
            ) and ok
            time.sleep(0.02)
        return ok

    # ── strafe helpers ────────────────────────────────────────────────────────
    def strafe(self, direction: str, distance: float = 3):
        t = self.get_telemetry()
        yaw = t.get("heading", 0)
        if direction == 'up':
            return self.goto_position(t["lat"], t["lon"], t["alt"] + distance)
        if direction == 'down':
            return self.goto_position(t["lat"], t["lon"],
                                      max(0.5, t["alt"] - distance))
        angle = yaw + (math.pi / 2 if direction == 'right' else -math.pi / 2)
        dlat = distance * math.cos(angle) / 111000
        dlon = (distance * math.sin(angle)
                / (111000 * math.cos(math.radians(t["lat"]))))
        return self.goto_position(t["lat"] + dlat, t["lon"] + dlon, t["alt"])

    def set_position(self, vx, vy, vz):
        """Legacy: hover at current position."""
        t = self.get_telemetry()
        return self.goto_position(t["lat"], t["lon"], t["alt"])

    def close(self):
        self.running = False
        if self._listener:
            self._listener.join(timeout=2)
        if self.sock:
            self.sock.close()