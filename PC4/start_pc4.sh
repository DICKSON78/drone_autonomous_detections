#!/bin/bash
# PC4 — Start all services
# Usage: ./start_pc4.sh [command]
#   start     Docker compose up (default)
#   dev       Run feedback service directly (Python, no Docker)
#   stop      Docker compose down
#   restart   Docker compose restart
#   rebuild   Docker compose up --build
#   logs      Follow logs
#   status    Show container status
#   test      Run all tests
#   cli       Launch interactive drone CLI

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${GREEN}[PC4]${NC} $1"; }
warn()  { echo -e "${YELLOW}[PC4]${NC} $1"; }
err()   { echo -e "${RED}[PC4]${NC} $1"; }
header(){ echo -e "${BLUE}══════════════════════════════════════${NC}"; }

# Detect docker compose command
if docker compose version &>/dev/null; then
  DC="docker compose"
elif docker-compose --version &>/dev/null; then
  DC="docker-compose"
else
  DC=""
fi

ensure_network() {
  if ! docker network ls | grep -q fyp-network; then
    info "Creating fyp-network..."
    docker network create fyp-network
  fi
}

source_env() {
  if [ -f config/environment.env ]; then
    set -a
    source config/environment.env
    set +a
  fi
}

# ── Commands ──────────────────────────────────────────────────────────

cmd_start() {
  header
  info "Starting PC4 feedback service (Docker)..."
  source_env
  ensure_network
  $DC up -d
  info "Waiting for health check..."
  for i in $(seq 1 15); do
    if curl -sf http://localhost:8005/health >/dev/null 2>&1; then
      info "Feedback service is healthy on http://localhost:8005"
      header
      exit 0
    fi
    echo -n "."
    sleep 1
  done
  warn "Health check did not pass within 15 s — check logs"
}

cmd_dev() {
  header
  info "Starting feedback service directly (dev mode)..."
  source_env
  export KAFKA_BOOTSTRAP_SERVERS="${KAFKA_BOOTSTRAP_SERVERS:-kafka:9092}"

  # Install deps if missing
  pip install -q -r src/feedback-service/requirements.txt 2>/dev/null || true

  # Create log directory
  mkdir -p /tmp/pc4-logs
  export NLG_LOG_FILE=/tmp/pc4-logs/nlg_generator.log

  info "KAFKA_BOOTSTRAP_SERVERS=$KAFKA_BOOTSTRAP_SERVERS"
  info "Starting uvicorn on http://0.0.0.0:8005"
  echo
  python src/feedback-service/feedback.py
}

cmd_stop() {
  if [ -n "$DC" ]; then
    info "Stopping services..."
    $DC down --remove-orphans 2>/dev/null || true
  else
    info "Stopping feedback.py processes..."
    pkill -f "feedback\.py" 2>/dev/null || true
  fi
  info "Stopped"
}

cmd_restart() {
  cmd_stop
  sleep 1
  cmd_start
}

cmd_rebuild() {
  header
  info "Rebuilding and starting..."
  source_env
  ensure_network
  $DC down --remove-orphans 2>/dev/null || true
  $DC up -d --build
  info "Waiting for health check..."
  for i in $(seq 1 30); do
    if curl -sf http://localhost:8005/health >/dev/null 2>&1; then
      info "Feedback service is healthy on http://localhost:8005"
      header
      exit 0
    fi
    echo -n "."
    sleep 1
  done
  warn "Health check did not pass within 30 s"
}

cmd_logs() {
  if [ -n "$DC" ]; then
    $DC logs -f
  else
    warn "No docker-compose found. Use: tail -f /tmp/pc4-logs/nlg_generator.log"
  fi
}

cmd_status() {
  if [ -n "$DC" ]; then
    $DC ps
  else
    warn "Docker not available"
  fi
  echo
  if curl -sf http://localhost:8005/health >/dev/null 2>&1; then
    info "Feedback service: RUNNING"
    curl -s http://localhost:8005/health | python3 -m json.tool 2>/dev/null || true
  else
    warn "Feedback service: NOT REACHABLE"
  fi
}

cmd_test() {
  header
  info "Running all PC4 tests..."
  source_env

  # Install deps if missing
  pip install -q -r src/feedback-service/requirements.txt 2>/dev/null || true

  cd src/feedback-service
  python -m pytest ../../tests/ -v "$@"
}

cmd_cli() {
  header
  info "Launching drone CLI..."
  source_env
  pip install -q -r src/feedback-service/requirements.txt 2>/dev/null || true
  exec python scripts/drone_cli.py "$@"
}

# ── Main ──────────────────────────────────────────────────────────────

case "${1:-start}" in
  start)    cmd_start ;;
  dev)      cmd_dev ;;
  stop)     cmd_stop ;;
  restart)  cmd_restart ;;
  rebuild)  cmd_rebuild ;;
  logs)     cmd_logs ;;
  status)   cmd_status ;;
  test)     shift; cmd_test "$@" ;;
  cli)      shift; cmd_cli "$@" ;;
  *)
    echo "Usage: $0 {start|dev|stop|restart|rebuild|logs|status|test|cli}"
    echo ""
    echo "  start     Docker compose up (default)"
    echo "  dev       Run feedback service directly (Python, no Docker)"
    echo "  stop      Docker compose down"
    echo "  restart   Docker compose restart"
    echo "  rebuild   Docker compose up --build"
    echo "  logs      Follow logs"
    echo "  status    Show container status"
    echo "  test      Run all tests"
    echo "  cli       Launch interactive drone CLI"
    exit 1
    ;;
esac
