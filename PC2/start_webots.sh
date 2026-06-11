#!/usr/bin/env bash
# PC2 Webots Launcher — starts simulation with MAVLink bridge
set -e

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
log()  { echo -e "${GREEN}[WEBOTS]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

WORLD_FILE="$SCRIPT_DIR/webots/worlds/mavic2pro_px4.wbt"
if [ ! -f "$WORLD_FILE" ]; then
    echo -e "${RED}[ERROR]${NC} World file not found: $WORLD_FILE"
    exit 1
fi

# Kill leftover processes
pkill -f "sensor_bridge.py" 2>/dev/null || true
pkill -f "object_detection_node.py" 2>/dev/null || true
pkill -f "px4_bridge.py" 2>/dev/null || true
pkill -f "mission_drone_controller.py" 2>/dev/null || true

pgrep -x webots >/dev/null && pkill -x webots 2>/dev/null || true
sleep 1

# Start Webots in background
log "Starting Webots..."
nohup webots --mode=realtime "$WORLD_FILE" > /tmp/webots.log 2>&1 &
WEBOTS_PID=$!
log "Webots PID: $WEBOTS_PID"

# Wait for the MAVLink bridge
log "Waiting for MAVLink bridge on UDP :14550..."
STARTED=0
for i in $(seq 1 60); do
    sleep 2
    if ss -uln 2>/dev/null | grep -q ":14550 "; then
        echo -e "${GREEN}[WEBOTS]${NC} MAVLink bridge ready on :14550"
        STARTED=1
        break
    fi
    if ! kill -0 $WEBOTS_PID 2>/dev/null; then
        echo -e "${RED}[ERROR]${NC} Webots died early. Check /tmp/webots.log"
        exit 1
    fi
done

if [ "$STARTED" -eq 0 ]; then
    echo -e "${RED}[ERROR]${NC} Bridge didn't start within 2 minutes. Check Webots."
    exit 1
fi

# Optional extras
if [ "$1" = "--full" ]; then
    log "Starting Sensor Bridge..."
    nohup python3 scripts/sensor_bridge.py 127.0.0.1 14550 --http-port 8090 > /tmp/sensor_bridge.log 2>&1 &
    log "Starting Object Detection..."
    nohup python3 scripts/object_detection_node.py --interval 3.0 > /tmp/object_detection.log 2>&1 &
fi

# Launch drone console in this terminal as background process
DRONE_CONSOLE_SCRIPT="$SCRIPT_DIR/scripts/enhanced_drone_console_v2.py"
if [ -f "$DRONE_CONSOLE_SCRIPT" ]; then
    log "Drone system ready. Starting console..."
    python3 "$DRONE_CONSOLE_SCRIPT" 127.0.0.1 14550
else
    log "Console script not found at $DRONE_CONSOLE_SCRIPT"
    wait $WEBOTS_PID
fi

# Cleanup when console exits
log "Stopping Webots..."
kill $WEBOTS_PID 2>/dev/null || true
wait $WEBOTS_PID 2>/dev/null || true
log "Stopped."
