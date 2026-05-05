# Custom gym environment for drone navigation training
 

import numpy as np
import random
from typing import Tuple, Dict, List

class NavigationEnvironment:
    """Custom Gym-like environment for drone navigation"""
    
    def __init__(self, grid_size: int = 100):
        self.grid_size = grid_size
        self.max_steps = 500
        self.current_step = 0
        self.drone_position = np.array([50.0, 50.0, 10.0])
        self.target_position = None
        self.obstacles = self._generate_obstacles()
        
    def _generate_obstacles(self):
        obstacles = []
        for _ in range(15):
            obstacles.append({
                'position': [random.randint(10, 90), random.randint(10, 90)],
                'radius': random.uniform(2, 6)
            })
        return obstacles

    def reset(self, target: List[float] = None):
        self.drone_position = np.array([50.0, 50.0, 10.0])
        self.target_position = np.array(target) if target else np.array([80.0, 80.0])
        self.current_step = 0
        return self._get_state()

    def step(self, action: int):
        # Actions: 0=North, 1=South, 2=West, 3=East, 4=Hover, 5=Emergency
        moves = [(0,1), (0,-1), (-1,0), (1,0), (0,0), (0,0)]
        dx, dy = moves[action]
        self.drone_position[0] += dx * 2
        self.drone_position[1] += dy * 2
        
        self.drone_position[0] = np.clip(self.drone_position[0], 0, self.grid_size)
        self.drone_position[1] = np.clip(self.drone_position[1], 0, self.grid_size)
        
        self.current_step += 1
        
        reward = self._calculate_reward()
        done = self._is_done()
        
        return self._get_state(), reward, done, {}

    def _get_state(self):
        state = [
            self.drone_position[0] / self.grid_size,
            self.drone_position[1] / self.grid_size,
            self.target_position[0] / self.grid_size,
            self.target_position[1] / self.grid_size,
            np.linalg.norm(self.drone_position[:2] - self.target_position) / self.grid_size
        ]
        
        # Add distances to nearest 5 obstacles
        for obs in sorted(self.obstacles, key=lambda o: np.linalg.norm(self.drone_position[:2] - o['position']))[:5]:
            dist = np.linalg.norm(self.drone_position[:2] - obs['position'])
            state.append(min(dist / 30.0, 1.0))
        
        while len(state) < 14:
            state.append(0.0)
            
        return np.array(state, dtype=np.float32)

    def _calculate_reward(self):
        distance = np.linalg.norm(self.drone_position[:2] - self.target_position)
        reward = -distance * 0.1
        
        if distance < 3.0:
            reward += 100.0
        if distance < 1.5:
            reward += 50.0
            
        # Obstacle penalty
        for obs in self.obstacles:
            if np.linalg.norm(self.drone_position[:2] - obs['position']) < obs['radius'] + 2:
                reward -= 40.0
                
        reward -= 0.1  # Step penalty
        return reward

    def _is_done(self):
        distance = np.linalg.norm(self.drone_position[:2] - self.target_position)
        return distance < 2.0 or self.current_step >= self.max_steps