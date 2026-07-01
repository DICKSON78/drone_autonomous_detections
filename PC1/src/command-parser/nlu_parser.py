"""
NLU Parser — rule-based natural language understanding for drone commands.

No ML, no spaCy, no training. Uses regex keyword matching for intent
classification, regex for altitude/number extraction, and a JSON gazetteer
for named-location lookup. Designed to be callable as a single function:

    parse_command("fly to forest at 25 meters")
    -> {"success": True, "intent": "goto", "altitude": 25.0, ...}
"""

import json
import logging
import os
import re
import time
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_GAZETTEER = os.path.join(os.path.dirname(__file__), "gazetteer.json")

# ── Intent keyword rules ─────────────────────────────────────────────────────
# Each intent has a list of regex patterns.  The first intent whose *cumulative
# match score* exceeds *threshold* wins (see _score_intents below).

_INTENT_RULES: dict[str, list[str]] = {
    "takeoff": [
        r"\btake\s*off\b",
        r"\blaunch\b",
        r"\bascend\b",
        r"\bclimb\b",
        r"\bgo\s*up\b",
    ],
    "land": [
        r"\bland(?:ing)?\b",
        r"\bdescend\b",
        r"\btouch\s*down\b",
        r"\bcome\s*down\b",
        r"\bgo\s*down\b",
    ],
    "goto": [
        r"\bgo\s*to\b",
        r"\bfly\s*to\b",
        r"\bnavigate\s*to\b",
        r"\bmove\s*to\b",
        r"\bhead\s*to\b",
        r"\bproceed\s*to\b",
        r"\btake\s*me\s*to\b",
    ],
    "rtl": [
        r"\breturn\s+(?:home|to\s+launch|to\s+base)\b",
        r"\brtl\b",
        r"\bgo\s+home\b",
        r"\bcome\s+back\b",
        r"\bhead\s+home\b",
        r"\breturn\s+to\s+landing\b",
    ],
    "hover": [
        r"\bhover\b",
        r"\bhold\s+(?:position|still)\b",
        r"\bstop\b",
        r"\bpause\b",
        r"\bstay\b",
    ],
    "arm": [
        r"\barm\b",
    ],
    "disarm": [
        r"\bdisarm\b",
        r"\bshut\s*down\b",
        r"\bpower\s*off\b",
    ],
}

_ALTITUDE_PATTERNS = [
    re.compile(r"(\d+(?:\.\d+)?)\s*(?:m(?:eters?)?)\b", re.IGNORECASE),
    re.compile(r"(?:altitude|alt|height)\s*(?:of\s*)?(\d+(?:\.\d+)?)", re.IGNORECASE),
    re.compile(r"(?:to|at)\s*(\d+(?:\.\d+)?)\s*(?:m(?:eters?)?|meters)", re.IGNORECASE),
]

_RAW_NUMBER = re.compile(r"\b(\d+(?:\.\d+)?)\b")

_GPS_PATTERN = re.compile(
    r"([+-]?\d+\.\d+)\s*[, ]\s*([+-]?\d+\.\d+)"
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def _load_gazetteer(path: str | None = None) -> dict[str, dict[str, float]]:
    path = path or _DEFAULT_GAZETTEER
    try:
        with open(path) as f:
            data = json.load(f)
        locs: dict[str, dict[str, float]] = data.get("locations", {})
        logger.info("Gazetteer loaded: %d locations from %s", len(locs), path)
        return locs
    except Exception as exc:
        logger.warning("Could not load gazetteer from %s: %s", path, exc)
        return {}


def _score_intents(text: str) -> list[tuple[str, int]]:
    """Return list of (intent, match_count) sorted descending by count."""
    lower = text.lower()
    scores: list[tuple[str, int]] = []
    for intent, patterns in _INTENT_RULES.items():
        count = 0
        for pat in patterns:
            if re.search(pat, lower):
                count += 1
        if count > 0:
            scores.append((intent, count))
    scores.sort(key=lambda x: -x[1])
    return scores


def _extract_altitude(text: str) -> float | None:
    for pat in _ALTITUDE_PATTERNS:
        m = pat.search(text)
        if m:
            return float(m.group(1))

    # Bare number preceded by altitude-related keywords
    lower = text.lower()
    for kw in ("altitude", "alt", "height", "climb", "descend", "to", "at"):
        idx = lower.find(kw)
        if idx != -1:
            after = lower[idx + len(kw):]
            m = _RAW_NUMBER.search(after)
            if m:
                return float(m.group(1))
    return None


def _resolve_location(text: str, gazetteer: dict) -> dict | None:
    """Try to find a known location name in *text*.

    Returns the gazetteer entry dict or *None*.
    """
    lower = text.lower()
    for name, entry in gazetteer.items():
        if name in lower:
            return entry

    # Fallback: inline GPS coordinates.
    m = _GPS_PATTERN.search(text)
    if m:
        return {"lat": float(m.group(1)), "lon": float(m.group(2)), "alt": 15.0}
    return None


# ── Public API ────────────────────────────────────────────────────────────────


def parse_command(
    text: str,
    gazetteer_path: str | None = None,
) -> dict[str, Any]:
    """Parse a free-text drone command into a structured result.

    Returns
    -------
    dict with keys:
        success      — bool
        intent       — str (one of the recognised intents or ``"unknown"``)
        command_id   — str
        raw_text     — str (original input)
        altitude     — float | None
        location     — str | None (matched location name, if any)
        target_gps   — dict | None  (``{"lat": …, "lon": …}``)
        reason       — str (helpful message, especially when *success* is False)
        confidence   — float (0-1, heuristic)
    """
    text = text.strip()
    if not text:
        return {
            "success": False,
            "intent": "unknown",
            "command_id": "",
            "raw_text": text,
            "altitude": None,
            "location": None,
            "target_gps": None,
            "reason": "Empty command — please say something like 'take off', 'land', or 'fly to forest'.",
            "confidence": 0.0,
        }

    gazetteer = _load_gazetteer(gazetteer_path)
    scores = _score_intents(text)

    if not scores:
        return {
            "success": False,
            "intent": "unknown",
            "command_id": "",
            "raw_text": text,
            "altitude": None,
            "location": None,
            "target_gps": None,
            "reason": (
                f"Sorry, I didn't understand \"{text}\". "
                "Try: takeoff, land, goto [location], rtl (return to launch), "
                "hover, arm, or disarm."
            ),
            "confidence": 0.0,
        }

    intent = scores[0][0]
    match_count = scores[0][1]
    confidence = min(1.0, 0.5 + 0.15 * match_count)

    altitude = _extract_altitude(text)
    location_entry = _resolve_location(text, gazetteer)

    location_name = None
    target_gps = None
    if location_entry:
        for name, entry in gazetteer.items():
            if name in text.lower():
                location_name = name
                break
        if location_name is None:
            location_name = "custom"
        target_gps = {
            "lat": location_entry["lat"],
            "lon": location_entry["lon"],
        }

    # Default altitude per intent
    if altitude is None:
        if intent == "takeoff":
            altitude = 10.0
        elif intent == "goto":
            altitude = location_entry["alt"] if location_entry else 15.0
        elif intent == "rtl":
            altitude = 10.0
        else:
            altitude = None

    command_id = f"cmd_{int(time.time() * 1000)}"

    return {
        "success": True,
        "intent": intent,
        "command_id": command_id,
        "raw_text": text,
        "altitude": altitude,
        "location": location_name,
        "target_gps": target_gps,
        "reason": "",
        "confidence": round(confidence, 2),
    }
