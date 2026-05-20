"""
Command Executor — executes parsed flight commands on the drone.
Handles command validation, safety checks, and execution sequencing.
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class CommandExecutor:
    """Executes validated flight commands with safety checks."""

    SAFETY_LIMITS = {
        "max_altitude": 120.0,
        "min_altitude": 0.5,
        "max_speed": 15.0,
        "geofence_radius": 500.0,
        "battery_min": 15.0,
    }

    def __init__(self, drone_interface=None):
        self.drone = drone_interface
        self._home_lat = -6.1630
        self._home_lon = 35.7516
        self._executing = False

    def set_home(self, lat: float, lon: float):
        self._home_lat = lat
        self._home_lon = lon

    def _validate_command(self, command: Dict[str, Any]) -> tuple:
        """Validate command against safety limits. Returns (valid, error_msg)."""
        cmd_type = command.get("type", "").lower()
        valid_types = {"takeoff", "land", "goto", "return", "hover", "forward", "disarm"}

        if cmd_type not in valid_types:
            return False, f"Unknown command type: {cmd_type}"

        altitude = command.get("altitude", 10.0)
        if altitude > self.SAFETY_LIMITS["max_altitude"]:
            return False, f"Altitude {altitude}m exceeds max {self.SAFETY_LIMITS['max_altitude']}m"
        if altitude < self.SAFETY_LIMITS["min_altitude"]:
            return False, f"Altitude {altitude}m below min {self.SAFETY_LIMITS['min_altitude']}m"

        target_gps = command.get("target_gps")
        if target_gps and cmd_type == "goto":
            dist = ((target_gps["lat"] - self._home_lat)**2 +
                    (target_gps["lon"] - self._home_lon)**2)**0.5 * 111000
            if dist > self.SAFETY_LIMITS["geofence_radius"]:
                return False, f"Target {dist:.0f}m exceeds geofence {self.SAFETY_LIMITS['geofence_radius']}m"

        return True, None

    async def execute(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a validated command. Returns result dict."""
        valid, error = self._validate_command(command)
        if not valid:
            logger.warning(f"Command rejected: {error}")
            return {"status": "rejected", "error": error, "command_id": command.get("command_id")}

        self._executing = True
        cmd_type = command.get("type", "").lower()
        result = {"command_id": command.get("command_id"), "type": cmd_type}

        try:
            if cmd_type == "takeoff":
                alt = command.get("altitude", 10.0)
                if self.drone:
                    await self.drone.arm()
                    await asyncio.sleep(1)
                    await self.drone.takeoff(alt)
                result["status"] = "executing"
                result["altitude"] = alt

            elif cmd_type == "land":
                if self.drone:
                    await self.drone.land()
                result["status"] = "executing"

            elif cmd_type == "goto":
                gps = command.get("target_gps", {})
                alt = command.get("altitude", 10.0)
                if self.drone:
                    await self.drone.goto(gps.get("lat", 0), gps.get("lon", 0), alt)
                result["status"] = "executing"
                result["target"] = gps

            elif cmd_type == "return":
                if self.drone:
                    await self.drone.return_to_launch()
                result["status"] = "executing"

            elif cmd_type == "hover":
                if self.drone:
                    await self.drone.hold()
                result["status"] = "executing"

            elif cmd_type == "disarm":
                if self.drone:
                    await self.drone.disarm()
                result["status"] = "executing"

            else:
                result["status"] = "unknown"

        except Exception as e:
            logger.error(f"Execution error: {e}")
            result["status"] = "failed"
            result["error"] = str(e)

        result["timestamp"] = datetime.now(timezone.utc).isoformat()
        self._executing = False
        return result

    @property
    def is_executing(self) -> bool:
        return self._executing
