# Model training script for AI development

#!/bin/bash
echo "=== PC2 Model Training Script ==="

if [ "$1" = "rl" ]; then
    echo "Starting RL Navigation Training..."
    python -m src.rl_navigation.model_trainer
elif [ "$1" = "yolo" ]; then
    echo "Fine-tuning YOLO model..."
    python -m src.object_detection.train_yolo
else
    echo "Usage: ./train_model.sh [rl|yolo]"
    echo "Note: Models are not trained yet. Use pretrained for now."
fi