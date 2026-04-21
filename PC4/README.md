# PC4: Web Interface & Feedback

## Your Role
You are the Feedback Service Engineer! You are the **voice and face** of the drone system.

### What You Do:
- **Text-to-Speech** — Convert system messages to spoken audio
- **Audio Feedback** — Provide real-time voice announcements
- **System Notifications** — Alert users of important events
- **Web Dashboard** — Live React UI showing drone telemetry and detections
- **WebSocket Relay** — Stream Kafka events to the browser in real time

## Services You'll Run

```
Feedback Service    (Port 8005)   ← TTS voice feedback
WebSocket Server    (Port 8006)   ← Kafka → browser relay
Web Dashboard       (Port 80)     ← React live UI
```

## Quick Setup (5 Minutes)

### Step 1: Install Docker (if not installed)
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker

sudo apt install docker-compose-plugin -y
```

### Step 2: Run Setup Script
```bash
chmod +x setup.sh
./setup.sh
```

### Step 3: Enter Team IPs
```
PC1 IP [192.168.1.10]: 192.168.1.10
PC2 IP [192.168.1.11]: 192.168.1.11
PC3 IP [192.168.1.12]: 192.168.1.12
PC4 IP (Your IP) [192.168.1.13]:
```

### Step 4: Wait for Setup
- **Download time**: 2–3 minutes
- **Build time**: 3–5 minutes
- **Start time**: 30 seconds

**Total: ~5 minutes first run, ~1 minute after**

---

## Test Your Services

```bash
# Feedback Service health
curl http://localhost:8005/health
# {"status": "healthy", "service": "feedback-service"}

# WebSocket Server health
curl http://localhost:8006/health
# {"status": "healthy", "service": "websocket-server"}

# Web Dashboard
curl http://localhost:80
# Returns HTML
```

## Test Text-to-Speech

```bash
curl -X POST http://localhost:8005/speak \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, this is a test", "priority": "normal"}'
# Listen for spoken message
```

## Priority Levels

| Priority | Spoken prefix | Use case |
|---|---|---|
| `low` | *(none)* | Info updates |
| `normal` | *(none)* | Standard messages |
| `high` | *"Warning."* | Obstacles, alerts |
| `emergency` | *"Emergency alert!"* | Critical failures |

```bash
# Emergency example
curl -X POST http://localhost:8005/speak \
  -H "Content-Type: application/json" \
  -d '{"message": "obstacle ahead", "priority": "high"}'
# Speaks: "Warning. obstacle ahead"
```

---

## Monitor Your Services

```bash
# Check all service status
docker compose ps

# Stream all logs
docker compose logs -f

# Specific service logs
docker compose logs -f feedback-service
docker compose logs -f websocket-server
docker compose logs -f web-dashboard
```

## Setup Script Subcommands

```bash
./setup.sh setup      # Full setup (default)
./setup.sh test       # Test all health endpoints
./setup.sh tts        # Test text-to-speech
./setup.sh logs       # Stream all logs
./setup.sh dashboard  # Open browser dashboard
./setup.sh stop       # Stop all services
./setup.sh restart    # Restart all services
./setup.sh status     # Show service status
./setup.sh network    # Create fyp-network if missing
```

---

## Common Issues & Solutions

### Issue: "No audio output"
```bash
sudo usermod -aG audio $USER
docker exec feedback-service aplay -l
docker compose restart feedback-service
```

### Issue: "TTS not working"
```bash
docker compose logs feedback-service

docker exec feedback-service python -c "
import pyttsx3
engine = pyttsx3.init()
engine.say('Test message')
engine.runAndWait()
"
```

### Issue: "fyp-network not found"
```bash
# Create the shared network
./setup.sh network
# or
docker network create fyp-network
```

### Issue: "Port conflicts"
```bash
sudo netstat -tulpn | grep -E ':8005|:8006|:80'
sudo kill -9 [PID]
docker compose down && docker compose up -d
```

### Issue: "WebSocket dashboard shows Disconnected"
```bash
curl http://localhost:8006/health
sudo ufw allow 8006
docker compose logs websocket-server
```

---

## API Reference

### Feedback Service — `http://PC4:8005`

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/speak` | Speak a message |
| POST | `/announce` | Announce a named event |
| GET | `/voices` | List TTS voices |
| GET | `/stats` | Alert statistics |

### WebSocket Server — `ws://PC4:8006`

Connect from any browser:
```js
const ws = new WebSocket('ws://PC4_IP:8006');
ws.onmessage = (e) => console.log(JSON.parse(e.data));
```

Message types received: `telemetry`, `detection`, `navigation`, `feedback`

---

## Team Communication

### You Coordinate With:
- **PC1** — Receive command status → voice feedback
- **PC2** — Receive detection alerts → announce obstacles
- **PC3** — Receive navigation results → announce actions

### Kafka Topics

| Topic | Direction | Source |
|---|---|---|
| `drone.commands.feedback` | consume | PC1 direct commands |
| `drone.detections.objects` | consume | PC2 YOLO results |
| `drone.navigation.result` | consume | PC3 RL actions |
| `drone.feedback.spoken` | produce | Every spoken message |

---

## Success Checklist

- [ ] Feedback service health returns "healthy"
- [ ] TTS speaks test messages
- [ ] Audio device accessible (`aplay -l` in container)
- [ ] WebSocket server health returns "healthy"
- [ ] Web dashboard loads at http://localhost
- [ ] Dashboard shows "Live" connection indicator
- [ ] Team can hear system announcements

**Need help? Check logs: `docker compose logs -f`**
**See also: `docs/TROUBLESHOOTING.md`**