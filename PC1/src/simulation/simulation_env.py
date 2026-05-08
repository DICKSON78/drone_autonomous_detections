# Simulation Environment for Guided Language Drone System (Simplified)
import numpy as np
import asyncio
import json
import logging
from typing import Dict, List, Tuple, Optional
import time
from kafka import KafkaProducer

class DroneSimulationEnvironment:
    """Simplified drone simulation environment"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.max_steps = 1000
        self.current_step = 0
        
        # Action space: [throttle, roll, pitch, yaw, camera_angle, emergency_stop]
        self.action_dim = 6
        
        # Observation space: position(3) + velocity(3) + orientation(3) + battery(1) + obstacles(2) + vision_features(10)
        self.observation_dim = 22
        
        # Initialize state
        self.state = self._reset_state()
        self.target_position = np.array([0.0, 0.0, 50.0])
        
        # Simulation parameters
        self.dt = 0.1  # 100ms timestep
        self.gravity = 9.81
        self.drone_mass = 1.0
        
        # Environment features
        self.weather_conditions = {
            'wind_speed': 0.0,
            'wind_direction': 0.0,
            'visibility': 1.0,
            'precipitation': 0.0
        }
        
        # Obstacles and objects
        self.obstacles = []
        self.objects = []
        self._generate_environment()
        
        logging.info("Drone simulation environment initialized")
    
    def _reset_state(self) -> np.ndarray:
        """Reset drone to initial state"""
        state = np.zeros(22)
        state[0:3] = [0.0, 0.0, 50.0]  # position [x, y, z]
        state[9] = 100.0  # battery percentage
        return state
    
    def _generate_environment(self):
        """Generate random obstacles and objects"""
        np.random.seed(int(time.time()))
        
        # Generate obstacles (buildings, trees)
        num_obstacles = np.random.randint(5, 15)
        self.obstacles = []
        for _ in range(num_obstacles):
            obstacle = {
                'position': np.random.uniform(-200, 200, 3),
                'size': np.random.uniform(10, 50, 3),
                'type': np.random.choice(['building', 'tree', 'pole'])
            }
            self.obstacles.append(obstacle)
        
        # Generate objects (people, cars, animals)
        num_objects = np.random.randint(3, 10)
        self.objects = []
        for _ in range(num_objects):
            obj = {
                'position': np.random.uniform(-150, 150, 3),
                'velocity': np.random.uniform(-5, 5, 3),
                'type': np.random.choice(['person', 'car', 'animal']),
                'detected': False
            }
            self.objects.append(obj)
    
    def reset(self, seed: Optional[int] = None, options: Optional[Dict] = None):
        """Reset environment for new episode"""
        super().reset(seed=seed)
        
        self.current_step = 0
        self.state = self._reset_state()
        self.target_position = np.array([
            np.random.uniform(-100, 100),
            np.random.uniform(-100, 100),
            np.random.uniform(30, 100)
        ])
        
        self._generate_environment()
        self._update_weather()
        
        return self.state, self._get_info()
    
    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """Execute one simulation step"""
        # Clip action to valid range
        action = np.clip(action, -1.0, 1.0)
        
        # Apply physics simulation
        self._apply_physics(action)
        
        # Update objects and obstacles
        self._update_objects()
        
        # Calculate reward
        reward = self._calculate_reward(action)
        
        # Check termination conditions
        terminated = self._is_terminated()
        truncated = self.current_step >= self.max_steps
        
        # Update observation with vision features
        self._update_vision_features()
        
        self.current_step += 1
        
        return self.state, reward, terminated, truncated, self._get_info()
    
    def _apply_physics(self, action: np.ndarray):
        """Apply physics simulation based on action"""
        # Extract actions
        throttle = action[0] * 20.0  # Vertical thrust
        roll = action[1] * 0.5        # Lateral tilt
        pitch = action[2] * 0.5       # Forward tilt
        yaw = action[3] * 0.3         # Rotation
        camera_angle = action[4] * 45.0  # Camera gimbal
        emergency_stop = action[5] > 0.5
        
        if emergency_stop:
            # Emergency hover
            self.state[3:6] *= 0.9  # Reduce velocity
        else:
            # Calculate forces
            thrust = throttle + self.drone_mass * self.gravity
            
            # Apply forces to acceleration
            ax = thrust * np.sin(pitch) * np.cos(yaw)
            ay = thrust * np.sin(pitch) * np.sin(yaw)
            az = (thrust * np.cos(pitch) - self.drone_mass * self.gravity) / self.drone_mass
            
            # Add wind effects
            wind_force = self._calculate_wind_force()
            ax += wind_force[0]
            ay += wind_force[1]
            az += wind_force[2]
            
            # Update velocity
            self.state[3] += ax * self.dt  # vx
            self.state[4] += ay * self.dt  # vy
            self.state[5] += az * self.dt  # vz
            
            # Update position
            self.state[0] += self.state[3] * self.dt  # x
            self.state[1] += self.state[4] * self.dt  # y
            self.state[2] += self.state[5] * self.dt  # z
            
            # Update orientation
            self.state[6] += roll * self.dt    # roll
            self.state[7] += pitch * self.dt   # pitch
            self.state[8] += yaw * self.dt     # yaw
        
        # Apply constraints
        self.state[2] = max(5.0, min(120.0, self.state[2]))  # altitude limits
        self.state[3:6] = np.clip(self.state[3:6], -20.0, 20.0)  # velocity limits
        
        # Battery consumption
        power_consumption = 0.01 * (1 + np.linalg.norm(action))
        self.state[9] = max(0.0, self.state[9] - power_consumption)
    
    def _calculate_wind_force(self) -> np.ndarray:
        """Calculate wind force on drone"""
        wind_speed = self.weather_conditions['wind_speed']
        wind_dir = self.weather_conditions['wind_direction']
        
        # Convert wind direction to force vector
        wind_force = np.array([
            wind_speed * np.cos(wind_dir),
            wind_speed * np.sin(wind_dir),
            0.0
        ]) * 0.1  # Scale factor
        
        # Add turbulence
        turbulence = np.random.normal(0, 0.5, 3)
        
        return wind_force + turbulence
    
    def _update_objects(self):
        """Update positions of dynamic objects"""
        for obj in self.objects:
            # Simple linear motion
            obj['position'] += obj['velocity'] * self.dt
            
            # Random direction changes
            if np.random.random() < 0.1:  # 10% chance per step
                obj['velocity'] = np.random.uniform(-5, 5, 3)
            
            # Keep objects in bounds
            obj['position'] = np.clip(obj['position'], -200, 200)
    
    def _update_vision_features(self):
        """Update vision-based observation features"""
        vision_features = np.zeros(10)
        
        # Simulate object detection
        for i, obj in enumerate(self.objects[:5]):  # Max 5 objects
            if i >= 5:
                break
                
            # Calculate distance to object
            distance = np.linalg.norm(self.state[0:3] - obj['position'])
            
            if distance < 100:  # Detection range
                # Object detected
                vision_features[i*2] = 1.0  # Detection flag
                vision_features[i*2 + 1] = 1.0 / (distance + 1.0)  # Proximity
        
        # Obstacle detection
        min_obstacle_dist = float('inf')
        for obstacle in self.obstacles:
            dist = np.linalg.norm(self.state[0:3] - obstacle['position'])
            min_obstacle_dist = min(min_obstacle_dist, dist)
        
        if min_obstacle_dist < 50:
            vision_features[8] = 1.0  # Obstacle detected
            vision_features[9] = 1.0 / (min_obstacle_dist + 1.0)
        
        # Update state with vision features
        self.state[12:22] = vision_features
    
    def _calculate_reward(self, action: np.ndarray) -> float:
        """Calculate reward for current state and action"""
        reward = 0.0
        
        # Distance to target reward
        distance_to_target = np.linalg.norm(self.state[0:3] - self.target_position)
        reward -= 0.1 * distance_to_target
        
        # Target reached bonus
        if distance_to_target < 10.0:
            reward += 100.0
        
        # Altitude reward
        if 20 <= self.state[2] <= 100:
            reward += 0.5
        elif self.state[2] < 10:
            reward -= 2.0
        
        # Speed penalty
        speed = np.linalg.norm(self.state[3:6])
        if speed > 15:
            reward -= 0.5
        
        # Collision penalty
        collision_risk = self._check_collision_risk()
        if collision_risk > 0.8:
            reward -= 10.0
        
        # Battery penalty
        if self.state[9] < 20:
            reward -= 1.0
        
        # Object detection bonus
        detected_objects = sum(1 for obj in self.objects if obj.get('detected', False))
        reward += detected_objects * 5.0
        
        # Action smoothness reward
        action_penalty = np.linalg.norm(action)
        reward -= 0.01 * action_penalty
        
        return reward
    
    def _check_collision_risk(self) -> float:
        """Check collision risk with obstacles"""
        max_risk = 0.0
        
        for obstacle in self.obstacles:
            distance = np.linalg.norm(self.state[0:3] - obstacle['position'])
            obstacle_radius = np.linalg.norm(obstacle['size']) / 2
            
            if distance < obstacle_radius + 10:  # Safety margin
                risk = 1.0 - (distance / (obstacle_radius + 10))
                max_risk = max(max_risk, risk)
        
        return max_risk
    
    def _is_terminated(self) -> bool:
        """Check if episode should terminate"""
        # Crashed
        if self.state[2] <= 0:
            return True
        
        # Battery depleted
        if self.state[9] <= 0:
            return True
        
        # Collision
        if self._check_collision_risk() > 0.95:
            return True
        
        # Target reached
        if np.linalg.norm(self.state[0:3] - self.target_position) < 5.0:
            return True
        
        return False
    
    def _update_weather(self):
        """Update weather conditions"""
        # Random weather changes
        if np.random.random() < 0.1:  # 10% chance per episode
            self.weather_conditions['wind_speed'] = np.random.uniform(0, 10)
            self.weather_conditions['wind_direction'] = np.random.uniform(0, 2*np.pi)
            self.weather_conditions['visibility'] = np.random.uniform(0.5, 1.0)
    
    def _get_info(self) -> Dict:
        """Get additional environment information"""
        return {
            'step': self.current_step,
            'target_position': self.target_position.tolist(),
            'distance_to_target': np.linalg.norm(self.state[0:3] - self.target_position),
            'battery': self.state[9],
            'altitude': self.state[2],
            'collision_risk': self._check_collision_risk(),
            'detected_objects': sum(1 for obj in self.objects if obj.get('detected', False)),
            'weather': self.weather_conditions
        }
    
    def get_drone_state(self) -> Dict:
        """Get current drone state in dictionary format"""
        return {
            'position': {
                'x': float(self.state[0]),
                'y': float(self.state[1]),
                'altitude': float(self.state[2])
            },
            'velocity': {
                'x': float(self.state[3]),
                'y': float(self.state[4]),
                'z': float(self.state[5])
            },
            'orientation': {
                'roll': float(self.state[6]),
                'pitch': float(self.state[7]),
                'yaw': float(self.state[8])
            },
            'battery': float(self.state[9]),
            'obstacle_ahead': float(self.state[10]),
            'obstacle_below': float(self.state[11]),
            'vision_features': self.state[12:22].tolist()
        }
    
    def set_target_position(self, position: np.ndarray):
        """Set new target position"""
        self.target_position = position
    
    def add_command_objective(self, objective: Dict):
        """Add command-specific objective"""
        if objective.get('search_objects'):
            # Mark objects as search targets
            for obj in self.objects:
                if obj['type'] in objective['search_objects']:
                    obj['is_target'] = True
        
        if objective.get('target_gps'):
            # Set target position from GPS
            self.target_position = np.array([
                objective['target_gps']['lat'],
                objective['target_gps']['lon'],
                objective.get('altitude', 50.0)
            ])

class SimulationManager:
    """Manages simulation environment and integration with drone system"""
    
    def __init__(self, kafka_producer: KafkaProducer = None):
        self.env = DroneSimulationEnvironment()
        self.kafka_producer = kafka_producer
        self.is_running = False
        self.current_episode = 0
        
        logging.info("Simulation manager initialized")
    
    async def run_simulation(self, command_context: Dict = None):
        """Run simulation episode"""
        self.is_running = True
        
        # Reset environment
        state, info = self.env.reset()
        
        # Apply command context
        if command_context:
            self.env.add_command_objective(command_context)
        
        logging.info(f"Starting simulation episode {self.current_episode}")
        
        try:
            while self.is_running:
                # Get current drone state
                drone_state = self.env.get_drone_state()
                
                # Send state to Kafka
                if self.kafka_producer:
                    state_message = {
                        'timestamp': time.time(),
                        'episode': self.current_episode,
                        'state': drone_state,
                        'info': info,
                        'context': command_context
                    }
                    
                    self.kafka_producer.send('drone.simulation.state', state_message)
                    self.kafka_producer.flush()
                
                # Wait for action (in real system, from RL controller)
                await asyncio.sleep(0.1)
                
                # Simulate step (would get action from controller)
                action = np.random.uniform(-0.1, 0.1, 6)  # Random small actions
                
                # Step simulation
                state, reward, terminated, truncated, info = self.env.step(action)
                
                # Send step results
                if self.kafka_producer:
                    step_message = {
                        'timestamp': time.time(),
                        'episode': self.current_episode,
                        'action': action.tolist(),
                        'reward': float(reward),
                        'terminated': terminated,
                        'truncated': truncated,
                        'info': info
                    }
                    
                    self.kafka_producer.send('drone.simulation.step', step_message)
                    self.kafka_producer.flush()
                
                if terminated or truncated:
                    logging.info(f"Episode {self.current_episode} finished: {info}")
                    self.current_episode += 1
                    break
        
        except Exception as e:
            logging.error(f"Simulation error: {e}")
        
        finally:
            self.is_running = False
    
    def stop_simulation(self):
        """Stop current simulation"""
        self.is_running = False
        logging.info("Simulation stopped")
    
    def get_environment_stats(self) -> Dict:
        """Get simulation environment statistics"""
        return {
            'current_episode': self.current_episode,
            'is_running': self.is_running,
            'obstacles_count': len(self.env.obstacles),
            'objects_count': len(self.env.objects),
            'weather': self.env.weather_conditions
        }

# Global simulation manager
simulation_manager = None

def initialize_simulation(kafka_producer: KafkaProducer = None):
    """Initialize global simulation manager"""
    global simulation_manager
    simulation_manager = SimulationManager(kafka_producer=kafka_producer)
    return simulation_manager
