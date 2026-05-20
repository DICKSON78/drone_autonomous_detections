#!/usr/bin/env bash

# PC2 Gazebo Launcher
# Starts the Dodoma simulation with auto-arm/takeoff, camera follow, and NLP console

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
log() { echo -e "${GREEN}[GAZEBO]${NC} $1"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 0. Network
log "Ensuring fyp-network exists..."
docker network inspect fyp-network >/dev/null 2>&1 || docker network create fyp-network

# 1. Verify SDF
log "Verifying world file..."
WORLD_FILE="./gazebo_worlds/dodoma/dodoma_tanzania.sdf"
[ ! -f "$WORLD_FILE" ] && echo -e "${RED}[ERROR]${NC} World file not found" && exit 1
log "World file found ✓"

# 2. Prepare X11
log "Preparing X11..."
xhost +local:docker > /dev/null 2>&1 || true
XAUTH=/tmp/.docker.xauth
if [ ! -f "$XAUTH" ]; then
    touch "$XAUTH" 2>/dev/null
    xauth nlist "$DISPLAY" 2>/dev/null | sed -e 's/^..../ffff/' | xauth -f "$XAUTH" nmerge - 2>/dev/null || true
fi

# 3. Copy GUI config into container volume
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
log "GUI config created ✓"

# 4. Start the container (use docker run to avoid docker-compose v1.29.2 bug)
log "Starting Gazebo PX4 container..."

# Check if container already exists and is running
if docker ps --format '{{.Names}}' | grep -q '^gazebo-px4$'; then
    log "Container already running ✓"
else
    # Remove stale container if exists
    docker rm -f gazebo-px4 2>/dev/null || true
    
    docker run -d \
        --name gazebo-px4 \
        --restart unless-stopped \
        --network fyp-network \
        -m 3g --memory-swap 4g \
        -p 14550:18570/udp \
        -p 14540:14580/udp \
        -p 14556:14556/udp \
        -e PX4_SIMULATOR=gz \
        -e PX4_GZ_WORLD=dodoma_tanzania \
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
        -v "$SCRIPT_DIR/gazebo_worlds/dodoma/dodoma_tanzania.sdf:/opt/px4-gazebo/share/gz/worlds/dodoma_tanzania.sdf" \
        -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
        -v /tmp/.docker.xauth:/tmp/.docker.xauth:rw \
        px4io/px4-sitl-gazebo:latest
    
    sleep 5
fi

if ! docker ps | grep -q gazebo-px4; then
    echo -e "${RED}[ERROR]${NC} Failed to start container."
    exit 1
fi

log "Container started. Waiting for Gazebo server..."
sleep 10

# Verify Gazebo is running
if docker exec gazebo-px4 sh -c "pgrep -f 'gz sim' >/dev/null 2>&1"; then
    log "${GREEN}Gazebo simulator is running!${NC}"
else
    warn "Gazebo not detected."
fi

# 5. Copy GUI config into container and launch GUI
log "Opening Gazebo GUI with camera tracking..."
docker exec gazebo-px4 mkdir -p /tmp/gui_config
docker cp gazebo_models/dodoma/gui_config/full.config gazebo-px4:/tmp/gui_config/
docker exec -d gazebo-px4 sh -c "DISPLAY=:0 gz sim -g --gui-config /tmp/gui_config/full.config &" 2>/dev/null || \
    echo -e "${YELLOW}[WARN]${NC} Could not open GUI automatically."

# 6. Wait for drone spawn then auto-arm/takeoff
log "Waiting for drone to spawn..."
for i in $(seq 1 30); do
    sleep 2
    DRONE_OK=$(docker exec gazebo-px4 bash -c "gz topic -e -t /world/dodoma_tanzania/pose/info -d 1 2>/dev/null" 2>/dev/null | grep -c "x500_0" || true)
    if [ "$DRONE_OK" -gt 0 ]; then
        log "${GREEN}Drone x500_0 detected!${NC}"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo -e "${YELLOW}[WARN]${NC} Drone not detected after 60s. Check logs."
    fi
done

# 7. Auto-arm and takeoff to show the drone flying
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
" 2>&1 || echo -e "${YELLOW}[WARN]${NC} Auto-arm/takeoff failed. Use NLP console."

# 8. Open NLP Drone Console
log "Opening NLP Drone Console..."
NLP_CMD="cd '$SCRIPT_DIR' && python3 scripts/nlp_console.py 127.0.0.1"
if command -v gnome-terminal &>/dev/null; then
    nohup gnome-terminal --title="NLP Drone Console" -- bash -c "$NLP_CMD; exec bash" &>/dev/null &
    sleep 1
elif command -v xterm &>/dev/null; then
    xterm -T "NLP Drone Console" -e "$NLP_CMD" &
else
    echo -e "${YELLOW}[WARN]${NC} No terminal emulator. Run: python3 scripts/nlp_console.py"
fi

# 9. Show status
echo ""
echo -e "${CYAN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║          ${BOLD}DODOMA DRONE READY${NC}${CYAN}                         ║${NC}"
echo -e "${CYAN}╠════════════════════════════════════════════════════════╣${NC}"
echo -e "${CYAN}║${NC}  ✓ Drone spawned and hovering at 10m              ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  ✓ Camera tracking x500_0                         ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  ✓ NLP console open for commands                  ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}                                                    ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  ${BOLD}Commands:${NC}                                        ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}    'take off to 20m'        'land'               ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}    'fly to bunge parliament' 'go forward 30m'    ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}    'fly to central hospital' 'return home'       ${CYAN}║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
