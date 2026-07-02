import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json
import os
import sys
import re
import random
import time

logger = logging.getLogger(__name__)

SEVERITY_EMERGENCY = 0
SEVERITY_ALERT = 1
SEVERITY_CRITICAL = 2
SEVERITY_ERROR = 3
SEVERITY_WARNING = 4
SEVERITY_NOTICE = 5
SEVERITY_INFO = 6

STATUSTEXT_MAXLEN = 50


# ── NLG Generator (rule-based obstacle feedback) ─────────────────────────

_ACTION_PHRASES = {
    "strafe_left": [
        "Adjusting course to the left",
        "Moving left to avoid",
        "Strafing left",
        "Veering left",
    ],
    "strafe_right": [
        "Adjusting course to the right",
        "Moving right to avoid",
        "Strafing right",
        "Veering right",
    ],
    "ascend": [
        "Climbing to avoid",
        "Gaining altitude",
        "Ascending",
    ],
    "descend": [
        "Descending to avoid",
        "Losing altitude",
        "Dropping down",
    ],
    "hover": [
        "Hovering in place",
        "Stopping",
        "Holding position",
    ],
    "forward": [
        "Continuing forward",
        "Proceeding ahead",
        "Moving forward",
        "Pushing ahead",
        "Advancing",
    ],
}
_DEFAULT_ACTION_PHRASES = [
    "Taking evasive action",
    "Avoiding obstacle",
    "Adjusting course",
]
_TEMPLATES_WITH_ACTION = [
    "{name} detected {position}. {action}.",
    "Obstacle: {name} spotted {position}. {action}.",
    "{name} {position}. {action}.",
    "Warning — {name} {position}. {action}.",
    "{name} sighted {position}. {action}.",
    "{action} — {name} {position}.",
]
_TEMPLATES_NO_ACTION = [
    "{name} detected {position}.",
    "Obstacle: {name} spotted {position}.",
    "{name} {position}.",
    "Warning — {name} {position}.",
    "{name} sighted {position}.",
]
_TEMPLATES_UNKNOWN_ACTION = [
    "Unknown object detected {position}. {action}.",
    "Obstacle spotted {position}. {action}.",
    "Something ahead {position}. {action}.",
]
_TEMPLATES_UNKNOWN_NO_ACTION = [
    "Unknown object detected {position}.",
    "Obstacle spotted {position}.",
    "Something ahead {position}.",
]


def _position_label(rel_x: float) -> str:
    if rel_x < 0.25:
        return "far left"
    if rel_x < 0.40:
        return "on the left"
    if rel_x < 0.60:
        return "dead ahead"
    if rel_x < 0.75:
        return "on the right"
    return "far right"


def _resolve_action(action_key: Optional[str]) -> str:
    if action_key is None:
        return ""
    action_key = action_key.lower()
    bank = _ACTION_PHRASES.get(action_key)
    if not bank:
        return _DEFAULT_ACTION_PHRASES[0]
    return bank[0]


def _nlg_generate(detection: Dict[str, Any], action_key: Optional[str] = None) -> str:
    obj_name = detection.get("class_name", "")
    rel_x = detection.get("bearing_h", 0.0)
    rel_x = 0.5 + rel_x / 3.0
    rel_x = max(0.0, min(1.0, rel_x))
    position = _position_label(rel_x)
    action = _resolve_action(action_key)

    has_name = bool(obj_name) and obj_name not in ("unknown", "")
    has_action = bool(action)

    if has_name and has_action:
        tpl = random.choice(_TEMPLATES_WITH_ACTION)
        return tpl.format(name=obj_name, position=position, action=action)
    elif has_name and not has_action:
        tpl = random.choice(_TEMPLATES_NO_ACTION)
        return tpl.format(name=obj_name, position=position)
    elif not has_name and has_action:
        tpl = random.choice(_TEMPLATES_UNKNOWN_ACTION)
        return tpl.format(position=position, action=action)
    else:
        tpl = random.choice(_TEMPLATES_UNKNOWN_NO_ACTION)
        return tpl.format(position=position)


# ── NLU Parser (rule-based command understanding) ─────────────────────────

_INTENT_RULES = {
    "takeoff": [
        r"\btake\s*off\b", r"\bascend\b",
        r"\bclimb\b", r"\bgo\s*up\b",
        r"\bchomoa\b", r"\bpanda\b", r"\binuka\b",
        r"\bruka\b",
    ],
    "land": [
        r"\bland(?:ing)?\b", r"\bdescend\b", r"\btouch\s*down\b",
        r"\bcome\s*down\b", r"\bgo\s*down\b",
        r"\btua\b", r"\bshuka\b",
    ],
    "goto": [
        r"\bgo\s*to\b", r"\bfly\s*to\b", r"\bnavigate\s*to\b",
        r"\bmove\s*to\b", r"\bhead\s*to\b", r"\bproceed\s*to\b",
        r"\btake\s*me\s*to\b",
        r"\bkwenda\b", r"\bnenda\b", r"\benda\b",
    ],
    "rtl": [
        r"\breturn\s+(?:home|to\s+launch|to\s+base)\b",
        r"\brtl\b", r"\bgo\s+home\b", r"\bcome\s+back\b",
        r"\bhead\s+home\b", r"\breturn\s+to\s+landing\b",
        r"\brudi\s+nyumbani\b", r"\brudi\s+kwenye\b", r"\bnirudishe\b",
    ],
    "hover": [
        r"\bhover\b", r"\bhold\s+(?:position|still)\b",
        r"\bstop\b", r"\bpause\b", r"\bstay\b",
        r"\bsimama\b", r"\bnyamaza\b",
    ],
    "arm": [r"\barm\b", r"\bwasha\b"],
    "disarm": [r"\bdisarm\b", r"\bshut\s*down\b", r"\bpower\s*off\b", r"\bzima\b"],
}

_ALTITUDE_PATTERNS = [
    re.compile(r"(\d+(?:\.\d+)?)\s*(?:m(?:eters?)?)\b", re.IGNORECASE),
    re.compile(r"(?:altitude|alt|height)\s*(?:of\s*)?(\d+(?:\.\d+)?)", re.IGNORECASE),
    re.compile(r"(?:to|at)\s*(\d+(?:\.\d+)?)\s*(?:m(?:eters?)?|meters)", re.IGNORECASE),
]
_RAW_NUMBER = re.compile(r"\b(\d+(?:\.\d+)?)\b")
_GPS_PATTERN = re.compile(r"([+-]?\d+\.\d+)\s*[, ]\s*([+-]?\d+\.\d+)")


def _score_intents(text: str) -> List[Tuple[str, int]]:
    lower = text.lower()
    scores = []
    for intent, patterns in _INTENT_RULES.items():
        count = 0
        for pat in patterns:
            if re.search(pat, lower):
                count += 1
        if count > 0:
            scores.append((intent, count))
    scores.sort(key=lambda x: -x[1])
    return scores


def _extract_altitude(text: str) -> Optional[float]:
    for pat in _ALTITUDE_PATTERNS:
        m = pat.search(text)
        if m:
            return float(m.group(1))
    lower = text.lower()
    for kw in ("altitude", "alt", "height", "climb", "descend", "to", "at"):
        idx = lower.find(kw)
        if idx != -1:
            after = lower[idx + len(kw):]
            m = _RAW_NUMBER.search(after)
            if m:
                return float(m.group(1))
    return None


def parse_command(text: str) -> Dict[str, Any]:
    text = text.strip()
    if not text:
        return {"success": False, "intent": "unknown", "command_id": "",
                "raw_text": text, "altitude": None, "location": None,
                "target_gps": None, "reason": "Empty command.", "confidence": 0.0}

    scores = _score_intents(text)
    if not scores:
        return {"success": False, "intent": "unknown", "command_id": "",
                "raw_text": text, "altitude": None, "location": None,
                "target_gps": None,
                "reason": f"Sorry, didn't understand \"{text}\".",
                "confidence": 0.0}

    intent = scores[0][0]
    match_count = scores[0][1]
    confidence = min(1.0, 0.5 + 0.15 * match_count)
    altitude = _extract_altitude(text)
    command_id = f"cmd_{int(time.time() * 1000)}"

    target_gps = None
    location = None

    number = _RAW_NUMBER.search(text)
    if number and intent == "goto":
        coords = _GPS_PATTERN.search(text)
        if coords:
            target_gps = {"lat": float(coords.group(1)), "lon": float(coords.group(2))}

    if altitude is None:
        if intent == "takeoff":
            altitude = 10.0
        elif intent == "goto":
            altitude = 15.0
        elif intent == "rtl":
            altitude = 10.0

    return {"success": True, "intent": intent, "command_id": command_id,
            "raw_text": text, "altitude": altitude, "location": location,
            "target_gps": target_gps, "reason": f"Parsed: {intent}", "confidence": confidence}


# ── DroneNLP class ────────────────────────────────────────────────────────

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
                       altitude: float, action_key: Optional[str] = None) -> str:
        speed = (action_vx ** 2 + action_vy ** 2 + action_vz ** 2) ** 0.5

        if not obstacles:
            if speed < 0.1:
                return "Hovering. No obstacles detected."
            dir_str = self._velocity_direction(action_vx, action_vy)
            return f"Moving {dir_str} at {speed:.1f} m/s. Path is clear."

        closest = min(obstacles, key=lambda o: o.get("distance", 100))
        dist = closest.get("distance", 0)

        if dist < 8.0:
            return _nlg_generate(closest, action_key)
        else:
            if speed < 0.1:
                obj_name = closest.get("class_name", "object")
                return f"Hovering. {obj_name} seen at {dist:.1f}m."
            dir_str = self._velocity_direction(action_vx, action_vy)
            obj_name = closest.get("class_name", "object")
            return f"Moving {dir_str}. {obj_name} at {dist:.1f}m."

    def parse_natural(self, text: str) -> Dict[str, Any]:
        return parse_command(text)

    def _velocity_direction(self, vx: float, vy: float) -> str:
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
        bearing_h = closest.get("bearing_h", 0)

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
