#!/usr/bin/env python3
"""
Integrated Drone Controller — YOLO detection + MAVLink autonomous flight.

Inaunganisha YOLO trained na mfumo wa drone ili drone inapokuwa
inatembea iweze kutambua imekutana na nini na kujibu vizuizi.
"""

import os, sys, time, json, signal, threading, queue
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mavlink_lite import DroneConnection
from mission_drone_controller import MissionDrone, DroneState, STATE_NAMES, CONFIG, SURVEILLANCE_WAYPOINTS

GREEN = "\033[92m"; YELLOW = "\033[93m"; RED = "\033[91m"
CYAN = "\033[96m"; BOLD = "\033[1m"; DIM = "\033[2m"; RESET = "\033[0m"

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

CLASS_COLORS = {
    "person": (0, 0, 255), "bicycle": (255, 0, 0), "car": (0, 255, 255),
    "motorcycle": (255, 128, 0), "airplane": (255, 0, 255), "bus": (128, 0, 128),
    "truck": (0, 128, 255), "boat": (255, 128, 128), "traffic light": (0, 255, 0),
    "bird": (255, 255, 0), "cat": (255, 128, 64), "dog": (64, 128, 255),
    "horse": (128, 64, 128), "sheep": (64, 64, 128), "cow": (128, 128, 64),
    "tree": (0, 128, 0), "building": (128, 128, 128),
}

DETECTION_CLASSES = {
    "person", "car", "truck", "bus", "motorcycle", "bicycle",
    "dog", "cat", "horse", "cow", "sheep", "bird",
    "traffic light", "stop sign", "fire hydrant",
}

OBSTACLE_CLASSES = {
    "person", "car", "truck", "bus", "motorcycle", "bicycle",
    "building", "tree", "pole", "traffic light",
    "dog", "horse", "cow", "sheep",
}


class CameraCapture:
    def __init__(self, source: str = "simulation", width: int = 640, height: int = 480):
        self.width = width
        self.height = height
        self.source = source
        self.cap = None
        self.is_simulated = (source == "simulation")
        self.frame_count = 0

        if not self.is_simulated and CV2_AVAILABLE:
            self._open()

    def _open(self):
        try:
            if self.source == "webcam":
                self.cap = cv2.VideoCapture(0)
            else:
                self.cap = cv2.VideoCapture(self.source)
            if self.cap and self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                self.is_simulated = False
        except Exception:
            self.is_simulated = True

    def capture(self) -> Optional[np.ndarray]:
        self.frame_count += 1
        if self.is_simulated:
            return self._generate_frame()
        if self.cap is None or not self.cap.isOpened():
            return self._generate_frame()
        ret, frame = self.cap.read()
        if not ret:
            return self._generate_frame()
        if frame.shape[1] != self.width or frame.shape[0] != self.height:
            frame = cv2.resize(frame, (self.width, self.height))
        return frame

    def _generate_frame(self) -> np.ndarray:
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        for i in range(self.height // 2):
            c = int(135 + (i / (self.height // 2)) * 50)
            frame[i, :] = [c, c, 255]
        for i in range(self.height // 2, self.height):
            c = int(34 + ((i - self.height // 2) / (self.height // 2)) * 50)
            frame[i, :] = [c, c, c]
        if self.frame_count % 30 < 15:
            cx, cy = self.width // 2, self.height // 2
            cv2.rectangle(frame, (cx - 30, cy - 20), (cx + 30, cy + 20), (0, 0, 200), -1)
            cv2.circle(frame, (cx, cy - 25), 8, (255, 228, 181), -1)
        if self.frame_count % 45 < 22:
            cv2.rectangle(frame, (120, 300), (200, 380), (100, 100, 100), -1)
        return frame

    def release(self):
        if self.cap is not None:
            self.cap.release()


class DetectionEngine:
    def __init__(self, model_path: str = "yolov8n.pt", confidence: float = 0.5):
        self.model_path = model_path
        self.confidence = confidence
        self.model = None
        self.fps = 0.0
        self._load()

    def _load(self):
        if YOLO_AVAILABLE:
            try:
                self.model = YOLO(self.model_path)
                print(f"  {GREEN}[YOLO] Model loaded: {self.model_path}{RESET}")
            except Exception as e:
                print(f"  {YELLOW}[YOLO] Failed to load model: {e}{RESET}")
                self.model = None
        else:
            print(f"  {YELLOW}[YOLO] ultralytics not installed, using mock{RESET}")

    def detect(self, frame: np.ndarray) -> Tuple[List[Dict], float]:
        start = time.time()
        if self.model is None:
            detections = self._mock_detect(frame)
        else:
            try:
                results = self.model(frame, conf=self.confidence, verbose=False)
                detections = self._parse_results(results[0])
            except Exception as e:
                detections = self._mock_detect(frame)
        elapsed = time.time() - start
        self.fps = 1.0 / elapsed if elapsed > 0 else 0
        return detections, elapsed

    def _parse_results(self, result) -> List[Dict]:
        detections = []
        if result.boxes is None:
            return detections
        for box in result.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            class_name = result.names[cls_id] if hasattr(result, 'names') and cls_id in result.names else f"class_{cls_id}"
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2
            w = x2 - x1
            h = y2 - y1
            detections.append({
                "class": class_name, "class_id": cls_id, "confidence": conf,
                "bbox": [x1, y1, x2, y2],
                "cx": cx, "cy": cy, "w": w, "h": h,
                "area": w * h,
                "is_obstacle": class_name in OBSTACLE_CLASSES,
            })
        return detections

    def _mock_detect(self, frame: np.ndarray) -> List[Dict]:
        h, w = frame.shape[:2]
        detections = []
        np.random.seed(int(time.time() * 1000) % 10000)
        if np.random.random() < 0.4:
            n = np.random.randint(1, 3)
            for _ in range(n):
                cx = np.random.uniform(0.1, 0.9) * w
                cy = np.random.uniform(0.1, 0.9) * h
                bw = np.random.uniform(30, 100)
                bh = np.random.uniform(30, 100)
                classes = ["person", "car", "tree", "building", "bird"]
                cls = np.random.choice(classes)
                detections.append({
                    "class": cls,
                    "class_id": 0,
                    "confidence": np.random.uniform(0.5, 0.95),
                    "bbox": [cx - bw/2, cy - bh/2, cx + bw/2, cy + bh/2],
                    "cx": cx, "cy": cy, "w": bw, "h": bh, "area": bw * bh,
                    "is_obstacle": cls in OBSTACLE_CLASSES,
                })
        return detections


class IntegratedDrone:
    def __init__(self, host="127.0.0.1", port=14550,
                 yolo_model="yolov8n.pt", detection_confidence=0.5,
                 camera_source="simulation", check_interval=1.0):
        self.host = host
        self.port = port
        self.check_interval = check_interval
        self.mission_drone = MissionDrone(host, port)
        self.camera = CameraCapture(source=camera_source)
        self.detector = DetectionEngine(yolo_model, detection_confidence)
        self.running = True
        self.detection_log = []
        self.avoidance_active = False
        self.last_avoidance_time = 0
        self.avoidance_cooldown = 3.0
        self.frame_queue = queue.Queue(maxsize=10)
        self.detection_queue = queue.Queue(maxsize=10)

        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _handle_signal(self, sig, frame):
        print(f"\n  {YELLOW}Shutting down integrated drone...{RESET}")
        self.running = False
        self.mission_drone.close()
        self.camera.release()
        sys.exit(0)

    def connect(self):
        return self.mission_drone.connect()

    def get_status(self) -> Dict:
        t = self.mission_drone.get_telemetry()
        return {
            "state": STATE_NAMES.get(self.mission_drone.state, "UNKNOWN"),
            "altitude": t["alt"],
            "battery": t["battery"],
            "gps": (t["lat"], t["lon"]),
            "speed": t.get("speed", 0),
            "heading": t["heading"],
            "armed": t["armed"],
            "detection_fps": self.detector.fps,
        }

    def print_status(self):
        s = self.get_status()
        bar = self._bar(s["battery"], 100)
        det = f" {YELLOW}[DET]{RESET}" if self.avoidance_active else ""
        print(f"\r  {CYAN}[FLIGHT]{RESET} State: {s['state']:15s}  "
              f"Alt: {s['altitude']:6.1f}m  Bat: {bar} {s['battery']:3.0f}%  "
              f"GPS: {s['gps'][0]:.4f}, {s['gps'][1]:.4f}{det}", end="")

    def _bar(self, val, mx, w=10):
        f = int(val / mx * w) if mx > 0 else 0
        f = max(0, min(w, f))
        c = GREEN if val > 60 else (YELLOW if val > 30 else RED)
        return f"{c}{'█' * f}{'░' * (w - f)}{RESET}"

    def _should_avoid(self, detections: List[Dict]) -> Tuple[bool, Optional[str], float]:
        if not detections:
            return False, None, 0.0

        now = time.time()
        if now - self.last_avoidance_time < self.avoidance_cooldown:
            return False, None, 0.0

        obstacles = [d for d in detections if d["is_obstacle"]]
        if not obstacles:
            return False, None, 0.0

        obstacles.sort(key=lambda d: d["area"], reverse=True)
        main = obstacles[0]
        img_area = self.camera.width * self.camera.height
        area_ratio = main["area"] / img_area

        if area_ratio > 0.05 and main["confidence"] > 0.5:
            self.last_avoidance_time = now
            if main["cx"] < self.camera.width * 0.3:
                return True, "right", main["class"]
            elif main["cx"] > self.camera.width * 0.7:
                return True, "left", main["class"]
            else:
                return True, "hover", main["class"]

        return False, None, 0.0

    def _execute_avoidance(self, action: str, obstacle_class: str):
        self.avoidance_active = True
        drone = self.mission_drone.drone
        ts = datetime.now().strftime("%H:%M:%S")

        print(f"\n  {YELLOW}{BOLD}[AVOID] {ts} — {obstacle_class} detected!{RESET}")
        print(f"  {YELLOW}Action: {action}{RESET}")

        if action == "left":
            print(f"  {CYAN}Strafing left 5m{RESET}")
            drone.strafe("left", 5)
            time.sleep(3)
        elif action == "right":
            print(f"  {CYAN}Strafing right 5m{RESET}")
            drone.strafe("right", 5)
            time.sleep(3)
        elif action == "hover":
            print(f"  {CYAN}Hovering for 3s, then climbing 3m{RESET}")
            time.sleep(2)
            t = drone.get_telemetry()
            drone.goto_position(t["lat"], t["lon"], t["alt"] + 3)
            time.sleep(3)

        self.avoidance_active = False
        print(f"  {GREEN}[AVOID] Resuming mission{RESET}")

    def _log_detection(self, detections: List[Dict], location: Tuple, altitude: float):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "detections": detections,
            "location": {"lat": location[0], "lon": location[1]},
            "altitude": altitude,
        }
        self.detection_log.append(entry)

    def detection_loop(self):
        print(f"  {GREEN}[DETECT] Starting detection loop{RESET}")
        while self.running:
            try:
                frame = self.camera.capture()
                if frame is not None:
                    detections, proc_time = self.detector.detect(frame)
                    if detections:
                        try:
                            self.detection_queue.put_nowait(detections)
                        except queue.Full:
                            pass
                        t = self.mission_drone.get_telemetry()
                        classes = [d["class"] for d in detections[:5]]
                        print(f"\n  {CYAN}[DETECT]{RESET} Found: {', '.join(classes)} "
                              f"({len(detections)} obj, {proc_time*1000:.0f}ms)")
                        self._log_detection(detections, (t["lat"], t["lon"]), t["alt"])
            except Exception as e:
                print(f"\n  {RED}[DETECT] Error: {e}{RESET}")
            time.sleep(self.check_interval)

    def run_mission(self, waypoints=None):
        if waypoints is None:
            waypoints = SURVEILLANCE_WAYPOINTS

        if not self.mission_drone.connect():
            print(f"  {RED}Failed to connect to drone{RESET}")
            return

        print(f"\n  {CYAN}{BOLD}╔══════════════════════════════════════════╗{RESET}")
        print(f"  {CYAN}{BOLD}║   INTEGRATED DETECTION MISSION STARTING ║{RESET}")
        print(f"  {CYAN}{BOLD}╚══════════════════════════════════════════╝{RESET}\n")

        detect_thread = threading.Thread(target=self.detection_loop, daemon=True)
        detect_thread.start()

        self.mission_drone.waypoints = waypoints
        self.mission_drone.mission_active = True
        t = self.mission_drone.get_telemetry()
        self.mission_drone.home_position = (t["lat"], t["lon"], t["alt"])

        print(f"  Home: {t['lat']:.6f}, {t['lon']:.6f}, Alt: {t['alt']:.1f}m\n")
        print(f"  {BOLD}Mission waypoints: {len(waypoints)}{RESET}\n")

        self.mission_drone.takeoff()
        self.mission_drone.state = DroneState.NAVIGATING

        for idx, wp in enumerate(waypoints[1:], 1):
            if not self.running:
                break
            self.mission_drone.current_waypoint_idx = idx
            print(f"\n  {BOLD}─ Waypoint {idx}/{len(waypoints)-1} ─{RESET}")

            local_x, local_y, alt = wp
            t = self.mission_drone.get_telemetry()
            home = self.mission_drone.home_position
            lat_off = local_y / 111000
            lon_off = local_x / (111000 * np.cos(np.radians(home[0])))
            target = (home[0] + lat_off, home[1] + lon_off, alt)

            print(f"  Target: ({local_x:.0f}, {local_y:.0f}) @ {alt:.0f}m")
            self.mission_drone.drone.goto_position(target[0], target[1], target[2])

            acceptance = CONFIG["flight"]["waypoint_acceptance_radius"]
            for step in range(40):
                if not self.running:
                    break
                time.sleep(1.5)
                t = self.mission_drone.get_telemetry()
                lat_d = (t["lat"] - target[0]) * 111000
                lon_d = (t["lon"] - target[1]) * 111000 * np.cos(np.radians(t["lat"]))
                dist = np.sqrt(lat_d**2 + lon_d**2)

                self.print_status()

                try:
                    detections = self.detection_queue.get_nowait()
                    should_avoid, direction, obj_class = self._should_avoid(detections)
                    if should_avoid:
                        self._execute_avoidance(direction, obj_class)
                        self.mission_drone.drone.goto_position(target[0], target[1], target[2])
                except queue.Empty:
                    pass

                if dist < acceptance:
                    print(f"\n  {GREEN}Waypoint {idx} reached ✓{RESET}")
                    break

            hover_t = CONFIG["flight"]["hover_time_at_waypoint"]
            print(f"  Hovering {hover_t}s...")
            for _ in range(int(hover_t)):
                if not self.running:
                    break
                time.sleep(1)

            battery = self.mission_drone.drone.get_telemetry().get("battery", 100)
            if battery >= 0 and battery < CONFIG["mission"]["low_battery_threshold"]:
                print(f"\n  {RED}{BOLD}Low battery ({battery}%)! Returning home{RESET}")
                break

        if CONFIG["mission"]["enable_return_to_home"]:
            self.mission_drone.return_to_home()
            self.mission_drone.smooth_land()

        self.mission_drone.state = DroneState.LANDED
        self.mission_drone.mission_active = False
        self.running = False

        print(f"\n  {GREEN}{BOLD}Mission complete! ✓{RESET}")
        self._print_summary()

    def _print_summary(self):
        print(f"\n  {CYAN}{BOLD}╔══════════════════════════════════════╗{RESET}")
        print(f"  {CYAN}{BOLD}║        MISSION SUMMARY              ║{RESET}")
        print(f"  {CYAN}{BOLD}╚══════════════════════════════════════╝{RESET}")

        total_detections = sum(len(e["detections"]) for e in self.detection_log)
        class_counts = {}
        for e in self.detection_log:
            for d in e["detections"]:
                cls = d["class"]
                class_counts[cls] = class_counts.get(cls, 0) + 1

        print(f"  Total frames with detections: {len(self.detection_log)}")
        print(f"  Total objects detected: {total_detections}")
        if class_counts:
            print(f"  Objects by type:")
            for cls, count in sorted(class_counts.items(), key=lambda x: -x[1])[:10]:
                print(f"    • {cls}: {count}")

        log_file = f"detection_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(log_file, "w") as f:
            json.dump(self.detection_log, f, indent=2, default=str)
        print(f"  Detection log saved: {log_file}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Integrated Drone with YOLO Detection")
    parser.add_argument("host", nargs="?", default="127.0.0.1", help="Drone UDP host")
    parser.add_argument("port", nargs="?", type=int, default=14550, help="Drone UDP port")
    parser.add_argument("--yolo-model", default="yolov8n.pt", help="Path to YOLO model")
    parser.add_argument("--confidence", type=float, default=0.5, help="Detection confidence")
    parser.add_argument("--camera", default="simulation", help="Camera source (simulation/webcam/video path)")
    parser.add_argument("--interval", type=float, default=1.0, help="Detection check interval (s)")
    parser.add_argument("--alt", type=float, default=None, help="Flight altitude")
    args = parser.parse_args()

    if args.alt:
        CONFIG["flight"]["default_altitude"] = args.alt
        for wp in SURVEILLANCE_WAYPOINTS:
            wp[2] = args.alt

    drone = IntegratedDrone(
        host=args.host, port=args.port,
        yolo_model=args.yolo_model,
        detection_confidence=args.confidence,
        camera_source=args.camera,
        check_interval=args.interval,
    )

    drone.run_mission()


if __name__ == "__main__":
    main()
