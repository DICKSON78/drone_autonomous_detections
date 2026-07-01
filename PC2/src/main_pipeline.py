#!/usr/bin/env python3
"""
Main Pipeline for Autonomous Drone Obstacle Detection
Inaunganisha YOLO + RL + NLP - mfumo kamili wa drone
"""

import cv2
import numpy as np
import time
import logging
import json
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime

# Import our modules
from object_detection.auto_label import DroneAutoLabeler
from object_detection.main import process_image, DetectionResponse
from rl_navigation.drone_env import DroneObstacleEnv
from rl_navigation.train_rl import DroneRLTrainer
from nlp_module import DroneNLP

# Try to import YOLO and RL models
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    logging.warning("YOLO not available. Using mock detection.")

try:
    from stable_baselines3 import PPO, A2C, DQN
    RL_AVAILABLE = True
except ImportError:
    RL_AVAILABLE = False
    logging.warning("Stable Baselines3 not available. Using mock RL.")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DroneSystem:
    """Mfumo kamili: YOLO + RL + NLP"""

    def __init__(self, config: Dict = None):
        self.config = config or self._default_config()
        self.yolo_model = None
        self.rl_model = None
        self.env = None
        self.nlp = DroneNLP()
        self.flight_history = []
        self.system_stats = {
            "total_frames": 0,
            "detections": 0,
            "avoidance_actions": 0,
            "crashes": 0,
            "start_time": datetime.now()
        }
        
        logger.info("🚁 Initializing Drone System...")
        self._initialize_models()

    def _default_config(self) -> Dict:
        """Default configuration for the drone system"""
        return {
            "yolo_model_path": "yolov8n.pt",
            "rl_model_path": "models/drone_ppo_final.zip",
            "detection_confidence": 0.4,
            "rl_confidence_threshold": 0.7,
            "max_obstacles": 10,
            "save_frames": False,
            "save_logs": True,
            "camera_source": 0,  # 0 for webcam, or video file path
            "output_video": "drone_output.mp4"
        }

    def _initialize_models(self):
        """Initialize YOLO and RL models"""
        
        # Initialize YOLO
        if YOLO_AVAILABLE:
            try:
                self.yolo_model = YOLO(self.config["yolo_model_path"])
                logger.info("✅ YOLO model loaded successfully")
            except Exception as e:
                logger.error(f"❌ Failed to load YOLO model: {e}")
                self.yolo_model = None
        else:
            logger.warning("⚠️ YOLO not available, using mock detection")
        
        # Initialize RL
        if RL_AVAILABLE:
            try:
                model_path = self.config["rl_model_path"]
                if Path(model_path).exists():
                    self.rl_model = PPO.load(model_path)
                    logger.info("✅ RL model loaded successfully")
                else:
                    logger.warning(f"⚠️ RL model not found: {model_path}")
                    self.rl_model = None
            except Exception as e:
                logger.error(f"❌ Failed to load RL model: {e}")
                self.rl_model = None
        else:
            logger.warning("⚠️ RL not available, using mock decisions")
        
        # Initialize environment
        self.env = DroneObstacleEnv()
        logger.info("✅ Environment initialized")

    def process_frame(self, frame: np.ndarray) -> Dict:
        """
        Shughulikia frame moja ya video.
        Inarudisha: action, maelezo, na vizuizi vilivyoonwa.
        """

        # ── Hatua 1: YOLO inaona vizuizi ──────────────────
        obstacles, detection_time = self._detect_obstacles(frame)
        
        # ── Hatua 2: RL inafanya uamuzi ───────────────────
        action, rl_confidence, reasoning = self._make_decision(obstacles)
        
        # ── Hatua 3: NLP inaeleza ──────────────────────────
        explanation = self.nlp.explain_current_state(obstacles, action, rl_confidence)
        
        # ── Hatua 4: Update statistics ──────────────────────
        self._update_statistics(obstacles, action, rl_confidence)
        
        # ── Hatua 5: Hifadhi historia ────────────────────────
        flight_event = {
            "timestamp": datetime.now(),
            "obstacles": obstacles,
            "action": action,
            "confidence": rl_confidence,
            "reasoning": reasoning,
            "explanation": explanation,
            "detection_time": detection_time
        }
        self.flight_history.append(flight_event)
        
        # ── Hatua 6: Weka visualizations ───────────────────
        annotated_frame = self._draw_frame(frame, obstacles, action, explanation)
        
        return {
            "obstacles": obstacles,
            "action": action,
            "action_name": DroneObstacleEnv.ACTIONS.get(action, "unknown"),
            "confidence": rl_confidence,
            "explanation": explanation,
            "reasoning": reasoning,
            "frame": annotated_frame,
            "detection_time": detection_time
        }

    def _detect_obstacles(self, frame: np.ndarray) -> Tuple[List[Dict], float]:
        """Detect obstacles using YOLO or mock detection"""
        start_time = time.time()
        
        if self.yolo_model is None:
            # Mock detection for testing
            return self._mock_detection(frame), time.time() - start_time
        
        try:
            results = self.yolo_model.predict(frame, conf=self.config["detection_confidence"], verbose=False)
            obstacles = self._extract_obstacles(results[0])
            detection_time = time.time() - start_time
            
            logger.info(f"🔍 Detected {len(obstacles)} obstacles in {detection_time:.3f}s")
            return obstacles, detection_time
            
        except Exception as e:
            logger.error(f"❌ Detection error: {e}")
            return self._mock_detection(frame), time.time() - start_time

    def _mock_detection(self, frame: np.ndarray) -> List[Dict]:
        """Generate mock obstacles for testing"""
        np.random.seed(int(time.time()) % 1000)
        n_obstacles = np.random.randint(0, 4)
        
        obstacles = []
        for i in range(n_obstacles):
            obstacles.append({
                "class": np.random.randint(0, 6),
                "confidence": np.random.uniform(0.5, 1.0),
                "x": np.random.uniform(0.1, 0.9),
                "y": np.random.uniform(0.1, 0.9),
                "w": np.random.uniform(0.05, 0.3),
                "h": np.random.uniform(0.05, 0.3)
            })
        
        return obstacles

    def _extract_obstacles(self, result) -> List[Dict]:
        """Extract obstacles from YOLO results"""
        obstacles = []
        class_names = ["tree", "building", "pole", "person", "vehicle", "aircraft"]
        
        for box in result.boxes:
            try:
                obstacles.append({
                    "class": int(box.cls),
                    "name": class_names[int(box.cls)] if int(box.cls) < len(class_names) else "unknown",
                    "confidence": float(box.conf),
                    "x": float(box.xywhn[0][0]),
                    "y": float(box.xywhn[0][1]),
                    "w": float(box.xywhn[0][2]),
                    "h": float(box.xywhn[0][3])
                })
            except Exception as e:
                logger.warning(f"Error extracting obstacle: {e}")
                continue
        
        return obstacles

    def _make_decision(self, obstacles: List[Dict]) -> Tuple[int, float, Dict]:
        """Make decision using RL or mock decision"""
        if self.rl_model is None:
            return self._mock_decision(obstacles)
        
        try:
            # Update environment with current obstacles
            self.env.obstacles_from_yolo(type('MockResult', (), {'boxes': obstacles})())
            
            # Get observation
            obs = self.env._get_observation()
            
            # Get action from RL model
            action, _states = self.rl_model.predict(obs, deterministic=True)
            action = int(action)
            
            # Calculate confidence (simplified)
            confidence = min(0.9, 0.5 + len(obstacles) * 0.1)
            
            reasoning = {
                "primary_reason": "avoidance" if obstacles else "safety",
                "confidence": confidence,
                "obstacle_count": len(obstacles)
            }
            
            logger.info(f"🧠 RL Decision: {DroneObstacleEnv.ACTIONS.get(action, 'unknown')} (confidence: {confidence:.2f})")
            return action, confidence, reasoning
            
        except Exception as e:
            logger.error(f"❌ RL decision error: {e}")
            return self._mock_decision(obstacles)

    def _mock_decision(self, obstacles: List[Dict]) -> Tuple[int, float, Dict]:
        """Generate mock decision for testing"""
        if not obstacles:
            return 4, 0.8, {"primary_reason": "safety", "confidence": 0.8}
        
        # Simple avoidance logic
        main_obstacle = max(obstacles, key=lambda o: o.get("confidence", 0) * o.get("w", 0))
        x_pos = main_obstacle.get("x", 0.5)
        
        if x_pos < 0.4:
            action = 1  # go right
        elif x_pos > 0.6:
            action = 0  # go left
        else:
            action = 2  # climb
        
        confidence = min(0.9, 0.6 + len(obstacles) * 0.1)
        
        reasoning = {
            "primary_reason": "avoidance",
            "confidence": confidence,
            "obstacle_count": len(obstacles),
            "main_obstacle": main_obstacle.get("name", "unknown")
        }
        
        return action, confidence, reasoning

    def _update_statistics(self, obstacles: List[Dict], action: int, confidence: float):
        """Update system statistics"""
        self.system_stats["total_frames"] += 1
        
        if obstacles:
            self.system_stats["detections"] += len(obstacles)
        
        if action in [0, 1, 2, 3]:  # avoidance actions
            self.system_stats["avoidance_actions"] += 1
        
        # Check for crash (simplified)
        if obstacles and confidence < 0.3:
            self.system_stats["crashes"] += 1

    def _draw_frame(self, frame: np.ndarray, obstacles: List[Dict], action: int, explanation: str) -> np.ndarray:
        """Weka maelezo kwenye frame"""
        annotated = frame.copy()
        
        # Draw obstacles
        for obs in obstacles:
            x, y, w, h = obs["x"], obs["y"], obs["w"], obs["h"]
            img_h, img_w = frame.shape[:2]
            
            # Convert normalized coordinates to pixel coordinates
            x1 = int((x - w/2) * img_w)
            y1 = int((y - h/2) * img_h)
            x2 = int((x + w/2) * img_w)
            y2 = int((y + h/2) * img_h)
            
            # Draw bounding box
            color = (0, 255, 0) if obs["confidence"] > 0.7 else (0, 255, 255)
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            
            # Draw label
            label = f"{obs.get('name', 'unknown')} {obs['confidence']:.2f}"
            cv2.putText(annotated, label, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        # Draw action info
        action_name = DroneObstacleEnv.ACTIONS.get(action, "unknown")
        cv2.putText(
            annotated, f"Action: {action_name}",
            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2
        )
        
        # Draw explanation (truncated)
        explanation_short = explanation[:60] + "..." if len(explanation) > 60 else explanation
        cv2.putText(
            annotated, explanation_short,
            (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1
        )
        
        # Draw statistics
        stats_text = f"Frames: {self.system_stats['total_frames']} | Detections: {self.system_stats['detections']}"
        cv2.putText(
            annotated, stats_text,
            (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1
        )
        
        return annotated

    def run_video(self, video_path: Optional[str] = None):
        """Endesha mfumo kwa video nzima"""
        
        if video_path is None:
            video_path = self.config["camera_source"]
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"❌ Cannot open video source: {video_path}")
            return
        
        # Setup video writer
        output_path = self.config["output_video"]
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        fps = 30
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        out = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))
        
        logger.info(f"🎥 Starting video processing: {video_path}")
        logger.info(f"📹 Output will be saved to: {output_path}")
        
        frame_count = 0
        start_time = time.time()
        
        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Process frame
                result = self.process_frame(frame)
                
                # Display info
                print(f"[{result['action_name']}] {result['explanation']}")
                
                # Show frame
                cv2.imshow("Drone Vision System", result["frame"])
                
                # Save frame
                out.write(result["frame"])
                
                frame_count += 1
                
                # Check for quit
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                
                # Limit processing for demo
                if frame_count >= 1000:  # Process max 1000 frames for demo
                    break
        
        finally:
            cap.release()
            out.release()
            cv2.destroyAllWindows()
        
        # Generate final summary
        processing_time = time.time() - start_time
        self._generate_final_summary(frame_count, processing_time)

    def _generate_final_summary(self, frame_count: int, processing_time: float):
        """Generate final flight summary"""
        
        # Calculate performance metrics
        fps = frame_count / processing_time if processing_time > 0 else 0
        detection_rate = self.system_stats["detections"] / max(1, self.system_stats["total_frames"])
        avoidance_rate = self.system_stats["avoidance_actions"] / max(1, self.system_stats["total_frames"])
        crash_rate = self.system_stats["crashes"] / max(1, self.system_stats["total_frames"])
        
        print("\n" + "="*60)
        print("🚁 DRONE SYSTEM - FINAL SUMMARY")
        print("="*60)
        print(f"📊 Processing Statistics:")
        print(f"   • Total Frames: {frame_count}")
        print(f"   • Processing Time: {processing_time:.2f}s")
        print(f"   • Average FPS: {fps:.1f}")
        print(f"🔍 Detection Statistics:")
        print(f"   • Total Detections: {self.system_stats['detections']}")
        print(f"   • Detection Rate: {detection_rate:.2f} per frame")
        print(f"🧠 Decision Statistics:")
        print(f"   • Avoidance Actions: {self.system_stats['avoidance_actions']}")
        print(f"   • Avoidance Rate: {avoidance_rate:.2%}")
        print(f"   • Crashes: {self.system_stats['crashes']}")
        print(f"   • Crash Rate: {crash_rate:.2%}")
        print("="*60)
        
        # Generate NLP summary
        nlp_summary = self.nlp.generate_flight_summary(self.flight_history)
        print(f"📝 Flight Summary:")
        print(f"   {nlp_summary}")
        print("="*60)
        
        # Save logs if enabled
        if self.config["save_logs"]:
            self._save_logs()

    def _save_logs(self):
        """Save system logs"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save flight history
        history_file = f"flight_history_{timestamp}.json"
        with open(history_file, 'w') as f:
            json.dump(self.flight_history, f, indent=2, default=str)
        
        # Save statistics
        stats_file = f"system_stats_{timestamp}.json"
        with open(stats_file, 'w') as f:
            json.dump(self.system_stats, f, indent=2, default=str)
        
        logger.info(f"📁 Logs saved: {history_file}, {stats_file}")

# ── Main execution ────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Autonomous Drone Obstacle Detection System")
    parser.add_argument("--video", type=str, help="Video file path (default: webcam)")
    parser.add_argument("--yolo-model", type=str, default="yolov8n.pt", help="YOLO model path")
    parser.add_argument("--rl-model", type=str, default="models/drone_ppo_final.zip", help="RL model path")
    parser.add_argument("--confidence", type=float, default=0.4, help="Detection confidence threshold")
    parser.add_argument("--output", type=str, default="drone_output.mp4", help="Output video file")
    parser.add_argument("--demo", action="store_true", help="Run demo with mock data")
    
    args = parser.parse_args()
    
    # Configure system
    config = {
        "yolo_model_path": args.yolo_model,
        "rl_model_path": args.rl_model,
        "detection_confidence": args.confidence,
        "output_video": args.output,
        "camera_source": args.video if args.video else 0
    }
    
    # Initialize and run system
    print("🚁 Starting Autonomous Drone Obstacle Detection System...")
    print("="*60)
    
    system = DroneSystem(config)
    
    if args.demo:
        print("🎬 Running demo mode...")
        # Run with webcam or test video
        video_source = args.video if args.video else 0
        system.run_video(video_source)
    else:
        print("🎥 Running full system...")
        video_source = args.video if args.video else 0
        system.run_video(video_source)
    
    print("🎉 System execution completed!")
