# Simulation Service for Guided Language Drone System
from fastapi import FastAPI
from pydantic import BaseModel
import asyncio
import json
import logging
from kafka import KafkaProducer, KafkaConsumer
from simulation_env import initialize_simulation
import time

app = FastAPI(title="Simulation Service")

# Kafka setup
producer = KafkaProducer(
    bootstrap_servers=['kafka:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

consumer = KafkaConsumer(
    'drone.commands.flight',
    bootstrap_servers=['kafka:9092'],
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)

# Global simulation manager
simulation_manager = None

class SimulationCommand(BaseModel):
    action: str  # start, stop, reset
    command_context: dict = None

class SimulationStatus(BaseModel):
    running: bool = False
    episode: int = 0
    stats: dict = {}

async def command_consumer():
    """Consume commands from Kafka for simulation"""
    global simulation_manager
    
    while True:
        try:
            for message in consumer:
                command = message.value
                logging.info(f"Received command for simulation: {command}")
                
                if simulation_manager and command.get('intent') in ['navigate', 'search', 'surveillance']:
                    # Start simulation with command context
                    await simulation_manager.run_simulation(command)
                
        except Exception as e:
            logging.error(f"Simulation consumer error: {e}")
            await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event():
    """Initialize simulation service"""
    global simulation_manager
    
    # Initialize simulation manager
    simulation_manager = initialize_simulation(kafka_producer=producer)
    
    # Start command consumer
    asyncio.create_task(command_consumer())
    
    logging.info("Simulation service started")

@app.post("/simulation/control")
async def control_simulation(command: SimulationCommand):
    """Control simulation (start/stop/reset)"""
    global simulation_manager
    
    try:
        if command.action == "start":
            if not simulation_manager.is_running:
                await simulation_manager.run_simulation(command.command_context)
                return {"status": "success", "message": "Simulation started"}
            else:
                return {"status": "error", "message": "Simulation already running"}
        
        elif command.action == "stop":
            simulation_manager.stop_simulation()
            return {"status": "success", "message": "Simulation stopped"}
        
        elif command.action == "reset":
            simulation_manager.stop_simulation()
            await asyncio.sleep(1)
            await simulation_manager.run_simulation(command.command_context)
            return {"status": "success", "message": "Simulation reset"}
        
        else:
            return {"status": "error", "message": "Invalid action"}
    
    except Exception as e:
        logging.error(f"Simulation control error: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/simulation/status")
async def get_simulation_status():
    """Get current simulation status"""
    global simulation_manager
    
    if not simulation_manager:
        return SimulationStatus()
    
    stats = simulation_manager.get_environment_stats()
    
    return SimulationStatus(
        running=simulation_manager.is_running,
        episode=simulation_manager.current_episode,
        stats=stats
    )

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "simulation"}

if __name__ == "__main__":
    import uvicorn
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=8002)
