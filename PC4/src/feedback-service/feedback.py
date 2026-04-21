from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
import logging
import asyncio
import time
from kafka import KafkaProducer, KafkaConsumer
from typing import Optional
import uvicorn

from tts_engine import TTSEngine
from audio_manager import AudioManager
from message_queue import MessageQueue

app = FastAPI(title="Feedback Service")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Kafka ─────────────────────────────────────────────────────────────────────

producer = KafkaProducer(
    bootstrap_servers=['PC1:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

consumer = KafkaConsumer(
    'drone.commands.feedback',
    'drone.detections.objects',
    'drone.navigation.result',
    bootstrap_servers=['PC1:9092'],
    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    group_id='feedback-service-group',
    auto_offset_reset='latest'
)

# ── Service instances ─────────────────────────────────────────────────────────

tts    = TTSEngine()
audio  = AudioManager()
mqueue = MessageQueue()

# ── Pydantic models ───────────────────────────────────────────────────────────

class SpeakRequest(BaseModel):
    message: str
    priority: Optional[str] = "normal"
    async_mode: Optional[bool] = True

class SpeakResponse(BaseModel):
    status: str
    message: str
    priority: str
    spoken: bool
    timestamp: float

class AnnounceRequest(BaseModel):
    event: str
    details: Optional[str] = ""

# ── Kafka consumer loop ───────────────────────────────────────────────────────

async def handle_kafka_messages():
    while True:
        try:
            msg_pack = consumer.poll(timeout_ms=1000)
            for tp, messages in msg_pack.items():
                for message in messages:
                    topic = tp.topic
                    data  = message.value
                    logger.info(f"[Kafka] {topic}: {str(data)[:100]}")

                    if topic == 'drone.detections.objects':
                        mqueue.handle_detection(data, tts, producer)
                    elif topic == 'drone.navigation.result':
                        mqueue.handle_navigation(data, tts, producer)
                    elif topic == 'drone.commands.feedback':
                        mqueue.handle_command(data, tts, producer)
        except Exception as e:
            logger.error(f"Kafka error: {e}")
            await asyncio.sleep(1)

# ── API routes ────────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "feedback-service",
        "audio_devices": audio.list_devices(),
        "timestamp": time.time()
    }

@app.post("/speak", response_model=SpeakResponse)
async def speak(request: SpeakRequest):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="message field is required")

    priority = (request.priority or "normal").lower()
    if priority not in {"low", "normal", "high", "emergency"}:
        raise HTTPException(status_code=400, detail="Invalid priority")

    msg = mqueue.build_message(request.message.strip(), priority)

    if request.async_mode:
        tts.speak_async(msg)
        spoken = True
    else:
        spoken = tts.speak_blocking(msg)

    producer.send('drone.feedback.spoken', {
        "message": msg, "priority": priority,
        "trigger": "api", "timestamp": time.time()
    })

    return SpeakResponse(status="ok", message=msg, priority=priority,
                         spoken=spoken, timestamp=time.time())

@app.post("/announce")
async def announce(request: AnnounceRequest):
    if not request.event.strip():
        raise HTTPException(status_code=400, detail="event field is required")
    text = request.event.replace("_", " ")
    if request.details:
        text = f"{text}. {request.details}"
    msg = mqueue.build_message(text, "high")
    tts.speak_async(msg)
    producer.send('drone.feedback.spoken', {
        "message": msg, "priority": "high",
        "trigger": "announce", "event": request.event, "timestamp": time.time()
    })
    return {"status": "announced", "event": request.event, "message": msg}

@app.get("/voices")
async def list_voices():
    return {"voices": tts.list_voices()}

@app.get("/audio-devices")
async def list_audio_devices():
    return {"devices": audio.list_devices()}

@app.get("/stats")
async def get_stats():
    return {
        "service": "feedback-service",
        "queue_stats": mqueue.stats(),
        "audio_ok": audio.is_available(),
        "timestamp": time.time()
    }

# ── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    logger.info("Starting Feedback Service on port 8005")
    audio.check_devices()
    asyncio.create_task(handle_kafka_messages())

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8005)