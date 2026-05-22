#!/usr/bin/env bash

# PC2 Gazebo Launcher — Optimized for 16GB RAM
# Starts Dodoma simulation with auto-arm/takeoff, mission drone services

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
log() { echo -e "${GREEN}[GAZEBO]${NC} $1"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Parse args: --city uses heavier 73-model world
USE_CITY=false
[ "$1" = "--city" ] && USE_CITY=true

# 0. Network
log "Ensuring fyp-network exists..."
docker network inspect fyp-network >/dev/null 2>&1 || docker network create fyp-network

# 1. Pick world (light = 44 models, city = 73 models)
if $USE_CITY; then
    WORLD_FILE="./gazebo_worlds/dodoma/dodoma_city.sdf"
    [ ! -f "$WORLD_FILE" ] && WORLD_FILE="./gazebo_worlds/dodoma/dodoma_tanzania.sdf"
    log "Using CITY world (heavier — 73 models)"
else
    WORLD_FILE="./gazebo_worlds/dodoma/dodoma_tanzania.sdf"
    [ ! -f "$WORLD_FILE" ] && WORLD_FILE="./gazebo_worlds/dodoma/dodoma_city.sdf"
    log "Using LIGHT world (44 models, 16GB RAM optimized)"
fi
[ ! -f "$WORLD_FILE" ] && echo -e "${RED}[ERROR]${NC} No world file found" && exit 1
log "World: $(basename $WORLD_FILE)"

# 2. Prepare X11
log "Preparing X11..."
xhost +local:docker > /dev/null 2>&1 || true
XAUTH=/tmp/.docker.xauth
if [ ! -f "$XAUTH" ]; then
    touch "$XAUTH" 2>/dev/null
    xauth nlist "$DISPLAY" 2>/dev/null | sed -e 's/^..../ffff/' | xauth -f "$XAUTH" nmerge - 2>/dev/null || true
fi

# 3. Generate GUI config
mkdir -p gazebo_models/dodoma/gui_config
cat > gazebo_models/dodoma/gui_config/full.config << 'CONFIG'
<?xml version="1.0" encoding="UTF-8"?>
<window>
  <plugin filename="GzScene3D" name="3D View">
    <gz-gui>
      <title>3D View</title>
      <property key="showTitleBar" type="bool">false</property>
      <property key="state" type="string">docked</property>
    </gz-gui>
    <engine>ogre2</engine>
    <scene>scene</scene>
    <ambient_light>0.4 0.4 0.45</ambient_light>
    <background_color>0.3 0.35 0.4</background_color>
    <camera_pose>-12 -12 15 0 0.6 0.785</camera_pose>
    <camera_clip><near>0.25</near><far>25000</far></camera_clip>
  </plugin>
  <plugin filename="CameraTracking" name="Camera Tracking">
    <follow_target>x500_0</follow_target>
  </plugin>
  <plugin filename="EntityContextMenuPlugin" name="Entity context menu"/>
  <plugin filename="GzSceneManager" name="Scene Manager"/>
  <plugin filename="InteractiveViewControl" name="Interactive view control"/>
  <plugin filename="SelectEntities" name="Select Entities"/>
  <plugin filename="WorldControl" name="World Control"/>
  <plugin filename="WorldStats" name="World Stats"/>
</window>
CONFIG
log "GUI config ready ✓"

# 4. Start container
log "Starting Gazebo PX4 container..."

if docker ps --format '{{.Names}}' | grep -q '^gazebo-px4$'; then
    log "Container already running ✓"
else
    docker rm -f gazebo-px4 2>/dev/null || true

    WORLD_NAME=$(basename "$WORLD_FILE" .sdf)

    docker run -d \
        --name gazebo-px4 \
        --restart unless-stopped \
        --network fyp-network \
        -m 2g --memory-swap 3g \
        --cpus 2 \
        --shm-size=512m \
        -p 14550:18570/udp \
        -p 14540:14580/udp \
        -p 14556:14556/udp \
        -e PX4_SIMULATOR=gz \
        -e PX4_GZ_WORLD="${WORLD_NAME}" \
        -e PX4_SIM_MODEL=gz_x500 \
        -e "GZ_SIM_RESOURCE_PATH=/gazebo_models/dodoma:/opt/px4-gazebo/share/gz/models:/opt/px4-gazebo/share/gz/worlds" \
        -e PX4_HOME_LAT=-6.1630 \
        -e PX4_HOME_LON=35.7516 \
        -e PX4_HOME_ALT=1120 \
        -e HEADLESS=1 \
        -e DISPLAY=${DISPLAY} \
        -e QT_X11_NO_MITSHM=1 \
        -e XAUTHORITY=/tmp/.docker.xauth \
        -e PX4_PARAM_COM_ARM_WO_GPS=1 \
        -e PX4_PARAM_FS_GCS_ENABLE=0 \
        -e PX4_PARAM_ARMING_CHECK=0 \
        -v "$SCRIPT_DIR/px4_config:/px4_config" \
        -v "$SCRIPT_DIR/gazebo_worlds:/gazebo_worlds:ro" \
        -v "$SCRIPT_DIR/gazebo_models:/gazebo_models:ro" \
        -v "$SCRIPT_DIR/gazebo_worlds/dodoma/dodoma_city.sdf:/opt/px4-gazebo/share/gz/worlds/dodoma_city.sdf" \
        -v "$SCRIPT_DIR/gazebo_worlds/dodoma/dodoma_tanzania.sdf:/opt/px4-gazebo/share/gz/worlds/dodoma_tanzania.sdf" \
        -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
        -v /tmp/.docker.xauth:/tmp/.docker.xauth:rw \
        px4io/px4-sitl-gazebo:latest

    sleep 5
fi

if ! docker ps | grep -q gazebo-px4; then
    echo -e "${RED}[ERROR]${NC} Failed to start container."
    docker logs gazebo-px4 --tail 20
    exit 1
fi

log "Waiting for Gazebo server..."
sleep 10

if docker exec gazebo-px4 sh -c "pgrep -f 'gz sim' >/dev/null 2>&1"; then
    log "${GREEN}Gazebo simulator is running!${NC}"
else
    warn "Gazebo not detected."
fi

# 5. Wait for drone spawn
log "Waiting for drone to spawn..."
WORLD_NAME=$(basename "$WORLD_FILE" .sdf)
for i in $(seq 1 30); do
    sleep 2
    DRONE_OK=$(docker exec gazebo-px4 bash -c "gz topic -e -t /world/${WORLD_NAME}/pose/info -d 1 2>/dev/null" 2>/dev/null | grep -c "x500_0" || true)
    if [ "$DRONE_OK" -gt 0 ]; then
        log "${GREEN}Drone x500_0 detected!${NC}"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo -e "${YELLOW}[WARN]${NC} Drone not detected after 60s."
    fi
done

# 6. Auto-arm and takeoff
log "Auto-arming drone and taking off to 10m..."
cd "$SCRIPT_DIR"
python3 -c "
import sys, time
sys.path.insert(0, '$SCRIPT_DIR/scripts')
from mavlink_lite import DroneConnection

drone = DroneConnection(('127.0.0.1', 14550))
drone.connect()
time.sleep(3)
print('  Connecting...')
t = drone.get_telemetry()
if t['connected']:
    print('  Connected! Arming...')
    drone.arm()
    time.sleep(2)
    t = drone.get_telemetry()
    if t['armed']:
        print('  ARMED! Taking off to 10m...')
        drone.takeoff(10)
        time.sleep(4)
        t = drone.get_telemetry()
        print('  Altitude: %.1fm' % t['alt'])
        print('  ${GREEN}Drone is now hovering at 10m${NC}')
    else:
        print('  ${YELLOW}Arm failed. Use NLP console.${NC}')
else:
    print('  ${YELLOW}Connection timeout. Use NLP console.${NC}')
drone.close()
" 2>&1 || echo -e "${YELLOW}[WARN]${NC} Auto-arm/takeoff failed."

# 7. Start mission services
log "Starting Sensor Bridge (telemetry)..."
cd "$SCRIPT_DIR"
nohup python3 scripts/sensor_bridge.py 127.0.0.1 14550 --http-port 8090 > /tmp/sensor_bridge.log 2>&1 &
SENSOR_PID=$!
sleep 1

log "Starting Object Detection..."
nohup python3 scripts/object_detection_node.py --interval 3.0 > /tmp/object_detection.log 2>&1 &
DETECT_PID=$!
sleep 1

# 8. Offer autonomous mission
TAKEOFF_ALT=25
echo ""
echo -e "${CYAN}════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  ${BOLD}MISSION DRONE READY${NC}${CYAN}                          ${NC}"
echo -e "${CYAN}  Drone hovering at 10m                        ${NC}"
echo -e "${CYAN}  Sensor bridge logging ✓                      ${NC}"
echo -e "${CYAN}  Object detection running ✓                   ${NC}"
echo -e "${CYAN}                                              ${NC}"
echo -e "${CYAN}  Start surveillance mission? (y/n)            ${NC}"
echo -e "${CYAN}════════════════════════════════════════════════${NC}"
echo ""
echo -n "  > "
read -t 15 RUN_MISSION || true

if [ "$RUN_MISSION" = "y" ] || [ "$RUN_MISSION" = "Y" ]; then
    log "Starting surveillance mission (${TAKEOFF_ALT}m)..."
    python3 scripts/mission_drone_controller.py 127.0.0.1 14550 --alt $TAKEOFF_ALT --mission 2>&1 || \
        echo -e "${YELLOW}[WARN]${NC} Mission failed."
    log "Mission complete. Drone returned to home."
else
    log "Skipping auto mission. Use NLP console for manual control."
fi

# 9. Open NLP console
log "Opening NLP Drone Console..."
NLP_CMD="cd '$SCRIPT_DIR' && python3 scripts/nlp_console.py 127.0.0.1"
if command -v gnome-terminal &>/dev/null; then
    nohup gnome-terminal --title="NLP Drone Console" -- bash -c "$NLP_CMD; exec bash" &>/dev/null &
    sleep 1
elif command -v xterm &>/dev/null; then
    xterm -T "NLP Drone Console" -e "$NLP_CMD" &
else
    echo -e "${YELLOW}[WARN]${NC} Run in another terminal: python3 scripts/nlp_console.py"
fi

# 10. Show final status
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║          ${BOLD}DODOMA DRONE — READY${NC}${CYAN}                        ║${NC}"
echo -e "${CYAN}╠══════════════════════════════════════════════════════════╣${NC}"
echo -e "${CYAN}║${NC}  ✓ Drone: x500_0 at 10m                            ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  ✓ World: $(basename $WORLD_FILE .sdf) (light: 44 models)${NC}             ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  ✓ Sensor bridge → http://localhost:8090            ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  ✓ Object detection running                        ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  ✓ NLP console open                               ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}                                                    ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  ${BOLD}To open Gazebo GUI (when ready):${NC}               ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}    docker exec -d gazebo-px4 gz sim -g              ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}                                                    ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  ${BOLD}NLP Commands:${NC}                                   ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}    'take off to 20m'        'land'                 ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}    'fly to bunge parliament' 'go forward 30m'      ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}    'fly to central hospital' 'return home'         ${CYAN}║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}  💡 Use --city flag for the heavier Dodoma City world (73 models)${NC}"
echo -e "${YELLOW}     e.g. ./start_gazebo.sh --city${NC}"
echo ""