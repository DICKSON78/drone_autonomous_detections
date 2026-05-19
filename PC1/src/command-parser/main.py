from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from kafka import KafkaProducer
import json
import os
import logging
from .nlp_handler import NLPHandler

app = FastAPI(title="PC1 - Command Parser Service")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Kafka configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092').split(',')
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

nlp = NLPHandler()

class CommandRequest(BaseModel):
    text: str

@app.post("/parse")
async def parse_command(request: CommandRequest):
    try:
        logger.info(f"Parsing command: {request.text}")
        command = nlp.parse(request.text)
        
        # Publish to Kafka
        producer.send('drone.commands.flight', command)
        logger.info(f"Published command to Kafka: {command['type']}")
        
        return command
    except Exception as e:
        logger.error(f"Error parsing command: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "command-parser"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
