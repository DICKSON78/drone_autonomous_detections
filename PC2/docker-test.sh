#!/bin/bash

# Docker Setup Test Script for Autonomous Drone System
echo "🚁 Testing Docker Setup for Autonomous Drone System"
echo "=================================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

echo "✅ Docker is running"

# Check if network exists
if ! docker network ls | grep -q "fyp-network"; then
    echo "🌐 Creating fyp-network..."
    docker network create fyp-network
else
    echo "✅ fyp-network already exists"
fi

# Test build object-detection service
echo ""
echo "🔍 Building object-detection service..."
if docker build -t drone-object-detection ./src/object-detection/; then
    echo "✅ object-detection service built successfully"
else
    echo "❌ Failed to build object-detection service"
    exit 1
fi

# Test build rl-navigation service
echo ""
echo "🧠 Building rl-navigation service..."
if docker build -t drone-rl-navigation ./src/rl-navigation/; then
    echo "✅ rl-navigation service built successfully"
else
    echo "❌ Failed to build rl-navigation service"
    exit 1
fi

# Test build integrated-pipeline service
echo ""
echo "🔌 Building integrated-pipeline service..."
if docker build -t drone-integrated-pipeline ./src/integrated-pipeline/; then
    echo "✅ integrated-pipeline service built successfully"
else
    echo "❌ Failed to build integrated-pipeline service"
    exit 1
fi

echo ""
echo "🎉 All Docker services built successfully!"
echo ""
echo "📋 Services available:"
echo "   • object-detection (port 8002)"
echo "   • rl-navigation (port 8003)"
echo "   • integrated-pipeline (port 8004)"
echo ""
echo "🚀 To start all services:"
echo "   docker-compose up -d"
echo ""
echo "🧪 To test individual services:"
echo "   docker run -p 8002:8002 drone-object-detection"
echo "   docker run -p 8003:8003 drone-rl-navigation"
echo "   docker run -p 8004:8004 drone-integrated-pipeline"
