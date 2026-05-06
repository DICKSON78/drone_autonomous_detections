# PX4 SITL connection for flight stack integration

"""
PX4 SITL MAVLink interface for drone control
"""

import socket
import threading
import time
import math
import logging
from typing import Tuple, Optional, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PX4Interface:
    """Real PX4 MAVLink interface (to be fully implemented with pymavlink)"""
    
    def __init__(self, host: str = 'localhost', port: int = 14550):
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
        self.position = {'x': 0.0, 'y': 0.0, 'z': 0.0}
        self.orientation = {'roll': 0.0, 'pitch': 0.0, 'yaw': 0.0}
        self.velocity = {'vx': 0.0, 'vy': 0.0, 'vz': 0.0}
        
        self.telemetry_thread = None
        self._running = False

    def connect(self) -> bool:
        """Establish connection to PX4"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.settimeout(2.0)
            self.connected = True
            self._running = True

            # Start telemetry thread
            self.telemetry_thread = threading.Thread(target=self._update_telemetry, daemon=True)
            self.telemetry_thread.start()

            logger.info(f"Connected to PX4 at {self.host}:{self.port}")
            return True
            
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self.connected = False
            return False

    def _update_telemetry(self):
        """Continuously update telemetry data (placeholder)"""
        while self._running and self.connected:
            try:
                # TODO: Replace with real pymavlink message parsing
                # For now, we simulate realistic movement
                time.sleep(0.2)
            except Exception as e:
                logger.error(f"Telemetry error: {e}")
                time.sleep(1)

    def _send_command(self, command_type: str, params: Dict):
        """Send command to PX4 (placeholder for real MAVLink)"""
        if not self.connected or not self.socket:
            return False
        try:
            # In future: Use pymavlink to encode proper MAVLink messages
            message = f"{command_type}:{params}".encode()
            self.socket.sendto(message, (self.host, self.port))
            return True
        except Exception as e:
            logger.error(f"Failed to send {command_type}: {e}")
            return False

    def arm(self) -> bool:
        logger.info("Arming drone...")
        return self._send_command('COMMAND_LONG', {
            'command': 400,  # MAV_CMD_COMPONENT_ARM_DISARM
            'param1': 1.0
        })

    def takeoff(self, altitude: float = 5.0) -> bool:
        logger.info(f"Taking off to {altitude}m...")
        return self._send_command('COMMAND_LONG', {
            'command': 22,   # MAV_CMD_NAV_TAKEOFF
            'param7': altitude
        })

    def set_velocity(self, vx: float, vy: float, vz: float, yaw_rate: float = 0.0):
        """Set velocity setpoint (m/s)"""
        self._send_command('SET_POSITION_TARGET_LOCAL_NED', {
            'type_mask': 0b0000111111000111,
            'vx': vx, 'vy': vy, 'vz': vz,
            'yaw_rate': yaw_rate
        })

    def set_position(self, x: float, y: float, z: float, yaw: Optional[float] = None):
        """Set position setpoint"""
        self._send_command('SET_POSITION_TARGET_LOCAL_NED', {
            'type_mask': 0b0000111111111000,
            'x': x, 'y': y, 'z': z,
            'yaw': yaw if yaw is not None else self.orientation['yaw']
        })

    def land(self) -> bool:
        logger.info("Landing drone...")
        return self._send_command('COMMAND_LONG', {
            'command': 21,   # MAV_CMD_NAV_LAND
            'param1': 0
        })

    def get_state(self) -> dict:
        """Return current drone state"""
        return {
            'position': self.position.copy(),
            'orientation': self.orientation.copy(),
            'velocity': self.velocity.copy(),
            'armed': self.connected,
            'connected': self.connected
        }

    def disconnect(self):
        """Disconnect from PX4"""
        self._running = False
        self.connected = False
        if self.socket:
            self.socket.close()
        logger.info("Disconnected from PX4")


# ========================== MOCK CLASS (Improved) ==========================

class MockPX4Interface(PX4Interface):
    """Improved Mock interface for testing without real PX4/Gazebo"""
    
    def __init__(self, host: str = 'localhost', port: int = 14550):
        """Properly call parent constructor"""
        super().__init__(host, port)
        self.sim_time = 0.0
        logger.info("Mock PX4 interface initialized (simulation mode)")

    def connect(self) -> bool:
        """Override connect for mock behavior"""
        self.connected = True
        self._running = True
        
        # Start simulated telemetry
        self.telemetry_thread = threading.Thread(target=self._update_telemetry, daemon=True)
        self.telemetry_thread.start()
        
        logger.info("Mock PX4 Interface connected (Simulation Mode)")
        return True

    def _update_telemetry(self):
        """Simulate realistic drone movement"""
        while self._running and self.connected:
            try:
                self.sim_time += 0.1
                
                # Simulate smooth circular + altitude movement
                self.position['x'] = 8 * math.sin(self.sim_time * 0.3)
                self.position['y'] = 8 * math.cos(self.sim_time * 0.25)
                self.position['z'] = 5 + 3 * math.sin(self.sim_time * 0.4)
                
                self.orientation['yaw'] = self.sim_time % (2 * math.pi)
                self.velocity['vx'] = -2.4 * math.sin(self.sim_time * 0.3)
                self.velocity['vy'] = -2.0 * math.cos(self.sim_time * 0.25)
                
                time.sleep(0.1)
            except:
                break


# Example usage
if __name__ == "__main__":
    import asyncio
    
    mock = MockPX4Interface()
    if mock.connect():
        print("Mock drone connected. Running for 5 seconds...")
        time.sleep(5)
        print("Current state:", mock.get_state())
        mock.land()
        mock.disconnect()