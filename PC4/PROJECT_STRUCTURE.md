# PC4 Project Structure

## Directory Overview
This is the standardized structure for PC4 (Web Interface & Feedback) development.

## Folders and Their Purpose

```
PC4/
├── 📁 src/                    # Source code files
│   ├── web-dashboard/          # React frontend application
│   │   ├── public/           # Static assets and HTML
│   │   ├── src/              # React source code
│   │   │   ├── components/   # Reusable UI components
│   │   │   ├── pages/        # Page components
│   │   │   ├── hooks/        # Custom React hooks
│   │   │   ├── services/     # API service functions
│   │   │   ├── utils/        # Utility functions
│   │   │   └── styles/       # CSS and styling
│   │   ├── package.json      # Node.js dependencies
│   │   └── webpack.config.js # Build configuration
│   │
│   ├── websocket-server/      # WebSocket backend
│   │   ├── server.js         # Main WebSocket server
│   │   ├── kafka_listener.js # Kafka message listener
│   │   ├── message_handler.js # Message processing
│   │   ├── client_manager.js # Client connection management
│   │   └── tests/           # WebSocket tests
│   │
│   └── feedback-service/      # Text-to-speech service
│       ├── feedback.py       # Main FastAPI service
│       ├── tts_engine.py     # Text-to-speech engine
│       ├── audio_manager.py  # Audio device management
│       ├── message_queue.py  # Message queue handling
│       └── tests/           # TTS tests
│
├── 📁 config/                # Configuration files
│   ├── nginx_config.conf   # Nginx web server config
│   ├── websocket_config.yaml # WebSocket settings
│   ├── tts_config.yaml     # Text-to-speech settings
│   ├── kafka_topics.yaml   # Kafka topic mappings
│   └── environment.env    # Environment variables
│
├── 📁 assets/                # Static assets
│   ├── images/            # Images and icons
│   ├── audio/             # Audio files
│   ├── fonts/             # Custom fonts
│   └── videos/            # Video files
│
├── 📁 docs/                 # Documentation
│   ├── FRONTEND_GUIDE.md  # Frontend development guide
│   ├── WEBSOCKET_API.md  # WebSocket API documentation
│   ├── TTS_SETUP.md      # Text-to-speech setup
│   ├── API_DOCS.md       # API documentation
│   └── TROUBLESHOOTING.md # Common issues
│
├── 📁 logs/                 # Log files
│   ├── web-dashboard.log   # Frontend build logs
│   ├── websocket.log      # WebSocket server logs
│   ├── feedback.log       # TTS service logs
│   └── nginx.log         # Nginx access logs
│
├── 📁 tests/                # Integration tests
│   ├── test_frontend.py    # Frontend tests
│   ├── test_websocket.py  # WebSocket tests
│   ├── test_tts.py        # TTS service tests
│   └── test_integration.py # End-to-end tests
│
├── 📁 scripts/              # Utility scripts
│   ├── build_frontend.sh  # Frontend build script
│   ├── setup_nginx.sh     # Nginx setup script
│   ├── run_tests.sh       # Test runner
│   └── deploy.sh         # Deployment script
│
├── 📁 docker-compose.yml    # Docker orchestration
├── 📄 Dockerfile           # Container definition
├── 📄 requirements.txt      # Python dependencies
├── 📄 README.md            # Main documentation
├── 📄 setup.sh             # Automated setup script
└── 📄 PROJECT_STRUCTURE.md  # This file
```

## File Naming Conventions

### Source Code Files:
- **React files**: `PascalCase.jsx` (e.g., `DroneMap.jsx`)
- **Python files**: `snake_case.py` (e.g., `websocket_server.py`)
- **JavaScript files**: `camelCase.js` (e.g., `messageHandler.js`)
- **Configuration**: `descriptive_name.yaml` (e.g., `websocket_config.yaml`)
- **Tests**: `test_*.py` (e.g., `test_frontend.py`)
- **Documentation**: `UPPER_CASE.md` (e.g., `FRONTEND_GUIDE.md`)

### Directory Naming:
- **Source code**: `kebab-case` (e.g., `web-dashboard`)
- **Configuration**: `config`
- **Assets**: `assets`
- **Documentation**: `docs`
- **Tests**: `tests`
- **Scripts**: `scripts`

## Developer Responsibilities

### What You'll Work On:
1. **Web Dashboard** (`src/web-dashboard/`)
   - React frontend application
   - Real-time data visualization
   - User interface for drone control
   - Responsive design for mobile

2. **WebSocket Server** (`src/websocket-server/`)
   - Real-time data streaming
   - Client connection management
   - Kafka message broadcasting
   - Message routing and filtering

3. **Feedback Service** (`src/feedback-service/`)
   - Text-to-speech conversion
   - Audio device management
   - Message prioritization
   - Voice feedback system

### Development Workflow:

#### 1. Frontend Development:
```bash
# Navigate to React app
cd src/web-dashboard/

# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Run tests
npm test
```

#### 2. WebSocket Development:
```bash
# Navigate to WebSocket server
cd src/websocket-server/

# Install Node.js dependencies
npm install

# Start development server
node server.js

# Test WebSocket connection
cd tests/
python test_websocket.py
```

#### 3. TTS Development:
```bash
# Navigate to TTS service
cd src/feedback-service/

# Install Python dependencies
pip install -r requirements.txt

# Start service
python feedback.py

# Test TTS
curl -X POST http://localhost:8005/speak \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello drone"}'
```

## Important Files and Their Purpose

### Core Application Files:
- `src/web-dashboard/src/App.jsx`: Main React application component
- `src/websocket-server/server.js`: WebSocket server implementation
- `src/feedback-service/feedback.py`: Text-to-speech FastAPI service

### Frontend Files:
- `src/web-dashboard/src/components/`: Reusable UI components
- `src/web-dashboard/src/pages/`: Page-level components
- `src/web-dashboard/src/services/`: API integration functions
- `src/web-dashboard/package.json`: Node.js dependencies and scripts

### Backend Files:
- `src/websocket-server/kafka_listener.js`: Kafka message consumption
- `src/websocket-server/message_handler.js`: WebSocket message processing
- `src/feedback-service/tts_engine.py`: Text-to-speech engine implementation

### Configuration Files:
- `config/nginx_config.conf`: Nginx web server configuration
- `config/websocket_config.yaml`: WebSocket server settings
- `config/tts_config.yaml`: Text-to-speech parameters
- `config/kafka_topics.yaml`: Kafka topic mappings

## Coding Standards

### React/JavaScript Standards:
- Use **PascalCase** for components
- Use **camelCase** for variables and functions
- Use functional components with hooks
- Include PropTypes for component validation
- Follow accessibility best practices

### Python Standards:
- Use **snake_case** for variables and functions
- Use **PascalCase** for classes
- Include type hints for API endpoints
- Document audio processing functions
- Handle audio device errors gracefully

### WebSocket Standards:
- Use JSON message format
- Include message timestamps
- Handle connection errors
- Implement reconnection logic
- Rate limit message broadcasting

## Common Tasks

### Adding New UI Components:
1. Create component in `src/web-dashboard/src/components/`
2. Add props and state management
3. Include styling in `src/web-dashboard/src/styles/`
4. Add tests in `tests/test_frontend.py`
5. Update documentation in `docs/FRONTEND_GUIDE.md`

### Adding WebSocket Features:
1. Update message schema in `src/websocket-server/message_handler.js`
2. Add client handling in `src/websocket-server/client_manager.js`
3. Update Kafka topics in `config/kafka_topics.yaml`
4. Add tests in `tests/test_websocket.py`
5. Update API docs in `docs/WEBSOCKET_API.md`

### Improving TTS:
1. Modify voice settings in `config/tts_config.yaml`
2. Update TTS engine in `src/feedback-service/tts_engine.py`
3. Add new voice options or languages
4. Test audio quality
5. Update setup guide in `docs/TTS_SETUP.md`

## UI/UX Standards

### Design Guidelines:
- Use consistent color scheme
- Implement responsive design
- Include loading states
- Add error handling UI
- Optimize for mobile devices

### Accessibility:
- Include ARIA labels
- Support keyboard navigation
- Provide text alternatives
- Ensure color contrast compliance
- Test with screen readers

### Performance:
- Optimize bundle size
- Implement lazy loading
- Use efficient rendering
- Monitor WebSocket performance
- Test on various devices

## Audio Standards

### Voice Feedback:
- Use clear, natural voice
- Prioritize important messages
- Handle audio device conflicts
- Support multiple languages
- Include volume controls

### Audio Management:
- Test on different systems
- Handle audio device errors
- Support multiple audio outputs
- Monitor audio performance
- Log audio issues

## Getting Help

### For Frontend Issues:
1. Check build logs in `logs/web-dashboard.log`
2. Verify React dependencies in `package.json`
3. Test components individually
4. Review `docs/FRONTEND_GUIDE.md`

### For WebSocket Issues:
1. Check WebSocket logs in `logs/websocket.log`
2. Verify Kafka connectivity
3. Test client connections
4. Review `docs/WEBSOCKET_API.md`

### For TTS Issues:
1. Check TTS logs in `logs/feedback.log`
2. Verify audio device availability
3. Test TTS configuration
4. Review `docs/TTS_SETUP.md`

### For Nginx Issues:
1. Check Nginx logs in `logs/nginx.log`
2. Verify configuration in `config/nginx_config.conf`
3. Test web server connectivity
4. Check port availability

---

**This structure ensures organized full-stack development and effective user experience.**
