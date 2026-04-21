# PC4 Project Structure

## Directory Overview
This is the standardized structure for PC4 (Web Interface & Feedback) development.

## Folders and Their Purpose

```
PC4/
├── 📁 microservices/              # Dockerized microservices (feedback only for now)
│   └── feedback_service/         # ← built by docker-compose feedback-service
│       ├── feedback.py           # Main FastAPI TTS service
│       ├── tts_engine.py         # pyttsx3 TTS engine wrapper
│       ├── audio_manager.py      # Audio device detection & management
│       ├── message_queue.py      # Priority rules, cooldown, Kafka handlers
│       ├── requirements.txt      # Python dependencies
│       ├── Dockerfile            # python:3.10-slim + espeak-ng + alsa
│       └── tests/
│           └── test_tts.py       # Unit tests (11 tests, no services needed)
│
├── 📁 src/                        # Full-stack source code
│   ├── web-dashboard/             # React frontend application (port 80)
│   │   ├── public/
│   │   │   └── index.html        # HTML entry point
│   │   ├── src/
│   │   │   ├── App.jsx           # Main React component + routing
│   │   │   ├── index.jsx         # React entry point
│   │   │   ├── components/       # Reusable UI components
│   │   │   │   ├── StatusCard.jsx
│   │   │   │   ├── TelemetryPanel.jsx
│   │   │   │   ├── AlertFeed.jsx
│   │   │   │   └── DetectionList.jsx
│   │   │   ├── pages/            # Page components
│   │   │   │   ├── Dashboard.jsx
│   │   │   │   ├── Detections.jsx
│   │   │   │   ├── Navigation.jsx
│   │   │   │   └── Feedback.jsx
│   │   │   ├── hooks/
│   │   │   │   └── useWebSocket.js   # Auto-reconnect WS hook
│   │   │   ├── services/
│   │   │   │   └── api.js            # REST calls to feedback + WS services
│   │   │   ├── utils/            # Utility functions
│   │   │   └── styles/
│   │   │       ├── global.css
│   │   │       └── app.css
│   │   ├── package.json          # Node.js dependencies
│   │   ├── webpack.config.js     # Build configuration
│   │   ├── nginx.conf            # Nginx SPA config
│   │   └── Dockerfile            # Multi-stage: build → nginx
│   │
│   ├── websocket-server/          # Node.js WebSocket relay (port 8006)
│   │   ├── server.js             # Express + WS server, REST health endpoints
│   │   ├── kafka_listener.js     # Subscribes to Kafka, broadcasts to clients
│   │   ├── message_handler.js    # Message formatting, client command routing
│   │   ├── client_manager.js     # Connection registry, per-client filters
│   │   ├── package.json          # Node.js dependencies
│   │   ├── Dockerfile            # node:20-slim
│   │   └── tests/
│   │       └── test_websocket.py # Integration tests (server must be running)
│   │
│   └── feedback-service/          # Symlink/copy of microservices/feedback_service
│       └── (same files as above)  # Used by src/ imports and docs references
│
├── 📁 config/                     # Configuration files
│   ├── nginx_config.conf         # Nginx host config (alternative to Docker)
│   ├── websocket_config.yaml     # WebSocket server settings
│   ├── tts_config.yaml           # TTS voice, rate, volume, alert thresholds
│   ├── kafka_topics.yaml         # Kafka topic mappings for all PC4 services
│   └── environment.env           # Team IPs and env vars (auto-written by setup.sh)
│
├── 📁 assets/                     # Static assets
│   ├── images/
│   ├── audio/
│   ├── fonts/
│   └── videos/
│
├── 📁 docs/                       # Documentation
│   ├── FRONTEND_GUIDE.md         # React development guide
│   ├── WEBSOCKET_API.md          # WebSocket protocol reference
│   ├── TTS_SETUP.md              # TTS voice setup and troubleshooting
│   ├── API_DOCS.md               # Full API reference
│   └── TROUBLESHOOTING.md        # Common issues and fixes
│
├── 📁 logs/                       # Log files (auto-created by setup.sh)
│   ├── web-dashboard.log
│   ├── websocket.log
│   ├── feedback.log
│   └── nginx.log
│
├── 📁 tests/                      # Integration & end-to-end tests
│   ├── test_frontend.py          # Dashboard smoke tests (nginx serving)
│   ├── test_websocket.py         # WebSocket protocol tests
│   ├── test_tts.py               # TTS service integration tests
│   └── test_integration.py       # Full end-to-end tests
│
├── 📁 scripts/                    # Utility scripts
│   ├── build_frontend.sh         # Build React app for production
│   ├── setup_nginx.sh            # Install and configure nginx on host
│   ├── run_tests.sh              # Run all test suites
│   └── deploy.sh                 # Zero-downtime redeploy
│
├── 📄 docker-compose.yml          # Orchestrates feedback + websocket + dashboard
├── 📄 Dockerfile                  # Root Dockerfile (feedback-service)
├── 📄 requirements.txt            # Python dependencies (feedback-service)
├── 📄 README.md                   # Main documentation
├── 📄 setup.sh                    # Automated setup (./setup.sh)
└── 📄 PROJECT_STRUCTURE.md        # This file
```

---

## Service → Port Map

| Service | Port | Tech | Build context |
|---|---|---|---|
| Feedback Service | 8005 | Python FastAPI | `./microservices/feedback_service` |
| WebSocket Server | 8006 | Node.js | `./src/websocket-server` |
| Web Dashboard | 80 | React + Nginx | `./src/web-dashboard` |

## Shared Network

All services connect to `fyp-network` (external Docker network shared with PC1/PC2/PC3).

```bash
# Create if missing:
docker network create fyp-network
# or:
./setup.sh network
```

---

## File Naming Conventions

| Type | Convention | Example |
|---|---|---|
| React components | `PascalCase.jsx` | `DroneMap.jsx` |
| Python modules | `snake_case.py` | `audio_manager.py` |
| JavaScript modules | `camelCase.js` | `kafkaListener.js` |
| Config files | `descriptive_name.yaml` | `tts_config.yaml` |
| Test files | `test_*.py` | `test_tts.py` |
| Docs | `UPPER_CASE.md` | `API_DOCS.md` |
| Directories (src) | `kebab-case` | `web-dashboard` |

---

## Development Workflow

### Feedback Service (Python)
```bash
cd microservices/feedback_service
pip install -r requirements.txt
python feedback.py

# Test
curl -X POST http://localhost:8005/speak \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello drone", "priority": "normal"}'
```

### WebSocket Server (Node.js)
```bash
cd src/websocket-server
npm install
node server.js

# Test
curl http://localhost:8006/health
python src/websocket-server/tests/test_websocket.py
```

### Web Dashboard (React)
```bash
cd src/web-dashboard
npm install
npm run dev     # http://localhost:3000 with hot reload
npm run build   # Production build → dist/
```

### Run All Tests
```bash
bash scripts/run_tests.sh
```

---

## Coding Standards

### Python
- `snake_case` for variables and functions, `PascalCase` for classes
- Type hints on all FastAPI endpoints
- Handle audio device errors gracefully

### JavaScript / React
- `PascalCase` for components, `camelCase` for functions and variables
- Functional components with hooks only
- Include PropTypes for component validation

### WebSocket Messages
- Always JSON format with a `type` and `timestamp` field
- Handle connection drops with auto-reconnect (3s interval)

---

## Getting Help

| Issue | Where to look |
|---|---|
| TTS not speaking | `docker compose logs feedback-service` |
| Dashboard disconnected | `docker compose logs websocket-server` |
| Dashboard blank | `docker compose logs web-dashboard` |
| Kafka not connecting | Check `config/environment.env` → `KAFKA_BOOTSTRAP_SERVERS` |
| Audio not playing | `docker exec feedback-service aplay -l` |
| Network errors | `docker network ls` → ensure `fyp-network` exists |

Full guide: `docs/TROUBLESHOOTING.md`

---

**This structure ensures organized full-stack development and effective user experience.**