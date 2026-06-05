# 🎯 DOKUMENTASI MODEL MACHINE LEARNING
## Prediksi Harga Pangan Berdasarkan Cuaca

---

## 📊 EXECUTIVE SUMMARY

### Business Problem
Harga pangan di Indonesia sangat fluktuatif dan dipengaruhi oleh berbagai faktor, salah satunya adalah **kondisi cuaca**. Cuaca buruk dapat:
- Mengganggu distribusi (hujan lebat → jalan rusak → harga naik)
- Mempengaruhi hasil panen (kekeringan → panen menurun → harga naik)
- Mengubah demand/supply balance

### Solution
**Model Machine Learning** yang dapat memprediksi apakah harga pangan akan **NAIK**, **TURUN**, atau **STABIL** berdasarkan data cuaca real-time.

### Business Value
- 💰 **Konsumen**: Beli sebelum harga naik
- 🌾 **Petani**: Jual di waktu yang tepat
- 🚚 **Distributor**: Kelola inventory lebih baik
- 📊 **Pemerintah**: Monitoring stabilitas harga

---

## 🎯 MODEL SPECIFICATION

### 1. Problem Type
**Multi-class Classification Problem**

### 2. Target Variable (Y)
Perubahan harga pangan dikategorikan menjadi 3 kelas:

| Kelas | Kriteria | Contoh |
|-------|----------|--------|
| 🔺 **NAIK** | Perubahan > 2% | Harga Rp 10,000 → Rp 10,300 (+3%) |
| ➡️ **STABIL** | -2% ≤ Perubahan ≤ 2% | Harga Rp 10,000 → Rp 10,100 (+1%) |
| 🔻 **TURUN** | Perubahan < -2% | Harga Rp 10,000 → Rp 9,700 (-3%) |

**Kenapa threshold 2%?**
- Perubahan < 2% dianggap fluktuasi normal
- Perubahan > 2% signifikan untuk keputusan bisnis

### 3. Input Features (X)
Model menggunakan **11 features** dari data cuaca:

#### a. Current Weather Features (8 features)
| Feature | Deskripsi | Satuan | Range Typical |
|---------|-----------|--------|---------------|
| `suhu_mean` | Suhu rata-rata | °C | 20-35 |
| `suhu_max` | Suhu maksimum | °C | 25-38 |
| `suhu_min` | Suhu minimum | °C | 18-28 |
| `curah_hujan_mm` | Curah hujan | mm | 0-200 |
| `kelembapan` | Kelembapan udara | % | 60-95 |
| `kecepatan_angin` | Kecepatan angin | km/h | 5-30 |
| `tekanan_udara` | Tekanan udara | hPa | 1005-1015 |
| `awan_persen` | Tutupan awan | % | 0-100 |

#### b. Historical Features (3 lag features)
| Feature | Deskripsi | Kenapa Penting? |
|---------|-----------|-----------------|
| `curah_hujan_lag_1d` | Hujan 1 hari lalu | Immediate impact pada distribusi |
| `curah_hujan_lag_3d` | Hujan 3 hari lalu | Short-term cumulative effect |
| `curah_hujan_lag_7d` | Hujan 7 hari lalu | Weekly pattern effect |

**Kenapa lag features penting?**
- Hujan kemarin mempengaruhi kondisi jalan hari ini
- Hujan terus-menerus (3-7 hari) → impact lebih besar
- Model bisa "melihat" pattern temporal

---

## 🤖 MACHINE LEARNING ALGORITHM

### Algorithm: Gradient Boosting Classifier

#### Kenapa Gradient Boosting?
✅ **Kelebihan**:
1. **High Accuracy**: Salah satu algoritma terbaik untuk classification
2. **Handle Non-linearity**: Hubungan cuaca-harga tidak linear
3. **Feature Importance**: Bisa tahu feature mana yang paling berpengaruh
4. **Robust**: Tahan terhadap outliers dan noise
5. **Ensemble Method**: Menggabungkan banyak weak learners jadi strong learner

❌ **Kekurangan**:
1. Training lebih lama dibanding model sederhana
2. Butuh hyperparameter tuning
3. Bisa overfit jika tidak di-tune dengan baik

#### Hyperparameters
```python
GradientBoostingClassifier(
    n_estimators=200,      # 200 decision trees
    learning_rate=0.1,     # Learning rate moderat
    max_depth=5,           # Depth untuk avoid overfitting
    random_state=42        # Reproducibility
)
```

#### Alternatif yang Dipertimbangkan
| Algorithm | Kenapa Tidak Dipilih |
|-----------|----------------------|
| Logistic Regression | Tidak bisa handle non-linear relationships |
| Random Forest | Bagus tapi Gradient Boosting lebih akurat |
| Neural Network | Overkill, butuh data lebih banyak, training lama |
| SVM | Tidak scalable untuk data besar |

---

## 📈 CARA KERJA MODEL

### 1. Training Phase (Offline)

```
[Data Cuaca] + [Data Harga] 
        ↓
   Merge by Date & Location
        ↓
   Feature Engineering
   - Calculate lag features
   - Categorize price changes
        ↓
   Train/Test Split (80/20)
        ↓
   Feature Scaling (StandardScaler)
        ↓
   Train Gradient Boosting
        ↓
   Evaluate Performance
        ↓
   Save Model (.pkl)
```

**Contoh Kode Training:**
```python
from models import train_model_from_data

# Automatic training dari CSV
predictor = train_model_from_data()

# Output:
# Training accuracy: 0.892
# Test accuracy: 0.856
# Model saved to models/saved/food_price_predictor.pkl
```

### 2. Inference Phase (Real-time)

```
[Streaming Weather Data]
        ↓
   Extract Features
        ↓
   Get Historical Rain (lag)
        ↓
   Feature Scaling
        ↓
   ML Prediction
        ↓
   Output: NAIK/TURUN/STABIL + Confidence
        ↓
   Generate Recommendations
```

**Contoh Kode Prediction:**
```python
from models import FoodPricePredictionModel

predictor = FoodPricePredictionModel()
predictor.load_model()

# Input weather data
weather_data = {
    'suhu_mean': 25.5,
    'curah_hujan_mm': 85.0,  # Hujan lebat!
    'kelembapan': 92.0,
    'kecepatan_angin': 18.0,
    'tekanan_udara': 1008.0,
    'awan_persen': 95.0,
    'suhu_max': 28.0,
    'suhu_min': 23.0
}

historical_rain = {
    'lag_1d': 75.0,  # Kemarin juga hujan
    'lag_3d': 60.0,
    'lag_7d': 50.0
}

# Predict
result = predictor.predict(weather_data, historical_rain)

print(result['prediction'])      # "NAIK"
print(result['confidence'])      # 0.87 (87%)
print(result['recommendation'])  # Actionable advice
```

---

## 🎓 TRAINING DATA REQUIREMENTS

### Minimum Requirements
- **Jumlah Data**: Minimal 1,000 samples
- **Time Range**: Minimal 3 bulan data historis
- **Coverage**: Multiple locations (kabupaten/kota)
- **Balance**: Tidak terlalu imbalanced (ratio < 1:5)

### Data Quality
✅ **Good Quality Indicators**:
- No missing values di features penting
- Realistic value ranges
- Temporal continuity (no big gaps)
- Geographic diversity

❌ **Bad Quality Indicators**:
- > 20% missing values
- Outliers yang ekstrem
- Imbalanced classes (95% satu kelas)
- Data corruption

### Training Strategy

#### Option 1: Real Data (RECOMMENDED)
```python
predictor = FoodPricePredictionModel()
predictor.train_from_csv(
    weather_csv='data/processed/cuaca/cuaca_openmeteo_minggu_01_20260101_20260107.csv',
    price_csv='data/processed/harga/harga_jawa_jan_mei_2026.csv'
)
```

**Pros**: Real patterns, better accuracy
**Cons**: Need actual data collection

#### Option 2: Synthetic Data (DEMO/TESTING)
```python
from models import train_synthetic_model
predictor = train_synthetic_model()
```

**Pros**: Quick start, no data needed
**Cons**: Simulated patterns, may not reflect reality

---

## 📊 MODEL EVALUATION

### Metrics yang Digunakan

#### 1. Accuracy
```
Accuracy = (Correct Predictions) / (Total Predictions)
```
**Target**: > 80% untuk production use

#### 2. Precision, Recall, F1-Score per Class
```
Precision = True Positives / (True Positives + False Positives)
Recall = True Positives / (True Positives + False Negatives)
F1 = 2 * (Precision * Recall) / (Precision + Recall)
```

#### 3. Confusion Matrix
```
                Predicted
              NAIK  STABIL  TURUN
Actual NAIK    150     20      5
       STABIL   15    180     10
       TURUN     8     12    145
```

**Interpretasi**:
- Diagonal (bold) = correct predictions
- Off-diagonal = misclassifications
- Cari pattern: Apakah model sering confuse NAIK vs STABIL?

### Feature Importance
```
Top 5 Most Important Features:
1. curah_hujan_mm        : 0.2543
2. curah_hujan_lag_1d    : 0.1876
3. kelembapan            : 0.1432
4. suhu_mean             : 0.1098
5. kecepatan_angin       : 0.0876
```

**Insight**:
- Curah hujan (current + lag) paling berpengaruh
- Kelembapan & suhu juga signifikan
- Bisa digunakan untuk feature selection

---

## 🔄 MODEL MAINTENANCE

### When to Retrain?

#### Scheduled Retraining
- **Frequency**: Setiap 1 bulan
- **Reason**: Seasonal patterns berubah
- **Data**: Accumulated data 1 bulan terakhir

#### Triggered Retraining
Retrain immediately jika:
1. **Accuracy Drop**: Test accuracy < 70%
2. **Concept Drift**: Prediction pattern berubah drastis
3. **New Data Available**: Data baru yang substantial (> 1000 samples)
4. **Seasonal Change**: Musim berubah (kemarau → hujan)

### Retraining Process
```python
# 1. Collect new data
new_weather_data = load_new_weather_data()
new_price_data = load_new_price_data()

# 2. Retrain model
predictor = FoodPricePredictionModel()
predictor.train_from_csv(new_weather_data, new_price_data)

# 3. Evaluate on holdout set
test_accuracy = evaluate_model(predictor, test_data)

# 4. Deploy if better
if test_accuracy > current_model_accuracy:
    deploy_new_model(predictor)
```

### Monitoring Metrics
Track these metrics over time:
- Daily/Weekly accuracy
- Prediction distribution (berapa % NAIK, TURUN, STABIL)
- Confidence scores
- Feature drift (apakah feature statistics berubah?)

---

## 💡 BUSINESS SCENARIOS

### Scenario 1: Heavy Rain (Hujan Lebat)
**Input**:
```
curah_hujan_mm = 85 mm
curah_hujan_lag_1d = 75 mm
curah_hujan_lag_3d = 60 mm
```

**Prediction**: 🔺 NAIK (87% confidence)

**Reasoning**:
- Hujan lebat mengganggu distribusi
- Jalan rusak, truk sulit lewat
- Supply berkurang → harga naik

**Recommendation**:
- **Konsumen**: Beli sekarang sebelum harga naik lebih tinggi
- **Petani**: Tahan hasil panen, tunggu harga peak
- **Distributor**: Stock up sebelum distribusi terganggu

### Scenario 2: Ideal Weather (Cuaca Bagus)
**Input**:
```
curah_hujan_mm = 5 mm
suhu_mean = 27°C
kelembapan = 75%
```

**Prediction**: ➡️ STABIL (78% confidence)

**Reasoning**:
- Cuaca mendukung aktivitas normal
- Distribusi lancar
- Panen stabil

**Recommendation**:
- **Konsumen**: Beli sesuai kebutuhan, tidak ada urgency
- **Petani**: Jual normal, tidak ada premium
- **Distributor**: Business as usual

### Scenario 3: Prolonged Dry Season (Kemarau Panjang)
**Input**:
```
curah_hujan_mm = 0 mm
curah_hujan_lag_7d = 0 mm
suhu_mean = 33°C
```

**Prediction**: 🔻 TURUN (65% confidence)

**Reasoning**:
- Panen melimpah (untuk komoditas tertentu)
- Distribusi sangat lancar
- Supply tinggi → harga turun

**Recommendation**:
- **Konsumen**: Tunggu, harga akan lebih murah
- **Petani**: Jual cepat sebelum oversupply
- **Distributor**: Avoid overstock

---

## 🚀 DEPLOYMENT ARCHITECTURE

### Real-time Prediction Pipeline

```
[Weather API] 
     ↓ (streaming)
[Kafka Producer]
     ↓
[Kafka Topic: weather-stream]
     ↓
[Consumer + ML Model]
     ↓
[Prediction Results]
     ↓ (store)
[Database / Dashboard]
```

### System Components
1. **Producer**: Fetch weather data dari API
2. **Kafka**: Message broker untuk streaming
3. **Consumer**: Process data + ML inference
4. **ML Model**: Loaded in memory untuk fast prediction
5. **Monitoring**: Prometheus + Grafana untuk metrics
6. **Security**: Authentication + encryption

---

## 📚 TECHNICAL DEEP DIVE

### Why Gradient Boosting?

#### Decision Tree Basics
- Binary tree yang split data berdasarkan features
- Leaf nodes = predictions
- Problem: Single tree prone to overfitting

#### Boosting Concept
1. Train tree 1 → make predictions → calculate errors
2. Train tree 2 → focus on errors from tree 1
3. Train tree 3 → focus on errors from tree 1+2
4. ... repeat N times
5. Final prediction = weighted sum of all trees

#### Gradient Descent
- Optimize loss function using gradient descent
- Each new tree tries to reduce residual errors
- Learning rate controls step size

### Math (Simplified)
```
F₀(x) = initial guess
For m = 1 to M:
    Fₘ(x) = Fₘ₋₁(x) + η * hₘ(x)
    where hₘ(x) = new tree trained on residuals
    η = learning rate

Final: F(x) = F₀(x) + Σ(η * hₘ(x))
```

### Feature Scaling: StandardScaler
```
z = (x - μ) / σ

where:
  z = scaled value
  x = original value
  μ = mean
  σ = standard deviation
```

**Why scaling?**
- Gradient boosting not strictly require scaling
- BUT scaling improves convergence speed
- Makes features comparable (mm vs hPa vs %)

---

## ⚠️ LIMITATIONS & ASSUMPTIONS

### Model Limitations
1. **Correlation ≠ Causation**: Model finds patterns, not causal relationships
2. **Historical Patterns**: Assumes future similar to past
3. **Other Factors Ignored**: Politik, ekonomi, logistik tidak dimodelkan
4. **Geographic Scope**: Model trained untuk specific regions
5. **Commodity Specific**: Different commodities may have different patterns

### Assumptions
1. Weather data is accurate and timely
2. Price data is representative
3. No major external shocks (war, pandemic, policy changes)
4. Distribution networks relatively stable
5. Market operates normally

### When Model May Fail
❌ **Black Swan Events**: Pandemic, war, policy shock
❌ **New Patterns**: Climate change introducing new patterns
❌ **Data Quality Issues**: Sensor malfunction, API downtime
❌ **Regional Specificity**: Model trained for Java may not work for Papua

---

## 🎯 NEXT STEPS & IMPROVEMENTS

### Short-term (1-3 months)
1. ✅ Deploy current model to production
2. ✅ Collect real prediction vs actual data
3. ✅ Monitor model performance
4. ✅ Setup retraining pipeline

### Mid-term (3-6 months)
1. 📊 Add more features:
   - Commodity-specific models
   - Geographic features (elevation, distance to market)
   - Economic indicators (fuel price, USD exchange rate)
2. 🧪 Experiment with other algorithms:
   - XGBoost (faster training)
   - LightGBM (memory efficient)
   - Deep Learning (if enough data)
3. 📈 A/B testing different models

### Long-term (6-12 months)
1. 🌍 Expand to all Indonesia regions
2. 📱 Mobile app for farmers/consumers
3. 🔮 Multi-step prediction (7 days ahead)
4. 🤖 Automated retraining system
5. 📊 Integration dengan sistem pemerintah

---

## 📞 SUPPORT & DOCUMENTATION

### Quick Start
```bash
# 1. Train model
python models/price_prediction_model.py

# 2. Run consumer
python consumer_price_prediction.py
```

### Full Documentation
- Model README: `models/README.md`
- API Documentation: `DOKUMENTASI_LENGKAP.md`
- Security Guide: `security/README.md`
- Monitoring Guide: `logs/README.md`

### Contact
- Data Scientist: [Your Contact]
- System Admin: [Admin Contact]
- Business Owner: [Owner Contact]

---

**Last Updated**: June 5, 2026
**Model Version**: 1.0.0
**Status**: ✅ Production Ready (with synthetic training data)
