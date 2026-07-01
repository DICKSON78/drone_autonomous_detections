import math
import numpy as np

CIVE_BUILDINGS = [
    (20, 18), (35, 15), (10, 22), (-15, 12), (-30, 20),
    (40, -5), (25, -10), (5, -8), (-10, -15), (-35, -10),
    (15, 30), (-20, 28), (30, 5), (-5, 25), (45, 10),
]
CIVE_TREES = [
    (-20, -20), (-18, -18), (-15, -22), (-22, -15), (30, 20),
    (28, 22), (32, 18), (25, 25), (-30, -5), (-28, -8),
    (10, 15), (8, 18), (12, 12), (-5, 5), (5, -5),
]

MAX_SPEED = 3.0
WORLD_SIZE = 60.0
OBS_RADIUS = 2.0
GOAL_RADIUS = 2.0


class CIVENavEnv:
    metadata = {"render_modes": []}

    def __init__(self, max_steps: int = 500):
        self.max_steps = max_steps
        self.current_step = 0

        self.observation_space = type('Box', (), {
            'shape': (14,), 'dtype': np.float32,
            'low': -np.inf, 'high': np.inf,
        })()

        self.action_space = type('Box', (), {
            'shape': (3,), 'dtype': np.float32,
            'low': -MAX_SPEED, 'high': MAX_SPEED,
        })()

        self._buildings = np.array(CIVE_BUILDINGS, dtype=np.float32)
        self._trees = np.array(CIVE_TREES, dtype=np.float32)
        self._obstacle_pos = np.vstack([self._buildings, self._trees])

        self.drone_pos = np.zeros(3, dtype=np.float32)
        self.drone_vel = np.zeros(3, dtype=np.float32)
        self.target_pos = np.zeros(3, dtype=np.float32)
        self.prev_dist = 0.0

    def _reset_state(self):
        self.drone_pos = np.array([0.0, 0.0, 5.0], dtype=np.float32)
        self.drone_vel = np.zeros(3, dtype=np.float32)
        angle = np.random.uniform(0, 2 * math.pi)
        radius = np.random.uniform(10, 25)
        tx = radius * math.cos(angle)
        ty = radius * math.sin(angle)
        self.target_pos = np.array([tx, ty, np.random.uniform(5, 15)], dtype=np.float32)
        self.prev_dist = float(np.linalg.norm(self.drone_pos[:2] - self.target_pos[:2]))
        self.current_step = 0

    def _get_obs(self) -> np.ndarray:
        dx, dy, dz = self.target_pos - self.drone_pos
        dist_to_target = np.linalg.norm([dx, dy, dz])
        dir_x = dx / (dist_to_target + 1e-6)
        dir_y = dy / (dist_to_target + 1e-6)
        dir_z = dz / (dist_to_target + 1e-6)

        dists = np.linalg.norm(self._obstacle_pos - self.drone_pos[:2], axis=1)
        nearest_idx = np.argmin(dists)
        nearest_dist = dists[nearest_idx]
        nearest_bearing = np.arctan2(
            self._obstacle_pos[nearest_idx, 1] - self.drone_pos[1],
            self._obstacle_pos[nearest_idx, 0] - self.drone_pos[0],
        )
        drone_bearing = np.arctan2(self.drone_vel[1], self.drone_vel[0])

        return np.array([
            self.drone_pos[0] / WORLD_SIZE,
            self.drone_pos[1] / WORLD_SIZE,
            self.drone_pos[2] / 30.0,
            self.drone_vel[0] / MAX_SPEED,
            self.drone_vel[1] / MAX_SPEED,
            self.drone_vel[2] / MAX_SPEED,
            dir_x, dir_y, dir_z,
            nearest_dist / WORLD_SIZE,
            math.sin(nearest_bearing),
            math.cos(nearest_bearing),
            math.sin(drone_bearing),
            math.cos(drone_bearing),
        ], dtype=np.float32)

    def reset(self):
        self._reset_state()
        return self._get_obs(), {}

    def step(self, action):
        vx, vy, vz = np.clip(action, -MAX_SPEED, MAX_SPEED)
        self.drone_pos[0] += vx * 0.1
        self.drone_pos[1] += vy * 0.1
        self.drone_pos[2] += vz * 0.1
        self.drone_pos = np.clip(self.drone_pos,
                                 [-WORLD_SIZE/2, -WORLD_SIZE/2, 1.0],
                                 [WORLD_SIZE/2, WORLD_SIZE/2, 30.0])
        self.drone_vel = np.array([vx, vy, vz], dtype=np.float32)
        self.current_step += 1

        dist = np.linalg.norm(self.drone_pos[:2] - self.target_pos[:2])
        alt_diff = abs(self.drone_pos[2] - self.target_pos[2])
        dist_3d = np.linalg.norm(self.drone_pos - self.target_pos)

        reward = 0.0

        progress = self.prev_dist - dist
        reward += progress * 0.5

        for obs in self._obstacle_pos:
            d = np.linalg.norm(self.drone_pos[:2] - obs)
            if d < OBS_RADIUS:
                reward -= 5.0 * (OBS_RADIUS - d) / OBS_RADIUS
            if d < 1.0:
                reward -= 50.0
                return self._get_obs(), reward, True, False, {}

        if dist < GOAL_RADIUS and alt_diff < 2.0:
            reward += 20.0
            return self._get_obs(), reward, True, False, {}

        reward += max(0, 5.0 - dist_3d) * 0.1
        reward -= 0.05
        reward -= abs(vz) * 0.01

        done = self.current_step >= self.max_steps
        self.prev_dist = dist

        return self._get_obs(), reward, done, False, {}
