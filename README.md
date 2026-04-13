# Autonomous Language-Guided Drone System - Docker Setup

A simulation-based autonomous drone system capable of executing environmental monitoring missions through natural language commands while providing real-time feedback to a user station.

## Project Overview

This Final Year Project develops a fully autonomous drone system that combines:
- **Language-Guided Navigation**: Natural language command parsing for high-level mission instructions
- **Reinforcement Learning**: Adaptive navigation using RL algorithms (PPO/DQN) for autonomous flight
- **Computer Vision**: Real-time obstacle detection and avoidance using YOLOv5
- **Environmental Awareness**: Simulation of environmental hazards (wind, terrain) in Gazebo
- **Intelligent Feedback**: Audio/text feedback system mimicking pilot-station communication
- **Complete Autonomy**: Mission execution without continuous human intervention

### Key Innovation
The system integrates full autonomy with a feedback module that mimics real UAV pilot-station interaction, allowing the drone to execute missions independently while keeping the user informed through status updates, obstacle alerts, and mission progress reports.

### Applications
- Environmental monitoring and wildlife research
- Disaster management and surveillance
- Agricultural inspection
- Conservation efforts

The entire system is implemented in simulation using Gazebo + PX4 + ROS, providing a safe testbed for developing and testing autonomous drone behaviors with intelligent feedback mechanisms.

## System Architecture

### PC 1: Command & Control (192.168.1.10)
- **Command Parser Service** (Port 8000) - Natural language command processing
- **Flight Control Service** (Port 8001) - MAVSDK drone control
- **Kafka Broker** (Port 9092) - Message queue

### PC 2: Vision & Navigation (192.168.1.11)
- **Object Detection Service** (Port 8002) - YOLOv5 AI vision
- **RL Navigation Service** (Port 8003) - Reinforcement Learning
- **Gazebo + PX4 SITL** - Drone simulation

### PC 3: Data & Monitoring (192.168.1.12)
- **Telemetry Collector** (Port 8004) - Data aggregation
- **InfluxDB** (Port 8086) - Time-series database
- **Grafana** (Port 3000) - Monitoring dashboard

### PC 4: Web Interface & Feedback (192.168.1.13)
- **Web Dashboard** (Port 80) - React control interface
- **WebSocket Server** (Port 8080) - Real-time updates
- **Feedback Service** (Port 8005) - Text-to-speech

## System Requirements

### Minimum Requirements per PC:
- **Operating System**: Ubuntu 20.04+ / Windows 10+ / macOS 10.15+
- **RAM**: 8GB (16GB recommended)
- **Storage**: 20GB free space
- **Network**: Internet connection for initial setup
- **Docker**: 20.10+ installed
- **Docker Compose**: 2.0+ installed

## Quick Start

### Step 1: Install Docker & Docker Compose

#### For Ubuntu/Debian:
```bash
# Update packages
sudo apt update

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose
sudo apt install docker-compose-plugin

# Verify installation
docker --version
docker compose version
```

#### For Windows:
1. Download **Docker Desktop** from https://docker.com/products/docker-desktop
2. Install with WSL2 enabled
3. Restart computer

#### For macOS:
1. Download **Docker Desktop** from https://docker.com/products/docker-desktop
2. Install and restart

### Step 2: Clone Repository
```bash
# Clone repository
git clone https://github.com/[your-username]/autonomous-drone-system.git
cd autonomous-drone-system
```

### Step 3: Network Configuration

#### Option A: Automatic Setup (Recommended)
```bash
# Run automatic setup
chmod +x setup.sh
./setup.sh
```

#### Option B: Manual Setup
```bash
# Edit your PC's IP in the setup script
nano setup.sh

# Replace with your actual IP:
PC1_IP="192.168.1.10"  # Change to your IP
PC2_IP="192.168.1.11"  # Change to your IP
PC3_IP="192.168.1.12"  # Change to your IP
PC4_IP="192.168.1.13"  # Change to your IP
```

### Step 4: Configure Network
Add to `/etc/hosts` (Linux/macOS):
```bash
sudo nano /etc/hosts

# Add these lines:
192.168.1.10 PC1
192.168.1.11 PC2
192.168.1.12 PC3
192.168.1.13 PC4
```

For Windows (C:\Windows\System32\drivers\etc\hosts):
```
192.168.1.10 PC1
192.168.1.11 PC2
192.168.1.12 PC3
192.168.1.13 PC4
```

## Instructions for Each PC Engineer

### PC 1: Command & Control Engineer

#### Your Responsibilities:
- **Natural Language Processing** - Parse user commands
- **Flight Control** - Manage drone operations
- **Message Broker** - Handle system communication

#### Services You'll Run:
```
Command Parser Service     (Port 8000)
Flight Control Service     (Port 8001)  
Kafka Message Broker       (Port 9092)
```

#### Setup Commands:
```bash
# After cloning repo
cd autonomous-drone-system
chmod +x setup.sh
./setup.sh

# Choose: 1) PC1 - Command & Control
# Enter team IPs when prompted
```

#### Testing Your Services:
```bash
# Test Command Parser
curl http://localhost:8000/health

# Test Flight Control  
curl http://localhost:8001/health

# Test Kafka
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --list
```

#### What You'll Work On:
- Improve NLP command parsing
- Add new flight commands
- Optimize Kafka performance
- Handle emergency procedures

#### Team Dependencies:
- **You send commands to:** PC2 (Flight instructions)
- **You receive data from:** PC2, PC3, PC4
- **Critical for:** System startup and command flow

---

### PC 2: Vision & Navigation Engineer

#### Your Responsibilities:
- **Object Detection** - YOLOv5 AI vision
- **Reinforcement Learning** - Autonomous navigation
- **Drone Simulation** - Gazebo + PX4

#### Services You'll Run:
```
Object Detection Service  (Port 8002)
RL Navigation Service      (Port 8003)
Gazebo Simulation         (GUI on PC2)
```

#### Setup Commands:
```bash
# After cloning repo
cd autonomous-drone-system
chmod +x setup.sh
./setup.sh

# Choose: 2) PC2 - Vision & Navigation
# Enter team IPs when prompted
```

#### Testing Your Services:
```bash
# Test Object Detection
curl http://localhost:8002/health

# Test RL Navigation
curl http://localhost:8003/health

# Test Gazebo (GUI should open)
docker exec -it gazebo-px4 gazebo
```

#### What You'll Work On:
- Train YOLOv5 for better detection
- Improve RL navigation algorithms
- Optimize simulation performance
- Add new object classes

#### Team Dependencies:
- **You receive from:** PC1 (Flight commands)
- **You send to:** PC1 (Navigation updates), PC3 (Detection data)
- **Critical for:** Autonomous flight and safety

---

### PC 3: Data & Monitoring Engineer

#### Your Responsibilities:
- **Data Collection** - Gather all telemetry
- **Time-Series Database** - InfluxDB management
- **Analytics Dashboard** - Grafana visualization

#### Services You'll Run:
```
Telemetry Collector      (Port 8004)
InfluxDB Database        (Port 8086)
Grafana Dashboard        (Port 3000)
```

#### Setup Commands:
```bash
# After cloning repo
cd autonomous-drone-system
chmod +x setup.sh
./setup.sh

# Choose: 3) PC3 - Data & Monitoring
# Enter team IPs when prompted
```

#### Testing Your Services:
```bash
# Test Telemetry Collector
curl http://localhost:8004/health

# Test InfluxDB
curl http://localhost:8086/health

# Test Grafana (Open browser)
# URL: http://localhost:3000
# Username: admin
# Password: admin123
```

#### What You'll Work On:
- Design Grafana dashboards
- Optimize database performance
- Create analytics reports
- Monitor system health

#### Team Dependencies:
- **You receive from:** PC1, PC2, PC4 (All data)
- **You provide to:** PC4 (Dashboard data), Team (Analytics)
- **Critical for:** System monitoring and performance analysis

---

### PC 4: Web Interface & Feedback Engineer

#### Your Responsibilities:
- **Web Dashboard** - React user interface
- **Real-time Updates** - WebSocket communication
- **Audio Feedback** - Text-to-speech system

#### Services You'll Run:
```
Web Dashboard            (Port 80)
WebSocket Server         (Port 8080)
Feedback Service         (Port 8005)
```

#### Setup Commands:
```bash
# After cloning repo
cd autonomous-drone-system
chmod +x setup.sh
./setup.sh

# Choose: 4) PC4 - Web Interface
# Enter team IPs when prompted
```

#### Testing Your Services:
```bash
# Test Web Dashboard (Open browser)
# URL: http://localhost

# Test WebSocket
curl http://localhost:8080

# Test Feedback Service
curl http://localhost:8005/health

# Test TTS
curl -X POST http://localhost:8005/speak \
  -H "Content-Type: application/json" \
  -d '{"message": "Test audio feedback"}'
```

#### What You'll Work On:
- Improve React dashboard UI
- Add real-time features
- Enhance audio feedback
- Mobile responsiveness

#### Team Dependencies:
- **You receive from:** PC3 (Telemetry data)
- **You send to:** PC1 (User commands)
- **Critical for:** User experience and system control

## Deployment Steps

#### 1. PC1 Setup (Command & Control)
```bash
cd PC1
docker-compose up -d
```

#### 2. PC2 Setup (Vision & Navigation)
```bash
cd PC2
docker-compose up -d
```

#### 3. PC3 Setup (Data & Monitoring)
```bash
cd PC3
docker-compose up -d
```

#### 4. PC4 Setup (Web Interface)
```bash
cd PC4
docker-compose up -d
```

## Configuration

### Environment Variables
Each service can be configured via environment variables in docker-compose.yml:

- `KAFKA_BOOTSTRAP_SERVERS` - Kafka broker address
- `INFLUXDB_URL` - InfluxDB connection URL
- `INFLUXDB_TOKEN` - Database authentication token

### Service Endpoints

#### PC1 Services
- Command Parser: `http://PC1:8000`
- Flight Control: `http://PC1:8001`
- Kafka: `PC1:9092`

#### PC2 Services
- Object Detection: `http://PC2:8002`
- RL Navigation: `http://PC2:8003`
- Gazebo Simulation: Available on PC2

#### PC3 Services
- Telemetry Collector: `http://PC3:8004`
- InfluxDB: `http://PC3:8086`
- Grafana: `http://PC3:3000` (admin/admin123)

#### PC4 Services
- Web Dashboard: `http://PC4`
- WebSocket Server: `http://PC4:8080`
- Feedback Service: `http://PC4:8005`

## Usage

### 1. Access Web Dashboard
Open browser: `http://PC4`

### 2. Send Commands
Type natural language commands:
- "Go to forest area and inspect for animals"
- "Return to home base"
- "Fly to lake and monitor"

### 3. Monitor System
- **Grafana Dashboard**: `http://PC3:3000`
- **Real-time Telemetry**: Web interface
- **Audio Feedback**: Automatic TTS announcements

## How PCs Work Together

### Communication Flow:
```
PC1 (Commands) → Kafka → PC2 (Flight) → PC3 (Data) → PC4 (Display)
     ↑                                                      ↓
     ←←←←←←←←←←←←← Feedback Loop ←←←←←←←←←←←←←←←←←←←←←←←
```

### Mission Example:
1. **User types:** "Go to forest area" (PC4)
2. **PC1 parses:** Command → GPS coordinates
3. **PC2 executes:** Flies drone, avoids obstacles
4. **PC3 stores:** All telemetry and detections
5. **PC4 displays:** Live map and speaks updates

### Access Points:
- **Main Dashboard:** `http://PC4_IP`
- **Analytics:** `http://PC3_IP:3000`
- **API Testing:** `http://PC1_IP:8000/docs`

## Monitoring

### Grafana Dashboards
1. GPS position tracking
2. Altitude graphs
3. Battery monitoring
4. Object detection statistics
5. System performance metrics

### Health Checks
All services expose `/health` endpoint:
```bash
curl http://PC1:8000/health
curl http://PC2:8002/health
curl http://PC3:8004/health
curl http://PC4:8005/health
```

## Troubleshooting

### Common Issues

#### 1. Kafka Connection Issues
```bash
# Check Kafka status
docker exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092

# Check topics
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --list
```

#### 2. Drone Connection Issues
```bash
# Check PX4 SITL
docker logs gazebo-px4

# Check MAVLink connection
docker exec flight-control python -c "from mavsdk import System; print('MAVSDK OK')"
```

#### 3. Audio Issues (PC4)
```bash
# Check audio devices
docker exec feedback-service aplay -l

# Test TTS
curl -X POST http://PC4:8005/speak \
  -H "Content-Type: application/json" \
  -d '{"message": "Test audio"}'
```

#### 4. Docker Connection Issues
```bash
# Check Docker status
sudo systemctl status docker

# Restart Docker
sudo systemctl restart docker

# Check if user is in docker group
groups $USER
```

#### 5. Port Conflicts
```bash
# Check what's using ports
sudo netstat -tulpn | grep :8000

# Kill conflicting processes
sudo kill -9 [PID]
```

### Service Logs
```bash
# View logs for any service
docker logs [container_name]

# Follow logs in real-time
docker logs -f [container_name]

# All services on a PC
docker-compose logs -f
```

## Success Checklist

### PC1 Engineer:
- [ ] Command Parser responding
- [ ] Flight Control connected
- [ ] Kafka topics created
- [ ] Can send test commands

### PC2 Engineer:
- [ ] YOLOv5 model loaded
- [ ] RL agent trained
- [ ] Gazebo simulation running
- [ ] Object detection working

### PC3 Engineer:
- [ ] InfluxDB receiving data
- [ ] Grafana dashboards loaded
- [ ] Telemetry collector running
- [ ] Database schema created

### PC4 Engineer:
- [ ] React dashboard loading
- [ ] WebSocket connected
- [ ] TTS speaking
- [ ] Real-time updates working

## Team Coordination

### Daily Workflow:
1. **Morning:** Check service health
2. **Development:** Work on your PC's features
3. **Testing:** Coordinate with team for integration
4. **Monitoring:** Check Grafana dashboards

### Communication:
- **Slack/Discord:** Daily coordination
- **GitHub:** Code sharing and issues
- **Grafana:** Performance monitoring
- **Web Dashboard:** Real-time system status

### Troubleshooting:
1. **Check your services first**
2. **Verify network connectivity**
3. **Check team member services**
4. **Use logs for debugging**

## Maintenance

### Updates
```bash
# Pull latest changes
git pull

# Rebuild services
docker-compose down
docker-compose up -d --build
```

### Backup Data
```bash
# Backup Grafana dashboards
docker exec grafana cp -r /var/lib/grafana/dashboards ./backup/

# Backup InfluxDB data
docker exec influxdb influx backup /backup/$(date +%Y%m%d)
```

### Scaling
To add more processing power:
```bash
# Scale specific services
docker-compose up -d --scale object-detection=2
docker-compose up -d --scale rl-navigation=2
```

## Development

### Adding New Services
1. Create new service directory
2. Add Dockerfile and requirements.txt
3. Update docker-compose.yml
4. Add Kafka topics if needed

### Testing
```bash
# Test individual services
docker-compose up --build [service_name]

# Integration tests
cd tests && python test_integration.py
```

## Ready to Fly!

Once all PCs are running:
1. **Open:** `http://PC4_IP` (Main dashboard)
2. **Send command:** "Go to forest area"
3. **Monitor:** All PCs working together
4. **Enjoy:** Autonomous drone system!

**Each PC is critical - team success depends on everyone!**

---

**System Requirements:**
- Ubuntu 20.04+ or equivalent
- Docker 20.10+
- Docker Compose 2.0+
- 8GB+ RAM per PC
- Network connectivity between PCs

**Total Setup Time: ~10 minutes**
