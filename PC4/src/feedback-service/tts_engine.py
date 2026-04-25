"""
TTS Engine — wraps pyttsx3 so the rest of the app never touches the library directly.
pyttsx3 is NOT thread-safe; a single lock serialises every call.
"""

import logging
import threading
from typing import Optional

import pyttsx3

log = logging.getLogger("tts-engine")


class TTSEngine:
    """Thread-safe wrapper around pyttsx3."""

    def __init__(self, rate: int = 150, volume: float = 1.0, voice_index: int = 0):
        self._rate = rate
        self._volume = volume
        self._voice_index = voice_index
        self._engine: Optional[pyttsx3.Engine] = None
        self._lock = threading.Lock()
        self._available = False
        self._init()

    # ── Initialisation ────────────────────────────────────────────────────────

    def _init(self) -> None:
        try:
            self._engine = pyttsx3.init()
            self._apply_settings()
            self._available = True
            log.info(
                "TTS engine ready  rate=%d wpm  volume=%.1f  voice=%d",
                self._rate, self._volume, self._voice_index,
            )
        except Exception as exc:
            log.warning("TTS engine could not start: %s — audio disabled", exc)

    def _apply_settings(self) -> None:
        assert self._engine is not None
        self._engine.setProperty("rate", self._rate)
        self._engine.setProperty("volume", self._volume)
        voices = self._engine.getProperty("voices") or []
        if voices and self._voice_index < len(voices):
            self._engine.setProperty("voice", voices[self._voice_index].id)

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def available(self) -> bool:
        return self._available

    def speak(self, text: str) -> bool:
        """Speak *text* synchronously. Returns True on success."""
        if not self._available or not self._engine:
            log.warning("TTS unavailable — skipping: %s", text)
            return False
        with self._lock:
            try:
                self._engine.say(text)
                self._engine.runAndWait()
                log.debug("Spoken: %s", text)
                return True
            except Exception as exc:
                log.error("TTS speak error: %s", exc)
                return False

    def set_rate(self, rate: int) -> None:
        """Change speech rate at runtime."""
        self._rate = rate
        if self._engine:
            with self._lock:
                self._engine.setProperty("rate", rate)

    def set_volume(self, volume: float) -> None:
        """Change volume (0.0–1.0) at runtime."""
        self._volume = max(0.0, min(1.0, volume))
        if self._engine:
            with self._lock:
                self._engine.setProperty("volume", self._volume)

    def get_voices(self) -> list[dict]:
        """Return list of available voices."""
        if not self._engine:
            return []
        voices = self._engine.getProperty("voices") or []
        return [
            {"index": i, "id": v.id, "name": v.name}
            for i, v in enumerate(voices)
        ]