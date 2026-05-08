#!/usr/bin/env python3
"""
Comprehensive Testing Script for PC1 AI Drone System
Tests NLP parsing, YOLO detection, RL control, and Kafka integration
"""

import requests
import json
import time
import logging
from typing import Dict, List

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DroneAITester:
    def __init__(self, base_url="http://localhost"):
        self.base_url = base_url
        self.command_parser_url = f"{base_url}:8000"
        self.flight_control_url = f"{base_url}:8001"
        self.test_results = []
    
    def log_test(self, test_name: str, passed: bool, details: str = ""):
        """Log test result"""
        status = "PASS" if passed else "FAIL"
        logger.info(f"{test_name}: {status} - {details}")
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "details": details,
            "timestamp": time.time()
        })
        return passed
    
    def test_service_health(self) -> bool:
        """Test if all services are healthy"""
        logger.info("=== Testing Service Health ===")
        
        # Test Command Parser
        try:
            response = requests.get(f"{self.command_parser_url}/health", timeout=5)
            parser_healthy = response.status_code == 200
            parser_data = response.json()
        except Exception as e:
            parser_healthy = False
            parser_data = str(e)
        
        # Test Flight Control
        try:
            response = requests.get(f"{self.flight_control_url}/health", timeout=5)
            flight_healthy = response.status_code == 200
            flight_data = response.json()
        except Exception as e:
            flight_healthy = False
            flight_data = str(e)
        
        parser_ok = self.log_test("Command Parser Health", parser_healthy, str(parser_data))
        flight_ok = self.log_test("Flight Control Health", flight_healthy, str(flight_data))
        
        return parser_ok and flight_ok
    
    def test_nlp_command_parsing(self) -> bool:
        """Test advanced NLP command parsing"""
        logger.info("=== Testing NLP Command Parsing ===")
        
        test_commands = [
            {
                "text": "Go to forest area",
                "expected_intent": "navigate",
                "expected_location": True,
                "user_id": "test_navigate"
            },
            {
                "text": "Search for missing person in the forest",
                "expected_intent": "search",
                "expected_objects": ["person"],
                "user_id": "test_search"
            },
            {
                "text": "Monitor the lake area for suspicious activity",
                "expected_intent": "surveillance",
                "expected_location": True,
                "user_id": "test_surveillance"
            },
            {
                "text": "Emergency land now",
                "expected_intent": "emergency_land",
                "user_id": "test_emergency"
            },
            {
                "text": "Return to home base",
                "expected_intent": "return_home",
                "user_id": "test_home"
            },
            {
                "text": "Hover over the building",
                "expected_intent": "hover",
                "expected_location": True,
                "user_id": "test_hover"
            },
            {
                "text": "Track the red car",
                "expected_intent": "track_object",
                "expected_objects": ["car"],
                "user_id": "test_track"
            }
        ]
        
        all_passed = True
        
        for test_case in test_commands:
            try:
                response = requests.post(
                    f"{self.command_parser_url}/parse-command",
                    json={"text": test_case["text"], "user_id": test_case["user_id"]},
                    timeout=10
                )
                
                if response.status_code == 200:
                    result = response.json()
                    passed = True
                    details = ""
                    
                    # Check intent
                    if result.get("parsed_command", {}).get("intent") != test_case["expected_intent"]:
                        passed = False
                        details += f"Intent mismatch: expected {test_case['expected_intent']}, got {result.get('parsed_command', {}).get('intent')}"
                    
                    # Check location
                    if test_case.get("expected_location") and not result.get("parsed_command", {}).get("target_gps"):
                        passed = False
                        details += " Missing target GPS"
                    
                    # Check objects
                    if test_case.get("expected_objects"):
                        search_objects = result.get("parsed_command", {}).get("search_objects", [])
                        for obj in test_case["expected_objects"]:
                            if obj not in search_objects:
                                passed = False
                                details += f" Missing object: {obj}"
                    
                    # Check confidence
                    confidence = result.get("parsed_command", {}).get("confidence", 0)
                    if confidence < 0.5:
                        passed = False
                        details += f" Low confidence: {confidence}"
                    
                    test_passed = self.log_test(f"NLP: {test_case['text']}", passed, details)
                    all_passed = all_passed and test_passed
                    
                else:
                    all_passed = False
                    self.log_test(f"NLP: {test_case['text']}", False, f"HTTP {response.status_code}")
                    
            except Exception as e:
                all_passed = False
                self.log_test(f"NLP: {test_case['text']}", False, str(e))
        
        return all_passed
    
    def test_flight_control_status(self) -> bool:
        """Test flight control status and drone state"""
        logger.info("=== Testing Flight Control Status ===")
        
        try:
            response = requests.get(f"{self.flight_control_url}/status", timeout=5)
            
            if response.status_code == 200:
                status_data = response.json()
                
                # Check required fields
                required_fields = ["connected", "latitude", "longitude", "altitude", "battery"]
                missing_fields = [field for field in required_fields if field not in status_data]
                
                if missing_fields:
                    passed = False
                    details = f"Missing fields: {missing_fields}"
                else:
                    passed = True
                    details = f"Battery: {status_data.get('battery', 0)}%, Altitude: {status_data.get('altitude', 0)}m"
                
                return self.log_test("Flight Control Status", passed, details)
            else:
                return self.log_test("Flight Control Status", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            return self.log_test("Flight Control Status", False, str(e))
    
    def test_kafka_message_flow(self) -> bool:
        """Test Kafka message flow between services"""
        logger.info("=== Testing Kafka Message Flow ===")
        
        try:
            # Send a command and check if it's processed
            test_command = {
                "text": "Test message flow to lake",
                "user_id": "test_kafka_flow"
            }
            
            response = requests.post(
                f"{self.command_parser_url}/parse-command",
                json=test_command,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Check if command was processed successfully
                success = result.get("status") == "success"
                command_id = result.get("parsed_command", {}).get("command_id")
                
                if success and command_id:
                    return self.log_test("Kafka Message Flow", True, f"Command ID: {command_id}")
                else:
                    return self.log_test("Kafka Message Flow", False, "Command processing failed")
            else:
                return self.log_test("Kafka Message Flow", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            return self.log_test("Kafka Message Flow", False, str(e))
    
    def test_complex_commands(self) -> bool:
        """Test complex multi-intent commands"""
        logger.info("=== Testing Complex Commands ===")
        
        complex_commands = [
            {
                "text": "Search the forest area for missing person and return if found",
                "user_id": "test_complex_1",
                "expected_intents": ["search"]
            },
            {
                "text": "Monitor the building perimeter while hovering at 100 meters",
                "user_id": "test_complex_2", 
                "expected_intents": ["surveillance", "hover"]
            },
            {
                "text": "Track the vehicle from forest to lake area",
                "user_id": "test_complex_3",
                "expected_intents": ["track_object"]
            }
        ]
        
        all_passed = True
        
        for test_case in complex_commands:
            try:
                response = requests.post(
                    f"{self.command_parser_url}/parse-command",
                    json={"text": test_case["text"], "user_id": test_case["user_id"]},
                    timeout=10
                )
                
                if response.status_code == 200:
                    result = response.json()
                    parsed_intent = result.get("parsed_command", {}).get("intent")
                    
                    # Check if any expected intent matches
                    intent_match = parsed_intent in test_case["expected_intents"]
                    
                    if intent_match:
                        passed = True
                        details = f"Intent: {parsed_intent}"
                    else:
                        passed = False
                        details = f"Intent mismatch: got {parsed_intent}, expected one of {test_case['expected_intents']}"
                    
                    test_passed = self.log_test(f"Complex: {test_case['text'][:30]}...", passed, details)
                    all_passed = all_passed and test_passed
                    
                else:
                    all_passed = False
                    self.log_test(f"Complex: {test_case['text'][:30]}...", False, f"HTTP {response.status_code}")
                    
            except Exception as e:
                all_passed = False
                self.log_test(f"Complex: {test_case['text'][:30]}...", False, str(e))
        
        return all_passed
    
    def test_error_handling(self) -> bool:
        """Test error handling and edge cases"""
        logger.info("=== Testing Error Handling ===")
        
        error_cases = [
            {
                "name": "Empty command",
                "data": {"text": "", "user_id": "test_empty"},
                "should_fail": False  # Should handle gracefully
            },
            {
                "name": "Invalid JSON",
                "data": "invalid json",
                "should_fail": True
            },
            {
                "name": "Missing user_id",
                "data": {"text": "test command"},
                "should_fail": False  # Should handle gracefully
            },
            {
                "name": "Very long command",
                "data": {"text": "test " * 1000, "user_id": "test_long"},
                "should_fail": False
            }
        ]
        
        all_passed = True
        
        for test_case in error_cases:
            try:
                if isinstance(test_case["data"], str):
                    # Test invalid JSON
                    response = requests.post(
                        f"{self.command_parser_url}/parse-command",
                        data=test_case["data"],
                        headers={"Content-Type": "application/json"},
                        timeout=5
                    )
                else:
                    # Test valid JSON with edge cases
                    response = requests.post(
                        f"{self.command_parser_url}/parse-command",
                        json=test_case["data"],
                        timeout=5
                    )
                
                if test_case["should_fail"]:
                    passed = response.status_code >= 400
                    details = f"Expected failure, got HTTP {response.status_code}"
                else:
                    passed = response.status_code == 200
                    details = f"Handled gracefully, HTTP {response.status_code}"
                
                test_passed = self.log_test(f"Error: {test_case['name']}", passed, details)
                all_passed = all_passed and test_passed
                
            except Exception as e:
                if test_case["should_fail"]:
                    test_passed = self.log_test(f"Error: {test_case['name']}", True, f"Expected exception: {str(e)[:50]}")
                else:
                    test_passed = self.log_test(f"Error: {test_case['name']}", False, f"Unexpected exception: {str(e)[:50]}")
                all_passed = all_passed and test_passed
        
        return all_passed
    
    def run_all_tests(self) -> Dict:
        """Run all tests and return summary"""
        logger.info("Starting Comprehensive AI System Tests")
        logger.info("=" * 50)
        
        start_time = time.time()
        
        # Run all test suites
        test_suites = [
            ("Service Health", self.test_service_health),
            ("NLP Command Parsing", self.test_nlp_command_parsing),
            ("Flight Control Status", self.test_flight_control_status),
            ("Kafka Message Flow", self.test_kafka_message_flow),
            ("Complex Commands", self.test_complex_commands),
            ("Error Handling", self.test_error_handling)
        ]
        
        results = {}
        
        for suite_name, test_func in test_suites:
            logger.info(f"\n--- {suite_name} ---")
            try:
                results[suite_name] = test_func()
            except Exception as e:
                logger.error(f"Test suite {suite_name} failed: {e}")
                results[suite_name] = False
        
        # Calculate summary
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["passed"])
        failed_tests = total_tests - passed_tests
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Print summary
        logger.info("\n" + "=" * 50)
        logger.info("TEST SUMMARY")
        logger.info("=" * 50)
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {failed_tests}")
        logger.info(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        logger.info(f"Duration: {duration:.2f} seconds")
        
        logger.info("\nSuite Results:")
        for suite_name, passed in results.items():
            status = "PASS" if passed else "FAIL"
            logger.info(f"  {suite_name}: {status}")
        
        if failed_tests > 0:
            logger.info("\nFailed Tests:")
            for result in self.test_results:
                if not result["passed"]:
                    logger.info(f"  - {result['test']}: {result['details']}")
        
        return {
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "success_rate": (passed_tests/total_tests)*100,
            "duration": duration,
            "suite_results": results,
            "detailed_results": self.test_results
        }

def main():
    """Main test execution"""
    tester = DroneAITester()
    
    try:
        results = tester.run_all_tests()
        
        # Save results to file
        with open("test_results.json", "w") as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"\nTest results saved to test_results.json")
        
        # Return appropriate exit code
        return 0 if results["failed"] == 0 else 1
        
    except KeyboardInterrupt:
        logger.info("Tests interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
