#!/usr/bin/env python3
"""
PC2 Gazebo GUI Launcher
Creates and launches Gazebo with drone, camera, and environment
"""

import os
import sys
import time
import subprocess
import threading
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GazeboLauncher:
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.worlds_dir = self.base_dir / "worlds"
        self.src_dir = self.base_dir / "src"
        self.processes = []
        
    def setup_environment(self):
        """Setup environment and create worlds"""
        logger.info("Setting up PC2 environment...")
        
        # Create directories
        self.worlds_dir.mkdir(exist_ok=True)
        (self.base_dir / "models").mkdir(exist_ok=True)
        (self.base_dir / "data" / "detection_images").mkdir(parents=True, exist_ok=True)
        (self.base_dir / "logs").mkdir(exist_ok=True)
        
        # Add src to path
        sys.path.insert(0, str(self.src_dir))
        
    def create_drone_world(self):
        """Create a world with drone, obstacles, and camera"""
        logger.info("Creating drone world with obstacles...")
        
        try:
            from gazebo_integration.world_builder import WorldBuilder
            
            builder = WorldBuilder()
            builder.create_base_world("drone_simulation_world")
            
            # Add buildings (urban environment)
            logger.info("  Adding buildings...")
            building_positions = [
                [20, 20, 0], [-20, 20, 0], [20, -20, 0], [-20, -20, 0],
                [10, 30, 0], [-10, 30, 0], [30, 10, 0], [-30, 10, 0],
                [0, 40, 0], [40, 0, 0], [-40, 0, 0], [0, -40, 0]
            ]
            
            for i, pos in enumerate(building_positions):
                size = [5, 8, 15]  # width, depth, height
                color = [0.7, 0.7, 0.7]  # Gray
                builder.add_obstacle(pos, size, color, f"building_{i}")
            
            # Add trees (forest environment)
            logger.info("  Adding trees...")
            tree_positions = [
                [15, 15, 0], [-15, 15, 0], [15, -15, 0], [-15, -15, 0],
                [25, 0, 0], [-25, 0, 0], [0, 25, 0], [0, -25, 0],
                [10, 10, 0], [-10, 10, 0], [10, -10, 0], [-10, -10, 0],
                [30, 30, 0], [-30, 30, 0], [30, -30, 0], [-30, -30, 0]
            ]
            
            for i, pos in enumerate(tree_positions):
                # Tree trunk
                builder.add_cylinder_obstacle(
                    pos, 0.5, 4.0, [0.55, 0.27, 0.07], f"tree_trunk_{i}"
                )
                # Tree canopy
                builder.add_sphere_obstacle(
                    [pos[0], pos[1], pos[2] + 4.0], 1.5, [0.0, 0.6, 0.0], f"tree_canopy_{i}"
                )
            
            # Add vehicles (cars, trucks)
            logger.info("  Adding vehicles...")
            vehicle_positions = [
                [5, 0, 0], [-5, 0, 0], [0, 5, 0], [0, -5, 0],
                [10, 10, 0], [-10, -10, 0]
            ]
            
            for i, pos in enumerate(vehicle_positions):
                size = [2, 1, 1.5]  # Car dimensions
                color = [0.8, 0.2, 0.2]  # Red
                builder.add_obstacle(pos, size, color, f"vehicle_{i}")
            
            # Add waypoints for navigation
            logger.info("  Adding navigation waypoints...")
            waypoints = [
                [0, 0, 2],  # Start position (drone takeoff)
                [20, 20, 5],  # Waypoint 1
                [-20, 20, 5],  # Waypoint 2
                [-20, -20, 5],  # Waypoint 3
                [20, -20, 5],   # Waypoint 4
                [0, 0, 2]     # Return home
            ]
            builder.add_waypoints(waypoints, [1.0, 0.0, 0.0])  # Red waypoints
            
            # Add no-fly zones
            logger.info("  Adding no-fly zones...")
            builder.add_no_fly_zone([0, 0, 0], 8.0, 20.0)  # Central no-fly zone
            
            # Save world
            world_file = self.worlds_dir / "drone_world.world"
            builder.save_world(str(world_file))
            logger.info(f"✓ World saved to {world_file}")
            
            return str(world_file)
            
        except Exception as e:
            logger.error(f"Failed to create world: {e}")
            return None
    
    def create_drone_model(self):
        """Create a simple drone model with camera"""
        logger.info("Creating drone model...")
        
        drone_sdf = """<?xml version="1.0"?>
<sdf version="1.6">
  <model name="drone">
    <pose>0 0 2 0 0 0</pose>
    
    <!-- Drone Body -->
    <link name="body">
      <inertial>
        <mass>1.5</mass>
        <inertia>
          <ixx>0.1</ixx>
          <ixy>0</ixy>
          <ixz>0</ixz>
          <iyy>0.1</iyy>
          <iyz>0</iyz>
          <izz>0.2</izz>
        </inertia>
      </inertial>
      
      <collision name="collision">
        <geometry>
          <box>
            <size>0.5 0.5 0.2</size>
          </box>
        </geometry>
      </collision>
      
      <visual name="visual">
        <geometry>
          <box>
            <size>0.5 0.5 0.2</size>
          </box>
        </geometry>
        <material>
          <ambient>0.2 0.2 0.8 1</ambient>
          <diffuse>0.2 0.2 0.8 1</diffuse>
        </material>
      </visual>
    </link>
    
    <!-- Camera -->
    <link name="camera_link">
      <pose>0.2 0 0.1 0 -1.5708 0</pose>
      
      <sensor name="camera" type="camera">
        <pose>0 0 0 0 0 0</pose>
        <camera>
          <horizontal_fov>1.047</horizontal_fov>
          <image>
            <width>640</width>
            <height>480</height>
            <format>R8G8B8</format>
          </image>
          <clip>
            <near>0.1</near>
            <far>100</far>
          </clip>
        </camera>
        
        <plugin name="camera_controller" filename="libgazebo_ros_camera.so">
          <robotNamespace>/drone</robotNamespace>
          <imageName>image_raw</imageName>
          <imageTopicName>image_raw</imageTopicName>
          <cameraInfoTopicName>camera_info</cameraInfoTopicName>
          <frameName>camera_link</frameName>
          <hackBaseline>0.07</hackBaseline>
          <distortionK1>0.0</distortionK1>
          <distortionK2>0.0</distortionK2>
          <distortionK3>0.0</distortionK3>
          <distortionT1>0.0</distortionT1>
          <distortionT2>0.0</distortionT2>
        </plugin>
      </sensor>
    </link>
  </model>
</sdf>"""
        
        models_dir = self.base_dir / "models" / "drone"
        models_dir.mkdir(parents=True, exist_ok=True)
        
        model_file = models_dir / "model.sdf"
        with open(model_file, 'w') as f:
            f.write(drone_sdf)
        
        logger.info(f"✓ Drone model saved to {model_file}")
        return str(models_dir)
    
    def setup_x11(self):
        """Setup X11 forwarding for GUI"""
        logger.info("Setting up X11 forwarding...")
        
        try:
            # Allow X11 connections
            subprocess.run(['xhost', '+local:docker'], check=True, capture_output=True)
            logger.info("✓ X11 forwarding enabled")
            return True
        except subprocess.CalledProcessError as e:
            logger.warning(f"X11 setup failed: {e}")
            logger.info("GUI may not work. Try running: export DISPLAY=:0")
            return False
    
    def launch_gazebo_gui(self, world_file):
        """Launch Gazebo with GUI"""
        logger.info("Launching Gazebo GUI...")
        
        try:
            # Set environment variables
            env = os.environ.copy()
            env['GAZEBO_MODEL_PATH'] = str(self.base_dir / "models")
            env['GAZEBO_PLUGIN_PATH'] = '/usr/lib/x86_64-linux-gnu/gazebo-11/plugins:/usr/lib/gazebo-11/plugins'
            env['GAZEBO_RESOURCE_PATH'] = '/usr/share/gazebo-11'
            
            # Launch Gazebo GUI
            cmd = [
                'gazebo', 
                '--verbose',
                str(world_file)
            ]
            
            logger.info(f"Running: {' '.join(cmd)}")
            
            process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            
            self.processes.append(process)
            
            # Log output
            def log_output():
                for line in iter(process.stdout.readline, ''):
                    if line.strip():
                        logger.info(f"Gazebo: {line.strip()}")
            
            log_thread = threading.Thread(target=log_output, daemon=True)
            log_thread.start()
            
            logger.info("✓ Gazebo GUI launched")
            logger.info("  - World loaded with buildings, trees, vehicles")
            logger.info("  - Drone model with camera at origin")
            logger.info("  - Navigation waypoints marked in red")
            logger.info("  - Central no-fly zone (red cylinder)")
            
            return process
            
        except Exception as e:
            logger.error(f"Failed to launch Gazebo: {e}")
            return None
    
    def launch_camera_feed(self):
        """Launch camera feed viewer"""
        logger.info("Setting up camera feed viewer...")
        
        try:
            # Create a simple camera viewer script
            viewer_script = self.base_dir / "camera_viewer.py"
            viewer_code = '''
import cv2
import numpy as np
import time

print("Camera Feed Viewer")
print("Press 'q' to quit")

# Create a dummy camera feed (simulated)
while True:
    # Generate simulated camera view
    frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    
    # Add some text
    cv2.putText(frame, f"Drone Camera - {time.strftime('%H:%M:%S')}", 
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.putText(frame, "Simulated Feed", (10, 70), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    cv2.imshow('Drone Camera Feed', frame)
    
    if cv2.waitKey(30) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()
'''
            
            with open(viewer_script, 'w') as f:
                f.write(viewer_code)
            
            # Launch camera viewer
            process = subprocess.Popen([
                sys.executable, str(viewer_script)
            ])
            
            self.processes.append(process)
            logger.info("✓ Camera feed viewer launched")
            
            return process
            
        except Exception as e:
            logger.error(f"Failed to launch camera viewer: {e}")
            return None
    
    def cleanup(self):
        """Clean up processes"""
        logger.info("Cleaning up...")
        
        for process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                try:
                    process.kill()
                except:
                    pass
        
        self.processes.clear()
        logger.info("✓ Cleanup completed")
    
    def run(self):
        """Main launch sequence"""
        logger.info("PC2 Gazebo GUI Launcher")
        logger.info("=" * 50)
        
        try:
            # Setup environment
            self.setup_environment()
            
            # Setup X11
            self.setup_x11()
            
            # Create world
            world_file = self.create_drone_world()
            if not world_file:
                logger.error("Failed to create world")
                return False
            
            # Create drone model
            self.create_drone_model()
            
            # Launch Gazebo
            gazebo_process = self.launch_gazebo_gui(world_file)
            if not gazebo_process:
                logger.error("Failed to launch Gazebo")
                return False
            
            # Wait a bit for Gazebo to start
            time.sleep(5)
            
            # Launch camera viewer
            camera_process = self.launch_camera_feed()
            
            logger.info("\\n" + "=" * 50)
            logger.info("✓ PC2 GAZEBO ENVIRONMENT READY!")
            logger.info("=" * 50)
            logger.info("Environment Features:")
            logger.info("  • Urban environment with 12 buildings")
            logger.info("  • Forest area with 16 trees")
            logger.info("  • 6 vehicles scattered around")
            logger.info("  • Drone with camera at origin")
            logger.info("  • 6 navigation waypoints (red markers)")
            logger.info("  • Central no-fly zone (red cylinder)")
            logger.info("  • Camera feed viewer window")
            logger.info("\\nControls:")
            logger.info("  • Gazebo: Use mouse to navigate view")
            logger.info("  • Camera: Press 'q' to close viewer")
            logger.info("  • Exit: Press Ctrl+C here")
            logger.info("=" * 50)
            
            # Wait for user interrupt
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("\\nShutdown requested by user")
            
            return True
            
        except Exception as e:
            logger.error(f"Launch failed: {e}")
            return False
        finally:
            self.cleanup()

if __name__ == "__main__":
    launcher = GazeboLauncher()
    success = launcher.run()
    
    if success:
        logger.info("Gazebo launcher completed successfully")
    else:
        logger.error("Gazebo launcher failed")
        sys.exit(1)
