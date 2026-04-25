"""
Message Queue — priority-ordered queue that feeds the TTS engine.

Design:
  • Uses Python's heapq-backed PriorityQueue (lower tuple value = higher priority).
  • A cooldown dict prevents the same message being repeated within COOLDOWN_SECONDS.
  • A background daemon thread drains the queue and calls tts.speak().
  • Stats are tracked for the /stats endpoint.
"""

import logging
import threading
import time
from queue import Empty, PriorityQueue
from typing import Callable, Optional

log = logging.getLogger("message-queue")

# Priority numbers fed into PriorityQueue (lower = dequeued first)
_PRIORITY_MAP = {
    "emergency": 0,
    "high":      1,
    "normal":    2,
    "low":       3,
}

_PREFIX_MAP = {
    "emergency": "Emergency alert! ",
    "high":      "Warning. ",
    "normal":    "",
    "low":       "",
}


class MessageQueue:
    """
    Thread-safe priority queue with cooldown deduplication.

    Args:
        speak_fn:         Callable that actually produces audio (returns bool).
        cooldown_seconds: Minimum gap (s) before the same text is spoken again.
        on_spoken:        Optional callback(text, priority) called after each
                          successful speech event (used for Kafka publishing).
    """

    def __init__(
        self,
        speak_fn: Callable[[str], bool],
        cooldown_seconds: float = 5.0,
        on_spoken: Optional[Callable[[str, str], None]] = None,
    ):
        self._speak = speak_fn
        self._cooldown_sec = cooldown_seconds
        self._on_spoken = on_spoken

        self._queue: PriorityQueue = PriorityQueue()
        self._cooldown: dict[str, float] = {}
        self._lock = threading.Lock()

        # Stats
        self._total_enqueued = 0
        self._total_spoken = 0
        self._total_dropped_cooldown = 0
        self._total_dropped_audio = 0

        # Start worker
        self._worker = threading.Thread(target=self._drain, daemon=True, name="mq-worker")
        self._worker.start()

    # ── Public ────────────────────────────────────────────────────────────────

    def enqueue(self, message: str, priority: str = "normal") -> bool:
        """
        Add *message* to the queue.

        Returns True if queued, False if suppressed by cooldown.
        """
        priority = priority if priority in _PRIORITY_MAP else "normal"
        prefixed = _PREFIX_MAP[priority] + message

        with self._lock:
            if self._in_cooldown(prefixed):
                log.debug("Cooldown — skipped: %s", prefixed)
                self._total_dropped_cooldown += 1
                return False
            pnum = _PRIORITY_MAP[priority]
            # Tie-break on insertion time so FIFO order holds within same priority
            self._queue.put((pnum, time.monotonic(), prefixed, priority))
            self._total_enqueued += 1
            log.debug("Enqueued [%s]: %s", priority, prefixed)
            return True

    @property
    def size(self) -> int:
        return self._queue.qsize()

    @property
    def stats(self) -> dict:
        return {
            "queue_size":             self.size,
            "total_enqueued":         self._total_enqueued,
            "total_spoken":           self._total_spoken,
            "total_dropped_cooldown": self._total_dropped_cooldown,
            "total_dropped_audio":    self._total_dropped_audio,
        }

    # ── Internal ──────────────────────────────────────────────────────────────

    def _in_cooldown(self, text: str) -> bool:
        last = self._cooldown.get(text, 0.0)
        return (time.monotonic() - last) < self._cooldown_sec

    def _drain(self) -> None:
        """Worker thread: continuously pop and speak."""
        while True:
            try:
                pnum, _, text, priority = self._queue.get(timeout=1.0)
            except Empty:
                continue
            except Exception as exc:
                log.error("Queue drain error: %s", exc)
                continue

            try:
                # Refresh cooldown stamp before speaking to block duplicates
                # that arrived while we were in the queue
                with self._lock:
                    self._cooldown[text] = time.monotonic()

                spoken = self._speak(text)

                with self._lock:
                    if spoken:
                        self._total_spoken += 1
                        log.info("Spoken [%s]: %s", priority, text)
                    else:
                        self._total_dropped_audio += 1

                if spoken and self._on_spoken:
                    try:
                        self._on_spoken(text, priority)
                    except Exception as cb_exc:
                        log.warning("on_spoken callback error: %s", cb_exc)
            except Exception as exc:
                log.error("Worker speak error: %s", exc)
            finally:
                self._queue.task_done()