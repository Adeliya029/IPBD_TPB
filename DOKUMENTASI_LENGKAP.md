# 📚 DOKUMENTASI LENGKAP - WEATHER DATA PIPELINE
## Machine Learning Integration, Monitoring & Logging, dan Security Implementation

---

## 📋 DAFTAR ISI

1. [Overview Sistem](#1-overview-sistem)
2. [Machine Learning Integration](#2-machine-learning-integration)
3. [Monitoring dan Logging](#3-monitoring-dan-logging)
4. [Keamanan Data (Security)](#4-keamanan-data-security)
5. [Alur Integrasi Lengkap](#5-alur-integrasi-lengkap)
6. [Instalasi dan Setup](#6-instalasi-dan-setup)
7. [Penggunaan Sistem](#7-penggunaan-sistem)
8. [Dashboard dan Visualisasi](#8-dashboard-dan-visualisasi)

---

## 1. OVERVIEW SISTEM

### 1.1 Arsitektur Sistem

```
┌─────────────────────────────────────────────────────────────────┐
│                     WEATHER DATA PIPELINE                        │
│                                                                  │
│  ┌──────────────┐    ┌──────────┐    ┌───────────────────┐   │
│  │   Producer   │───▶│  Kafka   │───▶│    Consumer       │   │
│  │  (Secured)   │    │ Message  │    │   (Secured)       │   │
│  │              │    │  Broker  │    │                   │   │
│  └──────────────┘    └──────────┘    └─────────┬─────────┘   │
│         │                                       │              │
│         │                                       ▼              │
│         │                              ┌─────────────────┐    │
│         │                              │   ML Model      │    │
│         │                              │   (Anomaly      │    │
│         │                              │   Detection)    │    │
│         │                              └─────────────────┘    │
│         │                                                      │
│         ▼                                       ▼              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │           MONITORING & LOGGING LAYER                 │    │
│  │  - Prometheus Metrics                                │    │
│  │  - Structured JSON Logs                              │    │
│  │  - Performance Tracking                              │    │
│  └──────────────────────────────────────────────────────┘    │
│         │                                       │              │
│         ▼                                       ▼              │
│  ┌──────────────┐                        ┌──────────────┐    │
│  │  Prometheus  │                        │   Grafana    │    │
│  │   (Metrics   │───────────────────────▶│ (Dashboard)  │    │
│  │  Collection) │                        │              │    │
│  └──────────────┘                        └──────────────┘    │
│                                                                │
│  ┌────────────────────────────────────────────────────────┐  │
│  │              SECURITY LAYER                            │  │
│  │  - Authentication (JWT)                                │  │
│  │  - Authorization (Role-based)                          │  │
│  │  - Data Encryption                                     │  │
│  │  - Audit Logging                                       │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

### 1.2 Komponen Utama

| Komponen | Fungsi | Port |
|----------|--------|------|
| **Producer** | Mengambil data cuaca dari API dan mengirim ke Kafka | - |
| **Kafka** | Message broker untuk streaming data | 9092 |
| **Consumer** | Membaca data dari Kafka dan melakukan inferensi ML | - |
| **ML Model** | Deteksi anomali cuaca (Isolation Forest) | - |
| **Prometheus** | Monitoring metrics collection | 9090 |
| **Grafana** | Dashboard visualisasi metrics | 3000 |

---

## 2. MACHINE LEARNING INTEGRATION

### 2.1 Konsep ML dalam Pipeline

Pipeline ini menggunakan **Anomaly Detection** untuk mendeteksi pola cuaca yang tidak normal.

**Algoritma**: Isolation Forest
- **Kenapa Isolation Forest?**
  - Tidak memerlukan label (unsupervised learning)
  - Efektif untuk real-time anomaly detection
  - Performa baik dengan high-dimensional data
  - Dapat mendeteksi outlier secara otomatis

### 2.2 Arsitektur ML

```
┌─────────────────────────────────────────────────────────┐
│                    ML PIPELINE                          │
│                                                         │
│  TRAINING PHASE (Offline)                              │
│  ┌──────────────┐    ┌──────────────┐    ┌─────────┐ │
│  │  Historical  │───▶│   Feature    │───▶│  Train  │ │
│  │    Data      │    │ Engineering  │    │  Model  │ │
│  └──────────────┘    └──────────────┘    └────┬────┘ │
│                                                 │      │
│                                                 ▼      │
│                                          ┌────────────┐│
│                                          │Save Model  ││
│                                          │  (.pkl)    ││
│                                          └────────────┘│
│                                                         │
│  INFERENCE PHASE (Real-time)                           │
│  ┌──────────────┐    ┌──────────────┐    ┌─────────┐ │
│  │  Streaming   │───▶│   Feature    │───▶│ Predict │ │
│  │    Data      │    │ Extraction   │    │ Anomaly │ │
│  └──────────────┘    └──────────────┘    └────┬────┘ │
│                                                 │      │
│                                                 ▼      │
│                                          ┌────────────┐│
│                                          │  Result    ││
│                                          │ - Normal   ││
│                                          │ - Anomaly  ││
│                                          └────────────┘│
└─────────────────────────────────────────────────────────┘
```

### 2.3 Features yang Digunakan

Model menggunakan 2 features utama:
1. **Temperature (°C)** - Suhu saat ini
2. **Windspeed (km/h)** - Kecepatan angin

**Feature Scaling**: StandardScaler untuk normalisasi data

### 2.4 Training Model

**File**: `ml_model.py`

#### a. Data Training
Model dilatih dengan data sintetis yang mewakili pola cuaca normal untuk 5 kota:

```python
# Jakarta: 25-33°C, 5-20 km/h
# Surabaya: 26-34°C, 8-25 km/h  
# Bandung: 20-28°C, 3-15 km/h
# Medan: 24-32°C, 5-18 km/h
# Makassar: 25-33°C, 10-30 km/h
```

Total: **1000 data points** (200 per kota)

#### b. Training Process

```python
from ml_model import train_initial_model

# Train model pertama kali
detector = train_initial_model()

# Model disimpan ke: models/anomaly_detector.pkl
```

**Parameter Model**:
- `contamination=0.1` (10% data dianggap anomali)
- `n_estimators=100` (jumlah trees)
- `random_state=42` (reproducibility)

#### c. Model Output

Model menghasilkan 3 output:
1. **is_anomaly** (bool) - Apakah data anomali?
2. **anomaly_score** (float) - Score anomali (semakin negatif = semakin anomali)
3. **confidence** (float) - Confidence level (0-1)

### 2.5 Inference (Real-time Prediction)

**Integrasi di Consumer**:

```python
# Load model
ml_detector = WeatherAnomalyDetector()
ml_detector.load_model()

# Untuk setiap data yang diterima
for message in consumer:
    data = message.value
    
    # ML Inference
    prediction = ml_detector.predict(data)
    
    if prediction['is_anomaly']:
        print(f"⚠️ ANOMALY DETECTED!")
        print(f"Anomaly Score: {prediction['anomaly_score']}")
        print(f"Confidence: {prediction['confidence']:.2%}")
```

**Contoh Output**:

```
⚠️ ML ALERT: ANOMALY DETECTED!
   Anomaly Score: -0.2543
   Confidence: 56.32%
   Total Anomalies: 3/50
```

### 2.6 Model Retraining

Model dapat di-retrain dengan data historis yang sebenarnya:

```python
# Kumpulkan data historis
historical_data = [
    {'temperature': 28.5, 'windspeed': 12.3},
    {'temperature': 29.1, 'windspeed': 13.7},
    # ... lebih banyak data
]

# Retrain model
detector = WeatherAnomalyDetector()
detector.train(historical_data)

# Model baru akan otomatis tersimpan
```

**Best Practice**:
- Retrain model setiap 1 bulan dengan data aktual
- Gunakan minimal 1000 data points untuk training
- Monitor performa model dengan confusion matrix

---

## 3. MONITORING DAN LOGGING

### 3.1 Arsitektur Monitoring

```
┌──────────────────────────────────────────────────────────┐
│                  MONITORING STACK                        │
│                                                          │
│  APPLICATION LAYER                                       │
│  ┌──────────────┐         ┌──────────────┐            │
│  │   Producer   │         │   Consumer   │            │
│  │              │         │              │            │
│  │ - Metrics    │         │ - Metrics    │            │
│  │ - Logs       │         │ - Logs       │            │
│  └──────┬───────┘         └──────┬───────┘            │
│         │                        │                     │
│         │ Expose :8001          │ Expose :8002       │
│         │                        │                     │
│         └────────┬───────────────┘                     │
│                  │                                     │
│                  ▼                                     │
│         ┌─────────────────┐                           │
│         │   Prometheus    │                           │
│         │   :9090         │                           │
│         │                 │                           │
│         │ - Scrape metrics│                           │
│         │ - Time-series DB│                           │
│         └────────┬────────┘                           │
│                  │                                     │
│                  │ Query                              │
│                  ▼                                     │
│         ┌─────────────────┐                           │
│         │    Grafana      │                           │
│         │    :3000        │                           │
│         │                 │                           │
│         │ - Dashboards    │                           │
│         │ - Alerts        │                           │
│         └─────────────────┘                           │
│                                                          │
│  LOGS                                                    │
│  ┌──────────────────────────────────────────────┐      │
│  │  logs/                                       │      │
│  │  ├── application.log  (Structured JSON)      │      │
│  │  ├── errors.log       (Error tracking)       │      │
│  │  └── audit.log        (Security events)      │      │
│  └──────────────────────────────────────────────┘      │
└──────────────────────────────────────────────────────────┘
```

### 3.2 Prometheus Metrics

**File**: `monitoring.py`

#### a. Counter Metrics (Jumlah Events)

| Metric | Deskripsi | Labels |
|--------|-----------|--------|
| `weather_messages_processed_total` | Total pesan yang diproses | status, city |
| `ml_predictions_total` | Total prediksi ML | result (anomaly/normal) |
| `pipeline_errors_total` | Total errors | component, error_type |
| `authentication_attempts_total` | Total login attempts | status |

**Contoh Query**:
```promql
# Total messages processed per city
sum(weather_messages_processed_total) by (city)

# Error rate
rate(pipeline_errors_total[5m])

# ML anomaly detection rate
ml_predictions_total{result="anomaly"} / ml_predictions_total
```

#### b. Histogram Metrics (Latency)

| Metric | Deskripsi |
|--------|-----------|
| `message_processing_seconds` | Waktu processing message |
| `ml_inference_seconds` | Waktu inferensi ML |

**Contoh Query**:
```promql
# 95th percentile processing latency
histogram_quantile(0.95, message_processing_seconds)

# Average ML inference time
rate(ml_inference_seconds_sum[5m]) / rate(ml_inference_seconds_count[5m])
```

#### c. Gauge Metrics (Current Values)

| Metric | Deskripsi |
|--------|-----------|
| `current_temperature_celsius` | Suhu saat ini per kota |
| `current_windspeed_kmh` | Kecepatan angin per kota |
| `system_cpu_usage_percent` | CPU usage |
| `system_memory_usage_percent` | Memory usage |
| `active_consumers` | Jumlah consumer aktif |

**Contoh Query**:
```promql
# Current temperature in Jakarta
current_temperature_celsius{city="Jakarta"}

# System resource alerts
system_cpu_usage_percent > 80
system_memory_usage_percent > 80
```

### 3.3 Structured Logging

**Format**: JSON Lines (JSONL) untuk easy parsing

**Contoh Log Entry**:
```json
{
  "timestamp": "2026-06-05T10:30:45.123456",
  "level": "INFO",
  "logger": "secure_consumer",
  "message": "Weather data processed",
  "module": "consumer_secure",
  "function": "main",
  "line": 142,
  "extra_fields": {
    "city": "Jakarta",
    "temperature": 28.5,
    "windspeed": 12.3,
    "is_anomaly": false,
    "anomaly_score": -0.1234,
    "message_id": 45,
    "user": "data_engineer"
  }
}
```

**Keuntungan Structured Logs**:
- ✅ Mudah di-parse dan dianalisis
- ✅ Dapat di-query dengan tools seperti jq, ELK stack
- ✅ Konsisten format across services
- ✅ Machine-readable

### 3.4 Log Types

#### a. Application Logs
**File**: `logs/application.log`

Berisi semua aktivitas aplikasi:
- Message processing
- ML predictions
- System events

#### b. Error Logs
**File**: `logs/errors.log`

Dedicated untuk tracking errors:
```json
{
  "timestamp": "2026-06-05T10:35:22",
  "component": "producer",
  "error_type": "RequestException",
  "error_message": "Connection timeout",
  "context": {
    "city": "Jakarta",
    "retry_count": 3
  }
}
```

#### c. Audit Logs
**File**: `logs/audit.log`

Security dan compliance tracking:
```
2026-06-05 10:30:00 - AUDIT - AUTH SUCCESS - User: admin, IP: 192.168.1.10
2026-06-05 10:30:15 - AUDIT - AUTHZ DENIED - User: viewer, Action: train_model
2026-06-05 10:30:30 - AUDIT - DATA ACCESS - User: data_engineer, Type: weather_data
```

### 3.5 Performance Monitoring

**Context Manager** untuk automatic timing:

```python
from monitoring import PerformanceMonitor, MetricsCollector

metrics = MetricsCollector()

# Automatically record duration
with PerformanceMonitor(metrics, 'consumer'):
    # Your code here
    process_message(data)
    
# Duration automatically recorded to Prometheus
```

**Metrics yang di-track**:
- Message processing time
- ML inference time
- API request time
- Database query time (jika ada)

### 3.6 Alerting

**Threshold-based Alerts**:

```python
alert_thresholds = {
    'error_rate': 0.1,      # 10% error rate
    'cpu_usage': 80.0,      # 80% CPU
    'memory_usage': 80.0,   # 80% Memory
    'anomaly_rate': 0.3     # 30% anomaly rate
}
```

Alert akan di-log dan dapat diintegrasikan dengan:
- Email notifications
- Slack webhooks
- PagerDuty
- SMS alerts

---

## 4. KEAMANAN DATA (SECURITY)

### 4.1 Security Architecture

```
┌──────────────────────────────────────────────────────────┐
│                  SECURITY LAYERS                         │
│                                                          │
│  LAYER 1: AUTHENTICATION                                 │
│  ┌────────────────────────────────────────────────┐    │
│  │  • JWT Token-based Authentication              │    │
│  │  • Password Hashing (SHA-256)                  │    │
│  │  • Token Expiration (24 hours)                 │    │
│  └────────────────────────────────────────────────┘    │
│                        │                                 │
│                        ▼                                 │
│  LAYER 2: AUTHORIZATION                                  │
│  ┌────────────────────────────────────────────────┐    │
│  │  • Role-Based Access Control (RBAC)            │    │
│  │  • Permission Checking                         │    │
│  │  • Resource-level Authorization                │    │
│  └────────────────────────────────────────────────┘    │
│                        │                                 │
│                        ▼                                 │
│  LAYER 3: DATA PROTECTION                               │
│  ┌────────────────────────────────────────────────┐    │
│  │  • Encryption (Fernet/AES)                     │    │
│  │  • Data Masking                                │    │
│  │  • Input Sanitization                          │    │
│  └────────────────────────────────────────────────┘    │
│                        │                                 │
│                        ▼                                 │
│  LAYER 4: AUDIT & COMPLIANCE                            │
│  ┌────────────────────────────────────────────────┐    │
│  │  • Audit Logging                               │    │
│  │  • Access Tracking                             │    │
│  │  • Compliance Reporting                        │    │
│  └────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────┘
```

### 4.2 Authentication (Autentikasi)

**File**: `security.py` - Class `AuthenticationManager`

#### a. User Management

**Default Users**:

| Username | Password | Role | Permissions |
|----------|----------|------|-------------|
| admin | admin123 | admin | read, write, train_model, view_logs |
| data_engineer | engineer123 | engineer | read, write, view_logs |
| viewer | viewer123 | viewer | read |

#### b. Login Process

```python
from security import AuthenticationManager

auth_manager = AuthenticationManager()

# Login
result = auth_manager.authenticate('admin', 'admin123')

if result['success']:
    token = result['token']
    role = result['role']
    # Use token for subsequent requests
```

**JWT Token Structure**:
```json
{
  "username": "admin",
  "role": "admin",
  "permissions": ["read", "write", "train_model", "view_logs"],
  "exp": 1717675200,  // Expiration timestamp
  "iat": 1717588800   // Issued at timestamp
}
```

#### c. Password Security

- **Hashing**: SHA-256 dengan salt
- **Salt**: Unique per deployment (production: unique per user)
- **No Plain Text**: Password tidak pernah disimpan dalam plain text

#### d. Token Verification

```python
# Verify token
verify_result = auth_manager.verify_token(token)

if verify_result['valid']:
    user_info = verify_result['payload']
    # Token valid, proceed
else:
    # Token invalid/expired
    print(verify_result['message'])
```

### 4.3 Authorization (Otorisasi)

**File**: `security.py` - Class `AuthorizationManager`

#### a. Role-Based Access Control (RBAC)

```
┌─────────────────────────────────────────────────┐
│              PERMISSION MATRIX                  │
├──────────────┬──────┬───────┬──────┬───────────┤
│ Permission   │ Admin│Engineer│Viewer│           │
├──────────────┼──────┼────────┼──────┼───────────┤
│ read         │  ✅  │   ✅   │  ✅  │ Read data │
│ write        │  ✅  │   ✅   │  ❌  │ Send data │
│ train_model  │  ✅  │   ❌   │  ❌  │ ML train  │
│ view_logs    │  ✅  │   ✅   │  ❌  │ View logs │
└──────────────┴──────┴────────┴──────┴───────────┘
```

#### b. Permission Checking

**Method 1: Manual Check**
```python
from security import AuthorizationManager

# Check permission
has_permission = AuthorizationManager.check_permission(
    user_permissions=['read', 'write'],
    required_permission='write'
)
```

**Method 2: Decorator**
```python
from security import AuthorizationManager

@AuthorizationManager.require_permission('train_model')
def train_ml_model(token=None, user_info=None):
    # Only users with 'train_model' permission can execute
    print(f"Training model... (User: {user_info['username']})")
    return "Model trained successfully"

# Call function
result = train_ml_model(token=admin_token)
```

### 4.4 Data Encryption

**File**: `security.py` - Class `DataEncryption`

#### a. Encryption Algorithm

- **Algorithm**: Fernet (AES-128 CBC + HMAC)
- **Key Storage**: `secrets/encryption.key`
- **Key Rotation**: Dapat di-rotate secara berkala

#### b. Usage

```python
from security import DataEncryption

encryptor = DataEncryption()

# Encrypt sensitive data
api_key = "secret_api_key_12345"
encrypted = encryptor.encrypt(api_key)
print(encrypted)  # "gAAAAABh..."

# Decrypt
decrypted = encryptor.decrypt(encrypted)
print(decrypted)  # "secret_api_key_12345"
```

#### c. Use Cases

- API keys storage
- Database credentials
- Sensitive configuration values
- Personal Identifiable Information (PII)

### 4.5 Data Protection

**File**: `security.py` - Class `DataProtection`

#### a. Data Masking

```python
from security import DataProtection

# Mask sensitive fields
data = {
    'username': 'admin',
    'password': 'secret123',
    'api_key': 'key_12345',
    'temperature': 28.5
}

masked = DataProtection.mask_sensitive_data(data)
print(masked)
# {
#   'username': 'admin',
#   'password': '***MASKED***',
#   'api_key': '***MASKED***',
#   'temperature': 28.5
# }
```

