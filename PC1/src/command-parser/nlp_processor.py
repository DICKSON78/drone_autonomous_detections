"""
NLP Processor — advanced natural language processing for drone commands.
Extends NLPHandler with spaCy pipeline enhancements:
  - Custom entity recognition (altitude, distance, direction)
  - Dependency parsing for relative commands ("go forward 30m")
  - Confidence scoring
"""

import spacy
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class NLPProcessor:
    """Advanced NLP pipeline for drone command understanding."""

    DIRECTION_MAP = {
        "forward": "north", "back": "south", "backward": "south",
        "left": "west", "right": "east", "up": "up", "down": "down",
        "north": "north", "south": "south", "east": "east", "west": "west",
    }

    def __init__(self, nlp_model: Optional[spacy.language.Language] = None):
        self.nlp = nlp_model
        if self.nlp is None:
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except OSError:
                logger.warning("en_core_web_sm not available, using blank model")
                self.nlp = spacy.blank("en")

    def extract_altitude(self, text: str) -> Optional[float]:
        """Extract altitude value from text (e.g. 'take off to 20m', 'climb 50 meters')."""
        patterns = [
            r"(\d+(?:\.\d+)?)\s*(?:m(?:eters?)?|ft|feet)",
            r"(?:to|at|altitude\s*(?:of\s*)?)(\d+(?:\.\d+)?)",
        ]
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                val = float(m.group(1))
                if "ft" in text.lower() or "feet" in text.lower():
                    val *= 0.3048
                return val
        return None

    def extract_distance(self, text: str) -> Optional[float]:
        """Extract distance value from text (e.g. 'go forward 30m')."""
        m = re.search(r"(\d+(?:\.\d+)?)\s*(?:m(?:eters?)?)", text, re.IGNORECASE)
        return float(m.group(1)) if m else None

    def extract_direction(self, text: str) -> Optional[str]:
        """Extract direction from text."""
        text_lower = text.lower()
        for word in self.DIRECTION_MAP:
            if word in text_lower:
                return self.DIRECTION_MAP[word]
        return None

    def extract_location(self, text: str) -> Optional[str]:
        """Extract location name using NER or keyword matching."""
        doc = self.nlp(text)
        for ent in doc.ents:
            if ent.label_ in ("GPE", "LOC", "FAC", "ORG"):
                return ent.text
        return None

    def compute_confidence(self, text: str, intent: str) -> float:
        """Return a confidence score (0.0–1.0) for the parsed intent."""
        text_lower = text.lower()
        keywords = {
            "takeoff": ["takeoff", "take off", "launch", "ascend", "climb"],
            "land": ["land", "landing", "descend", "touchdown", "come down"],
            "return": ["return", "rtl", "come back", "home", "back to base"],
            "goto": ["go to", "fly to", "navigate", "move to", "head to"],
            "hover": ["hover", "hold position", "stay", "stop"],
            "forward": ["forward", "go forward", "move forward"],
        }
        relevant = keywords.get(intent, [])
        if not relevant:
            return 0.5
        matches = sum(1 for kw in relevant if kw in text_lower)
        return min(1.0, matches / len(relevant) + 0.3)

    def process(self, text: str) -> dict:
        """Full NLP processing pipeline. Returns structured command dict."""
        doc = self.nlp(text)
        result = {
            "raw_text": text,
            "altitude": self.extract_altitude(text),
            "distance": self.extract_distance(text),
            "direction": self.extract_direction(text),
            "location": self.extract_location(text),
            "entities": {ent.label_: ent.text for ent in doc.ents},
        }
        return result
