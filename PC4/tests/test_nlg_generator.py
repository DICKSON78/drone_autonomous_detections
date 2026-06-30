"""
Unit tests for the rule-based NLG feedback generator.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src/feedback-service"))

from nlg_generator import NLGFeedback, generate_feedback


SAMPLE_DETECTION = {
    "class_name": "tree",
    "confidence": 0.92,
    "bbox": [100.0, 200.0, 150.0, 250.0],
}

SAMPLE_DETECTION_NO_CLASS = {
    "confidence": 0.85,
    "bbox": [300.0, 100.0, 400.0, 200.0],
}


class TestGenerateFeedback:
    def test_with_class_name(self):
        sentence = generate_feedback(SAMPLE_DETECTION, 0.75,
                                     allow_cooldown=False)
        assert isinstance(sentence, str)
        assert len(sentence) > 0
        assert "tree" in sentence.lower()

    def test_without_class_name(self):
        sentence = generate_feedback(SAMPLE_DETECTION_NO_CLASS, 0.75,
                                     allow_cooldown=False)
        assert isinstance(sentence, str)
        assert len(sentence) > 0
        assert any(w in sentence.lower()
                   for w in ("unknown", "obstacle", "something"))

    def test_with_action(self):
        sentence = generate_feedback(SAMPLE_DETECTION, 0.2, "strafe_left",
                                     allow_cooldown=False)
        assert "left" in sentence.lower()

    def test_different_positions(self):
        for rel_x, keyword in [(0.1, "left"), (0.5, "ahead"), (0.9, "right")]:
            sentence = generate_feedback(
                SAMPLE_DETECTION, rel_x, "strafe_right",
                allow_cooldown=False,
            )
            assert keyword in sentence.lower(), (
                f"Expected {keyword!r} in {sentence!r}"
            )

    def test_different_actions(self):
        for action in ("ascend", "descend", "hover", "forward"):
            sentence = generate_feedback(SAMPLE_DETECTION, 0.5, action,
                                         allow_cooldown=False)
            assert sentence, f"Empty sentence for action={action!r}"
            assert len(sentence) > 10, f"Sentence too short: {sentence!r}"


class TestNLGFeedback:
    def setup_method(self):
        self.nlg = NLGFeedback(cooldown_seconds=0.01)

    def test_cooldown_suppresses_duplicate(self):
        first = self.nlg.generate(SAMPLE_DETECTION, 0.75, "strafe_left")
        assert first != ""
        second = self.nlg.generate(SAMPLE_DETECTION, 0.75, "strafe_left")
        assert second == ""

    def test_cooldown_allows_different_position(self):
        first = self.nlg.generate(SAMPLE_DETECTION, 0.1, "strafe_left")
        assert first != ""
        second = self.nlg.generate(SAMPLE_DETECTION, 0.9, "strafe_right")
        assert second != ""

    def test_cooldown_expires(self):
        nlg = NLGFeedback(cooldown_seconds=0.0)
        first = nlg.generate(SAMPLE_DETECTION, 0.5, "hover")
        assert first != ""
        second = nlg.generate(SAMPLE_DETECTION, 0.5, "hover")
        assert second != ""

    def test_varied_output(self):
        sentences = set()
        nlg = NLGFeedback(cooldown_seconds=0.0)
        for _ in range(30):
            s = nlg.generate(SAMPLE_DETECTION, 0.5, "strafe_left",
                            allow_cooldown=False)
            if s:
                sentences.add(s)
        assert len(sentences) >= 2, (
            f"Only {len(sentences)} unique sentences: {sentences}"
        )
