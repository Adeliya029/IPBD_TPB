"""
Machine Learning Model untuk Prediksi Anomali Cuaca
Menggunakan Isolation Forest untuk deteksi anomali temperature dan windspeed
"""

import pickle
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class WeatherAnomalyDetector:
    """Model ML untuk deteksi anomali cuaca"""
    
    def __init__(self, model_path='models/saved/anomaly_detector.pkl'):
        self.model_path = model_path
        self.model = None
        self.scaler = StandardScaler()
        self.is_trained = False
        
    def train(self, training_data):
        """
        Training model dengan data historis
        Args:
            training_data: List of dict dengan keys: temperature, windspeed
        """
        logger.info("Starting model training...")
        
        # Prepare features
        features = np.array([
            [d['temperature'], d['windspeed']] 
            for d in training_data
        ])
        
        # Scale features
        features_scaled = self.scaler.fit_transform(features)
        
        # Train Isolation Forest
        self.model = IsolationForest(
            contamination=0.1,  # 10% data dianggap anomali
            random_state=42,
            n_estimators=100
        )
        self.model.fit(features_scaled)
        self.is_trained = True
        
        logger.info(f"Model trained with {len(training_data)} samples")
        
        # Save model
        self.save_model()
        
        return self
    
    def predict(self, weather_data):
        """
        Prediksi apakah data cuaca anomali
        Args:
            weather_data: Dict dengan keys: temperature, windspeed
        Returns:
            dict: {
                'is_anomaly': bool,
                'anomaly_score': float,
                'confidence': float
            }
        """
        if not self.is_trained:
            logger.warning("Model not trained, loading from file...")
            self.load_model()
        
        # Prepare features
        features = np.array([[
            weather_data['temperature'],
            weather_data['windspeed']
        ]])
        
        # Scale
        features_scaled = self.scaler.transform(features)
        
        # Predict
        prediction = self.model.predict(features_scaled)[0]
        anomaly_score = self.model.score_samples(features_scaled)[0]
        
        # -1 = anomaly, 1 = normal
        is_anomaly = prediction == -1
        
        # Convert score to confidence (0-1)
        confidence = 1 / (1 + np.exp(anomaly_score))
        
        result = {
            'is_anomaly': bool(is_anomaly),
            'anomaly_score': float(anomaly_score),
            'confidence': float(confidence),
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"Prediction: {result}")
        return result
    
    def save_model(self):
        """Save model ke disk"""
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'is_trained': self.is_trained,
            'timestamp': datetime.now().isoformat()
        }
        
        with open(self.model_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        logger.info(f"Model saved to {self.model_path}")
    
    def load_model(self):
        """Load model dari disk"""
        if not os.path.exists(self.model_path):
            logger.error(f"Model file not found: {self.model_path}")
            raise FileNotFoundError(f"Model not found: {self.model_path}")
        
        with open(self.model_path, 'rb') as f:
            model_data = pickle.load(f)
        
        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.is_trained = model_data['is_trained']
        
        logger.info(f"Model loaded from {self.model_path}")
        return self


# Training script
def train_initial_model():
    """Script untuk training model pertama kali"""
    logger.info("Generating synthetic training data...")
    
    # Generate synthetic training data (normal weather patterns)
    np.random.seed(42)
    training_data = []
    
    # Jakarta: 25-33°C, 5-20 km/h
    for _ in range(200):
        training_data.append({
            'temperature': np.random.normal(29, 2),
            'windspeed': np.random.normal(12, 4)
        })
    
    # Surabaya: 26-34°C, 8-25 km/h
    for _ in range(200):
        training_data.append({
            'temperature': np.random.normal(30, 2.5),
            'windspeed': np.random.normal(15, 5)
        })
    
    # Bandung: 20-28°C, 3-15 km/h
    for _ in range(200):
        training_data.append({
            'temperature': np.random.normal(24, 2),
            'windspeed': np.random.normal(9, 3)
        })
    
    # Medan: 24-32°C, 5-18 km/h
    for _ in range(200):
        training_data.append({
            'temperature': np.random.normal(28, 2),
            'windspeed': np.random.normal(11, 3.5)
        })
    
    # Makassar: 25-33°C, 10-30 km/h
    for _ in range(200):
        training_data.append({
            'temperature': np.random.normal(29, 2.5),
            'windspeed': np.random.normal(18, 6)
        })
    
    # Train model
    detector = WeatherAnomalyDetector()
    detector.train(training_data)
    
    logger.info("Initial model training completed!")
    return detector


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Train initial model
    train_initial_model()
