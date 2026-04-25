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

# ── Config (kept inline so this file is self-contained as the entry point) ───
KAFKA_SERVERS  = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
KAFKA_GROUP    = "feedback-service-group"
KAFKA_IN       = ["drone.commands.feedback", "drone.detections.objects", "drone.navigation.result"]
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

# ── Globals (set during lifespan) ─────────────────────────────────────────────
tts: TTSEngine
mq:  MessageQueue
audio: AudioManager


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
    detections = [
        d for d in data.get("detections", [])
        if d.get("confidence", 0) >= CONFIDENCE_THR
    ]
    if not detections:
        return
    classes = list({d.get("class_name", "object") for d in detections})
    label   = classes[0] if len(classes) == 1 else f"{len(detections)} objects"
    text    = f"{len(detections)} {label} detected"
    if queue.enqueue(text, "high"):
        _publish_spoken(producer, "Warning. " + text, "high", "drone.detections.objects")


def _handle_navigation(data: dict, queue: MessageQueue, producer) -> None:
    action     = data.get("action", "")
    confidence = data.get("confidence", 0)
    if not action or confidence < CONFIDENCE_THR:
        return
    text = f"Navigation: {action}"
    if queue.enqueue(text, "normal"):
        _publish_spoken(producer, text, "normal", "drone.navigation.result")


def _handle_command(data: dict, queue: MessageQueue, producer) -> None:
    text     = data.get("message", "")
    priority = data.get("priority", "normal")
    if not text:
        return
    if queue.enqueue(text, priority):
        prefix = {"high": "Warning. ", "emergency": "Emergency alert! "}.get(priority, "")
        _publish_spoken(producer, prefix + text, priority, "drone.commands.feedback")


def _kafka_thread(queue: MessageQueue) -> None:
    """Runs forever in a daemon thread. Reconnects automatically."""
    try:
        from kafka import KafkaConsumer, KafkaProducer  # type: ignore
    except ImportError:
        log.warning("kafka-python not installed — Kafka consumer disabled")
        return

    _HANDLERS = {
        "drone.detections.objects":  _handle_detections,
        "drone.navigation.result":   _handle_navigation,
        "drone.commands.feedback":   _handle_command,
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
            log.info("Kafka consumer connected to %s", KAFKA_SERVERS)
            for msg in consumer:
                handler = _HANDLERS.get(msg.topic)
                if handler:
                    try:
                        handler(msg.value, queue, producer)
                    except Exception as exc:
                        log.error("Handler error on %s: %s", msg.topic, exc)
        except Exception as exc:
            log.warning("Kafka error (%s) — retry in 10 s", exc)
            if producer:
                try: producer.close()
                except Exception: pass
            time.sleep(10)


# ── FastAPI lifespan ──────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global tts, mq, audio
    tts   = TTSEngine(rate=TTS_RATE, volume=TTS_VOLUME, voice_index=TTS_VOICE_IDX)
    audio = AudioManager()
    mq    = MessageQueue(
        speak_fn=tts.speak,
        cooldown_seconds=COOLDOWN_SEC,
    )
    threading.Thread(target=_kafka_thread, args=(mq,), daemon=True, name="kafka").start()
    log.info("Feedback service started on port %d", PORT)
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
        "status":     "healthy",
        "service":    "feedback-service",
        "audio_ok":   tts.available,
        "queue_size": mq.size,
        "timestamp":  time.time(),
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
        "service":       "feedback-service",
        "queue_stats":   mq.stats,
        "audio_ok":      tts.available,
        "kafka_servers": KAFKA_SERVERS,
        "timestamp":     time.time(),
    }


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("feedback:app", host="0.0.0.0", port=PORT, log_level="info")
