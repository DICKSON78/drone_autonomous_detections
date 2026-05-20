from fastapi import FastAPI
from mavsdk import System
import asyncio
import json
from kafka import KafkaConsumer, KafkaProducer
import os
import logging
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
        # Connect to PC2 where Gazebo/PX4 runs (Docker DNS or explicit IP)
        pc2_ip = os.getenv('PC2_MAVLINK_HOST', 'gazebo-px4')
        await drone.connect(system_address=f"udp://{pc2_ip}:14540")
        logging.info(f"Connecting to drone at {pc2_ip}:14540")
        
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
    """Execute flight command from parsed command"""
    try:
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
            command["altitude"], 
            0
        )
        logging.info(f"Going to location: {target_gps}")
        
        # Monitor progress
        while True:
            async for position in drone.telemetry.position():
                distance = ((position.latitude - target_gps["lat"])**2 + 
                           (position.longitude - target_gps["lon"])**2)**0.5
                
                if distance < 0.0001:  # Very close to target
                    logging.info("Reached target location")
                    await drone.action.land()
                    return True
                
                # Send telemetry update
                telemetry = {
                    "latitude": position.latitude,
                    "longitude": position.longitude,
                    "altitude": position.relative_altitude,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                producer.send('drone.telemetry.gps', telemetry)

                async for battery in drone.telemetry.battery():
                    batt_data = {
                        "voltage_v": battery.remaining_voltage_v,
                        "percentage": battery.percentage,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    producer.send('drone.telemetry.battery', batt_data)
                    break

                async for attitude in drone.telemetry.attitude():
                    att_data = {
                        "roll_deg": attitude.roll_deg,
                        "pitch_deg": attitude.pitch_deg,
                        "yaw_deg": attitude.yaw_deg,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    producer.send('drone.telemetry.attitude', att_data)
                    break

                async for velocity in drone.telemetry.velocity_body():
                    vel_data = {
                        "north_m_s": velocity.north_m_s,
                        "east_m_s": velocity.east_m_s,
                        "down_m_s": velocity.down_m_s,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    producer.send('drone.telemetry.velocity', vel_data)
                    break
                
                await asyncio.sleep(1)
                break
    
    except Exception as e:
        logging.error(f"Flight execution error: {e}")
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
