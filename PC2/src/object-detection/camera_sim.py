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
            elif self.source == "simulation":
                # Try multiple Gazebo stream ports in order of preference
                stream_urls = [
                    "udp://gazebo-px4:5600",
                    "udp://gazebo-px4:5601",
                    "rtsp://gazebo-px4:8554/stream",
                    "http://gazebo-px4:8080/stream",
                ]
                for url in stream_urls:
                    logger.info(f"Attempting Gazebo stream: {url}")
                    self.cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
                    if self.cap.isOpened():
                        # Test if we can actually read a frame
                        ret, _ = self.cap.read()
                        if ret:
                            logger.info(f"Successfully connected to Gazebo stream: {url}")
                            break
                    self.cap.release()
                    self.cap = None
                
                if self.cap is None or not self.cap.isOpened():
                    logger.warning("Failed to connect to any Gazebo stream. Falling back to generated frames.")
                    self.is_simulated = True
            else:
                self.cap = cv2.VideoCapture(self.source)
            
            if not self.is_simulated and (self.cap is None or not self.cap.isOpened()):
                logger.warning(f"Failed to open camera source: {self.source}")
                self.is_simulated = True
            elif not self.is_simulated:
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
        """Generate simulated camera view with recognizable objects for YOLO detection"""
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        # Sky gradient (top half)
        for i in range(self.height // 2):
            color = int(135 + (i / (self.height // 2)) * 50)
            frame[i, :] = [color, color, 255]
        
        # Ground gradient (bottom half)
        for i in range(self.height // 2, self.height):
            color = int(34 + ((i - self.height // 2) / (self.height // 2)) * 50)
            frame[i, :] = [color, color, color]
        
        # Draw tree-like shapes (brown trunk + green canopy)
        for _ in range(random.randint(1, 3)):
            x = random.randint(50, self.width - 50)
            y = random.randint(self.height // 2, self.height - 60)
            # Trunk
            cv2.rectangle(frame, (x-5, y), (x+5, y+30), (139, 90, 43), -1)
            # Canopy
            cv2.circle(frame, (x, y-10), 25, (34, 139, 34), -1)
        
        # Draw building-like rectangles
        for _ in range(random.randint(1, 2)):
            x = random.randint(50, self.width - 100)
            y = random.randint(self.height // 2, self.height - 80)
            w, h = random.randint(40, 80), random.randint(50, 100)
            cv2.rectangle(frame, (x, y), (x+w, y+h), (169, 169, 169), -1)
            # Windows
            for wy in range(y+10, y+h-10, 15):
                for wx in range(x+10, x+w-10, 15):
                    cv2.rectangle(frame, (wx, wy), (wx+8, wy+8), (173, 216, 230), -1)
        
        # Draw person-like shapes
        for _ in range(random.randint(0, 2)):
            x = random.randint(50, self.width - 50)
            y = random.randint(self.height // 2 + 20, self.height - 40)
            # Head
            cv2.circle(frame, (x, y-15), 6, (255, 228, 181), -1)
            # Body
            cv2.rectangle(frame, (x-5, y-9), (x+5, y+10), (random.randint(100,200), random.randint(100,200), random.randint(100,200)), -1)
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, f"SIMULATED - {timestamp}", (10, self.height - 10),
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