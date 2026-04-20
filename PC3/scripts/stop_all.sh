#!/usr/bin/env bash
# Stop all PC3 services

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PC3_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PC3_DIR/logs"

GREEN='\033[0;32m'; NC='\033[0m'
log() { echo -e "${GREEN}[PC3]${NC} $1"; }

log "Stopping PC3 services..."

# Stop by PID files
for pid_file in "$LOG_DIR"/*.pid; do
  [ -f "$pid_file" ] || continue
  pid=$(cat "$pid_file")
  name=$(basename "$pid_file" .pid)
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid" && log "✓ Stopped $name (PID: $pid)"
  fi
  rm -f "$pid_file"
done

# Stop Docker services
cd "$PC3_DIR"
docker compose down
log "✓ Docker services stopped"
log "All PC3 services stopped."
