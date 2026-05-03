# Image preprocessing for computer vision pipeline
"""
Image processing utilities for detection pipeline
"""

import cv2
import numpy as np
from typing import Tuple, Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ImageProcessor:
    """Image preprocessing and postprocessing utilities"""
    
    def __init__(self):
        """Initialize image processor"""
        pass
    
    def preprocess(self, image: np.ndarray, 
                  target_size: Tuple[int, int] = (640, 640)) -> np.ndarray:
        """
        Preprocess image for model input
        
        Args:
            image: Input image (BGR format)
            target_size: Target size (width, height)
            
        Returns:
            Preprocessed image
        """
        if image is None:
            raise ValueError("Input image is None")
        
        # Convert BGR to RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Resize
        image_resized = cv2.resize(image_rgb, target_size)
        
        # Normalize to [0, 1]
        image_normalized = image_resized.astype(np.float32) / 255.0
        
        return image_normalized
    
    def postprocess(self, predictions: np.ndarray, 
                   original_size: Tuple[int, int]) -> List[dict]:
        """
        Postprocess model predictions
        
        Args:
            predictions: Model output
            original_size: Original image size (height, width)
            
        Returns:
            List of detection dictionaries
        """
        # This would parse model-specific outputs
        # For now, return empty list
        return []
    
    def resize_with_aspect(self, image: np.ndarray, 
                          target_size: Tuple[int, int]) -> np.ndarray:
        """
        Resize image while maintaining aspect ratio
        
        Args:
            image: Input image
            target_size: Target size (width, height)
            
        Returns:
            Resized image with padding
        """
        h, w = image.shape[:2]
        target_w, target_h = target_size
        
        # Calculate scaling factor
        scale = min(target_w / w, target_h / h)
        new_w = int(w * scale)
        new_h = int(h * scale)
        
        # Resize
        resized = cv2.resize(image, (new_w, new_h))
        
        # Create padded image
        padded = np.zeros((target_h, target_w, 3), dtype=np.uint8)
        padded[:new_h, :new_w] = resized
        
        return padded
    
    def enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """Enhance image contrast using CLAHE"""
        if len(image.shape) == 3:
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            l = clahe.apply(l)
            enhanced = cv2.merge([l, a, b])
            enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
        else:
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(image)
        
        return enhanced
    
    def remove_noise(self, image: np.ndarray) -> np.ndarray:
        """Remove noise using bilateral filter"""
        return cv2.bilateralFilter(image, 9, 75, 75)
    
    def get_timestamp(self) -> str:
        """Get current timestamp"""
        return datetime.now().isoformat()