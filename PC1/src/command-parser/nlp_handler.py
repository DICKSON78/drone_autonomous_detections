import spacy
import json
import os
import logging

logger = logging.getLogger(__name__)

class NLPHandler:
    """
    Handles drone command parsing using spaCy NER and keyword intent classification.
    Based on the user's provided NLP training code.
    """
    
    def __init__(self, model_path: str = "/app/models/nlp/command_model", 
                 intent_path: str = "/app/models/nlp/intent_keywords.json"):
        self.model_path = model_path
        self.intent_path = intent_path
        self.nlp = None
        self.keyword_map = {}
        
        self.load_models()

    def load_models(self):
        """Load spaCy model and intent keywords"""
        try:
            if os.path.exists(self.model_path):
                self.nlp = spacy.load(self.model_path)
                logger.info(f"NLP NER model loaded from {self.model_path}")
            else:
                logger.warning(f"NLP model not found at {self.model_path}. Using fallback parser.")
                self.nlp = spacy.blank("en")
            
            if os.path.exists(self.intent_path):
                with open(self.intent_path, "r") as f:
                    self.keyword_map = json.load(f)
                logger.info(f"Intent keyword map loaded from {self.intent_path}")
            else:
                logger.warning(f"Intent keywords not found at {self.intent_path}")
        except Exception as e:
            logger.error(f"Error loading NLP models: {e}")

    def predict_intent(self, text: str) -> str:
        """Predict intent based on keyword voting (from user code)"""
        if not self.keyword_map:
            # Simple fallback
            text_lower = text.lower()
            if "land" in text_lower: return "land"
            if "takeoff" in text_lower or "take off" in text_lower: return "takeoff"
            if "return" in text_lower or "rtl" in text_lower: return "return"
            return "goto"

        scores = {}
        for word in text.lower().split():
            if word in self.keyword_map:
                for intent, count in self.keyword_map[word].items():
                    scores[intent] = scores.get(intent, 0) + count
        if not scores:
            return "goto" # Default
        return max(scores, key=scores.get)

    def parse(self, text: str) -> dict:
        """
        Full inference: text -> structured drone command.
        """
        doc = self.nlp(text)
        intent = self.predict_intent(text)
        entities = {ent.label_: ent.text for ent in doc.ents}

        # Coordinate mapping for Dodoma
        locations = {
            'dodoma': { 'lat': -6.1630, 'lon': 35.7516 },
            'bunge': { 'lat': -6.1630, 'lon': 35.7516 },
            'forest': { 'lat': -6.1650, 'lon': 35.7550 },
            'river': { 'lat': -6.1620, 'lon': 35.7500 },
            'base': { 'lat': -6.1630, 'lon': 35.7516 },
            'home': { 'lat': -6.1630, 'lon': 35.7516 }
        }

        location_name = entities.get("LOCATION", "home").lower()
        target_gps = locations.get(location_name, locations['home'])

        command = {
            "command_id": f"cmd_{int(os.times()[4])}",
            "type": intent,
            "raw_text": text,
            "target_gps": target_gps,
            "altitude": 10.0,
            "entities": entities
        }
        
        if "TARGET" in entities:
            command["target_object"] = entities["TARGET"]
        
        return command
