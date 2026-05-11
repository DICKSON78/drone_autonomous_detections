# 🚁 Autonomous Drone Obstacle Detection System - Complete Guide

## 📋 Overview

This is a complete **Autonomous Drone Obstacle Detection** system that includes:
- **YOLO** (Object Detection)
- **RL** (Reinforcement Learning) 
- **NLP** (Natural Language Processing)

The system is built within **PC2 - Vision & Navigation** and combines three technologies to provide a complete drone obstacle avoidance solution.

---

## 🏗️ Project Structure (PC2)

```
PC2/
├── src/
│   ├── object-detection/
│   │   ├── main.py              # FastAPI service
│   │   ├── auto_label.py        # Auto-labeling system
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   ├── rl-navigation/
│   │   ├── main.py              # FastAPI service
│   │   ├── drone_env.py         # RL environment
│   │   ├── train_rl.py          # RL training
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   ├── nlp_module.py            # NLP explanations
│   ├── main_pipeline.py         # Integrated system
│   └── train_yolo.py            # YOLO training
├── data/                        # Training data
├── models/                      # Trained models
├── logs/                        # System logs
├── dataset.yaml                 # Dataset configuration
├── requirements.txt             # All dependencies
└── docker-compose.yml
```

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
cd PC2
pip install -r requirements.txt
```

### 2. Prepare Training Data
```bash
# Update path in auto_label.py
python src/object-detection/auto_label.py
```

### 3. Train YOLO Model
```bash
python src/train_yolo.py --epochs 100
```

### 4. Train RL Model
```bash
python src/rl-navigation/train_rl.py --timesteps 500000
```

### 5. Run Complete System
```bash
python src/main_pipeline.py --demo
```

---

## 📚 Module Descriptions

### 🔍 Object Detection (YOLO)

**Location**: `src/object-detection/`

**Features**:
- **Auto-labeling**: Use pretrained YOLO to generate labels
- **FastAPI Service**: REST API for real-time detection
- **Multi-class Support**: 6 classes (tree, building, pole, person, vehicle, aircraft)

**Classes**:
```
0: tree      (Tree)
1: building  (Building)  
2: pole      (Pole)
3: person    (Person)
4: vehicle   (Vehicle)
5: aircraft  (Aircraft)
```

**API Endpoints**:
- `POST /detect` - Detect objects in image
- `POST /detect-base64` - Detect in base64 image
- `GET /health` - Health check
- `GET /classes` - Supported classes

### 🧠 Reinforcement Learning

**Location**: `src/rl-navigation/`

**Features**:
- **Custom Environment**: Drone obstacle avoidance environment
- **PPO Training**: Proximal Policy Optimization
- **Multi-env Training**: Parallel training for efficiency
- **Evaluation Metrics**: Performance measurement

**Actions**:
```
0: turn_left    (Turn left)
1: turn_right   (Turn right)
2: climb        (Climb up)
3: descend      (Descend down)
4: forward      (Move forward)
5: stop         (Stop)
```

**Reward System**:
- +10: If it avoids obstacles
- -100: If it crashes
- +1: If it moves forward safely
- -5: If it stops without reason

### 🗣️ NLP Module

**Location**: `src/nlp_module.py`

**Features**:
- **English Explanations**: Explanations in English language
- **Flight Analysis**: Analyze flight patterns
- **Alert Messages**: Alert messages
- **Flight Summary**: Complete flight summary

**Example Explanations**:
```
"Drone detected person to the left, very close (95% confidence). Taking action: turn right."
```

### 🔌 Main Pipeline

**Location**: `src/main_pipeline.py`

**Features**:
- **Integration**: Combines YOLO + RL + NLP
- **Real-time Processing**: Process video frames live
- **Visualization**: Show results on video
- **Logging**: Save performance data

---

## 🛠️ Configuration

### Dataset Configuration (`dataset.yaml`)
```yaml
path: ./data
train: images/train
val: images/val
nc: 6
names:
  0: tree
  1: building
  2: pole
  3: person
  4: vehicle
  5: aircraft
```

### System Configuration
```python
config = {
    "yolo_model_path": "yolov8n.pt",
    "rl_model_path": "models/drone_ppo_final.zip",
    "detection_confidence": 0.4,
    "rl_confidence_threshold": 0.7,
    "max_obstacles": 10
}
```

---

## 📊 Performance Metrics

### YOLO Metrics
- **mAP@0.5**: Mean Average Precision at IoU 0.5
- **mAP@0.5:0.95**: Mean Average Precision at IoU 0.5-0.95
- **Precision**: Detection precision
- **Recall**: Detection recall

### RL Metrics
- **Success Rate**: Percentage of successful episodes
- **Average Reward**: Average reward per episode
- **Crash Rate**: Percentage of crashes
- **Avoidance Rate**: Percentage of obstacles avoided

### System Metrics
- **FPS**: Frames per second processing
- **Detection Time**: Detection time per frame
- **Decision Time**: RL decision time
- **Total Latency**: Complete processing time

---

## 🎂 System Usage

### 1. Training Mode
```bash
# Train YOLO
python src/train_yolo.py --epochs 100 --batch 16

# Train RL
python src/rl-navigation/train_rl.py --timesteps 500000 --model PPO
```

### 2. Demo Mode
```bash
# Run with webcam
python src/main_pipeline.py --demo

# Run with video file
python src/main_pipeline.py --video test_video.mp4
```

### 3. Production Mode
```bash
# Start services
docker-compose up -d

# Run pipeline
python src/main_pipeline.py --video rtsp://drone_camera
```

---

## 🐛 Debugging & Troubleshooting

### Common Issues

#### 1. YOLO Model Not Loading
```bash
# Reinstall ultralytics
pip install ultralytics==8.0.206

# Check if model file exists
ls yolov8n.pt
```

#### 2. RL Model Not Working
```bash
# Install stable-baselines3
pip install stable-baselines3==2.2.1

# Check training
python src/rl-navigation/train_rl.py --test
```

#### 3. Memory Issues
```python
# Reduce batch size
config = {"batch_size": 8}

# Use smaller model
config = {"model_name": "yolov8n.pt"}
```

#### 4. GPU Support
```bash
# Check if CUDA is available
nvidia-smi

# Install PyTorch GPU version
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

---

## 📈 Optimization Tips

### YOLO Optimization
- Use `yolov8n.pt` for real-time performance
- Reduce `imgsz` for faster processing
- Increase `confidence` for fewer false positives

### RL Optimization
- Increase `n_envs` for parallel training
- Use `tensorboard` for monitoring
- Adjust reward function for better performance

### System Optimization
- Use GPU for YOLO inference
- Optimize image resolution
- Cache models in memory

---

## 🔧 Advanced Configuration

### Custom Classes
```python
# Add new classes in dataset.yaml
names:
  6: power_line
  7: wind_turbine
  8: satellite_dish
```

### Custom Rewards
```python
# Change reward function in drone_env.py
def _compute_reward(self, action):
    # Custom reward logic
    pass
```

### Custom NLP
```python
# Add new explanations in nlp_module.py
def explain_custom_situation(self, situation):
    # Custom explanation logic
    pass
```

---

## 📱 API Integration

### Object Detection API
```python
import requests

# Detect objects
response = requests.post(
    "http://localhost:8002/detect",
    files={"file": open("image.jpg", "rb")}
)
detections = response.json()
```

### RL Decision API
```python
# Get RL decision
response = requests.post(
    "http://localhost:8003/decide",
    json={"obstacles": obstacles}
)
action = response.json()["action"]
```

---

## 🎯 Use Cases

### 1. Agricultural Monitoring
- Detect trees, buildings, power lines
- Avoid obstacles during crop monitoring
- Generate flight reports in English

### 2. Urban Inspection
- Detect buildings, vehicles, people
- Navigate through urban environments
- Real-time obstacle avoidance

### 3. Wildlife Conservation
- Detect animals (birds, mammals)
- Avoid disturbing wildlife
- Generate conservation reports

---

## 📚 References

### YOLO Documentation
- [Ultralytics Docs](https://docs.ultralytics.com/)
- [YOLOv8 Paper](https://arxiv.org/abs/2305.14299)

### Reinforcement Learning
- [Stable Baselines3](https://stable-baselines3.readthedocs.io/)
- [OpenAI Gym](https://gymnasium.farama.org/)

### Computer Vision
- [OpenCV Docs](https://opencv.org/)
- [PyTorch Docs](https://pytorch.org/docs/)

---

## 🤝 Contributing

1. Fork project
2. Create feature branch
3. Make changes
4. Test thoroughly
5. Submit pull request

---

## 📄 License

This project is part of the Autonomous Drone System FYP.

---

## 👥 Team

- **PC1**: Command & Control
- **PC2**: Vision & Navigation (This module)
- **PC3**: Data & Monitoring
- **PC4**: Web Interface & Feedback

---

## 🎉 Conclusion

The **Autonomous Drone Obstacle Detection** system has been completely built and can be used for:
- Real-time obstacle detection
- Autonomous navigation
- Flight analysis
- Safety monitoring

For more help, contact the PC2 team or check the documentation for PC1, PC3, and PC4.
