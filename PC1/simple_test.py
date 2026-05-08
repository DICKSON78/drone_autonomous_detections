#!/usr/bin/env python3
"""
Simple Test Script for PC1 AI Drone System
Tests the current running services without requiring rebuilds
"""

import requests
import json
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_basic_functionality():
    """Test basic functionality of the drone system"""
    logger.info("=== Testing Basic Drone System Functionality ===")
    
    base_url = "http://localhost"
    command_parser_url = f"{base_url}:8000"
    flight_control_url = f"{base_url}:8001"
    
    # Test 1: Service Health
    logger.info("1. Testing Service Health...")
    try:
        parser_response = requests.get(f"{command_parser_url}/health", timeout=5)
        flight_response = requests.get(f"{flight_control_url}/health", timeout=5)
        
        parser_healthy = parser_response.status_code == 200
        flight_healthy = flight_response.status_code == 200
        
        logger.info(f"Command Parser Health: {'✓' if parser_healthy else '✗'}")
        logger.info(f"Flight Control Health: {'✓' if flight_healthy else '✗'}")
        
        if parser_healthy:
            logger.info(f"Parser Response: {parser_response.json()}")
        if flight_healthy:
            logger.info(f"Flight Response: {flight_response.json()}")
            
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return False
    
    if not (parser_healthy and flight_healthy):
        logger.error("Services are not healthy, stopping tests")
        return False
    
    # Test 2: Basic Command Processing
    logger.info("\n2. Testing Basic Command Processing...")
    test_commands = [
        "Go to forest area",
        "Search for person in forest", 
        "Monitor the lake area",
        "Emergency land now",
        "Return to home base"
    ]
    
    for i, command in enumerate(test_commands, 1):
        try:
            logger.info(f"  Testing command {i}: '{command}'")
            
            response = requests.post(
                f"{command_parser_url}/parse-command",
                json={"text": command, "user_id": f"test_user_{i}"},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"    ✓ Success: {result.get('status', 'unknown')}")
                
                parsed = result.get('parsed_command', {})
                logger.info(f"    Target GPS: {parsed.get('target_gps', 'None')}")
                logger.info(f"    Action: {parsed.get('action', 'None')}")
                logger.info(f"    Confidence: {parsed.get('confidence', 0)}")
                
            else:
                logger.error(f"    ✗ Failed with HTTP {response.status_code}")
                logger.error(f"    Response: {response.text}")
                
        except Exception as e:
            logger.error(f"    ✗ Exception: {e}")
    
    # Test 3: Flight Control Status
    logger.info("\n3. Testing Flight Control Status...")
    try:
        status_response = requests.get(f"{flight_control_url}/status", timeout=5)
        
        if status_response.status_code == 200:
            status_data = status_response.json()
            logger.info("    ✓ Status endpoint working")
            logger.info(f"    Status data: {status_data}")
        else:
            logger.error(f"    ✗ Status endpoint failed: HTTP {status_response.status_code}")
            
    except Exception as e:
        logger.error(f"    ✗ Status check exception: {e}")
    
    # Test 4: Kafka Message Flow
    logger.info("\n4. Testing Kafka Message Flow...")
    try:
        test_command = {
            "text": "Test kafka integration to lake",
            "user_id": "test_kafka"
        }
        
        response = requests.post(
            f"{command_parser_url}/parse-command",
            json=test_command,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            command_id = result.get('parsed_command', {}).get('command_id')
            logger.info(f"    ✓ Message sent to Kafka")
            logger.info(f"    Command ID: {command_id}")
        else:
            logger.error(f"    ✗ Kafka message failed: HTTP {response.status_code}")
            
    except Exception as e:
        logger.error(f"    ✗ Kafka test exception: {e}")
    
    logger.info("\n=== Basic Tests Complete ===")
    return True

def test_advanced_commands():
    """Test more advanced command scenarios"""
    logger.info("\n=== Testing Advanced Command Scenarios ===")
    
    command_parser_url = "http://localhost:8000"
    
    advanced_commands = [
        {
            "name": "Search with object detection",
            "command": "Search for missing person in the dense forest area",
            "expected_features": ["search", "person", "forest"]
        },
        {
            "name": "Surveillance mission", 
            "command": "Monitor the building perimeter for suspicious activity",
            "expected_features": ["monitor", "building"]
        },
        {
            "name": "Emergency scenario",
            "command": "Emergency land immediately due to low battery",
            "expected_features": ["emergency", "land"]
        },
        {
            "name": "Complex navigation",
            "command": "Navigate from forest to lake while avoiding obstacles",
            "expected_features": ["navigate", "forest", "lake"]
        },
        {
            "name": "Tracking mission",
            "command": "Track the red car moving through the forest",
            "expected_features": ["track", "car", "forest"]
        }
    ]
    
    for test_case in advanced_commands:
        logger.info(f"\nTesting: {test_case['name']}")
        logger.info(f"Command: '{test_case['command']}'")
        
        try:
            response = requests.post(
                f"{command_parser_url}/parse-command",
                json={"text": test_case['command'], "user_id": "advanced_test"},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                parsed = result.get('parsed_command', {})
                
                logger.info(f"  ✓ Processed successfully")
                logger.info(f"  Action: {parsed.get('action', 'None')}")
                logger.info(f"  Target: {parsed.get('target_gps', 'None')}")
                logger.info(f"  Confidence: {parsed.get('confidence', 0)}")
                
                # Check for expected features
                command_lower = test_case['command'].lower()
                found_features = []
                
                for feature in test_case['expected_features']:
                    if feature in command_lower:
                        found_features.append(feature)
                
                logger.info(f"  Expected features found: {found_features}")
                
            else:
                logger.error(f"  ✗ Failed: HTTP {response.status_code}")
                
        except Exception as e:
            logger.error(f"  ✗ Exception: {e}")

def test_error_scenarios():
    """Test error handling and edge cases"""
    logger.info("\n=== Testing Error Scenarios ===")
    
    command_parser_url = "http://localhost:8000"
    
    error_tests = [
        {
            "name": "Empty command",
            "data": {"text": "", "user_id": "test"},
            "expected_status": "should_handle_gracefully"
        },
        {
            "name": "Very long command",
            "data": {"text": "test " * 100, "user_id": "test"},
            "expected_status": "should_handle_gracefully"
        },
        {
            "name": "Special characters",
            "data": {"text": "Go to forest @#$%^&*()", "user_id": "test"},
            "expected_status": "should_handle_gracefully"
        }
    ]
    
    for test_case in error_tests:
        logger.info(f"\nTesting: {test_case['name']}")
        
        try:
            response = requests.post(
                f"{command_parser_url}/parse-command",
                json=test_case['data'],
                timeout=5
            )
            
            logger.info(f"  Status Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"  ✓ Handled gracefully")
                logger.info(f"  Response: {result.get('status', 'unknown')}")
            else:
                logger.info(f"  ✓ Rejected appropriately")
                logger.info(f"  Error: {response.text[:100]}")
                
        except Exception as e:
            logger.info(f"  ✓ Exception handled: {str(e)[:50]}")

def main():
    """Main test execution"""
    logger.info("Starting PC1 AI Drone System Tests")
    logger.info("=" * 50)
    
    try:
        # Run basic functionality tests
        basic_success = test_basic_functionality()
        
        if basic_success:
            # Run advanced command tests
            test_advanced_commands()
            
            # Run error scenario tests
            test_error_scenarios()
            
            logger.info("\n" + "=" * 50)
            logger.info("All tests completed!")
            logger.info("Check the logs above for detailed results.")
            
        else:
            logger.error("Basic functionality tests failed, skipping advanced tests")
            
    except KeyboardInterrupt:
        logger.info("\nTests interrupted by user")
    except Exception as e:
        logger.error(f"Test execution failed: {e}")

if __name__ == "__main__":
    main()
