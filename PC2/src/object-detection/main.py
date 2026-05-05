# object-detection from main entry


from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel
import cv2
import numpy as np
import json
import logging
import asyncio
import base64
from kafka import KafkaProducer, KafkaConsumer
from typing import List, Dict
import time
import uvicorn

from .yolo_handler import YOLOHandler
from .camera_sim import CameraSimulator
from .image_processor import ImageProcessor

app = FastAPI(title="PC2 - Object Detection Service")

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize components
detector = YOLOHandler(model_name="yolov8n.pt", device="auto")
camera = CameraSimulator(width=640, height=480, source="simulation")
image_processor = ImageProcessor()

# Kafka (use service name inside Docker network)
producer = KafkaProducer(
    bootstrap_servers=['pc1:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

consumer = KafkaConsumer(
    'drone.commands.detection',
    bootstrap_servers=['pc1:9092'],
    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    auto_offset_reset='latest',
    enable_auto_commit=True
)

class DetectionResult(BaseModel):
    class_name: str
    confidence: float
    bbox: List[float]
    timestamp: str

class DetectionResponse(BaseModel):
    detections: List[DetectionResult]
    image_width: int
    image_height: int
    processing_time: float
    timestamp: str

@app.post("/detect", response_model=DetectionResponse)
async def detect_objects(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image is None:
            raise HTTPException(400, detail="Invalid image")

        start = time.time()
        detections = detector.detect(image, conf_threshold=0.5)
        processing_time = time.time() - start

        result = DetectionResponse(
            detections=[DetectionResult(**d) for d in detections],
            image_width=image.shape[1],
            image_height=image.shape[0],
            processing_time=processing_time,
            timestamp=time.time()
        )

        # Send to Kafka
        if detections:
            producer.send('drone.telemetry.detections', result.dict())

        return result

    except Exception as e:
        logger.error(f"Detection failed: {e}")
        raise HTTPException(500, detail=str(e))


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "pc2-object-detection",
        "model_loaded": True
    }


async def continuous_detection_loop():
    """Background continuous detection task"""
    logger.info("Starting continuous detection loop...")
    while True:
        try:
            frame = camera.capture_frame()
            if frame is not None:
                detections = detector.detect(frame)
                if detections:
                    producer.send('drone.telemetry.detections', {
                        "detections": detections,
                        "timestamp": time.time(),
                        "source": "continuous"
                    })
            await asyncio.sleep(0.1)  # ~10 FPS
        except Exception as e:
            logger.error(f"Continuous detection error: {e}")
            await asyncio.sleep(1)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(continuous_detection_loop())
    logger.info("PC2 Object Detection Service Started")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)