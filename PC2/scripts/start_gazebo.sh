#!/bin/bash
# Start Gazebo + PX4 SITL with lightweight Dodoma world
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "========================================"
echo "  Drone Autonomous Simulation Launcher"
echo "========================================"

# 1. Generate lightweight world (54 models instead of 158)
echo "[1/5] Generating lightweight city world..."
python3 scripts/gen_performant_city.py

# 2. Ensure fyp-network exists
echo "[2/5] Checking Docker network..."
docker network ls | grep -q "fyp-network" || docker network create fyp-network

# 3. Stop existing containers
echo "[3/5] Stopping existing containers..."
for c in gazebo-px4 object-detection kafka-bridge; do
    docker stop "$c" 2>/dev/null && docker rm "$c" 2>/dev/null || true
done

# 4. Build and start services
echo "[4/5] Starting containers..."
docker compose up -d gazebo-px4

echo "   Waiting for Gazebo to initialize..."
sleep 8

# Check Gazebo is running
if docker ps -q -f name=gazebo-px4 | grep -q .; then
    echo "   Gazebo running ✓"
else
    echo "   ERROR: Gazebo failed to start"
    docker logs gazebo-px4 --tail 30
    exit 1
fi

echo "[5/5] Starting auxiliary services..."
docker compose up -d object-detection 2>/dev/null || true

echo ""
echo "========================================"
echo "  Simulation is running!"
echo "========================================"
echo ""
echo "  To connect drone console:"
echo "    python3 scripts/enhanced_drone_console_v2.py 127.0.0.1 14540"
echo ""
echo "  To run auto flight mission:"
echo "    python3 scripts/auto_flight.py"
echo ""
echo "  To check Gazebo logs:"
echo "    docker logs gazebo-px4 -f"
echo ""
echo "  YOLO detection available at:"
echo "    http://localhost:8002/detect"
echo "========================================"
