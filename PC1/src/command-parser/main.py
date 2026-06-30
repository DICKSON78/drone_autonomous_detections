from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from kafka import KafkaProducer
import json
import logging
import os
import time
from nlu_parser import parse_command

app = FastAPI(title="PC1 - Command Parser Service")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
)
logger = logging.getLogger(__name__)

# File logging for testing evidence
_log_file = os.getenv("NLU_LOG_FILE", "/var/log/nlu_parser.log")
os.makedirs(os.path.dirname(_log_file), exist_ok=True)
_fh = logging.FileHandler(_log_file)
_fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(_fh)

# Kafka configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092').split(',')
producer = None
try:
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    logger.info("Kafka producer connected to %s", KAFKA_BOOTSTRAP_SERVERS)
except Exception as exc:
    logger.warning("Kafka unavailable — running in REST-only mode: %s", exc)

# ── Flight-control message format ─────────────────────────────────────────────
# The flight-control service (flight_controller.py / command_executor.py)
# expects: {command_id, type, raw_text, target_gps, altitude, entities}
# where *type* is one of: takeoff, land, goto, return, hover, forward, disarm.

_INTENT_TO_FLIGHT_TYPE = {
    "takeoff": "takeoff",
    "land": "land",
    "goto": "goto",
    "rtl": "return",
    "hover": "hover",
    "arm": "arm",
    "disarm": "disarm",
}


def _to_flight_format(parsed: dict) -> dict:
    cmd_type = _INTENT_TO_FLIGHT_TYPE.get(parsed["intent"], parsed["intent"])
    result: dict = {
        "command_id": parsed.get("command_id", f"cmd_{int(time.time()*1000)}"),
        "type": cmd_type,
        "raw_text": parsed["raw_text"],
    }
    if parsed.get("altitude") is not None:
        result["altitude"] = parsed["altitude"]
    if cmd_type == "goto" and parsed.get("target_gps"):
        result["target_gps"] = parsed["target_gps"]
    if parsed.get("location"):
        result["entities"] = {"LOCATION": parsed["location"]}
    return result


class CommandRequest(BaseModel):
    text: str


@app.post("/parse")
async def parse_endpoint(request: CommandRequest):
    try:
        logger.info("Raw input: %s", request.text)
        parsed = parse_command(request.text)

        if not parsed["success"]:
            logger.info("Parse failed: %s — %s", request.text, parsed["reason"])
            return {
                "success": False,
                "intent": "unknown",
                "raw_text": request.text,
                "reason": parsed["reason"],
            }

        flight_cmd = _to_flight_format(parsed)
        logger.info("Parsed -> %s | alt=%.1f | gps=%s",
                     flight_cmd["type"], flight_cmd["altitude"], flight_cmd["target_gps"])

        # Publish to Kafka (degrade gracefully if Kafka is down)
        if producer:
            try:
                producer.send("drone.commands.flight", flight_cmd)
                producer.flush()
                logger.info("Published to drone.commands.flight: %s", flight_cmd["type"])
            except Exception as exc:
                logger.warning("Kafka send failed: %s", exc)

        return flight_cmd

    except Exception as e:
        logger.error("Parse endpoint error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    kafka_ok = producer is not None
    return {
        "status": "healthy",
        "service": "command-parser",
        "kafka_connected": kafka_ok,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
