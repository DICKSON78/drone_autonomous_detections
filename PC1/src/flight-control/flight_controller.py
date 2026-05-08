from fastapi import FastAPI
from mavsdk import System
import asyncio
import json
from kafka import KafkaConsumer, KafkaProducer
import logging
from pydantic import BaseModel
from yolo_detector import initialize_detector
from rl_controller import initialize_rl_controller

app = FastAPI(title="Flight Control Service")

# Kafka setup
consumer = KafkaConsumer(
    'drone.commands.flight',
    bootstrap_servers=['kafka:9092'],
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)

producer = KafkaProducer(
    bootstrap_servers=['kafka:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# Global instances
drone = None
yolo_detector = None
rl_controller = None

class DroneStatus(BaseModel):
    connected: bool = False
    armed: bool = False
    latitude: float = 0.0
    longitude: float = 0.0
    altitude: float = 0.0
    battery: float = 0.0

async def connect_drone():
    """Connect to drone (PX4 SITL)"""
    global drone
    drone = System()
    
    try:
        await drone.connect(system_address="udp://:14540")
        logging.info("Connected to drone")
        
        # Wait for drone to be ready
        async for state in drone.core.connection_state():
            if state.is_connected:
                logging.info("Drone discovered")
                break
        
        return True
    except Exception as e:
        logging.error(f"Failed to connect to drone: {e}")
        return False

async def execute_flight_command(command):
    """Enhanced flight command execution with AI integration"""
    try:
        # Get current drone state
        current_state = await get_current_drone_state()
        
        # Use RL controller for autonomous flight if available
        if rl_controller and command.get("intent") in ["navigate", "search", "surveillance"]:
            rl_commands = rl_controller.autonomous_flight_control(current_state, command)
            await execute_rl_commands(rl_commands, command)
        else:
            # Traditional flight execution
            await execute_traditional_flight(command)
        
        # Enhanced monitoring with YOLO detection
        if yolo_detector and command.get("search_objects"):
            await monitor_with_vision(command)
        
        return True
    
    except Exception as e:
        logging.error(f"Enhanced flight execution error: {e}")
        return False

async def execute_traditional_flight(command):
    """Execute traditional flight commands"""
    # Arm the drone
    await drone.action.arm()
    logging.info("Drone armed")
    
    # Takeoff
    await drone.action.takeoff()
    logging.info("Drone taking off")
    
    # Wait for takeoff to complete
    await asyncio.sleep(10)
    
    # Go to target location
    target_gps = command["target_gps"]
    await drone.action.goto_location(
        target_gps["lat"], 
        target_gps["lon"], 
        command.get("altitude", 50.0), 
        0
    )
    logging.info(f"Going to location: {target_gps}")

async def execute_rl_commands(rl_commands, command):
    """Execute RL-generated flight commands"""
    logging.info(f"Executing RL commands: {rl_commands}")
    
    # Arm and takeoff if not already in air
    try:
        await drone.action.arm()
        await drone.action.takeoff()
        await asyncio.sleep(10)
    except:
        pass  # Already flying
    
    # Apply RL commands
    if rl_commands.get('emergency_stop'):
        await drone.action.hold()
        logging.info("Emergency stop activated by RL controller")
    else:
        # Navigate to target using RL guidance
        target_gps = command.get("target_gps")
        if target_gps:
            await drone.action.goto_location(
                target_gps["lat"],
                target_gps["lon"], 
                command.get("altitude", 50.0),
                0
            )

async def monitor_with_vision(command):
    """Monitor flight with YOLO vision system"""
    search_objects = command.get("search_objects", [])
    if not search_objects:
        return
    
    logging.info(f"Starting vision monitoring for objects: {search_objects}")
    
    # Simulate vision processing (in real system, would get camera frames)
    for i in range(10):  # Simulate 10 frames
        await asyncio.sleep(2)
        
        # Mock frame data
        mock_frame = {"timestamp": asyncio.get_event_loop().time()}
        
        # Process with YOLO
        if yolo_detector:
            detection_result = yolo_detector.process_frame_async(
                np.zeros((480, 640, 3)),  # Mock frame
                command
            )
            
            # Send detection results
            if detection_result.get('search_success'):
                logging.info(f"Found target objects: {detection_result['search_results']}")
                producer.send('drone.vision.detections', detection_result)

async def get_current_drone_state():
    """Get comprehensive drone state"""
    try:
        async for position in drone.telemetry.position():
            async for battery in drone.telemetry.battery():
                return {
                    "position": {
                        "lat": position.latitude,
                        "lon": position.longitude,
                        "altitude": position.relative_altitude
                    },
                    "battery": battery.remaining_percent,
                    "velocity": {"x": 0, "y": 0, "z": 0},  # Simplified
                    "orientation": {"roll": 0, "pitch": 0, "yaw": 0}  # Simplified
                }
    except:
        return {
            "position": {"lat": -1.2920, "lon": 36.8200, "altitude": 50.0},
            "battery": 100.0,
            "velocity": {"x": 0, "y": 0, "z": 0},
            "orientation": {"roll": 0, "pitch": 0, "yaw": 0}
        }

async def command_consumer():
    """Consume commands from Kafka"""
    while True:
        try:
            for message in consumer:
                command = message.value
                logging.info(f"Received command: {command}")
                
                # Execute flight command
                success = await execute_flight_command(command)
                
                # Send status update
                status = {
                    "command_id": command.get("command_id"),
                    "status": "completed" if success else "failed",
                    "timestamp": "2024-01-01T00:00:00Z"
                }
                producer.send('drone.status', status)
                
        except Exception as e:
            logging.error(f"Consumer error: {e}")
            await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event():
    """Initialize AI components and drone connection"""
    global yolo_detector, rl_controller
    
    # Initialize YOLO detector
    try:
        yolo_detector = initialize_detector(kafka_producer=producer)
        logging.info("YOLO detector initialized")
    except Exception as e:
        logging.error(f"Failed to initialize YOLO: {e}")
    
    # Initialize RL controller
    try:
        rl_controller = initialize_rl_controller(kafka_producer=producer)
        logging.info("RL controller initialized")
    except Exception as e:
        logging.error(f"Failed to initialize RL controller: {e}")
    
    # Start command consumer in background
    asyncio.create_task(command_consumer())
    
    # Connect to drone
    await connect_drone()

@app.get("/status")
async def get_drone_status():
    """Get current drone status"""
    if not drone:
        return DroneStatus()
    
    try:
        # Get current position
        async for position in drone.telemetry.position():
            return DroneStatus(
                connected=True,
                latitude=position.latitude,
                longitude=position.longitude,
                altitude=position.relative_altitude
            )
            break
    except:
        return DroneStatus(connected=True)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "flight-control"}

if __name__ == "__main__":
    import uvicorn
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=8001)
