import os
import math
import numpy as np
import logging

logger = logging.getLogger(__name__)

class RLHandler:
    """
    Handles navigation decisions using the PPO agent trained in the Colab notebook.
    Falls back to rule-based obstacle avoidance when no model is available.
    """
    
    def __init__(self, model_path: str = "/app/models/rl/navigation_agent"):
        self.model_path = model_path
        self.model = None
        self._load_model()

    def _load_model(self):
        """Load trained SB3 PPO model if available."""
        try:
            path = self.model_path
            if not path.endswith('.zip') and os.path.exists(path + '.zip'):
                path = path + '.zip'
            if os.path.exists(path):
                from stable_baselines3 import PPO
                self.model = PPO.load(path)
                logger.info(f"RL Navigation agent loaded from {path}")
            else:
                logger.warning(f"RL model not found at {self.model_path}. Using rule-based fallback.")
        except ImportError:
            logger.warning("stable_baselines3 not installed. Using rule-based fallback.")
        except Exception as e:
            logger.error(f"Error loading RL model: {e}")

    def get_action(self, drone_pos, target_pos, obstacles):
        """
        Get navigation action. Uses PPO if model loaded, otherwise rule-based avoidance.
        drone_pos, target_pos: normalized [x, y, z] in 0-1 range
        obstacles: list of dicts with 'center' [px_x, px_y] in 640x480 frame
        """
        ACTION_NAMES = {
            0: "forward", 1: "backward", 2: "left",
            3: "right",   4: "up",       5: "down"
        }

        # Try PPO first
        if self.model is not None:
            try:
                obs_features = self._build_obs(drone_pos, target_pos, obstacles)
                action, _ = self.model.predict(obs_features, deterministic=True)
                return ACTION_NAMES[int(action)], 0.9
            except Exception as e:
                logger.error(f"RL inference error: {e}")

        # Fallback: rule-based obstacle avoidance
        return self._rule_based_action(drone_pos, target_pos, obstacles)

    def _build_obs(self, drone_pos, target_pos, obstacles):
        """Build 15-dim observation vector matching training env."""
        def get_dist(o):
            center = o.get("center", [320, 240])
            cx, cy = center[0] / 640.0, center[1] / 480.0
            return math.hypot(drone_pos[0] - cx, drone_pos[1] - cy)

        sorted_obs = sorted(obstacles, key=get_dist)[:3]
        obs_features = []
        for o in sorted_obs:
            center = o.get("center", [320, 240])
            cx, cy = center[0] / 640.0, center[1] / 480.0
            d = get_dist(o)
            obs_features.extend([cx, cy, min(d, 1.0)])
        while len(obs_features) < 9:
            obs_features.extend([0.5, 0.5, 1.0])
        return np.array(list(drone_pos) + list(target_pos) + obs_features, dtype=np.float32)

    def _rule_based_action(self, drone_pos, target_pos, obstacles):
        """
        Simple rule-based obstacle avoidance.
        - Compute direction to target
        - If nearest obstacle is within safety margin and in path, go around it
        - Otherwise move toward target
        """
        # Direction to target (normalized)
        dx = target_pos[0] - drone_pos[0]
        dy = target_pos[1] - drone_pos[1]
        dz = target_pos[2] - drone_pos[2]
        dist_to_target = math.hypot(dx, dy, dz)

        if dist_to_target < 0.02:
            return "hover", 0.5

        # Normalize direction
        if dist_to_target > 0:
            dx /= dist_to_target
            dy /= dist_to_target
            dz /= dist_to_target

        # Check nearest obstacle
        SAFETY_MARGIN = 0.08  # normalized units
        nearest_obs = None
        nearest_dist = float('inf')

        for o in obstacles:
            center = o.get("center", [320, 240])
            cx, cy = center[0] / 640.0, center[1] / 480.0
            d = math.hypot(drone_pos[0] - cx, drone_pos[1] - cy)
            if d < nearest_dist:
                nearest_dist = d
                nearest_obs = (cx, cy, d)

        # If obstacle is close and in the path, avoid it
        if nearest_obs and nearest_dist < SAFETY_MARGIN:
            ox, oy, od = nearest_obs
            # Vector from obstacle to drone (push away)
            avoid_x = drone_pos[0] - ox
            avoid_y = drone_pos[1] - oy

            if abs(avoid_x) > abs(avoid_y):
                return "left" if avoid_x < 0 else "right", 0.7
            else:
                return "backward" if avoid_y < 0 else "forward", 0.7

        # Move toward target
        if abs(dz) > 0.15:
            return "up" if dz > 0 else "down", 0.6
        if abs(dy) > abs(dx):
            return "forward" if dy > 0 else "backward", 0.6
        return "right" if dx > 0 else "left", 0.6

    @property
    def is_ready(self):
        return self.model is not None
