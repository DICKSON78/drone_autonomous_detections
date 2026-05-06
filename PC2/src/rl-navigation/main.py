 # rl-navigation from main entry

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import numpy as np
import torch
import logging
import asyncio
from kafka import KafkaProducer, KafkaConsumer
import time
import uvicorn

from .environment import NavigationEnvironment
from .rl_agent import RLAgent

app = FastAPI(title="PC2 - RL Navigation Service")

logger = logging.getLogger(__name__)

# Kafka (use docker service name)
producer = KafkaProducer(bootstrap_servers=['pc1:9092'], value_serializer=lambda v: json.dumps(v).encode('utf-8'))
consumer = KafkaConsumer('drone.commands.navigation', bootstrap_servers=['pc1:9092'], 
                        value_deserializer=lambda m: json.loads(m.decode('utf-8')))

env = NavigationEnvironment()
agent = RLAgent(state_dim=14, action_dim=6)

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
        state = env.reset(request.target_position)
        path = [request.current_position]
        
        for _ in range(50):  # Max planning steps
            action = agent.get_action(state, deterministic=True)
            next_state, _, done, _ = env.step(action)
            path.append(env.drone_position.tolist())
            state = next_state
            if done:
                break
                
        action_names = ["up", "down", "left", "right", "hover", "emergency"]
        return NavigationResponse(
            next_action=action_names[action],
            confidence=0.85,
            path=path,
            estimated_time=len(path) * 0.2
        )
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "rl-navigation"}

@app.on_event("startup")
async def startup():
    logger.info("RL Navigation Service Started")
    # Load model if exists
    agent.load()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)