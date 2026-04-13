# PC2 Project Structure

## Directory Overview
This is the standardized structure for PC2 (Vision & Navigation) development.

## Folders and Their Purpose

```
PC2/
├── 📁 src/                    # Source code files
│   ├── object-detection/       # Computer vision logic
│   │   ├── detector.py        # Main YOLOv5 detection service
│   │   ├── yolo_handler.py   # YOLO model wrapper
│   │   ├── image_processor.py # Image preprocessing
│   │   ├── camera_sim.py     # Camera simulation
│   │   └── tests/           # Unit tests for detection
│   │
│   ├── rl-navigation/          # Reinforcement learning logic
│   │   ├── rl_agent.py       # Main RL service
│   │   ├── environment.py    # Custom gym environment
│   │   ├── model_trainer.py  # PPO model training
│   │   ├── policy_network.py # Neural network architecture
│   │   └── tests/           # Unit tests for RL
│   │
│   └── gazebo-integration/   # Simulation integration
│       ├── gazebo_client.py  # Gazebo API client
│       ├── px4_interface.py  # PX4 SITL connection
│       ├── world_builder.py  # Custom world creation
│       └── tests/           # Integration tests
│
├── 📁 models/                # AI model files
│   ├── yolov5s.pt          # Pre-trained YOLOv5 model
│   ├── rl_model.pth         # Trained RL model
│   ├── model_metadata.yaml  # Model information
│   └── checkpoints/         # Training checkpoints
│
├── 📁 config/                # Configuration files
│   ├── detection_config.yaml # Object detection parameters
│   ├── rl_config.yaml      # Reinforcement learning settings
│   ├── gazebo_worlds.yaml  # Simulation environments
│   └── environment.env     # Environment variables
│
├── 📁 data/                  # Data and datasets
│   ├── training_images/    # Training image dataset
│   ├── annotations/        # Bounding box annotations
│   ├── simulation_logs/   # Gazebo simulation logs
│   └── performance_data/  # Model performance metrics
│
├── 📁 docs/                 # Documentation
│   ├── MODEL_TRAINING.md  # Model training guide
│   ├── GAZEBO_SETUP.md    # Gazebo configuration
│   ├── API_DOCS.md        # API documentation
│   └── TROUBLESHOOTING.md # Common issues
│
├── 📁 logs/                 # Log files
│   ├── object-detection.log # Detection service logs
│   ├── rl-navigation.log    # RL service logs
│   ├── gazebo.log         # Gazebo simulation logs
│   └── training.log       # Model training logs
│
├── 📁 tests/                # Integration tests
│   ├── test_vision.py     # Computer vision tests
│   ├── test_navigation.py  # RL navigation tests
│   ├── test_gazebo.py     # Simulation tests
│   └── test_integration.py # End-to-end tests
│
├── 📁 scripts/              # Utility scripts
│   ├── train_model.sh      # Model training script
│   ├── setup_gazebo.sh    # Gazebo environment setup
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
- **Python files**: `snake_case.py` (e.g., `object_detector.py`)
- **Model files**: `descriptive_name.pt` or `model_name.pth`
- **Configuration**: `descriptive_name.yaml` (e.g., `detection_config.yaml`)
- **Tests**: `test_*.py` (e.g., `test_vision.py`)
- **Documentation**: `UPPER_CASE.md` (e.g., `MODEL_TRAINING.md`)

### Directory Naming:
- **Source code**: `kebab-case` (e.g., `object-detection`)
- **Models**: `models`
- **Data**: `data`
- **Configuration**: `config`
- **Documentation**: `docs`
- **Tests**: `tests`

## Developer Responsibilities

### What You'll Work On:
1. **Object Detection Service** (`src/object-detection/`)
   - Implement YOLOv5 object detection
   - Process camera images in real-time
   - Detect obstacles and targets
   - Publish detection results to Kafka

2. **RL Navigation Service** (`src/rl-navigation/`)
   - Train reinforcement learning agent
   - Implement PPO (Proximal Policy Optimization)
   - Make autonomous navigation decisions
   - Handle path planning and obstacle avoidance

3. **Gazebo Integration** (`src/gazebo-integration/`)
   - Set up drone simulation environment
   - Connect to PX4 SITL flight stack
   - Create custom worlds and scenarios
   - Simulate realistic physics

### Development Workflow:

#### 1. Training New Models:
```bash
# Prepare training data
cd data/training_images/
# Organize images and annotations

# Train YOLO model
cd scripts/
./train_model.sh yolov5

# Train RL agent
python src/rl-navigation/model_trainer.py
```

#### 2. Testing Detection:
```bash
# Test object detection
cd tests/
python test_vision.py

# Test with custom images
python src/object-detection/detector.py --test-image path/to/image.jpg
```

#### 3. Simulation Testing:
```bash
# Start Gazebo with custom world
cd src/gazebo-integration/
python gazebo_client.py --world forest.world

# Test RL agent in simulation
python src/rl-navigation/rl_agent.py --sim-mode
```

## Important Files and Their Purpose

### Core Application Files:
- `src/object-detection/detector.py`: Main YOLOv5 FastAPI service
- `src/rl-navigation/rl_agent.py`: Reinforcement learning navigation service
- `src/gazebo-integration/gazebo_client.py`: Gazebo simulation interface

### Model Files:
- `models/yolov5s.pt`: Pre-trained YOLOv5 model for object detection
- `models/rl_model.pth`: Trained reinforcement learning model
- `models/model_metadata.yaml`: Model version and performance information

### Configuration Files:
- `config/detection_config.yaml`: YOLO detection parameters
- `config/rl_config.yaml`: Reinforcement learning hyperparameters
- `config/gazebo_worlds.yaml`: Simulation environment definitions

### Data Files:
- `data/training_images/`: Dataset for training detection models
- `data/simulation_logs/`: Gazebo simulation logs and metrics
- `data/performance_data/`: Model performance tracking

## Coding Standards

### Python Code Style:
- Use **snake_case** for variables and functions
- Use **PascalCase** for classes
- Maximum line length: 88 characters
- Include type hints for AI/ML functions
- Document model architectures and parameters

### ML/AI Standards:
- Save model checkpoints regularly
- Log training metrics and curves
- Version control model configurations
- Document data preprocessing steps
- Test models on validation sets

### Documentation Standards:
- Document model training procedures
- Include performance benchmarks
- Provide setup instructions for GPU requirements
- Maintain API documentation for services

## Common Tasks

### Adding New Object Classes:
1. Update `config/detection_config.yaml` with new classes
2. Add training data to `data/training_images/`
3. Retrain YOLO model using `scripts/train_model.sh`
4. Update model metadata in `models/model_metadata.yaml`
5. Test detection with new classes

### Improving RL Performance:
1. Modify reward function in `src/rl-navigation/environment.py`
2. Adjust hyperparameters in `config/rl_config.yaml`
3. Train new model using `src/rl-navigation/model_trainer.py`
4. Evaluate performance in `data/performance_data/`
5. Update model in `models/` directory

### Creating New Gazebo Worlds:
1. Design world in Gazebo editor
2. Save world file to appropriate directory
3. Update `config/gazebo_worlds.yaml`
4. Test with `src/gazebo-integration/gazebo_client.py`
5. Document world features in `docs/GAZEBO_SETUP.md`

## Performance Optimization

### GPU Requirements:
- **Object Detection**: NVIDIA GPU with 4GB+ VRAM recommended
- **RL Training**: NVIDIA GPU with 8GB+ VRAM for faster training
- **Simulation**: CPU-intensive, GPU optional for rendering

### Memory Management:
- Monitor GPU memory usage during training
- Use batch processing for image detection
- Clear model cache between runs
- Optimize model size for deployment

## Getting Help

### For Model Issues:
1. Check training logs in `logs/training.log`
2. Review model performance in `data/performance_data/`
3. Verify model files in `models/` directory
4. Check GPU availability and memory

### For Simulation Issues:
1. Check Gazebo logs in `logs/gazebo.log`
2. Verify PX4 SITL connection
3. Test with basic world files
4. Review `docs/GAZEBO_SETUP.md`

### For Detection Issues:
1. Check detection logs in `logs/object-detection.log`
2. Test with known good images
3. Verify YOLO model loading
4. Review `config/detection_config.yaml`

---

**This structure ensures organized AI/ML development and easy model management.**
