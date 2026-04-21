import threading
import logging
import os

logger = logging.getLogger(__name__)

_lock = threading.Lock()


class TTSEngine:
    """Thread-safe pyttsx3 wrapper with configurable voice settings."""

    def __init__(self):
        self.rate   = int(os.getenv("TTS_RATE", 150))
        self.volume = float(os.getenv("TTS_VOLUME", 1.0))
        self.voice_index = os.getenv("TTS_VOICE_INDEX")
        logger.info(f"TTSEngine init: rate={self.rate} volume={self.volume}")

    def _make_engine(self):
        """Create a fresh engine instance (pyttsx3 is not thread-safe to share)."""
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty('rate', self.rate)
            engine.setProperty('volume', self.volume)
            if self.voice_index is not None:
                voices = engine.getProperty('voices')
                idx = int(self.voice_index)
                if 0 <= idx < len(voices):
                    engine.setProperty('voice', voices[idx].id)
            return engine
        except Exception as e:
            logger.warning(f"TTS engine unavailable: {e}")
            return None

    def speak_blocking(self, message: str) -> bool:
        """Speak message synchronously. Returns True if audio played."""
        with _lock:
            engine = self._make_engine()
            if engine is None:
                logger.info(f"[TTS-SILENT] {message}")
                return False
            try:
                engine.say(message)
                engine.runAndWait()
                logger.info(f"[TTS] {message}")
                return True
            except Exception as e:
                logger.error(f"TTS speak error: {e}")
                return False
            finally:
                try:
                    engine.stop()
                except Exception:
                    pass

    def speak_async(self, message: str):
        """Fire-and-forget speech call."""
        t = threading.Thread(target=self.speak_blocking, args=(message,), daemon=True)
        t.start()

    def list_voices(self) -> list:
        """Return all available voices on this system."""
        engine = self._make_engine()
        if engine is None:
            return []
        try:
            voices = engine.getProperty('voices')
            return [{"index": i, "id": v.id, "name": v.name}
                    for i, v in enumerate(voices)]
        except Exception:
            return []
        finally:
            try:
                engine.stop()
            except Exception:
                pass