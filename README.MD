# 🌾 IPBD_TPB — Pipeline Big Data Prediksi Harga Pangan

**Sistem End-to-End Big Data** untuk menganalisis dan memprediksi perubahan harga pangan di Pulau Jawa berdasarkan kondisi cuaca, menggunakan Apache Kafka, PostgreSQL, MinIO, Airflow, Prometheus, dan Grafana — semuanya berjalan lokal via Docker.

---

## 📋 Daftar Isi

1. [Arsitektur Sistem](#arsitektur)
2. [Prasyarat & Instalasi](#prasyarat)
3. [Menjalankan Sistem](#menjalankan)
4. [Batch Processing](#batch)
5. [Stream Processing](#stream)
6. [Machine Learning (Training & Clustering)](#ml)
7. [Monitoring & Logging (Grafana)](#monitoring)
8. [Alerting (Airflow + Telegram)](#alerting)
9. [Keamanan](#keamanan)
10. [Governance](#governance)
11. [Bukti Eksekusi Berulang](#bukti)
12. [Struktur Folder](#struktur)

---

## 1. Arsitektur Sistem <a name="arsitektur"></a>

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DATA SOURCES                                │
│  SP2KP API (Kemendag)          Open-Meteo Archive   Open-Meteo RT   │
│  Harga pangan harian           Cuaca historis        Cuaca realtime │
└────────────┬───────────────────────────┬───────────────────┬────────┘
             │ BATCH                     │ BATCH             │ STREAM
             ▼                           ▼                   ▼
┌────────────────────────┐   ┌────────────────────┐  ┌──────────────────┐
│  Airflow Scheduler     │   │  MinIO (Data Lake) │  │  Kafka Producer  │
│  batch_pipeline_dag    │──▶│  raw-zone          │  │  open_producer   │
│  (harian 06:00 WIB)    │   │  processed-zone    │  └────────┬─────────┘
└────────────────────────┘   └────────────────────┘           │
             │                                                 ▼
             ▼                                       ┌──────────────────┐
┌─────────────────────────┐                         │  Kafka Consumer  │
│  PostgreSQL             │◀────────────────────────│  open_consumer   │
│  harga_pangan_raw       │                         └──────────────────┘
│  cuaca_historical       │
│  cuaca_realtime         │
│  cuaca_harga_merged     │
│  predictions            │
│  alerts                 │
│  audit_log              │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  Machine Learning       │
│  GradientBoosting       │──▶ NAIK / TURUN / STABIL
│  K-Means Clustering     │──▶ Pola Cuaca (4 cluster)
└────────────┬────────────┘
             │
             ▼
┌────────────────────────────────┐
│  Grafana Dashboard (Port 3000) │
│  📊 Pipeline Monitoring        │
│  🌾 Analitik Harga Pangan      │
│  🤖 Prediksi ML + Clustering   │
└────────────────────────────────┘
```

### Komponen

| Komponen | Teknologi | Port |
|---|---|---|
| Stream Broker | Apache Kafka + Zookeeper | 9092 / 2181 |
| Database | PostgreSQL 15 | 5440 |
| Data Lake | MinIO | 9000 / 9001 |
| Monitoring Metrics | Prometheus | 9090 |
| **Dashboard (satu-satunya)** | **Grafana** | **3000** |
| Scheduler / Orchestration | Apache Airflow 2.8 | 8080 |
| ML Klasifikasi | GradientBoosting (scikit-learn) | — |
| ML Clustering | K-Means (scikit-learn, k=3/4/5) | — |

---

## 2. Prasyarat & Instalasi <a name="prasyarat"></a>

### Kebutuhan Sistem

- Python 3.10+
- Docker Desktop (aktif)
- Git

### Install Dependensi Python

```bash
pip install -r requirements.txt
```

### Konfigurasi `.env`

Salin dan sesuaikan (password **tidak pernah hardcode** di kode):

```bash
copy .env.example .env
```

Isi `.env` (sudah terisi default, cukup tambahkan Telegram jika ingin alert):

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5440
POSTGRES_DB=harga_pangan
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

KAFKA_BOOTSTRAP=localhost:9092
TOPIC_CUACA=cuaca-stream

MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# Opsional — untuk alert Telegram
TELEGRAM_BOT_TOKEN=isi_token_bot_anda
TELEGRAM_CHAT_ID=isi_chat_id_anda
```

---

## 3. Menjalankan Sistem <a name="menjalankan"></a>

### Langkah 1 — Start semua service Docker

```bash
docker-compose up -d
```

Tunggu ±60 detik hingga semua service ready. Cek status:

```bash
docker-compose ps
```

Semua service harus `running`:
- `zookeeper`, `kafka`
- `postgres`, `airflow-postgres`
- `minio`
- `prometheus`, `grafana`
- `airflow-init`, `airflow-webserver`, `airflow-scheduler`

### Langkah 2 — Inisialisasi Database

Database otomatis terinisialisasi dari `database/init.sql` saat container `postgres` pertama kali dijalankan.

Verifikasi:

```bash
docker exec -it postgres psql -U postgres -d harga_pangan -c "\dt"
```

Harus muncul 8 tabel: `alerts`, `audit_log`, `cuaca_historical`, `cuaca_harga_merged`, `cuaca_realtime`, `harga_pangan_raw`, `metadata_catalog`, `predictions`.

### Langkah 3 — Akses Dashboard

| Layanan | URL | Login |
|---|---|---|
| **Grafana** (monitoring) | http://localhost:3000 | admin / admin |
| **Airflow** (scheduler) | http://localhost:8080 | admin / admin123 |
| **MinIO** (data lake) | http://localhost:9001 | minioadmin / minioadmin |
| **Prometheus** (metrics) | http://localhost:9090 | — |

---

## 4. Batch Processing <a name="batch"></a>

### Apa itu Batch Processing?

Batch processing mengolah data dalam jumlah besar sekaligus pada interval tertentu (harian). Berbeda dengan streaming yang real-time, batch memproses akumulasi data: download → clean → simpan → merge → training ML.

### Cara Menjalankan Batch Pipeline

**Via Python langsung (manual):**

```bash
python pipeline/run_batch.py
```

**Via Airflow (otomatis terjadwal):**

Buka http://localhost:8080 → DAG `batch_pipeline_harga_pangan` → klik **Trigger DAG ▶**

### 10 Step Batch Pipeline

| Step | Nama | Deskripsi |
|---|---|---|
| 1 | `download_cuaca` | Download data cuaca historis dari Open-Meteo Archive API |
| 2 | `download_harga` | Download data harga pangan dari SP2KP Kemendag API |
| 3 | `clean_cuaca` | Cleaning: handle null, normalisasi, type conversion |
| 4 | `clean_harga` | Cleaning: handle harga=0, forward-fill, drop duplikat |
| 5 | `upload_minio` | Upload raw + processed CSV ke MinIO (Data Lake) |
| 6 | `load_postgres` | Load CSV ke tabel PostgreSQL |
| 7 | `merge_data` | Merge cuaca + harga, buat lag features (1d, 3d, 7d) |
| 8 | `train_model` | Training GradientBoosting + K-Means clustering |
| 9 | `quality_checks` | Validasi null, range, duplikat, tipe data |
| 10 | `audit_log` | Catat pipeline run + generate lineage.json |

### Jalankan 3x / 4x / 10x (untuk bukti)

```bash
# 3x run
python demo_run_pipeline.py --runs 3

# 10x run
python demo_run_pipeline.py --runs 10
```

**Log execution** tersimpan di: `logs/data/application.log` dan `logs/data/demo_run.log`

---

## 5. Stream Processing <a name="stream"></a>

### Apa itu Stream Processing?

Stream processing mengolah data secara real-time, segera setelah data masuk. Pipeline streaming ini:
1. **Producer** — ambil data cuaca terkini dari Open-Meteo setiap jam → publish ke Kafka topic `cuaca-stream`
2. **Consumer** — baca dari Kafka → simpan ke tabel `cuaca_realtime` di PostgreSQL

**Perbedaan dengan Batch:**
- Batch: data diproses sekaligus setelah dikumpulkan (misalnya sehari sekali)
- Stream: data diproses segera begitu datang (real-time, per jam)

### Jalankan Stream Processing

**Terminal 1 — Producer** (publish data cuaca ke Kafka):

```bash
python streaming/open_producer.py
```

**Terminal 2 — Consumer** (baca Kafka → simpan ke DB):

```bash
python streaming/open_consumer.py
```

**Terminal 3 — Prediction Consumer** (baca cuaca realtime → prediksi ML):

```bash
python consumer_price_prediction.py
```

### Jalankan Berulang (untuk bukti)

```bash
# Streaming demo 3x siklus
python demo_run_pipeline.py --mode streaming --runs 3
```

**Log execution** tersimpan di: `logs/data/application.log`

---

## 6. Machine Learning — Training & Clustering <a name="ml"></a>

### 6.1 Model Klasifikasi (GradientBoosting)

**Tujuan:** Memprediksi apakah harga pangan akan **NAIK**, **TURUN**, atau **STABIL** berdasarkan 11 fitur cuaca.

**Algoritma:** Gradient Boosting Classifier (n_estimators=200, learning_rate=0.1, max_depth=5)

**Training dari data nyata:**

```bash
python -c "from models.price_prediction_model import train_model_from_data; train_model_from_data()"
```

**Training dari data sintetis (jika DB belum ada):**

```bash
python -c "from models.price_prediction_model import train_synthetic_model; train_synthetic_model()"
```

**Model tersimpan di:** `models/saved/food_price_predictor.pkl`

### 6.2 Model Clustering (K-Means)

**Tujuan:** Menemukan **pola/kelompok kondisi cuaca** yang berkorelasi dengan perubahan harga.

**4 Cluster yang Diidentifikasi:**

| Cluster | Nama | Karakteristik |
|---|---|---|
| 0 | Cuaca Normal | Suhu 27°C, hujan sedang, kelembapan 75% |
| 1 | Suhu Tinggi - Kering | Suhu 35°C, hujan rendah, angin kencang |
| 2 | Musim Hujan Lebat | Hujan >80mm, kelembapan 95%, awan tebal |
| 3 | Kemarau Ekstrem | Suhu 38°C, hampir tidak ada hujan |

**Training Clustering (3 eksperimen: k=3, k=4, k=5):**

```bash
python models/clustering_model.py
```

**Laporan tersimpan di:** `logs/data/clustering_report.json`

**Model tersimpan di:** `models/saved/weather_clustering.pkl`

### 6.3 Jalankan Training Berulang (minimal 3x)

```bash
# 3x training batch (classification + clustering)
python demo_run_pipeline.py --runs 3

# Atau hanya clustering
python demo_run_pipeline.py --mode clustering --runs 3
```

---

## 7. Monitoring & Logging (Grafana) <a name="monitoring"></a>

### Grafana Dashboard

Buka **http://localhost:3000** → Login: `admin` / `admin`

Dua dashboard sudah otomatis ter-provision:

#### 🔍 Pipeline Monitoring
Folder: **IPBD Pipeline** → `Pipeline Monitoring — IPBD Harga Pangan`

Panel yang tersedia:
- **Total Pipeline Runs** — jumlah batch pipeline yang pernah dijalankan
- **Steps Berhasil / Gagal** — hitungan step pipeline per status
- **Alert Aktif** — jumlah alert yang belum resolved
- **Records Harga Pangan** — total baris di tabel `harga_pangan_raw`
- **Records Stream** — total baris di tabel `cuaca_realtime`
- **Riwayat Audit Log** — tabel lengkap semua pipeline run + status tiap step
- **Distribusi Alert** — pie chart severity & tipe alert
- **Alert Aktif Detail** — tabel alert yang belum resolved
- **CPU & Memory Usage** — gauge dari Prometheus
- **Stream Events per Menit** — time series messages Kafka
- **Log Execution Detail** — tabel semua step pipeline dengan timestamp

#### 🌾 Analitik Harga Pangan
Folder: **IPBD Pipeline** → `Analitik Harga Pangan — IPBD`

Panel yang tersedia:
- **Rata-rata Harga per Komoditas** — bar chart harga semua komoditas
- **Distribusi Prediksi ML** — donut chart NAIK/TURUN/STABIL
- **Distribusi Cluster K-Means** — pie chart 4 pola cuaca
- **Tren Harga Beras** — time series Beras Medium & Premium
- **Tren Harga Cabai** — time series berbagai jenis cabai
- **Cuaca Realtime** — tabel data cuaca terkini dengan color coding suhu
- **Riwayat Harga Spike** — tabel alert HARGA_SPIKE dari database
- **Prediksi ML Terkini** — tabel prediksi + cluster label + confidence

### Logging Severity

Semua komponen menggunakan `StructuredLogger` dengan 5 level severity:

| Level | Kapan Digunakan |
|---|---|
| `DEBUG` | Detail informasi untuk debugging (langkah kecil di dalam proses) |
| `INFO` | Proses normal berjalan (step berhasil, data dimuat) |
| `WARNING` | Ada anomali tapi proses lanjut (data gap, MinIO tidak tersedia) |
| `ERROR` | Komponen gagal, pipeline lanjut ke step berikutnya |
| `FATAL` | Error kritis — task gagal setelah semua retry (via Airflow callback) |

**Contoh penggunaan:**

```python
from logs.monitoring import StructuredLogger

logger = StructuredLogger("NamaKomponen")

logger.debug("Detail proses...", step="clean_cuaca")
logger.info("Data dimuat", rows=1500, source="harga_pangan_raw")
logger.warning("MinIO tidak tersedia, skip upload")
logger.error("Gagal insert ke DB", table="cuaca_historical", error=str(e))
logger.fatal("Pipeline gagal setelah 3 retry", task="download_cuaca")
```

**File log:**
- `logs/data/application.log` — log umum semua komponen (JSON)
- `logs/data/alerts.log` — log semua alert yang dikirim
- `logs/data/quality_report.json` — laporan quality check terakhir
- `logs/data/clustering_report.json` — laporan clustering terakhir
- `logs/data/lineage.json` — data lineage end-to-end
- `logs/data/demo_run.log` — log eksekusi demo pipeline

---

## 8. Alerting (Airflow + Telegram) <a name="alerting"></a>

### 8.1 Tipe Alert

| Tipe | Trigger | Severity |
|---|---|---|
| `HARGA_SPIKE` | Harga naik > 20% dalam 3 hari | CRITICAL |
| `DATA_GAP` | Tidak ada data stream > 6 jam | WARNING |
| `MODEL_DEGRADATION` | Akurasi model < 60% | WARNING |
| `PIPELINE_FAILURE` | Step pipeline gagal setelah retry | CRITICAL |
| `ANOMALI_CUACA` | Suhu/hujan di luar range normal | WARNING |

### 8.2 Airflow — Notifikasi Otomatis saat Job Gagal

Airflow dikonfigurasi dengan `on_failure_callback` di setiap task. Saat task **gagal setelah 3x retry**:

1. Airflow memanggil `on_failure_callback(context)`
2. Log `[FATAL]` ditulis ke file log
3. `PanganAlertManager.check_pipeline_failure()` dipanggil otomatis
4. Alert disimpan ke tabel `alerts` di PostgreSQL
5. Notifikasi dikirim ke **Telegram** (jika dikonfigurasi)

**DAG yang tersedia di Airflow (http://localhost:8080):**

| DAG | Jadwal | Fungsi |
|---|---|---|
| `batch_pipeline_harga_pangan` | Setiap hari 06:00 WIB | Batch pipeline 10 step + ML training |
| `stream_monitor_harga_pangan` | Setiap jam | Monitor stream health + harga spike check |

**Trigger manual (untuk uji coba):**

```bash
# Via Airflow CLI di dalam container
docker exec airflow-scheduler airflow dags trigger batch_pipeline_harga_pangan
docker exec airflow-scheduler airflow dags trigger stream_monitor_harga_pangan
```

### 8.3 Konfigurasi Telegram Alert

Edit `.env`:

```env
TELEGRAM_BOT_TOKEN=1234567890:AAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TELEGRAM_CHAT_ID=-1001234567890
```

**Test alert manual:**

```bash
python -c "
from alerts.alert_manager import PanganAlertManager
am = PanganAlertManager()
am.check_pipeline_failure('test_task', 'Uji coba notif Telegram', 'demo-001')
"
```

### 8.4 Cek Alert dari Database

```bash
docker exec -it postgres psql -U postgres -d harga_pangan -c "SELECT alert_type, severity, message, created_at FROM alerts ORDER BY created_at DESC LIMIT 10;"
```

---

## 9. Keamanan <a name="keamanan"></a>

### 9.1 Password di Environment Variable

Semua credentials disimpan di `.env` dan dibaca via `os.getenv()`. **Tidak ada password hardcode di kode Python.**

```python
# ✅ Cara benar (digunakan di semua script)
password = os.getenv("POSTGRES_PASSWORD")

# ❌ Cara salah (tidak ada di project ini)
password = "postgres"
```

File `.env` masuk ke `.gitignore` — tidak akan ter-commit ke repository.

### 9.2 PII Masking

Data yang diproses (harga pangan & cuaca) adalah data publik, tidak ada PII. Namun mekanisme masking tersedia:

```python
from security.security import DataProtection

# Masking field sensitif sebelum logging
safe = DataProtection.mask_sensitive_data({
    "password": "secret",    # → "***MASKED***"
    "api_key": "abc123",     # → "***MASKED***"
    "data": "normal_value"   # → tetap
})
```

### 9.3 Authentication (JWT)

```python
from security.security import AuthenticationManager

auth = AuthenticationManager()
result = auth.authenticate("admin", "admin123")
token = result["token"]  # JWT valid 24 jam
```

Role yang tersedia: `admin` (baca+tulis+train), `engineer` (baca+tulis), `viewer` (hanya baca).

---

## 10. Governance <a name="governance"></a>

### 10.1 Data Quality Checks

Dijalankan otomatis setiap batch pipeline (Step 9). Cek yang dilakukan:

**Data Cuaca:** suhu range (-10 s/d 50°C), curah hujan ≥ 0, kelembapan 0-100%, tidak ada duplikat per (tanggal, kab_kota)

**Data Harga:** harga > 0 dan < 1.000.000, komoditas tidak null, tanggal valid, tidak ada duplikat per (tanggal, kab_kota, komoditas)

```bash
# Jalankan manual
python governance/quality_checks.py

# Lihat laporan
type logs\data\quality_report.json
```

### 10.2 Metadata Management

Setiap tabel memiliki metadata (owner, deskripsi, sumber, frekuensi update):

```bash
python governance/metadata_manager.py
```

### 10.3 Audit Trail

Setiap pipeline run tercatat otomatis di tabel `audit_log`:

```sql
-- Lihat riwayat audit
SELECT pipeline_run_id, tabel_nama, operasi, username,
       data_sesudah->>'status' as status, created_at
FROM audit_log
ORDER BY created_at DESC
LIMIT 20;
```

### 10.4 Data Lineage

File `logs/data/lineage.json` otomatis di-generate setiap pipeline run. Mendokumentasikan alur data lengkap dari sumber hingga dashboard.

```bash
# Generate manual
python governance/audit_trail.py
```

### 10.5 Compliance

- **Sumber data:** SP2KP API (Kemendag, data publik) + Open-Meteo (CC BY 4.0)
- **Tidak ada PII** yang diproses atau disimpan
- **Data retensi:** Raw CSV 90 hari, audit log permanen, model pkl 6 bulan

---

## 11. Bukti Eksekusi Berulang <a name="bukti"></a>

Gunakan script `demo_run_pipeline.py` untuk menjalankan pipeline 3x, 4x, atau 10x:

```bash
# 3 run batch pipeline + clustering
python demo_run_pipeline.py --runs 3

# 4 run
python demo_run_pipeline.py --runs 4

# 10 run
python demo_run_pipeline.py --runs 10

# Hanya stream
python demo_run_pipeline.py --mode streaming --runs 3

# Hanya clustering (k=3, k=4, k=5 bergantian)
python demo_run_pipeline.py --mode clustering --runs 3
```

Setiap run menghasilkan:
- **Pipeline Run ID** unik (contoh: `demo-run-01-a3f7b2`)
- **Log file** dengan timestamp: `logs/data/demo_run.log`
- **Quality report** terbaru: `logs/data/quality_report.json`
- **Lineage file**: `logs/data/lineage.json`
- **Model tersimpan**: `models/saved/food_price_predictor.pkl` + `weather_clustering.pkl`

**Untuk screenshot bukti:** Setelah menjalankan pipeline, buka Grafana → Panel "Riwayat Audit Log Pipeline" — semua run akan muncul di sana.

---

## 12. Struktur Folder <a name="struktur"></a>

```
IPBD_TPB/
│
├── 📁 airflow/dags/
│   ├── batch_pipeline_dag.py        ← DAG batch harian + alert Telegram
│   └── stream_monitor_dag.py        ← DAG monitor stream per jam
│
├── 📁 alerts/
│   ├── alert_manager.py             ← PanganAlertManager (5 tipe alert)
│   └── alert_rules.py               ← Threshold & aturan alert
│
├── 📁 batch/
│   ├── cuaca/
│   │   ├── histori_cuaca.py         ← Download data cuaca Open-Meteo
│   │   └── clean_cuaca.py           ← Cleaning data cuaca
│   ├── harga/
│   │   ├── batch_pangan.py          ← Download harga pangan SP2KP
│   │   └── clean_harga.py           ← Cleaning data harga
│   └── storage/
│       └── upload_minio.py          ← Upload ke MinIO (Data Lake)
│
│
├── 📁 database/
│   └── init.sql                     ← Schema 8 tabel PostgreSQL
│
├── 📁 data/
│   ├── raw/                         ← Data mentah dari API
│   ├── processed/                   ← Data setelah cleaning
│   └── backup/                      ← Backup data
│
├── 📁 governance/
│   ├── audit_trail.py               ← Audit log & data lineage
│   ├── metadata_manager.py          ← Metadata tabel (owner, deskripsi)
│   └── quality_checks.py            ← Validasi kualitas data
│
├── 📁 grafana/
│   ├── dashboards/
│   │   ├── pipeline_monitoring.json ← Dashboard monitoring pipeline
│   │   └── harga_pangan.json        ← Dashboard analitik harga
│   └── provisioning/
│       ├── datasources/
│       │   ├── prometheus.yml       ← Auto-provision Prometheus
│       │   └── postgres.yml         ← Auto-provision PostgreSQL
│       └── dashboards/
│           └── dashboard.yml        ← Konfigurasi folder dashboard
│
├── 📁 logs/
│   ├── monitoring.py                ← StructuredLogger (INFO/DEBUG/WARNING/ERROR/FATAL)
│   └── data/                        ← Output log files
│       ├── application.log          ← Log umum semua komponen
│       ├── alerts.log               ← Log semua alert
│       ├── quality_report.json      ← Laporan quality check
│       ├── clustering_report.json   ← Laporan K-Means clustering
│       └── lineage.json             ← Data lineage end-to-end
│
├── 📁 models/
│   ├── price_prediction_model.py    ← GradientBoosting (NAIK/TURUN/STABIL)
│   ├── clustering_model.py          ← K-Means clustering (k=3/4/5)
│   ├── ml_model.py                  ← IsolationForest (anomaly detection)
│   └── saved/
│       ├── food_price_predictor.pkl ← Model klasifikasi tersimpan
│       └── weather_clustering.pkl   ← Model clustering tersimpan
│
├── 📁 pipeline/
│   ├── run_batch.py                 ← Batch orchestrator 10 step
│   └── health_check.py             ← Health check endpoint
│
├── 📁 security/
│   └── security.py                  ← JWT auth, Fernet encryption, PII masking
│
├── 📁 streaming/
│   ├── open_producer.py             ← Kafka producer (cuaca realtime)
│   └── open_consumer.py             ← Kafka consumer → PostgreSQL
│
├── consumer_price_prediction.py     ← Prediction pipeline (stream → ML → DB)
├── demo_run_pipeline.py             ← Script demo eksekusi berulang
├── docker-compose.yml               ← Semua service Docker
├── prometheus.yml                   ← Prometheus scrape config
├── requirements.txt                 ← Dependensi Python
├── .env                             ← Credentials (tidak di-commit ke git)
└── README.md                        ← Dokumen ini
```

---

## 🛠️ Troubleshooting

### Kafka tidak bisa terkoneksi

```bash
# Cek apakah Kafka sudah jalan
docker logs kafka | tail -20

# Restart jika perlu
docker-compose restart kafka
```

### PostgreSQL tidak bisa konek

```bash
# Cek status
docker exec postgres pg_isready -U postgres

# Lihat log
docker logs postgres | tail -20
```

### Grafana dashboard tidak muncul

```bash
# Restart Grafana untuk reload provisioning
docker-compose restart grafana
```

### Airflow gagal inisialisasi

```bash
# Jalankan ulang init
docker-compose run --rm airflow-init

# Cek log
docker logs airflow-webserver | tail -30
```

### Reset semua data (mulai dari awal)

```bash
docker-compose down -v
docker-compose up -d
```

---

## 📦 Quick Start (Semua Langkah)

```bash
# 1. Masuk ke folder project
cd "d:\SEMESTER 4\IPBD\Tugas Akhir  Projek\IPBD_TPB"

# 2. Install dependensi Python
pip install -r requirements.txt

# 3. Start semua service Docker (Kafka, PostgreSQL, MinIO, Prometheus, Grafana, Airflow)
docker-compose up -d

# 4. Tunggu semua service ready (±60 detik), lalu cek status
docker-compose ps

# 5. Jalankan demo pipeline 3x (batch + clustering + quality check + audit log)
python demo_run_pipeline.py --runs 3

# 6. Buka Grafana — SATU-SATUNYA DASHBOARD
#    URL: http://localhost:3000  (admin / admin)
#    Dashboard otomatis muncul: "Pipeline Monitoring" & "Analitik Harga Pangan"
start http://localhost:3000

# 7. Buka Airflow — lihat & trigger DAG
#    URL: http://localhost:8080  (admin / admin123)
start http://localhost:8080

# 8. Jalankan streaming (buka 2 terminal terpisah)
# Terminal 1 — Producer (kirim cuaca ke Kafka):
python streaming/open_producer.py
# Terminal 2 — Consumer (terima dari Kafka, simpan ke DB):
python streaming/open_consumer.py
# Terminal 3 — Prediction (baca cuaca realtime → prediksi ML → DB → tampil di Grafana):
python consumer_price_prediction.py
```
