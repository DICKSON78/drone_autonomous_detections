from fastapi import FastAPI
from mavsdk import System
import asyncio
import json
from kafka import KafkaConsumer, KafkaProducer
import os
import logging
import time
from datetime import datetime, timezone
from pydantic import BaseModel

app = FastAPI(title="Flight Control Service")

# Kafka configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092').split(',')

consumer = KafkaConsumer(
    'drone.commands.flight',
    'drone.navigation.decisions',
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    auto_offset_reset='latest'
)

producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# Global drone instance
drone = None

# Home position matching the Webots simulation origin
HOME_LAT = -6.1630
HOME_LON = 35.7516

class DroneStatus(BaseModel):
    connected: bool = False
    armed: bool = False
    latitude: float = 0.0
    longitude: float = 0.0
    altitude: float = 0.0
    battery: float = 0.0

async def connect_drone():
    """Connect to drone (PX4 SITL on PC2)"""
    global drone
    drone = System()
    
    try:
        pc2_ip = os.getenv('PC2_MAVLINK_HOST', 'gazebo-px4')
        await drone.connect(system_address=f"udp://{pc2_ip}:14540")
        logging.info(f"Connecting to drone at {pc2_ip}:14540")
        
        async for state in drone.core.connection_state():
            if state.is_connected:
                logging.info("Drone discovered")
                break
        
        return True
    except Exception as e:
        logging.error(f"Failed to connect to drone: {e}")
        return False

async def wait_for_position(timeout: float = 15.0) -> bool:
    """Wait until telemetry position is available."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            async for p in drone.telemetry.position():
                if p.latitude != 0.0 and p.longitude != 0.0:
                    return True
                break
        except Exception:
            pass
        await asyncio.sleep(0.5)
    return False

async def execute_flight_command(command):
    """Execute a flight command, dispatching by *type*."""
    cmd_type = command.get("type", "")
    altitude = command.get("altitude", 10.0)
    logging.info("Executing command: type=%s altitude=%.1f", cmd_type, altitude)

    try:
        if cmd_type == "takeoff":
            if not await wait_for_position():
                logging.warning("No GPS fix before takeoff")
            await drone.action.arm()
            await asyncio.sleep(1)
            await drone.action.takeoff()
            logging.info("Takeoff initiated to %.1fm", altitude)

        elif cmd_type == "land":
            await drone.action.land()
            logging.info("Landing")

        elif cmd_type == "goto":
            target_gps = command.get("target_gps", {"lat": HOME_LAT, "lon": HOME_LON})
            if not await wait_for_position():
                logging.warning("No GPS fix before goto")
            await drone.action.arm()
            await asyncio.sleep(1)
            await drone.action.takeoff()
            await asyncio.sleep(2)
            # Climb to target altitude first
            async for pos in drone.telemetry.position():
                current_alt = pos.relative_altitude
                break
            if current_alt < altitude - 2:
                await drone.action.goto_location(
                    target_gps["lat"], target_gps["lon"], altitude, 0
                )
                await asyncio.sleep(3)
            await drone.action.goto_location(
                target_gps["lat"], target_gps["lon"], altitude, 0
            )
            logging.info("Navigating to %.6f, %.6f at %.1fm",
                         target_gps["lat"], target_gps["lon"], altitude)
            # Monitor progress with telemetry
            for _ in range(300):
                async for pos in drone.telemetry.position():
                    dist = ((pos.latitude - target_gps["lat"]) ** 2 +
                            (pos.longitude - target_gps["lon"]) ** 2) ** 0.5
                    # publish telemetry
                    producer.send("drone.telemetry.gps", {
                        "latitude": pos.latitude, "longitude": pos.longitude,
                        "altitude": pos.relative_altitude,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                    if dist < 0.0001:
                        logging.info("Reached target")
                        await drone.action.land()
                        return True
                    break
                await asyncio.sleep(1)

        elif cmd_type in ("return", "rtl"):
            await drone.action.return_to_launch()
            logging.info("Returning to launch")

        elif cmd_type == "hover":
            await drone.action.hold()
            logging.info("Hovering")

        elif cmd_type == "arm":
            await drone.action.arm()
            logging.info("Armed")

        elif cmd_type == "disarm":
            await drone.action.disarm()
            logging.info("Disarmed")

        else:
            logging.warning("Unknown command type: %s", cmd_type)
            return False

        return True

    except Exception as e:
        logging.error("Flight execution error: %s", e)
        return False

async def execute_move_command(action):
    """Execute simple movement from autonomous navigation"""
    if not drone: return
    try:
        # Check if drone is in the air
        async for in_air in drone.telemetry.in_air():
            if not in_air:
                logging.info("Drone not in air, ignoring move command")
                return
            break
            
        logging.info(f"Executing autonomous move: {action}")
        
        # Get current position
        async for position in drone.telemetry.position():
            curr_lat = position.latitude
            curr_lon = position.longitude
            curr_alt = position.relative_altitude
            break
            
        # Small offset (approx 1 meter)
        offset = 0.00001
        
        if action == "left":
            await drone.action.goto_location(curr_lat, curr_lon - offset, curr_alt, 0)
        elif action == "right":
            await drone.action.goto_location(curr_lat, curr_lon + offset, curr_alt, 0)
        elif action == "up":
            await drone.action.goto_location(curr_lat, curr_lon, curr_alt + 2, 0)
        
    except Exception as e:
        logging.error(f"Move execution error: {e}")

async def command_consumer():
    """Consume commands from Kafka"""
    while True:
        try:
            for message in consumer:
                command = message.value
                logging.info(f"Received command: {command}")
                
                # Execute flight command
                if message.topic == 'drone.commands.flight':
                    success = await execute_flight_command(command)
                elif message.topic == 'drone.navigation.decisions':
                    await execute_move_command(command.get("action"))
                    success = True
                
                # Send status update
                status = {
                    "command_id": command.get("command_id"),
                    "command_type": command.get("type", "unknown"),
                    "status": "completed" if success else "failed",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                producer.send('drone.status.flight', status)
                
        except Exception as e:
            logging.error(f"Consumer error: {e}")
            await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event():
    """Initialize drone connection and start command consumer"""
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
