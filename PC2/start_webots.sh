#!/usr/bin/env bash
# PC2 Webots Launcher — starts CIVE campus simulation with YOLO+PPO bridge
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

# Ensure venv is set up
VENV_DIR="$SCRIPT_DIR/venv"
if [ ! -f "$VENV_DIR/lib/python3.12/site-packages/system.pth" ]; then
    log "Creating venv at $VENV_DIR ..."
    python3 -m venv "$VENV_DIR" 2>/dev/null
    "$VENV_DIR/bin/python3" -m ensurepip --upgrade 2>/dev/null
    echo "/usr/lib/python3/dist-packages" > "$VENV_DIR/lib/python3.12/site-packages/system.pth"
    "$VENV_DIR/bin/python3" -m pip install pymavlink 2>/dev/null
fi

pkill -f "px4_bridge.py" 2>/dev/null || true
pgrep -x webots >/dev/null && pkill -x webots 2>/dev/null || true
sleep 1

SNAP="/snap/webots/current"
WEBOTS_BIN="$SNAP/usr/share/webots/bin/webots-bin"
if [ ! -x "$WEBOTS_BIN" ]; then
    echo -e "${RED}[ERROR]${NC} Webots binary not found at $WEBOTS_BIN"
    exit 1
fi
log "Webots binary: $WEBOTS_BIN"

export PATH="$VENV_DIR/bin:$PATH"
export WEBOTS_PYTHON=$VENV_DIR/bin/python3
export LD_LIBRARY_PATH="$SNAP/usr/share/webots/lib/webots:/lib/x86_64-linux-gnu:/usr/lib/x86_64-linux-gnu:$SNAP/lib/x86_64-linux-gnu:$SNAP/usr/lib/x86_64-linux-gnu"
export QT_QPA_PLATFORM=wayland
export QT_QPA_PLATFORM_PLUGIN_PATH="$SNAP/usr/share/webots/lib/webots/plugins/platforms"
export GIO_MODULE_DIR=/dev/null

log "Starting Webots..."
nohup "$WEBOTS_BIN" --mode=realtime "$WORLD_FILE" > /tmp/webots.log 2>&1 &
WEBOTS_PID=$!
log "Webots PID: $WEBOTS_PID"

log "Waiting for MAVLink bridge on UDP :14550..."
STARTED=0
for i in $(seq 1 120); do
    sleep 2
    if ss -uln 2>/dev/null | grep -q ":14550 "; then
        echo -e "${GREEN}[WEBOTS]${NC} MAVLink bridge ready on :14550"
        STARTED=1
        break
    fi
    if ! kill -0 $WEBOTS_PID 2>/dev/null; then
        echo -e "${RED}[ERROR]${NC} Webots died early. Check /tmp/webots.log"
        tail -30 /tmp/webots.log 2>/dev/null
        exit 1
    fi
done

if [ "$STARTED" -eq 0 ]; then
    echo -e "${RED}[ERROR]${NC} Bridge didn't start within 4 minutes. Check /tmp/webots.log"
    tail -50 /tmp/webots.log 2>/dev/null
    exit 1
fi

WORLD_NAME=$(basename "$WORLD_FILE")
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║ ${BOLD}UDOM CIVE CAMPUS — DRONE RUNNING${NC}${CYAN}                    ║${NC}"
echo -e "${CYAN}╠══════════════════════════════════════════════════════════╣${NC}"
echo -e "${CYAN}║${NC}  World       → $WORLD_NAME            ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  GPS ref     → -6.21745, 35.81396 | Alt: 1120m          ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  Detection   → YOLOv8n @ 640×480                       ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  Control     → PPO continuous [vx,vy,vz] ±3 m/s         ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  MAVLink     → UDP :14550 (connect QGC here)           ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}                                                          ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  Close Webots window to stop                            ${CYAN}║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"

wait $WEBOTS_PID
log "Webots stopped."
