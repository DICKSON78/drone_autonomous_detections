#!/usr/bin/env bash

# PC2 Gazebo Launcher
# Starts the Dodoma simulation environment, GUI, and drone control console

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

log() { echo -e "${GREEN}[GAZEBO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 0. Ensure shared network exists
log "Ensuring fyp-network exists..."
docker network inspect fyp-network >/dev/null 2>&1 || docker network create fyp-network

# 1. Verify files exist
log "Verifying custom world and models..."
WORLD_FILE="./gazebo_worlds/dodoma/dodoma_tanzania.sdf"
MODEL_TREE="./gazebo_models/dodoma/acacia_tree/model.config"

if [ ! -f "$WORLD_FILE" ]; then
    error "World file not found at $WORLD_FILE"
    exit 1
fi
log "World file found ✓"

if [ ! -f "$MODEL_TREE" ]; then
    error "Tree model not found at $MODEL_TREE"
    exit 1
fi
log "Acacia tree model found ✓"

# 2. Prepare X11
log "Preparing X11..."
xhost +local:docker > /dev/null 2>&1 || true
XAUTH=/tmp/.docker.xauth
if [ ! -f "$XAUTH" ]; then
    touch "$XAUTH" 2>/dev/null
    xauth nlist "$DISPLAY" 2>/dev/null | sed -e 's/^..../ffff/' | xauth -f "$XAUTH" nmerge - 2>/dev/null || true
fi

# 3. Start the container
log "Starting Gazebo PX4 container with Dodoma world..."
log "  ${BOLD}Simulator:${NC} Gazebo Harmonic"
log "  ${BOLD}World:${NC} Dodoma, Tanzania (realistic city)"
log "  ${BOLD}Drone:${NC} PX4 x500"
docker-compose up -d gazebo-px4
sleep 5

if ! docker ps | grep -q gazebo-px4; then
    error "Failed to start container. Check: docker-compose logs gazebo-px4"
    exit 1
fi

log "Container started! Waiting for Gazebo..."
sleep 8

# Verify Gazebo is running
if docker exec gazebo-px4 sh -c "pgrep -f 'gz sim' >/dev/null 2>&1"; then
    log "${GREEN}Gazebo simulator is running!${NC}"
else
    warn "Gazebo not detected yet. Check: docker logs gazebo-px4"
fi

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║          ${BOLD}DODOMA ENVIRONMENT - READY${NC}${CYAN}                         ║${NC}"
echo -e "${CYAN}╠══════════════════════════════════════════════════════════════╣${NC}"
echo -e "${CYAN}║${NC}  ${BOLD}Location:${NC}  Dodoma, Tanzania                         ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  ${BOLD}Area:${NC}       Roads, buildings, acacia trees, hills   ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  ${BOLD}Drone:${NC}      x500 (spawned by PX4)                   ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  ${BOLD}GUI:${NC}        Opening in new window...                 ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  ${BOLD}Console:${NC}    Opening drone control terminal...        ${CYAN}║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# 4. Open Gazebo GUI in background
log "Opening Gazebo GUI..."
docker exec -d gazebo-px4 sh -c "DISPLAY=:0 gz sim -g &" 2>/dev/null || \
    warn "Could not open GUI automatically. Run: docker exec -it gazebo-px4 gz sim -g"

# 5. Open drone console in a new terminal
log "Opening Drone Control Console..."
CONSOLE_CMD="cd '$SCRIPT_DIR' && python3 scripts/drone_console.py 127.0.0.1"

if command -v gnome-terminal &>/dev/null; then
    nohup gnome-terminal --title="Drone Control Console" -- bash -c "$CONSOLE_CMD; exec bash" &>/dev/null &
    sleep 1
elif command -v xterm &>/dev/null; then
    xterm -T "Drone Control Console" -e "$CONSOLE_CMD" &
    sleep 1
else
    warn "No terminal emulator found. Run console manually:"
    warn "  python3 scripts/drone_console.py"
fi

# 6. Offer auto-flight option
echo ""
echo -e "${YELLOW}══════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}  Start autonomous flight mission?${NC}"
echo -e "${YELLOW}  The drone will auto-arm, takeoff, and fly waypoints${NC}"
echo -e "${YELLOW}══════════════════════════════════════════════════════════════${NC}"
echo -n "  [y/N]: "
read -r START_MISSION
if [[ "$START_MISSION" =~ ^[Yy]$ ]]; then
    log "Starting autonomous flight mission..."
    if command -v gnome-terminal &>/dev/null; then
        nohup gnome-terminal --title="Auto Flight Mission" -- bash -c \
            "python3 '$SCRIPT_DIR/scripts/auto_flight.py' 127.0.0.1 15; exec bash" &>/dev/null &
    else
        python3 "$SCRIPT_DIR/scripts/auto_flight.py" 127.0.0.1 15 &
    fi
fi

echo ""
log "All systems ready!"
echo -e "  ${BOLD}GUI:${NC}     docker exec -it gazebo-px4 gz sim -g"
echo -e "  ${BOLD}Console:${NC} python3 scripts/drone_console.py"
echo -e "  ${BOLD}Mission:${NC}  python3 scripts/auto_flight.py"
echo -e "  ${BOLD}Logs:${NC}     docker logs gazebo-px4"
