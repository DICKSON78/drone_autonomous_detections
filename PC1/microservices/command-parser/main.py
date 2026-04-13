from fastapi import FastAPI
from pydantic import BaseModel
import spacy
import json
import redis
from kafka import KafkaProducer
import logging
import subprocess
import sys

# Download spaCy model if not present
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    logging.info("Downloading spaCy model...")
    subprocess.check_call([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
    nlp = spacy.load("en_core_web_sm")

app = FastAPI(title="Command Parser Service")

# Kafka producer
producer = KafkaProducer(
    bootstrap_servers=['kafka:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

class Command(BaseModel):
    text: str
    user_id: str

def parse_command_to_gps(command_text: str) -> dict:
    """Parse natural language command to GPS coordinates"""
    doc = nlp(command_text.lower())
    
    # Simple GPS mapping (in real system, use geocoding API)
    location_mappings = {
        "forest": {"lat": -1.2921, "lon": 36.8219},
        "lake": {"lat": -1.2850, "lon": 36.8300},
        "field": {"lat": -1.3000, "lon": 36.8100},
        "home": {"lat": -1.2920, "lon": 36.8200}
    }
    
    detected_location = None
    for token in doc:
        if token.text in location_mappings:
            detected_location = location_mappings[token.text]
            break
    
    if not detected_location:
        detected_location = {"lat": -1.2920, "lon": 36.8200}  # Default
    
    return {
        "command": command_text,
        "target_gps": detected_location,
        "altitude": 50.0,  # Default altitude
        "action": "navigate"
    }

@app.post("/parse-command")
async def parse_command(command: Command):
    """Parse natural language command and publish to Kafka"""
    try:
        parsed_command = parse_command_to_gps(command.text)
        
        # Add metadata
        parsed_command.update({
            "user_id": command.user_id,
            "timestamp": "2024-01-01T00:00:00Z",
            "command_id": f"cmd_{hash(command.text)}"
        })
        
        # Publish to Kafka
        producer.send('drone.commands.flight', parsed_command)
        producer.flush()
        
        logging.info(f"Published command: {parsed_command}")
        
        return {
            "status": "success",
            "parsed_command": parsed_command,
            "message": "Command sent to drone"
        }
    
    except Exception as e:
        logging.error(f"Error processing command: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "command-parser"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
