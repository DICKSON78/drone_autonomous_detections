#!/usr/bin/env python3
"""
Drone Environment for Reinforcement Learning
Environment ya drone kwa ajili ya kuepuka vizuizi
"""

import gymnasium as gym
import numpy as np
from gymnasium import spaces
from typing import Dict, List, Tuple, Any, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DroneObstacleEnv(gym.Env):
    """
    Drone obstacle avoidance environment.
    
    State:  obstacles zilizoonwa na YOLO
    Action: [go_left, go_right, climb, descend, forward, stop]
    Reward: +10 kama inaepuka, -100 kama inagonga, +1 kila hatua salama
    """

    ACTIONS = {
        0: "go_left",
        1: "go_right", 
        2: "climb",
        3: "descend",
        4: "forward",
        5: "stop",
    }

    def __init__(self, config: Dict = None):
        super().__init__()
        
        self.config = config or self._default_config()
        
        # State: [x, y, w, h, class, confidence] × max obstacles
        self.max_obstacles = self.config["max_obstacles"]
        self.obs_features = self.config["obs_features"]
        
        # Observation space: normalized coordinates and features
        self.observation_space = spaces.Box(
            low=0.0,
            high=1.0,
            shape=(self.max_obstacles * self.obs_features,),
            dtype=np.float32
        )

        # Action space: 6 discrete actions
        self.action_space = spaces.Discrete(6)

        # Environment state
        self.obstacles = []
        self.step_count = 0
        self.max_steps = self.config["max_steps"]
        self.drone_position = [0.5, 0.5]  # Center position
        self.collision_threshold = self.config["collision_threshold"]
        
        # Statistics
        self.total_reward = 0
        self.episodes_completed = 0
        self.crashes_count = 0

    def _default_config(self) -> Dict:
        """Default environment configuration"""
        return {
            "max_obstacles": 10,
            "obs_features": 6,
            "max_steps": 200,
            "collision_threshold": 0.1,
            "obstacle_speed": 0.02,
            "detection_confidence": 0.5,
            "reward_config": {
                "safe_forward": 1.0,
                "avoidance": 10.0,
                "crash": -100.0,
                "stop_penalty": -5.0,
                "step_penalty": -0.1
            }
        }

    def reset(self, seed: Optional[int] = None, options: Optional[Dict] = None) -> Tuple[np.ndarray, Dict]:
        """Reset environment to initial state"""
        super().reset(seed=seed)
        
        self.obstacles = self._generate_random_obstacles()
        self.step_count = 0
        self.drone_position = [0.5, 0.5]
        self.total_reward = 0
        
        obs = self._get_observation()
        info = self._get_info()
        
        return obs, info

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """Execute one step in the environment"""
        self.step_count += 1
        
        # Calculate reward and termination
        reward, terminated = self._compute_reward(action)
        self.total_reward += reward
        
        # Update drone position based on action
        self._update_drone_position(action)
        
        # Move obstacles (simulate drone movement)
        self._update_obstacles()
        
        # Check for crashes
        crashed = self._check_collision()
        if crashed:
            terminated = True
            self.crashes_count += 1
            reward = self.config["reward_config"]["crash"]
        
        # Check if episode should truncate
        truncated = self.step_count >= self.max_steps
        
        # Get new observation
        obs = self._get_observation()
        info = self._get_info()
        
        if terminated or truncated:
            self.episodes_completed += 1
            logger.info(f"Episode {self.episodes_completed} completed. Steps: {self.step_count}, Reward: {self.total_reward}")
        
        return obs, reward, terminated, truncated, info

    def _compute_reward(self, action: int) -> Tuple[float, bool]:
        """
        Compute reward based on current state and action.
        
        Reward logic:
        - Kizuizi kipo mbele na karibu → lazima epuka
        - Action sahihi = +10
        - Action mbaya = -20  
        - Hakuna kizuizi na anasogea mbele = +1
        """
        danger_obstacles = self._get_danger_obstacles()
        
        if not danger_obstacles:
            # Hakuna hatari — endelea mbele
            reward = self.config["reward_config"]["safe_forward"] if action == 4 else 0.0
            return reward, False
        
        # Kizuizi kipo — lazima epuka
        obs = danger_obstacles[0]
        center_x = obs["x"]
        
        # Determine best avoidance action
        if action in [0, 1, 2, 3]:  # epuka kwa njia yoyote
            return self.config["reward_config"]["avoidance"], False
        elif action == 4:  # aliendelea mbele — hatari!
            return self.config["reward_config"]["crash"], True
        else:  # stop
            return self.config["reward_config"]["stop_penalty"], False

    def _get_danger_obstacles(self) -> List[Dict]:
        """Get obstacles that pose immediate danger"""
        return [
            obs for obs in self.obstacles
            if obs["x"] > 0.4 and obs["w"] > 0.25 and obs["confidence"] > self.config["detection_confidence"]
        ]

    def _update_drone_position(self, action: int):
        """Update drone position based on action"""
        move_distance = 0.05
        
        if action == 0:  # go_left
            self.drone_position[0] = max(0.1, self.drone_position[0] - move_distance)
        elif action == 1:  # go_right
            self.drone_position[0] = min(0.9, self.drone_position[0] + move_distance)
        elif action == 2:  # climb
            self.drone_position[1] = max(0.1, self.drone_position[1] - move_distance)
        elif action == 3:  # descend
            self.drone_position[1] = min(0.9, self.drone_position[1] + move_distance)
        elif action == 4:  # forward (move towards obstacles)
            pass  # Forward movement is simulated by moving obstacles closer

    def _update_obstacles(self):
        """Update obstacle positions (simulate drone forward movement)"""
        obstacle_speed = self.config["obstacle_speed"]
        
        self.obstacles = [
            {**obs, "x": obs["x"] - obstacle_speed}
            for obs in self.obstacles
            if obs["x"] > -0.1  # Remove obstacles that have passed
        ]

    def _check_collision(self) -> bool:
        """Check if drone has collided with any obstacle"""
        for obs in self.obstacles:
            # Simple collision detection based on distance
            distance = np.sqrt((self.drone_position[0] - obs["x"])**2 + 
                             (self.drone_position[1] - obs["y"])**2)
            
            if distance < self.collision_threshold:
                return True
        
        return False

    def _get_observation(self) -> np.ndarray:
        """Get current observation as normalized array"""
        obs_array = np.zeros(self.max_obstacles * self.obs_features, dtype=np.float32)
        
        for i, obs in enumerate(self.obstacles[:self.max_obstacles]):
            base = i * self.obs_features
            obs_array[base + 0] = obs["x"]
            obs_array[base + 1] = obs["y"]
            obs_array[base + 2] = obs["w"]
            obs_array[base + 3] = obs["h"]
            obs_array[base + 4] = obs["class"] / 6.0  # normalize class (0-5)
            obs_array[base + 5] = obs["confidence"]
        
        return obs_array

    def _get_info(self) -> Dict:
        """Get additional environment information"""
        return {
            "step_count": self.step_count,
            "obstacles_count": len(self.obstacles),
            "danger_obstacles": len(self._get_danger_obstacles()),
            "drone_position": self.drone_position.copy(),
            "total_reward": self.total_reward,
            "episodes_completed": self.episodes_completed,
            "crashes_count": self.crashes_count
        }

    def _generate_random_obstacles(self) -> List[Dict]:
        """Generate random obstacles for training"""
        n = np.random.randint(1, 5)
        return [
            {
                "x": np.random.uniform(0.1, 0.9),
                "y": np.random.uniform(0.1, 0.9),
                "w": np.random.uniform(0.05, 0.4),
                "h": np.random.uniform(0.05, 0.4),
                "class": np.random.randint(0, 6),
                "confidence": np.random.uniform(0.5, 1.0),
            }
            for _ in range(n)
        ]

    def obstacles_from_yolo(self, yolo_detections):
        """Update obstacles using actual YOLO detection results"""
        if hasattr(yolo_detections, 'boxes'):
            self.obstacles = [
                {
                    "x": float(box.xywhn[0][0]),
                    "y": float(box.xywhn[0][1]),
                    "w": float(box.xywhn[0][2]),
                    "h": float(box.xywhn[0][3]),
                    "class": int(box.cls),
                    "confidence": float(box.conf),
                }
                for box in yolo_detections.boxes
            ]
        else:
            logger.warning("Invalid YOLO detections format")
            self.obstacles = []

    def get_statistics(self) -> Dict:
        """Get environment statistics"""
        return {
            "episodes_completed": self.episodes_completed,
            "total_reward": self.total_reward,
            "crashes_count": self.crashes_count,
            "average_reward_per_episode": self.total_reward / max(1, self.episodes_completed),
            "crash_rate": self.crashes_count / max(1, self.episodes_completed)
        }

    def render(self, mode='human'):
        """Render environment state (optional for debugging)"""
        if mode == 'human':
            print(f"Step: {self.step_count}, Position: {self.drone_position}, Obstacles: {len(self.obstacles)}")
            for i, obs in enumerate(self.obstacles):
                print(f"  Obstacle {i}: {obs}")

    def close(self):
        """Close environment and cleanup"""
        logger.info("Drone environment closed")

# Custom environment registration
gym.register(
    id='DroneObstacleEnv-v0',
    entry_point=DroneObstacleEnv,
    max_episode_steps=200,
)

if __name__ == "__main__":
    # Test environment
    env = DroneObstacleEnv()
    
    print("Testing Drone Environment...")
    obs, info = env.reset()
    print(f"Initial observation shape: {obs.shape}")
    print(f"Initial info: {info}")
    
    for step in range(10):
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        print(f"Step {step}: Action {action}, Reward {reward}, Terminated {terminated}")
        
        if terminated or truncated:
            break
    
    stats = env.get_statistics()
    print(f"Final statistics: {stats}")
    env.close()
