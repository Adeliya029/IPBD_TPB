# 🤖 Models Package

Package ini berisi implementasi Machine Learning untuk deteksi anomali cuaca.

## 📁 Struktur

```
models/
├── __init__.py          # Package initialization
├── ml_model.py          # Model implementation (Isolation Forest)
├── saved/               # Direktori untuk saved models
│   └── anomaly_detector.pkl  # Trained model (auto-generated)
└── README.md
```

## 🚀 Penggunaan

### Training Model

```python
from models import train_initial_model

# Train model pertama kali
detector = train_initial_model()
```

### Load & Predict

```python
from models import WeatherAnomalyDetector

# Load model
detector = WeatherAnomalyDetector()
detector.load_model()

# Predict
weather_data = {
    'temperature': 28.5,
    'windspeed': 12.3
}

prediction = detector.predict(weather_data)
print(f"Anomaly: {prediction['is_anomaly']}")
print(f"Score: {prediction['anomaly_score']}")
print(f"Confidence: {prediction['confidence']}")
```

## 📊 Model Details

- **Algorithm**: Isolation Forest
- **Features**: temperature, windspeed
- **Output**: is_anomaly, anomaly_score, confidence
