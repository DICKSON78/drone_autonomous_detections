#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;96m'; BOLD='\033[1m'; RESET='\033[0m'

MODEL="${1:-yolov8n.pt}"
HOST="${2:-127.0.0.1}"
PORT="${3:-14550}"
CAMERA="${4:-simulation}"
ALT="${5:-25}"

echo -e "${CYAN}${BOLD}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║       INTEGRATED DRONE — YOLO + MAVLink AUTOPILOT      ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${RESET}"

echo -e "  ${BOLD}Configuration:${RESET}"
echo -e "  YOLO Model : ${GREEN}${MODEL}${RESET}"
echo -e "  Drone Host : ${HOST}:${PORT}"
echo -e "  Camera     : ${CAMERA}"
echo -e "  Altitude   : ${ALT}m"
echo ""

# Check YOLO model exists
if [ ! -f "${MODEL}" ] && [ "${MODEL}" = "yolov8n.pt" ]; then
    echo -e "  ${YELLOW}Downloading YOLOv8n model...${RESET}"
    python3 -c "from ultralytics import YOLO; YOLO('yolov8n.pt')" 2>/dev/null || true
fi

echo -e "  ${GREEN}Starting integrated drone system...${RESET}"
echo ""

python3 "${SCRIPT_DIR}/integrated_drone.py" \
    "${HOST}" "${PORT}" \
    --yolo-model "${MODEL}" \
    --confidence 0.5 \
    --camera "${CAMERA}" \
    --alt "${ALT}"
