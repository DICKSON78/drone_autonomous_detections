# Enhanced Natural language processing for guided drone commands
import spacy
import json
import logging
from typing import Dict, List, Tuple

class AdvancedCommandProcessor:
    def __init__(self):
        """Initialize advanced NLP models for command interpretation"""
        try:
            # Load spaCy for NER and parsing
            self.nlp = spacy.load("en_core_web_sm")
            
            # Simple rule-based intent classification (fallback for transformers)
            self.intent_keywords = {
                "navigate": ["go", "fly", "move", "travel", "head"],
                "search": ["find", "search", "look", "detect", "scan"],
                "surveillance": ["monitor", "watch", "observe", "survey", "patrol"],
                "emergency_land": ["emergency", "land now", "crash", "abort"],
                "return_home": ["home", "return", "back", "base"],
                "hover": ["hover", "stay", "wait", "hold"],
                "track_object": ["track", "follow", "chase", "pursue"]
            }
            
            logging.info("Advanced NLP models loaded successfully")
        except Exception as e:
            logging.error(f"Failed to load NLP models: {e}")
            self.nlp = None
            self.intent_keywords = {}
    
    def extract_entities(self, command_text: str) -> Dict:
        """Extract entities from command using spaCy NER"""
        if not self.nlp:
            return {"locations": [], "objects": [], "actions": [], "modifiers": []}
        
        doc = self.nlp(command_text.lower())
        
        entities = {
            "locations": [],
            "objects": [],
            "actions": [],
            "modifiers": []
        }
        
        # Location mappings
        location_mappings = {
            "forest": {"lat": -1.2921, "lon": 36.8219, "type": "vegetation"},
            "lake": {"lat": -1.2850, "lon": 36.8300, "type": "water"},
            "field": {"lat": -1.3000, "lon": 36.8100, "type": "open"},
            "home": {"lat": -1.2920, "lon": 36.8200, "type": "base"},
            "building": {"lat": -1.2950, "lon": 36.8250, "type": "structure"},
            "road": {"lat": -1.2880, "lon": 36.8220, "type": "infrastructure"}
        }
        
        # Object mappings for YOLO detection
        object_mappings = {
            "person": "person",
            "car": "car", 
            "truck": "truck",
            "animal": "animal",
            "drone": "drone"
        }
        
        for token in doc:
            # Extract locations
            if token.text in location_mappings:
                entities["locations"].append({
                    "name": token.text,
                    "coords": location_mappings[token.text]
                })
            
            # Extract objects
            if token.text in object_mappings:
                entities["objects"].append({
                    "name": token.text,
                    "yolo_class": object_mappings[token.text]
                })
            
            # Extract action verbs
            if token.pos_ == "VERB":
                entities["actions"].append(token.lemma_)
        
        return entities
    
    def classify_intent(self, command_text: str) -> str:
        """Classify command intent using rule-based approach"""
        if not self.intent_keywords:
            return "navigate"  # Default fallback
        
        try:
            command_lower = command_text.lower()
            
            # Score each intent based on keyword matches
            intent_scores = {}
            for intent, keywords in self.intent_keywords.items():
                score = 0
                for keyword in keywords:
                    if keyword in command_lower:
                        score += 1
                intent_scores[intent] = score
            
            # Return intent with highest score
            if intent_scores:
                best_intent = max(intent_scores, key=intent_scores.get)
                if intent_scores[best_intent] > 0:
                    return best_intent
            
            return "navigate"  # Default fallback
        except Exception as e:
            logging.error(f"Intent classification failed: {e}")
            return "navigate"
    
    def parse_complex_command(self, command_text: str) -> Dict:
        """Parse complex guided language commands"""
        entities = self.extract_entities(command_text)
        intent = self.classify_intent(command_text)
        
        # Build comprehensive command structure
        parsed_command = {
            "original_command": command_text,
            "intent": intent,
            "entities": entities,
            "target_gps": None,
            "search_objects": [],
            "flight_parameters": {
                "altitude": 50.0,
                "speed": 10.0,
                "hover_time": 30.0
            },
            "constraints": [],
            "confidence": 0.8
        }
        
        # Set target GPS if location specified
        if entities["locations"]:
            parsed_command["target_gps"] = entities["locations"][0]["coords"]
            parsed_command["confidence"] += 0.1
        
        # Set objects for YOLO detection
        if entities["objects"]:
            parsed_command["search_objects"] = [obj["yolo_class"] for obj in entities["objects"]]
            parsed_command["confidence"] += 0.1
        
        # Adjust parameters based on intent
        if intent == "surveillance":
            parsed_command["flight_parameters"]["altitude"] = 100.0
            parsed_command["flight_parameters"]["speed"] = 5.0
        elif intent == "search":
            parsed_command["flight_parameters"]["altitude"] = 30.0
            parsed_command["flight_parameters"]["speed"] = 8.0
        elif intent == "emergency_land":
            parsed_command["flight_parameters"]["altitude"] = 0.0
            parsed_command["flight_parameters"]["speed"] = 2.0
        
        return parsed_command

# Global processor instance
command_processor = AdvancedCommandProcessor()
