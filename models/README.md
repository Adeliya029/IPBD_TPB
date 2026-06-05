# 🤖 Models Package

Package ini berisi implementasi Machine Learning untuk sistem prediksi harga pangan.

## 📁 Struktur

```
models/
├── __init__.py                    # Package initialization
├── ml_model.py                    # Anomaly Detection Model (Legacy)
├── price_prediction_model.py     # ⭐ Food Price Prediction Model (MAIN)
├── saved/                         # Direktori untuk saved models
│   ├── anomaly_detector.pkl      # Old model
│   └── food_price_predictor.pkl  # New model (auto-generated)
└── README.md
```

## 🎯 Model Utama: Food Price Prediction

Model ini memprediksi **perubahan harga pangan** berdasarkan **kondisi cuaca**.

### Business Goal
Membantu stakeholder (konsumen, petani, distributor) untuk:
- 📊 Memprediksi apakah harga pangan akan NAIK, TURUN, atau STABIL
- 🌦️ Memahami pengaruh cuaca terhadap harga pangan
- 💡 Mendapatkan rekomendasi aksi berdasarkan prediksi

### Target Prediksi

| Kategori | Kriteria | Makna |
|----------|----------|-------|
| 🔺 NAIK | Perubahan > 2% | Harga akan naik signifikan |
| ➡️ STABIL | -2% ≤ Perubahan ≤ 2% | Harga relatif tidak berubah |
| 🔻 TURUN | Perubahan < -2% | Harga akan turun signifikan |

### Features yang Digunakan

Model menggunakan 11 features cuaca:

**Current Weather:**
1. `suhu_mean` - Suhu rata-rata (°C)
2. `suhu_max` - Suhu maksimum (°C)
3. `suhu_min` - Suhu minimum (°C)
4. `curah_hujan_mm` - Curah hujan (mm)
5. `kelembapan` - Kelembapan udara (%)
6. `kecepatan_angin` - Kecepatan angin (km/h)
7. `tekanan_udara` - Tekanan udara (hPa)
8. `awan_persen` - Tutupan awan (%)

**Historical Features (Lag):**
9. `curah_hujan_lag_1d` - Hujan 1 hari lalu
10. `curah_hujan_lag_3d` - Hujan 3 hari lalu
11. `curah_hujan_lag_7d` - Hujan 7 hari lalu

### Algoritma

- **Model**: Gradient Boosting Classifier
- **Hyperparameters**:
  - n_estimators: 200
  - learning_rate: 0.1
  - max_depth: 5
- **Why Gradient Boosting?**
  - Excellent untuk classification problems
  - Handle non-linear relationships
  - Feature importance analysis
  - Robust terhadap outliers

## 🚀 Penggunaan

### Training Model

**Option 1: Train dari Data CSV**
```python
from models import FoodPricePredictionModel

predictor = FoodPricePredictionModel()
predictor.train_from_csv(
    weather_csv_path='data/processed/cuaca/cuaca_openmeteo_minggu_01_20260101_20260107.csv',
    price_csv_path='data/processed/harga/harga_jawa_jan_mei_2026.csv'
)
```

**Option 2: Train dari Script**
```python
from models import train_model_from_data

# Automatically finds and trains from data files
predictor = train_model_from_data()
```

**Option 3: Synthetic Data (untuk testing)**
```python
from models import train_synthetic_model

# Uses synthetic data based on weather-price patterns
predictor = train_synthetic_model()
```

### Load & Predict

```python
from models import FoodPricePredictionModel

# Load model
predictor = FoodPricePredictionModel()
predictor.load_model()

# Predict
weather_data = {
    'suhu_mean': 25.5,
    'curah_hujan_mm': 85.0,
    'kelembapan': 92.0,
    'kecepatan_angin': 18.0,
    'tekanan_udara': 1008.0,
    'awan_persen': 95.0,
    'suhu_max': 28.0,
    'suhu_min': 23.0
}

historical_rain = {
    'lag_1d': 75.0,
    'lag_3d': 60.0,
    'lag_7d': 50.0
}

prediction = predictor.predict(weather_data, historical_rain)

print(f"Prediksi: {prediction['prediction']}")
print(f"Confidence: {prediction['confidence']:.1%}")
print(f"\n{prediction['recommendation']}")
```

### Output Example

```json
{
  "prediction": "NAIK",
  "prediction_code": 2,
  "confidence": 0.87,
  "probabilities": {
    "TURUN": 0.05,
    "STABIL": 0.08,
    "NAIK": 0.87
  },
  "recommendation": "⚠️ PREDIKSI HARGA NAIK (Confidence: 87.0%)\nRekomendasi:\n- Konsumen: Pertimbangkan untuk membeli kebutuhan pangan lebih awal\n- Petani: Waktu yang baik untuk menjual hasil panen\n- Distributor: Antisipasi peningkatan permintaan\n⚠️ Curah hujan tinggi (85.0 mm) - Potensi gangguan distribusi",
  "weather_summary": "Suhu: 25.5°C, Hujan: 85.0 mm, Kelembapan: 92.0%",
  "timestamp": "2026-06-05T10:30:45.123456"
}
```

## 📊 Model Performance

Model di-evaluate dengan metrics:
- **Accuracy**: Overall prediction accuracy
- **Precision/Recall/F1-Score** per class
- **Confusion Matrix**: Melihat misclassification
- **Feature Importance**: Features yang paling berpengaruh

## 🔄 Model Retraining

Best Practice:
- Retrain setiap **1 bulan** dengan data aktual
- Minimal **1000 samples** untuk good performance
- Monitor model drift dan accuracy degradation
- Update jika accuracy < 70%

## 🧪 Testing

Run test script:
```bash
python models/price_prediction_model.py
```
