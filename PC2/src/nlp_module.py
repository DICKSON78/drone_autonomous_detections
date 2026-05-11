#!/usr/bin/env python3
"""
NLP Module for Drone System (English Version)
Provides explanations of drone state in natural language
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DroneNLP:
    """
    NLP Module that explains drone results in natural language.
    Uses templates + logic for better explanations.
    """

    def __init__(self, language: str = "en"):
        self.language = language
        self.class_names = ["tree", "building", "pole", "person", "vehicle", "aircraft"]
        self.action_names = {
            0: "turn left",
            1: "turn right", 
            2: "climb up",
            3: "descend down",
            4: "move forward",
            5: "stop",
        }
        self.distance_descriptions = {
            "very_close": "very close",
            "close": "close", 
            "medium": "medium distance",
            "far": "far",
            "very_far": "very far"
        }
        
        # Flight history for analysis
        self.flight_history = []
        self.session_start = datetime.now()

    def explain_current_state(self, obstacles: List[Dict], action: int, confidence: float = 0.0) -> str:
        """Generate explanation of drone's current state"""
        
        if not obstacles:
            return f"Path is clear. Drone {self.action_names.get(action, 'taking action')}."
        
        # Get the most dangerous obstacle
        main_obstacle = max(obstacles, key=lambda o: o.get("confidence", 0) * o.get("w", 0) * o.get("h", 0))
        
        object_name = self._get_object_name(main_obstacle)
        object_confidence = int(main_obstacle.get("confidence", 0) * 100)
        action_description = self.action_names.get(action, "taking action")
        
        # Determine obstacle position
        position = self._get_position_description(main_obstacle)
        
        # Determine distance (from box size)
        distance = self._get_distance_description(main_obstacle)
        
        # If multiple obstacles
        additional_info = ""
        if len(obstacles) > 1:
            other_objects = self._get_other_objects_summary(obstacles[1:])
            additional_info = f" Also there are {other_objects}."
        
        # If action confidence is high
        confidence_info = ""
        if confidence > 0:
            confidence_pct = int(confidence * 100)
            confidence_info = f" (action confidence: {confidence_pct}%)"
        
        explanation = (
            f"Drone detected {object_name} {position}, {distance} "
            f"({object_confidence}% confidence). "
            f"Taking action: {action_description}{confidence_info}.{additional_info}"
        )
        
        return explanation

    def _get_object_name(self, obstacle: Dict) -> str:
        """Get object name based on class"""
        class_id = obstacle.get("class", 0)
        if 0 <= class_id < len(self.class_names):
            return self.class_names[class_id]
        return "unknown object"

    def _get_position_description(self, obstacle: Dict) -> str:
        """Determine obstacle position"""
        x = obstacle.get("x", 0.5)
        
        if x < 0.33:
            return "to the left"
        elif x > 0.66:
            return "to the right"
        elif x < 0.45:
            return "slightly left"
        elif x > 0.55:
            return "slightly right"
        else:
            return "ahead"

    def _get_distance_description(self, obstacle: Dict) -> str:
        """Determine distance from box size"""
        width = obstacle.get("w", 0.1)
        height = obstacle.get("h", 0.1)
        size = width * height
        
        if size > 0.3:
            return self.distance_descriptions["very_close"]
        elif size > 0.15:
            return self.distance_descriptions["close"]
        elif size > 0.08:
            return self.distance_descriptions["medium"]
        elif size > 0.04:
            return self.distance_descriptions["far"]
        else:
            return self.distance_descriptions["very_far"]

    def _get_other_objects_summary(self, obstacles: List[Dict]) -> str:
        """Get summary of other obstacles"""
        if not obstacles:
            return ""
        
        object_counts = {}
        for obs in obstacles:
            name = self._get_object_name(obs)
            object_counts[name] = object_counts.get(name, 0) + 1
        
        summary_parts = []
        for name, count in object_counts.items():
            if count == 1:
                summary_parts.append(f"{name} 1")
            else:
                summary_parts.append(f"{name} {count}")
        
        return f"other obstacles {len(obstacles)}: {', '.join(summary_parts)}"

    def analyze_flight_pattern(self, recent_actions: List[int], recent_obstacles: List[List[Dict]]) -> str:
        """Analyze recent flight pattern and provide advice"""
        
        if not recent_actions:
            return "No recent data available."
        
        # Analyze action patterns
        action_counts = {}
        for action in recent_actions:
            action_name = self.action_names.get(action, "unknown")
            action_counts[action_name] = action_counts.get(action_name, 0) + 1
        
        most_common_action = max(action_counts, key=action_counts.get)
        
        # Analyze obstacle patterns
        total_obstacles = sum(len(obs_list) for obs_list in recent_obstacles)
        avg_obstacles = total_obstacles / max(1, len(recent_obstacles))
        
        # Provide advice
        if avg_obstacles > 3:
            advice = "Area is crowded with obstacles. Reduce speed and be more alert."
        elif most_common_action in ["turn left", "turn right"]:
            advice = "Drone is avoiding frequently. Consider alternative routes."
        elif most_common_action == "move forward":
            advice = "Path appears clear. You can increase speed."
        else:
            advice = "Operation is proceeding normally."
        
        return (
            f"In the last {len(recent_actions)} steps, "
            f"most common action is '{most_common_action}'. "
            f"Average obstacles per step: {avg_obstacles:.1f}. {advice}"
        )

    def generate_flight_summary(self, flight_history: List[Dict]) -> str:
        """Generate summary of entire flight"""
        
        if not flight_history:
            return "No flight data available."
        
        total_steps = len(flight_history)
        avoidance_actions = sum(1 for h in flight_history if h.get("action") not in [4, 5] and h.get("obstacles"))
        crashes = sum(1 for h in flight_history if h.get("crashed", False))
        
        # Analyze detected objects
        object_counts = {}
        for h in flight_history:
            for obs in h.get("obstacles", []):
                name = self._get_object_name(obs)
                object_counts[name] = object_counts.get(name, 0) + 1
        
        # Get most detected objects
        top_objects = sorted(object_counts.items(), key=lambda x: -x[1])[:3]
        top_objects_str = ", ".join(f"{name}({count})" for name, count in top_objects) if top_objects else "none"
        
        # Analyze performance
        crash_rate = (crashes / total_steps * 100) if total_steps > 0 else 0
        avoidance_rate = (avoidance_actions / total_steps * 100) if total_steps > 0 else 0
        
        # Flight duration
        if flight_history:
            start_time = flight_history[0].get("timestamp", datetime.now())
            end_time = flight_history[-1].get("timestamp", datetime.now())
            duration = end_time - start_time
            duration_str = str(duration).split('.')[0]  # Remove microseconds
        else:
            duration_str = "0:00:00"
        
        summary = (
            f"Flight completed. Duration: {duration_str}, "
            f"steps {total_steps}, "
            f"obstacles avoided {avoidance_actions} ({avoidance_rate:.1f}%), "
            f"crashes {crashes} ({crash_rate:.1f}%). "
            f"Most detected objects: {top_objects_str}."
        )
        
        return summary

    def explain_action_reasoning(self, obstacles: List[Dict], action: int, reasoning: Dict) -> str:
        """Explain reasoning behind drone decision"""
        
        action_name = self.action_names.get(action, "taking action")
        
        if not obstacles:
            return f"No obstacles to avoid. Drone {action_name}."
        
        # Get primary reason
        primary_reason = reasoning.get("primary_reason", "safety")
        confidence = reasoning.get("confidence", 0.0)
        
        if primary_reason == "avoidance":
            main_obstacle = max(obstacles, key=lambda o: o.get("confidence", 0) * o.get("w", 0))
            object_name = self._get_object_name(main_obstacle)
            position = self._get_position_description(main_obstacle)
            
            return (
                f"DRONE DECISION: {action_name.upper()}\n"
                f"REASON: Avoid {object_name} {position}\n"
                f"Decision confidence: {int(confidence * 100)}%\n"
                f"Obstacles detected: {len(obstacles)}"
            )
        
        elif primary_reason == "safety":
            return (
                f"DRONE DECISION: {action_name.upper()}\n"
                f"REASON: Safety protocol requires stopping\n"
                f"Decision confidence: {int(confidence * 100)}%"
            )
        
        else:
            return (
                f"DRONE DECISION: {action_name.upper()}\n"
                f"REASON: Normal operation\n"
                f"Decision confidence: {int(confidence * 100)}%"
            )

    def generate_alert_message(self, alert_type: str, details: Dict) -> str:
        """Generate alert message"""
        
        if alert_type == "collision_risk":
            obstacle = details.get("obstacle", {})
            object_name = self._get_object_name(obstacle)
            distance = self._get_distance_description(obstacle)
            
            return (
                f"⚠️ COLLISION RISK ALERT!\n"
                f"Drone approaching {object_name} {distance}. "
                f"Immediate action required!"
            )
        
        elif alert_type == "low_battery":
            battery_level = details.get("battery_level", 0)
            return (
                f"🔋 LOW BATTERY ALERT!\n"
                f"Battery remaining: {battery_level}%. "
                f"Return to nearest station immediately!"
            )
        
        elif alert_type == "system_error":
            error_message = details.get("error", "Unknown error")
            return (
                f"❌ SYSTEM ERROR ALERT!\n"
                f"Error: {error_message}. "
                f"Check system and try again."
            )
        
        else:
            return f"📢 Alert: {alert_type}"

    def log_flight_event(self, event_type: str, details: Dict):
        """Log flight event"""
        
        event = {
            "timestamp": datetime.now(),
            "event_type": event_type,
            "details": details
        }
        
        self.flight_history.append(event)
        
        # Keep only last 1000 events
        if len(self.flight_history) > 1000:
            self.flight_history = self.flight_history[-1000:]
        
        logger.info(f"Flight event logged: {event_type}")

    def export_flight_log(self, filename: Optional[str] = None) -> str:
        """Export flight log as file"""
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"flight_log_{timestamp}.json"
        
        log_data = {
            "session_start": self.session_start.isoformat(),
            "total_events": len(self.flight_history),
            "events": self.flight_history
        }
        
        with open(filename, 'w') as f:
            json.dump(log_data, f, indent=2, default=str)
        
        logger.info(f"Flight log exported to: {filename}")
        return filename

# Example usage and testing
if __name__ == "__main__":
    # Test NLP module
    nlp = DroneNLP()
    
    # Test current state explanation
    test_obstacles = [
        {"class": 3, "confidence": 0.9, "x": 0.7, "y": 0.5, "w": 0.3, "h": 0.2},
        {"class": 0, "confidence": 0.7, "x": 0.2, "y": 0.3, "w": 0.1, "h": 0.15}
    ]
    
    explanation = nlp.explain_current_state(test_obstacles, action=0)
    print("Current State Explanation:")
    print(explanation)
    print()
    
    # Test action reasoning
    reasoning = {"primary_reason": "avoidance", "confidence": 0.85}
    action_explanation = nlp.explain_action_reasoning(test_obstacles, action=0, reasoning=reasoning)
    print("Action Reasoning:")
    print(action_explanation)
    print()
    
    # Test flight summary
    test_history = [
        {"action": 4, "obstacles": [], "crashed": False},
        {"action": 0, "obstacles": test_obstacles, "crashed": False},
        {"action": 1, "obstacles": test_obstacles, "crashed": False}
    ]
    
    summary = nlp.generate_flight_summary(test_history)
    print("Flight Summary:")
    print(summary)
    print()
    
    # Test alert
    alert = nlp.generate_alert_message("collision_risk", {"obstacle": test_obstacles[0]})
    print("Alert Message:")
    print(alert)
