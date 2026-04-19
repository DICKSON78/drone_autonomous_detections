# Drone Autonomous Navigation System

This repository contains a complete autonomous drone navigation system with language-guided commands. The system is distributed across four logical components (PC1-PC4), all orchestrated using Docker.

## 🏗️ System Architecture

- **PC1 (Core & Kafka)**: Message broker and flight control logic.
- **PC2 (Vision & AI)**: YOLOv8 object detection, RL navigation, and Gazebo simulation.
- **PC3 (Telemetry & Dashboard)**: InfluxDB/Postgres storage, Grafana dashboards, and Node.js API Gateway.
- **PC4 (Feedback)**: Audio and visual feedback services.

## 🚀 One-Command Quick Start

To make it easy for all developers, we use a global system manager.

### 1. Prerequisites
- Docker & Docker Compose
- Git

### 2. Setup Shared Network
Before starting any containers, create the shared network:
```bash
docker network create fyp-network
```

### 3. Launch the System
Run the interactive manager script:
```bash
./manage_system.sh
```
- Select **Option 5** to start the entire stack.
- The manager will ensure all containers are started in the correct order.

## 🛠️ Development Workflow

- **Environment**: All services are containerized. You do **not** need to install Node.js, Python, or Databases on your host machine.
- **Configuration**: System-wide settings are in the `config/` folders of each PC.
- **Monitoring**: 
    - **Grafana**: [http://localhost:3000](http://localhost:3000) (admin/admin123)
    - **API Gateway**: [http://localhost:3001](http://localhost:3001)
    - **InfluxDB**: [http://localhost:8086](http://localhost:8086)

## 📂 Project Structure
```text
.
├── manage_system.sh       # Global system manager (Entry Point)
├── PC1/                   # Core & Messaging
├── PC2/                   # AI & Simulation
├── PC3/                   # Telemetry & Dashboard
├── PC4/                   # Feedback Service
└── docs/                  # Detailed documentation
```

## 🤝 Collaboration
When making changes:
1. Ensure your service's `Dockerfile` or `docker-compose.yml` is updated if you add new dependencies.
2. Test using the global manager to ensure cross-PC connectivity.
3. Keep `.env.example` files updated.
