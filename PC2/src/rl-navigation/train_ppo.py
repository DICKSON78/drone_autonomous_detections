#!/usr/bin/env python3
"""
Train PPO navigation agent for drone obstacle avoidance.
Produces a model compatible with rl_handler.py's expected observation format.

Observation space (15-dim):
  [drone_x, drone_y, drone_z, target_x, target_y, target_z,
   obs1_cx, obs1_cy, obs1_dist,
   obs2_cx, obs2_cy, obs2_dist,
   obs3_cx, obs3_cy, obs3_dist]

Action space (6):
  0=forward, 1=backward, 2=left, 3=right, 4=up, 5=down
"""

import os
import sys
import gymnasium as gym
from gymnasium import spaces
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.env_checker import check_env

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "rl")
MODEL_PATH = os.path.join(OUTPUT_DIR, "navigation_agent")

class DroneNavEnv(gym.Env):
    """Gymnasium environment matching rl_handler.py observation format."""

    metadata = {"render_modes": ["human"]}

    def __init__(self, grid_size: int = 100, max_steps: int = 200):
        super().__init__()
        self.grid_size = grid_size
        self.max_steps = max_steps
        self.current_step = 0

        # Observation: 15 floats (drone 3D + target 3D + 3 obstacles × 3)
        self.observation_space = spaces.Box(low=0.0, high=1.0, shape=(15,), dtype=np.float32)

        # Action: 6 discrete (forward, backward, left, right, up, down)
        self.action_space = spaces.Discrete(6)

        self._reset_state()

    def _reset_state(self):
        self.drone_pos = np.array([0.5, 0.5, 0.1], dtype=np.float32)  # normalized 0-1
        self.target_pos = np.array([
            np.random.uniform(0.6, 0.95),
            np.random.uniform(0.6, 0.95),
            np.random.uniform(0.05, 0.3),
        ], dtype=np.float32)
        self.obstacles = []
        for _ in range(8):
            self.obstacles.append({
                "cx": np.random.uniform(0.1, 0.9),
                "cy": np.random.uniform(0.1, 0.9),
                "radius": np.random.uniform(0.03, 0.08),
            })
        self.current_step = 0

    def _get_obs(self):
        # Sort obstacles by distance, take nearest 3
        def dist(o):
            return np.hypot(self.drone_pos[0] - o["cx"], self.drone_pos[1] - o["cy"])

        sorted_obs = sorted(self.obstacles, key=dist)[:3]
        obs_features = []
        for o in sorted_obs:
            d = dist(o)
            obs_features.extend([o["cx"], o["cy"], min(d, 1.0)])

        # Pad to 9 if fewer than 3 obstacles
        while len(obs_features) < 9:
            obs_features.extend([0.5, 0.5, 1.0])

        return np.array(
            list(self.drone_pos) + list(self.target_pos) + obs_features,
            dtype=np.float32,
        )

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self._reset_state()
        return self._get_obs(), {}

    def step(self, action):
        step_size = 0.03
        moves = [
            [0.0, step_size, 0.0],   # 0: forward (+y)
            [0.0, -step_size, 0.0],  # 1: backward (-y)
            [-step_size, 0.0, 0.0],  # 2: left (-x)
            [step_size, 0.0, 0.0],   # 3: right (+x)
            [0.0, 0.0, step_size],   # 4: up (+z)
            [0.0, 0.0, -step_size],  # 5: down (-z)
        ]
        self.drone_pos += moves[action]
        self.drone_pos = np.clip(self.drone_pos, 0.0, 1.0)
        self.current_step += 1

        # Reward
        dist_to_target = np.linalg.norm(self.drone_pos - self.target_pos)
        reward = -dist_to_target  # closer = better

        # Obstacle collision penalty
        for o in self.obstacles:
            d = np.hypot(self.drone_pos[0] - o["cx"], self.drone_pos[1] - o["cy"])
            if d < o["radius"]:
                reward -= 5.0

        # Step penalty
        reward -= 0.01

        # Done conditions
        done = dist_to_target < 0.05 or self.current_step >= self.max_steps

        if done and dist_to_target < 0.05:
            reward += 50.0  # Goal reached bonus

        return self._get_obs(), reward, done, False, {}


def train(total_timesteps: int = 50_000, save: bool = True):
    print(f"[train] Creating environment...")
    env = DroneNavEnv()
    check_env(env, warn=True)

    print(f"[train] Training PPO agent for {total_timesteps} timesteps...")
    model = PPO(
        policy="MlpPolicy",
        env=env,
        learning_rate=3e-4,
        n_steps=512,
        batch_size=64,
        n_epochs=10,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=0.01,
        verbose=1,
        device="cpu",
    )

    model.learn(total_timesteps=total_timesteps, progress_bar=True)

    if save:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        model.save(MODEL_PATH)
        print(f"[train] Model saved to {MODEL_PATH}.zip")

    # Quick evaluation
    print(f"[train] Quick evaluation (10 episodes)...")
    eval_env = DroneNavEnv()
    wins = 0
    for ep in range(10):
        obs, _ = eval_env.reset()
        for _ in range(200):
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, done, truncated, _ = eval_env.step(action)
            if done or truncated:
                if reward > 0:
                    wins += 1
                break
    print(f"[train] Win rate: {wins}/10")


if __name__ == "__main__":
    timesteps = int(sys.argv[1]) if len(sys.argv) > 1 else 50_000
    train(total_timesteps=timesteps)
