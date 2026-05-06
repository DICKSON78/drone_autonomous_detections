# YOLOv5 model wrapper for object detection
"""
YOLO model handler for object detection
"""

import torch
import numpy as np
from typing import List, Dict, Any, Optional
import logging
from ultralytics import YOLO

logger = logging.getLogger(__name__)

class YOLOHandler:
    """Wrapper class for YOLO model operations"""
    
    def __init__(self, model_name: str = "yolov8n.pt", device: str = "cpu"):
        """
        Initialize YOLO model
        
        Args:
            model_name: Model name or path
            device: 'cpu' or 'cuda'
        """
        self.device = device
        self.model_name = model_name
        
        try:
            self.model = YOLO(model_name)
            
            # Move to GPU if available
            if device == "cuda" and torch.cuda.is_available():
                self.model.to('cuda')
                logger.info(f"Model loaded on GPU: {torch.cuda.get_device_name(0)}")
            else:
                logger.info("Model loaded on CPU")
                
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            raise
    
    def detect(self, image: np.ndarray, conf_threshold: float = 0.5,
              iou_threshold: float = 0.45) -> List[Dict[str, Any]]:
        """
        Run detection on single image
        
        Args:
            image: Input image (BGR or RGB)
            conf_threshold: Confidence threshold
            iou_threshold: IoU threshold for NMS
            
        Returns:
            List of detection dictionaries
        """
        try:
            # Run inference
            results = self.model(
                image, 
                conf=conf_threshold,
                iou=iou_threshold,
                verbose=False
            )
            
            # Parse results
            detections = []
            if len(results) > 0:
                boxes = results[0].boxes
                if boxes is not None:
                    for box in boxes:
                        detection = {
                            'bbox': box.xyxy[0].cpu().numpy().tolist(),
                            'confidence': float(box.conf[0].cpu().numpy()),
                            'class_id': int(box.cls[0].cpu().numpy())
                        }
                        detections.append(detection)
            
            return detections
            
        except Exception as e:
            logger.error(f"Detection error: {e}")
            return []
    
    def detect_batch(self, images: List[np.ndarray], 
                    conf_threshold: float = 0.5) -> List[List[Dict]]:
        """
        Run detection on batch of images
        
        Args:
            images: List of input images
            conf_threshold: Confidence threshold
            
        Returns:
            List of detection lists for each image
        """
        try:
            results = self.model(images, conf=conf_threshold, verbose=False)
            
            all_detections = []
            for result in results:
                detections = []
                if result.boxes is not None:
                    for box in result.boxes:
                        detection = {
                            'bbox': box.xyxy[0].cpu().numpy().tolist(),
                            'confidence': float(box.conf[0].cpu().numpy()),
                            'class_id': int(box.cls[0].cpu().numpy())
                        }
                        detections.append(detection)
                all_detections.append(detections)
            
            return all_detections
            
        except Exception as e:
            logger.error(f"Batch detection error: {e}")
            return [[] for _ in images]
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        return {
            'model_name': self.model_name,
            'device': self.device,
            'num_classes': 80,  # COCO dataset
            'input_size': (640, 640)
        }