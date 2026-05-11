#!/usr/bin/env python3
"""
YOLO Training Script for Drone Obstacle Detection
Kufundisha YOLO model kwa ajili ya drone obstacle detection
"""

import os
import logging
import yaml
from pathlib import Path
from typing import Dict, Optional
from ultralytics import YOLO

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DroneYOLOTrainer:
    """Trainer class for drone YOLO model"""
    
    def __init__(self, config: Dict = None):
        self.config = config or self._default_config()
        self.model = None
        self.setup_directories()
    
    def _default_config(self) -> Dict:
        """Default training configuration"""
        return {
            "model_name": "yolov8n.pt",  # Start with small model for drone (real-time)
            "dataset_yaml": "dataset.yaml",
            "epochs": 100,
            "imgsz": 640,
            "batch": 16,
            "patience": 20,
            "save_period": 10,
            "device": "cpu",  # Change to "0" for GPU
            "project": "runs/detect",
            "name": "drone_yolo",
            "optimizer": "AdamW",
            "lr0": 0.01,
            "weight_decay": 0.0005,
            "warmup_epochs": 3,
            "warmup_momentum": 0.8,
            "warmup_bias_lr": 0.1,
            "box": 7.5,
            "cls": 0.5,
            "dfl": 1.5,
            "pose": 12.0,
            "kobj": 1.0,
            "label_smoothing": 0.0,
            "nbs": 64,
            "hsv_h": 0.015,
            "hsv_s": 0.7,
            "hsv_v": 0.4,
            "degrees": 10.0,
            "translate": 0.1,
            "scale": 0.5,
            "shear": 0.0,
            "perspective": 0.0,
            "flipud": 0.0,
            "fliplr": 0.5,
            "mosaic": 1.0,
            "mixup": 0.0,
            "copy_paste": 0.0
        }
    
    def setup_directories(self):
        """Create necessary directories"""
        dirs = ["data", "models", "logs", "runs"]
        for dir_path in dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {dir_path}")
    
    def check_dataset(self) -> bool:
        """Check if dataset is properly configured"""
        dataset_path = Path(self.config["dataset_yaml"])
        
        if not dataset_path.exists():
            logger.error(f"Dataset configuration not found: {dataset_path}")
            return False
        
        try:
            with open(dataset_path, 'r') as f:
                dataset_config = yaml.safe_load(f)
            
            # Check train and val directories
            base_path = Path(dataset_config.get('path', './data'))
            train_dir = base_path / dataset_config.get('train', 'images/train')
            val_dir = base_path / dataset_config.get('val', 'images/val')
            
            if not train_dir.exists():
                logger.error(f"Training directory not found: {train_dir}")
                return False
            
            if not val_dir.exists():
                logger.error(f"Validation directory not found: {val_dir}")
                return False
            
            # Count images
            train_images = list(train_dir.glob("*.jpg")) + list(train_dir.glob("*.png"))
            val_images = list(val_dir.glob("*.jpg")) + list(val_dir.glob("*.png"))
            
            logger.info(f"Dataset check passed:")
            logger.info(f"  • Training images: {len(train_images)}")
            logger.info(f"  • Validation images: {len(val_images)}")
            logger.info(f"  • Classes: {dataset_config.get('nc', 0)}")
            
            return len(train_images) > 0 and len(val_images) > 0
            
        except Exception as e:
            logger.error(f"Error checking dataset: {e}")
            return False
    
    def load_model(self) -> bool:
        """Load YOLO model"""
        try:
            self.model = YOLO(self.config["model_name"])
            logger.info(f"✅ YOLO model loaded: {self.config['model_name']}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to load YOLO model: {e}")
            return False
    
    def train(self) -> Optional[str]:
        """Train YOLO model"""
        logger.info("🚁 Starting YOLO training for drone obstacle detection...")
        
        # Check dataset
        if not self.check_dataset():
            logger.error("❌ Dataset check failed. Cannot start training.")
            return None
        
        # Load model
        if not self.load_model():
            return None
        
        # Prepare training arguments
        train_args = {
            "data": self.config["dataset_yaml"],
            "epochs": self.config["epochs"],
            "imgsz": self.config["imgsz"],
            "batch": self.config["batch"],
            "patience": self.config["patience"],
            "save": True,
            "device": self.config["device"],
            "project": self.config["project"],
            "name": self.config["name"],
            "optimizer": self.config["optimizer"],
            "lr0": self.config["lr0"],
            "weight_decay": self.config["weight_decay"],
            "warmup_epochs": self.config["warmup_epochs"],
            "warmup_momentum": self.config["warmup_momentum"],
            "warmup_bias_lr": self.config["warmup_bias_lr"],
            "box": self.config["box"],
            "cls": self.config["cls"],
            "dfl": self.config["dfl"],
            "pose": self.config["pose"],
            "kobj": self.config["kobj"],
            "label_smoothing": self.config["label_smoothing"],
            "nbs": self.config["nbs"],
            "hsv_h": self.config["hsv_h"],
            "hsv_s": self.config["hsv_s"],
            "hsv_v": self.config["hsv_v"],
            "degrees": self.config["degrees"],
            "translate": self.config["translate"],
            "scale": self.config["scale"],
            "shear": self.config["shear"],
            "perspective": self.config["perspective"],
            "flipud": self.config["flipud"],
            "fliplr": self.config["fliplr"],
            "mosaic": self.config["mosaic"],
            "mixup": self.config["mixup"],
            "copy_paste": self.config["copy_paste"]
        }
        
        try:
            logger.info(f"Training configuration:")
            logger.info(f"  • Model: {self.config['model_name']}")
            logger.info(f"  • Dataset: {self.config['dataset_yaml']}")
            logger.info(f"  • Epochs: {self.config['epochs']}")
            logger.info(f"  • Batch size: {self.config['batch']}")
            logger.info(f"  • Image size: {self.config['imgsz']}")
            logger.info(f"  • Device: {self.config['device']}")
            
            # Start training
            results = self.model.train(**train_args)
            
            # Get model path
            model_path = f"{self.config['project']}/{self.config['name']}/weights/best.pt"
            
            if Path(model_path).exists():
                logger.info(f"✅ Training completed successfully!")
                logger.info(f"📁 Model saved to: {model_path}")
                
                # Copy to models directory for easy access
                models_dir = Path("models")
                models_dir.mkdir(exist_ok=True)
                import shutil
                shutil.copy2(model_path, models_dir / "drone_yolo_best.pt")
                logger.info(f"📁 Model also copied to: models/drone_yolo_best.pt")
                
                return model_path
            else:
                logger.error(f"❌ Model file not found: {model_path}")
                return None
                
        except KeyboardInterrupt:
            logger.info("Training interrupted by user")
            return None
        except Exception as e:
            logger.error(f"❌ Training failed: {e}")
            return None
    
    def evaluate_model(self, model_path: str) -> Dict:
        """Evaluate trained model"""
        logger.info(f"Evaluating model: {model_path}")
        
        try:
            # Load trained model
            model = YOLO(model_path)
            
            # Run validation
            results = model.val(
                data=self.config["dataset_yaml"],
                imgsz=self.config["imgsz"],
                batch=self.config["batch"],
                device=self.config["device"]
            )
            
            # Extract metrics
            metrics = {
                "map50": results.box.map50,  # mAP@0.5
                "map50_95": results.box.map,  # mAP@0.5:0.95
                "precision": results.box.mp,
                "recall": results.box.mr,
                "fitness": results.box.fitness
            }
            
            logger.info(f"Evaluation Results:")
            logger.info(f"  • mAP@0.5: {metrics['map50']:.4f}")
            logger.info(f"  • mAP@0.5:0.95: {metrics['map50_95']:.4f}")
            logger.info(f"  • Precision: {metrics['precision']:.4f}")
            logger.info(f"  • Recall: {metrics['recall']:.4f}")
            logger.info(f"  • Fitness: {metrics['fitness']:.4f}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"❌ Evaluation failed: {e}")
            return {}
    
    def export_model(self, model_path: str, format: str = "onnx") -> Optional[str]:
        """Export model to different formats"""
        logger.info(f"Exporting model to {format}: {model_path}")
        
        try:
            model = YOLO(model_path)
            
            # Export model
            exported_path = model.export(format=format, imgsz=self.config["imgsz"])
            
            logger.info(f"✅ Model exported to: {exported_path}")
            return exported_path
            
        except Exception as e:
            logger.error(f"❌ Export failed: {e}")
            return None

def quick_test():
    """Quick test of the training system"""
    logger.info("Running quick YOLO training test...")
    
    config = {
        "model_name": "yolov8n.pt",
        "dataset_yaml": "dataset.yaml",
        "epochs": 5,  # Very short test
        "imgsz": 320,  # Smaller images for faster training
        "batch": 8,
        "patience": 3,
        "device": "cpu"
    }
    
    trainer = DroneYOLOTrainer(config)
    model_path = trainer.train()
    
    if model_path:
        # Quick evaluation
        metrics = trainer.evaluate_model(model_path)
        logger.info(f"Quick test metrics: {metrics}")
    
    return model_path

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Train Drone YOLO Model")
    parser.add_argument("--test", action="store_true", help="Run quick test")
    parser.add_argument("--model", type=str, default="yolov8n.pt", help="Base model name")
    parser.add_argument("--epochs", type=int, default=100, help="Number of epochs")
    parser.add_argument("--batch", type=int, default=16, help="Batch size")
    parser.add_argument("--device", type=str, default="cpu", help="Device (cpu or 0 for GPU)")
    parser.add_argument("--dataset", type=str, default="dataset.yaml", help="Dataset configuration")
    
    args = parser.parse_args()
    
    if args.test:
        quick_test()
    else:
        config = {
            "model_name": args.model,
            "dataset_yaml": args.dataset,
            "epochs": args.epochs,
            "batch": args.batch,
            "device": args.device
        }
        
        trainer = DroneYOLOTrainer(config)
        model_path = trainer.train()
        
        if model_path:
            # Evaluate trained model
            metrics = trainer.evaluate_model(model_path)
            
            # Export to ONNX for deployment
            onnx_path = trainer.export_model(model_path, "onnx")
        
        logger.info("🎉 YOLO training process completed!")
