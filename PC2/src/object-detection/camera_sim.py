# Camera simulation for testing object detection

"""
Camera simulator for drone footage
"""

import cv2
import numpy as np
from typing import Optional, Tuple, Any
import logging
import random
from datetime import datetime

logger = logging.getLogger(__name__)

class CameraSimulator:
    """Simulates camera feed from drone"""
    
    def __init__(self, width: int = 640, height: int = 480, 
                 source: str = "simulation", fps: int = 30):
        """
        Initialize camera simulator
        
        Args:
            width: Frame width
            height: Frame height
            source: Camera source ('simulation', 'webcam', or video file path)
            fps: Frames per second
        """
        self.width = width
        self.height = height
        self.source = source
        self.fps = fps
        self.cap = None
        self.is_simulated = (source == "simulation")
        
        if not self.is_simulated:
            self._open_camera()
        
        logger.info(f"Camera initialized: source={source}, size={width}x{height}")
    
    def _open_camera(self):
        """Open real camera or video file"""
        try:
            if self.source == "webcam":
                self.cap = cv2.VideoCapture(0)
            else:
                self.cap = cv2.VideoCapture(self.source)
            
            if not self.cap.isOpened():
                logger.warning(f"Failed to open camera source: {self.source}")
                self.is_simulated = True
            else:
                # Set resolution
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                
        except Exception as e:
            logger.error(f"Camera error: {e}")
            self.is_simulated = True
    
    def capture_frame(self) -> Optional[np.ndarray]:
        """
        Capture a single frame
        
        Returns:
            Frame as numpy array (BGR format)
        """
        if self.is_simulated:
            return self._generate_simulated_frame()
        else:
            ret, frame = self.cap.read()
            if not ret:
                logger.warning("Failed to read frame from camera")
                return self._generate_simulated_frame()
            
            # Resize if needed
            if frame.shape[1] != self.width or frame.shape[0] != self.height:
                frame = cv2.resize(frame, (self.width, self.height))
            
            return frame
    
    def _generate_simulated_frame(self) -> np.ndarray:
        """Generate simulated camera view with simple objects"""
        # Create base image (sky/ground gradient)
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        # Sky gradient (top half)
        for i in range(self.height // 2):
            color = int(135 + (i / (self.height // 2)) * 50)
            frame[i, :] = [color, color, 255]  # Blue-ish
        
        # Ground gradient (bottom half)
        for i in range(self.height // 2, self.height):
            color = int(34 + ((i - self.height // 2) / (self.height // 2)) * 50)
            frame[i, :] = [color, color, color]  # Gray-ish
        
        # Add some random "objects" (circles)
        num_objects = random.randint(0, 5)
        for _ in range(num_objects):
            x = random.randint(50, self.width - 50)
            y = random.randint(self.height // 4, self.height - 50)
            radius = random.randint(10, 30)
            color = (
                random.randint(0, 255),
                random.randint(0, 255),
                random.randint(0, 255)
            )
            cv2.circle(frame, (x, y), radius, color, -1)
        
        # Add timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, timestamp, (10, self.height - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return frame
    
    def start_stream(self):
        """Start continuous streaming (for async operations)"""
        # This would be implemented for real-time streaming
        pass
    
    def close(self):
        """Release camera resources"""
        if self.cap is not None:
            self.cap.release()
            logger.info("Camera released")