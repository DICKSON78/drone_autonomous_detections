#!/usr/bin/env bash

# PC2 Gazebo Launcher — Optimized for 16GB RAM
# Starts Dodoma simulation with auto-arm/takeoff, mission drone services

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
log() { echo -e "${GREEN}[GAZEBO]${NC} $1"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Parse world selection
# default: light (30 models), --city: 44 models, --full: 73 models
WORLD_NAME="dodoma_light"
case "$1" in
  --city)  WORLD_NAME="dodoma_tanzania" ;;
  --full)  WORLD_NAME="dodoma_city" ;;
esac

# Clean up leftover processes
pkill -f "sensor_bridge.py" 2>/dev/null || true
pkill -f "object_detection_node.py" 2>/dev/null || true

# 0. Network
log "Ensuring fyp-network exists..."
docker network inspect fyp-network >/dev/null 2>&1 || docker network create fyp-network

# 1. Verify world file
WORLD_FILE="./gazebo_worlds/dodoma/${WORLD_NAME}.sdf"
if [ ! -f "$WORLD_FILE" ]; then
    echo -e "${RED}[ERROR]${NC} World file not found: $WORLD_FILE"
    echo -e "${YELLOW}  Available: dodoma_light (30), dodoma_tanzania (44), dodoma_city (73)${NC}"
    exit 1
fi
MODEL_COUNT=$(grep -c '<model name=' "$WORLD_FILE")
log "World: ${WORLD_NAME}.sdf (${MODEL_COUNT} models)"

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
    <gz-gui><title>3D View</title><property key="showTitleBar" type="bool">false</property><property key="state" type="string">docked</property></gz-gui>
    <engine>ogre2</engine><scene>scene</scene>
    <ambient_light>0.4 0.4 0.45</ambient_light><background_color>0.3 0.35 0.4</background_color>
    <camera_pose>-12 -12 15 0 0.6 0.785</camera_pose>
    <camera_clip><near>0.25</near><far>25000</far></camera_clip>
  </plugin>
  <plugin filename="CameraTracking" name="Camera Tracking">
    <follow_target>x500_0</follow_target>
  </plugin>
  <plugin filename="WorldControl" name="World Control"/>
  <plugin filename="WorldStats" name="World Stats"/>
</window>
CONFIG
log "GUI config ready ✓"

# 4. Start container
log "Starting Gazebo PX4 container..."

docker rm -f gazebo-px4 2>/dev/null || true

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
    -v "$SCRIPT_DIR/gazebo_worlds/dodoma/dodoma_light.sdf:/opt/px4-gazebo/share/gz/worlds/dodoma_light.sdf" \
    -v "$SCRIPT_DIR/gazebo_worlds/dodoma/dodoma_tanzania.sdf:/opt/px4-gazebo/share/gz/worlds/dodoma_tanzania.sdf" \
    -v "$SCRIPT_DIR/gazebo_worlds/dodoma/dodoma_city.sdf:/opt/px4-gazebo/share/gz/worlds/dodoma_city.sdf" \
    -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
    -v /tmp/.docker.xauth:/tmp/.docker.xauth:rw \
    px4io/px4-sitl-gazebo:latest

sleep 5

if ! docker ps | grep -q gazebo-px4; then
    echo -e "${RED}[ERROR]${NC} Failed to start container."
    docker logs gazebo-px4 --tail 20
    exit 1
fi

log "Waiting for Gazebo server..."
sleep 8

# 5. Auto-launch Gazebo GUI with software rendering
log "Opening Gazebo GUI..."
docker exec -d gazebo-px4 sh -c " \
    mkdir -p /tmp/gui_config && \
    LIBGL_ALWAYS_SOFTWARE=1 MESA_GL_VERSION_OVERRIDE=3.3 \
    DISPLAY=:0 gz sim -g --gui-config /tmp/gui_config/full.config 2>/dev/null" 2>/dev/null || true

# Copy GUI config into container
docker cp gazebo_models/dodoma/gui_config/full.config gazebo-px4:/tmp/gui_config/ 2>/dev/null || true

# Re-launch GUI with config
docker exec -d gazebo-px4 sh -c "\
    LIBGL_ALWAYS_SOFTWARE=1 MESA_GL_VERSION_OVERRIDE=3.3 \
    DISPLAY=:0 gz sim -g --gui-config /tmp/gui_config/full.config 2>/dev/null" 2>/dev/null || \
    echo -e "${YELLOW}[WARN]${NC} GUI launch deferred. Run: docker exec gazebo-px4 gz sim -g"

# 6. Wait for drone spawn
log "Waiting for drone to spawn..."
for i in $(seq 1 20); do
    sleep 2
    DRONE_OK=$(docker exec gazebo-px4 bash -c "gz topic -e -t /world/${WORLD_NAME}/pose/info -d 1 2>/dev/null" 2>/dev/null | grep -c "x500_0" || true)
    if [ "$DRONE_OK" -gt 0 ]; then
        log "${GREEN}Drone x500_0 detected!${NC}"
        break
    fi
    if [ "$i" -eq 20 ]; then
        echo -e "${YELLOW}[WARN]${NC} Drone not detected after 40s — check 'docker logs gazebo-px4'"
    fi
done

# 7. Auto-arm and takeoff
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

# 8. Start mission services
log "Starting Sensor Bridge (telemetry)..."
cd "$SCRIPT_DIR"
nohup python3 scripts/sensor_bridge.py 127.0.0.1 14550 --http-port 8090 > /tmp/sensor_bridge.log 2>&1 &
SENSOR_PID=$!
sleep 1

log "Starting Object Detection..."
nohup python3 scripts/object_detection_node.py --interval 3.0 > /tmp/object_detection.log 2>&1 &
DETECT_PID=$!
sleep 1

# 9. Offer autonomous mission
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
    log "Skipping auto mission."
fi

# 10. Open NLP console
log "Opening NLP Drone Console..."
NLP_CMD="cd '$SCRIPT_DIR' && python3 scripts/nlp_console.py 127.0.0.1"
if command -v gnome-terminal &>/dev/null; then
    nohup gnome-terminal --title="NLP Drone Console" -- bash -c "$NLP_CMD; exec bash" &>/dev/null &
elif command -v xterm &>/dev/null; then
    xterm -T "NLP Drone Console" -e "$NLP_CMD" &
else
    echo -e "${YELLOW}[WARN]${NC} Open another terminal and run: python3 scripts/nlp_console.py 127.0.0.1"
fi

# 11. Final status
cat << EOF

${CYAN}╔══════════════════════════════════════════════════════════╗${NC}
${CYAN}║          ${BOLD}DODOMA DRONE — READY${NC}${CYAN}                        ║${NC}
${CYAN}╠══════════════════════════════════════════════════════════╣${NC}
${CYAN}║${NC}  ✓ Drone: x500_0 hovering at 10m                    ${CYAN}║${NC}
${CYAN}║${NC}  ✓ World: ${WORLD_NAME} (${MODEL_COUNT} models)                        ${CYAN}║${NC}
${CYAN}║${NC}  ✓ Sensor bridge → http://localhost:8090              ${CYAN}║${NC}
${CYAN}║${NC}  ✓ Object detection running                          ${CYAN}║${NC}
${CYAN}║${NC}                                                    ${CYAN}║${NC}
${CYAN}║${NC}  ${BOLD}Gazebo GUI:${NC}                                        ${CYAN}║${NC}
${CYAN}║${NC}    If GUI didn't open, run:                           ${CYAN}║${NC}
${CYAN}║${NC}    docker exec -e DISPLAY=\$DISPLAY gazebo-px4 gz sim -g${CYAN}║${NC}
${CYAN}║${NC}                                                    ${CYAN}║${NC}
${CYAN}║${NC}  ${BOLD}NLP Commands:${NC}                                   ${CYAN}║${NC}
${CYAN}║${NC}    'take off to 20m'        'land'                   ${CYAN}║${NC}
${CYAN}║${NC}    'fly to bunge parliament' 'go forward 30m'        ${CYAN}║${NC}
${CYAN}║${NC}    'fly to central hospital' 'return home'           ${CYAN}║${NC}
${CYAN}╚══════════════════════════════════════════════════════════╝${NC}
EOF
echo ""
echo -e "${YELLOW}  World options: ./start_gazebo.sh       → light (30 models)${NC}"
echo -e "${YELLOW}                 ./start_gazebo.sh --city → Tanzania (44 models)${NC}"
echo -e "${YELLOW}                 ./start_gazebo.sh --full → City (73 models)${NC}"
echo ""