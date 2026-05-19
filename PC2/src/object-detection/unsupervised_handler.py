import os
import pickle
import numpy as np
import torch
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image
import logging

logger = logging.getLogger(__name__)

class UnsupervisedHandler:
    """
    Handles inference using models trained in the Colab notebook.
    Uses ResNet50 for feature extraction and K-Means for clustering.
    """
    
    def __init__(self, model_dir: str = "/app/models/unsupervised"):
        self.model_dir = model_dir
        self.kmeans = None
        self.pca = None
        self.scaler = None
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        # Feature extractor (ResNet50)
        self.feature_extractor = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)
        self.feature_extractor.fc = torch.nn.Identity()
        self.feature_extractor.eval()
        self.feature_extractor.to(self.device)
        
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        
        self.load_models()

    def load_models(self):
        """Load K-Means, PCA, and Scaler from pickles"""
        try:
            kmeans_path = os.path.join(self.model_dir, 'cluster_model.pkl')
            pca_path    = os.path.join(self.model_dir, 'pca_model.pkl')
            scaler_path = os.path.join(self.model_dir, 'scaler.pkl')
            
            if all(os.path.exists(p) for p in [kmeans_path, pca_path, scaler_path]):
                with open(kmeans_path, 'rb') as f: self.kmeans = pickle.load(f)
                with open(pca_path,    'rb') as f: self.pca    = pickle.load(f)
                with open(scaler_path, 'rb') as f: self.scaler = pickle.load(f)
                logger.info(f"Unsupervised models loaded successfully from {self.model_dir}")
            else:
                logger.warning(f"Unsupervised models not found in {self.model_dir}. Run the Colab notebook first.")
        except Exception as e:
            logger.error(f"Error loading unsupervised models: {e}")

    def classify(self, image: np.ndarray) -> dict:
        """
        Classify a single image into a cluster.
        Args:
            image: BGR numpy array (OpenCV format)
        """
        if self.kmeans is None:
            return {"error": "Models not loaded"}
            
        try:
            # Convert to PIL and preprocess
            import cv2
            img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            img_pil = Image.fromarray(img_rgb)
            img_tensor = self.transform(img_pil).unsqueeze(0).to(self.device)
            
            # Extract features
            with torch.no_grad():
                features = self.feature_extractor(img_tensor).squeeze().cpu().numpy()
            
            # Scale and reduce
            features_scaled = self.scaler.transform(features.reshape(1, -1))
            features_reduced = self.pca.transform(features_scaled)
            
            # Predict
            cluster_id = int(self.kmeans.predict(features_reduced)[0])
            
            # Simple confidence proxy (inverse of distance to centroid)
            distances = np.linalg.norm(features_reduced - self.kmeans.cluster_centers_, axis=1)
            confidence = 1.0 / (1.0 + distances[cluster_id])
            
            return {
                "cluster_id": cluster_id,
                "confidence": float(confidence),
                "model_type": "unsupervised"
            }
        except Exception as e:
            logger.error(f"Unsupervised classification error: {e}")
            return {"error": str(e)}

    @property
    def is_ready(self):
        return self.kmeans is not None
