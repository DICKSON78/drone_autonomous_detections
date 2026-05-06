# Main reinforcement learning navigation FastAPI service

"""
RL Agent for Fully Autonomous Drone Navigation
Using DQN - Optimized for real-time autonomous operation
"""

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import random
import logging
from collections import deque
from typing import Tuple, List, Dict

logger = logging.getLogger(__name__)

class DQN(nn.Module):
    """Deep Q-Network for autonomous navigation"""
    def __init__(self, state_dim: int = 14, action_dim: int = 6):
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
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.network(x)


class RLAgent:
    """Autonomous Drone Navigation Agent"""
    
    def __init__(self, state_dim: int = 14, action_dim: int = 6, device: str = "auto"):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.device = device if device != "auto" else ("cuda" if torch.cuda.is_available() else "cpu")
        
        self.policy_net = DQN(state_dim, action_dim).to(self.device)
        self.target_net = DQN(state_dim, action_dim).to(self.device)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        
        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=0.001)
        
        self.memory = deque(maxlen=20000)
        
        # Training parameters
        self.gamma = 0.99
        self.epsilon = 0.1          # Low epsilon for autonomous mode (mostly exploit)
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.995
        self.batch_size = 128
        self.target_update = 200
        self.steps_done = 0
        
        logger.info(f"Autonomous RL Agent initialized on {self.device} | Epsilon: {self.epsilon}")

    def get_action(self, state: np.ndarray, deterministic: bool = True) -> int:
        """
        Get next action for autonomous flight
        - deterministic=True during real flight (exploitation)
        """
        self.steps_done += 1
        
        # In real autonomous mode, mostly use best action
        if not deterministic and random.random() < self.epsilon:
            return random.randrange(self.action_dim)
        
        with torch.no_grad():
            state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            q_values = self.policy_net(state_tensor)
            action = q_values.argmax().item()
            
        return action

    def remember(self, state, action, reward, next_state, done):
        """Store experience for training"""
        self.memory.append((state, action, reward, next_state, done))

    def train(self) -> float:
        """Perform one training step"""
        if len(self.memory) < self.batch_size:
            return 0.0

        batch = random.sample(self.memory, self.batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)

        states = torch.FloatTensor(np.array(states)).to(self.device)
        actions = torch.LongTensor(actions).unsqueeze(1).to(self.device)
        rewards = torch.FloatTensor(rewards).to(self.device)
        next_states = torch.FloatTensor(np.array(next_states)).to(self.device)
        dones = torch.BoolTensor(dones).to(self.device)

        current_q = self.policy_net(states).gather(1, actions).squeeze(1)
        
        with torch.no_grad():
            next_q = self.target_net(next_states).max(1)[0]
            next_q[dones] = 0.0
        
        target_q = rewards + self.gamma * next_q

        loss = nn.MSELoss()(current_q, target_q)

        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.policy_net.parameters(), 1.0)
        self.optimizer.step()

        # Decay exploration
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

        # Update target network
        if self.steps_done % self.target_update == 0:
            self.target_net.load_state_dict(self.policy_net.state_dict())

        return loss.item()

    def save(self, path: str = "/app/models/rl_navigation.pth"):
        torch.save({
            'policy_net': self.policy_net.state_dict(),
            'target_net': self.target_net.state_dict(),
            'optimizer': self.optimizer.state_dict(),
            'epsilon': self.epsilon,
            'steps_done': self.steps_done
        }, path)
        logger.info(f"Model saved: {path}")

    def load(self, path: str = "/app/models/rl_navigation.pth"):
        try:
            checkpoint = torch.load(path, map_location=self.device)
            self.policy_net.load_state_dict(checkpoint['policy_net'])
            self.target_net.load_state_dict(checkpoint['target_net'])
            self.optimizer.load_state_dict(checkpoint['optimizer'])
            self.epsilon = checkpoint.get('epsilon', 0.1)
            logger.info(f"Loaded pretrained model for autonomous flight")
            return True
        except Exception:
            logger.warning("No pretrained model found - using fresh agent")
            return False