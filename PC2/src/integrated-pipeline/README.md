# Integrated Pipeline Service

This service combines YOLO object detection, RL navigation, and NLP explanations into a single unified system.

## Features

- **Object Detection**: YOLOv8-based obstacle detection
- **Navigation**: Reinforcement learning-based decision making
- **Natural Language**: English explanations of drone decisions
- **Real-time Processing**: Complete pipeline processing

## API Endpoints

- `GET /health` - Health check
- `POST /process_frame` - Process frame with complete system
- `GET /stats` - Get system statistics

## Usage

```bash
# Build and run
docker-compose up integrated-pipeline

# Test health
curl http://localhost:8004/health

# Process frame
curl -X POST http://localhost:8004/process_frame \
  -H "Content-Type: application/json" \
  -d '{"frame": "base64_encoded_image_data"}'
```

## Dependencies

- PyTorch & TorchVision
- Ultralytics YOLO
- Stable Baselines3
- OpenCV
- FastAPI
- Kafka Python
