import pytest
import time
from unittest.mock import MagicMock
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from message_queue import MessageQueue, CONFIDENCE_THRESHOLD, ANNOUNCE_COOLDOWN_SEC


class TestMessageQueue:
    def setup_method(self):
        self.mq = MessageQueue()
        self.tts = MagicMock()
        self.producer = MagicMock()

    def test_build_message_emergency(self):
        assert self.mq.build_message("stop", "emergency").startswith("Emergency alert!")

    def test_build_message_high(self):
        assert self.mq.build_message("obstacle", "high").startswith("Warning.")

    def test_build_message_normal(self):
        assert self.mq.build_message("ok", "normal") == "ok"

    def test_detection_above_threshold_speaks(self):
        data = {"detections": [{"class_name": "person", "confidence": 0.9}]}
        self.mq.handle_detection(data, self.tts, self.producer)
        self.tts.speak_async.assert_called_once()

    def test_detection_below_threshold_silent(self):
        data = {"detections": [{"class_name": "person", "confidence": 0.3}]}
        self.mq.handle_detection(data, self.tts, self.producer)
        self.tts.speak_async.assert_not_called()

    def test_detection_cooldown_blocks_repeat(self):
        data = {"detections": [{"class_name": "car", "confidence": 0.9}]}
        self.mq.handle_detection(data, self.tts, self.producer)
        self.mq.handle_detection(data, self.tts, self.producer)
        assert self.tts.speak_async.call_count == 1

    def test_navigation_emergency_action(self):
        data = {"result": {"next_action": "emergency", "confidence": 0.9}}
        self.mq.handle_navigation(data, self.tts, self.producer)
        call_arg = self.tts.speak_async.call_args[0][0]
        assert "Emergency" in call_arg

    def test_navigation_low_confidence(self):
        data = {"result": {"next_action": "left", "confidence": 0.1}}
        self.mq.handle_navigation(data, self.tts, self.producer)
        call_arg = self.tts.speak_async.call_args[0][0]
        assert "Warning" in call_arg

    def test_command_speak(self):
        data = {"action": "speak", "message": "hello", "priority": "normal"}
        self.mq.handle_command(data, self.tts, self.producer)
        self.tts.speak_async.assert_called_once()

    def test_command_announce(self):
        data = {"action": "announce", "event": "mission_complete"}
        self.mq.handle_command(data, self.tts, self.producer)
        self.tts.speak_async.assert_called_once()

    def test_stats_tracks_total(self):
        data = {"result": {"next_action": "hover", "confidence": 0.8}}
        self.mq.handle_navigation(data, self.tts, self.producer)
        assert self.mq.stats()["total_spoken"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])