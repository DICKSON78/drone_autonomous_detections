"""
Data models and schemas for command parsing.
Pydantic models for request/response validation across PC1 services.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class CommandRequest(BaseModel):
    """Raw text command from user or upstream service."""
    text: str = Field(..., min_length=1, max_length=500, description="Natural language command")
    source: Optional[str] = Field(None, description="Origin of the command (web, api, voice)")


class ParsedCommand(BaseModel):
    """Structured command after NLP parsing."""
    command_id: str
    type: str = Field(..., description="Intent: takeoff, land, goto, return, hover, forward")
    raw_text: str
    target_gps: Optional[Dict[str, float]] = Field(None, description="{'lat': float, 'lon': float}")
    altitude: Optional[float] = Field(10.0, ge=0, le=120)
    distance: Optional[float] = Field(None, ge=0)
    direction: Optional[str] = None
    location: Optional[str] = None
    entities: Dict[str, str] = {}
    confidence: float = Field(0.5, ge=0, le=1)
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class FlightStatus(BaseModel):
    """Current drone flight status."""
    connected: bool = False
    armed: bool = False
    in_air: bool = False
    latitude: float = 0.0
    longitude: float = 0.0
    altitude: float = 0.0
    battery_pct: float = 0.0
    heading: float = 0.0
    mode: str = "UNKNOWN"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class TelemetryPoint(BaseModel):
    """Single telemetry data point for Kafka publishing."""
    latitude: float
    longitude: float
    altitude: float
    battery_pct: Optional[float] = None
    heading: Optional[float] = None
    speed: Optional[float] = None
    gps_fix: Optional[int] = None
    satellites: Optional[int] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class CommandResponse(BaseModel):
    """API response for /parse endpoint."""
    success: bool
    command: Optional[ParsedCommand] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    version: str = "1.0.0"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ── Kafka topic definitions ──
KAFKA_TOPICS = {
    "commands_flight": "drone.commands.flight",
    "commands_parsed": "drone.commands.parsed",
    "telemetry_gps": "drone.telemetry.gps",
    "telemetry_full": "drone.telemetry.full",
    "status_flight": "drone.status.flight",
    "navigation_decisions": "drone.navigation.decisions",
    "detections": "drone.detections",
    "feedback_events": "drone.feedback.events",
}
