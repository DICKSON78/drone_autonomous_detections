#!/usr/bin/env bash

# ─────────────────────────────────────────────────────────────────────────────
# DRONE AUTONOMOUS SYSTEM - GLOBAL MANAGER
# ─────────────────────────────────────────────────────────────────────────────

# Colors for output
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Base directory
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log() { echo -e "${GREEN}[SYSTEM]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ─── Ensure Network Exists ───────────────────────────────────────────────────
ensure_network() {
    if ! docker network inspect fyp-network >/dev/null 2>&1; then
        log "Creating shared network: fyp-network..."
        docker network create fyp-network
    else
        log "Shared network 'fyp-network' is ready."
    fi
}

# ─── Start PC1 ────────────────────────────────────────────────────────────────
start_pc1() {
    log "Starting PC1 (Core & Kafka)..."
    cd "$ROOT_DIR/PC1" && docker compose up -d
}

# ─── Start PC2 ────────────────────────────────────────────────────────────────
start_pc2() {
    log "Starting PC2 (Vision & AI)..."
    cd "$ROOT_DIR/PC2" && docker compose up -d
}

# ─── Start PC3 ────────────────────────────────────────────────────────────────
start_pc3() {
    log "Starting PC3 (Telemetry & Dashboard)..."
    cd "$ROOT_DIR/PC3" && ./setup.sh
}

# ─── Start PC4 ────────────────────────────────────────────────────────────────
start_pc4() {
    log "Starting PC4 (Feedback)..."
    cd "$ROOT_DIR/PC4" && docker compose up -d
}

# ─── Main Menu ────────────────────────────────────────────────────────────────
main_menu() {
    clear
    echo -e "${CYAN}==================================================${NC}"
    echo -e "${CYAN}     DRONE AUTONOMOUS SYSTEM MANAGER             ${NC}"
    echo -e "${CYAN}==================================================${NC}"
    echo -e "1) Start PC1 (Core, Kafka, Zookeeper)"
    echo -e "2) Start PC2 (YOLOv8, RL Navigation, Gazebo)"
    echo -e "3) Start PC3 (API Gateway, InfluxDB, Grafana)"
    echo -e "4) Start PC4 (Feedback Service)"
    echo -e "5) Start ALL (Full System)"
    echo -e "--------------------------------------------------"
    echo -e "s) Show Status (docker ps)"
    echo -e "q) Quit"
    echo -n "Select an option: "
}

# ─── Execution ────────────────────────────────────────────────────────────────
ensure_network

while true; do
    main_menu
    read -r choice
    case $choice in
        1) start_pc1 ;;
        2) start_pc2 ;;
        3) start_pc3 ;;
        4) start_pc4 ;;
        5) 
            start_pc1
            sleep 5 # Wait for Kafka
            start_pc3
            start_pc2
            start_pc4
            ;;
        s|S)
            log "Current Docker status:"
            docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
            echo -e "\nPress Enter to continue..."
            read -r
            ;;
        q|Q)
            log "Exiting..."
            exit 0
            ;;
        *)
            error "Invalid choice: $choice"
            sleep 1
            ;;
    esac
    echo -e "\nTask complete. Press Enter to return to menu..."
    read -r
done
