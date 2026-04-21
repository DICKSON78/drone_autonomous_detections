import time
import logging
from typing import Dict

logger = logging.getLogger(__name__)

# ── Priority config ───────────────────────────────────────────────────────────

PRIORITY_PREFIXES: Dict[str, str] = {
    "emergency": "Emergency alert! ",
    "high":      "Warning. ",
    "normal":    "",
    "low":       "",
}

CONFIDENCE_THRESHOLD  = 0.65
ANNOUNCE_COOLDOWN_SEC = 5.0

CRITICAL_CLASSES = {"person", "car", "truck", "bus"}
RELEVANT_CLASSES = CRITICAL_CLASSES | {
    "bicycle", "motorcycle", "dog", "cat", "bird",
    "tree", "building", "house", "road"
}


class MessageQueue:
    """
    Processes incoming Kafka messages, applies priority rules and cooldown
    filtering, and delegates to TTSEngine for speech output.
    """

    def __init__(self):
        self._last_announced: Dict[str, float] = {}
        self._total_spoken = 0

    # ── Public helpers ────────────────────────────────────────────────────────

    def build_message(self, text: str, priority: str) -> str:
        return PRIORITY_PREFIXES.get(priority, "") + text

    def stats(self) -> dict:
        return {
            "total_spoken": self._total_spoken,
            "announced_classes": list(self._last_announced.keys()),
            "confidence_threshold": CONFIDENCE_THRESHOLD,
            "cooldown_seconds": ANNOUNCE_COOLDOWN_SEC,
        }

    # ── Kafka event handlers ──────────────────────────────────────────────────

    def handle_detection(self, data: dict, tts, producer):
        """Process a drone.detections.objects payload."""
        detections = [
            d for d in data.get("detections", [])
            if d.get("confidence", 0) >= CONFIDENCE_THRESHOLD
            and d.get("class_name") in RELEVANT_CLASSES
        ]
        counts: Dict[str, int] = {}
        for d in detections:
            cls = d["class_name"]
            counts[cls] = counts.get(cls, 0) + 1

        for cls, count in counts.items():
            if self._cooldown_ok(cls):
                priority = "high" if cls in CRITICAL_CLASSES else "normal"
                noun = cls if count == 1 else f"{count} {cls}s"
                msg = self.build_message(f"{noun} detected.", priority)
                tts.speak_async(msg)
                self._publish(producer, msg, priority, "detection",
                              class_name=cls, count=count)

    def handle_navigation(self, data: dict, tts, producer):
        """Process a drone.navigation.result payload."""
        result     = data.get("result", {})
        action     = result.get("next_action", "")
        confidence = result.get("confidence", 0.0)
        if not action:
            return
        if action == "emergency":
            msg, priority = self.build_message("Emergency stop initiated.", "emergency"), "emergency"
        elif confidence < 0.3:
            msg, priority = self.build_message("Low navigation confidence. Hovering.", "high"), "high"
        else:
            msg, priority = self.build_message(f"Navigating. Next action: {action}.", "normal"), "normal"
        tts.speak_async(msg)
        self._publish(producer, msg, priority, "navigation",
                      action=action, confidence=confidence)

    def handle_command(self, data: dict, tts, producer):
        """Process a drone.commands.feedback payload."""
        action = data.get("action", "")
        if action == "speak":
            message  = data.get("message", "").strip()
            priority = data.get("priority", "normal").lower()
            if message:
                msg = self.build_message(message, priority)
                tts.speak_async(msg)
                self._publish(producer, msg, priority, "direct_command")
        elif action == "announce":
            event   = data.get("event", "").replace("_", " ")
            details = data.get("details", "")
            text    = f"{event}. {details}" if details else event
            msg     = self.build_message(text, "high")
            tts.speak_async(msg)
            self._publish(producer, msg, "high", "announce", event=data.get("event"))
        elif action == "system_status":
            message  = data.get("message", "System status update.")
            priority = data.get("priority", "normal")
            msg      = self.build_message(message, priority)
            tts.speak_async(msg)
            self._publish(producer, msg, priority, "system_status")

    # ── Internals ─────────────────────────────────────────────────────────────

    def _cooldown_ok(self, key: str) -> bool:
        now = time.time()
        if now - self._last_announced.get(key, 0.0) >= ANNOUNCE_COOLDOWN_SEC:
            self._last_announced[key] = now
            return True
        return False

    def _publish(self, producer, message: str, priority: str,
                 trigger: str, **extra):
        self._total_spoken += 1
        try:
            producer.send('drone.feedback.spoken', {
                "message": message, "priority": priority,
                "trigger": trigger, "timestamp": time.time(), **extra
            })
        except Exception as e:
            logger.error(f"Kafka publish error: {e}")