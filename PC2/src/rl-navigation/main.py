from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import numpy as np
import torch
import torch.nn as nn
import json
import logging
import asyncio
from kafka import KafkaProducer, KafkaConsumer
from typing import List, Dict, Optional, Tuple
import uvicorn
import time
import gym
from collections import deque
import random

app = FastAPI(title="RL Navigation Service")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Kafka setup
producer = KafkaProducer(
    bootstrap_servers=['PC1:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

consumer = KafkaConsumer(
    'drone.commands.navigation',
    bootstrap_servers=['PC1:9092'],
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)

# RL Model Definition
class DQN(nn.Module):
    """Deep Q-Network for drone navigation"""
    def __init__(self, state_dim: int, action_dim: int):
        super(DQN, self).__init__()
        self.network = nn.Sequential(
            nn.Linear(state_dim, 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, action_dim)
        )
    
    def forward(self, x):
        return self.network(x)

class NavigationEnvironment:
    """Simulated navigation environment for training and inference"""
    def __init__(self):
        self.grid_size = 100
        self.obstacles = self._generate_obstacles()
        self.target_position = None
        self.drone_position = np.array([50.0, 50.0, 10.0])  # x, y, altitude
        self.max_steps = 1000
        self.current_step = 0
        
    def _generate_obstacles(self):
        """Generate random obstacles in the environment"""
        obstacles = []
        for _ in range(20):  # 20 random obstacles
            x = random.randint(10, 90)
            y = random.randint(10, 90)
            radius = random.randint(2, 5)
            obstacles.append({'position': [x, y], 'radius': radius})
        return obstacles
    
    def reset(self, target_position: List[float]):
        """Reset environment with new target"""
        self.target_position = np.array(target_position[:2])  # Only x, y
        self.drone_position = np.array([50.0, 50.0, 10.0])
        self.current_step = 0
        return self._get_state()
    
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, Dict]:
        """Execute action and return new state, reward, done, info"""
        # Action mapping: 0=up, 1=down, 2=left, 3=right, 4=forward, 5=backward
        action_map = {
            0: [0, 1],    # up (increase y)
            1: [0, -1],   # down (decrease y)
            2: [-1, 0],   # left (decrease x)
            3: [1, 0],    # right (increase x)
            4: [0, 0],    # hover
            5: [0, 0],    # emergency stop
        }
        
        if action < len(action_map):
            movement = action_map[action]
            self.drone_position[0] += movement[0]
            self.drone_position[1] += movement[1]
        
        # Keep drone in bounds
        self.drone_position[0] = np.clip(self.drone_position[0], 0, 100)
        self.drone_position[1] = np.clip(self.drone_position[1], 0, 100)
        
        self.current_step += 1
        
        # Calculate reward
        reward = self._calculate_reward()
        done = self._is_done()
        
        return self._get_state(), reward, done, {}
    
    def _get_state(self) -> np.ndarray:
        """Get current state representation"""
        # State: [drone_x, drone_y, target_x, target_y, distance_to_target, obstacle_distances]
        state = [
            self.drone_position[0] / 100.0,  # Normalize to [0,1]
            self.drone_position[1] / 100.0,
            self.target_position[0] / 100.0,
            self.target_position[1] / 100.0
        ]
        
        # Add obstacle distances
        for obstacle in self.obstacles[:5]:  # Limit to 5 nearest obstacles
            dist = np.linalg.norm(self.drone_position[:2] - obstacle['position'])
            state.append(min(dist / 20.0, 1.0))  # Normalize and cap
        
        # Pad if fewer obstacles
        while len(state) < 14:  # 4 + 10 = 14
            state.append(0.0)
        
        return np.array(state)
    
    def _calculate_reward(self) -> float:
        """Calculate reward based on current state"""
        if self.target_position is None:
            return -1.0
        
        # Distance to target
        distance = np.linalg.norm(self.drone_position[:2] - self.target_position)
        
        # Reward for getting closer to target
        reward = -distance / 100.0
        
        # Bonus for reaching target
        if distance < 2.0:
            reward += 100.0
        
        # Penalty for hitting obstacles
        for obstacle in self.obstacles:
            if np.linalg.norm(self.drone_position[:2] - obstacle['position']) < obstacle['radius']:
                reward -= 50.0
        
        # Small penalty for each step to encourage efficiency
        reward -= 0.1
        
        return reward
    
    def _is_done(self) -> bool:
        """Check if episode is done"""
        if self.target_position is None:
            return True
        
        distance = np.linalg.norm(self.drone_position[:2] - self.target_position)
        return distance < 2.0 or self.current_step >= self.max_steps

# Global variables
env = NavigationEnvironment()
model = None
target_network = None
optimizer = None
memory = deque(maxlen=10000)
epsilon = 1.0
epsilon_decay = 0.995
epsilon_min = 0.01
batch_size = 32
gamma = 0.99
target_update_freq = 100

class NavigationRequest(BaseModel):
    current_position: List[float]
    target_position: List[float]
    obstacles: Optional[List[Dict]] = None

class NavigationResponse(BaseModel):
    next_action: str
    confidence: float
    path: List[List[float]]
    estimated_time: float

def initialize_model():
    """Initialize RL model"""
    global model, target_network, optimizer
    
    state_dim = 14  # Based on our state representation
    action_dim = 6  # up, down, left, right, hover, emergency
    
    model = DQN(state_dim, action_dim)
    target_network = DQN(state_dim, action_dim)
    target_network.load_state_dict(model.state_dict())
    
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    
    # Load pretrained model if available
    try:
        model.load_state_dict(torch.load('/app/models/rl_navigation_model.pth'))
        logger.info("Pretrained model loaded successfully")
    except FileNotFoundError:
        logger.info("No pretrained model found, starting with random weights")

def get_action(state: np.ndarray, training: bool = False) -> Tuple[int, float]:
    """Get action from model"""
    global epsilon
    
    if training and random.random() < epsilon:
        return random.randint(0, 5), 0.0  # Random action
    
    with torch.no_grad():
        state_tensor = torch.FloatTensor(state).unsqueeze(0)
        q_values = model(state_tensor)
        action = q_values.argmax().item()
        confidence = torch.softmax(q_values, dim=1).max().item()
        return action, confidence

def train_model():
    """Train the RL model"""
    if len(memory) < batch_size:
        return
    
    batch = random.sample(memory, batch_size)
    states = torch.FloatTensor([transition[0] for transition in batch])
    actions = torch.LongTensor([transition[1] for transition in batch])
    rewards = torch.FloatTensor([transition[2] for transition in batch])
    next_states = torch.FloatTensor([transition[3] for transition in batch])
    dones = torch.BoolTensor([transition[4] for transition in batch])
    
    current_q_values = model(states).gather(1, actions.unsqueeze(1))
    next_q_values = target_network(next_states).max(1)[0].detach()
    target_q_values = rewards + (gamma * next_q_values * ~dones)
    
    loss = nn.MSELoss()(current_q_values.squeeze(), target_q_values)
    
    optimizer.zero_grad()
    loss.backward()
    optimizer.step()
    
    # Update epsilon
    global epsilon
    epsilon = max(epsilon_min, epsilon * epsilon_decay)

async def navigate_to_target(request: NavigationRequest) -> NavigationResponse:
    """Navigate drone to target using RL"""
    try:
        # Update environment with current request
        env.drone_position = np.array(request.current_position)
        env.obstacles = request.obstacles or env.obstacles
        
        # Get initial state
        state = env.reset(request.target_position)
        
        path = [request.current_position.copy()]
        total_confidence = 0.0
        steps = 0
        max_steps = 100
        
        while steps < max_steps:
            # Get action from model
            action, confidence = get_action(state, training=False)
            total_confidence += confidence
            
            # Execute action
            next_state, reward, done, info = env.step(action)
            
            # Add to path
            path.append(env.drone_position.tolist())
            
            if done:
                break
            
            state = next_state
            steps += 1
            await asyncio.sleep(0.01)  # Small delay to prevent blocking
        
        # Map action to human-readable format
        action_names = ["up", "down", "left", "right", "hover", "emergency"]
        next_action = action_names[action] if 'action' in locals() else "hover"
        
        return NavigationResponse(
            next_action=next_action,
            confidence=total_confidence / max(1, steps),
            path=path,
            estimated_time=steps * 0.1  # Assuming 0.1s per step
        )
        
    except Exception as e:
        logger.error(f"Navigation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# API Routes
@app.post("/navigate", response_model=NavigationResponse)
async def navigate(request: NavigationRequest):
    """Navigate to target position"""
    return await navigate_to_target(request)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "rl-navigation",
        "model_loaded": model is not None,
        "epsilon": epsilon,
        "memory_size": len(memory)
    }

@app.post("/train")
async def start_training(episodes: int = 100):
    """Start training the RL model"""
    try:
        for episode in range(episodes):
            # Reset environment
            target = [random.randint(10, 90), random.randint(10, 90)]
            state = env.reset(target)
            total_reward = 0
            done = False
            
            while not done:
                action, _ = get_action(state, training=True)
                next_state, reward, done, _ = env.step(action)
                
                # Store experience
                memory.append((state, action, reward, next_state, done))
                
                state = next_state
                total_reward += reward
                
                # Train model
                train_model()
            
            if episode % 10 == 0:
                logger.info(f"Episode {episode}, Total Reward: {total_reward}")
            
            # Update target network
            if episode % target_update_freq == 0:
                target_network.load_state_dict(model.state_dict())
        
        # Save model
        torch.save(model.state_dict(), '/app/models/rl_navigation_model.pth')
        
        return {"status": "training completed", "episodes": episodes}
        
    except Exception as e:
        logger.error(f"Training error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/model-info")
async def get_model_info():
    """Get model information"""
    return {
        "model_type": "DQN",
        "state_dim": 14,
        "action_dim": 6,
        "memory_size": len(memory),
        "epsilon": epsilon,
        "training_samples": len(memory)
    }

# Kafka message handler
async def handle_kafka_messages():
    """Handle incoming Kafka messages"""
    while True:
        try:
            msg_pack = consumer.poll(timeout_ms=1000)
            
            for tp, messages in msg_pack.items():
                for message in messages.value:
                    logger.info(f"Received navigation command: {message}")
                    
                    if message.get('action') == 'navigate':
                        request = NavigationRequest(
                            current_position=message.get('current_position', [50, 50, 10]),
                            target_position=message.get('target_position', [75, 75]),
                            obstacles=message.get('obstacles', [])
                        )
                        
                        result = await navigate_to_target(request)
                        
                        # Send result back
                        producer.send('drone.navigation.result', {
                            'command_id': message.get('command_id'),
                            'result': result.dict(),
                            'timestamp': time.time()
                        })
        
        except Exception as e:
            logger.error(f"Kafka message handling error: {e}")
            await asyncio.sleep(1)

@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    logger.info("Starting RL Navigation Service")
    initialize_model()
    
    # Start background tasks
    asyncio.create_task(handle_kafka_messages())

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)
