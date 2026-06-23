# 📋 PANDUAN MENJALANKAN — IPBD_TPB
### Pipeline Big Data Prediksi Harga Pangan

> **Baca seluruh panduan ini sebelum mulai!**
> Estimasi waktu setup pertama kali: ±10–15 menit.

---

## ✅ PRASYARAT (Wajib Terpasang)

Pastikan software berikut sudah terinstal di komputer Anda:

| Software | Versi Minimum | Cek dengan |
|---|---|---|
| **Python** | 3.10+ | `python --version` |
| **Docker Desktop** | Terbaru | `docker --version` |
| **Git** | Terbaru | `git --version` |

> ⚠️ **Docker Desktop harus dalam keadaan RUNNING** sebelum langkah apapun dijalankan.

---

## 🚀 LANGKAH-LANGKAH MENJALANKAN

---

### LANGKAH 1 — Masuk ke Folder Proyek

Buka **PowerShell** atau **Command Prompt**, lalu jalankan:

```powershell
cd "d:\SEMESTER 4\IPBD\Tugas Akhir  Projek\IPBD_TPB"
```

---

### LANGKAH 2 — Konfigurasi File `.env`

Salin file konfigurasi contoh:

```powershell
copy .env.example .env
```

File `.env` sudah terisi nilai default dan **siap dipakai**. Tidak perlu diubah kecuali ingin mengaktifkan alert Telegram.

> 💡 **Opsional — Telegram Alert:** Jika ingin menerima notifikasi, buka `.env` dan isi:
> ```
> TELEGRAM_BOT_TOKEN=isi_token_bot_anda
> TELEGRAM_CHAT_ID=isi_chat_id_anda
> ```

---

### LANGKAH 3 — Install Dependensi Python

```powershell
pip install -r requirements.txt
```

> ⏳ Proses ini membutuhkan koneksi internet dan mungkin memerlukan beberapa menit.

---

### LANGKAH 4 — Jalankan Semua Service Docker

```powershell
docker-compose up -d
```

Perintah ini akan menjalankan semua service berikut secara otomatis:
- `zookeeper` + `kafka` (stream broker)
- `postgres` (database utama)
- `airflow-postgres` (database Airflow)
- `minio` (data lake)
- `prometheus` (metrics)
- `grafana` (dashboard)
- `airflow-init` + `airflow-webserver` + `airflow-scheduler`

> ⏳ **Tunggu ±60–120 detik** hingga semua service benar-benar siap.

---

### LANGKAH 5 — Cek Status Service

```powershell
docker-compose ps
```

Semua service harus berstatus **`running`** (atau `Up`).
Jika ada yang `Exit` atau `unhealthy`, lihat bagian **Troubleshooting** di bawah.

---

### LANGKAH 6 — Verifikasi Database

Pastikan 8 tabel berhasil dibuat otomatis:

```powershell
docker exec -it postgres psql -U postgres -d harga_pangan -c "\dt"
```

**Output yang diharapkan:**
```
 Schema |       Name          | Type  |  Owner
--------+---------------------+-------+----------
 public | alerts              | table | postgres
 public | audit_log           | table | postgres
 public | cuaca_historical    | table | postgres
 public | cuaca_harga_merged  | table | postgres
 public | cuaca_realtime      | table | postgres
 public | harga_pangan_raw    | table | postgres
 public | metadata_catalog    | table | postgres
 public | predictions         | table | postgres
```

---

### LANGKAH 7 — Jalankan Pipeline Utama (Asli)

Ada dua cara untuk menjalankan proses pengumpulan data: **Versi Asli (Full)** atau **Versi Demo (Simulasi)**.

#### OPSI A: Menjalankan Pipeline Asli (Direkomendasikan)
Versi ini akan mengunduh data cuaca dan harga pangan sungguhan dari API, memprosesnya, lalu menyimpannya ke database.
```powershell
python pipeline/run_batch.py
```
> ⏳ Proses ini memakan waktu beberapa menit tergantung koneksi internet karena mengunduh banyak data historis.

#### OPSI B: Menjalankan Versi Demo (Hanya Simulasi)
Jika hanya ingin melihat simulasi training model dan logs tanpa mengunduh data asli:
```powershell
python demo_run_pipeline.py --runs 3
```

**Hasil yang tersimpan (untuk kedua opsi):**
- `logs/data/application.log` — log detail tiap komponen
- `logs/data/quality_report.json` — laporan kualitas data
- `models/saved/food_price_predictor.pkl` — model klasifikasi
- `models/saved/weather_clustering.pkl` — model clustering

---

### LANGKAH 8 — Jalankan Stream Processing

> 💡 Buka **3 terminal PowerShell baru** secara bersamaan (semuanya di folder proyek yang sama).

**Terminal 1 — Producer (kirim data cuaca ke Kafka):**

```powershell
python streaming/open_producer.py
```

**Terminal 2 — Consumer (terima dari Kafka, simpan ke DB):**

```powershell
python streaming/open_consumer.py
```

**Terminal 3 — Prediction Consumer (cuaca realtime → prediksi ML → DB):**

```powershell
python consumer_price_prediction.py
```

> 📌 Biarkan ketiga terminal ini berjalan. Data streaming akan terus diproses secara real-time.
> Untuk menghentikan, tekan **Ctrl+C** di masing-masing terminal.

---

### LANGKAH 9 — Akses Dashboard & UI

Buka browser dan akses alamat berikut:

| Layanan | URL | Username | Password |
|---|---|---|---|
| 📊 **Grafana** (Dashboard Utama) | http://localhost:3000 | `admin` | `admin` |
| ✈️ **Airflow** (Scheduler/DAG) | http://localhost:8080 | `admin` | `admin123` |
| 🪣 **MinIO** (Data Lake) | http://localhost:9001 | `minioadmin` | `minioadmin` |
| 📈 **Prometheus** (Metrics) | http://localhost:9090 | *(tidak perlu login)* | — |

#### Di Grafana (http://localhost:3000):
1. Login dengan `admin` / `admin`
2. Klik menu **Dashboards** (ikon di sidebar kiri)
3. Buka folder **"IPBD Pipeline"**
4. Tersedia 2 dashboard:
   - **Pipeline Monitoring** — melihat status pipeline, audit log, alert
   - **Analitik Harga Pangan** — grafik harga, prediksi ML, clustering

#### Di Airflow (http://localhost:8080):
1. Login dengan `admin` / `admin123`
2. Tersedia 2 DAG:
   - `batch_pipeline_harga_pangan` — pipeline batch harian
   - `stream_monitor_harga_pangan` — monitor stream per jam
3. Klik tombol **▶ Trigger DAG** untuk menjalankan manual

---

### LANGKAH 10 — Trigger DAG via Command Line (Opsional)

Jika ingin menjalankan DAG Airflow dari terminal:

```powershell
# Trigger batch pipeline
docker exec airflow-scheduler airflow dags trigger batch_pipeline_harga_pangan

# Trigger stream monitor
docker exec airflow-scheduler airflow dags trigger stream_monitor_harga_pangan
```

---

### LANGKAH 11 — Cek Alert dari Database (Opsional)

```powershell
docker exec -it postgres psql -U postgres -d harga_pangan -c "SELECT alert_type, severity, message, created_at FROM alerts ORDER BY created_at DESC LIMIT 10;"
```

---

## 🔁 MENJALANKAN ULANG PIPELINE (Bukti Eksekusi Berulang)

```powershell
# 3x run batch + clustering + quality check
python demo_run_pipeline.py --runs 3

# 4x run
python demo_run_pipeline.py --runs 4

# 10x run
python demo_run_pipeline.py --runs 10

# Hanya streaming (3 siklus)
python demo_run_pipeline.py --mode streaming --runs 3

# Hanya clustering (k=3, k=4, k=5 bergantian)
python demo_run_pipeline.py --mode clustering --runs 3
```

---

## 🛑 MENGHENTIKAN SISTEM

```powershell
# Hentikan semua service (data tetap tersimpan)
docker-compose down

# Hentikan + hapus semua data (mulai dari nol)
docker-compose down -v
```

---

## 🔧 TROUBLESHOOTING

### ❌ Kafka tidak bisa terkoneksi

```powershell
# Cek log Kafka
docker logs kafka | Select-Object -Last 20

# Restart Kafka
docker-compose restart kafka
```

### ❌ PostgreSQL tidak bisa konek

```powershell
# Cek status
docker exec postgres pg_isready -U postgres

# Lihat log
docker logs postgres | Select-Object -Last 20
```

### ❌ Grafana dashboard tidak muncul

```powershell
# Restart Grafana untuk reload provisioning
docker-compose restart grafana
```

### ❌ Airflow gagal inisialisasi

```powershell
# Jalankan ulang init
docker-compose run --rm airflow-init

# Cek log
docker logs airflow-webserver | Select-Object -Last 30
```

### ❌ Reset total (mulai dari awal)

```powershell
# Hapus semua container + volume + data
docker-compose down -v

# Jalankan kembali dari awal
docker-compose up -d
```

---

## 📁 FILE LOG PENTING

| File | Isi |
|---|---|
| `logs/data/application.log` | Log umum semua komponen (JSON) |
| `logs/data/alerts.log` | Log semua alert yang terkirim |
| `logs/data/demo_run.log` | Log eksekusi demo pipeline |
| `logs/data/quality_report.json` | Laporan quality check terbaru |
| `logs/data/clustering_report.json` | Laporan K-Means clustering |
| `logs/data/lineage.json` | Data lineage end-to-end |

---

## ⚡ QUICK START (Ringkasan Semua Perintah)

```powershell
# 1. Masuk ke folder proyek
cd "d:\SEMESTER 4\IPBD\Tugas Akhir  Projek\IPBD_TPB"

# 2. Salin konfigurasi .env
copy .env.example .env

# 3. Install dependensi Python
pip install -r requirements.txt

# 4. Jalankan semua service Docker
docker-compose up -d

# 5. Tunggu ±60 detik, lalu cek status
docker-compose ps

# 6. Verifikasi database
docker exec -it postgres psql -U postgres -d harga_pangan -c "\dt"

# 7. Jalankan batch pipeline 3x
python demo_run_pipeline.py --runs 3

# 8a. Terminal 1 — Producer streaming
python streaming/open_producer.py

# 8b. Terminal 2 — Consumer streaming
python streaming/open_consumer.py

# 8c. Terminal 3 — Prediction consumer
python consumer_price_prediction.py

# 9. Buka Grafana di browser
start http://localhost:3000

# 10. Buka Airflow di browser
start http://localhost:8080
```

---

*Panduan ini dibuat untuk proyek IPBD_TPB — Pipeline Big Data Prediksi Harga Pangan.*
*Semua service berjalan secara lokal via Docker — tidak memerlukan koneksi cloud.*
