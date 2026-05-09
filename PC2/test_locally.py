#!/usr/bin/env python3
"""
PC2 Local Testing Script
Tests all PC2 components locally before Docker deployment
"""

import os
import sys
import time
import logging
import requests
import subprocess
import threading
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PC2LocalTester:
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.src_dir = self.base_dir / "src"
        self.processes = []
        
    def check_dependencies(self):
        """Check if all required dependencies are installed"""
        logger.info("Checking dependencies...")
        
        try:
            import cv2
            import numpy as np
            import torch
            import fastapi
            import uvicorn
            logger.info("✓ Python dependencies available")
        except ImportError as e:
            logger.error(f"✗ Missing dependency: {e}")
            return False
            
        return True
    
    def test_object_detection(self):
        """Test object detection module"""
        logger.info("Testing Object Detection Module...")
        
        try:
            # Add to path
            sys.path.insert(0, str(self.src_dir / "object-detection"))
            
            from yolo_handler import YOLOHandler
            from camera_sim import CameraSimulator
            from image_processor import ImageProcessor
            
            # Test YOLO Handler
            logger.info("  Testing YOLO Handler...")
            detector = YOLOHandler(model_name="yolov8n.pt", device="cpu")
            
            # Test Camera Simulator
            logger.info("  Testing Camera Simulator...")
            camera = CameraSimulator(width=640, height=480, source="simulation")
            frame = camera.capture_frame()
            
            if frame is not None:
                logger.info("  ✓ Camera simulator working")
                
                # Test detection
                logger.info("  Testing object detection...")
                detections = detector.detect(frame)
                logger.info(f"  ✓ Detection successful: {len(detections)} objects found")
            else:
                logger.error("  ✗ Camera simulator failed")
                return False
                
            # Test Image Processor
            logger.info("  Testing Image Processor...")
            processor = ImageProcessor()
            processed = processor.preprocess(frame)
            logger.info("  ✓ Image processing working")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ Object detection test failed: {e}")
            return False
    
    def test_rl_navigation(self):
        """Test RL navigation module"""
        logger.info("Testing RL Navigation Module...")
        
        try:
            # Add to path
            sys.path.insert(0, str(self.src_dir / "rl-navigation"))
            
            from environment import NavigationEnvironment
            from rl_agent import RLAgent
            
            # Test Environment
            logger.info("  Testing Navigation Environment...")
            env = NavigationEnvironment()
            state = env.reset()
            logger.info(f"  ✓ Environment initialized, state shape: {state.shape}")
            
            # Test Agent
            logger.info("  Testing RL Agent...")
            agent = RLAgent(state_dim=14, action_dim=6)
            action = agent.get_action(state)
            logger.info(f"  ✓ Agent working, action: {action}")
            
            # Test episode
            logger.info("  Testing episode execution...")
            total_reward = 0
            for step in range(10):
                action = agent.get_action(state)
                next_state, reward, done, _ = env.step(action)
                total_reward += reward
                state = next_state
                if done:
                    break
            logger.info(f"  ✓ Episode execution successful, total reward: {total_reward:.2f}")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ RL navigation test failed: {e}")
            return False
    
    def test_gazebo_integration(self):
        """Test Gazebo integration"""
        logger.info("Testing Gazebo Integration...")
        
        try:
            # Add to path
            sys.path.insert(0, str(self.src_dir / "gazebo-integration"))
            
            from world_builder import WorldBuilder
            from px4_interface import MockPX4Interface
            
            # Test World Builder
            logger.info("  Testing World Builder...")
            builder = WorldBuilder()
            builder.create_base_world("test_world")
            
            # Add some obstacles
            builder.add_obstacle([5, 5, 0], [2, 2, 2], [1, 0, 0])
            builder.add_sphere_obstacle([0, 10, 1], 1.0, [0, 1, 0])
            
            # Save world
            world_file = self.base_dir / "test_world.world"
            builder.save_world(str(world_file))
            logger.info(f"  ✓ World saved to {world_file}")
            
            # Test PX4 Interface (Mock)
            logger.info("  Testing PX4 Interface (Mock)...")
            px4 = MockPX4Interface()
            if px4.connect():
                state = px4.get_state()
                logger.info(f"  ✓ PX4 mock working: {state['position']}")
            else:
                logger.error("  ✗ PX4 mock failed to connect")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"✗ Gazebo integration test failed: {e}")
            return False
    
    def start_services_locally(self):
        """Start services locally for testing"""
        logger.info("Starting services locally...")
        
        try:
            # Start Object Detection Service
            logger.info("Starting Object Detection Service...")
            od_process = subprocess.Popen([
                sys.executable, "-m", "uvicorn", 
                "main:app", "--host", "0.0.0.0", "--port", "8002"
            ], cwd=str(self.src_dir / "object-detection"))
            self.processes.append(od_process)
            time.sleep(3)
            
            # Start RL Navigation Service
            logger.info("Starting RL Navigation Service...")
            rl_process = subprocess.Popen([
                sys.executable, "-m", "uvicorn", 
                "main:app", "--host", "0.0.0.0", "--port", "8003"
            ], cwd=str(self.src_dir / "rl-navigation"))
            self.processes.append(rl_process)
            time.sleep(3)
            
            return True
            
        except Exception as e:
            logger.error(f"✗ Failed to start services: {e}")
            return False
    
    def test_api_endpoints(self):
        """Test API endpoints"""
        logger.info("Testing API Endpoints...")
        
        try:
            # Test Object Detection Health
            logger.info("  Testing Object Detection Health...")
            response = requests.get("http://localhost:8002/health", timeout=5)
            if response.status_code == 200:
                logger.info("  ✓ Object Detection API healthy")
            else:
                logger.error(f"  ✗ Object Detection API error: {response.status_code}")
                return False
            
            # Test RL Navigation Health
            logger.info("  Testing RL Navigation Health...")
            response = requests.get("http://localhost:8003/health", timeout=5)
            if response.status_code == 200:
                logger.info("  ✓ RL Navigation API healthy")
            else:
                logger.error(f"  ✗ RL Navigation API error: {response.status_code}")
                return False
            
            # Test Navigation Endpoint
            logger.info("  Testing Navigation Endpoint...")
            nav_request = {
                "current_position": [0.0, 0.0],
                "target_position": [10.0, 10.0],
                "obstacles": []
            }
            response = requests.post(
                "http://localhost:8003/navigate", 
                json=nav_request, 
                timeout=10
            )
            if response.status_code == 200:
                result = response.json()
                logger.info(f"  ✓ Navigation working: {result['next_action']}")
            else:
                logger.error(f"  ✗ Navigation API error: {response.status_code}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"✗ API endpoint test failed: {e}")
            return False
    
    def stop_services(self):
        """Stop all running services"""
        logger.info("Stopping services...")
        for process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                try:
                    process.kill()
                except:
                    pass
        self.processes.clear()
    
    def run_full_test(self):
        """Run complete test suite"""
        logger.info("Starting PC2 Local Test Suite")
        logger.info("=" * 50)
        
        try:
            # Check dependencies
            if not self.check_dependencies():
                logger.error("Dependency check failed. Install missing packages.")
                return False
            
            # Test individual modules
            logger.info("\n" + "=" * 50)
            logger.info("MODULE TESTS")
            logger.info("=" * 50)
            
            od_ok = self.test_object_detection()
            rl_ok = self.test_rl_navigation()
            gazebo_ok = self.test_gazebo_integration()
            
            if not (od_ok and rl_ok and gazebo_ok):
                logger.error("Module tests failed!")
                return False
            
            logger.info("✓ All module tests passed!")
            
            # Start services and test APIs
            logger.info("\n" + "=" * 50)
            logger.info("API TESTS")
            logger.info("=" * 50)
            
            if not self.start_services_locally():
                logger.error("Failed to start services!")
                return False
            
            try:
                api_ok = self.test_api_endpoints()
                if api_ok:
                    logger.info("✓ All API tests passed!")
                else:
                    logger.error("API tests failed!")
                    return False
            finally:
                self.stop_services()
            
            logger.info("\n" + "=" * 50)
            logger.info("✓ PC2 LOCAL TESTS COMPLETED SUCCESSFULLY!")
            logger.info("=" * 50)
            return True
            
        except KeyboardInterrupt:
            logger.info("\nTest interrupted by user")
            return False
        except Exception as e:
            logger.error(f"Test suite failed: {e}")
            return False
        finally:
            self.stop_services()

if __name__ == "__main__":
    tester = PC2LocalTester()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "modules":
            tester.check_dependencies()
            tester.test_object_detection()
            tester.test_rl_navigation()
            tester.test_gazebo_integration()
        elif command == "services":
            tester.start_services_locally()
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                tester.stop_services()
        elif command == "api":
            tester.test_api_endpoints()
        else:
            print("Usage: python test_locally.py [modules|services|api]")
    else:
        tester.run_full_test()
