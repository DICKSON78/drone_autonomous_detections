"""
PC3 Telemetry Collector Service
================================
FastAPI microservice that:
  1. Subscribes to Kafka topics (drone.telemetry.*)
  2. Processes and validates telemetry data
  3. Writes to InfluxDB time-series database
  4. Exposes REST endpoints for direct telemetry ingestion
  5. Bridges to Node.js API Gateway via HTTP

Runs on port 8004
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

import uvicorn
import yaml
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from kafka import KafkaConsumer, KafkaProducer
from pydantic import BaseModel, Field

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("telemetry-collector")

# ─── Config ───────────────────────────────────────────────────────────────────
CONFIG = {
    "influxdb": {
        "url":    os.getenv("INFLUXDB_URL",    "http://localhost:8086"),
        "token":  os.getenv("INFLUXDB_TOKEN",  "drone-telemetry-token"),
        "org":    os.getenv("INFLUXDB_ORG",    "drone-project"),
        "bucket": os.getenv("INFLUXDB_BUCKET", "drone_telemetry"),
    },
    "kafka": {
        "bootstrap_servers": os.getenv("KAFKA_BROKERS", "localhost:9092"),
        "group_id": "pc3-telemetry-collector",
    },
}

# ─── InfluxDB client ──────────────────────────────────────────────────────────
influx_client = InfluxDBClient(
    url=CONFIG["influxdb"]["url"],
    token=CONFIG["influxdb"]["token"],
    org=CONFIG["influxdb"]["org"],
)
write_api = influx_client.write_api(write_options=SYNCHRONOUS)
query_api = influx_client.query_api()

# ─── Global state ─────────────────────────────────────────────────────────────
consumers: Dict[str, KafkaConsumer] = {}
stats = {
    "messages_processed": 0,
    "messages_failed": 0,
    "started_at": datetime.now(timezone.utc).isoformat(),
}

# ─── FastAPI app ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="PC3 Telemetry Collector",
    description="Collects drone telemetry from Kafka and writes to InfluxDB",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Pydantic Models ──────────────────────────────────────────────────────────
class TelemetryIngest(BaseModel):
    drone_id: str
    data_type: str = Field(..., pattern="^(gps|battery|attitude|flight|detections|navigation|system)$")
    data: Dict[str, Any]
    timestamp: Optional[float] = None


class HealthStatus(BaseModel):
    status: str
    service: str
    timestamp: str
    influxdb_connected: bool
    kafka_topics: List[str]
    stats: Dict


# ─── Kafka consumer helpers ───────────────────────────────────────────────────
def create_consumer(topic: str, group_suffix: str = "") -> Optional[KafkaConsumer]:
    try:
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=CONFIG["kafka"]["bootstrap_servers"],
            group_id=f"{CONFIG['kafka']['group_id']}{group_suffix}",
            auto_offset_reset="latest",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            consumer_timeout_ms=1000,
            enable_auto_commit=True,
        )
        logger.info(f"Created consumer for topic: {topic}")
        return consumer
    except Exception as e:
        logger.error(f"Failed to create consumer for {topic}: {e}")
        return None


# ─── InfluxDB write helpers ───────────────────────────────────────────────────
def write(point: Point):
    try:
        write_api.write(bucket=CONFIG["influxdb"]["bucket"], record=point)
    except Exception as e:
        logger.error(f"InfluxDB write error: {e}")
        stats["messages_failed"] += 1


# ─── Data processors ──────────────────────────────────────────────────────────
def process_gps(data: Dict):
    point = (
        Point("gps_telemetry")
        .tag("drone_id",  data.get("drone_id", "drone_001"))
        .tag("source_pc", "PC1")
        .field("latitude",  float(data.get("latitude",  data.get("lat",  0))))
        .field("longitude", float(data.get("longitude", data.get("lon",  0))))
        .field("altitude",  float(data.get("altitude",  data.get("alt",  0))))
        .field("speed",     float(data.get("speed", 0)))
        .time(datetime.now(timezone.utc))
    )
    write(point)


def process_battery(data: Dict):
    point = (
        Point("battery_telemetry")
        .tag("drone_id",  data.get("drone_id", "drone_001"))
        .tag("source_pc", "PC1")
        .field("percentage",  float(data.get("percentage",   data.get("remaining_percent", 0))))
        .field("voltage",     float(data.get("voltage_v",    data.get("voltage",    0))))
        .field("current",     float(data.get("current_battery", data.get("current", 0))))
        .field("temperature", float(data.get("temperature_degc", data.get("temperature", 0))))
        .time(datetime.now(timezone.utc))
    )
    write(point)


def process_attitude(data: Dict):
    point = (
        Point("attitude_telemetry")
        .tag("drone_id",  data.get("drone_id", "drone_001"))
        .tag("source_pc", "PC1")
        .field("roll_deg",  float(data.get("roll_deg",  0)))
        .field("pitch_deg", float(data.get("pitch_deg", 0)))
        .field("yaw_deg",   float(data.get("yaw_deg",   0)))
        .time(datetime.now(timezone.utc))
    )
    write(point)


def process_flight(data: Dict):
    point = (
        Point("flight_status")
        .tag("drone_id",    data.get("drone_id", "drone_001"))
        .tag("source_pc",   "PC1")
        .tag("is_armed",    str(data.get("is_armed",   False)))
        .tag("is_flying",   str(data.get("is_flying",  False)))
        .tag("flight_mode", data.get("flight_mode", "unknown"))
        .field("altitude_m", float(data.get("altitude", 0)))
        .field("speed_ms",   float(data.get("speed",    0)))
        .time(datetime.now(timezone.utc))
    )
    write(point)


def process_detections(data: Dict):
    detections = data.get("detections", [])
    for det in detections:
        bbox = det.get("bbox", [0, 0, 0, 0])
        point = (
            Point("object_detections")
            .tag("drone_id",    data.get("drone_id", "drone_001"))
            .tag("source_pc",   "PC2")
            .tag("object_class", det.get("class_name", det.get("label", "unknown")))
            .field("confidence",  float(det.get("confidence", 0)))
            .field("bbox_x",      float(bbox[0] if len(bbox) > 0 else 0))
            .field("bbox_y",      float(bbox[1] if len(bbox) > 1 else 0))
            .field("bbox_width",  float(bbox[2] if len(bbox) > 2 else 0))
            .field("bbox_height", float(bbox[3] if len(bbox) > 3 else 0))
            .time(datetime.now(timezone.utc))
        )
        write(point)


def process_velocity(data: Dict):
    point = (
        Point("velocity_telemetry")
        .tag("drone_id",  data.get("drone_id", "drone_001"))
        .tag("source_pc", "PC1")
        .field("north", float(data.get("north", 0)))
        .field("east",  float(data.get("east",  0)))
        .field("down",  float(data.get("down",  0)))
        .field("speed", float(data.get("speed", 0)))
        .time(datetime.now(timezone.utc))
    )
    write(point)


def process_navigation(data: Dict):
    point = (
        Point("navigation_telemetry")
        .tag("drone_id",   data.get("drone_id", "drone_001"))
        .tag("source_pc",  "PC2")
        .tag("next_action", data.get("next_action", "unknown"))
        .field("confidence",     float(data.get("confidence",     0)))
        .field("estimated_time", float(data.get("estimated_time", 0)))
        .field("path_length",    float(len(data.get("path", []))))
        .time(datetime.now(timezone.utc))
    )
    write(point)


def process_system(data: Dict):
    drone_state = data.get("drone_state", {})
    point = (
        Point("system_metrics")
        .tag("drone_id",  data.get("drone_id", "drone_001"))
        .tag("source_pc", "PC1")
        .field("battery_percentage", float(drone_state.get("battery", 0)))
        .field("cpu_usage",    float(data.get("cpu_usage",    0)))
        .field("memory_usage", float(data.get("memory_usage", 0)))
        .field("disk_usage",   float(data.get("disk_usage",   0)))
        .time(datetime.now(timezone.utc))
    )
    write(point)


TOPIC_PROCESSORS = {
    "drone.telemetry.gps":        process_gps,
    "drone.telemetry.battery":    process_battery,
    "drone.telemetry.attitude":   process_attitude,
    "drone.telemetry.velocity":   process_velocity,
    "drone.telemetry.flight":     process_flight,
    "drone.detections.objects":   process_detections,
    "drone.navigation.decisions": process_navigation,
    "drone.alerts.critical":      process_system,
    "drone.status.system":        process_system,
    "drone.status.flight":        lambda d: logger.info(f"[STATUS] {d}"),
}


# ─── Kafka consumer loop ──────────────────────────────────────────────────────
async def consume_topic(topic: str, processor):
    consumer = create_consumer(topic)
    if not consumer:
        return
    consumers[topic] = consumer
    logger.info(f"Started consuming: {topic}")

    loop = asyncio.get_event_loop()

    try:
        while True:
            messages = await loop.run_in_executor(
                None, lambda: consumer.poll(timeout_ms=1000)
            )
            for tp, records in messages.items():
                for record in records:
                    try:
                        await loop.run_in_executor(None, processor, record.value)
                        stats["messages_processed"] += 1
                    except Exception as e:
                        logger.error(f"[{topic}] Processing error: {e}")
                        stats["messages_failed"] += 1
            await asyncio.sleep(0.05)
    except asyncio.CancelledError:
        logger.info(f"Consumer cancelled: {topic}")
    except Exception as e:
        logger.error(f"Consumer error [{topic}]: {e}")
    finally:
        consumer.close()
        consumers.pop(topic, None)


async def start_all_consumers():
    tasks = [
        asyncio.create_task(consume_topic(topic, processor))
        for topic, processor in TOPIC_PROCESSORS.items()
    ]
    await asyncio.gather(*tasks, return_exceptions=True)


# ─── REST Endpoints ───────────────────────────────────────────────────────────
@app.post("/telemetry")
async def ingest_telemetry(payload: TelemetryIngest):
    """Accept telemetry via REST and write to InfluxDB."""
    processor_map = {
        "gps":        process_gps,
        "battery":    process_battery,
        "attitude":   process_attitude,
        "velocity":   process_velocity,
        "flight":     process_flight,
        "detections": process_detections,
        "navigation": process_navigation,
        "system":     process_system,
    }
    processor = processor_map.get(payload.data_type)
    if not processor:
        raise HTTPException(status_code=400, detail=f"Unknown data_type: {payload.data_type}")

    merged = {"drone_id": payload.drone_id, **payload.data}
    processor(merged)
    stats["messages_processed"] += 1
    return {"status": "success", "drone_id": payload.drone_id, "data_type": payload.data_type}


@app.get("/health", response_model=HealthStatus)
def health_check():
    """Service health check."""
    influxdb_ok = False
    try:
        influx_client.health()
        influxdb_ok = True
    except Exception:
        pass

    return HealthStatus(
        status="healthy" if influxdb_ok else "degraded",
        service="telemetry-collector",
        timestamp=datetime.now(timezone.utc).isoformat(),
        influxdb_connected=influxdb_ok,
        kafka_topics=list(consumers.keys()),
        stats=stats,
    )


@app.get("/status")
def get_status():
    """Detailed service status."""
    return {
        "service":   "pc3-telemetry-collector",
        "version":   "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime":    stats["started_at"],
        "consumers": list(consumers.keys()),
        "stats":     stats,
        "influxdb":  CONFIG["influxdb"],
        "kafka":     CONFIG["kafka"],
    }


@app.get("/metrics")
def get_metrics():
    """Prometheus-style metrics."""
    return {
        "messages_processed_total": stats["messages_processed"],
        "messages_failed_total":    stats["messages_failed"],
        "active_consumers":         len(consumers),
        "success_rate": (
            round(stats["messages_processed"] /
                  max(stats["messages_processed"] + stats["messages_failed"], 1) * 100, 2)
        ),
    }


# ─── Startup / Shutdown ───────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    logger.info("=" * 50)
    logger.info("PC3 TELEMETRY COLLECTOR STARTING")
    logger.info("=" * 50)

    try:
        health = influx_client.health()
        logger.info(f"InfluxDB status: {health.status}")
    except Exception as e:
        logger.error(f"InfluxDB connection failed: {e}")

    asyncio.create_task(start_all_consumers())


@app.on_event("shutdown")
async def shutdown():
    logger.info("Shutting down telemetry collector...")
    for consumer in consumers.values():
        consumer.close()
    influx_client.close()
    logger.info("Shutdown complete.")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8004, log_level="info")
