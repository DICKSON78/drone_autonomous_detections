import asyncio
import json
import logging
import math
import os
import socket
import sys
import time
from datetime import datetime
from typing import Optional

import fastapi
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from pymavlink.dialects.v20 import common as mavlink

_nlp_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "PC2", "src")
if not os.path.isdir(_nlp_path):
    _nlp_path = "/app/nlp"
sys.path.insert(0, _nlp_path)
from nlp_module import DroneNLP, parse_command

sys.path.insert(0, os.path.dirname(__file__))
from telemetry_store import (
    insert_telemetry, insert_event, insert_detection, get_telemetry_history,
    get_events, cleanup_old, get_latest_telemetry
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PC3")

# ── Config ──
BRIDGE_HOST = os.environ.get("BRIDGE_HOST", "127.0.0.1")
BRIDGE_PORT = int(os.environ.get("BRIDGE_PORT", "14550"))
APP_PORT = int(os.environ.get("APP_PORT", "8007"))
_local_renderer = os.path.join(os.path.dirname(__file__), "..", "renderer")
RENDERER_DIR = _local_renderer if os.path.isdir(_local_renderer) else os.path.join(os.path.dirname(__file__), "renderer")

# ── State ──
app = fastapi.FastAPI(title="Drone Command Center")
nlp = DroneNLP()
mav = mavlink.MAVLink(None, srcSystem=2, srcComponent=1)

bridge_sock: Optional[socket.socket] = None
bridge_addr: Optional[tuple] = None
detection_sock: Optional[socket.socket] = None
connected_clients: set[WebSocket] = set()

drone_state = {
    "connected": False, "armed": False, "in_air": False,
    "altitude": 0.0, "heading": 0.0, "speed": 0.0, "battery": 100.0,
    "lat": 0.0, "lon": 0.0, "waypoint": 0, "vx": 0.0, "vy": 0.0, "vz": 0.0,
    "detections": [],
}
_telem_counter = 0
_last_bridge_contact = time.time()


def _init_socket():
    global bridge_sock, bridge_addr, _last_bridge_contact
    try:
        bridge_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        bridge_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        bridge_sock.bind(("0.0.0.0", 14552))
        bridge_sock.settimeout(0.05)
        bridge_addr = (BRIDGE_HOST, BRIDGE_PORT)
        _last_bridge_contact = time.time()
        # Send discovery heartbeat so bridge knows where to send telemetry
        try:
            hb = mav.heartbeat_encode(2, 0, 0, 0, 0).pack(mav)
            bridge_sock.sendto(hb, bridge_addr)
        except Exception:
            pass
        drone_state["connected"] = True
        logger.info(f"Bridge: {bridge_addr} (bound :14552)")
    except Exception as e:
        logger.error(f"Sock init: {e}")
        drone_state["connected"] = False


def _init_detection_socket():
    global detection_sock
    try:
        detection_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        detection_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        detection_sock.bind(("0.0.0.0", 14551))
        detection_sock.settimeout(0.05)
        logger.info("Detection listener on :14551")
    except Exception as e:
        logger.error(f"Detection sock init: {e}")


def _send_mavlink(msg) -> bool:
    if not bridge_sock or not bridge_addr:
        return False
    try:
        bridge_sock.sendto(msg.pack(mav), bridge_addr)
        return True
    except Exception as e:
        logger.error(f"MAVLink send: {e}")
        return False


# ── MAVLink Commands ──

def _cmd_takeoff(alt: float = 10.0) -> str:
    _send_mavlink(mav.command_long_encode(1, 1, mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 1, 1.0, 0, 0, 0, 0, 0, 0))
    time.sleep(0.05)
    _send_mavlink(mav.command_long_encode(1, 1, mavlink.MAV_CMD_NAV_TAKEOFF, 1, 0, 0, 0, 0, 0, 0, alt))
    insert_event("command", f"takeoff {alt}m")
    return f"Taking off to {alt:.0f}m."

def _cmd_land() -> str:
    _send_mavlink(mav.command_long_encode(1, 1, mavlink.MAV_CMD_NAV_LAND, 1, 0, 0, 0, 0, 0, 0, 0))
    insert_event("command", "land")
    return "Landing now."

def _cmd_rtl() -> str:
    _send_mavlink(mav.command_long_encode(1, 1, mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH, 1, 0, 0, 0, 0, 0, 0, 0))
    insert_event("command", "rtl")
    return "Returning to launch point."

def _cmd_goto(lat: float, lon: float, alt: float = 15.0) -> str:
    _send_mavlink(mav.command_long_encode(1, 1, mavlink.MAV_CMD_NAV_WAYPOINT, 1, 0, 0, 0, 0, lat, lon, alt))
    insert_event("command", f"goto {lat:.4f},{lon:.4f}")
    return f"Navigating to {lat:.4f}, {lon:.4f} at {alt:.0f}m."

def _cmd_hover() -> str:
    _send_mavlink(mav.set_position_target_local_ned_encode(
        1, 1, 1, mavlink.MAV_FRAME_BODY_OFFSET_NED, 0x07, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0))
    insert_event("command", "hover")
    return "Hovering in place."

def _cmd_arm() -> str:
    _send_mavlink(mav.command_long_encode(1, 1, mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 1, 1.0, 0, 0, 0, 0, 0, 0))
    insert_event("command", "arm")
    return "Armed."

def _cmd_disarm() -> str:
    _send_mavlink(mav.command_long_encode(1, 1, mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 1, 0.0, 0, 0, 0, 0, 0, 0))
    insert_event("command", "disarm")
    return "Disarmed."

_COMMAND_MAP = {
    "takeoff": lambda p: _cmd_takeoff(p.get("altitude", 10.0)),
    "land": lambda p: _cmd_land(),
    "rtl": lambda p: _cmd_rtl(),
    "goto": lambda p: _cmd_goto(
        p.get("target_gps", {}).get("lat", 0),
        p.get("target_gps", {}).get("lon", 0),
        p.get("altitude", 15.0)),
    "hover": lambda p: _cmd_hover(),
    "arm": lambda p: _cmd_arm(),
    "disarm": lambda p: _cmd_disarm(),
}


def _execute_nlu(parsed: dict) -> str:
    if not parsed.get("success"):
        return parsed.get("reason", "Command not understood.")
    handler = _COMMAND_MAP.get(parsed["intent"])
    if not handler:
        return f"Can't handle '{parsed['intent']}'."
    feedback = handler(parsed)
    drone_state["waypoint"] += 1 if parsed["intent"] in ("takeoff", "goto") else 0
    return feedback


# ── Bridge polling ──

def _handle_telem(msg):
    global _telem_counter, _last_bridge_contact
    _last_bridge_contact = time.time()
    drone_state["connected"] = True
    t = msg.get_type()
    if t == "HEARTBEAT":
        drone_state["armed"] = bool(msg.base_mode & 0x80)
        drone_state["in_air"] = (msg.system_status == 4)
    elif t == "GLOBAL_POSITION_INT":
        drone_state["lat"] = msg.lat / 1e7
        drone_state["lon"] = msg.lon / 1e7
        drone_state["altitude"] = msg.relative_alt / 1000.0
        drone_state["heading"] = msg.hdg / 100.0
        drone_state["vx"] = msg.vx / 100.0
        drone_state["vy"] = msg.vy / 100.0
        drone_state["vz"] = msg.vz / 100.0
    elif t == "VFR_HUD":
        drone_state["speed"] = msg.groundspeed
        drone_state["heading"] = msg.heading
        drone_state["altitude"] = msg.alt
    elif t == "SYS_STATUS":
        drone_state["battery"] = (msg.battery_remaining
                                  if msg.battery_remaining >= 0
                                  else drone_state["battery"])
    elif t == "STATUSTEXT":
        text = msg.text.rstrip(b"\x00").decode("utf-8", errors="replace")
        if text:
            insert_event("status", text)

    _telem_counter += 1
    if _telem_counter >= 10:
        insert_telemetry(drone_state)
        _telem_counter = 0


async def _poll_bridge():
    while True:
        try:
            if bridge_sock:
                data, addr = bridge_sock.recvfrom(4096)
                for byte in data:
                    try:
                        msg = mav.parse_char(bytes([byte]))
                        if msg:
                            _handle_telem(msg)
                    except Exception:
                        pass
            else:
                _init_socket()
        except socket.timeout:
            pass
        except BlockingIOError:
            pass
        except Exception as e:
            logger.error(f"Poll: {e}")

        try:
            if detection_sock:
                data, addr = detection_sock.recvfrom(65536)
                try:
                    det = json.loads(data.decode())
                    if isinstance(det, dict) and "items" in det:
                        drone_state["detections"] = det["items"]
                        for item in det["items"]:
                            insert_detection(item)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass
        except socket.timeout:
            pass
        except BlockingIOError:
            pass
        except Exception as e:
            logger.error(f"Detection poll: {e}")

        # Mark disconnected if no contact for 5s
        if time.time() - _last_bridge_contact > 5.0:
            drone_state["connected"] = False

        await _broadcast_state()
        await asyncio.sleep(0.05)

    # Also periodically cleanup old data
    cleanup_old(48)


# ── WebSocket ──

async def _broadcast_state():
    global connected_clients
    payload = json.dumps(drone_state)
    dead = set()
    for ws in connected_clients:
        try:
            await ws.send_text(payload)
        except Exception:
            dead.add(ws)
    connected_clients -= dead


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    connected_clients.add(ws)
    logger.info(f"WS client. Total: {len(connected_clients)}")
    try:
        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)
            text = data.get("text", "").strip()
            if not text:
                continue
            nlu_result = parse_command(text)
            logger.info(f"NLU: {text} -> {nlu_result.get('intent')}")
            feedback = _execute_nlu(nlu_result) if nlu_result["success"] else nlu_result.get("reason", "Say again?")
            await ws.send_text(json.dumps({
                "type": "response", "text": feedback,
                "intent": nlu_result.get("intent", "unknown"),
                "confidence": nlu_result.get("confidence", 0.0),
            }))
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WS: {e}")
    finally:
        connected_clients.discard(ws)


# ── HTTP routes ──

@app.get("/api/state")
async def api_state():
    return drone_state

@app.get("/api/health")
async def health():
    return {
        "status": "ok", "bridge": drone_state["connected"],
        "armed": drone_state["armed"], "in_air": drone_state["in_air"],
        "clients": len(connected_clients), "uptime": (datetime.now() - nlp.session_start).total_seconds(),
    }

@app.get("/api/telemetry")
async def api_telemetry(hours: float = 1):
    return get_telemetry_history(hours)

@app.get("/api/events")
async def api_events(limit: int = 100):
    return get_events(limit)

@app.get("/api/radar")
async def api_radar():
    """Return radar data (detections + drone state) for the canvas renderer."""
    return {
        "heading": drone_state.get("heading", 0),
        "altitude": drone_state.get("altitude", 0),
        "speed": drone_state.get("speed", 0),
        "detections": drone_state.get("detections", []),
        "lat": drone_state.get("lat", 0),
        "lon": drone_state.get("lon", 0),
        "vx": drone_state.get("vx", 0),
        "vy": drone_state.get("vy", 0),
        "vz": drone_state.get("vz", 0),
        "armed": drone_state.get("armed", False),
        "in_air": drone_state.get("in_air", False),
    }

# ── Static files ──
app.mount("/", StaticFiles(directory=RENDERER_DIR, html=True), name="renderer")

# ── Startup ──

@app.on_event("startup")
async def startup():
    _init_socket()
    _init_detection_socket()
    asyncio.create_task(_poll_bridge())

@app.on_event("shutdown")
async def shutdown():
    if bridge_sock:
        bridge_sock.close()
    if detection_sock:
        detection_sock.close()

if __name__ == "__main__":
    logger.info(f"PC3 Desktop backend on :{APP_PORT}, bridge at {BRIDGE_HOST}:{BRIDGE_PORT}")
    uvicorn.run(app, host="0.0.0.0", port=APP_PORT)
