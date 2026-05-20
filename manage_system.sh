#!/usr/bin/env bash

# ─────────────────────────────────────────────────────────────────────────────
# DRONE AUTONOMOUS SYSTEM - GLOBAL MANAGER
# Supports: Single-Machine (All) | Distributed LAN (Single Service)
# ─────────────────────────────────────────────────────────────────────────────

GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; RED='\033[0;31m'
BOLD='\033[1m'; NC='\033[0m'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$ROOT_DIR/.lan_config"
LAN_CONF="$CONFIG_DIR/lan.conf"
MARKER_DIR="$CONFIG_DIR/.markers"

log()   { echo -e "${GREEN}[SYSTEM]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }
info()  { echo -e "${CYAN}[INFO]${NC} $1"; }

mkdir -p "$MARKER_DIR"

# ─── Dependency Helpers ──────────────────────────────────────────────────────
docker_image_exists() {
    docker image inspect "$1" >/dev/null 2>&1
}

python_pkg_installed() {
    python3 -c "import $1" 2>/dev/null
}

pip_install() {
    pip3 install --break-system-packages --quiet "$1" 2>/dev/null || \
    pip3 install --quiet "$1" 2>/dev/null || \
    warn "Failed to install $1"
}

# ─── PC1 Dependency Check ────────────────────────────────────────────────────
check_pc1_deps() {
    local marker="$MARKER_DIR/pc1_deps_done"
    if [ -f "$marker" ]; then
        info "PC1 dependencies already installed."
        return 0
    fi

    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║          ${BOLD}PC1 FIRST-TIME SETUP${NC}${CYAN}                         ║${NC}"
    echo -e "${CYAN}╠══════════════════════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║${NC}  Checking and installing dependencies...            ${CYAN}║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    local needs_install=0

    # Check Docker images
    for img in "confluentinc/cp-zookeeper:7.4.0" "confluentinc/cp-kafka:7.4.0" "python:3.10-slim"; do
        if ! docker_image_exists "$img"; then
            warn "Missing image: $img"
            needs_install=1
        else
            log "Image OK: $img"
        fi
    done

    # Pull missing images
    if [ $needs_install -eq 1 ]; then
        info "Pulling Docker images (this may take a while)..."
        docker pull confluentinc/cp-zookeeper:7.4.0
        docker pull confluentinc/cp-kafka:7.4.0
    fi

    # Build Docker services
    info "Building PC1 Docker services..."
    cd "$ROOT_DIR/PC1" && docker-compose build

    touch "$marker"
    log "PC1 setup complete."
}

# ─── PC2 Dependency Check ────────────────────────────────────────────────────
check_pc2_deps() {
    local marker="$MARKER_DIR/pc2_deps_done"
    if [ -f "$marker" ]; then
        info "PC2 dependencies already installed."
        return 0
    fi

    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║          ${BOLD}PC2 FIRST-TIME SETUP${NC}${CYAN}                         ║${NC}"
    echo -e "${CYAN}╠══════════════════════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║${NC}  Checking and installing dependencies...            ${CYAN}║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Check Gazebo image
    if ! docker_image_exists "px4io/px4-sitl-gazebo:latest"; then
        warn "Missing image: px4io/px4-sitl-gazebo:latest"
        info "Pulling Gazebo PX4 image (large download)..."
        docker pull px4io/px4-sitl-gazebo:latest
    else
        log "Image OK: px4io/px4-sitl-gazebo:latest"
    fi

    # Build AI services (downloads YOLOv8, installs heavy deps)
    info "Building PC2 Docker services (YOLOv8, RL Navigation)..."
    cd "$ROOT_DIR/PC2" && docker-compose build object-detection rl-navigation

    touch "$marker"
    log "PC2 setup complete."
}

# ─── PC3 Dependency Check ────────────────────────────────────────────────────
check_pc3_deps() {
    local marker="$MARKER_DIR/pc3_deps_done"
    if [ -f "$marker" ]; then
        info "PC3 dependencies already installed."
        return 0
    fi

    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║          ${BOLD}PC3 FIRST-TIME SETUP${NC}${CYAN}                         ║${NC}"
    echo -e "${CYAN}╠══════════════════════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║${NC}  Checking and installing dependencies...            ${CYAN}║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Check Docker images
    for img in "grafana/grafana:latest" "prom/prometheus:latest" "prom/node-exporter:latest" "influxdb:2.7"; do
        if ! docker_image_exists "$img"; then
            warn "Missing image: $img"
            docker pull "$img"
        else
            log "Image OK: $img"
        fi
    done

    # Build telemetry collector and API gateway
    info "Building PC3 Docker services..."
    cd "$ROOT_DIR/PC3" && docker-compose build telemetry-collector api-gateway

    touch "$marker"
    log "PC3 setup complete."
}

# ─── PC4 Dependency Check ────────────────────────────────────────────────────
check_pc4_deps() {
    local marker="$MARKER_DIR/pc4_deps_done"
    if [ -f "$marker" ]; then
        info "PC4 dependencies already installed."
        return 0
    fi

    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║          ${BOLD}PC4 FIRST-TIME SETUP${NC}${CYAN}                         ║${NC}"
    echo -e "${CYAN}╠══════════════════════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║${NC}  Checking and installing dependencies...            ${CYAN}║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Build feedback service
    info "Building PC4 Docker service..."
    cd "$ROOT_DIR/PC4" && docker-compose build

    touch "$marker"
    log "PC4 setup complete."
}

# ─── Check All Dependencies ──────────────────────────────────────────────────
check_all_deps() {
    check_pc1_deps
    check_pc2_deps
    check_pc3_deps
    check_pc4_deps
}

# ─── Network Detection ───────────────────────────────────────────────────────
get_lan_ip() {
    ip route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src") print $(i+1); exit}'
}

get_lan_subnet() {
    local ip=$(get_lan_ip)
    echo "${ip%.*}.0/24"
}

ping_host() {
    timeout 2 ping -c 1 -W 1 "$1" >/dev/null 2>&1
}

detect_lan() {
    local my_ip=$(get_lan_ip)
    local subnet=$(get_lan_subnet)
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║          ${BOLD}NETWORK DETECTION${NC}${CYAN}                            ║${NC}"
    echo -e "${CYAN}╠══════════════════════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║${NC}  This machine IP:  ${BOLD}${my_ip}${NC}                          ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  Detected subnet:  ${BOLD}${subnet}${NC}                ${CYAN}║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    if [ -z "$my_ip" ] || [[ "$my_ip" == 127.* ]]; then
        warn "Could not detect LAN IP. Assuming single-machine mode."
        return 1
    fi

    # Check if LAN config exists
    if [ -f "$LAN_CONF" ]; then
        source "$LAN_CONF"
        info "Saved LAN config found:"
        echo "  PC1 (Kafka):       $PC1_IP"
        echo "  PC2 (Gazebo/AI):   $PC2_IP"
        echo "  PC3 (Monitoring):  $PC3_IP"
        echo "  PC4 (Feedback):    $PC4_IP"
        echo ""

        # Verify reachability
        local reachable=0
        local total=0
        for pc in PC1_IP PC2_IP PC3_IP PC4_IP; do
            local ip="${!pc}"
            if [ -n "$ip" ] && [ "$ip" != "localhost" ] && [ "$ip" != "127.0.0.1" ]; then
                total=$((total + 1))
                if ping_host "$ip"; then
                    log "${pc}: ${ip} ✓ (reachable)"
                    reachable=$((reachable + 1))
                else
                    warn "${pc}: ${ip} ✗ (unreachable)"
                fi
            fi
        done

        if [ $total -gt 0 ] && [ $reachable -eq $total ]; then
            log "All configured PCs are reachable on LAN."
            return 0
        elif [ $reachable -gt 0 ]; then
            warn "$reachable/$total PCs reachable. Some may be offline."
            return 0
        else
            warn "No configured PCs are reachable. You may be out of LAN."
            return 1
        fi
    fi

    warn "No saved LAN configuration found."
    return 1
}

# ─── LAN Configuration Wizard ────────────────────────────────────────────────
configure_lan() {
    local my_ip=$(get_lan_ip)
    local default_subnet="${my_ip%.*}"

    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║          ${BOLD}LAN CONFIGURATION WIZARD${NC}${CYAN}                     ║${NC}"
    echo -e "${CYAN}╠══════════════════════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║${NC}  Enter IP addresses for each PC in your network.    ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  Use 'localhost' or '127.0.0.1' if running locally. ${CYAN}║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    read -p "  PC1 IP (Kafka, Command Parser)     [${default_subnet}.101]: " pc1
    read -p "  PC2 IP (Gazebo, Object Detection)  [${default_subnet}.102]: " pc2
    read -p "  PC3 IP (Grafana, Monitoring)       [${default_subnet}.103]: " pc3
    read -p "  PC4 IP (Feedback, TTS)             [${default_subnet}.104]: " pc4

    PC1_IP=${pc1:-${default_subnet}.101}
    PC2_IP=${pc2:-${default_subnet}.102}
    PC3_IP=${pc3:-${default_subnet}.103}
    PC4_IP=${pc4:-${default_subnet}.104}

    # Save config
    mkdir -p "$CONFIG_DIR"
    cat > "$LAN_CONF" << EOF
PC1_IP=$PC1_IP
PC2_IP=$PC2_IP
PC3_IP=$PC3_IP
PC4_IP=$PC4_IP
EOF

    echo ""
    log "LAN configuration saved to $LAN_CONF"
    echo "  PC1: $PC1_IP"
    echo "  PC2: $PC2_IP"
    echo "  PC3: $PC3_IP"
    echo "  PC4: $PC4_IP"
    echo ""

    # Verify reachability
    info "Verifying connectivity..."
    for pc in PC1_IP PC2_IP PC3_IP PC4_IP; do
        local ip="${!pc}"
        if [ "$ip" != "localhost" ] && [ "$ip" != "127.0.0.1" ]; then
            if ping_host "$ip"; then
                log "${pc}: ${ip} ✓"
            else
                warn "${pc}: ${ip} ✗ (unreachable)"
            fi
        else
            info "${pc}: ${ip} (local)"
        fi
    done
}

# ─── Write Environment Config ────────────────────────────────────────────────
write_env_config() {
    local pc_num=$1
    local env_file="$ROOT_DIR/PC${pc_num}/config/environment.env"

    cat > "$env_file" << EOF
# Environment variables for PC${pc_num} runtime configuration
# Auto-generated by manage_system.sh

# PC IP Addresses
PC1_IP=${PC1_IP}
PC2_IP=${PC2_IP}
PC3_IP=${PC3_IP}
PC4_IP=${PC4_IP}

# Kafka connection
KAFKA_BOOTSTRAP_SERVERS=${PC1_IP}:9092
EOF

    log "PC${pc_num} environment config written."
}

# ─── Write Docker Compose Env Override ───────────────────────────────────────
write_compose_env() {
    local pc_num=$1
    local env_file="$ROOT_DIR/PC${pc_num}/.env"

    cat > "$env_file" << EOF
PC1_IP=${PC1_IP}
PC2_IP=${PC2_IP}
PC3_IP=${PC3_IP}
PC4_IP=${PC4_IP}
EOF

    log "PC${pc_num} .env file written for docker-compose."
}

# ─── Ensure Network Exists ───────────────────────────────────────────────────
ensure_network() {
    if ! docker network inspect fyp-network >/dev/null 2>&1; then
        log "Creating shared network: fyp-network..."
        docker network create fyp-network
    fi
}

# ─── Start PC1 ───────────────────────────────────────────────────────────────
start_pc1() {
    local mode=${1:-local}
    if [ "$mode" = "lan" ]; then
        write_env_config 1
        write_compose_env 1
    fi

    check_pc1_deps

    log "Starting PC1 (Core & Kafka)..."
    cd "$ROOT_DIR/PC1" && docker-compose up -d
}

# ─── Start PC2 ───────────────────────────────────────────────────────────────
start_pc2() {
    local mode=${1:-local}
    if [ "$mode" = "lan" ]; then
        write_env_config 2
        write_compose_env 2
    fi

    check_pc2_deps

    log "Starting PC2 (Vision & AI)..."

    # Check if Gazebo container exists
    if docker ps --format '{{.Names}}' | grep -q '^gazebo-px4$'; then
        log "Gazebo already running."
    else
        if [ -f "$ROOT_DIR/PC2/start_gazebo.sh" ]; then
            bash "$ROOT_DIR/PC2/start_gazebo.sh"
        else
            cd "$ROOT_DIR/PC2" && docker-compose up -d gazebo-px4
        fi
    fi

    cd "$ROOT_DIR/PC2" && docker-compose up -d object-detection rl-navigation
}

# ─── Start PC3 ───────────────────────────────────────────────────────────────
start_pc3() {
    local mode=${1:-local}
    if [ "$mode" = "lan" ]; then
        write_env_config 3
        write_compose_env 3
    fi

    check_pc3_deps

    log "Starting PC3 (Telemetry & Dashboard)..."
    cd "$ROOT_DIR/PC3" && bash start_pc3.sh
}

# ─── Start PC4 ───────────────────────────────────────────────────────────────
start_pc4() {
    local mode=${1:-local}
    if [ "$mode" = "lan" ]; then
        write_env_config 4
        write_compose_env 4
    fi

    check_pc4_deps

    log "Starting PC4 (Feedback)..."
    cd "$ROOT_DIR/PC4" && docker-compose up -d
}

# ─── Stop PC ─────────────────────────────────────────────────────────────────
stop_pc() {
    local pc_num=$1
    log "Stopping PC${pc_num}..."
    case $pc_num in
        1) cd "$ROOT_DIR/PC1" && docker-compose down ;;
        2)
            docker rm -f gazebo-px4 2>/dev/null || true
            cd "$ROOT_DIR/PC2" && docker-compose down
            ;;
        3)
            cd "$ROOT_DIR/PC3" && docker-compose down
            pkill -f "drone_exporter.py" 2>/dev/null || true
            ;;
        4) cd "$ROOT_DIR/PC4" && docker-compose down ;;
    esac
}

# ─── Stop All ────────────────────────────────────────────────────────────────
stop_all() {
    log "Stopping all services..."
    docker rm -f gazebo-px4 2>/dev/null || true
    pkill -f "drone_exporter.py" 2>/dev/null || true

    for pc in PC1 PC2 PC3 PC4; do
        if [ -f "$ROOT_DIR/$pc/docker-compose.yml" ]; then
            cd "$ROOT_DIR/$pc" && docker-compose down 2>/dev/null
        fi
    done
    log "All services stopped."
}

# ─── Single Service Menu ─────────────────────────────────────────────────────
single_service_menu() {
    local pc_num=$1
    local pc_name=""
    case $pc_num in
        1) pc_name="PC1 (Core & Kafka)" ;;
        2) pc_name="PC2 (Vision & AI)" ;;
        3) pc_name="PC3 (Monitoring)" ;;
        4) pc_name="PC4 (Feedback)" ;;
    esac

    clear
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║          ${BOLD}${pc_name}${NC}${CYAN}                          ║${NC}"
    echo -e "${CYAN}╠══════════════════════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║${NC}                                                    ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  1) Run LOCALLY (connect to LAN PCs)              ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  2) Configure LAN IPs and run                     ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  3) Stop this service                             ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}                                                    ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  b) Back to main menu                             ${CYAN}║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo -n "Select: "
    read -r choice

    case $choice in
        1)
            # Run locally - prompt for LAN IPs if not configured
            if [ ! -f "$LAN_CONF" ]; then
                info "No LAN configuration found. Configure now?"
                read -p "  Configure LAN IPs? (y/N): " conf
                if [[ "$conf" =~ ^[Yy]$ ]]; then
                    configure_lan
                else
                    info "Using defaults (localhost for all). Services will only work if all PCs are on this machine."
                    PC1_IP="localhost"
                    PC2_IP="localhost"
                    PC3_IP="localhost"
                    PC4_IP="localhost"
                fi
            else
                source "$LAN_CONF"
                info "Using saved LAN configuration."
            fi
            start_single_pc $pc_num "lan"
            ;;
        2)
            configure_lan
            start_single_pc $pc_num "lan"
            ;;
        3)
            stop_pc $pc_num
            log "PC${pc_num} stopped."
            ;;
        b|B) return ;;
        *) error "Invalid choice." ;;
    esac
}

start_single_pc() {
    local pc_num=$1
    local mode=$2
    case $pc_num in
        1) start_pc1 "$mode" ;;
        2) start_pc2 "$mode" ;;
        3) start_pc3 "$mode" ;;
        4) start_pc4 "$mode" ;;
    esac
}

# ─── Clear LAN Config ───────────────────────────────────────────────────────
clear_lan_config() {
    if [ -f "$LAN_CONF" ]; then
        rm -f "$LAN_CONF"
        log "LAN configuration cleared."
    else
        info "No LAN configuration to clear."
    fi
}

# ─── Reset Setup (Force Re-install) ──────────────────────────────────────────
reset_setup() {
    echo ""
    echo -e "${YELLOW}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║          ${BOLD}RESET SETUP MARKERS${NC}${YELLOW}                          ║${NC}"
    echo -e "${YELLOW}╠══════════════════════════════════════════════════════════╣${NC}"
    echo -e "${YELLOW}║${NC}  This will force dependency re-check on next start. ${YELLOW}║${NC}"
    echo -e "${YELLOW}║${NC}  Existing Docker images will NOT be removed.        ${YELLOW}║${NC}"
    echo -e "${YELLOW}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "  Which PC to reset?"
    echo "  1) PC1    2) PC2    3) PC3    4) PC4    a) ALL"
    echo -n "  Select: "
    read -r reset_choice

    case $reset_choice in
        1) rm -f "$MARKER_DIR/pc1_deps_done"; log "PC1 marker cleared." ;;
        2) rm -f "$MARKER_DIR/pc2_deps_done"; log "PC2 marker cleared." ;;
        3) rm -f "$MARKER_DIR/pc3_deps_done"; log "PC3 marker cleared." ;;
        4) rm -f "$MARKER_DIR/pc4_deps_done"; log "PC4 marker cleared." ;;
        a|A) rm -f "$MARKER_DIR"/pc*_deps_done; log "All markers cleared." ;;
        *) error "Invalid choice." ;;
    esac
}

# ─── Start All (Single Machine) ──────────────────────────────────────────────
start_all() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║          ${BOLD}STARTING FULL SYSTEM (LOCAL)${NC}${CYAN}                 ║${NC}"
    echo -e "${CYAN}╠══════════════════════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║${NC}  All services will run on this machine.             ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  Docker DNS handles inter-service communication.    ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  No IP configuration required.                      ${CYAN}║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Clear any stale LAN config for this session
    clear_lan_config

    # Remove any stale .env files that might override Docker DNS defaults
    for pc in PC1 PC2 PC3 PC4; do
        rm -f "$ROOT_DIR/$pc/.env" 2>/dev/null
    done

    ensure_network

    # Check and install dependencies (first run only)
    check_all_deps

    log "Starting PC1 (Kafka + Zookeeper)..."
    cd "$ROOT_DIR/PC1" && docker-compose up -d
    sleep 5

    log "Starting PC3 (Monitoring)..."
    cd "$ROOT_DIR/PC3" && bash start_pc3.sh
    sleep 3

    log "Starting PC2 (Gazebo + AI)..."
    if docker ps --format '{{.Names}}' | grep -q '^gazebo-px4$'; then
        log "Gazebo already running."
    else
        if [ -f "$ROOT_DIR/PC2/start_gazebo.sh" ]; then
            bash "$ROOT_DIR/PC2/start_gazebo.sh"
        else
            cd "$ROOT_DIR/PC2" && docker-compose up -d gazebo-px4
        fi
    fi
    cd "$ROOT_DIR/PC2" && docker-compose up -d object-detection rl-navigation
    sleep 3

    log "Starting PC4 (Feedback)..."
    cd "$ROOT_DIR/PC4" && docker-compose up -d

    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║          ${BOLD}ALL SERVICES STARTED${NC}${CYAN}                         ║${NC}"
    echo -e "${CYAN}╠══════════════════════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║${NC}  Grafana:     http://localhost:3000 (admin/admin123)${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  Prometheus:  http://localhost:9090                  ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  InfluxDB:    http://localhost:8086                  ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  Radar UI:    http://localhost:8007/radar            ${CYAN}║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# ─── Show Status ─────────────────────────────────────────────────────────────
show_status() {
    clear
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║          ${BOLD}SYSTEM STATUS${NC}${CYAN}                                ║${NC}"
    echo -e "${CYAN}╠══════════════════════════════════════════════════════════╣${NC}"
    echo ""

    # LAN Config
    if [ -f "$LAN_CONF" ]; then
        source "$LAN_CONF"
        info "LAN Configuration:"
        echo -e "  ${BOLD}PC1 (Kafka):${NC}       $PC1_IP"
        echo -e "  ${BOLD}PC2 (Gazebo):${NC}      $PC2_IP"
        echo -e "  ${BOLD}PC3 (Grafana):${NC}     $PC3_IP"
        echo -e "  ${BOLD}PC4 (Feedback):${NC}    $PC4_IP"
    else
        info "Mode: ${BOLD}Single-Machine (Local)${NC} — Docker DNS handles routing."
    fi
    echo ""

    # Setup Status
    info "Setup Status:"
    for pc in 1 2 3 4; do
        if [ -f "$MARKER_DIR/pc${pc}_deps_done" ]; then
            log "  PC${pc}: Dependencies installed ✓"
        else
            warn "  PC${pc}: First-time setup required ⚠"
        fi
    done
    echo ""

    # Docker containers
    info "Running Containers:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null
    echo ""

    # Network
    info "Docker Networks:"
    docker network ls --format "table {{.Name}}\t{{.Driver}}" | grep -E "NAME|fyp"
    echo ""

    # LAN Connectivity
    if [ -f "$LAN_CONF" ]; then
        info "LAN Connectivity:"
        for pc in PC1_IP PC2_IP PC3_IP PC4_IP; do
            local ip="${!pc}"
            if [ "$ip" != "localhost" ] && [ "$ip" != "127.0.0.1" ]; then
                if ping_host "$ip"; then
                    log "  ${pc}: ${ip} ✓"
                else
                    warn "  ${pc}: ${ip} ✗"
                fi
            else
                info "  ${pc}: ${ip} (local)"
            fi
        done
    fi
    echo ""
}

# ─── Demo URLs for Presentation ──────────────────────────────────────────────
show_demo_urls() {
    clear
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║     ${BOLD}LGADS DEMO - WEB SERVICE URLS${NC}${CYAN}                 ║${NC}"
    echo -e "${CYAN}╠══════════════════════════════════════════════════════════╣${NC}"
    echo ""
    echo -e "${BOLD}📊 SYSTEM STATUS DASHBOARD (Start Here!)${NC}"
    echo -e "   ${GREEN}http://localhost/status${NC}"
    echo -e "   Shows ALL services, topics, and health in one view"
    echo ""
    echo -e "${BOLD}🔧 KAFKA UI - Message Broker Dashboard${NC}"
    echo -e "   ${GREEN}http://localhost:8080${NC}"
    echo -e "   View: Brokers, Topics, Consumer Groups, Messages"
    echo ""
    echo -e "${BOLD}📂 ZOOKEEPER WEB UI - Service Registry (Official ZooNavigator)${NC}"
    echo -e "   ${GREEN}http://localhost:9000${NC}"
    echo -e "   Click 'Connect' → enter: zookeeper:2181"
    echo -e "   Browse znodes: /brokers/ids, /brokers/topics, /consumers"
    echo -e "   ${YELLOW}Proves: All services registered in Zookeeper on port 2181${NC}"
    echo -e "   ${YELLOW}Department can verify: Kafka broker ID, topics, consumer groups${NC}"
    echo ""
    echo -e "${BOLD}📈 GRAFANA - Real-time Telemetry Dashboard${NC}"
    echo -e "   ${GREEN}http://localhost:3000${NC}  (admin / admin123)"
    echo -e "   Dashboards: Drone Mission Control, Radar, Telemetry"
    echo -e "   ${YELLOW}Proves: Live GPS, altitude, battery, speed visualization${NC}"
    echo ""
    echo -e "${BOLD}📡 INFLUXDB - Time-Series Database${NC}"
    echo -e "   ${GREEN}http://localhost:8086${NC}"
    echo -e "   View: Buckets, Data Explorer, Query Builder"
    echo -e "   ${YELLOW}Proves: Telemetry data persistence${NC}"
    echo ""
    echo -e "${BOLD}📊 PROMETHEUS - Metrics Collection${NC}"
    echo -e "   ${GREEN}http://localhost:9090${NC}"
    echo -e "   View: Targets, Graphs, Service Discovery"
    echo ""
    echo -e "${BOLD}🌐 API GATEWAY - REST API & System Status${NC}"
    echo -e "   ${GREEN}http://localhost:8008${NC}"
    echo -e "   Health:    http://localhost:8008/api/health"
    echo -e "   Status UI: http://localhost:8008/status"
    echo -e "   ${YELLOW}Proves: All microservices connected via API${NC}"
    echo ""
    echo -e "${BOLD}🤖 PC2 SERVICES${NC}"
    echo -e "   Object Detection: ${GREEN}http://localhost:8002/health${NC}"
    echo -e "   RL Navigation:    ${GREEN}http://localhost:8003/health${NC}"
    echo ""
    echo -e "${BOLD}🎮 PC1 SERVICES${NC}"
    echo -e "   Command Parser:   ${GREEN}http://localhost:8000/health${NC}"
    echo -e "   Flight Control:   ${GREEN}http://localhost:8001/health${NC}"
    echo ""
    echo -e "${BOLD}🔊 PC4 SERVICES${NC}"
    echo -e "   Feedback (TTS):   ${GREEN}http://localhost:8005/health${NC}"
    echo ""
    echo -e "${CYAN}╠══════════════════════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║${NC}  ${BOLD}Demo Flow Recommendation:${NC}                            ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  1. Open http://localhost:8008/status (system overview)  ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  2. Open http://localhost:8080 (Kafka topics)            ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  3. Open http://localhost:9000 (Zookeeper znodes)        ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  4. Open http://localhost:3000 (Grafana dashboards)      ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  5. Send command via API Gateway                         ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  6. Watch live telemetry in Grafana                      ${CYAN}║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# ─── Main Menu ───────────────────────────────────────────────────────────────
main_menu() {
    clear
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║          ${BOLD}DRONE AUTONOMOUS SYSTEM MANAGER${NC}${CYAN}              ║${NC}"
    echo -e "${CYAN}╠══════════════════════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║${NC}                                                    ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${BOLD}FULL SYSTEM:${NC}                                         ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}    5) Start ALL (Single Machine - Local)           ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}    6) Stop ALL                                     ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}                                                    ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${BOLD}INDIVIDUAL SERVICES:${NC}                                 ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}    1) PC1 - Core & Kafka                           ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}    2) PC2 - Vision & AI (Gazebo)                   ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}    3) PC3 - Monitoring (Grafana)                   ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}    4) PC4 - Feedback (TTS)                         ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}                                                    ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${BOLD}NETWORK:${NC}                                             ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}    n) Detect / Configure LAN                       ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}    c) Clear LAN Config (reset to local)            ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}                                                    ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${BOLD}SYSTEM:${NC}                                              ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}    s) Show Status                                  ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}    d) Show Demo URLs (Presentation)                ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}    r) Reset Setup (force re-install)               ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}    q) Quit                                         ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}                                                    ${CYAN}║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo -n "Select an option: "
}

# ─── Execution ───────────────────────────────────────────────────────────────
ensure_network

while true; do
    main_menu
    read -r choice
    case $choice in
        1) single_service_menu 1 ;;
        2) single_service_menu 2 ;;
        3) single_service_menu 3 ;;
        4) single_service_menu 4 ;;
        5) start_all ;;
        6) stop_all ;;
        n|N)
            detect_lan
            read -p "Configure LAN IPs? (y/N): " conf
            if [[ "$conf" =~ ^[Yy]$ ]]; then
                configure_lan
            fi
            ;;
        c|C) clear_lan_config ;;
        r|R) reset_setup ;;
        s|S) show_status ;;
        d|D) show_demo_urls ;;
        q|Q) log "Exiting..."; exit 0 ;;
        *) error "Invalid choice: $choice"; sleep 1 ;;
    esac
    echo -e "\nPress Enter to return to menu..."
    read -r
done
