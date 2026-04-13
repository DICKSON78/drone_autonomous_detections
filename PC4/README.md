# PC4: Feedback Service

## Your Role
You are the Feedback Service Engineer! You are the voice of the drone system.

### What You Do:
- **Text-to-Speech** - Convert system messages to spoken audio
- **Audio Feedback** - Provide real-time voice announcements
- **System Notifications** - Alert users of important events

## Services You'll Run

```
Feedback Service         (Port 8005)
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
PC1 IP [192.168.1.10]: 192.168.1.10
PC2 IP [192.168.1.11]: 192.168.1.11
PC3 IP [192.168.1.12]: 192.168.1.12
PC4 IP (Your IP - press Enter): 
```

### Step 4: Wait for Setup
- **Download time**: 2-3 minutes
- **Build time**: 1-2 minutes
- **Start time**: 30 seconds

**Total time: ~5 minutes first time, 1 minute subsequent**

## Test Your Services

After setup completes, test everything:

```bash
# Test Feedback Service
curl http://localhost:8005/health
# Should return: {"status": "healthy", "service": "feedback-service"}
```

## Test Text-to-Speech

```bash
# Test TTS functionality
curl -X POST http://localhost:8005/speak \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, this is a test", "priority": "normal"}'

# You should hear the message spoken
```

## Monitor Your Services

```bash
# Check service status
docker-compose ps

# View logs (real-time)
docker-compose logs -f

# Check specific service logs
docker-compose logs -f feedback-service
```

## Common Issues & Solutions

### Issue: "No audio output"
```bash
# Check audio device permissions
sudo usermod -aG audio $USER

# Test audio manually
docker exec feedback-service aplay -l

# Restart service
docker-compose restart feedback-service
```

### Issue: "TTS not working"
```bash
# Check service logs
docker-compose logs feedback-service

# Test TTS manually
docker exec feedback-service python -c "
import pyttsx3
engine = pyttsx3.init()
engine.say('Test message')
engine.runAndWait()
"
```

### Issue: "Port conflicts"
```bash
# Check what's using port 8005
sudo netstat -tulpn | grep :8005

# Kill conflicting process
sudo kill -9 [PID]

# Restart service
docker-compose down && docker-compose up -d
```

## Success Indicators

You're successful when:
- [ ] Feedback service is running
- [ ] Health endpoint returns "healthy"
- [ ] TTS speaks test messages
- [ ] Audio device is accessible
- [ ] Team can hear system announcements

## Team Communication

### You Coordinate With:
- **PC1**: Receive command status, provide voice feedback
- **PC2**: Receive detection alerts, announce obstacles
- **PC3**: Receive system metrics, provide status updates

### Your Critical Functions:
- **Audio output** - All system voice feedback goes through you
- **User notifications** - Important system announcements
- **Real-time alerts** - Emergency and status messages

## Next Steps

Once your PC4 is running:
1. **Test TTS quality** - Adjust voice settings
2. **Set up alerts** - Configure notification priorities
3. **Test audio hardware** - Ensure good speaker setup
4. **Monitor performance** - Check audio latency

## You're Ready!

When everything is working:
```bash
# Your service is running
curl http://localhost:8005/health

# TTS is working
curl -X POST http://localhost:8005/speak \
  -H "Content-Type: application/json" \
  -d '{"message": "System ready", "priority": "normal"}'

# System has voice feedback!
```

**Need help? Check logs: `docker-compose logs -f`**
