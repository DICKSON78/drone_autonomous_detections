 # rl-navigation from main entry

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import numpy as np
import logging
import asyncio
from kafka import KafkaProducer, KafkaConsumer
import time
import uvicorn
import json
import os
from typing import List, Dict

from rl_handler import RLHandler

app = FastAPI(title="PC2 - RL Navigation Service")

logger = logging.getLogger(__name__)

# Kafka configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092').split(',')

producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

consumer = KafkaConsumer(
    'drone.commands.navigation',
    'drone.detections.objects',
    'drone.telemetry.gps',
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    auto_offset_reset='latest',
    enable_auto_commit=True
)

agent = RLHandler(model_path="/app/models/rl/navigation_agent")

class NavigationRequest(BaseModel):
    current_position: List[float]
    target_position: List[float]
    obstacles: List[Dict] = []

class NavigationResponse(BaseModel):
    next_action: str
    confidence: float
    path: List[List[float]]
    estimated_time: float

@app.post("/navigate", response_model=NavigationResponse)
async def navigate(request: NavigationRequest):
    try:
        # Get current position and target from request
        drone_pos = request.current_position
        target_pos = request.target_position
        obstacles = request.obstacles

        action_name, confidence = agent.get_action(drone_pos, target_pos, obstacles)
        
        response = NavigationResponse(
            next_action=action_name,
            confidence=confidence,
            path=[drone_pos], # Path planning not implemented in PPO simple inference
            estimated_time=1.0
        )
        
        # Send decision to Kafka
        producer.send('drone.navigation.decisions', response.dict())
        
        return response
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "rl-navigation"}

@app.on_event("startup")
async def startup():
    logger.info("RL Navigation Service Started")
    # Model already loaded in RLHandler.__init__
    # Start autonomous loop
    asyncio.create_task(autonomous_navigation_loop())

async def autonomous_navigation_loop():
    """Background loop to process live detections and make decisions"""
    logger.info("Autonomous navigation loop started")
    current_pos = [0.5, 0.5, 0.5]
    target_pos = [0.6, 0.6, 0.5] # Default target if none set
    
    for message in consumer:
        try:
            if message.topic == 'drone.telemetry.gps':
                data = message.value
                # Normalize GPS to 0-1 (approx for Dodoma area)
                current_pos = [0.5, 0.5, data.get('altitude', 0.0) / 100.0]
                
            elif message.topic == 'drone.detections.objects':
                data = message.value
                detections = data.get('detections', [])
                unsupervised = data.get('unsupervised', {})
                
                # If obstacles are detected, calculate avoidance
                if detections or unsupervised:
                    action_name, confidence = agent.get_action(current_pos, target_pos, detections)
                    
                    decision = {
                        "action": action_name,
                        "confidence": confidence,
                        "source": "autonomous_vision",
                        "timestamp": time.time()
                    }
                    producer.send('drone.navigation.decisions', decision)
                    logger.info(f"Autonomous Decision: {decision['action']}")
                    
        except Exception as e:
            logger.error(f"Error in autonomous loop: {e}")
            await asyncio.sleep(1)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)