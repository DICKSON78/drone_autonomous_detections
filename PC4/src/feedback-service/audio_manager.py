"""
Audio Manager — discovers ALSA devices and validates audio hardware availability.
"""

import logging
import subprocess
from dataclasses import dataclass

log = logging.getLogger("audio-manager")


@dataclass
class AudioDevice:
    card: int
    device: int
    name: str
    raw: str


class AudioManager:
    """Queries the host ALSA subsystem for available playback devices."""

    def list_devices(self) -> list[AudioDevice]:
        """Return all ALSA playback devices found via `aplay -l`."""
        try:
            result = subprocess.run(
                ["aplay", "-l"],
                capture_output=True, text=True, timeout=5,
            )
            return self._parse(result.stdout)
        except FileNotFoundError:
            log.warning("aplay not found — ALSA device listing unavailable")
            return []
        except subprocess.TimeoutExpired:
            log.warning("aplay timed out")
            return []
        except Exception as exc:
            log.error("aplay error: %s", exc)
            return []

    def _parse(self, output: str) -> list[AudioDevice]:
        devices: list[AudioDevice] = []
        for line in output.splitlines():
            if not line.startswith("card"):
                continue
            try:
                # e.g. "card 0: PCH [HDA Intel PCH], device 0: ALC3246 ..."
                parts = line.split(":")
                card_part = parts[0].strip()          # "card 0"
                card_num = int(card_part.split()[1])
                # device number
                dev_part = line.split("device")[1].split(":")[0].strip()
                dev_num = int(dev_part)
                # name from second colon-segment
                name = parts[1].strip() if len(parts) > 1 else "unknown"
                devices.append(AudioDevice(card=card_num, device=dev_num, name=name, raw=line.strip()))
            except (IndexError, ValueError):
                continue
        return devices

    def default_device_available(self) -> bool:
        """True if at least one playback device exists."""
        return len(self.list_devices()) > 0

    def device_strings(self) -> list[str]:
        """Human-readable list of device strings (for the REST API)."""
        devices = self.list_devices()
        if not devices:
            return ["No ALSA devices found"]
        return [d.raw for d in devices]