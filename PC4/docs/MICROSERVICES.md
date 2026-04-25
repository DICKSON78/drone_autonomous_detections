# PC4 Microservices - Complete System Overview

## System Architecture

PC4 (Web Interface & Feedback) is a **3-tier microservice system** providing the user-facing layer for the drone autonomous detection platform.

```
┌─────────────────────────────────────────────────────────────┐
│                   Web Dashboard (Port 80)                   │
│              React SPA + Nginx + TLS Ready                  │
│  Dashboard | Detections | Navigation | Feedback | Settings │
└────────────────────┬──────────────────────────────────────┘
                     │ HTTP/WebSocket
         ┌───────────┴───────────┐
         │                       │
┌────────▼──────────┐  ┌────────▼──────────────┐
│ Feedback Service  │  │  WebSocket Server     │
│ (Port 8005)       │  │  (Port 8006)          │
│ FastAPI + pyttsx3 │  │  Express.js + WS      │
│                   │  │                       │
│ • TTS Voice       │  │ • Kafka Consumer      │
│ • Priority Queue  │  │ • Client Manager      │
│ • Audio Manager   │  │ • Message Relay       │
│ • Kafka Producer  │  │ • Broadcast System    │
└─────────┬─────────┘  └────────┬──────────────┘
          │                     │
          └──────────┬──────────┘
                     │
          ┌──────────▼───────────┐
          │   Kafka Broker       │
          │   (PC1 - Port 9092)  │
          │                      │
          │ Topics:              │
          │ • drone.telemetry    │
          │ • drone.detections   │
          │ • drone.navigation   │
          │ • drone.commands     │
          │ • drone.feedback     │
          └──────────────────────┘
```

---

## Service 1: Feedback Service (Port 8005)

### Purpose
Convert system events into human-understandable voice announcements with priority-based handling.

### Technology Stack
- **Language**: Python 3.10+
- **Framework**: FastAPI (async)
- **TTS Engine**: pyttsx3
- **Message Queue**: Kafka (consumer)
- **Dependencies**: 
  - `uvicorn` - ASGI server
  - `kafka-python` - Message broker
  - `pydantic` - Data validation

### What It Does

#### Input Sources
1. **API Calls** (HTTP POST)
   - `/speak` - Direct message to speech
   - `/announce` - Named event announcements

2. **Kafka Topics** (Event-driven)
   - `drone.commands.feedback` - Direct commands
   - `drone.detections.objects` - Object detection events
   - `drone.navigation.result` - Navigation events

#### Processing
- **Priority-based filtering**: Low, Normal, High, Emergency
- **Confidence thresholding**: Only announce if confidence > 65%
- **Cooldown mechanism**: Prevent duplicate announcements
- **Message prefixing**: Add priority indicators ("Warning", "Emergency alert!")

#### Output
- **Audio**: Spoken messages through system audio device
- **Logging**: Event logs for debugging
- **Kafka**: Publish to `drone.feedback.spoken` for audit trail

### API Endpoints

```
GET /health
Response: { "status": "healthy", "service": "feedback-service", ... }

POST /speak
Body: { "message": "string", "priority": "low|normal|high|emergency", "async_mode": boolean }
Response: { "status": "ok", "message": "...", "priority": "...", "spoken": boolean, "timestamp": number }

POST /announce
Body: { "event": "string", "details": "string" }
Response: { "status": "announced", "event": "...", "message": "..." }

GET /voices
Response: { "voices": [{ "index": 0, "id": "...", "name": "..." }] }

GET /audio-devices
Response: { "devices": ["card 0", "card 1", ...] }

GET /stats
Response: { "service": "feedback-service", "queue_stats": {...}, "audio_ok": true, ... }
```

### Configuration

Environment Variables:
```
KAFKA_BOOTSTRAP_SERVERS=kafka:9092        # Kafka broker
TTS_RATE=150                               # Speech rate (WPM)
TTS_VOLUME=1.0                             # Volume (0.0 - 1.0)
TTS_VOICE_INDEX=0                          # Voice to use
PORT=8005                                  # Service port
```

### Docker Setup
```dockerfile
# Base: Python 3.10-slim
# Audio Support: espeak-ng, alsa-utils, curl
# Devices: /dev/snd:/dev/snd (sound card passthrough)
# Health Check: Every 30s via /health endpoint
```

---

## Service 2: WebSocket Server (Port 8006)

### Purpose
Real-time streaming of drone system events from Kafka to connected web clients.

### Technology Stack
- **Language**: Node.js 20+
- **Framework**: Express.js + ws (WebSocket library)
- **Message Broker**: KafkaJS
- **Dependencies**:
  - `express` - HTTP server
  - `ws` - WebSocket implementation
  - `kafkajs` - Kafka client
  - `cors` - Cross-origin support
  - `uuid` - Client identification

### What It Does

#### Client Management
- **Connection tracking**: UUID-based client identification
- **Per-client filtering**: Subscribe to specific message types
- **Auto-reconnection**: Handles client disconnects gracefully
- **Message buffering**: Prevents message loss during reconnects

#### Message Relay
- **Kafka Consumer**: Subscribes to 5 topics
- **Message Formatting**: Standardizes format for web clients
- **Broadcasting**: Sends to all connected clients or filtered subset
- **Type Mapping**: Kafka topics → WebSocket message types

#### Topics Subscribed
| Kafka Topic | WS Message Type | Content |
|---|---|---|
| `drone.telemetry` | `telemetry` | GPS, battery, IMU data |
| `drone.detections.objects` | `detection` | Detected objects with confidence |
| `drone.navigation.result` | `navigation` | Navigation decisions, waypoints |
| `drone.commands.feedback` | `command` | System command responses |
| `drone.feedback.spoken` | `feedback` | TTS messages sent |

### WebSocket Protocol

#### Client → Server Messages

```json
{
  "type": "subscribe",
  "data": { "types": ["telemetry", "detection", "navigation"] }
}

{
  "type": "ping",
  "timestamp": 1234567890
}

{
  "type": "request_status"
}
```

#### Server → Client Messages

```json
{
  "type": "connected",
  "clientId": "abc12345",
  "timestamp": 1234567890
}

{
  "type": "telemetry|detection|navigation|feedback|command",
  "topic": "drone.telemetry",
  "data": { "..." },
  "timestamp": 1234567890
}

{
  "type": "pong",
  "timestamp": 1234567890
}
```

### REST API Endpoints

```
GET /health
Response: { "status": "healthy", "service": "websocket-server", "clients": 5, "timestamp": 1234567890 }

GET /clients
Response: { "clients": [{ "id": "abc12345", "ip": "192.168.1.100", "connectedAt": 1234567890, "filter": ["telemetry", "detection"] }] }

POST /broadcast
Body: { "type": "alert", "data": {...} }
Response: { "status": "broadcast", "recipients": 5 }
```

### Configuration

Environment Variables:
```
WS_PORT=8006                               # WebSocket server port
KAFKA_BROKER=kafka:9092                    # Kafka broker
NODE_ENV=production                        # Environment
```

### Docker Setup
```dockerfile
# Base: Node.js 20-slim
# Health Check: Every 30s via /health endpoint
# Logging: JSON file driver, 10MB max per file
```

---

## Service 3: Web Dashboard (Port 80)

### Purpose
Interactive real-time visualization of drone system state and user control interface.

### Technology Stack
- **Frontend**: React 18.2 with hooks
- **Build Tool**: Webpack 5
- **Transpiler**: Babel (ES2020)
- **Server**: Nginx (Alpine Linux)
- **Communication**: Fetch API + WebSocket
- **Styling**: CSS Grid, Flexbox, Responsive Design

### What It Does

#### Pages
1. **Dashboard** - System overview, status cards, recent telemetry
2. **Detections** - Detailed object detection list with filtering and confidence bars
3. **Navigation** - Drone navigation decisions, waypoints, confidence levels
4. **Feedback** - TTS message history with priority indicators

#### Components
- **StatusCard** - Key metrics with icons and status indicators
- **TelemetryPanel** - GPS, battery, IMU visualization
- **AlertFeed** - Scrolling alert/event feed
- **DetectionList** - Grid of detected objects

#### Features
- Real-time WebSocket connection with auto-reconnection
- Responsive design (mobile, tablet, desktop)
- Dark mode support
- Connection status indicator
- Message counter
- Smooth animations and transitions

### Custom Hooks
- **useWebSocket** - WebSocket management with reconnection logic, message buffering

### Services
- **API layer** - HTTP calls to Feedback Service and WebSocket Server
- **Helper utilities** - Formatting, color mapping, calculations

### Pages & Routes

```
/                    → Dashboard (default)
                     • Status overview
                     • Telemetry gauges
                     • Recent detections & feedback

/detections          → Object Detections
                     • Filterable detection list
                     • Confidence bars
                     • Bounding box display
                     • Class-based filtering

/navigation          → Navigation & Planning
                     • Next action display
                     • Confidence visualization
                     • Waypoint display
                     • Path information

/feedback            → Voice Feedback History
                     • Message chronology
                     • Priority filtering
                     • Trigger information
                     • Statistics panel
```

### Nginx Configuration
```
• Port 80 HTTP serving
• SPA routing (fallback to index.html)
• API proxying to Feedback Service (/api/feedback)
• WebSocket proxying to WS Server (/api/websocket)
• Gzip compression for assets
• Cache control for static files
• Security headers (X-Frame-Options, CSP)
• Health check endpoint
```

### Build Configuration

```bash
# Development (with hot reload)
npm run dev           # Webpack dev server on :3000

# Production build
npm run build         # Creates optimized dist/ folder

# Testing
npm test              # Jest test runner
```

### Docker Setup
```dockerfile
# Stage 1: Build React app
FROM node:20-slim
# ... build to dist/

# Stage 2: Serve with nginx
FROM nginx:alpine
# ... copy dist/ to /usr/share/nginx/html
# Health check: Every 30s via /health endpoint
```

---

## Data Flow

### Example: Object Detection Flow

```
1. PC2 (Detection Service) detects objects
   ↓
2. Publishes to Kafka topic: drone.detections.objects
   {
     "detections": [
       {"class_name": "person", "confidence": 0.95, "bbox": [100, 200, 300, 400]},
       {"class_name": "car", "confidence": 0.87, "bbox": [50, 100, 250, 350]}
     ]
   }
   ↓
3. Feedback Service consumes message
   → Filters by confidence (> 0.65)
   → Checks cooldown (no duplicates within 5 sec)
   → Builds message: "Warning. 1 person detected"
   → Speaks via pyttsx3
   → Publishes to drone.feedback.spoken
   ↓
4. WebSocket Server receives both:
   - Original detection message
   - TTS confirmation message
   ↓
5. Formats and broadcasts to all connected browsers:
   {
     "type": "detection",
     "data": {...},
     "timestamp": 1234567890
   }
   ↓
6. Web Dashboard receives via WebSocket
   → Updates Detections page
   → Shows alert in Dashboard
   → Adds to Feedback history
   ↓
7. User sees real-time update!
```

---

## Deployment

### Docker Compose
```yaml
# All 3 services defined in docker-compose.yml
# Automatic startup order (web-dashboard depends on both services)
# Health checks ensure readiness
# Logging configured (10MB files, 3 backups)
# Network: fyp-network (shared with other PCs)
```

### Quick Start
```bash
# Full setup
cd PC4
./setup.sh setup

# Or manual:
docker network create fyp-network
docker compose up -d

# Verify
./setup.sh test
```

### Services Status
```bash
docker compose ps          # Show status
docker compose logs -f     # Stream logs
./setup.sh status         # Custom status check
```

---

## Monitoring & Troubleshooting

### Health Checks
```bash
# Feedback Service
curl http://localhost:8005/health

# WebSocket Server
curl http://localhost:8006/health

# Web Dashboard
curl http://localhost:80

# Full test
./setup.sh test
```

### Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f feedback-service
docker compose logs -f websocket-server
docker compose logs -f web-dashboard

# Follow with grep
docker compose logs -f | grep ERROR
```

### Common Issues

| Issue | Solution |
|---|---|
| No audio output | `sudo usermod -aG audio $USER`, restart |
| WebSocket disconnected | Check `curl http://localhost:8006/health` |
| Dashboard shows no data | Check if Kafka topics exist: `./setup.sh test` |
| Port already in use | `sudo netstat -tulpn \| grep -E ':80\|:8005\|:8006'` |
| Network not found | `docker network create fyp-network` |

---

## Development

### Feedback Service (Python)
```bash
cd PC4/src/feedback-service
pip install -r requirements.txt
python feedback.py
```

### WebSocket Server (Node.js)
```bash
cd PC4/src/websocket-server
npm install
node server.js        # or: npm run dev (with nodemon)
```

### Web Dashboard (React)
```bash
cd PC4/src/web-dashboard
npm install
npm run dev           # http://localhost:3000
```

---

## Summary

PC4 is a **production-ready 3-tier microservice architecture** providing:

✅ **Real-time voice feedback** (Feedback Service)
✅ **Event streaming** (WebSocket Server)
✅ **Interactive dashboard** (Web Dashboard)
✅ **Automatic deployment** (Docker Compose)
✅ **Health monitoring** (Built-in checks)
✅ **Responsive UI** (Mobile-first design)
✅ **Scalable architecture** (Independent services)

All services integrate with the shared Kafka broker and fyp-network for seamless system-wide communication.
