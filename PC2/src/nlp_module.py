import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json

logger = logging.getLogger(__name__)

SEVERITY_EMERGENCY = 0
SEVERITY_ALERT = 1
SEVERITY_CRITICAL = 2
SEVERITY_ERROR = 3
SEVERITY_WARNING = 4
SEVERITY_NOTICE = 5
SEVERITY_INFO = 6

STATUSTEXT_MAXLEN = 50


class DroneNLP:
    def __init__(self, language: str = "en"):
        self.language = language
        self._last_statustext = ""
        self._last_stats_ts = 0.0
        self.flight_history = []
        self.session_start = datetime.now()

    def make_statustext(self, severity: int, text: str) -> bytes:
        truncated = text.encode("utf-8", errors="replace")[:STATUSTEXT_MAXLEN]
        logging.debug(f"NLP STATUSTEXT [{severity}]: {truncated.decode(errors='replace')}")
        try:
            from pymavlink.dialects.v20 import common as mavlink
            mav = mavlink.MAVLink(None, srcSystem=1, srcComponent=1)
            msg = mav.statustext_encode(severity, truncated)
            return msg.pack(mav)
        except ImportError:
            return b""

    def get_statustext(self, text: str, severity: int = SEVERITY_INFO) -> Tuple[bytes, float]:
        now = datetime.now().timestamp()
        if text == self._last_statustext and now - self._last_stats_ts < 5.0:
            return b"", 0.0
        self._last_statustext = text
        self._last_stats_ts = now
        packet = self.make_statustext(severity, text)
        return packet, now

    def explain_action(self, action_vx: float, action_vy: float,
                       action_vz: float, obstacles: List[Dict],
                       altitude: float) -> str:
        speed = (action_vx ** 2 + action_vy ** 2 + action_vz ** 2) ** 0.5
        if not obstacles:
            if speed < 0.1:
                return "Hovering. No obstacles detected."
            dir_str = self._velocity_direction(action_vx, action_vy)
            return f"Moving {dir_str} at {speed:.1f} m/s. Path is clear."

        closest = min(obstacles, key=lambda o: o.get("distance", 100))
        obj_name = closest.get("class_name", "object")
        dist = closest.get("distance", 0)
        dir_to = closest.get("bearing_str", "ahead")

        if dist < 3:
            return f"Avoiding {obj_name} {dir_to} at {dist:.1f}m. Taking evasive action."
        elif dist < 8:
            return f"{obj_name} detected {dir_to}, {dist:.1f}m. Adjusting path."
        else:
            if speed < 0.1:
                return f"Hovering. {obj_name} seen {dir_to} at {dist:.1f}m."
            dir_str = self._velocity_direction(action_vx, action_vy)
            return f"Moving {dir_str}. {obj_name} {dir_to}, {dist:.1f}m."

    def _velocity_direction(self, vx: float, vy: float) -> str:
        angle = (np.degrees(np.arctan2(vy, vx)) if 'np' in dir() else
                 (vy, vx) if abs(vx) > 0.1 or abs(vy) > 0.1 else (0, 0))
        try:
            import numpy as np
            angle = np.degrees(np.arctan2(vy, vx))
        except ImportError:
            angle = 0.0
        if abs(angle) < 30:
            return "forward"
        elif abs(angle) < 60:
            return "forward-right" if angle > 0 else "forward-left"
        elif abs(angle) < 120:
            return "right" if angle > 0 else "left"
        elif abs(angle) < 150:
            return "back-right" if angle > 0 else "back-left"
        else:
            return "backward"

    def explain_reasoning(self, action_vx: float, action_vy: float,
                          action_vz: float, obstacles: List[Dict]) -> str:
        if not obstacles:
            return "No obstacles. Continuing current path."
        closest = min(obstacles, key=lambda o: o.get("distance", 100))
        obj_name = closest.get("class_name", "object")
        dist = closest.get("distance", 0)
        bearing_h, bearing_v = closest.get("bearing_h", 0), closest.get("bearing_v", 0)

        parts = [f"Closest threat: {obj_name} at {dist:.1f}m"]
        side = "right" if bearing_h > 0 else "left"
        parts.append(f"bearing {side} {abs(bearing_h):.0f}deg")
        if action_vz > 0.5:
            parts.append("climbing to avoid")
        elif action_vz < -0.5:
            parts.append("descending to avoid")
        if abs(action_vy) > 0.5:
            parts.append(f"moving {side}")
        return ". ".join(parts) + "."

    def explain_current_state(self, obstacles: List[Dict], action: int,
                              confidence: float = 0.0) -> str:
        action_names = {0: "turn left", 1: "turn right", 2: "climb up",
                        3: "descend", 4: "move forward", 5: "stop"}
        act_str = action_names.get(action, "taking action")
        if not obstacles:
            return f"Path clear. Drone {act_str}."
        obj = max(obstacles, key=lambda o: (o.get("confidence", 0) *
                  o.get("width", 0) * o.get("height", 0)))
        obj_name = obj.get("class_name", "object")
        pos_desc = self._pos_desc(obj)
        dist_desc = self._dist_desc(obj)
        extra = ""
        if len(obstacles) > 1:
            extra = f" Also {len(obstacles) - 1} more objects."
        conf_str = f" (confidence: {int(confidence * 100)}%)" if confidence > 0 else ""
        return (f"Drone detected {obj_name} {pos_desc}, {dist_desc}. "
                f"Action: {act_str}{conf_str}.{extra}")

    def _pos_desc(self, obs: Dict) -> str:
        cx = obs.get("center", [0.5, 0.5])[0] if "center" in obs else obs.get("x", 0.5)
        if cx < 0.33:
            return "to the left"
        elif cx > 0.66:
            return "to the right"
        elif cx < 0.45:
            return "slightly left"
        elif cx > 0.55:
            return "slightly right"
        return "ahead"

    def _dist_desc(self, obs: Dict) -> str:
        w = obs.get("width", 0)
        h = obs.get("height", 0)
        fw = obs.get("frame_w", 640)
        fh = obs.get("frame_h", 480)
        size = (w / fw if fw else 0.1) * (h / fh if fh else 0.1)
        if size > 0.3:
            return "very close"
        elif size > 0.15:
            return "close"
        elif size > 0.08:
            return "medium distance"
        elif size > 0.04:
            return "far"
        return "very far"

    def generate_alert(self, alert_type: str, details: Dict) -> Tuple[str, int]:
        if alert_type == "collision_risk":
            obj = details.get("obstacle", {})
            name = obj.get("class_name", "object")
            dist = obj.get("distance", 0)
            return f"COLLISION: {name} at {dist:.0f}m!", SEVERITY_ALERT
        elif alert_type == "low_battery":
            return f"LOW BATTERY: {details.get('battery', 0)}%", SEVERITY_WARNING
        elif alert_type == "system_error":
            return f"SYS ERR: {details.get('error', 'unknown')}", SEVERITY_CRITICAL
        return f"Alert: {alert_type}", SEVERITY_INFO

    def generate_flight_summary(self, history: List[Dict]) -> str:
        if not history:
            return "No flight data."
        steps = len(history)
        avoids = sum(1 for h in history if h.get("action") not in [4, 5] and h.get("obstacles"))
        crashes = sum(1 for h in history if h.get("crashed"))
        if history:
            dur = history[-1].get("timestamp", datetime.now()) - history[0].get("timestamp", datetime.now())
            dur_str = str(dur).split(".")[0]
        else:
            dur_str = "0:00:00"
        cr = crashes / steps * 100 if steps else 0
        ar = avoids / steps * 100 if steps else 0
        return (f"Flight: {dur_str}, {steps} steps, "
                f"{avoids} avoids ({ar:.0f}%), {crashes} crashes ({cr:.0f}%).")

    def log_event(self, event_type: str, details: Dict):
        self.flight_history.append({"timestamp": datetime.now(), "event": event_type, "details": details})
        if len(self.flight_history) > 1000:
            self.flight_history = self.flight_history[-1000:]

    def export_log(self, filename: Optional[str] = None) -> str:
        if filename is None:
            filename = f"flight_{datetime.now():%Y%m%d_%H%M%S}.json"
        with open(filename, "w") as f:
            json.dump({"session": self.session_start.isoformat(),
                       "events": self.flight_history}, f, indent=2, default=str)
        return filename
