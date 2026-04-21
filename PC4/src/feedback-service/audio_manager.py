import logging
import subprocess
import os

logger = logging.getLogger(__name__)


class AudioManager:
    """Manages audio device detection, validation, and health checking."""

    def check_devices(self):
        """Log available audio devices on startup."""
        devices = self.list_devices()
        if devices:
            logger.info(f"Audio devices found: {devices}")
        else:
            logger.warning("No audio devices found — TTS will run in silent mode")

    def list_devices(self) -> list:
        """Return a list of available audio output devices."""
        devices = []
        # Try aplay (ALSA) first — standard on Linux
        try:
            result = subprocess.run(
                ["aplay", "-l"], capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.splitlines():
                if line.startswith("card"):
                    devices.append(line.strip())
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.debug(f"aplay device list error: {e}")

        # Fallback: check /dev/snd directly
        if not devices and os.path.isdir("/dev/snd"):
            try:
                entries = os.listdir("/dev/snd")
                devices = [f"/dev/snd/{e}" for e in entries if e.startswith("pcm")]
            except Exception:
                pass

        return devices

    def is_available(self) -> bool:
        """Return True if at least one audio output device is present."""
        return len(self.list_devices()) > 0

    def get_default_device(self) -> str | None:
        """Return the name of the default audio device, or None."""
        devices = self.list_devices()
        return devices[0] if devices else None