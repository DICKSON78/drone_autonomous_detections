#!/usr/bin/env python3
"""
Auto-Label Module for Drone Object Detection
Tumia YOLO pretrained kuzalisha labels kwa picha zako
"""

from ultralytics import YOLO
import os
import shutil
import random
import json
import logging
from pathlib import Path
from typing import List, Dict, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DroneAutoLabeler:
    """Class for auto-labeling drone images using pretrained YOLO"""
    
    def __init__(self, config: Dict = None):
        self.config = config or self._default_config()
        self.model = None
        self.setup_directories()
        
    def _default_config(self) -> Dict:
        """Default configuration for auto-labeling"""
        return {
            "kaggle_dir": "/path/to/your/kaggle/images",  # Badilisha hapa
            "dataset_dir": "data",
            "confidence": 0.35,
            "train_split": 0.8,
            "supported_formats": [".png", ".jpg", ".jpeg"],
        }
    
    def setup_directories(self):
        """Create necessary directories"""
        dirs = [
            self.config["dataset_dir"],
            f"{self.config['dataset_dir']}/images/train",
            f"{self.config['dataset_dir']}/images/val", 
            f"{self.config['dataset_dir']}/labels/train",
            f"{self.config['dataset_dir']}/labels/val"
        ]
        
        for dir_path in dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {dir_path}")
    
    @property
    def classes_map(self) -> Dict[int, str]:
        """COCO class ids → drone class ids"""
        return {
            0:  "person",    # mtu
            2:  "vehicle",   # gari
            3:  "vehicle",   # motorcycle
            5:  "vehicle",   # bus
            7:  "vehicle",   # truck
            4:  "aircraft",  # airplane
            14: "aircraft",  # bird
        }
    
    @property
    def class_names(self) -> List[str]:
        """Drone-specific class names"""
        return ["tree", "building", "pole", "person", "vehicle", "aircraft"]
    
    def load_model(self, model_name: str = "yolov8x.pt"):
        """Load YOLO model"""
        try:
            self.model = YOLO(model_name)
            logger.info(f"YOLO model {model_name} loaded successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            return False
    
    def split_images(self) -> Tuple[List[str], List[str]]:
        """Gawanya picha 80% train, 20% val"""
        kaggle_dir = self.config["kaggle_dir"]
        
        if not os.path.exists(kaggle_dir):
            logger.error(f"Kaggle directory not found: {kaggle_dir}")
            return [], []
        
        images = sorted([
            f for f in os.listdir(kaggle_dir)
            if any(f.lower().endswith(ext) for ext in self.config["supported_formats"])
        ])
        
        if not images:
            logger.error("No images found in Kaggle directory")
            return [], []
        
        random.seed(42)
        random.shuffle(images)
        split_idx = int(len(images) * self.config["train_split"])
        
        train_images = images[:split_idx]
        val_images = images[split_idx:]
        
        # Copy images to respective directories
        for img_list, split_name in [(train_images, "train"), (val_images, "val")]:
            for img in img_list:
                src_path = os.path.join(kaggle_dir, img)
                dst_path = os.path.join(
                    self.config["dataset_dir"], 
                    "images", 
                    split_name, 
                    img
                )
                shutil.copy2(src_path, dst_path)
        
        logger.info(f"✅ Train: {len(train_images)} | Val: {len(val_images)}")
        return train_images, val_images
    
    def auto_label_split(self, split: str = "train") -> int:
        """Tumia YOLOv8 pretrained kuzalisha labels"""
        if not self.model:
            if not self.load_model():
                return 0
        
        imgs_dir = os.path.join(self.config["dataset_dir"], "images", split)
        lbls_dir = os.path.join(self.config["dataset_dir"], "labels", split)
        
        if not os.path.exists(imgs_dir):
            logger.error(f"Images directory not found: {imgs_dir}")
            return 0
        
        images = sorted(os.listdir(imgs_dir))
        labeled_count = 0
        
        logger.info(f"Starting auto-labeling for {split} split ({len(images)} images)")
        
        for i, img_file in enumerate(images):
            img_path = os.path.join(imgs_dir, img_file)
            label_path = os.path.join(lbls_dir, os.path.splitext(img_file)[0] + ".txt")
            
            try:
                # Run YOLO prediction
                results = self.model.predict(img_path, conf=self.config["confidence"], verbose=False)
                detections = []
                
                # Process detections
                for box in results[0].boxes:
                    cls_id = int(box.cls)
                    if cls_id not in self.classes_map:
                        continue
                    
                    class_name = self.classes_map[cls_id]
                    if class_name not in self.class_names:
                        continue
                    
                    new_cls = self.class_names.index(class_name)
                    x, y, w, h = box.xywhn[0].tolist()
                    detections.append(f"{new_cls} {x:.6f} {y:.6f} {w:.6f} {h:.6f}")
                
                # Save labels
                with open(label_path, "w") as f:
                    f.write("\n".join(detections))
                
                if detections:
                    labeled_count += 1
                
                # Progress update
                if (i + 1) % 100 == 0:
                    logger.info(f"  [{split}] {i+1}/{len(images)} | Labeled: {labeled_count}")
                    
            except Exception as e:
                logger.error(f"Error processing {img_file}: {e}")
                continue
        
        logger.info(f"✅ {split} complete - {labeled_count}/{len(images)} images have detections")
        return labeled_count
    
    def create_dataset_yaml(self):
        """Create dataset.yaml configuration"""
        yaml_content = f"""# Drone Dataset Configuration
path: ./{self.config['dataset_dir']}
train: images/train
val: images/val

nc: {len(self.class_names)}
names:
"""
        for i, name in enumerate(self.class_names):
            yaml_content += f"  {i}: {name}\n"
        
        yaml_path = os.path.join(self.config["dataset_dir"], "dataset.yaml")
        with open(yaml_path, "w") as f:
            f.write(yaml_content)
        
        logger.info(f"✅ Dataset configuration saved to: {yaml_path}")
        return yaml_path
    
    def generate_label_statistics(self) -> Dict:
        """Generate statistics about labeled dataset"""
        stats = {"total_images": 0, "total_labels": 0, "class_distribution": {}}
        
        for split in ["train", "val"]:
            labels_dir = os.path.join(self.config["dataset_dir"], "labels", split)
            if not os.path.exists(labels_dir):
                continue
            
            label_files = [f for f in os.listdir(labels_dir) if f.endswith(".txt")]
            stats[f"{split}_images"] = len(label_files)
            stats["total_images"] += len(label_files)
            
            for label_file in label_files:
                label_path = os.path.join(labels_dir, label_file)
                try:
                    with open(label_path, "r") as f:
                        lines = f.readlines()
                        stats["total_labels"] += len(lines)
                        
                        for line in lines:
                            if line.strip():
                                class_id = int(line.split()[0])
                                class_name = self.class_names[class_id] if class_id < len(self.class_names) else "unknown"
                                stats["class_distribution"][class_name] = stats["class_distribution"].get(class_name, 0) + 1
                except Exception as e:
                    logger.error(f"Error reading {label_file}: {e}")
        
        return stats
    
    def run_full_pipeline(self) -> Dict:
        """Run complete auto-labeling pipeline"""
        logger.info("🚁 Starting Auto-Labeling Pipeline...")
        
        # Step 1: Load model
        if not self.load_model():
            return {"status": "error", "message": "Failed to load YOLO model"}
        
        # Step 2: Split images
        train_imgs, val_imgs = self.split_images()
        if not train_imgs and not val_imgs:
            return {"status": "error", "message": "No images found"}
        
        # Step 3: Auto-label train split
        train_labeled = self.auto_label_split("train")
        
        # Step 4: Auto-label validation split  
        val_labeled = self.auto_label_split("val")
        
        # Step 5: Create dataset.yaml
        yaml_path = self.create_dataset_yaml()
        
        # Step 6: Generate statistics
        stats = self.generate_label_statistics()
        
        result = {
            "status": "success",
            "train_images": len(train_imgs),
            "val_images": len(val_imgs),
            "train_labeled": train_labeled,
            "val_labeled": val_labeled,
            "total_labels": stats["total_labels"],
            "class_distribution": stats["class_distribution"],
            "dataset_yaml": yaml_path
        }
        
        logger.info(f"✅ Auto-labeling complete! {result}")
        return result

if __name__ == "__main__":
    # Example usage
    config = {
        "kaggle_dir": "/path/to/your/drone/images",  # Badilisha hapa
        "dataset_dir": "data",
        "confidence": 0.35,
        "train_split": 0.8
    }
    
    labeler = DroneAutoLabeler(config)
    result = labeler.run_full_pipeline()
    
    if result["status"] == "success":
        print("🎉 Auto-labeling completed successfully!")
        print(f"Train: {result['train_labeled']}/{result['train_images']} labeled")
        print(f"Val: {result['val_labeled']}/{result['val_images']} labeled")
        print(f"Total labels: {result['total_labels']}")
    else:
        print(f"❌ Error: {result['message']}")
