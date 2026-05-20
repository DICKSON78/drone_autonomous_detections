#!/usr/bin/env bash
# PC3 Monitoring Stack Launcher
# Starts Grafana + Prometheus + Node Exporter + InfluxDB + Telemetry Collector + API Gateway + Drone MAVLink Exporter

set -e

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
log() { echo -e "${GREEN}[PC3]${NC} $1"; }
warn() { echo -e "${YELLOW}[PC3]${NC} $1"; }
err()  { echo -e "${RED}[PC3]${NC} $1"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load environment variables
if [ -f "config/environment.env" ]; then
    export $(grep -v '^#' config/environment.env | xargs)
fi

# ── 0. Network ──
log "Ensuring fyp-network exists..."
docker network inspect fyp-network >/dev/null 2>&1 || docker network create fyp-network

# ── 1. Check PC2 MAVLink availability ──
log "Checking PC2 MAVLink port (14550)..."
if timeout 2 bash -c 'echo >/dev/udp/127.0.0.1/14550' 2>/dev/null; then
    log "MAVLink port 14550 reachable ✓"
else
    warn "MAVLink port 14550 not reachable — drone exporter will show disconnected until PC2 starts"
fi

# ── 2. Start Docker services ──
log "Starting monitoring stack (Grafana, Prometheus, Node Exporter, InfluxDB)..."

# Work around docker-compose v1.29.2 bug by removing stale containers first
docker rm -f grafana prometheus node-exporter influxdb 2>/dev/null || true

docker-compose up -d 2>&1 || {
    err "docker-compose failed. Falling back to docker run..."

    # InfluxDB
    docker rm -f influxdb 2>/dev/null || true
    docker run -d --name influxdb --restart unless-stopped --network fyp-network \
        -p 8086:8086 \
        -e DOCKER_INFLUXDB_INIT_MODE=setup \
        -e DOCKER_INFLUXDB_INIT_USERNAME=admin \
        -e DOCKER_INFLUXDB_INIT_PASSWORD=admin123 \
        -e DOCKER_INFLUXDB_INIT_ORG=drone-project \
        -e DOCKER_INFLUXDB_INIT_BUCKET=drone_telemetry \
        -e DOCKER_INFLUXDB_INIT_ADMIN_TOKEN=drone-telemetry-token \
        -e DOCKER_INFLUXDB_INIT_RETENTION=30d \
        -v influxdb_data:/var/lib/influxdb2 \
        -v "$SCRIPT_DIR/influxdb:/docker-entrypoint-initdb.d" \
        influxdb:2.7

    # Grafana
    docker rm -f grafana 2>/dev/null || true
    docker run -d --name grafana --restart unless-stopped --network fyp-network \
        -p 3000:3000 \
        -e GF_SECURITY_ADMIN_USER=admin \
        -e GF_SECURITY_ADMIN_PASSWORD=admin123 \
        -e GF_PATHS_PROVISIONING=/etc/grafana/provisioning \
        -e GF_SECURITY_ALLOW_EMBEDDING=true \
        -e GF_AUTH_ANONYMOUS_ENABLED=false \
        -e GF_USERS_ALLOW_SIGN_UP=false \
        -v grafana_data:/var/lib/grafana \
        -v "$SCRIPT_DIR/grafana/provisioning:/etc/grafana/provisioning" \
        -v "$SCRIPT_DIR/grafana/grafana.ini:/etc/grafana/grafana.ini" \
        -v "$SCRIPT_DIR/grafana/dashboards:/var/lib/grafana/dashboards" \
        grafana/grafana:latest

    # Prometheus
    docker rm -f prometheus 2>/dev/null || true
    docker run -d --name prometheus --restart unless-stopped --network fyp-network \
        -p 9090:9090 \
        -v "$SCRIPT_DIR/config/prometheus.yml:/etc/prometheus/prometheus.yml" \
        -v prometheus_data:/prometheus \
        prom/prometheus:latest

    # Node Exporter
    docker rm -f node-exporter 2>/dev/null || true
    docker run -d --name node-exporter --restart unless-stopped --network fyp-network \
        -p 9100:9100 \
        prom/node-exporter:latest
}

sleep 3

# ── 3. Verify Docker services ──
for svc in grafana prometheus node-exporter influxdb; do
    if docker ps --format '{{.Names}}' | grep -q "^${svc}$"; then
        log "${svc} running ✓"
    else
        warn "${svc} failed to start"
    fi
done

# ── 4. Start Drone Exporter (MAVLink → Prometheus metrics) ──
log "Starting Drone MAVLink Exporter on port 8007..."

# Kill any existing exporter
pkill -f "drone_exporter.py" 2>/dev/null || true
sleep 1

mkdir -p "$SCRIPT_DIR/logs"
nohup python3 "$SCRIPT_DIR/scripts/drone_exporter.py" > "$SCRIPT_DIR/logs/drone_exporter.log" 2>&1 &
EXPORTER_PID=$!
log "Drone exporter PID: $EXPORTER_PID"

sleep 2

if kill -0 $EXPORTER_PID 2>/dev/null; then
    log "Drone exporter running ✓"
else
    err "Drone exporter failed. Check logs: tail -f $SCRIPT_DIR/logs/drone_exporter.log"
fi

# ── 5. Wait for Grafana to be ready ──
log "Waiting for Grafana to be ready..."
for i in $(seq 1 15); do
    if curl -sf http://localhost:3000/api/health >/dev/null 2>&1; then
        log "Grafana ready ✓"
        break
    fi
    if [ "$i" -eq 15 ]; then
        warn "Grafana not ready after 30s. Check: docker logs grafana"
    fi
    sleep 2
done

# ── 6. Status ──
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║          ${BOLD}PC3 MONITORING STACK READY${NC}${CYAN}                   ║${NC}"
echo -e "${CYAN}╠══════════════════════════════════════════════════════════╣${NC}"
echo -e "${CYAN}║${NC}                                                      ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  ${BOLD}Service${NC}              ${BOLD}Port${NC}     ${BOLD}URL${NC}                   ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  ──────────────────────────────────────────────  ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  Grafana              3000     http://localhost:3000   ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  Prometheus           9090     http://localhost:9090   ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  Node Exporter        9100     http://localhost:9100   ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  InfluxDB             8086     http://localhost:8086   ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  Drone Exporter       8007     http://localhost:8007   ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  Drone Radar (UI)     8007     http://localhost:8007/radar ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}                                                      ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  ${BOLD}Grafana Login:${NC} admin / admin123                       ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  ${BOLD}InfluxDB Login:${NC} admin / admin123                      ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}                                                      ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  ${BOLD}Endpoints:${NC}                                           ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}    /metrics        — Prometheus scrape target            ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}    /health         — Health check                        ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}    /obstacles      — JSON obstacle list                  ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}    /radar          — PPI radar visualization             ${CYAN}║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
log "Logs: tail -f $SCRIPT_DIR/logs/drone_exporter.log"
log "Stop: docker-compose down && pkill -f drone_exporter.py"
