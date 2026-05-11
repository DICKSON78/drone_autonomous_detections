#!/usr/bin/env python3
"""
Reinforcement Learning Training Script for Drone Navigation
Kufundisha RL agent kwa ajili ya drone obstacle avoidance
"""

import os
import logging
import numpy as np
from typing import Dict, Any
from stable_baselines3 import PPO, A2C, DQN
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.callbacks import EvalCallback, CheckpointCallback, BaseCallback
from stable_baselines3.common.monitor import Monitor
import torch
import gymnasium as gym
from drone_env import DroneObstacleEnv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TrainingCallback(BaseCallback):
    """Custom callback for training progress monitoring"""
    
    def __init__(self, verbose: int = 1):
        super().__init__(verbose)
        self.episode_rewards = []
        self.episode_lengths = []
        self.crash_rates = []
    
    def _on_step(self) -> bool:
        # Called after each step
        return True
    
    def _on_rollout_end(self) -> None:
        # Called at the end of each rollout
        if hasattr(self.training_env, 'get_attr'):
            try:
                # Get statistics from all environments
                stats_list = self.training_env.get_attr('get_statistics')()
                if stats_list:
                    avg_stats = {}
                    for key in stats_list[0].keys():
                        avg_stats[key] = np.mean([s[key] for s in stats_list])
                    
                    if self.verbose > 0:
                        logger.info(f"Rollout stats: {avg_stats}")
            except Exception as e:
                logger.warning(f"Could not get rollout stats: {e}")

class DroneRLTrainer:
    """Trainer class for drone reinforcement learning"""
    
    def __init__(self, config: Dict = None):
        self.config = config or self._default_config()
        self.env = None
        self.eval_env = None
        self.model = None
        self.setup_directories()
    
    def _default_config(self) -> Dict:
        """Default training configuration"""
        return {
            "model_type": "PPO",  # PPO, A2C, or DQN
            "total_timesteps": 500_000,
            "n_envs": 4,
            "eval_freq": 10_000,
            "save_freq": 20_000,
            "model_params": {
                "learning_rate": 3e-4,
                "n_steps": 2048,
                "batch_size": 64,
                "n_epochs": 10,
                "gamma": 0.99,
                "gae_lambda": 0.95,
                "clip_range": 0.2,
                "ent_coef": 0.01,
            },
            "env_params": {
                "max_obstacles": 10,
                "max_steps": 200,
                "collision_threshold": 0.1,
                "obstacle_speed": 0.02,
            }
        }
    
    def setup_directories(self):
        """Create necessary directories"""
        dirs = ["models", "logs", "logs/tensorboard", "logs/evaluations"]
        for dir_path in dirs:
            os.makedirs(dir_path, exist_ok=True)
            logger.info(f"Created directory: {dir_path}")
    
    def create_environments(self):
        """Create training and evaluation environments"""
        logger.info("Creating training and evaluation environments...")
        
        # Training environments (vectorized for efficiency)
        self.env = make_vec_env(
            DroneObstacleEnv,
            n_envs=self.config["n_envs"],
            env_kwargs=self.config["env_params"],
            seed=42
        )
        
        # Evaluation environment (single environment)
        self.eval_env = make_vec_env(
            DroneObstacleEnv,
            n_envs=1,
            env_kwargs=self.config["env_params"],
            seed=123
        )
        
        logger.info(f"Created {self.config['n_envs']} training environments and 1 evaluation environment")
    
    def create_model(self):
        """Create RL model based on configuration"""
        model_type = self.config["model_type"]
        params = self.config["model_params"]
        
        logger.info(f"Creating {model_type} model...")
        
        if model_type == "PPO":
            self.model = PPO(
                "MlpPolicy",
                self.env,
                verbose=1,
                tensorboard_log="logs/tensorboard",
                **params
            )
        elif model_type == "A2C":
            self.model = A2C(
                "MlpPolicy", 
                self.env,
                verbose=1,
                tensorboard_log="logs/tensorboard",
                **params
            )
        elif model_type == "DQN":
            self.model = DQN(
                "MlpPolicy",
                self.env,
                verbose=1,
                tensorboard_log="logs/tensorboard",
                **params
            )
        else:
            raise ValueError(f"Unsupported model type: {model_type}")
        
        logger.info(f"{model_type} model created successfully")
    
    def create_callbacks(self):
        """Create training callbacks"""
        callbacks = []
        
        # Evaluation callback
        eval_callback = EvalCallback(
            self.eval_env,
            best_model_save_path="models/",
            log_path="logs/evaluations/",
            eval_freq=self.config["eval_freq"],
            deterministic=True,
            render=False,
            verbose=1
        )
        callbacks.append(eval_callback)
        
        # Checkpoint callback
        checkpoint_callback = CheckpointCallback(
            save_freq=self.config["save_freq"],
            save_path="models/checkpoints/",
            name_prefix=f"drone_{self.config['model_type'].lower()}"
        )
        callbacks.append(checkpoint_callback)
        
        # Custom training callback
        training_callback = TrainingCallback(verbose=1)
        callbacks.append(training_callback)
        
        return callbacks
    
    def train(self):
        """Train the RL model"""
        logger.info("🚁 Starting RL training...")
        
        # Create environments
        self.create_environments()
        
        # Create model
        self.create_model()
        
        # Create callbacks
        callbacks = self.create_callbacks()
        
        # Start training
        try:
            self.model.learn(
                total_timesteps=self.config["total_timesteps"],
                callback=callbacks,
                progress_bar=True
            )
            
            # Save final model
            model_path = f"models/drone_{self.config['model_type'].lower()}_final"
            self.model.save(model_path)
            
            logger.info(f"✅ Training completed! Model saved to: {model_path}")
            return model_path
            
        except KeyboardInterrupt:
            logger.info("Training interrupted by user")
            return None
        except Exception as e:
            logger.error(f"Training failed: {e}")
            return None
        finally:
            self.cleanup()
    
    def evaluate_model(self, model_path: str, n_episodes: int = 100):
        """Evaluate trained model"""
        logger.info(f"Evaluating model: {model_path}")
        
        # Load model
        if self.config["model_type"] == "PPO":
            model = PPO.load(model_path)
        elif self.config["model_type"] == "A2C":
            model = A2C.load(model_path)
        elif self.config["model_type"] == "DQN":
            model = DQN.load(model_path)
        else:
            raise ValueError(f"Unsupported model type: {self.config['model_type']}")
        
        # Create evaluation environment
        eval_env = DroneObstacleEnv(self.config["env_params"])
        
        # Evaluation metrics
        total_rewards = []
        episode_lengths = []
        crashes = 0
        
        for episode in range(n_episodes):
            obs, info = eval_env.reset()
            episode_reward = 0
            episode_length = 0
            done = False
            
            while not done:
                action, _ = model.predict(obs, deterministic=True)
                obs, reward, terminated, truncated, info = eval_env.step(action)
                
                episode_reward += reward
                episode_length += 1
                
                if terminated or truncated:
                    done = True
                    if terminated:  # Crash
                        crashes += 1
            
            total_rewards.append(episode_reward)
            episode_lengths.append(episode_length)
        
        # Calculate statistics
        avg_reward = np.mean(total_rewards)
        std_reward = np.std(total_rewards)
        avg_length = np.mean(episode_lengths)
        crash_rate = crashes / n_episodes
        
        results = {
            "avg_reward": avg_reward,
            "std_reward": std_reward,
            "avg_episode_length": avg_length,
            "crash_rate": crash_rate,
            "total_episodes": n_episodes
        }
        
        logger.info(f"Evaluation Results: {results}")
        return results
    
    def cleanup(self):
        """Clean up resources"""
        if self.env:
            self.env.close()
        if self.eval_env:
            self.eval_env.close()
        logger.info("Environment cleanup completed")

def quick_test():
    """Quick test of the training system"""
    logger.info("Running quick test...")
    
    config = {
        "model_type": "PPO",
        "total_timesteps": 10_000,  # Short test
        "n_envs": 2,
        "eval_freq": 5_000,
        "save_freq": 5_000,
        "model_params": {
            "learning_rate": 3e-4,
            "n_steps": 512,
            "batch_size": 32,
            "n_epochs": 5,
            "gamma": 0.99,
        },
        "env_params": {
            "max_obstacles": 5,
            "max_steps": 100,
            "collision_threshold": 0.1,
        }
    }
    
    trainer = DroneRLTrainer(config)
    model_path = trainer.train()
    
    if model_path:
        # Quick evaluation
        results = trainer.evaluate_model(model_path, n_episodes=10)
        logger.info(f"Quick test results: {results}")
    
    return model_path

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Train Drone RL Model")
    parser.add_argument("--test", action="store_true", help="Run quick test")
    parser.add_argument("--model", choices=["PPO", "A2C", "DQN"], default="PPO", help="Model type")
    parser.add_argument("--timesteps", type=int, default=500_000, help="Total training timesteps")
    parser.add_argument("--envs", type=int, default=4, help="Number of parallel environments")
    
    args = parser.parse_args()
    
    if args.test:
        quick_test()
    else:
        config = {
            "model_type": args.model,
            "total_timesteps": args.timesteps,
            "n_envs": args.envs,
            "eval_freq": 10_000,
            "save_freq": 20_000,
            "model_params": {
                "learning_rate": 3e-4,
                "n_steps": 2048,
                "batch_size": 64,
                "n_epochs": 10,
                "gamma": 0.99,
            },
            "env_params": {
                "max_obstacles": 10,
                "max_steps": 200,
                "collision_threshold": 0.1,
            }
        }
        
        trainer = DroneRLTrainer(config)
        model_path = trainer.train()
        
        if model_path:
            # Evaluate trained model
            results = trainer.evaluate_model(model_path, n_episodes=100)
            logger.info(f"Final evaluation results: {results}")
        
        logger.info("🎉 Training process completed!")
