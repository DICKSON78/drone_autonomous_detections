import os
import math
import numpy as np
import torch
from stable_baselines3 import PPO
import logging

logger = logging.getLogger(__name__)

class RLHandler:
    """
    Handles navigation decisions using the PPO agent trained in the Colab notebook.
    Based on the user's provided RL training code.
    """
    
    def __init__(self, model_path: str = "/app/models/rl/navigation_agent"):
        self.model_path = model_path
        self.model = None
        self.load_model()

    def load_model(self):
        """Load trained SB3 PPO model"""
        try:
            # Check for .zip file
            path = self.model_path
            if not path.endswith('.zip') and os.path.exists(path + '.zip'):
                path = path + '.zip'
                
            if os.path.exists(path):
                self.model = PPO.load(self.model_path)
                logger.info(f"RL Navigation agent loaded from {self.model_path}")
            else:
                logger.warning(f"RL model not found at {self.model_path}. Using fallback decisions.")
        except Exception as e:
            logger.error(f"Error loading RL model: {e}")

    def get_action(self, drone_pos, target_pos, obstacles):
        """
        Get navigation action from the trained RL agent.
        Matches the observation space: [drone_x, drone_y, drone_z, target_x, target_y, target_z, obs1, obs2, obs3]
        """
        ACTION_NAMES = {
            0: "forward", 1: "backward", 2: "left",
            3: "right",   4: "up",       5: "down"
        }

        if self.model is None:
            return "hover", 0.5

        try:
            # Build observation vector (must match user's DroneNavEnv._get_obs format)
            # Normalised 0-1. Drone and target are already normalized in the request.
            
            obs_features = []
            # Sort obstacles by distance to drone
            def get_dist(o):
                center = o.get("center", [320, 240])
                cx, cy = center[0] / 640.0, center[1] / 480.0
                return math.hypot(drone_pos[0] - cx, drone_pos[1] - cy)

            sorted_obs = sorted(obstacles, key=get_dist)[:3]

            for o in sorted_obs:
                center = o.get("center", [320, 240])
                cx, cy = center[0] / 640.0, center[1] / 480.0
                dist = get_dist(o)
                obs_features.extend([cx, cy, min(dist, 1.0)])

            # Pad to 9 values if fewer than 3 obstacles
            while len(obs_features) < 9:
                obs_features.extend([0.5, 0.5, 1.0])

            observation = np.array(
                list(drone_pos) + list(target_pos) + obs_features,
                dtype=np.float32,
            )

            action, _ = self.model.predict(observation, deterministic=True)
            action = int(action)
            return ACTION_NAMES[action], 0.9
            
        except Exception as e:
            logger.error(f"RL inference error: {e}")
            return "hover", 0.0

    @property
    def is_ready(self):
        return self.model is not None
