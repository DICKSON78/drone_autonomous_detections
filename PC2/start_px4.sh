#!/bin/bash
# Start script for PX4 Gazebo simulation
# Works around docker-compose v1.29.2 'ContainerConfig' bug

set -e
cd "$(dirname "$0")"

echo "=== PX4 Gazebo SITL Starter ==="

# Remove stale container if it exists (docker-compose v1.29.2 bug workaround)
if docker ps -a --format '{{.Names}}' | grep -q '^gazebo-px4$'; then
    echo "Removing stale gazebo-px4 container..."
    docker rm -f gazebo-px4 2>/dev/null || true
fi

# Start with docker-compose
echo "Starting services..."
docker-compose up -d gazebo-px4 2>&1

echo ""
echo "Waiting for PX4 to boot..."
sleep 10

# Check status
if docker ps -f name=gazebo-px4 --format '{{.Status}}' | grep -q "Up"; then
    echo "✓ gazebo-px4 is running"
    docker exec gazebo-px4 ps aux 2>/dev/null | grep -E "px4|gz sim" | head -2
else
    echo "✗ gazebo-px4 failed to start"
    docker logs gazebo-px4 --tail 30 2>&1 | grep -v "pxh>" | tail -10
fi
