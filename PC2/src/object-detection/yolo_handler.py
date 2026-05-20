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

# COCO class names (80 classes)
COCO_CLASSES = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat",
    "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat",
    "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack",
    "umbrella", "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball",
    "kite", "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket",
    "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple",
    "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair",
    "couch", "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse", "remote",
    "keyboard", "cell phone", "microwave", "oven", "toaster", "sink", "refrigerator", "book",
    "clock", "vase", "scissors", "teddy bear", "hair drier", "toothbrush"
]

# Map COCO classes to LGADS semantic categories
CLASS_MAPPING = {
    # Animals (direct COCO matches)
    "person": "person",
    "bird": "bird",
    "cat": "animal",
    "dog": "animal",
    "horse": "animal",
    "sheep": "animal",
    "cow": "animal",
    "elephant": "animal",
    "bear": "animal",
    "zebra": "animal",
    "giraffe": "animal",
    # Vehicles
    "car": "vehicle",
    "bus": "vehicle",
    "truck": "vehicle",
    "motorcycle": "vehicle",
    "bicycle": "vehicle",
    "boat": "vehicle",
    "airplane": "vehicle",
    "train": "vehicle",
    # Structures (closest COCO matches)
    "bench": "structure",
    "chair": "structure",
    "couch": "structure",
    "bed": "structure",
    "dining table": "structure",
    "potted plant": "vegetation",
}

# Target classes for LGADS
TARGET_CLASSES = {"person", "bird", "animal", "vehicle", "structure", "vegetation", "tree", "building"}

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
                        class_id = int(box.cls[0].cpu().numpy())
                        coco_name = COCO_CLASSES[class_id] if class_id < len(COCO_CLASSES) else "unknown"
                        semantic_class = CLASS_MAPPING.get(coco_name, coco_name)
                        
                        detection = {
                            'bbox': box.xyxy[0].cpu().numpy().tolist(),
                            'confidence': float(box.conf[0].cpu().numpy()),
                            'class_id': class_id,
                            'class_name': semantic_class,
                            'coco_class': coco_name
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