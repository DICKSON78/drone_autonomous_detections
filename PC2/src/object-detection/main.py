from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel
import cv2
import numpy as np
import torch
import json
import logging
import asyncio
import base64
from kafka import KafkaProducer, KafkaConsumer
from typing import List, Dict, Optional
import uvicorn
from ultralytics import YOLO
import time

app = FastAPI(title="Object Detection Service")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Kafka setup
producer = KafkaProducer(
    bootstrap_servers=['PC1:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

consumer = KafkaConsumer(
    'drone.commands.detection',
    bootstrap_servers=['PC1:9092'],
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)

# Load YOLOv5 model
try:
    model = YOLO('yolov8n.pt')  # You can use yolov8s.pt for better accuracy
    logger.info("YOLOv8 model loaded successfully")
except Exception as e:
    logger.error(f"Failed to load YOLO model: {e}")
    model = None

class DetectionResult(BaseModel):
    class_name: str
    confidence: float
    bbox: List[float]  # [x1, y1, x2, y2]
    timestamp: str

class DetectionResponse(BaseModel):
    detections: List[DetectionResult]
    image_width: int
    image_height: int
    processing_time: float
    timestamp: str

class DroneTelemetry(BaseModel):
    position: Dict
    altitude: float
    battery: float
    status: str

# Object classes relevant for drone missions
RELEVANT_CLASSES = {
    'person', 'car', 'truck', 'bicycle', 'motorcycle', 'bus',
    'dog', 'cat', 'horse', 'cow', 'sheep', 'bird',
    'tree', 'bush', 'building', 'house', 'road', 'river'
}

def filter_relevant_detections(detections):
    """Filter detections to only include relevant objects for drone missions"""
    relevant_detections = []
    for det in detections:
        class_name = model.names[int(det.cls)] if model and hasattr(model, 'names') else 'unknown'
        if class_name in RELEVANT_CLASSES:
            relevant_detections.append({
                'class_name': class_name,
                'confidence': float(det.conf),
                'bbox': det.xyxy[0].tolist()
            })
    return relevant_detections

async def process_image(image_data: np.ndarray) -> DetectionResponse:
    """Process image with YOLOv8 and return detections"""
    if model is None:
        raise HTTPException(status_code=500, detail="YOLO model not loaded")
    
    start_time = time.time()
    
    # Run inference
    results = model(image_data)
    
    # Process results
    detections = []
    for result in results:
        relevant_dets = filter_relevant_detections(result.boxes)
        for det in relevant_dets:
            detections.append(DetectionResult(
                class_name=det['class_name'],
                confidence=det['confidence'],
                bbox=det['bbox'],
                timestamp=time.time()
            ))
    
    processing_time = time.time() - start_time
    
    return DetectionResponse(
        detections=detections,
        image_width=image_data.shape[1],
        image_height=image_data.shape[0],
        processing_time=processing_time,
        timestamp=time.time()
    )

def simulate_camera_feed():
    """Simulate camera feed from drone"""
    # This would normally connect to Gazebo camera feed
    # For now, generate random test images
    height, width = 480, 640
    return np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)

async def continuous_detection():
    """Run continuous object detection in background"""
    while True:
        try:
            # Simulate getting image from drone camera
            image = simulate_camera_feed()
            
            # Process image
            result = await process_image(image)
            
            # Send detections to Kafka
            if result.detections:
                detection_data = {
                    'detections': [det.dict() for det in result.detections],
                    'timestamp': result.timestamp,
                    'processing_time': result.processing_time
                }
                
                producer.send('drone.detections.objects', detection_data)
                logger.info(f"Sent {len(result.detections)} detections to Kafka")
            
            await asyncio.sleep(0.1)  # 10 FPS
            
        except Exception as e:
            logger.error(f"Error in continuous detection: {e}")
            await asyncio.sleep(1)

# API Routes
@app.post("/detect", response_model=DetectionResponse)
async def detect_objects(file: UploadFile = File(...)):
    """Detect objects in uploaded image"""
    try:
        # Read and decode image
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            raise HTTPException(status_code=400, detail="Invalid image file")
        
        # Process image
        result = await process_image(image)
        return result
        
    except Exception as e:
        logger.error(f"Detection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/detect-base64", response_model=DetectionResponse)
async def detect_objects_base64(image_data: dict):
    """Detect objects in base64 encoded image"""
    try:
        # Decode base64 image
        image_bytes = base64.b64decode(image_data['image'])
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            raise HTTPException(status_code=400, detail="Invalid image data")
        
        # Process image
        result = await process_image(image)
        return result
        
    except Exception as e:
        logger.error(f"Detection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "object-detection",
        "model_loaded": model is not None,
        "timestamp": time.time()
    }

@app.get("/classes")
async def get_supported_classes():
    """Get list of supported object classes"""
    if model and hasattr(model, 'names'):
        return {
            "all_classes": list(model.names.values()),
            "relevant_classes": list(RELEVANT_CLASSES)
        }
    return {"all_classes": [], "relevant_classes": list(RELEVANT_CLASSES)}

@app.post("/start-continuous")
async def start_continuous_detection():
    """Start continuous object detection"""
    # In a real implementation, this would start a background task
    return {"status": "continuous detection started"}

@app.post("/stop-continuous")
async def stop_continuous_detection():
    """Stop continuous object detection"""
    # In a real implementation, this would stop the background task
    return {"status": "continuous detection stopped"}

@app.get("/stats")
async def get_detection_stats():
    """Get detection statistics"""
    return {
        "total_detections": 0,  # Would be tracked in real implementation
        "average_processing_time": 0.0,
        "fps": 10.0
    }

# Kafka message handler
async def handle_kafka_messages():
    """Handle incoming Kafka messages"""
    while True:
        try:
            # Poll for messages
            msg_pack = consumer.poll(timeout_ms=1000)
            
            for tp, messages in msg_pack.items():
                for message in messages:
                    logger.info(f"Received command: {message.value}")
                    
                    # Process detection commands
                    if message.value.get('action') == 'start_detection':
                        await start_continuous_detection()
                    elif message.value.get('action') == 'stop_detection':
                        await stop_continuous_detection()
        
        except Exception as e:
            logger.error(f"Kafka message handling error: {e}")
            await asyncio.sleep(1)

@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    logger.info("Starting Object Detection Service")
    
    # Start background tasks
    asyncio.create_task(continuous_detection())
    asyncio.create_task(handle_kafka_messages())

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
