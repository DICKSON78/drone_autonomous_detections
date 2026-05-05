# Neural network architecture for PPO algorithm
"""
Policy Network for RL Agent
"""

import torch
import torch.nn as nn
import torch.nn.functional as F

class PolicyNetwork(nn.Module):
    """Neural network for policy approximation"""
    
    def __init__(self, state_dim: int, action_dim: int, hidden_dims: list = [256, 256]):
        """
        Initialize policy network
        
        Args:
            state_dim: Input state dimension
            action_dim: Output action dimension
            hidden_dims: List of hidden layer dimensions
        """
        super(PolicyNetwork, self).__init__()
        
        layers = []
        prev_dim = state_dim
        
        # Build hidden layers
        for hidden_dim in hidden_dims:
            layers.append(nn.Linear(prev_dim, hidden_dim))
            layers.append(nn.ReLU())
            prev_dim = hidden_dim
        
        # Output layer
        layers.append(nn.Linear(prev_dim, action_dim))
        layers.append(nn.Tanh())  # Output in [-1, 1]
        
        self.network = nn.Sequential(*layers)
        
        # Initialize weights
        self.apply(self._init_weights)
    
    def _init_weights(self, module):
        """Initialize network weights"""
        if isinstance(module, nn.Linear):
            nn.init.orthogonal_(module.weight, gain=0.01)
            nn.init.constant_(module.bias, 0)
    
    def forward(self, state: torch.Tensor) -> torch.Tensor:
        """
        Forward pass
        
        Args:
            state: State tensor
            
        Returns:
            Action tensor
        """
        return self.network(state)
    
    def get_action(self, state: torch.Tensor, deterministic: bool = True) -> torch.Tensor:
        """
        Get action from policy
        
        Args:
            state: State tensor
            deterministic: If True, return deterministic action
            
        Returns:
            Action tensor
        """
        action = self.forward(state)
        
        if not deterministic:
            # Add noise for exploration
            noise = torch.randn_like(action) * 0.1
            action = torch.clamp(action + noise, -1, 1)
        
        return action