# PC1 Project Structure

## Directory Overview
This is the standardized structure for PC1 (Command & Control) development.

## Folders and Their Purpose

```
PC1/
├── 📁 src/                    # Source code files
│   ├── command-parser/         # Command processing logic
│   │   ├── main.py           # Main FastAPI application
│   │   ├── models.py         # Data models and schemas
│   │   ├── nlp_processor.py   # Natural language processing
│   │   └── tests/           # Unit tests for command parser
│   │
│   └── flight-control/        # Flight control logic
│       ├── flight_controller.py # Main MAVSDK application
│       ├── drone_interface.py  # Drone communication layer
│       ├── command_executor.py # Command execution logic
│       └── tests/           # Unit tests for flight control
│
├── 📁 config/                # Configuration files
│   ├── kafka_topics.yaml     # Kafka topic definitions
│   ├── drone_config.yaml     # Drone parameters
│   └── environment.env      # Environment variables
│
├── 📁 docs/                 # Documentation
│   ├── API_DOCS.md          # API documentation
│   ├── SETUP_GUIDE.md        # Setup instructions
│   └── TROUBLESHOOTING.md   # Common issues and solutions
│
├── 📁 logs/                 # Log files
│   ├── command-parser.log    # Command parser logs
│   ├── flight-control.log    # Flight control logs
│   └── kafka.log           # Kafka broker logs
│
├── 📁 tests/                # Integration tests
│   ├── test_integration.py   # Full system tests
│   ├── test_commands.py     # Command processing tests
│   └── test_flight.py      # Flight control tests
│
├── 📁 scripts/              # Utility scripts
│   ├── setup_dev.sh         # Development environment setup
│   ├── run_tests.sh        # Test runner script
│   └── deploy.sh           # Deployment script
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
- **Python files**: `snake_case.py` (e.g., `command_processor.py`)
- **Configuration**: `descriptive_name.yaml` or `environment.env`
- **Tests**: `test_*.py` (e.g., `test_commands.py`)
- **Documentation**: `UPPER_CASE.md` (e.g., `API_DOCS.md`)

### Directory Naming:
- **Source code**: `kebab-case` (e.g., `command-parser`)
- **Configuration**: `config`
- **Documentation**: `docs`
- **Tests**: `tests`
- **Logs**: `logs`

## Developer Responsibilities

### What You'll Work On:
1. **Command Parser Service** (`src/command-parser/`)
   - Parse natural language commands
   - Convert to structured drone commands
   - Handle user input validation
   - Manage command history

2. **Flight Control Service** (`src/flight-control/`)
   - Connect to drone via MAVSDK
   - Execute flight commands
   - Monitor drone status
   - Handle emergency procedures

3. **Kafka Integration** (`config/kafka_topics.yaml`)
   - Define message topics
   - Handle message serialization
   - Manage consumer groups
   - Ensure message delivery

### Development Workflow:

#### 1. Adding New Features:
```bash
# Create feature branch
git checkout -b feature/new-command-type

# Work in appropriate directory
cd src/command-parser/
# or
cd src/flight-control/

# Write code following naming conventions
# Add tests in tests/ directory
# Update documentation in docs/
```

#### 2. Testing Your Changes:
```bash
# Run unit tests
cd tests/
python -m pytest test_commands.py

# Run integration tests
python test_integration.py

# Check code quality
flake8 src/
black src/
```

#### 3. Before Committing:
```bash
# Run all tests
./scripts/run_tests.sh

# Check formatting
black src/ tests/

# Commit with descriptive message
git add .
git commit -m "Add support for emergency landing commands"
```

## Important Files and Their Purpose

### Core Application Files:
- `src/command-parser/main.py`: FastAPI server for command processing
- `src/flight-control/flight_controller.py`: MAVSDK drone control
- `docker-compose.yml`: Service orchestration and networking

### Configuration Files:
- `config/kafka_topics.yaml`: Message broker configuration
- `config/drone_config.yaml`: Flight parameters and limits
- `environment.env`: Runtime environment variables

### Documentation Files:
- `docs/API_DOCS.md`: Complete API reference
- `docs/SETUP_GUIDE.md`: Detailed setup instructions
- `README.md`: Quick start and overview

### Testing Files:
- `tests/test_integration.py`: End-to-end system tests
- `src/*/tests/`: Unit tests for each service

## Coding Standards

### Python Code Style:
- Use **snake_case** for variables and functions
- Use **PascalCase** for classes
- Maximum line length: 88 characters
- Use type hints where appropriate
- Include docstrings for all functions

### Documentation Standards:
- Update API docs when changing endpoints
- Include examples in documentation
- Document configuration options
- Maintain README with current status

### Testing Standards:
- Write unit tests for all new functions
- Include integration tests for new features
- Test error conditions and edge cases
- Maintain test coverage > 80%

## Common Tasks

### Adding New Command Type:
1. Update `src/command-parser/models.py` with new command schema
2. Implement parsing logic in `src/command-parser/nlp_processor.py`
3. Add execution logic in `src/flight-control/command_executor.py`
4. Write tests in `tests/test_commands.py`
5. Update API documentation

### Adding New Drone Capability:
1. Update `src/flight-control/drone_interface.py`
2. Add new commands to `config/drone_config.yaml`
3. Implement in `src/flight-control/flight_controller.py`
4. Add monitoring and logging
5. Write integration tests

### Updating Kafka Topics:
1. Modify `config/kafka_topics.yaml`
2. Update producers and consumers
3. Test message flow
4. Update documentation

## Getting Help

### For Code Issues:
1. Check logs in `logs/` directory
2. Review `docs/TROUBLESHOOTING.md`
3. Run tests to isolate problems
4. Check Git history for recent changes

### For System Issues:
1. Verify Docker containers: `docker-compose ps`
2. Check network connectivity: `ping PC2`, `ping PC3`, `ping PC4`
3. Review service logs: `docker-compose logs -f`

### For Team Coordination:
1. Use team communication channel
2. Share error logs and stack traces
3. Document solutions in `docs/`
4. Update this structure file as needed

---

**This structure ensures consistent development practices and easy collaboration across the team.**
