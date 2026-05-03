# Unit tests for computer vision functionality


import cv2
import numpy as np
from yolo_handler import YOLOHandler
from camera_sim import CameraSimulator

def test_detector():
    detector = YOLOHandler()
    camera = CameraSimulator()
    
    frame = camera.capture_frame()
    detections = detector.detect(frame)
    
    assert isinstance(detections, list)
    print(f"Detected {len(detections)} objects")