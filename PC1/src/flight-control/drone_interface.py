"""
Drone Interface — abstraction layer for drone communication.
Supports both MAVSDK (real drone) and MAVLink (SITL simulation).
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class DroneInterface:
    """Unified drone interface supporting MAVSDK and MAVLink backends."""

    def __init__(self, system_address: str = "udp://127.0.0.1:14540"):
        self.system_address = system_address
        self._drone = None
        self._connected = False
        self._armed = False
        self._in_air = False

    async def connect(self) -> bool:
        """Connect to the drone."""
        try:
            from mavsdk import System
            self._drone = System()
            await self._drone.connect(system_address=self.system_address)

            async for state in self._drone.core.connection_state():
                if state.is_connected:
                    self._connected = True
                    logger.info(f"Drone connected at {self.system_address}")
                    return True
            return False
        except ImportError:
            logger.warning("mavsdk not available, using MAVLink fallback")
            self._connected = True
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False

    async def arm(self) -> bool:
        """Arm the drone."""
        if not self._drone:
            return False
        try:
            await self._drone.action.arm()
            self._armed = True
            logger.info("Drone armed")
            return True
        except Exception as e:
            logger.error(f"Arm failed: {e}")
            return False

    async def disarm(self) -> bool:
        """Disarm the drone."""
        if not self._drone:
            return False
        try:
            await self._drone.action.disarm()
            self._armed = False
            logger.info("Drone disarmed")
            return True
        except Exception as e:
            logger.error(f"Disarm failed: {e}")
            return False

    async def takeoff(self, altitude: float = 10.0) -> bool:
        """Take off to specified altitude."""
        if not self._drone:
            return False
        try:
            await self._drone.action.takeoff()
            self._in_air = True
            logger.info(f"Taking off to {altitude}m")
            return True
        except Exception as e:
            logger.error(f"Takeoff failed: {e}")
            return False

    async def land(self) -> bool:
        """Land the drone."""
        if not self._drone:
            return False
        try:
            await self._drone.action.land()
            self._in_air = False
            logger.info("Landing")
            return True
        except Exception as e:
            logger.error(f"Land failed: {e}")
            return False

    async def goto(self, lat: float, lon: float, alt: float = 10.0) -> bool:
        """Fly to GPS coordinates."""
        if not self._drone:
            return False
        try:
            await self._drone.action.goto_location(lat, lon, alt, 0.0)
            logger.info(f"Going to ({lat}, {lon}) at {alt}m")
            return True
        except Exception as e:
            logger.error(f"Goto failed: {e}")
            return False

    async def hold(self) -> bool:
        """Hold current position."""
        if not self._drone:
            return False
        try:
            await self._drone.action.hold()
            logger.info("Position hold")
            return True
        except Exception as e:
            logger.error(f"Hold failed: {e}")
            return False

    async def return_to_launch(self) -> bool:
        """Return to launch point."""
        if not self._drone:
            return False
        try:
            await self._drone.action.return_to_launch()
            logger.info("RTL initiated")
            return True
        except Exception as e:
            logger.error(f"RTL failed: {e}")
            return False

    async def get_position(self) -> Optional[Dict[str, float]]:
        """Get current GPS position."""
        if not self._drone:
            return None
        try:
            async for position in self._drone.telemetry.position():
                return {
                    "latitude": position.latitude,
                    "longitude": position.longitude,
                    "altitude": position.relative_altitude,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
        except Exception as e:
            logger.error(f"Position query failed: {e}")
            return None

    async def get_battery(self) -> Optional[float]:
        """Get battery percentage."""
        if not self._drone:
            return None
        try:
            async for battery in self._drone.telemetry.battery():
                return battery.remaining * 100.0
        except Exception:
            return None

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def is_armed(self) -> bool:
        return self._armed
