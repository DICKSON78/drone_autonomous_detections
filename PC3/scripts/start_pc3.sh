#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# PC3 Startup Script
# Starts: Docker (InfluxDB + Grafana), Python Telemetry Collector, Node.js Gateway
# ─────────────────────────────────────────────────────────────────────────────

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PC3_DIR="$SCRIPT_DIR"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'

log()  { echo -e "${GREEN}[PC3]${NC} $1"; }
warn() { echo -e "${YELLOW}[PC3]${NC} $1"; }
err()  { echo -e "${RED}[PC3]${NC} $1"; }

log "============================================="
log "  PC3 - TELEMETRY & DASHBOARD SYSTEM"
log "============================================="

# ─── 1. Docker services ───────────────────────────────────────────────────────
log "Starting Docker services (InfluxDB + Grafana + Postgres)..."
cd "$PC3_DIR"
docker compose up -d influxdb grafana postgres
log "Waiting for databases to be ready..."
until curl -sf http://localhost:8086/health > /dev/null 2>&1; do
  sleep 3; printf '.'
done
log "✓ InfluxDB ready"

# ─── 2. Python Telemetry Collector ───────────────────────────────────────────
log "Starting Python Telemetry Collector (port 8004)..."
if [ -d "$HOME/fyp_env" ]; then
  source "$HOME/fyp_env/bin/activate"
elif [ -d "$HOME/.venv" ]; then
  source "$HOME/.venv/bin/activate"
else
  warn "No virtual environment found — using system Python"
fi

cd "$PC3_DIR/src/telemetry-collector"
pip install -q -r requirements.txt
nohup python telemetry.py > "$PC3_DIR/logs/telemetry-collector.log" 2>&1 &
TELEMETRY_PID=$!
echo $TELEMETRY_PID > "$PC3_DIR/logs/telemetry-collector.pid"
log "✓ Telemetry Collector started (PID: $TELEMETRY_PID)"

# ─── 3. Node.js API Gateway ──────────────────────────────────────────────────
log "Starting Node.js API Gateway (port 3001)..."
cd "$PC3_DIR/src/api-gateway"

# Create .env from example if it doesn't exist
if [ ! -f .env ]; then
  cp .env.example .env
  warn "Created .env from .env.example — update KAFKA_BROKERS if needed"
fi

npm install --silent
mkdir -p "$PC3_DIR/logs"
nohup npm start > "$PC3_DIR/logs/api-gateway.log" 2>&1 &
GATEWAY_PID=$!
echo $GATEWAY_PID > "$PC3_DIR/logs/api-gateway.pid"
log "✓ API Gateway started (PID: $GATEWAY_PID)"

# ─── 4. Wait and verify ───────────────────────────────────────────────────────
sleep 4
log "Verifying services..."

check_service() {
  local name="$1"; local url="$2"
  if curl -sf "$url" > /dev/null 2>&1; then
    log "  ✓ $name → $url"
  else
    warn "  ✗ $name not responding at $url (may still be starting)"
  fi
}

check_service "InfluxDB"            "http://localhost:8086/health"
check_service "Grafana"             "http://localhost:3000/api/health"
check_service "API Gateway"         "http://localhost:3001/api/health"
check_service "Telemetry Collector" "http://localhost:8004/health"

log "Checking Postgres..."
if docker exec postgres pg_isready -U fyp_user -d fyp_db > /dev/null 2>&1; then
  log "  ✓ Postgres → Ready"
else
  warn "  ✗ Postgres not responding"
fi

log "============================================="
log "  PC3 SERVICES RUNNING"
log "============================================="
log "  InfluxDB  : http://localhost:8086"
log "  Grafana   : http://localhost:3000   (admin / admin123)"
log "  Python    : http://localhost:8004"
log "  API GW    : http://localhost:3001"
log "  WebSocket : ws://localhost:3001/ws"
log "  Logs      : $PC3_DIR/logs/"
log "============================================="
log "  To stop all:  $SCRIPT_DIR/scripts/stop_all.sh"
