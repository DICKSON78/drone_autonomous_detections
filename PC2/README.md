# PC2: Vision & Navigation

## Your Role
You are the Vision & Navigation Engineer! You are the eyes and brain of the drone.

### What You Do:
- **See the world** - YOLOv5 detects objects (trees, animals, buildings)
- **Think and navigate** - Reinforcement Learning makes autonomous decisions
- **Simulate reality** - Gazebo creates 3D world for drone to fly in

## Services You'll Run

```
Object Detection Service  (Port 8002)
RL Navigation Service      (Port 8003)
Gazebo Simulation         (GUI on your PC)
```

## Quick Setup (5 Minutes)

### Step 1: Install Docker (If not installed)
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose
sudo apt install docker-compose-plugin -y
```

### **Step 2: Install Graphics Drivers (Important for Gazebo)**
```bash
# For NVIDIA GPUs
sudo apt install nvidia-driver-470 nvidia-cuda-toolkit

# For Intel/AMD GPUs
sudo apt install mesa-utils libgl1-mesa-glx libglu1-mesa

# Reboot after installation
sudo reboot
```

### **Step 3: Run Setup Script**
```bash
# Make script executable
chmod +x setup.sh

# Run setup (does everything automatically)
./setup.sh
```

### **Step 4: Enter Team IPs**
Script will ask for team member IPs:
```
PC1 IP [192.168.1.10]: 192.168.1.10
PC2 IP [Your IP - press Enter]: 
PC3 IP [192.168.1.12]: 192.168.1.12
PC4 IP [192.168.1.13]: 192.168.1.13
```

### **Step 5: Wait for Setup**
- **Download time**: 10-15 minutes (YOLO model + Gazebo)
- **Build time**: 5-8 minutes
- **Start time**: 2 minutes

**Total time: ~25 minutes first time, 3 minutes subsequent**

##  Test Your Services

After setup completes, test everything:

```bash
# Test Object Detection
curl http://localhost:8002/health
# Should return: {"status": "healthy", "service": "object-detection"}

# Test RL Navigation
curl http://localhost:8003/health
# Should return: {"status": "healthy", "service": "rl-navigation"}

# Test Gazebo (GUI should open automatically)
# If not, open manually:
docker exec -it gazebo-px4 gazebo
```

##  Test Object Detection

```bash
# Test YOLOv5 detection
curl -X POST http://localhost:8002/detect \
  -H "Content-Type: application/json" \
  -d '{"image": "base64_encoded_image_data"}'

# Response should be:
# {
#   "status": "success",
#   "detections": [
#     {
#       "class": "tree",
#       "confidence": 0.85,
#       "bbox": [100, 100, 200, 300],
#       "distance_estimate": "15m"
#     }
#   ]
# }
```

##  Test RL Navigation

```bash
# Test RL agent (it will make navigation decisions)
curl http://localhost:8003/health
# The agent should be processing drone position and obstacles
```

##  Gazebo Simulation

### **Open Gazebo GUI:**
```bash
# Method 1: Automatic (should open during setup)
# Method 2: Manual
docker exec -it gazebo-px4 gazebo

# Method 3: With specific world
docker exec -it gazebo-px4 gazebo /usr/share/gazebo-11/worlds/empty.world
```

### **What You Should See:**
- **3D environment** with ground, sky, and objects
- **Drone model** (should be visible)
- **Physics simulation** running
- **Camera view** from drone perspective

##  Monitor Your Services

```bash
# Check all services status
docker-compose ps

# View logs (real-time)
docker-compose logs -f

# Check specific service logs
docker-compose logs -f object-detection
docker-compose logs -f rl-navigation
docker-compose logs -f gazebo-px4
```

##  Common Issues & Solutions

### **Issue: "Gazebo won't open / Black screen"**
```bash
# Check graphics drivers
glxinfo | grep "OpenGL renderer"

# Install/update drivers
sudo apt update
sudo apt install nvidia-driver-470

# Allow X11 forwarding
xhost +local:docker

# Restart Gazebo
docker-compose restart gazebo-px4
```

### **Issue: "YOLO model not found"**
```bash
# Check if model was downloaded
docker exec object-detection ls -la /app/

# Download manually if needed
docker exec object-detection wget -O /app/yolov5s.pt \
  https://github.com/ultralytics/yolov5/releases/download/v7.0/yolov5s.pt

# Restart service
docker-compose restart object-detection
```

### **Issue: "RL agent not training"**
```bash
# Check RL logs
docker-compose logs rl-navigation

# Restart RL service
docker-compose restart rl-navigation

# Check if GPU is available
docker exec rl-navigation python -c "import torch; print(torch.cuda.is_available())"
```

### **Issue: "High CPU usage"**
```bash
# Check resource usage
docker stats

# Limit resources if needed
# Edit docker-compose.yml and add:
# deploy:
#   resources:
#     limits:
#       cpus: '2.0'
#       memory: 4G
```

##  What You Should See

### **Successful Setup:**
```bash
# docker-compose ps output should show:
NAME                COMMAND                  SERVICE             STATUS              PORTS
object-detection     "python detector.py"     object-detection     running             0.0.0.0:8002->8002/tcp
rl-navigation        "python rl_agent.py"     rl-navigation        running             0.0.0.0:8003->8003/tcp
gazebo-px4          "/bin/bash -c './..."   gazebo-px4           running
```

### **Gazebo Window:**
- **3D world** with terrain
- **Drone model** in center
- **Objects** (trees, buildings) placed
- **Physics** simulation active

### **Health Check Results:**
```bash
# All should return "healthy"
curl http://localhost:8002/health  ✓
curl http://localhost:8003/health  ✓
```

##  Daily Workflow

### **Every Morning:**
```bash
cd /path/to/PC2
docker-compose ps  # Check services
docker exec gazebo-px4 gazebo  # Open simulation
```

### **When Developing:**
```bash
# View detection logs while coding
docker-compose logs -f object-detection

# Test new detection model
curl -X POST http://localhost:8002/detect \
  -H "Content-Type: application/json" \
  -d '{"image": "test_image"}'
```

### **When Training RL:**
```bash
# Monitor training progress
docker-compose logs -f rl-navigation

# Check training metrics
docker exec rl-navigation python -c "
import torch
model = torch.load('rl_navigation_model.pth')
print(f'Model parameters: {sum(p.numel() for p in model.parameters())}')
"
```

##  Success Indicators

You're successful when:
- [ ] All 3 services are running
- [ ] Health endpoints return "healthy"
- [ ] Gazebo opens with 3D world
- [ ] YOLOv5 model detects objects
- [ ] RL agent makes navigation decisions
- [ ] Other PCs receive your data

##  Team Communication

### **You Coordinate With:**
- **PC1**: Receive flight commands, send navigation updates
- **PC3**: Send detection data, receive telemetry
- **PC4**: Provide obstacle warnings, receive user input

### **Your Critical Functions:**
- **Vision processing** - All object detection goes through you
- **Autonomous navigation** - RL decisions control drone movement
- **Simulation** - Gazebo provides realistic environment

##  Next Steps

Once your PC2 is running:
1. **Explore Gazebo** - Add objects, test physics
2. **Train YOLO** - Improve detection accuracy
3. **Develop RL** - Enhance navigation algorithms
4. **Test integration** - Work with PC1 for flight commands

##  Fun Things to Try

### **Add Objects to Gazebo:**
```bash
# Add trees, buildings, obstacles
docker exec -it gazebo-px4 bash
cd /usr/share/gazebo-11/models/
gazebo --verbose /path/to/your_world.world
```

### **Test YOLO with Custom Images:**
```bash
# Create test images with objects
# Convert to base64 and send to detection service
curl -X POST http://localhost:8002/detect \
  -H "Content-Type: application/json" \
  -d @test_image.json
```

### **Monitor RL Training:**
```bash
# Watch RL agent learn
docker-compose logs -f rl-navigation

# Check reward progress
docker exec rl-navigation tail -f training.log
```

##  You're Ready!

When everything is working:
```bash
# Your services are running
curl http://localhost:8002/health  ✓
curl http://localhost:8003/health  ✓

# Gazebo is open with 3D world
# YOLO is detecting objects
# RL agent is making decisions
# Drone can see, think, and navigate! 
```

**Need help? Check logs: `docker-compose logs -f`**
