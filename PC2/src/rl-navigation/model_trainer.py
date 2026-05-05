# PPO model training for autonomous navigation
"""
Model trainer for RL agent
"""

import numpy as np
import torch
from typing import Dict, Any, List
import logging
from tqdm import tqdm

from .rl_agent import RLAgent
from .environment import NavigationEnvironment

logger = logging.getLogger(__name__)

class ModelTrainer:
    """Trainer for RL navigation model"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize trainer
        
        Args:
            config: Training configuration
        """
        self.config = config
        self.env = NavigationEnvironment(config)
        self.agent = RLAgent(
            state_dim=10,
            action_dim=4,
            config=config
        )
        
        self.num_episodes = config.get('num_episodes', 1000)
        self.save_frequency = config.get('save_frequency', 100)
        
        logger.info("Model trainer initialized")
    
    def train(self) -> List[float]:
        """
        Train the RL agent
        
        Returns:
            List of episode rewards
        """
        episode_rewards = []
        
        for episode in tqdm(range(self.num_episodes), desc="Training episodes"):
            state = self.env.reset()
            episode_reward = 0
            done = False
            
            while not done:
                # Get action
                action = self.agent.get_action(state, {}, eval_mode=False)
                
                # Take step
                next_state, reward, done, info = self.env.step(action)
                
                # Update agent
                self.agent.update(state, action, reward, next_state, done)
                
                episode_reward += reward
                state = next_state
            
            episode_rewards.append(episode_reward)
            
            # Log progress
            if (episode + 1) % 10 == 0:
                avg_reward = np.mean(episode_rewards[-10:])
                logger.info(f"Episode {episode + 1}, Avg Reward: {avg_reward:.2f}")
            
            # Save model
            if (episode + 1) % self.save_frequency == 0:
                self.agent.save_model()
        
        # Final save
        self.agent.save_model()
        
        return episode_rewards
    
    def evaluate(self, num_episodes: int = 10) -> float:
        """
        Evaluate trained agent
        
        Args:
            num_episodes: Number of evaluation episodes
            
        Returns:
            Average reward
        """
        total_rewards = []
        
        for episode in range(num_episodes):
            state = self.env.reset()
            episode_reward = 0
            done = False
            
            while not done:
                action = self.agent.get_action(state, {}, eval_mode=True)
                next_state, reward, done, _ = self.env.step(action)
                episode_reward += reward
                state = next_state
            
            total_rewards.append(episode_reward)
        
        avg_reward = np.mean(total_rewards)
        logger.info(f"Evaluation over {num_episodes} episodes: Avg Reward = {avg_reward:.2f}")
        
        return avg_reward