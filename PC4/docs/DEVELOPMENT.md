# PC4 Development Guide

## 📋 Quick Start

```bash
# Setup (runs once)
./setup.sh

# Start services
docker compose up -d

# Check status
./setup.sh status

# Test services
./setup.sh test
```

## 🏗️ Architecture

PC4 consists of three microservices:

1. **Feedback Service** (Port 8005) - Python FastAPI
   - Text-to-speech voice feedback
   - Priority-based message queuing
   - Audio device management
   - Kafka consumer for drone events

2. **WebSocket Server** (Port 8006) - Node.js/Express
   - Real-time event relay from Kafka
   - Client connection management
   - Message filtering and formatting
   - Health monitoring

3. **Web Dashboard** (Port 80) - React + Nginx
   - Live telemetry visualization
   - Real-time detection feeds
   - Navigation monitoring
   - Feedback history

## 📁 Project Structure

```
PC4/
├── src/
│   ├── feedback-service/        # Python FastAPI TTS engine
│   │   ├── feedback.py          # Main service
│   │   ├── tts_engine.py        # pyttsx3 wrapper
│   │   ├── audio_manager.py     # Audio device handling
│   │   ├── message_queue.py     # Message processing
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── tests/
│   │
│   ├── websocket-server/        # Node.js WebSocket relay
│   │   ├── server.js            # Express + WS setup
│   │   ├── kafka_listener.js    # Kafka integration
│   │   ├── message_handler.js   # Message processing
│   │   ├── client_manager.js    # Connection management
│   │   ├── Dockerfile
│   │   ├── package.json
│   │   └── tests/
│   │
│   └── web-dashboard/           # React SPA
│       ├── src/
│       │   ├── App.jsx          # Main component
│       │   ├── index.jsx        # Entry point
│       │   ├── components/      # Reusable components
│       │   ├── pages/           # Page components
│       │   ├── hooks/           # Custom hooks (useWebSocket)
│       │   ├── services/        # API service layer
│       │   ├── utils/           # Utility functions
│       │   └── styles/          # CSS files
│       ├── public/
│       │   └── index.html
│       ├── Dockerfile
│       ├── nginx.conf
│       ├── webpack.config.js
│       ├── package.json
│       └── .babelrc
│
├── scripts/
│   ├── build_frontend.sh        # Build React app
│   ├── deploy.sh                # Zero-downtime deploy
│   ├── run_tests.sh             # Run all tests
│   └── setup_nginx.sh           # Install nginx on host
│
├── config/
│   ├── environment.env          # Team IPs and settings
│   ├── kafka_topics.yaml        # Kafka topic config
│   ├── tts_config.yaml          # TTS voice settings
│   ├── websocket_config.yaml    # WebSocket settings
│   └── nginx_config.conf        # Alternative nginx config
│
├── tests/                       # Integration tests
├── docker-compose.yml
├── setup.sh                     # Main setup script
└── README.md
```

## 🛠️ Development Workflow

### Feedback Service (Python)

```bash
# Install dependencies
cd src/feedback-service
pip install -r requirements.txt

# Run locally
python feedback.py

# Test
python -m pytest tests/

# Build Docker image
docker build -t pc4-feedback .
```

**Key Features:**
- FastAPI with async support
- pyttsx3 for text-to-speech
- Kafka producer/consumer integration
- Thread-safe audio engine
- Audio device detection

### WebSocket Server (Node.js)

```bash
# Install dependencies
cd src/websocket-server
npm install

# Run locally
node server.js

# Watch mode (with nodemon)
npm run dev

# Test
npm test

# Build Docker image
docker build -t pc4-websocket .
```

**Key Features:**
- Real-time WebSocket connections
- Kafka topic subscriptions
- Client filtering and broadcasting
- Connection persistence
- Message buffering

### Web Dashboard (React)

```bash
# Install dependencies
cd src/web-dashboard
npm install

# Development server (with hot reload)
npm run dev
# Visit http://localhost:3000

# Production build
npm run build

# Test
npm test

# Build Docker image
docker build -t pc4-dashboard .
```

**Key Features:**
- React 18 with hooks
- WebSocket auto-reconnection
- Real-time message streaming
- Responsive UI with CSS Grid
- Four main pages: Dashboard, Detections, Navigation, Feedback

## 📡 API Reference

### Feedback Service Endpoints

```bash
# Health check
GET /health
# Returns: { status, service, audio_devices, timestamp }

# Speak message
POST /speak
# Body: { message, priority?, async_mode? }
# Returns: { status, message, priority, spoken, timestamp }

# Announce event
POST /announce
# Body: { event, details? }
# Returns: { status, event, message }

# List voices
GET /voices
# Returns: { voices: [{index, id, name}] }

# Get statistics
GET /stats
# Returns: { service, queue_stats, audio_ok, timestamp }

# List audio devices
GET /audio-devices
# Returns: { devices: [string] }
```

### WebSocket Server Endpoints

```bash
# Health check
GET /health
# Returns: { status, service, clients, timestamp }

# Get connected clients
GET /clients
# Returns: { clients: [{id, ip, connectedAt, filter}] }

# Broadcast message
POST /broadcast
# Body: { type, data }
# Returns: { status, recipients }

# WebSocket connection
WS ws://localhost:8006
# Messages: { type, data, timestamp }
```

### Web Dashboard

```
http://localhost:80

Pages:
- /           Dashboard (home)
- /detections Object detections
- /navigation Navigation & planning
- /feedback   TTS feedback history
```

## 🔌 WebSocket Message Types

**Client → Server:**
```json
{
  "type": "subscribe",
  "data": { "types": ["telemetry", "detection", "navigation", "feedback"] }
}
```

**Server → Client:**
```json
{
  "type": "telemetry|detection|navigation|feedback",
  "topic": "drone.telemetry",
  "data": { "..." },
  "timestamp": 1234567890
}
```

## 🔒 Environment Variables

### Feedback Service
```
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
TTS_RATE=150
TTS_VOLUME=1.0
TTS_VOICE_INDEX=0
PORT=8005
```

### WebSocket Server
```
WS_PORT=8006
KAFKA_BROKER=kafka:9092
NODE_ENV=production
```

### Web Dashboard
```
REACT_APP_API_URL=http://localhost
REACT_APP_WS_URL=ws://localhost:8006
```

## 🧪 Testing

### Run all tests
```bash
bash scripts/run_tests.sh
```

### Test Feedback Service
```bash
cd src/feedback-service
python -m pytest tests/ -v
```

### Test WebSocket Server
```bash
cd src/websocket-server
npm test
```

### Manual API testing
```bash
# Test feedback service
curl http://localhost:8005/health
curl -X POST http://localhost:8005/speak \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "priority": "normal"}'

# Test websocket server
curl http://localhost:8006/health

# Test dashboard
curl http://localhost:80
```

## 📊 Monitoring

### Check service logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f feedback-service
docker compose logs -f websocket-server
docker compose logs -f web-dashboard
```

### Service status
```bash
docker compose ps
```

### Performance monitoring
```bash
# CPU and memory
docker stats

# Network traffic
docker network inspect fyp-network
```

## 🚀 Deployment

### Docker Compose (recommended)
```bash
bash scripts/deploy.sh
```

### Manual deployment
```bash
# Build images
docker compose build

# Start services
docker compose up -d

# Scale specific service
docker compose up -d --scale websocket-server=2
```

### Nginx on host
```bash
sudo bash scripts/setup_nginx.sh
```

## 🐛 Troubleshooting

### "No audio output"
```bash
# Check audio devices
docker exec feedback-service aplay -l

# Verify audio in container
docker exec feedback-service python -c "
import pyttsx3
engine = pyttsx3.init()
engine.say('Test')
engine.runAndWait()
"
```

### "WebSocket disconnected"
```bash
# Check connectivity
curl http://localhost:8006/health

# Check Kafka connection
docker compose logs websocket-server | grep Kafka
```

### "Dashboard shows no data"
```bash
# Check if Kafka topics exist
docker exec -it $(docker compose ps -q kafka) \
  kafka-topics.sh --list --bootstrap-server localhost:9092

# Check WebSocket messages
curl http://localhost:8006/clients
```

## 📝 Coding Standards

### Python
- `snake_case` for functions and variables
- `PascalCase` for classes
- Type hints on all functions
- Docstrings for public methods

### JavaScript/React
- `PascalCase` for components
- `camelCase` for functions and variables
- PropTypes validation
- Functional components with hooks only

### CSS
- Mobile-first responsive design
- BEM naming convention
- CSS custom properties for theming
- Minimize nesting

## 🔄 Git Workflow

```bash
# Create feature branch
git checkout -b feature/new-feature

# Make changes
git add .
git commit -m "feat: describe changes"

# Push to remote
git push origin feature/new-feature

# Create pull request
```

## 📚 Additional Resources

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Express Docs](https://expressjs.com/)
- [React Docs](https://react.dev/)
- [Webpack Docs](https://webpack.js.org/)
- [KafkaJS Docs](https://kafka.js.org/)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 License

This project is part of the FYP drone autonomous detection system.
