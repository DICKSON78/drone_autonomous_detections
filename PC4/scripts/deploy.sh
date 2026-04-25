#!/bin/bash
# PC4 Deploy Script
# Zero-downtime deployment using docker-compose

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo "🚀 PC4 Deployment Script"
echo "======================="

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null && ! command -v docker &> /dev/null; then
  echo "❌ Docker or docker-compose not found"
  exit 1
fi

# Use 'docker compose' if available (newer), otherwise 'docker-compose'
if docker compose version &> /dev/null; then
  DOCKER_COMPOSE="docker compose"
else
  DOCKER_COMPOSE="docker-compose"
fi

# Source environment
if [ -f "config/environment.env" ]; then
  export $(cat config/environment.env | grep -v '^#' | xargs)
  echo "📋 Loaded environment from config/environment.env"
fi

# Pre-deployment checks
echo ""
echo "🔍 Pre-deployment checks..."

if [ ! -f "docker-compose.yml" ]; then
  echo "❌ docker-compose.yml not found"
  exit 1
fi

# Check if network exists
if ! docker network ls | grep -q fyp-network; then
  echo "⚠️  Creating fyp-network..."
  docker network create fyp-network || true
fi

# Build services
echo ""
echo "🔨 Building services..."
$DOCKER_COMPOSE build --no-cache

# Stop old containers gracefully
echo ""
echo "⏹️  Stopping old services..."
$DOCKER_COMPOSE down --remove-orphans 2>/dev/null || true

# Wait a moment
sleep 2

# Start new services
echo ""
echo "▶️  Starting new services..."
$DOCKER_COMPOSE up -d

# Wait for services to be ready
echo ""
echo "⏳ Waiting for services to be ready..."
for i in {1..30}; do
  if curl -s http://localhost:8005/health > /dev/null 2>&1 && \
     curl -s http://localhost:8006/health > /dev/null 2>&1 && \
     curl -s http://localhost:80 > /dev/null 2>&1; then
    echo "✅ All services are healthy!"
    break
  fi
  echo -n "."
  sleep 1
done

# Final status check
echo ""
echo "📊 Service status:"
$DOCKER_COMPOSE ps

echo ""
echo "🎉 Deployment complete!"
echo ""
echo "Services:"
echo "  - Feedback Service: http://localhost:8005"
echo "  - WebSocket Server: ws://localhost:8006"
echo "  - Web Dashboard:    http://localhost:80"
