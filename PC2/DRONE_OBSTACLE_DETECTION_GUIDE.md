# 🚁 Autonomous Drone Obstacle Detection System - Kamili Guide

## 📋 Muhtasari

Hii ni mfumo kamili wa **Autonomous Drone Obstacle Detection** unaojumuisha:
- **YOLO** (Object Detection)
- **RL** (Reinforcement Learning) 
- **NLP** (Natural Language Processing)

Mfumo umejengwa ndani ya **PC2 - Vision & Navigation** na unaunganisha teknolojia tatu kutoa suluhisho kamili la drone obstacle avoidance.

---

## 🏗️ Muundo wa Project (PC2)

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

## 🚀 Mwanzo wa Haraka

### 1. Sakinisha Dependencies
```bash
cd PC2
pip install -r requirements.txt
```

### 2. Andaa Data ya Training
```bash
# Badilisha path kwenye auto_label.py
python src/object-detection/auto_label.py
```

### 3. Fundisha YOLO Model
```bash
python src/train_yolo.py --epochs 100
```

### 4. Fundisha RL Model
```bash
python src/rl-navigation/train_rl.py --timesteps 500000
```

### 5. Endesha Mfumo Kamili
```bash
python src/main_pipeline.py --demo
```

---

## 📚 Maelezo ya Kila Module

### 🔍 Object Detection (YOLO)

**Location**: `src/object-detection/`

**Vipengele**:
- **Auto-labeling**: Tumia YOLO pretrained kuzalisha labels
- **FastAPI Service**: REST API kwa real-time detection
- **Multi-class Support**: 6 classes (tree, building, pole, person, vehicle, aircraft)

**Classes**:
```
0: tree      (Mti)
1: building  (Jengo)  
2: pole      (Nguzo)
3: person    (Mtu)
4: vehicle   (Gari)
5: aircraft  (Ndege)
```

**API Endpoints**:
- `POST /detect` - Detect objects in image
- `POST /detect-base64` - Detect in base64 image
- `GET /health` - Health check
- `GET /classes` - Supported classes

### 🧠 Reinforcement Learning

**Location**: `src/rl-navigation/`

**Vipengele**:
- **Custom Environment**: Drone obstacle avoidance environment
- **PPO Training**: Proximal Policy Optimization
- **Multi-env Training**: Parallel training for efficiency
- **Evaluation Metrics**: Performance measurement

**Actions**:
```
0: go_left    (Geuka kushoto)
1: go_right   (Geuka kulia)
2: climb      (Panda juu)
3: descend    (Shuka chini)
4: forward    (Endelea mbele)
5: stop       (Simama)
```

**Reward System**:
- +10: Kama inaepuka k vizuizi
- -100: Kama inagonga (crash)
- +1: Kama inasogea mbele salama
- -5: Kama inasimama bila sababu

### 🗣️ NLP Module

**Location**: `src/nlp_module.py`

**Vipengele**:
- **Swahili Explanations**: Maelezo kwa lugha ya Kiswahili
- **Flight Analysis**: Chambua muundo wa flight
- **Alert Messages**: Ujumbe wa tahadhari
- **Flight Summary**: Muhtasari wa safari nzima

**Mifano ya Maelezo**:
```
"Drone imeona mtu kushoto, karibu sana (95% uhakika). Inachukua hatua: geuka kulia."
```

### 🔌 Main Pipeline

**Location**: `src/main_pipeline.py`

**Vipengele**:
- **Integration**: Inaunganisha YOLO + RL + NLP
- **Real-time Processing**: Process video frames live
- **Visualization**: Onyesha matokeo kwenye video
- **Logging**: Hifadhi data ya performance

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
- **Precision**: Precision ya detection
- **Recall**: Recall ya detection

### RL Metrics
- **Success Rate**: Asilimia ya episodes zilizofanikiwa
- **Average Reward**: Wastani wa reward kwa episode
- **Crash Rate**: Asilimia ya ajali
- **Avoidance Rate**: Asilimia ya vizuizi vilivyoevuka

### System Metrics
- **FPS**: Frames per second processing
- **Detection Time**: Muda wa detection kwa frame
- **Decision Time**: Muda wa uamuzi wa RL
- **Total Latency**: Muda wa processing kamili

---

## 🎂 Matumizi ya Mfumo

### 1. Training Mode
```bash
# Fundisha YOLO
python src/train_yolo.py --epochs 100 --batch 16

# Fundisha RL
python src/rl-navigation/train_rl.py --timesteps 500000 --model PPO
```

### 2. Demo Mode
```bash
# Endesha na webcam
python src/main_pipeline.py --demo

# Endesha na video file
python src/main_pipeline.py --video test_video.mp4
```

### 3. Production Mode
```bash
# Start services
docker-compose up -d

# Endesha pipeline
python src/main_pipeline.py --video rtsp://drone_camera
```

---

## 🐛 Debugging & Troubleshooting

### Common Issues

#### 1. YOLO Model Haipaki
```bash
# Sakinisha ultralytics upya
pip install ultralytics==8.0.206

# Angalia kama model file ipo
ls yolov8n.pt
```

#### 2. RL Model Haifanyi Kazi
```bash
# Sakinisha stable-baselines3
pip install stable-baselines3==2.2.1

# Angalia kana training
python src/rl-navigation/train_rl.py --test
```

#### 3. Memory Issues
```python
# Punguza batch size
config = {"batch_size": 8}

# Tumia smaller model
config = {"model_name": "yolov8n.pt"}
```

#### 4. GPU Support
```bash
# Angalia kama CUDA ipo
nvidia-smi

# Sakinisha PyTorch GPU version
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

---

## 📈 Optimization Tips

### YOLO Optimization
- Tumia `yolov8n.pt` kwa real-time performance
- Punguza `imgsz` kwa faster processing
- Ongeza `confidence` kwa less false positives

### RL Optimization
- Ongeza `n_envs` kwa parallel training
 tumia `tensorboard` kwa monitoring
- Adjust reward function kwa better performance

### System Optimization
- Tumia GPU kwa YOLO inference
- Optimize image resolution
- Cache models kwenye memory

---

## 🔧 Advanced Configuration

### Custom Classes
```python
# Ongeza classes mpya kwenye dataset.yaml
names:
  6: power_line
  7: wind_turbine
  8: satellite_dish
```

### Custom Rewards
```python
# Badilisha reward function kwenye drone_env.py
def _compute_reward(self, action):
    # Custom reward logic
    pass
```

### Custom NLP
```python
# Ongeza maelezo mapya kwenye nlp_module.py
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
- Generate flight reports in Swahili

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

## 🎉 Mwisho

Mfumo wa **Autonomous Drone Obstacle Detection** umejengwa kikamilifu na unaweza kutumika kwa ajili ya:
- Real-time obstacle detection
- Autonomous navigation
- Flight analysis
- Safety monitoring

Kwa msaada zaidi, wasiliana na team ya PC2 au angalia documentation ya PC1, PC3, na PC4.
