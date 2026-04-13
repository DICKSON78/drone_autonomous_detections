# PC1: Command & Control

## Your Role
You are the Command & Control Engineer! You lead the drone system.

### What You Do:
- **Parse user commands** - "Go to forest" → GPS coordinates
- **Control drone flight** - Takeoff, landing, navigation
- **Manage communication** - Kafka message broker for all PCs

## Services You'll Run

```
Command Parser Service     (Port 8000)
Flight Control Service     (Port 8001)  
Kafka Message Broker       (Port 9092)
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

### Step 2: Run Setup Script
```bash
# Make script executable
chmod +x setup.sh

# Run setup (does everything automatically)
./setup.sh
```

### Step 3: Enter Team IPs
Script will ask for team member IPs:
```
PC1 IP [192.168.1.10]: [Your IP - press Enter]
PC2 IP [192.168.1.11]: 192.168.1.11
PC3 IP [192.168.1.12]: 192.168.1.12
PC4 IP [192.168.1.13]: 192.168.1.13
```

### Step 4: Wait for Setup
- **Download time**: 5-10 minutes (first time only)
- **Build time**: 3-5 minutes
- **Start time**: 1 minute

**Total time: ~15 minutes first time, 2 minutes subsequent**

## Test Your Services

After setup completes, test everything:

```bash
# Test Command Parser
curl http://localhost:8000/health
# Should return: {"status": "healthy", "service": "command-parser"}

# Test Flight Control
curl http://localhost:8001/health
# Should return: {"status": "healthy", "service": "flight-control"}

# Test Kafka
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --list
# Should show: drone.commands.flight, drone.telemetry.gps, etc.
```

## Send Test Commands

```bash
# Send a test command
curl -X POST http://localhost:8000/parse-command \
  -H "Content-Type: application/json" \
  -d '{"text": "Go to forest area", "user_id": "test_user"}'

# Response should be:
# {
#   "status": "success",
#   "parsed_command": {
#     "command": "Go to forest area",
#     "target_gps": {"lat": -1.2921, "lon": 36.8219},
#     "altitude": 50.0,
#     "action": "navigate"
#   },
#   "message": "Command sent to drone"
# }
```

## Monitor Your Services

```bash
# Check all services status
docker-compose ps

# View logs (real-time)
docker-compose logs -f

# Check specific service logs
docker-compose logs -f command-parser
docker-compose logs -f flight-control
docker-compose logs -f kafka
```

## Common Issues & Solutions

### Issue: "Port already in use"
```bash
# Check what's using the port
sudo netstat -tulpn | grep :8000

# Kill the process
sudo kill -9 [PID]

# Restart services
docker-compose down && docker-compose up -d
```

### Issue: "Connection refused"
```bash
# Check if service is running
docker-compose ps

# Restart specific service
docker-compose restart command-parser

# Check logs for errors
docker-compose logs command-parser
```

### Issue: "Kafka not responding"
```bash
# Check Kafka status
docker-compose logs kafka

# Restart Kafka
docker-compose restart kafka

# Wait 30 seconds then test again
```

### Issue: "Docker build failed"
```bash
# Clean and rebuild
docker-compose down
docker system prune -f
docker-compose up -d --build
```

## What You Should See

### Successful Setup:
```bash
# docker-compose ps output should show:
NAME                COMMAND                  SERVICE             STATUS              PORTS
command-parser       "python main.py"         command-parser       running             0.0.0.0:8000->8000/tcp
flight-control       "python flight_cont..."   flight-control       running             0.0.0.0:8001->8001/tcp
kafka                "/etc/confluent/dock..."   kafka                running             0.0.0.0:9092->9092/tcp
zookeeper            "/etc/confluent/dock..."   zookeeper            running
```

### Health Check Results:
```bash
# All should return "healthy"
curl http://localhost:8000/health
curl http://localhost:8001/health
```

## Daily Workflow

### Every Morning:
```bash
cd /path/to/PC1
docker-compose ps  # Check services
```

### When Developing:
```bash
# View logs while coding
docker-compose logs -f command-parser

# Restart after changes
docker-compose restart command-parser
```

### When Testing:
```bash
# Send test commands
curl -X POST http://localhost:8000/parse-command \
  -H "Content-Type: application/json" \
  -d '{"text": "Test command", "user_id": "dev"}'
```

## Success Indicators

You're successful when:
- [ ] All 3 services are running
- [ ] Health endpoints return "healthy"
- [ ] Kafka topics are created
- [ ] Commands are processed without errors
- [ ] Other PCs can connect to your Kafka

## Team Communication

### You Coordinate With:
- **PC2**: Send flight commands, receive navigation updates
- **PC3**: Provide command logs, receive system status
- **PC4**: Handle user commands, provide feedback

### Your Critical Functions:
- **System startup** - You must be running for others to work
- **Command processing** - All drone commands go through you
- **Message routing** - Kafka handles all PC communication

## Next Steps

Once your PC1 is running:
1. **Test with team members**
2. **Monitor Grafana dashboard** (PC3:3000)
3. **Check web dashboard** (PC4)
4. **Start developing new features**

## You're Ready!

When everything is working:
```bash
# Your services are running
curl http://localhost:8000/health
curl http://localhost:8001/health

# Team can connect
# Other PCs can send commands through you
# System is ready for autonomous flight!
```

**Need help? Check logs: `docker-compose logs -f`**
