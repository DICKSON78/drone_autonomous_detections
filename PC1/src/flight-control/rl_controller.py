# Reinforcement Learning Controller for Autonomous Drone Flight (Simplified)
import numpy as np
import logging
from typing import Dict, List, Tuple, Optional
import asyncio
from kafka import KafkaProducer
import json

class DroneEnvironment:
    """Simulation environment for RL training and inference"""
    
    def __init__(self):
        self.state_dim = 12  # position (3), velocity (3), orientation (3), battery (1), obstacles (2)
        self.action_dim = 6   # throttle, roll, pitch, yaw, camera_angle, emergency_stop
        self.max_altitude = 120.0
        self.min_altitude = 5.0
        self.max_speed = 20.0
        self.reset_environment()
    
    def reset_environment(self):
        """Reset environment to initial state"""
        self.current_state = np.zeros(self.state_dim)
        self.current_state[2] = 50.0  # Initial altitude
        self.current_state[9] = 100.0  # Full battery
        self.target_position = np.array([0.0, 0.0, 50.0])
        self.obstacles = []
        self.time_step = 0
        self.episode_reward = 0.0
        return self.current_state
    
    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, Dict]:
        """Execute action and return new state, reward, done, info"""
        # Apply action constraints
        action = np.clip(action, -1.0, 1.0)
        
        # Update state based on action
        self._apply_physics(action)
        
        # Calculate reward
        reward = self._calculate_reward(action)
        
        # Check if episode is done
        done = self._is_done()
        
        # Additional info
        info = {
            'distance_to_target': np.linalg.norm(self.current_state[:3] - self.target_position),
            'battery': self.current_state[9],
            'altitude': self.current_state[2],
            'collision_risk': self._check_collision_risk()
        }
        
        self.time_step += 1
        self.episode_reward += reward
        
        return self.current_state, reward, done, info
    
    def _apply_physics(self, action: np.ndarray):
        """Apply physics simulation based on action"""
        dt = 0.1  # Time step
        
        # Extract actions
        throttle = action[0] * 10.0  # Throttle affects vertical speed
        roll = action[1] * 0.5      # Roll affects lateral movement
        pitch = action[2] * 0.5     # Pitch affects forward movement
        yaw = action[3] * 0.3       # Yaw affects rotation
        camera_angle = action[4] * 45.0  # Camera angle
        emergency_stop = action[5] > 0.5
        
        if emergency_stop:
            # Emergency stop - hover in place
            self.current_state[3:6] *= 0.9  # Reduce velocity
        else:
            # Update velocities
            self.current_state[3] += pitch * dt  # Forward velocity
            self.current_state[4] += roll * dt    # Lateral velocity
            self.current_state[5] += throttle * dt  # Vertical velocity
            
            # Update position
            self.current_state[:3] += self.current_state[3:6] * dt
            
            # Update orientation
            self.current_state[6:9] += np.array([roll, pitch, yaw]) * dt
        
        # Apply constraints
        self.current_state[2] = np.clip(self.current_state[2], self.min_altitude, self.max_altitude)
        self.current_state[3:6] = np.clip(self.current_state[3:6], -self.max_speed, self.max_speed)
        
        # Battery consumption
        self.current_state[9] -= 0.01 * dt * (1 + np.linalg.norm(action))
        self.current_state[9] = max(0, self.current_state[9])
    
    def _calculate_reward(self, action: np.ndarray) -> float:
        """Calculate reward based on current state and action"""
        reward = 0.0
        
        # Distance reward (closer to target is better)
        distance = np.linalg.norm(self.current_state[:3] - self.target_position)
        reward += -0.1 * distance
        
        # Altitude reward (maintain safe altitude)
        if 20 <= self.current_state[2] <= 100:
            reward += 0.5
        else:
            reward -= 1.0
        
        # Speed penalty (too fast is dangerous)
        speed = np.linalg.norm(self.current_state[3:6])
        if speed > 15:
            reward -= 0.5
        
        # Battery penalty
        if self.current_state[9] < 20:
            reward -= 2.0
        
        # Collision avoidance reward
        collision_risk = self._check_collision_risk()
        if collision_risk > 0.8:
            reward -= 5.0
        elif collision_risk < 0.2:
            reward += 0.2
        
        # Emergency stop penalty (use only when necessary)
        if action[5] > 0.5 and collision_risk < 0.5:
            reward -= 1.0
        
        return reward
    
    def _check_collision_risk(self) -> float:
        """Check collision risk based on obstacles and altitude"""
        # Simple collision risk based on altitude
        if self.current_state[2] < 10:
            return 0.9
        elif self.current_state[2] < 20:
            return 0.5
        else:
            return 0.1
    
    def _is_done(self) -> bool:
        """Check if episode is complete"""
        # Done if reached target
        distance = np.linalg.norm(self.current_state[:3] - self.target_position)
        if distance < 5.0:
            return True
        
        # Done if battery depleted
        if self.current_state[9] <= 0:
            return True
        
        # Done if crashed
        if self.current_state[2] <= 0:
            return True
        
        # Done if time limit exceeded
        if self.time_step > 1000:
            return True
        
        return False

class DQNNetwork:
    """Mock Deep Q-Network for drone control"""
    
    def __init__(self, state_dim: int, action_dim: int):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.model = "mock_dqn_model"
    
    def forward(self, x):
        # Mock forward pass - return random actions
        return np.random.uniform(-1, 1, (1, self.action_dim))

class RLDroneController:
    """Reinforcement Learning controller for autonomous drone flight"""
    
    def __init__(self, model_path: str = None, kafka_producer: KafkaProducer = None):
        self.state_dim = 12
        self.action_dim = 6
        self.device = "cpu"
        
        # Initialize mock networks
        self.q_network = DQNNetwork(self.state_dim, self.action_dim)
        self.target_network = DQNNetwork(self.state_dim, self.action_dim)
        
        # Load model if available
        if model_path:
            logging.info(f"Mock RL model path: {model_path}")
        
        # Training parameters
        self.epsilon = 0.1  # Exploration rate
        self.gamma = 0.99   # Discount factor
        self.learning_rate = 0.001
        
        # Experience replay
        self.memory = []  # Simplified memory
        
        # Environment
        self.env = DroneEnvironment()
        
        # Kafka producer
        self.kafka_producer = kafka_producer
        
        # Training mode
        self.training_mode = False
        
        logging.info("Mock RL Controller initialized")
    
    def select_action(self, state: np.ndarray, training: bool = False) -> np.ndarray:
        """Select action using epsilon-greedy policy"""
        import random
        
        if training and random.random() < self.epsilon:
            # Random exploration
            return np.random.uniform(-1, 1, self.action_dim)
        
        # Mock greedy action
        q_values = self.q_network.forward(state)
        action_index = np.argmax(q_values[0])
        
        # Convert index to continuous action
        action = np.zeros(self.action_dim)
        action[action_index] = 1.0
        
        return action
    
    def train_step(self, batch_size: int = 32) -> float:
        """Mock training step"""
        if len(self.memory) < batch_size:
            return 0.0
        
        # Mock training - return random loss
        import random
        return random.uniform(0.01, 0.1)
    
    def update_target_network(self):
        """Mock update target network"""
        logging.info("Mock target network updated")
    
    def save_model(self, path: str):
        """Mock save model"""
        logging.info(f"Mock model saved to {path}")
    
    def autonomous_flight_control(self, current_state: Dict, command_context: Dict) -> Dict:
        """Generate autonomous flight commands using RL"""
        # Convert current state to numpy array
        state_vector = self._dict_to_state_vector(current_state)
        
        # Select action
        action = self.select_action(state_vector, training=self.training_mode)
        
        # Convert action to flight commands
        flight_commands = self._action_to_flight_commands(action)
        
        # Add context-specific adjustments
        flight_commands = self._adjust_for_context(flight_commands, command_context)
        
        # Send commands to Kafka
        if self.kafka_producer:
            command_data = {
                'timestamp': asyncio.get_event_loop().time(),
                'state': current_state,
                'action': action.tolist(),
                'flight_commands': flight_commands,
                'context': command_context,
                'controller': 'rl'
            }
            
            try:
                self.kafka_producer.send('drone.commands.autonomous', command_data)
                self.kafka_producer.flush()
            except Exception as e:
                logging.error(f"Failed to send RL commands to Kafka: {e}")
        
        return flight_commands
    
    def _dict_to_state_vector(self, state_dict: Dict) -> np.ndarray:
        """Convert state dictionary to numpy array"""
        state_vector = np.zeros(self.state_dim)
        
        # Position
        state_vector[0] = state_dict.get('position', {}).get('lat', 0.0)
        state_vector[1] = state_dict.get('position', {}).get('lon', 0.0)
        state_vector[2] = state_dict.get('position', {}).get('altitude', 50.0)
        
        # Velocity
        state_vector[3] = state_dict.get('velocity', {}).get('x', 0.0)
        state_vector[4] = state_dict.get('velocity', {}).get('y', 0.0)
        state_vector[5] = state_dict.get('velocity', {}).get('z', 0.0)
        
        # Orientation
        state_vector[6] = state_dict.get('orientation', {}).get('roll', 0.0)
        state_vector[7] = state_dict.get('orientation', {}).get('pitch', 0.0)
        state_vector[8] = state_dict.get('orientation', {}).get('yaw', 0.0)
        
        # Battery
        state_vector[9] = state_dict.get('battery', 100.0)
        
        # Obstacles (simplified)
        state_vector[10] = state_dict.get('obstacle_ahead', 0.0)
        state_vector[11] = state_dict.get('obstacle_below', 0.0)
        
        return state_vector
    
    def _action_to_flight_commands(self, action: np.ndarray) -> Dict:
        """Convert RL action to flight commands"""
        return {
            'throttle': float(action[0]),
            'roll': float(action[1]),
            'pitch': float(action[2]),
            'yaw': float(action[3]),
            'camera_angle': float(action[4]),
            'emergency_stop': bool(action[5] > 0.5),
            'confidence': 0.8
        }
    
    def _adjust_for_context(self, commands: Dict, context: Dict) -> Dict:
        """Adjust commands based on command context"""
        intent = context.get('intent', 'navigate')
        
        if intent == 'emergency_land':
            commands['throttle'] = -0.5
            commands['emergency_stop'] = False
        elif intent == 'hover':
            commands['throttle'] = 0.0
            commands['roll'] = 0.0
            commands['pitch'] = 0.0
            commands['yaw'] = 0.0
        elif intent == 'surveillance':
            commands['camera_angle'] = -45.0  # Look down
            commands['speed'] = 5.0
        
        return commands

# Global RL controller instance
rl_controller = None

def initialize_rl_controller(model_path: str = None, kafka_producer: KafkaProducer = None):
    """Initialize global RL controller"""
    global rl_controller
    rl_controller = RLDroneController(model_path=model_path, kafka_producer=kafka_producer)
    return rl_controller
