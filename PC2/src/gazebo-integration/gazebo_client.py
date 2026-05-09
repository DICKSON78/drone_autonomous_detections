# Gazebo API client for simulation control
"""
Gazebo simulation client for drone autonomous system
"""

import asyncio
import subprocess
import time
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

class GazeboClient:
    """Client for managing Gazebo simulation"""
    
    def __init__(self, world_file: str = "/app/worlds/drone_world.world"):
        self.world_file = world_file
        self.gazebo_process = None
        self.px4_process = None
        self.connected = False
        self.world_name = os.path.basename(world_file).replace('.world', '')
        
        logger.info(f"GazeboClient initialized with world: {world_file}")
    
    async def start(self) -> bool:
        """Start Gazebo + PX4 SITL simulation"""
        try:
            if self._is_gazebo_running():
                logger.info("Gazebo is already running")
                self.connected = True
                return True

            logger.info("Starting Gazebo simulation...")

            # Use gzserver for headless mode (recommended in Docker)
            cmd = [
                'gzserver', 
                '--verbose',
                self.world_file
            ]

            self.gazebo_process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid  # Allows clean kill
            )

            await asyncio.sleep(8)  # Give Gazebo time to initialize

            # Start PX4 SITL (better approach)
            await self._start_px4_sitl()

            self.connected = True
            logger.info(f"Gazebo + PX4 started successfully with world: {self.world_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to start Gazebo: {e}")
            await self.stop()
            return False
    
    async def _start_px4_sitl(self):
        """Start PX4 Software-In-The-Loop simulation"""
        try:
            px4_cmd = [
                'make', '-C', '/px4', 
                'px4_sitl', 
                'gazebo-classic'  # or 'gazebo' depending on your PX4 version
            ]
            
            self.px4_process = subprocess.Popen(
                px4_cmd,
                cwd='/px4',
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            await asyncio.sleep(5)
            logger.info("PX4 SITL started")
            
        except Exception as e:
            logger.warning(f"PX4 SITL start failed (this may be expected in some setups): {e}")
    
    async def stop(self):
        """Stop all simulation processes"""
        if self.gazebo_process:
            try:
                self.gazebo_process.terminate()
                await asyncio.sleep(1)
                if self.gazebo_process.poll() is None:
                    self.gazebo_process.kill()
            except:
                pass
        
        if self.px4_process:
            try:
                self.px4_process.terminate()
            except:
                pass
                
        self.connected = False
        logger.info("Gazebo simulation stopped")
    
    def _is_gazebo_running(self) -> bool:
        """Check if gzserver is running"""
        try:
            result = subprocess.run(['pgrep', '-f', 'gzserver'], 
                                  capture_output=True, text=True)
            return bool(result.stdout.strip())
        except:
            return False
    
    # Placeholder methods for future use
    def pause(self):
        pass
    
    def reset(self):
        pass