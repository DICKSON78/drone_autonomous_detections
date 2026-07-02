#!/usr/bin/env python3
import array
import json
import math
import os
import socket
import sys
import threading
import time
import traceback

VENV_PYTHON = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'venv', 'bin', 'python3'))
if os.path.abspath(sys.executable) != VENV_PYTHON:
    if os.path.exists(VENV_PYTHON):
        print(f"[BRIDGE] Re-execing with {VENV_PYTHON}")
        sys.stdout.flush()
        os.execv(VENV_PYTHON, [VENV_PYTHON] + sys.argv)
    else:
        print(f"[BRIDGE] VENV_PYTHON {VENV_PYTHON} not found, staying with {sys.executable}")
else:
    print(f"[BRIDGE] Already running under {sys.executable}")

import numpy as np

from controller import Robot, Supervisor, GPS, InertialUnit, Gyro, Camera

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from detection import YOLODetector, ObstacleDetection, detect_from_webots

src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'src')
sys.path.insert(0, src_path)
from nlp_module import DroneNLP

_READY_FILE = "/tmp/bridge_ready.json"

def _write_ready(name: str, ok: bool):
    try:
        d = {}
        if os.path.exists(_READY_FILE):
            with open(_READY_FILE) as f:
                d = json.load(f)
        d[name] = ok
        d["ts"] = time.time()
        with open(_READY_FILE, "w") as f:
            json.dump(d, f)
    except Exception:
        pass

ZONE_LABELS = ["Zone A (City)", "Road →", "Road →", "Zone B (Road Course)",
               "Zone B (Road Course)", "← Return", "Home"]

def _zone_name(idx: int) -> str:
    return ZONE_LABELS[idx] if 0 <= idx < len(ZONE_LABELS) else f"WP {idx+1}"

def _current_zone_name(gps_x: float) -> str:
    if gps_x < -5:
        return "Zone A"
    elif gps_x < 35:
        return "Road"
    elif gps_x < 70:
        return "Zone B"
    return "Return"

try:
    from pymavlink.dialects.v20 import common as mavlink
except ImportError:
    from pymavlink.dialects.v10 import common as mavlink

REF_LAT = -6.21745
REF_LON = 35.81396
REF_ALT = 1120.0

# ===== ZONE A — Existing buildings/trees (west side) =====
CIVE_BUILDINGS = [
    (15, -10), (20, 15), (-20, 25),          # SimpleBuilding
    (-43.87, -19.84), (-44.26, -27.34),       # Windmills
    (-46.24, 30.57), (-38.75, 23.4),          # Windmills
    (-50.35, 11.25),                           # SmallManor
]
CIVE_TREES = [
    (-14.01, -14.48), (-19.62, -24.38),
    (-22.01, 6.2), (-10.69, -25.13),
    (-14.34, 14.56), (-26.63, -7.17),
    (-9.37, 14.02), (15, 25),
]

# ===== ZONE B — Road obstacles (east side, along the connecting road) =====
CIVE_ROAD_OBS_CONES = [
    (38, -5), (42, -6), (46, -4), (50, -6), (55, -4),   # cones blocking road
    (72, 5), (78, 12), (84, 18),                           # cones on curve
]
CIVE_ROAD_OBS_BOXES = [
    (44, -7), (52, -3), (60, -5), (88, 22),               # boxes on road
]
CIVE_ROAD_OBS_OTHER = [
    (65, -3.5),                                            # Tesla on road
]
CIVE_ROAD_OBS = CIVE_ROAD_OBS_CONES + CIVE_ROAD_OBS_BOXES + CIVE_ROAD_OBS_OTHER

CIVE_OBS = np.array(CIVE_BUILDINGS + CIVE_TREES + CIVE_ROAD_OBS, dtype=np.float32)

# Path waypoints (x, y) — forms a loop through both zones via the connecting road
# Zone A (west) → Road → Zone B (east) → Return
WAYPOINTS = [
    (-15, 0),     # WP1: Head west into Zone A (building area)
    (10, -5),     # WP2: Approach the connecting road
    (30, -5),     # WP3: Follow road east toward Zone B
    (55, -5),     # WP4: Zone B — road obstacle section begins
    (75, 15),     # WP5: Zone B — navigate through obstacles on curve
    (40, 20),     # WP6: Head back toward origin (cross-country)
    (0, 0),       # WP7: Return home
]
WAYPOINT_RADIUS = 20.0

MAV_TYPE_QUADROTOR = 2
MAV_AUTOPILOT_GENERIC = 0
MAV_MODE_FLAG_ARMED = 128
MAV_STATE_STANDBY = 3
MAV_STATE_ACTIVE = 4
MAV_FRAME_LOCAL_NED = 1
MAV_FRAME_BODY_OFFSET_NED = 8


def clamp(val, lo, hi):
    return max(lo, min(hi, val))


def gps_from_webots(x, y, z):
    lat = REF_LAT + y / 111320.0
    lon = REF_LON + x / (111320.0 * math.cos(math.radians(REF_LAT)))
    alt = REF_ALT + z
    return lat, lon, alt


class MavicBridge(Supervisor):
    FLIGHT_MODE_MANUAL = 0
    FLIGHT_MODE_GUIDED = 4

    # Motor/PID — thrust = K_VERTICAL_THRUST + vertical_input  →  motor velocity
    K_VERTICAL_THRUST = 61.0

    K_VEL_P = 1.0
    K_VEL_ALT_P = 5.0
    MAX_TILT = 6.0
    MAX_YAW_RATE = 0.5
    MOTOR_MAX = 200
    K_VEL_XY = 3.5          # N per m/s horizontal velocity error (world-frame force)
    K_TILT = 0.5            # Nm per m/s velocity error (visual tilt torque)

    # Propeller thrust constant (from Mavic2Pro.proto)
    THRUST_CONST = 0.00026          # N·s²/rad² per prop

    YOLO_INTERVAL = 0.5
    PPO_INTERVAL = 0.2
    NLP_INTERVAL = 0.2
    TELEMETRY_INTERVAL = 0.05
    HEARTBEAT_INTERVAL = 0.5
    TARGET_ALT_DEFAULT = 5.0

    def __init__(self):
        Robot.__init__(self)
        self.time_step = int(self.getBasicTimeStep())
        self._setup_devices()
        self._setup_mavlink()
        self._setup_state()
        self._setup_ai()
        self._last_ts = time.time()
        # Position PID for waypoint horizontal control
        self._pos_integral_x = 0.0
        self._pos_integral_y = 0.0

    def _setup_devices(self):
        self.camera = self.getDevice("camera")
        self.camera.enable(self.time_step)
        self.cam_w = self.camera.getWidth()
        self.cam_h = self.camera.getHeight()

        self.imu = self.getDevice("inertial unit")
        self.imu.enable(self.time_step)
        self.gps = self.getDevice("gps")
        self.gps.enable(self.time_step)
        self.gyro = self.getDevice("gyro")
        self.gyro.enable(self.time_step)

        self.fl_motor = self.getDevice("front left propeller")
        self.fr_motor = self.getDevice("front right propeller")
        self.rl_motor = self.getDevice("rear left propeller")
        self.rr_motor = self.getDevice("rear right propeller")
        self.cam_pitch = self.getDevice("camera pitch")
        self.cam_pitch.setPosition(0.7)
        try:
            self.view_node = self.getFromDef("MAIN_VIEW")
        except:
            self.view_node = None

        for m in [self.fl_motor, self.fr_motor, self.rl_motor, self.rr_motor]:
            m.setPosition(float("inf"))
            m.setVelocity(0)

    def _setup_mavlink(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.settimeout(0.005)
        self.sock.bind(("0.0.0.0", 14550))
        self.mav = mavlink.MAVLink(None, srcSystem=1, srcComponent=1)
        self._gcs_addr = None
        # QGC forward socket — sends MAVLink to QGroundControl on :14550
        self._qgc_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Detection broadcast socket — sends YOLO results as JSON
        self._det_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._det_sock.connect(("127.0.0.1", 14551))

    def _setup_state(self):
        self.armed = False
        self.in_air = False
        self.landing_mode = False
        self.flight_mode = self.FLIGHT_MODE_MANUAL
        self.target_lat = REF_LAT
        self.target_lon = REF_LON
        self.target_alt = self.TARGET_ALT_DEFAULT
        self.target_vx = 0.0
        self.target_vy = 0.0
        self.target_vz = 0.0
        self.target_yaw_rate = 0.0

        self._start_time = time.time()
        self._takeoff_start = 0.0
        self._waypoint_idx = 0
        self._wp_sent_feedback = False

        self.roll = self.pitch = self.yaw = 0.0
        self.yaw_target = 0.0
        self.yaw_integral = 0.0
        self.gps_x = self.gps_y = self.gps_z = 0.0
        self.gps_lat = REF_LAT
        self.gps_lon = REF_LON
        self.gps_alt = REF_ALT
        self.vx = self.vy = self.vz = 0.0
        self.gyro_x = self.gyro_y = self.gyro_z = 0.0

        self._prev_gps = None
        self._alt_integral = 0.0

    def _setup_ai(self):
        self.yolo = None
        self.yolo_ready = False
        self.last_yolo = 0.0
        self.last_ppo = 0.0
        self.last_nlp = 0.0
        self.last_telemetry = 0.0
        self.last_heartbeat = 0.0
        self.last_statustext = 0.0
        self.detections: list = []
        self.obstacles_for_nlp: list = []
        self.ppo_action = [0.0, 0.0, 0.0]
        self.ppo_confidence = 0.0
        self.ppo_model = None

        self.nlp = DroneNLP()
        self.nlp_explanation = ""
        self.nlp_severity = 6

    def _ensure_yolo(self):
        if self.yolo is None and not self.yolo_ready:
            try:
                self.yolo = YOLODetector()
                self.yolo_ready = True
                print("[YOLO] YOLOv8n detector loaded")
            except Exception as e:
                print(f"[YOLO] Failed to load: {e}")
                self.yolo_ready = True  # mark as tried so we don't retry

    def _ensure_ppo(self):
        if self.ppo_model is None:
            pkl_path = os.path.join(
                src_path, "models", "rl", "navigation_agent_cont.pkl"
            )
            try:
                import pickle as _pk
                with open(pkl_path, "rb") as _f:
                    data = _pk.load(_f)
                self._ppo_W = data["W"]
                self._ppo_b = data["b"]
                self._ppo_V = data["V"]
                self.ppo_model = True
                print(f"[PPO] Loaded evolved model {data.get('type')} "
                      f"({self._ppo_W.shape[0]}→{self._ppo_W.shape[1]}→{self._ppo_V.shape[1]})")
            except Exception as e:
                print(f"[PPO] Failed to load {pkl_path}: {e}; using rule-based fallback")
                self.ppo_model = False

    def _predict_ppo(self, obs: np.ndarray) -> np.ndarray:
        h = np.tanh(obs @ self._ppo_W + self._ppo_b)
        return h @ self._ppo_V

    def _recv_mavlink(self):
        try:
            data, addr = self.sock.recvfrom(4096)
            if self._gcs_addr is None or addr != self._gcs_addr:
                self._gcs_addr = addr
                print(f"[MAV] GCS connected from {addr}")
            for byte in data:
                try:
                    msg = self.mav.parse_char(bytes([byte]))
                    if msg is not None:
                        self._handle_msg(msg)
                except Exception:
                    pass
        except socket.timeout:
            pass
        except BlockingIOError:
            pass

    def _handle_msg(self, msg):
        t = msg.get_type()
        if t == "COMMAND_LONG":
            self._handle_command_long(msg)
        elif t == "COMMAND_INT":
            pass
        elif t == "SET_POSITION_TARGET_LOCAL_NED":
            self._handle_setpoint(msg)
        elif t == "MANUAL_CONTROL":
            self._handle_manual(msg)
        elif t == "HEARTBEAT":
            pass
        else:
            pass

    def _handle_command_long(self, msg):
        cmd = msg.command
        p1 = msg.param1
        p5, p6, p7 = msg.param5, msg.param6, msg.param7

        if cmd == mavlink.MAV_CMD_COMPONENT_ARM_DISARM:
            self.armed = (p1 == 1.0)
            print(f"[CMD] {'ARM' if self.armed else 'DISARM'}")
            if not self.armed:
                self.in_air = False
                self.landing_mode = False

        elif cmd == mavlink.MAV_CMD_NAV_TAKEOFF:
            alt_cmd = p7 if p7 > 0 else self.TARGET_ALT_DEFAULT
            print(f"[CMD] TAKEOFF to {alt_cmd:.1f}m")
            self.armed = True
            self.in_air = True
            self.target_alt = alt_cmd
            self._alt_integral = 0.0
            self._takeoff_start = time.time()
            self._set_waypoint(0)
            self._send_statustext(f"TAKEOFF to {alt_cmd}m, heading to waypoint 1/{len(WAYPOINTS)}")

        elif cmd == mavlink.MAV_CMD_NAV_LAND:
            print("[CMD] LAND")
            self.in_air = False
            self.landing_mode = True
            self.target_alt = -0.1
            self.target_vx = self.target_vy = self.target_vz = 0.0

        elif cmd == mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH:
            print("[CMD] RETURN TO LAUNCH")
            self.target_lat = REF_LAT
            self.target_lon = REF_LON
            self.target_alt = 15.0

        elif cmd == mavlink.MAV_CMD_NAV_WAYPOINT:
            if p5 != 0 and p6 != 0:
                print(f"[CMD] GOTO {p5:.6f}, {p6:.6f}, {p7:.1f}")
                self.target_lat = p5
                self.target_lon = p6
                self.target_alt = p7 if p7 > 0 else 15.0

        elif cmd == mavlink.MAV_CMD_DO_REPOSITION:
            if p5 != 0 and p6 != 0:
                print(f"[CMD] REPOSITION {p5:.6f}, {p6:.6f}, {p7:.1f}")
                self.target_lat = p5
                self.target_lon = p6
                self.target_alt = p7 if p7 > 0 else 15.0

        elif cmd == mavlink.MAV_CMD_DO_CHANGE_SPEED:
            print(f"[CMD] SET SPEED {p1:.1f} m/s")

        elif cmd == mavlink.MAV_CMD_DO_SET_MODE:
            if p1 == 1:
                self.flight_mode = int(p2) if p2 else self.FLIGHT_MODE_GUIDED
                print(f"[CMD] SET MODE to {self.flight_mode}")

        self._send_command_ack(cmd, 0)

    def _send_command_ack(self, cmd, result=0):
        try:
            ack = self.mav.command_ack_encode(cmd, result, 0, 0, 1).pack(self.mav)
            self._send_to_gcs(ack)
        except Exception:
            pass

    def _handle_setpoint(self, msg):
        if msg.target_system != 1:
            return
        type_mask = msg.type_mask
        POS_IGNORE = 0x01
        VEL_IGNORE = 0x02
        YAW_IGNORE = 0x08

        if not (type_mask & VEL_IGNORE):
            self.target_vx = msg.vx
            self.target_vy = msg.vy
            self.target_vz = msg.vz
        if not (type_mask & POS_IGNORE):
            self.target_lat = REF_LAT
            self.target_lon = REF_LON
        if not (type_mask & YAW_IGNORE):
            self.target_yaw_rate = msg.yaw_rate if hasattr(msg, 'yaw_rate') else 0.0

    def _handle_manual(self, msg):
        if msg.target_system != 1 and msg.target_system != 0:
            return
        x = clamp(msg.x / 1000.0, -1, 1) if msg.x != 0 else 0.0
        y = clamp(msg.y / 1000.0, -1, 1) if msg.y != 0 else 0.0
        z = clamp(msg.z / 1000.0, -1, 1) if msg.z != 0 else 0.0
        r = clamp(msg.r / 1000.0, -1, 1) if msg.r != 0 else 0.0
        self.target_vx = y * 3.0
        self.target_vy = x * 3.0
        self.target_vz = z * 1.5
        self.target_yaw_rate = r * 0.5
        if msg.button & 1:
            self.armed = True
        elif msg.button & 2:
            self.armed = False

    def _update_sensors(self):
        self.roll, self.pitch, self.yaw = self.imu.getRollPitchYaw()
        gps_vals = self.gps.getValues()
        self.gps_x, self.gps_y, self.gps_z = gps_vals
        self.gps_lat, self.gps_lon, self.gps_alt = gps_from_webots(
            self.gps_x, self.gps_y, self.gps_z
        )

        gyro_vals = self.gyro.getValues()
        self.gyro_x, self.gyro_y, self.gyro_z = gyro_vals

        dt = self.time_step / 1000.0
        if self._prev_gps is not None:
            self.vx = (gps_vals[0] - self._prev_gps[0]) / dt if dt > 0 else 0
            self.vy = (gps_vals[1] - self._prev_gps[1]) / dt if dt > 0 else 0
            self.vz = (gps_vals[2] - self._prev_gps[2]) / dt if dt > 0 else 0
        self._prev_gps = gps_vals

    def _body_velocities(self):
        sin_y = math.sin(self.yaw)
        cos_y = math.cos(self.yaw)
        vx_body = self.vy * cos_y + self.vx * sin_y
        vy_body = self.vy * sin_y - self.vx * cos_y
        return vx_body, vy_body

    def _run_yolo(self):
        now = time.time()
        if now - self.last_yolo < self.YOLO_INTERVAL:
            return
        self._ensure_yolo()
        self.last_yolo = now

        if not self.yolo_ready or self.yolo is None:
            return

        img = self.camera.getImage()
        if img is None:
            return

        dets = detect_from_webots(img, self.cam_w, self.cam_h, self.yolo)
        obstacles = []
        alt = max(0.1, self.gps_z)
        for d in dets:
            dist = d.estimate_distance(alt, self.cam_h)
            bh, bv = d.bearing(self.cam_w, self.cam_h)
            obstacles.append({
                "class_id": d.class_id,
                "class_name": d.class_name,
                "confidence": d.confidence,
                "bbox": d.bbox,
                "center": d.center,
                "width": d.width,
                "height": d.height,
                "distance": dist,
                "bearing_h": bh,
                "bearing_v": bv,
            })
        self.detections = obstacles
        self._send_detections()

    def _run_ppo(self):
        now = time.time()
        if now - self.last_ppo < self.PPO_INTERVAL:
            return
        self.last_ppo = now

        self._rule_based_action()

    def _build_ppo_obs(self):
        W = 60.0
        V_MAX = 3.0

        # Nearest from known obstacle positions
        nearest_dist = W
        nearest_bearing = 0.0

        for ox, oy in CIVE_OBS:
            dx = ox - self.gps_x
            dy = oy - self.gps_y
            d = math.hypot(dx, dy)
            if d < nearest_dist:
                nearest_dist = d
                nearest_bearing = math.atan2(dy, dx)

        # Blend with YOLO detections (real-time obstacle awareness)
        for d in self.detections:
            bh = d.get("bearing_h", 0.0)
            dist = d.get("distance", 100.0)
            if dist < 1.0 or dist > 50.0:
                continue
            # convert bearing to world-frame obstacle position
            obs_angle = bh + self.yaw
            ox = self.gps_x + dist * math.cos(obs_angle)
            oy = self.gps_y + dist * math.sin(obs_angle)
            # check if this detection is closer than current nearest
            dd = math.hypot(ox - self.gps_x, oy - self.gps_y)
            if dd < nearest_dist:
                nearest_dist = dd
                nearest_bearing = math.atan2(oy - self.gps_y, ox - self.gps_x)

        dlat = self.target_lat - self.gps_lat
        dlon = self.target_lon - self.gps_lon
        de = dlon * 111320.0 * math.cos(math.radians(self.gps_lat))  # east (meters)
        dn = dlat * 111320.0                                           # north (meters)
        dz = self.target_alt - self.gps_z
        td = math.hypot(dn, de, dz) + 1e-6

        drone_bearing = math.atan2(self.vy, self.vx)

        return np.array([
            self.gps_x / W,
            self.gps_y / W,
            self.gps_z / 30.0,
            self.vx / V_MAX,
            self.vy / V_MAX,
            self.vz / V_MAX,
            de / td,
            dn / td,
            dz / td,
            nearest_dist / W,
            math.sin(nearest_bearing),
            math.cos(nearest_bearing),
            math.sin(drone_bearing),
            math.cos(drone_bearing),
        ], dtype=np.float32)

    def _get_action_key(self) -> str:
        vx, vy, vz = self.ppo_action
        eps = 0.3
        if abs(vx) < eps and abs(vy) < eps:
            return "hover" if abs(vz) < 0.3 else "ascend" if vz > 0 else "descend"
        if abs(vy) > abs(vx):
            return "strafe_right" if vy > 0 else "strafe_left"
        return "forward"

    def _rule_based_action(self):
        vx, vy, vz = 0.0, 0.0, 0.0

        # Obstacle avoidance — proportional response by distance + bearing
        nearest = None
        nearest_dist = 100.0
        for d in self.detections:
            dist = d.get("distance", 100.0)
            if dist < nearest_dist:
                nearest_dist = dist
                nearest = d

        AVOID_THRESHOLD = 12.0
        if nearest and nearest_dist < AVOID_THRESHOLD:
            bh = nearest.get("bearing_h", 0.0)
            # Intensity scales from 0 at threshold to 1 at 1.5m
            intensity = clamp(1.0 - (nearest_dist - 1.5) / (AVOID_THRESHOLD - 1.5), 0.0, 1.0)
            # Dodge laterally away from obstacle bearing, with forward bias
            vy = clamp(-bh * 4.0 * intensity, -2.0, 2.0)
            vx = clamp(1.5 * intensity, 0.5, 1.5)
            vz = clamp(1.0 * intensity, 0.0, 1.0)
            self.ppo_confidence = 0.5 + 0.4 * intensity
            self.ppo_action = [vx, vy, vz]
            self.target_vx, self.target_vy, self.target_vz = vx, vy, vz
            return

        # Waypoint following
        if self.in_air and len(WAYPOINTS) > 0:
            tx, ty = WAYPOINTS[self._waypoint_idx]
            dx = tx - self.gps_x
            dy = ty - self.gps_y
            dist_wp = math.hypot(dx, dy)
            if dist_wp > 0.5:
                speed = clamp(dist_wp * 0.5, 0.5, 2.0)
                # World-frame velocity toward waypoint → body frame
                wx = dx / dist_wp * speed
                wy = dy / dist_wp * speed
                vx = wy * math.cos(self.yaw) + wx * math.sin(self.yaw)
                vy = wy * math.sin(self.yaw) - wx * math.cos(self.yaw)

        self.ppo_action = [vx, vy, vz]
        self.target_vx = vx
        self.target_vy = vy
        self.target_vz = vz
        self.ppo_confidence = 0.3

    def _run_velocity_control(self):
        vx_body, vy_body = self._body_velocities()

        vx_err = self.target_vx - vx_body
        vy_err = self.target_vy - vy_body
        alt = self.gps_z
        alt_err = self.target_alt - alt

        yaw_rate = self.gyro_z
        yaw_pos_err = self.yaw_target - self.yaw
        if yaw_pos_err > math.pi:
            yaw_pos_err -= 2 * math.pi
        elif yaw_pos_err < -math.pi:
            yaw_pos_err += 2 * math.pi

        # Cascaded yaw: outer P → target rate, inner P → torque.
        target_yaw_rate = clamp(0.3 * yaw_pos_err, -0.5, 0.5)
        yaw_cmd = clamp(8.0 * (target_yaw_rate - yaw_rate), -10.0, 10.0)
        pitch_cmd = clamp(-self.K_VEL_P * vx_err - self.gyro_x * 0.3, -self.MAX_TILT, self.MAX_TILT)
        roll_cmd = clamp(self.K_VEL_P * vy_err + self.gyro_y * 0.3, -self.MAX_TILT, self.MAX_TILT)

        if self.landing_mode:
            descend_rate = min(2.0, max(0.2, alt * 0.25))
            vert_target = -descend_rate
            vz_err = vert_target - self.vz
            vertical_input = vz_err * 5.0
            if alt < 0.15:
                vertical_input = -self.K_VERTICAL_THRUST * 0.95
                self.landing_mode = False
                self.in_air = False
                self.target_alt = 0.0
        else:
            # PD altitude: P for position, D for damping. Wide range to overcome mixing spread.
            vertical_input = clamp(8.0 * alt_err - 8.0 * self.vz, -30, 30)

        if not self.armed:
            for m in [self.fl_motor, self.fr_motor, self.rl_motor, self.rr_motor]:
                m.setVelocity(0)
            return

        on_ground = alt < 0.2 and not self.in_air
        if on_ground:
            idle = 8.0
            self.fl_motor.setVelocity(idle)
            self.fr_motor.setVelocity(-idle)
            self.rl_motor.setVelocity(-idle)
            self.rr_motor.setVelocity(idle)
            return

        # Climb phase: force zero horizontal tilt so drone lifts straight.
        taking_off = self.in_air and alt < 2.0 and alt < self.target_alt - 0.5
        if taking_off:
            yaw_cmd = 0.0
            pitch_cmd = 0.0
            roll_cmd = 0.0
            self.target_vx = self.target_vy = 0.0
            # Gradual thrust ramp over 2s to prevent asymmetric motor response.
            t_since = time.time() - self._takeoff_start if self._takeoff_start > 0 else 2.0
            ramp = min(1.0, t_since / 2.0)
            vertical_input = vertical_input * ramp

        # Motor mixing with yaw
        thrust_base = clamp(self.K_VERTICAL_THRUST + vertical_input, 0, self.MOTOR_MAX)
        mm = self.MOTOR_MAX
        fl = thrust_base + pitch_cmd - roll_cmd + yaw_cmd
        fr = thrust_base + pitch_cmd + roll_cmd - yaw_cmd
        rl = thrust_base - pitch_cmd - roll_cmd - yaw_cmd
        rr = thrust_base - pitch_cmd + roll_cmd + yaw_cmd
        self.fl_motor.setVelocity(clamp(fl, 0, mm))
        self.fr_motor.setVelocity(clamp(-fr, -mm, 0))
        self.rl_motor.setVelocity(clamp(-rl, -mm, 0))
        self.rr_motor.setVelocity(clamp(rr, 0, mm))

        # Vertical thrust assist: the Webots Propeller model produces little
        # actual lift in this setup, so apply the computed thrust as a direct
        # force (no horizontal/torque overlay, vertical-only in world frame).
        root = self.getSelf()
        if root:
            w_act = [self.fl_motor.getVelocity(), self.fr_motor.getVelocity(),
                     self.rl_motor.getVelocity(), self.rr_motor.getVelocity()]
            f_total = self.THRUST_CONST * sum(wi*wi for wi in map(abs, w_act))
            # World-frame vertical lift only — double-counts with Propeller tilt thrust.
            root.addForce([0.0, 0.0, f_total], False)

    def _run_nlp(self):
        now = time.time()
        if now - self.last_nlp < self.NLP_INTERVAL:
            return
        self.last_nlp = now

        expl = self.nlp.explain_action(
            self.ppo_action[0], self.ppo_action[1],
            self.ppo_action[2], self.detections, self.gps_z,
            action_key=self._get_action_key()
        )
        if expl != self.nlp_explanation:
            self.nlp_explanation = expl
            packet, ts = self.nlp.get_statustext(expl, severity=6)
            if packet and self._gcs_addr:
                try:
                    self.sock.sendto(packet, self._gcs_addr)
                except Exception:
                    pass

    def _send_heartbeat(self):
        now = time.time()
        if now - self.last_heartbeat >= self.HEARTBEAT_INTERVAL:
            base_mode = 0
            if self.armed:
                base_mode |= MAV_MODE_FLAG_ARMED
            system_status = MAV_STATE_ACTIVE if (self.armed and self.in_air) else MAV_STATE_STANDBY
            try:
                hb = self.mav.heartbeat_encode(
                    MAV_TYPE_QUADROTOR, MAV_AUTOPILOT_GENERIC,
                    base_mode, self.flight_mode, system_status
                ).pack(self.mav)
                self._send_to_gcs(hb)
            except Exception:
                pass
            self.last_heartbeat = now

    def _send_to_gcs(self, pkt: bytes):
        descs = []
        if self._gcs_addr:
            try:
                self.sock.sendto(pkt, self._gcs_addr)
                descs.append("gcs")
            except Exception:
                pass
        try:
            self.sock.sendto(pkt, ("127.0.0.1", 14552))
            descs.append("pc3")
        except Exception:
            pass
        try:
            self._qgc_sock.sendto(pkt, ("127.0.0.1", 14550))
            descs.append("qgc")
        except Exception:
            pass

    def _send_telemetry(self):
        now = time.time()
        if now - self.last_telemetry >= self.TELEMETRY_INTERVAL:
            lat_int = int(self.gps_lat * 1e7)
            lon_int = int(self.gps_lon * 1e7)
            alt_mm = int(self.gps_alt * 1000)
            rel_alt_mm = int(self.gps_z * 1000)
            hdg_deg = (math.degrees(self.yaw) % 360)
            boot_ms = int((now - self._start_time) * 1000) & 0xFFFFFFFF

            try:
                gps_raw = self.mav.gps_raw_int_encode(
                    0, 3, lat_int, lon_int, alt_mm,
                    0, 0, 0, 0, 10
                ).pack(self.mav)
                self._send_to_gcs(gps_raw)

                vx_cm = int(self.vx * 100)
                vy_cm = int(self.vy * 100)
                vz_cm = int(-self.vz * 100)

                gpi = self.mav.global_position_int_encode(
                    boot_ms, lat_int, lon_int, alt_mm,
                    rel_alt_mm, vx_cm, vy_cm, vz_cm, int(hdg_deg * 100)
                ).pack(self.mav)
                self._send_to_gcs(gpi)

                att = self.mav.attitude_encode(
                    boot_ms, self.roll, self.pitch, self.yaw,
                    self.gyro_x, self.gyro_y, self.gyro_z
                ).pack(self.mav)
                self._send_to_gcs(att)

                vfr = self.mav.vfr_hud_encode(
                    0, 0, hdg_deg, 50, self.gps_z, 0
                ).pack(self.mav)
                self._send_to_gcs(vfr)
            except Exception:
                pass
            self.last_telemetry = now

    def _send_detections(self):
        if not self.detections:
            return
        try:
            payload = json.dumps({
                "ts": time.time(),
                "count": len(self.detections),
                "items": self.detections[:10],
            }).encode()
            self._det_sock.send(payload)
        except Exception:
            pass

    def _set_waypoint(self, idx):
        if idx >= len(WAYPOINTS):
            idx = 0
        tx, ty = WAYPOINTS[idx]
        self.target_lat = REF_LAT + ty / 111320.0
        self.target_lon = REF_LON + tx / (111320.0 * math.cos(math.radians(REF_LAT)))
        self._waypoint_idx = idx
        self._wp_sent_feedback = False
        self.yaw_target = math.atan2(tx - self.gps_x, ty - self.gps_y)
        self.yaw_integral = 0.0

    def _send_statustext(self, text, severity=6):
        if not text:
            return
        try:
            encoded = text.encode("utf-8", errors="replace")[:50]
            pkt = self.mav.statustext_encode(severity, encoded).pack(self.mav)
            self._send_to_gcs(pkt)
        except Exception:
            pass

    def run(self):
        print(f"[BRIDGE] Started. Camera {self.cam_w}x{self.cam_h}. UDP :14550")
        print(f"[BRIDGE] GPS ref: {REF_LAT}, {REF_LON}, {REF_ALT}")
        self._ensure_ppo()
        last_status = 0.0
        auto_takeoff = 0  # disabled — user must ARM/TAKEOFF via GCS

        # Eager-load models at startup (status files for start_all.sh)
        self._ensure_yolo()
        self._ensure_ppo()
        _write_ready("yolo", self.yolo_ready)
        _write_ready("ppo", self.ppo_model is not None)
        _write_ready("nlp", True)

        while self.step(self.time_step) != -1:
            now = time.time()
            self._update_sensors()
            self._recv_mavlink()

            if self.armed:
                self._run_yolo()
                self._run_ppo()

                # Waypoint progression with zone awareness
                if self.in_air and len(WAYPOINTS) > 0:
                    tx, ty = WAYPOINTS[self._waypoint_idx]
                    dist_wp = math.hypot(self.gps_x - tx, self.gps_y - ty)
                    if dist_wp < WAYPOINT_RADIUS:
                        if not self._wp_sent_feedback:
                            zone_name = _zone_name(self._waypoint_idx)
                            self._send_statustext(
                                f"Waypoint {self._waypoint_idx+1}/{len(WAYPOINTS)} "
                                f"({zone_name}) reached"
                            )
                            self._wp_sent_feedback = True
                        # Advance to next waypoint
                        nxt = (self._waypoint_idx + 1) % len(WAYPOINTS)
                        if nxt != self._waypoint_idx:
                            print(f"[WP] ADVANCE {self._waypoint_idx} → {nxt}")
                            self._set_waypoint(nxt)
                            zone_name = _zone_name(nxt)
                            self._send_statustext(
                                f"→ Navigating to waypoint {nxt+1}/{len(WAYPOINTS)} "
                                f"({zone_name})"
                            )

                # Obstacle avoidance feedback (throttled) — richer detail
                if self.in_air:
                    for d in self.detections[:1]:
                        dist = d.get("distance", 100.0)
                        if dist < 8.0 and now - getattr(self, "_last_obs_fb", 0) > 2.0:
                            zone = _current_zone_name(self.gps_x)
                            self._send_statustext(
                                f"[{zone}] {d['class_name']} at {dist:.1f}m — avoiding"
                            )
                            self._last_obs_fb = now

            self._run_velocity_control()

            self._send_heartbeat()
            if self.armed or self.in_air:
                self._send_telemetry()
                self._run_nlp()

            if now - last_status > 2.0:
                det_str = ""
                if self.detections:
                    det_str = " det: " + ", ".join(d["class_name"] for d in self.detections[:3])
                pa = self.ppo_action
                try:
                    mv = [self.fl_motor.getVelocity(), self.fr_motor.getVelocity(),
                          self.rl_motor.getVelocity(), self.rr_motor.getVelocity()]
                except:
                    mv = [0,0,0,0]
                view_pos = "?"
                view_rot = "?"
                try:
                    if self.view_node:
                        vp = self.view_node.getPosition()
                        vr = self.view_node.getOrientation()
                        view_pos = f"{vp[0]:.1f},{vp[1]:.1f},{vp[2]:.1f}"
                        view_rot = f"{vr[0]:.2f},{vr[1]:.2f},{vr[2]:.2f},{vr[3]:.2f}"
                except:
                    pass
                cp = self.cam_pitch.getTargetPosition() if self.cam_pitch else 0
                yaw_deg = math.degrees(self.yaw)
                print(f"[BRIDGE] armed={self.armed} air={self.in_air} "
                      f"alt={self.gps_z:.2f}/{self.target_alt:.1f} "
                      f"pos=[{self.gps_x:.1f} {self.gps_y:.1f}] "
                      f"vel=[{self.vx:.2f} {self.vy:.2f} {self.vz:.2f}] "
                      f"yaw={yaw_deg:.0f} "
                      f"wp={self._waypoint_idx+1}/{len(WAYPOINTS)} "
                      f"mot=[{mv[0]:.0f} {mv[1]:.0f} {mv[2]:.0f} {mv[3]:.0f}]"
                      f" cam_pitch={cp:.2f}"
                      f" ppo=[{pa[0]:.2f} {pa[1]:.2f} {pa[2]:.2f}]"
                      f"{det_str}")
                last_status = now


try:
    robot = MavicBridge()
    robot.run()
except Exception as e:
    print(f"[BRIDGE] FATAL: {e}", flush=True)
    traceback.print_exc()
    sys.exit(1)
