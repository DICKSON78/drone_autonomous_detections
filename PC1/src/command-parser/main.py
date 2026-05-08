from fastapi import FastAPI
from pydantic import BaseModel
import spacy
import json
import redis
from kafka import KafkaProducer
import logging
import subprocess
import sys
from nlp_processor import command_processor

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
    """Enhanced command parsing using advanced NLP processor"""
    try:
        # Use advanced NLP processor for complex command parsing
        parsed_command = command_processor.parse_complex_command(command_text)
        
        # Add timestamp and command ID
        import time
        parsed_command.update({
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "command_id": f"cmd_{int(time.time() * 1000)}"
        })
        
        logging.info(f"Advanced parsing result: {parsed_command}")
        return parsed_command
        
    except Exception as e:
        logging.error(f"Advanced parsing failed, falling back to simple parsing: {e}")
        
        # Fallback to simple parsing
        doc = nlp(command_text.lower())
        
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
            detected_location = {"lat": -1.2920, "lon": 36.8200}
        
        return {
            "command": command_text,
            "target_gps": detected_location,
            "altitude": 50.0,
            "action": "navigate",
            "intent": "navigate",
            "confidence": 0.6
        }

@app.post("/parse-command")
async def parse_command(command: Command):
    """Parse natural language command and publish to Kafka"""
    try:
        parsed_command = parse_command_to_gps(command.text)
        
        # Add user_id (timestamp and command_id already added in parse_command_to_gps)
        parsed_command.update({
            "user_id": command.user_id
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
