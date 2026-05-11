#!/bin/bash

# Start Colab Jupyter Container for Drone System
echo "🚁 Starting Colab Jupyter Container for Autonomous Drone System"
echo "================================================================"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Stop existing container if running
if docker ps -q -f name=colab-drone-system | grep -q .; then
    echo "🛑 Stopping existing colab-drone-system container..."
    docker stop colab-drone-system
    docker rm colab-drone-system
fi

# Build and start the container
echo "🔨 Building Colab Docker container..."
docker-compose -f docker-compose.colab.yml build

echo "🚀 Starting Colab Jupyter container..."
docker-compose -f docker-compose.colab.yml up -d

# Wait for container to start
echo "⏳ Waiting for Jupyter to start..."
sleep 10

# Check if container is running
if docker ps -q -f name=colab-drone-system | grep -q .; then
    echo "✅ Colab Jupyter container is running!"
    echo ""
    echo "📋 Connection Information:"
    echo "   • Local URL: http://localhost:39361"
    echo "   • Remote URL: http://YOUR_SERVER_IP:39361"
    echo "   • Token: No token required"
    echo ""
    echo "🔗 For Google Colab:"
    echo "   1. Go to Colab: https://colab.research.google.com"
    echo "   2. File → Connect to local runtime"
    echo "   3. Use: http://YOUR_SERVER_IP:39361"
    echo ""
    echo "📊 Check logs:"
    echo "   docker logs colab-drone-system"
else
    echo "❌ Failed to start Colab Jupyter container"
    exit 1
fi
