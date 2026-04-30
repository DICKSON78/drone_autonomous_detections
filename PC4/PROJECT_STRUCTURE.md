# PC4 Project Structure

## Directory Overview
This is the standardized structure for PC4 (Feedback Service) development.
PC4 provides Text-to-Speech (TTS) and audio feedback for the drone system.

## Folders and Their Purpose

```
PC4/
├── 📁 src/                    # Source code files
│   └── feedback-service/      # Text-to-speech service
│       ├── feedback.py       # Main FastAPI service
│       ├── tts_engine.py     # Text-to-speech engine
│       ├── audio_manager.py  # Audio device management
│       ├── message_queue.py  # Message queue handling
│       ├── Dockerfile        # Container definition
│       ├── requirements.txt  # Python dependencies
│       └── tests/           # TTS tests
│
├── 📁 config/                # Configuration files
│   ├── feedback_config.yaml  # Feedback service configuration
│   ├── tts_config.yaml       # Text-to-speech settings
│   ├── kafka_topics.yaml     # Kafka topic mappings
│   └── environment.env       # Environment variables
│
├── 📁 logs/                 # Log files
│   └── feedback.log          # TTS service logs
│
├── 📁 tests/                # Integration tests
│   ├── test_tts.py          # TTS service tests
│   └── test_integration.py   # End-to-end tests
│
├── 📁 scripts/              # Utility scripts
│   ├── run_tests.sh         # Test runner
│   └── deploy.sh            # Deployment script
│
├── 📁 docker-compose.yml    # Docker orchestration
├── 📄 README.md            # Main documentation
├── 📄 setup.sh             # Automated setup script
└── 📄 PROJECT_STRUCTURE.md  # This file
```

## File Naming Conventions

### Source Code Files:
- **Python files**: `snake_case.py` (e.g., `feedback.py`, `tts_engine.py`)
- **Configuration**: `descriptive_name.yaml` (e.g., `feedback_config.yaml`)
- **Tests**: `test_*.py` (e.g., `test_tts.py`)
- **Documentation**: `UPPER_CASE.md` (e.g., `TTS_SETUP.md`)

### Directory Naming:
- **Source code**: `kebab-case` (e.g., `feedback-service`)
- **Configuration**: `config`
- **Documentation**: `docs`
- **Tests**: `tests`
- **Scripts**: `scripts`
- **Logs**: `logs`

## Developer Responsibilities

### What You'll Work On:
1. **Feedback Service** (`src/feedback-service/`)
   - Text-to-speech conversion
   - Audio device management
   - Message prioritization
   - Voice feedback system
   - Kafka message consumption
   - REST API endpoints

### Development Workflow:

#### TTS Development:
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
  -d '{"message": "Hello drone", "priority": "normal"}'
```

## Important Files and Their Purpose

### Core Application Files:
- `src/feedback-service/feedback.py`: Main FastAPI service
- `src/feedback-service/tts_engine.py`: Text-to-speech engine
- `src/feedback-service/audio_manager.py`: Audio device management
- `src/feedback-service/message_queue.py`: Message queue handling

### Configuration Files:
- `config/feedback_config.yaml`: Feedback service configuration
- `config/tts_config.yaml`: Text-to-speech parameters
- `config/kafka_topics.yaml`: Kafka topic mappings
- `config/environment.env`: Environment variables

## Coding Standards

### Python Standards:
- Use **snake_case** for variables and functions
- Use **PascalCase** for classes
- Include type hints for API endpoints
- Document audio processing functions
- Handle audio device errors gracefully
- Follow PEP 8 style guidelines

## Common Tasks

### Improving TTS:
1. Modify voice settings in `config/tts_config.yaml`
2. Update TTS engine in `src/feedback-service/tts_engine.py`
3. Add new voice options or languages
4. Test audio quality
5. Update configuration in `config/feedback_config.yaml`

### Adding Kafka Topics:
1. Update Kafka topics in `config/kafka_topics.yaml`
2. Add topic handlers in `src/feedback-service/feedback.py`
3. Test topic consumption
4. Add tests in `tests/test_tts.py`

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

### For TTS Issues:
1. Check TTS logs in `logs/feedback.log`
2. Verify audio device availability
3. Test TTS configuration
4. Review configuration in `config/tts_config.yaml`

### For Kafka Issues:
1. Check Kafka connectivity
2. Verify topic configuration in `config/kafka_topics.yaml`
3. Test message consumption
4. Check service logs

### For Audio Issues:
1. Verify audio device permissions
2. Test audio device availability
3. Check audio configuration in `config/feedback_config.yaml`
4. Test with simple TTS command

---

**This structure ensures organized Feedback Service development and effective audio feedback system.**