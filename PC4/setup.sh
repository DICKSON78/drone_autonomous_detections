#!/bin/bash

# PC4: Web Interface & Feedback Setup Script
# This script automatically sets up everything for PC4

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[PC4]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[PC4]${NC} $1"
}

print_error() {
    echo -e "${RED}[PC4]${NC} $1"
}

print_header() {
    echo -e "${BLUE}====================================${NC}"
    echo -e "${BLUE}  PC4: Web Interface & Feedback     ${NC}"
    echo -e "${BLUE}====================================${NC}"
}

# ── Get team IPs ───────────────────────────────────────────────────────────────
get_team_ips() {
    print_status "Enter team member IP addresses:"
    echo ""

    read -p "PC1 IP [192.168.1.10]: " PC1_IP
    read -p "PC2 IP [192.168.1.11]: " PC2_IP
    read -p "PC3 IP [192.168.1.12]: " PC3_IP
    read -p "PC4 IP (Your IP) [192.168.1.13]: " PC4_IP

    PC1_IP=${PC1_IP:-"192.168.1.10"}
    PC2_IP=${PC2_IP:-"192.168.1.11"}
    PC3_IP=${PC3_IP:-"192.168.1.12"}
    PC4_IP=${PC4_IP:-"192.168.1.13"}

    print_status "Team IPs configured:"
    echo "  PC1: $PC1_IP"
    echo "  PC2: $PC2_IP"
    echo "  PC3: $PC3_IP"
    echo "  PC4 (You): $PC4_IP"
}

# ── Check Docker ───────────────────────────────────────────────────────────────
check_docker() {
    print_status "Checking Docker..."

    if ! command -v docker >/dev/null 2>&1; then
        print_error "Docker not installed. Installing..."
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        sudo usermod -aG docker $USER
        print_warning "Please run: newgrp docker && ./setup.sh"
        exit 1
    fi

    if ! docker info >/dev/null 2>&1; then
        print_error "Docker daemon not running. Starting..."
        sudo systemctl start docker
        sudo usermod -aG docker $USER
        print_warning "Please run: newgrp docker && ./setup.sh"
        exit 1
    fi

    # Ensure Docker Compose plugin is available
    if ! docker compose version >/dev/null 2>&1 && ! command -v docker-compose >/dev/null 2>&1; then
        print_warning "Docker Compose not found. Installing plugin..."
        sudo apt-get update -qq && sudo apt-get install -y docker-compose-plugin
    fi

    print_status "Docker is ready"
}

# ── Check audio permissions ────────────────────────────────────────────────────
check_audio() {
    print_status "Checking audio permissions..."

    if groups $USER | grep -q audio; then
        print_status "User already in audio group"
    else
        print_warning "Adding user to audio group..."
        sudo usermod -aG audio $USER
        print_warning "You may need to logout and back in for audio to work"
    fi

    if [ ! -d /dev/snd ]; then
        print_warning "/dev/snd not found — TTS will run in silent/log mode"
        # Remove audio device mapping so Docker doesn't fail
        sed -i '/\/dev\/snd/d' docker-compose.yml 2>/dev/null || true
    else
        print_status "Audio device /dev/snd found"
    fi
}

# ── Create shared Docker network ───────────────────────────────────────────────
create_network() {
    print_status "Ensuring fyp-network exists..."
    docker network inspect fyp-network >/dev/null 2>&1 || \
        docker network create fyp-network
    print_status "fyp-network ready"
}

# ── Update configuration ───────────────────────────────────────────────────────
update_config() {
    print_status "Updating configuration with team IPs..."

    # Patch docker-compose.yml placeholder hostnames
    sed -i "s/PC1_IP_PLACEHOLDER/$PC1_IP/g" docker-compose.yml 2>/dev/null || true
    sed -i "s/PC2_IP_PLACEHOLDER/$PC2_IP/g" docker-compose.yml 2>/dev/null || true
    sed -i "s/PC3_IP_PLACEHOLDER/$PC3_IP/g" docker-compose.yml 2>/dev/null || true
    sed -i "s/PC4_IP_PLACEHOLDER/$PC4_IP/g" docker-compose.yml 2>/dev/null || true

    # Write environment config
    mkdir -p config
    cat > config/environment.env <<EOF
PC1_IP=$PC1_IP
PC2_IP=$PC2_IP
PC3_IP=$PC3_IP
PC4_IP=$PC4_IP
KAFKA_BOOTSTRAP_SERVERS=$PC1_IP:9092
PORT=8005
TTS_RATE=150
TTS_VOLUME=1.0
TTS_VOICE_INDEX=0
DEBUG=false
WS_PORT=8006
KAFKA_BROKER=$PC1_IP:9092
EOF
    print_status "config/environment.env written"

    # Update /etc/hosts for hostname resolution
    if sudo -n true 2>/dev/null; then
        sudo sed -i '/# PC4 Drone System/,/# End PC4 System/d' /etc/hosts 2>/dev/null || true
        sudo tee -a /etc/hosts > /dev/null <<EOF
# PC4 Drone System
$PC1_IP PC1
$PC2_IP PC2
$PC3_IP PC3
$PC4_IP PC4
# End PC4 System
EOF
        print_status "Updated /etc/hosts"
    fi
}

# ── Build and start all services ───────────────────────────────────────────────
build_services() {
    print_status "Stopping any existing services..."
    docker compose down 2>/dev/null || docker-compose down 2>/dev/null || true

    print_status "Building Docker images (5–8 minutes first time)..."
    docker compose up -d --build 2>/dev/null || docker-compose up -d --build

    print_status "Waiting for services to initialise..."
    sleep 30
}

# ── Wait for a service to become healthy ───────────────────────────────────────
wait_for_service() {
    local name=$1
    local url=$2
    local max=10

    for i in $(seq 1 $max); do
        if curl -sf "$url" >/dev/null 2>&1; then
            print_status "$name is running"
            return 0
        fi
        [ $i -eq $max ] && print_warning "$name not ready yet — check: docker compose logs $name"
        sleep 5
    done
}

# ── Test all services ──────────────────────────────────────────────────────────
test_services() {
    print_status "Testing services..."

    wait_for_service "Feedback Service"  "http://localhost:8005/health"
    wait_for_service "WebSocket Server"  "http://localhost:8006/health"
    wait_for_service "Web Dashboard"     "http://localhost:80"
}

# ── Test TTS ───────────────────────────────────────────────────────────────────
test_tts() {
    print_status "Testing Text-to-Speech..."

    local response
    response=$(curl -sf -X POST http://localhost:8005/speak \
        -H "Content-Type: application/json" \
        -d '{"message": "PC4 setup complete. System ready.", "priority": "normal"}' 2>/dev/null || echo "")

    if [ -n "$response" ]; then
        print_status "TTS test sent — listen for spoken message"
    else
        print_warning "TTS test could not reach feedback-service — check logs"
    fi
}

# ── Show final results ─────────────────────────────────────────────────────────
show_results() {
    echo ""
    print_header
    echo ""
    print_status "PC4 Setup Complete!"
    echo ""
    echo "  Services running:"
    echo "    Web Dashboard    → http://$PC4_IP"
    echo "    WebSocket Server → http://$PC4_IP:8006"
    echo "    Feedback Service → http://$PC4_IP:8005"
    echo ""
    echo "  Team services:"
    echo "    PC1 (Command)    → $PC1_IP"
    echo "    PC2 (Detection)  → $PC2_IP"
    echo "    PC3 (Navigation) → $PC3_IP"
    echo ""
    print_status "Quick tests:"
    echo "  curl http://localhost:8005/health"
    echo "  curl http://localhost:8006/health"
    echo ""
    print_status "Test TTS:"
    echo "  curl -X POST http://localhost:8005/speak \\"
    echo "    -H \"Content-Type: application/json\" \\"
    echo "    -d '{\"message\": \"Hello drone\", \"priority\": \"normal\"}'"
    echo ""
    print_status "View logs:"
    echo "  docker compose logs -f"
    echo "  docker compose logs -f feedback-service"
}

# ── Open browser dashboard ─────────────────────────────────────────────────────
open_dashboard() {
    print_status "Opening web dashboard..."

    if command -v xdg-open >/dev/null 2>&1; then
        xdg-open http://localhost 2>/dev/null &
    elif command -v open >/dev/null 2>&1; then
        open http://localhost 2>/dev/null &
    else
        print_status "Open http://localhost in your browser"
    fi
}

# ── Full setup ─────────────────────────────────────────────────────────────────
main() {
    print_header
    get_team_ips
    check_docker
    check_audio
    create_network
    update_config
    build_services
    test_services
    test_tts
    show_results
    open_dashboard

    echo ""
    read -p "View service logs? (y/n): " show_logs
    if [[ $show_logs =~ ^[Yy]$ ]]; then
        docker compose logs -f 2>/dev/null || docker-compose logs -f
    fi
}

# ── Subcommand dispatch ────────────────────────────────────────────────────────
case "${1:-setup}" in
    "setup")
        main
        ;;
    "test")
        test_services
        ;;
    "tts")
        test_tts
        ;;
    "logs")
        docker compose logs -f 2>/dev/null || docker-compose logs -f
        ;;
    "dashboard")
        open_dashboard
        ;;
    "stop")
        docker compose down 2>/dev/null || docker-compose down
        print_status "All services stopped"
        ;;
    "restart")
        docker compose restart 2>/dev/null || docker-compose restart
        print_status "All services restarted"
        ;;
    "status")
        docker compose ps 2>/dev/null || docker-compose ps
        ;;
    "network")
        create_network
        ;;
    *)
        echo "Usage: $0 {setup|test|tts|logs|dashboard|stop|restart|status|network}"
        echo ""
        echo "  setup     - Full setup (default)"
        echo "  test      - Test all service health endpoints"
        echo "  tts       - Test text-to-speech"
        echo "  logs      - Stream all service logs"
        echo "  dashboard - Open web dashboard in browser"
        echo "  stop      - Stop all services"
        echo "  restart   - Restart all services"
        echo "  status    - Show service status"
        echo "  network   - Create fyp-network if missing"
        exit 1
        ;;
esac