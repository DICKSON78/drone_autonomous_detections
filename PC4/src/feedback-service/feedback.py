"""
PC4 — Feedback Service  (entry point: feedback.py)
Provides REST API + Kafka consumer → TTS voice output.
"""

import json
import logging
import os
import threading
import time
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from audio_manager import AudioManager
from message_queue import MessageQueue
from tts_engine import TTSEngine
from nlg_generator import NLGFeedback

# ── Config (kept inline so this file is self-contained as the entry point) ───
KAFKA_SERVERS  = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
KAFKA_GROUP    = "feedback-service-group"
KAFKA_IN       = ["drone.commands.flight", "drone.detections.objects", "drone.navigation.decisions", "drone.status.flight"]
KAFKA_OUT      = "drone.feedback.spoken"
TTS_RATE       = int(os.getenv("TTS_RATE",        "150"))
TTS_VOLUME     = float(os.getenv("TTS_VOLUME",    "1.0"))
TTS_VOICE_IDX  = int(os.getenv("TTS_VOICE_INDEX", "0"))
PORT           = int(os.getenv("PORT",            "8005"))
CONFIDENCE_THR = 0.65
COOLDOWN_SEC   = 5.0

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
)
log = logging.getLogger("feedback-service")

# File logging for NLG testing evidence
_nlg_log_file = os.getenv("NLG_LOG_FILE", "/var/log/nlg_generator.log")
try:
    os.makedirs(os.path.dirname(_nlg_log_file), exist_ok=True)
    _nlg_fh = logging.FileHandler(_nlg_log_file)
    _nlg_fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    log.addHandler(_nlg_fh)
except Exception:
    pass

# ── Globals (set during lifespan) ─────────────────────────────────────────────
tts: TTSEngine
mq:  MessageQueue
audio: AudioManager
nlg:  NLGFeedback
_kafka_connected: bool = False


# ── Kafka helpers ─────────────────────────────────────────────────────────────

def _publish_spoken(producer, text: str, priority: str, source: str) -> None:
    if producer is None:
        return
    try:
        producer.send(KAFKA_OUT, {
            "message": text, "priority": priority,
            "source_topic": source, "timestamp": time.time(),
        })
    except Exception as exc:
        log.warning("Kafka publish error: %s", exc)


def _handle_detections(data: dict, queue: MessageQueue, producer) -> None:
    raw = [
        d for d in data.get("detections", [])
        if d.get("confidence", 0) >= CONFIDENCE_THR
    ]
    if not raw:
        return

    # Frame width: detect from bbox values or fall back to camera default (640).
    frame_width = 640
    for d in raw:
        bbox = d.get("bbox") or []
        if len(bbox) == 4:
            # If pixel coords look normalised (< 1) scale accordingly
            if max(bbox) <= 1.0:
                frame_width = 1.0
            break

    # Sort by confidence descending
    raw.sort(key=lambda d: d.get("confidence", 0), reverse=True)

    # Generate NLG message for the top detection
    top = raw[0]
    bbox = top.get("bbox") or [0, 0, 0, 0]
    cx = (bbox[0] + bbox[2]) / 2.0
    rel_x = cx / frame_width if frame_width > 0 else 0.5

    text = nlg.generate(top, rel_x, allow_cooldown=True)
    if not text:
        # Suppressed by cooldown — try the next detection if any
        for alt in raw[1:]:
            alt_bbox = alt.get("bbox") or [0, 0, 0, 0]
            alt_cx = (alt_bbox[0] + alt_bbox[2]) / 2.0
            alt_rel_x = alt_cx / frame_width if frame_width > 0 else 0.5
            text = nlg.generate(alt, alt_rel_x, allow_cooldown=True)
            if text:
                break

    if not text:
        return  # everything on cooldown

    # Append count if multiple distinct objects
    if len(raw) > 1:
        distinct = list({d.get("class_name", "object") for d in raw})
        text += f" Plus {len(raw) - 1} more obstacle{'s' if len(raw) > 2 else ''}."

    log.info("NLG: %s", text)

    if queue.enqueue(text, "high"):
        # Also speak on background thread (text-only if TTS unavailable)
        nlg.speak(text)
        _publish_spoken(producer, "Warning. " + text, "high", "drone.detections.objects")


def _handle_navigation(data: dict, queue: MessageQueue, producer) -> None:
    action     = data.get("action", "")
    confidence = data.get("confidence", 0)
    if not action or confidence < CONFIDENCE_THR:
        return
    text = f"Navigation: {action}"
    if queue.enqueue(text, "normal"):
        _publish_spoken(producer, text, "normal", "drone.navigation.decisions")


def _handle_command(data: dict, queue: MessageQueue, producer) -> None:
    text     = data.get("raw_text", data.get("message", ""))
    priority = data.get("priority", "normal")
    cmd_type = data.get("type", "")
    if not text and not cmd_type:
        return
    if not text:
        text = f"Command: {cmd_type}"
    if queue.enqueue(text, priority):
        prefix = {"high": "Warning. ", "emergency": "Emergency alert! "}.get(priority, "")
        _publish_spoken(producer, prefix + text, priority, "drone.commands.flight")


def _handle_status(data: dict, queue: MessageQueue, producer) -> None:
    status   = data.get("status", "")
    cmd_type = data.get("command_type", "command")
    if not status:
        return
    text = f"Flight {status}"
    if queue.enqueue(text, "normal"):
        _publish_spoken(producer, text, "normal", "drone.status.flight")


def _wait_for_kafka(timeout: int = 60) -> bool:
    """Block until Kafka is reachable or *timeout* seconds elapse."""
    try:
        from kafka.admin import KafkaAdminClient
    except ImportError:
        return False
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            admin = KafkaAdminClient(
                bootstrap_servers=KAFKA_SERVERS,
                client_id="feedback-service-init",
            )
            admin.list_topics()
            admin.close()
            log.info("Kafka is reachable at %s", KAFKA_SERVERS)
            return True
        except Exception as exc:
            log.warning("Waiting for Kafka at %s (%s) …", KAFKA_SERVERS, exc)
            time.sleep(5)
    log.error("Kafka not reachable after %d s — starting without Kafka", timeout)
    return False


def _kafka_thread(queue: MessageQueue) -> None:
    """Runs forever in a daemon thread. Reconnects automatically."""
    global _kafka_connected
    try:
        from kafka import KafkaConsumer, KafkaProducer  # type: ignore
    except ImportError:
        log.warning("kafka-python not installed — Kafka consumer disabled")
        return

    _HANDLERS = {
        "drone.detections.objects":  _handle_detections,
        "drone.navigation.decisions":  _handle_navigation,
        "drone.commands.flight":   _handle_command,
        "drone.status.flight":     _handle_status,
    }

    while True:
        producer = None
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode(),
            )
            consumer = KafkaConsumer(
                *KAFKA_IN,
                bootstrap_servers=KAFKA_SERVERS,
                group_id=KAFKA_GROUP,
                value_deserializer=lambda b: json.loads(b.decode()),
                auto_offset_reset="latest",
                consumer_timeout_ms=5000,
            )
            _kafka_connected = True
            log.info("Kafka consumer connected to %s", KAFKA_SERVERS)
            for msg in consumer:
                handler = _HANDLERS.get(msg.topic)
                if handler:
                    try:
                        handler(msg.value, queue, producer)
                    except Exception as exc:
                        log.error("Handler error on %s: %s", msg.topic, exc)
        except Exception as exc:
            _kafka_connected = False
            log.warning("Kafka error (%s) — retry in 10 s", exc)
            if producer:
                try: producer.close()
                except Exception: pass
            time.sleep(10)


# ── FastAPI lifespan ──────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global tts, mq, audio, nlg
    tts   = TTSEngine(rate=TTS_RATE, volume=TTS_VOLUME, voice_index=TTS_VOICE_IDX)
    audio = AudioManager()
    mq    = MessageQueue(
        speak_fn=tts.speak,
        cooldown_seconds=COOLDOWN_SEC,
    )
    nlg   = NLGFeedback(cooldown_seconds=COOLDOWN_SEC)
    kafka_ok = _wait_for_kafka(timeout=60)
    threading.Thread(target=_kafka_thread, args=(mq,), daemon=True, name="kafka").start()
    if kafka_ok:
        log.info("Feedback service started on port %d — Kafka connected", PORT)
    else:
        log.warning("Feedback service started on port %d — Kafka NOT available", PORT)
    yield
    log.info("Feedback service shutdown")


app = FastAPI(title="PC4 Feedback Service", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class SpeakRequest(BaseModel):
    message: str
    priority: str = "normal"
    async_mode: bool = True

class AnnounceRequest(BaseModel):
    event: str
    details: str = ""


# ── Endpoints ─────────────────────────────────────────────────────────────────

VALID_PRIORITIES = {"low", "normal", "high", "emergency"}

EVENT_MESSAGES = {
    "startup":      ("Drone system starting up",        "normal"),
    "shutdown":     ("Drone system shutting down",       "normal"),
    "low_battery":  ("Battery level is low",             "high"),
    "obstacle":     ("Obstacle detected ahead",          "high"),
    "landing":      ("Drone is landing",                 "normal"),
    "takeoff":      ("Drone is taking off",               "normal"),
    "mission_done": ("Mission complete",                  "normal"),
    "emergency":    ("Emergency situation detected",      "emergency"),
}


@app.get("/health")
def health():
    return {
        "status":           "healthy",
        "service":          "feedback-service",
        "audio_ok":         tts.available,
        "kafka_connected":  _kafka_connected,
        "queue_size":       mq.size,
        "timestamp":        time.time(),
    }


@app.post("/speak")
def speak(req: SpeakRequest):
    if req.priority not in VALID_PRIORITIES:
        raise HTTPException(422, f"priority must be one of {sorted(VALID_PRIORITIES)}")
    queued = mq.enqueue(req.message, req.priority)
    return {
        "status":    "ok",
        "message":   req.message,
        "priority":  req.priority,
        "queued":    queued,
        "timestamp": time.time(),
    }


@app.post("/announce")
def announce(req: AnnounceRequest):
    text, priority = EVENT_MESSAGES.get(req.event, (f"Event: {req.event}", "normal"))
    if req.details:
        text += f". {req.details}"
    mq.enqueue(text, priority)
    return {"status": "announced", "event": req.event, "message": text, "priority": priority}


@app.get("/voices")
def voices():
    return {"voices": tts.get_voices()}


@app.get("/audio-devices")
def audio_devices():
    return {"devices": audio.device_strings(), "default_available": audio.default_device_available()}


@app.get("/stats")
def stats():
    return {
        "service":          "feedback-service",
        "queue_stats":      mq.stats,
        "audio_ok":         tts.available,
        "kafka_connected":  _kafka_connected,
        "kafka_servers":    KAFKA_SERVERS,
        "timestamp":        time.time(),
    }


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("feedback:app", host="0.0.0.0", port=PORT, log_level="info")
