from fastapi import FastAPI
from mavsdk import System
import asyncio
import json
from kafka import KafkaConsumer, KafkaProducer
import logging
from pydantic import BaseModel

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
                    "timestamp": "2024-01-01T00:00:00Z"
                }
                producer.send('drone.telemetry.gps', telemetry)
                
                await asyncio.sleep(1)
                break
    
    except Exception as e:
        logging.error(f"Flight execution error: {e}")
        return False

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
