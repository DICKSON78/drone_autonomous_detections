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

# Kill leftover processes (only our bridge, not random Python)
pkill -f "sensor_bridge.py" 2>/dev/null || true
pkill -f "object_detection_node.py" 2>/dev/null || true
pkill -f "px4_bridge.py" 2>/dev/null || true
pkill -f "mission_drone_controller.py" 2>/dev/null || true

pgrep -x webots >/dev/null && pkill -x webots 2>/dev/null || true
sleep 1

# Start Webots in realtime mode (controller auto-launches from world file)
log "Starting Webots..."
nohup webots --mode=realtime "$WORLD_FILE" > /tmp/webots.log 2>&1 &
WEBOTS_PID=$!
log "Webots PID: $WEBOTS_PID"

# Wait for the MAVLink bridge controller
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

# Optional: start sensor bridge + object detection (off by default to save RAM)
if [ "$1" = "--full" ]; then
    log "Starting Sensor Bridge..."
    nohup python3 scripts/sensor_bridge.py 127.0.0.1 14550 --http-port 8090 > /tmp/sensor_bridge.log 2>&1 &
    log "Starting Object Detection..."
    nohup python3 scripts/object_detection_node.py --interval 3.0 > /tmp/object_detection.log 2>&1 &
fi

# Launch the drone console in a new terminal window
DRONE_CONSOLE_SCRIPT="$SCRIPT_DIR/scripts/drone_console.py"
CONSOLE_PID=""
if [ -f "$DRONE_CONSOLE_SCRIPT" ]; then
    log "Launching Drone Console terminal..."
    # Detect terminal emulator and launch console
    TERMINAL_CMD=""
    if command -v ptyxis &>/dev/null; then
        TERMINAL_CMD="ptyxis -x"
    elif command -v gnome-terminal &>/dev/null; then
        TERMINAL_CMD="gnome-terminal --"
    elif command -v x-terminal-emulator &>/dev/null; then
        # Check what x-terminal-emulator resolves to
        REAL_TERM=$(readlink -f "$(command -v x-terminal-emulator)" 2>/dev/null)
        if echo "$REAL_TERM" | grep -q "ptyxis"; then
            TERMINAL_CMD="ptyxis -x"
        elif echo "$REAL_TERM" | grep -q "gnome-terminal"; then
            TERMINAL_CMD="gnome-terminal --"
        else
            TERMINAL_CMD="x-terminal-emulator -e"
        fi
    elif command -v xterm &>/dev/null; then
        TERMINAL_CMD="xterm -hold -e"
    elif command -v konsole &>/dev/null; then
        TERMINAL_CMD="konsole --hold -e"
    fi

    if [ -n "$TERMINAL_CMD" ]; then
        $TERMINAL_CMD "$SCRIPT_DIR/scripts/drone_console_launcher.sh" &
        CONSOLE_PID=$!
    else
        log "No terminal emulator found. Run manually: python3 scripts/drone_console.py"
    fi
else
    log "Drone console not found at $DRONE_CONSOLE_SCRIPT"
fi

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║          ${BOLD}WEBOTS DRONE — RUNNING${NC}${CYAN}                        ║${NC}"
echo -e "${CYAN}╠══════════════════════════════════════════════════════════╣${NC}"
echo -e "${CYAN}║${NC}  MAVLink bridge → UDP :14550                          ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  Drone Console → $(basename "$DRONE_CONSOLE_SCRIPT") in new terminal         ${CYAN}║${NC}"
if [ "$1" = "--full" ]; then
    echo -e "${CYAN}║${NC}  Telemetry → http://localhost:8090                     ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  Object detection running                              ${CYAN}║${NC}"
fi
echo -e "${CYAN}║${NC}                                                          ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  Commands: [1]=Arm+Takeoff  [2]=Arm  [3]=Land           ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}           [4]=Disarm  [5]=Return Home  [6]=Set Speed    ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}           [G]=Goto GPS  [Q]=Quit                        ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}                                                          ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  Close Webots window OR press Q in console to stop      ${CYAN}║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"

wait $WEBOTS_PID

# Cleanup: kill the console when Webots exits
if [ -n "$CONSOLE_PID" ]; then
    kill $CONSOLE_PID 2>/dev/null || true
fi
log "Webots stopped."
