"""
NLG Generator — rule-based natural language generation for drone obstacle feedback.

Produces varied, human-readable sentences describing what was detected, where it
is in the camera frame, and what avoidance action was taken.  No ML, no LLM.

Usage
-----
    gen = NLGFeedback()
    msg = gen.generate({"class_name": "tree", "confidence": 0.92}, 0.75, "strafe_left")
    # -> "Tree detected on the right. Adjusting course to the left."
"""

import logging
import random
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)


# ── Position buckets ──────────────────────────────────────────────────────────

def _position_label(rel_x: float) -> str:
    """Map normalised horizontal position (0=left … 1=right) to a label."""
    if rel_x < 0.25:
        return "far left"
    if rel_x < 0.40:
        return "on the left"
    if rel_x < 0.60:
        return "dead ahead"
    if rel_x < 0.75:
        return "on the right"
    return "far right"


def _position_bucket_key(rel_x: float) -> str:
    """Coarse bucket for cooldown deduplication."""
    if rel_x < 0.33:
        return "left"
    if rel_x < 0.66:
        return "center"
    return "right"


# ── Template banks ────────────────────────────────────────────────────────────
# Each key is a tuple (has_class_name, has_action).
# Each entry is a list of template strings with {placeholders}.

_TEMPLATES: dict[tuple[bool, bool], list[str]] = {
    # ── Has class_name, has action ─────────────────────────────────────────
    (True, True): [
        "{name} detected {position}. {action}.",
        "Obstacle: {name} spotted {position}. {action}.",
        "{name} {position}. {action}.",
        "Warning — {name} {position}. {action}.",
        "{name} sighted {position}. {action}.",
        "{action} — {name} {position}.",
    ],
    # ── Has class_name, no action ──────────────────────────────────────────
    (True, False): [
        "{name} detected {position}.",
        "Obstacle: {name} spotted {position}.",
        "{name} {position}.",
        "Warning — {name} {position}.",
        "{name} sighted {position}.",
    ],
    # ── No class_name, has action ──────────────────────────────────────────
    (False, True): [
        "Unknown object detected {position}. {action}.",
        "Obstacle spotted {position}. {action}.",
        "Something ahead {position}. {action}.",
    ],
    # ── No class_name, no action ───────────────────────────────────────────
    (False, False): [
        "Unknown object detected {position}.",
        "Obstacle spotted {position}.",
        "Something ahead {position}.",
    ],
}

_ACTION_PHRASES: dict[str, list[str]] = {
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

_DEFAULT_ACTION_PHRASES: list[str] = [
    "Taking evasive action",
    "Avoiding obstacle",
    "Adjusting course",
]


def _resolve_action(action_key: str | None) -> str:
    if action_key is None:
        return ""
    action_key = action_key.lower()
    bank = _ACTION_PHRASES.get(action_key)
    if not bank:
        return random.choice(_DEFAULT_ACTION_PHRASES)
    return random.choice(bank)


# ── NLG Feedback generator ────────────────────────────────────────────────────


class NLGFeedback:
    """Rule-based NLG for obstacle-detection feedback with cooldown and optional TTS."""

    def __init__(self, cooldown_seconds: float = 5.0):
        self._cooldown_seconds = cooldown_seconds
        self._cooldown_store: dict[str, float] = {}
        self._lock = threading.Lock()
        self._tts_engine = None
        logger.info(
            "NLGFeedback initialised (cooldown=%ss)", cooldown_seconds
        )

    # ── Optional TTS (offline, pyttsx3) ────────────────────────────────────

    def _init_tts(self) -> None:
        if self._tts_engine is not None:
            return
        try:
            import pyttsx3  # type: ignore[import-untyped]

            self._tts_engine = pyttsx3.init()
            self._tts_engine.setProperty("rate", 150)
            self._tts_engine.setProperty("volume", 1.0)
            logger.info("TTS engine initialised for NLG")
        except ImportError:
            logger.info("pyttsx3 not available — NLG will be text-only")
        except Exception as exc:
            logger.warning("TTS init failed — text-only mode: %s", exc)

    def speak(self, text: str) -> None:
        """Speak *text* on a background thread (fails silently)."""
        self._init_tts()
        if self._tts_engine is None:
            return
        try:
            t = threading.Thread(target=self._speak_sync, args=(text,), daemon=True)
            t.start()
        except Exception as exc:
            logger.debug("TTS thread start failed: %s", exc)

    def _speak_sync(self, text: str) -> None:
        try:
            self._tts_engine.say(text)
            self._tts_engine.runAndWait()
        except Exception as exc:
            logger.debug("TTS speak error (degraded): %s", exc)

    # ── Cooldown ───────────────────────────────────────────────────────────

    def _cooldown_key(self, name: str, rel_x: float) -> str:
        bucket = _position_bucket_key(rel_x)
        return f"{name}|{bucket}"

    def _check_cooldown(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            last = self._cooldown_store.get(key, 0.0)
            if (now - last) < self._cooldown_seconds:
                return True  # still on cooldown
            self._cooldown_store[key] = now
        return False

    # ── Main generate method ───────────────────────────────────────────────

    def generate(
        self,
        detection: dict[str, Any],
        rel_x: float,
        action_key: str | None = None,
        *,
        allow_cooldown: bool = True,
    ) -> str:
        """Generate a natural-language feedback sentence.

        Parameters
        ----------
        detection:
            Dict with at least *bbox* (xyxy list).  If *class_name* is present
            it is used; otherwise the object is called "unknown object".
        rel_x:
            Normalised horizontal centre of the detection (0 = left, 1 = right).
        action_key:
            Optional key into _ACTION_PHRASES (or any string for fallback).
        allow_cooldown:
            When True (default) the same (class_name, position-bucket) pair
            will not be re-reported within *cooldown_seconds*.

        Returns
        -------
        Generated sentence (empty string if suppressed by cooldown).
        """
        class_name = detection.get("class_name") or detection.get("class", "")
        if not class_name or class_name == "unknown":
            class_name = ""

        if allow_cooldown:
            cd_key = self._cooldown_key(class_name or "unknown", rel_x)
            if self._check_cooldown(cd_key):
                logger.debug("Cooldown suppressed: %s", cd_key)
                return ""

        position = _position_label(rel_x)
        action_phrase = _resolve_action(action_key)

        has_class = bool(class_name)
        has_action = bool(action_phrase)

        templates = _TEMPLATES.get((has_class, has_action), _TEMPLATES[(False, False)])
        template = random.choice(templates)

        sentence = template.format(
            name=class_name or "unknown object",
            position=position,
            action=action_phrase,
        )

        logger.debug(
            "NLG: cls=%r rel_x=%.2f action=%r -> %s",
            class_name, rel_x, action_key, sentence,
        )
        return sentence


# ── Standalone convenience function ───────────────────────────────────────────

_DEFAULT_NLG = NLGFeedback()


def generate_feedback(
    detection: dict[str, Any],
    rel_x: float,
    action_key: str | None = None,
    *,
    speak: bool = False,
    allow_cooldown: bool = True,
) -> str:
    """One-shot convenience wrapper around ``NLGFeedback.generate()``."""
    sentence = _DEFAULT_NLG.generate(
        detection, rel_x, action_key, allow_cooldown=allow_cooldown,
    )
    if speak and sentence:
        _DEFAULT_NLG.speak(sentence)
    return sentence
