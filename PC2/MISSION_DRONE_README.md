# Mission Drone System

A comprehensive autonomous drone system for surveillance, object detection, and mission planning in the Dodoma city simulation environment.

## Overview

This system provides a **complete mission-capable drone** with the following features:

- **Autonomous Flight Control**: OFFBOARD mode flight with waypoint navigation
- **Real-time Object Detection**: Camera-based detection of vehicles, obstacles, and buildings
- **Mission Planning**: Pre-programmed waypoint missions with automatic execution
- **Sensor Integration**: IMU, GPS, barometer, camera, and telemetry systems
- **Safety Features**: Low battery detection, geofencing, return-to-home functionality
- **Gazebo Simulation**: Realistic physics-based simulation in a Dodoma city environment

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  MISSION DRONE SYSTEM                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Mission Drone Controller (Python)             │  │
│  │  - Waypoint navigation                                │  │
│  │  - Autonomous mission execution                       │  │
│  │  - Flight mode management                             │  │
│  │  - Safety monitoring                                  │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↕                                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │    Sensor Bridge & Object Detection                  │  │
│  │  - Camera feed processing                            │  │
│  │  - GPS/IMU integration                               │  │
│  │  - Real-time object detection                        │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↕                                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  MAVROS (MAVLink ROS Interface)                      │  │
│  │  - Flight controller communication                   │  │
│  │  - Telemetry aggregation                             │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↕                                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │    Gazebo Simulation Environment                     │  │
│  │  - Iris Drone Model (1.5kg quadcopter)               │  │
│  │  - Dodoma City World                                 │  │
│  │  - Physics engine (ODE)                              │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Hardware/Drone Specifications

### Iris Drone Model
- **Mass**: 1.5 kg
- **Frame Type**: Quadcopter (X configuration)
- **Motor Type**: 4x BLDC motors
- **Propeller Size**: 125mm diameter
- **Max Speed**: 20 m/s
- **Cruise Speed**: 8 m/s
- **Max Climb Rate**: 5 m/s
- **Flight Time**: ~30 minutes (estimated)
- **Battery**: 3S LiPo (assumed)

### Sensor Suite
1. **IMU** (Inertial Measurement Unit)
   - 6-axis (accelerometer + gyroscope)
   - Update rate: 200 Hz
   
2. **GPS/GNSS**
   - Lat/Lon/Alt positioning
   - Update rate: 10 Hz
   - Dodoma coordinates: -6.1629°, 35.7516°
   
3. **Camera**
   - Resolution: 1280x960
   - FPS: 30
   - FOV: 110°
   - Downward-facing with gimbal
   
4. **Barometer/Altimeter**
   - Altitude measurement
   - Update rate: 50 Hz
   
5. **Telemetry System**
   - Real-time flight data
   - Battery voltage monitoring
   - Flight status reporting

## Software Components

### 1. **Mission Drone Controller** (`mission_drone_controller.py`)
Main autonomous flight control system.

**Key Features:**
- Autonomous waypoint navigation
- Mission planning and execution
- Flight mode management (OFFBOARD, AUTO.LAND, etc.)
- Return-to-home functionality
- Low battery detection and response
- Hovering and precise positioning

**Methods:**
```python
drone.arm_drone()                  # Arm motors
drone.takeoff(altitude=25)         # Takeoff to altitude
drone.go_to_waypoint([x, y, z])    # Navigate to waypoint
drone.execute_mission(waypoints)   # Execute multi-waypoint mission
drone.return_to_home()             # Return and land
drone.land()                       # Land at current position
drone.hover(duration=5)            # Hover for specified duration
```

### 2. **Sensor Bridge** (`sensor_bridge.py`)
Integrates all sensors and publishes standardized ROS messages.

**Published Topics:**
- `/sensor/imu` - IMU data
- `/sensor/gps` - GPS position
- `/sensor/camera/image_raw` - Camera frames
- `/sensor/altitude` - Altitude measurements
- `/sensor/battery` - Battery voltage/percentage
- `/sensor/velocity` - Velocity vector

### 3. **Object Detection Node** (`object_detection_node.py`)
Real-time object detection using computer vision.

**Detection Classes:**
- Vehicles (red HSV range)
- Obstacles (green HSV range)
- Buildings (blue HSV range)
- Custom classes (extensible)

**Published Topics:**
- `/drone/detected_objects` - Detection data (normalized coordinates)
- `/drone/detection_visualization` - Annotated image frames
- `/drone/detection_log` - Text detection logs

## Launch Instructions

### Prerequisites
```bash
sudo apt-get install ros-noetic-mavros ros-noetic-mavros-extras
sudo apt-get install ros-noetic-gazebo-ros-control
pip3 install opencv-python-headless
```

### Launch the Complete System
```bash
# Terminal 1: Launch Gazebo world with drone
roslaunch drone_autonomous_detections mission_drone.launch world:=dodoma_city

# Terminal 2: (Auto-launched with mission_drone.launch)
# Mission controller will start automatically
```

### Manual Launch (Step-by-step)
```bash
# Terminal 1: Start Gazebo
gz sim /path/to/dodoma_city.sdf

# Terminal 2: Start MAVROS
roslaunch mavros px4.launch fcu_url:="udp://:14540@127.0.0.1:14557"

# Terminal 3: Start mission controller
rosrun drone_autonomous_detections mission_drone_controller.py

# Terminal 4: Start sensor bridge
rosrun drone_autonomous_detections sensor_bridge.py

# Terminal 5: Start object detector
rosrun drone_autonomous_detections object_detection_node.py

# Terminal 6: View with RViz
rosrun rviz rviz -d /path/to/drone_mission.rviz
```

## Configuration

Edit `config/mission_drone_config.yaml` to customize:
- Flight parameters (speed, altitude, hover time)
- Safety thresholds (battery, geofence)
- Sensor settings (update rates, FOV)
- Detection parameters (confidence, classes)
- PID control gains

## Example Mission

The default mission performs a **surveillance pattern**:

```python
surveillance_waypoints = [
    [0, 0, 25],      # Takeoff
    [50, 0, 25],     # North
    [50, 50, 25],    # Northeast
    [0, 50, 25],     # East
    [-50, 50, 25],   # Southeast
    [-50, 0, 25],    # South
    [-50, -50, 25],  # Southwest
    [0, -50, 25],    # West
    [50, -50, 25],   # Northwest
    [0, 0, 25],      # Return to start
]
```

**Execution Flow:**
1. Arm motors
2. Takeoff to 25m altitude
3. Navigate through 8 waypoints (hovers 2s at each)
4. Return to home position
5. Land and disarm

## ROS Topic Reference

### Published by Controller
- `/mavros/setpoint_position/local` - Target position
- `/mavros/setpoint_velocity/cmd_vel` - Target velocity
- `/drone/mission_status` - Current mission state

### Subscribed by Controller
- `/mavros/local_position/pose` - Current position
- `/mavros/imu/data` - IMU measurements
- `/mavros/global_position/global` - GPS data
- `/drone/detected_objects` - Detection results

## Safety Features

1. **Low Battery Protection**
   - Triggers at 15% battery
   - Automatically returns to home
   - Critical landing at 5% battery

2. **Geofencing**
   - Default radius: 500m
   - Max altitude: 100m
   - Prevents out-of-bounds flight

3. **Collision Avoidance**
   - Monitors detected obstacles
   - Adjusts waypoints if needed
   - Emergency descent capability

4. **Flight Monitoring**
   - Real-time telemetry logging
   - Flight state tracking
   - Error condition detection

## Troubleshooting

### Drone Not Taking Off
```bash
# Check MAVROS connection
rostopic echo /mavros/state

# Verify GPS lock
rostopic echo /mavros/global_position/global

# Check battery level
rostopic echo /sensor/battery
```

### Object Detection Not Working
```bash
# Verify camera feed
rostopic echo /sensor/camera/image_raw

# Check detection node status
rosnode list | grep detector
```

### High CPU Usage
- Reduce camera FPS in config
- Lower detection confidence threshold
- Disable visualization during flight

## Future Enhancements

- [ ] Optical flow visual odometry
- [ ] LiDAR-based obstacle avoidance
- [ ] Thermal imaging integration
- [ ] Multi-drone coordination
- [ ] Machine learning-based detection (YOLO, TensorFlow)
- [ ] 3D mapping and SLAM
- [ ] Autonomous trajectory planning

## File Structure

```
PC2/
├── gazebo_models/dodoma/iris_drone/
│   ├── model.config
│   └── model.sdf
├── gazebo_worlds/dodoma/
│   └── dodoma_city.sdf
├── scripts/
│   ├── mission_drone_controller.py
│   ├── sensor_bridge.py
│   └── object_detection_node.py
├── config/
│   └── mission_drone_config.yaml
├── launch/
│   └── mission_drone.launch
└── docs/
    └── MISSION_DRONE_README.md
```

## License

This mission drone system is part of the Drone Autonomous Detections project.

## Support

For issues or questions, please refer to:
- [Project Repository](https://github.com/DICKSON78/drone_autonomous_detections)
- Gazebo Documentation: https://gazebosim.org
- MAVROS Documentation: http://docs.ros.org/en/noetic/api/mavros/html/
- ROS Documentation: http://wiki.ros.org/noetic
