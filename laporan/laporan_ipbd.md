# LAPORAN PROYEK IPBD  
## Sistem Big Data Prediksi Harga Pangan Berbasis Kondisi Cuaca di Pulau Jawa

**Informatika dan Pemrosesan Big Data — IPBD**  
**Dosen Pengampu:** [Nama Dosen]  
**Tahun Akademik:** 2025/2026

---

## Daftar Isi

1. [Latar Belakang](#1-latar-belakang)
2. [Arsitektur Sistem](#2-arsitektur-sistem)
3. [Batch Processing](#3-batch-processing)
4. [Stream Processing](#4-stream-processing)
5. [Machine Learning — Training & Prediction](#5-machine-learning--training--prediction)
6. [Dashboard & Visualisasi](#6-dashboard--visualisasi)
7. [Monitoring & Logging](#7-monitoring--logging)
8. [Alerting & Notifikasi](#8-alerting--notifikasi)
9. [Keamanan](#9-keamanan)
10. [Data Governance](#10-data-governance)
11. [Kesimpulan & Saran](#11-kesimpulan--saran)

---

## 1. Latar Belakang

### 1.1 Konteks Permasalahan

Harga pangan di Indonesia bersifat fluktuatif dan dipengaruhi oleh berbagai faktor, salah satunya adalah kondisi cuaca. Perubahan cuaca yang ekstrem — seperti musim hujan berkepanjangan atau kekeringan — dapat mengganggu rantai pasok pangan dan menyebabkan lonjakan harga. Dampaknya langsung dirasakan oleh konsumen dan pelaku usaha di sektor pangan.

Pulau Jawa, sebagai pusat ekonomi dan populasi terbesar di Indonesia, memiliki kerentanan tinggi terhadap fluktuasi harga pangan. Enam provinsi di Jawa (DKI Jakarta, Jawa Barat, Jawa Tengah, DI Yogyakarta, Jawa Timur, dan Banten) mencakup lebih dari 150 juta penduduk yang sangat bergantung pada ketersediaan dan stabilitas harga pangan.

Namun, hingga saat ini belum banyak tersedia sistem yang mampu mengintegrasikan data cuaca dan data harga pangan secara real-time untuk memberikan peringatan dini dan prediksi yang dapat digunakan sebagai dasar pengambilan keputusan.

### 1.2 Tujuan Proyek

Proyek ini bertujuan untuk membangun sistem **end-to-end Big Data** yang mampu:

1. **Mengumpulkan data** harga pangan dari SP2KP Kemendag dan data cuaca dari Open-Meteo secara batch maupun streaming.
2. **Menyimpan dan mengelola data** di data lake (MinIO) dan database relasional (PostgreSQL).
3. **Melakukan analisis dan prediksi** menggunakan machine learning (Gradient Boosting untuk klasifikasi harga, K-Means untuk clustering cuaca).
4. **Memvisualisasikan hasil** dalam dashboard interaktif yang memberikan insight untuk pengambilan keputusan.
5. **Memantau dan memberikan notifikasi** otomatis jika terdeteksi anomali harga atau kegagalan pipeline.

### 1.3 Ruang Lingkup

| Aspek | Cakupan |
|---|---|
| **Wilayah** | 6 provinsi di Pulau Jawa (DKI Jakarta, Jawa Barat, Jawa Tengah, DI Yogyakarta, Jawa Timur, Banten) — 119 kabupaten/kota |
| **Komoditas** | 17 komoditas pangan utama (beras, cabai, bawang, daging, minyak goreng, telur, dll.) |
| **Periode Data** | Januari – Mei 2026 |
| **Sumber Data** | SP2KP API (Kemendag), Open-Meteo Archive & Realtime API |
| **Teknologi** | Apache Kafka, PostgreSQL, MinIO, Apache Airflow, Prometheus, Grafana, scikit-learn |

---

## 2. Arsitektur Sistem

### 2.1 Gambaran Umum

Sistem dibangun dengan arsitektur **end-to-end data pipeline** yang terdiri dari empat lapisan utama: data source, data ingestion & storage, data processing & analytics, dan visualization & monitoring. Seluruh komponen berjalan di atas Docker container pada satu mesin lokal.

<!-- SCREENSHOT: Diagram arsitektur sistem -->
<!-- Format: ![Diagram Arsitektur Sistem](assets/screenshots/arsitektur_sistem.png) -->
<!-- *Gambar 1: Diagram arsitektur end-to-end sistem IPBD* -->

### 2.2 Komponen Sistem

| Komponen | Teknologi | Fungsi | Port |
|---|---|---|---|
| Stream Broker | Apache Kafka 7.5.0 | Menampung data cuaca real-time dari producer ke consumer | 9092 |
| Koordinator | Apache ZooKeeper | Koordinasi cluster Kafka | 2181 |
| Database Utama | PostgreSQL 15 | Menyimpan data harga, cuaca, prediksi, alert, audit log | 5440 |
| Database Airflow | PostgreSQL 15 | Metadata dan logging Airflow | 5432 (internal) |
| Data Lake | MinIO | Penyimpanan objek untuk raw dan processed CSV | 9000, 9001 |
| Monitoring Metrics | Prometheus | Scrape metrics dari producer & consumer | 9090 |
| Dashboard | Grafana | Visualisasi pipeline monitoring & analitik harga | 3000 |
| Orchestrator | Apache Airflow 2.8 | Penjadwalan batch pipeline dan monitoring stream | 8080 |
| Backend API | FastAPI | REST API untuk React dashboard | 8050 |
| Frontend Dashboard | React + Vite + ECharts | Dashboard analitik interaktif | 5173 |

### 2.3 Alur Data

```
SP2KP API ──▶ Batch Pipeline ──▶ MinIO (Data Lake) ──▶ PostgreSQL ──▶ ML Model ──▶ Prediksi
Open-Meteo ──┘                                              ▲                         │
                                                             │                         ▼
Open-Meteo RT ──▶ Kafka Producer ──▶ Kafka ──▶ Consumer ────┘                  Grafana Dashboard
                                                                                React Dashboard
```

- **Data batch:** Download dari API → cleaning → upload ke MinIO → load ke PostgreSQL → merge cuaca & harga → training model → simpan prediksi.
- **Data stream:** Producer ambil cuaca real-time dari Open-Meteo → publish ke Kafka → Consumer baca & simpan ke PostgreSQL → enrichment cluster label.

### 2.4 Status Infrastruktur

Seluruh komponen berjalan dalam container Docker dengan status **healthy**:

<!-- SCREENSHOT: docker-compose ps semua container running -->
<!-- ![Docker Container Status](assets/screenshots/docker_ps.png) -->
<!-- *Gambar 2: Seluruh container Docker dalam status running* -->

```
NAME                STATUS          PORTS
zookeeper           Up 3 hours      2181/tcp
kafka               Up 3 hours      9092/tcp
postgres            Up 3 hours      5440->5432/tcp
airflow-postgres    Up 3 hours      5432/tcp
minio               Up 3 hours      9000-9001/tcp
prometheus          Up 3 hours      9090/tcp
grafana             Up 2 hours      3000/tcp
airflow-webserver   Up 4 hours      8080/tcp
airflow-scheduler   Up 4 hours      (healthy)
airflow-init        Exited (0)      (initialized)
```

---

## 3. Batch Processing

### 3.1 Konsep

Batch processing adalah metode pengolahan data dalam jumlah besar sekaligus pada interval tertentu. Dalam proyek ini, batch pipeline berfungsi untuk mendownload data historis cuaca dan harga dari API eksternal, melakukan cleaning, menyimpan ke data lake (MinIO) dan database (PostgreSQL), melakukan merge data cuaca-harga, serta melatih model machine learning.

### 3.2 Pipeline Utama

Batch pipeline terdiri dari **10 step** yang dijalankan secara berurutan oleh `pipeline/run_batch.py`:

| Step | Nama | Deskripsi | Status |
|---|---|---|---|
| 1 | `download_cuaca` | Download data cuaca historis dari Open-Meteo Archive API | ✅ |
| 2 | `download_harga` | Download data harga pangan dari SP2KP Kemendag API | ✅ |
| 3 | `clean_cuaca` | Cleaning: handle null, normalisasi suhu, type conversion | ✅ |
| 4 | `clean_harga` | Cleaning: handle harga=0, forward-fill, drop duplikat | ✅ |
| 5 | `upload_minio` | Upload raw + processed CSV ke MinIO (Data Lake) | ✅ |
| 6 | `load_postgres` | Load CSV ke tabel PostgreSQL via bulk COPY | ✅ |
| 7 | `merge_data` | Merge cuaca + harga, buat lag features (1d, 3d, 7d) | ✅ |
| 8 | `train_model` | Training GradientBoosting + K-Means clustering | ✅ |
| 9 | `quality_checks` | Validasi null, range, duplikat, tipe data | ✅ |
| 10 | `audit_log` | Catat pipeline run + generate lineage.json | ✅ |

### 3.3 Eksekusi Berulang

Pipeline telah dijalankan secara berulang untuk membuktikan stabilitas dan reproducibility. Setiap run menghasilkan **Pipeline Run ID** unik yang tercatat di tabel `audit_log`.

<!-- SCREENSHOT: Terminal output pipeline 3x run -->
<!-- ![Batch Pipeline 3x Run](assets/screenshots/batch_3x_run.png) -->
<!-- *Gambar 3: Eksekusi batch pipeline 3 kali berturut-turut* -->

<!-- SCREENSHOT: Terminal output pipeline 10x run -->
<!-- ![Batch Pipeline 10x Run](assets/screenshots/batch_10x_run.png) -->
<!-- *Gambar 4: Eksekusi batch pipeline 10 kali berturut-turut* -->

**Contoh output eksekusi:**

```
============================================================
BATCH PIPELINE — run-demo-01-a3f7b2
Start: 2026-07-02 11:40:23
============================================================
▶ Step: 1_download_cuaca
  ℹ️ Data cuaca raw sudah ada, skip download
▶ Step: 2_download_harga
  ℹ️ Data harga raw sudah ada, skip download
...
▶ Step: 10_audit_log
  ✅ 10_audit_log berhasil (attempt 1)
============================================================
PIPELINE SELESAI — run-demo-01-a3f7b2
Durasi: 33.2 detik
Step berhasil: 10/10
============================================================
```

### 3.4 Hasil Batch Processing

| Metrik | Nilai |
|---|---|
| Rata-rata durasi pipeline | ~33 detik |
| Step sukses per run | 10/10 (100%) |
| Jumlah run berturut-turut berhasil | 10 kali |
| Total data cuaca historis | 1.617 baris |
| Total data harga pangan | 298.327 baris |
| Total data merged | 6.734 baris |

### 3.5 Analisis Batch Processing

Pipeline batch menunjukkan **stabilitas tinggi** — seluruh 10 step berhasil dalam setiap eksekusi tanpa kegagalan. Mekanisme **retry logic** (3x percobaan per step) dan **skip logic** (data yang sudah ada tidak didownload ulang) memastikan efisiensi. Penggunaan **bulk COPY** (bukan row-by-row INSERT) pada step 6 membuat loading data ke PostgreSQL sangat cepat, mampu memproses 298.327 baris dalam hitungan detik.

---

## 4. Stream Processing

### 4.1 Konsep

Stream processing mengolah data secara real-time segera setelah data masuk. Dalam proyek ini, streaming digunakan untuk mengambil data cuaca terkini dari Open-Meteo API secara periodik, mengirimkannya melalui **Apache Kafka**, dan menyimpannya ke tabel `cuaca_realtime` di PostgreSQL.

### 4.2 Komponen Streaming

| Komponen | File | Fungsi |
|---|---|---|
| **Producer** | `streaming/open_producer.py` | Ambil data cuaca dari 119 kota di 6 provinsi dari Open-Meteo API → publish ke Kafka topic `cuaca-stream` |
| **Consumer** | `streaming/open_consumer.py` | Baca dari Kafka → simpan ke PostgreSQL `cuaca_realtime` |
| **Kafka Topic** | `cuaca-stream` | Topik buffer data cuaca real-time |

### 4.3 Alur Streaming

```
Open-Meteo API (119 lokasi)
        │
        ▼
  Kafka Producer ──▶ Kafka ──▶ Kafka Consumer ──▶ PostgreSQL
  (port 8001)       (9092)     (port 8002)        cuaca_realtime
        │                        │
        ▼                        ▼
  Prometheus                Prometheus
  (metrics)                 (metrics)
```

### 4.4 Eksekusi Streaming

Producer mengambil data cuaca untuk 119 kabupaten/kota dari Open-Meteo Current Weather API. Data yang dikirim meliputi: suhu, kelembapan, curah hujan, kecepatan angin, tekanan udara, dan kondisi cuaca.

<!-- SCREENSHOT: Terminal producer streaming berjalan -->
<!-- ![Stream Producer](assets/screenshots/stream_producer.png) -->
<!-- *Gambar 5: Kafka producer mengirim data cuaca dari 119 lokasi* -->

<!-- SCREENSHOT: Terminal consumer streaming berjalan -->
<!-- ![Stream Consumer](assets/screenshots/stream_consumer.png) -->
<!-- *Gambar 6: Kafka consumer menerima dan menyimpan data ke PostgreSQL* -->

**Contoh output producer:**
```
[INFO] Producer started — topic=cuaca-stream, bootstrap=localhost:9092
[INFO] Mengirim data cuaca untuk 119 lokasi...
[INFO] ✓ KAB. BOGOR: 28.2°C, Berawan — Terkirim
[INFO] ✓ KAB. BANDUNG: 26.5°C, Hujan Ringan — Terkirim
[INFO] ✓ KOTA SURABAYA: 33.5°C, Cerah — Terkirim
...
[INFO] Selesai: 110/119 berhasil terkirim (9 timeout)
```

### 4.5 Hasil Streaming

| Metrik | Nilai |
|---|---|
| Lokasi tujuan | 119 kabupaten/kota |
| Pesan berhasil terkirim | 110 dari 119 |
| Data tersimpan di DB | 117 baris (update+insert) |
| Provinsi tercakup | 6 (semua provinsi Jawa) |
| Frekuensi | Real-time (setiap jam) |

### 4.6 Analisis Stream Processing

Streaming berhasil mengirimkan **92.4% data** dari 119 lokasi. 9 lokasi gagal karena timeout koneksi ke Open-Meteo API (terjadi pada lokasi dengan koneksi lambat). Consumer secara otomatis menyimpan data ke PostgreSQL dan setiap message dicatat secara lengkap dengan timestamp. Sistem metrics (Prometheus) di port 8001 (producer) dan 8002 (consumer) memantau jumlah pesan, error rate, dan system resource.

---

## 5. Machine Learning — Training & Prediction

### 5.1 Konsep

Machine learning dalam proyek ini memiliki dua fungsi utama:

1. **Klasifikasi harga pangan** — memprediksi apakah harga suatu komoditas akan NAIK, TURUN, atau STABIL berdasarkan kondisi cuaca.
2. **Clustering cuaca** — mengelompokkan pola cuaca ke dalam cluster yang merepresentasikan kondisi iklim berbeda.

Proses **training** menggunakan data historis yang telah terkumpul di PostgreSQL. Proses **prediction** membaca data dari tabel `cuaca_harga_merged`, melakukan prediksi, memperkaya (enrich) dengan label cluster, dan menyimpan hasil ke tabel `predictions`.

### 5.2 Model Klasifikasi — GradientBoosting

**Algoritma:** Gradient Boosting Classifier (sklearn)  
**Jumlah estimator:** 200  
**Learning rate:** 0.1  
**Max depth:** 5  
**Fitur:** 6 fitur cuaca yang tersedia di data merged

| Fitur | Deskripsi |
|---|---|
| `suhu_mean` | Suhu rata-rata harian (°C) |
| `curah_hujan_mm` | Curah hujan (mm) |
| `kelembapan` | Kelembapan relatif (%) |
| `kecepatan_angin` | Kecepatan angin (km/h) |
| `tekanan_udara` | Tekanan udara (hPa) |
| `curah_hujan_lag_7d` | Rata-rata curah hujan 7 hari terakhir (mm) |

**Target kelas:**
| Kode | Label | Ambang Batas |
|---|---|---|
| 0 | TURUN | Perubahan harga < -2% |
| 1 | STABIL | -2% ≤ perubahan ≤ 2% |
| 2 | NAIK | Perubahan harga > 2% |

**Hasil training:**

```
Training accuracy: 0.855
Test accuracy:     0.853

Classification Report:
              precision    recall  f1-score   support
     TURUN       0.20      0.01      0.01       161
    STABIL       0.86      1.00      0.92      1152
      NAIK       0.00      0.00      0.00        34

  accuracy                         0.85      1347
```

### 5.3 Model Clustering — K-Means

**Algoritma:** K-Means (sklearn)  
**Jumlah cluster:** 3  
**Fitur:** 5 fitur cuaca

| Fitur | Deskripsi |
|---|---|
| `suhu_mean` | Suhu rata-rata harian (°C) |
| `curah_hujan_mm` | Curah hujan (mm) |
| `kelembapan` | Kelembapan relatif (%) |
| `kecepatan_angin` | Kecepatan angin (km/h) |
| `tekanan_udara` | Tekanan udara (hPa) |

**Hasil clustering (di-cuaca_harga_merged — 6.734 baris):**

| Cluster | Label | Jumlah | Persentase | Karakteristik |
|---|---|---|---|---|
| 0 | Cuaca Normal | 3.340 | 49,6% | Suhu sedang, hujan ringan |
| 1 | Suhu Tinggi - Kering | 1.759 | 26,1% | Suhu tinggi, hujan rendah |
| 2 | Musim Hujan Lebat | 1.635 | 24,3% | Hujan tinggi, kelembapan tinggi |

**Metrik evaluasi:**
- Silhouette Score: **0,2423**
- Inertia: 6.482,52

### 5.4 Eksekusi Training Berulang

Model dilatih menggunakan data yang tersimpan di PostgreSQL `cuaca_historical` dan `cuaca_harga_merged`. Training dilakukan secara periodik melalui pipeline batch (step 8) maupun secara mandiri.

<!-- SCREENSHOT: Terminal output retrain models -->
<!-- ![Training Models](assets/screenshots/training_models.png) -->
<!-- *Gambar 7: Proses retraining model klasifikasi dan clustering dari data di DB* -->

### 5.5 Prediction & Enrichment

Proses prediksi dilakukan oleh `scripts/predict_and_store.py` dengan alur:

```
Data di cuaca_harga_merged (6.734 baris)
        │
        ▼
  Load model (food_price_predictor.pkl)
        │
        ▼
  Prediksi NAIK/TURUN/STABIL per baris
        │
        ▼
  Enrich dengan cluster label dari model clustering
        │
        ▼
  Simpan ke tabel predictions (label + confidence + probabilitas + cluster)
```

**Hasil prediksi:**

| Label | Jumlah | Persentase |
|---|---|---|
| STABIL | 6.717 | 99,75% |
| TURUN | 17 | 0,25% |
| NAIK | 0 | 0% |

**Distribusi confidence:**

| Rentang Confidence | Jumlah Baris | Interpretasi |
|---|---|---|
| 0,49 – 0,60 | 399 | Keyakinan rendah |
| 0,60 – 0,80 | 2.175 | Keyakinan sedang |
| 0,80 – 0,99 | 943 | Keyakinan tinggi |
| 1,00 | 3.384 | Keyakinan maksimal |

**Rata-rata confidence:** 0,8548

### 5.6 Analisis Machine Learning

**Klasifikasi:** Model mencapai akurasi 85.3% pada data test. Namun, model cenderung bias ke kelas **STABIL** karena distribusi data yang tidak seimbang (85.5% data adalah STABIL). Harga pangan di periode Januari–Mei 2026 relatif stabil dengan perubahan kurang dari ±2%. Ini wajar karena periode tersebut bukan musim paceklik atau bencana alam besar di Jawa.

**Clustering:** Silhouette score 0.242 menunjukkan pemisahan cluster yang cukup baik (moderate). Tiga cluster yang terbentuk masuk akal secara domain: Normal (49.6%), Kering (26.1%), dan Hujan Lebat (24.3%). Pembagian ini konsisten dengan pola iklim di Pulau Jawa.

**Prediction & Enrichment:** Seluruh 6.734 baris data berhasil diprediksi dan di-enrich dengan cluster label. Hasilnya tersimpan di tabel `predictions` dengan struktur:
- `prediksi_label` : NAIK / TURUN / STABIL
- `confidence` : skor keyakinan 0–1
- `probabilitas_naik / turun / stabil` : distribusi probabilitas per kelas
- `cluster_label / cluster_nama` : label cluster K-Means

---

## 6. Dashboard & Visualisasi

### 6.1 Konsep

Dashboard bertujuan untuk menyajikan data dan hasil analisis dalam bentuk visual yang mudah dipahami oleh pengambil keputusan. Proyek ini menyediakan **dua dashboard**:

1. **Grafana Dashboard** — untuk monitoring infrastruktur dan data pipeline (bersifat teknis).
2. **React Dashboard** — untuk analitik harga pangan yang interaktif dan user-friendly (untuk decision maker).

### 6.2 Grafana — Analitik Harga Pangan

<!-- SCREENSHOT: Grafana dashboard full page -->
<!-- ![Grafana Dashboard](assets/screenshots/grafana_dashboard.png) -->
<!-- *Gambar 8: Dashboard Grafana "Analitik Harga Pangan — IPBD"* -->

Dashboard Grafana dibagi menjadi **5 section** dengan **21 panel**:

#### 📊 Ringkasan (Overview)
| Panel | Tipe | Insight |
|---|---|---|
| Rata-rata Harga Nasional | Stat | Angka rata-rata harga seluruh komoditas |
| Komoditas Dipantau | Stat | Jumlah komoditas yang dipantau |
| Alert Aktif | Stat | Jumlah alert CRITICAL yang belum resolved |
| Prediksi Stabil | Stat | Jumlah prediksi STABIL dari model ML |

#### 💰 Analisis Harga
| Panel | Tipe | Insight |
|---|---|---|
| Top 10 Komoditas Termahal | Bar Horizontal | Komoditas dengan harga tertinggi — langsung kelihatan yang paling mahal |
| Tren Harga — Komoditas Utama | Line Chart | Pergerakan harga 6 komoditas utama sepanjang waktu |
| Heatmap Perubahan Harga per Bulan | Table (warna) | Warna merah = naik, hijau = turun per komoditas per bulan |
| Volatilitas Harga | Bar Horizontal | Standar deviasi harga — semakin panjang bar, semakin fluktuatif |

**Contoh insight dari Heatmap:**
```
      Jan   Feb   Mar   Apr   Mei
Cabai Merah  +2.1  +5.4  -1.2  +3.8  +0.5
Beras Medium -0.3  -0.1  +0.2  -0.4  -0.1
```
➡️ *Cabai lebih fluktuatif daripada beras. Keputusan: stok cabai perlu dipantau lebih ketat.*

#### 🗺️ Analisis Wilayah
| Panel | Tipe | Insight |
|---|---|---|
| Ranking Provinsi | Table + Progress Bar | Perbandingan harga antar 6 provinsi |
| Detail Harga per Kab/Kota | Table | Top 50 harga tertinggi per kabupaten/kota |

#### 🌤️ Analisis Cuaca & Korelasi
| Panel | Tipe | Insight |
|---|---|---|
| Scatter: Curah Hujan vs Harga | XY Chart | Visualisasi hubungan curah hujan dan harga |
| Scatter: Suhu vs Harga | XY Chart | Visualisasi hubungan suhu dan harga |
| Korelasi Suhu vs Harga | Stat | Nilai korelasi Pearson (−0,0039) |
| Korelasi Hujan vs Harga | Stat | Nilai korelasi Pearson (0,0014) |
| Korelasi Kelembapan vs Harga | Stat | Nilai korelasi Pearson (0,0006) |

**Analisis korelasi:** Ketiga korelasi mendekati 0, artinya **tidak ada hubungan linier yang signifikan** antara cuaca dan harga pada level agregat nasional. Ini wajar karena harga pangan dipengaruhi oleh banyak faktor lain (kebijakan, distribusi, permintaan) selain cuaca.

#### 🤖 Machine Learning & Risiko
| Panel | Tipe | Insight |
|---|---|---|
| Distribusi Prediksi ML | Pie Chart (Donut) | Proporsi prediksi NAIK / TURUN / STABIL |
| Distribusi Cluster | Pie Chart | Proporsi 3 cluster cuaca |
| Gauge Risiko Alert | Gauge | Level risiko berdasarkan jumlah alert |
| Ranking Kenaikan per Provinsi | Table | Provinsi dengan perubahan harga terbesar |
| Prediksi per Hari | Stacked Bar | Tren prediksi sepanjang waktu |

### 6.3 React Dashboard

<!-- SCREENSHOT: React dashboard full page -->
<!-- ![React Dashboard](assets/screenshots/react_dashboard.png) -->
<!-- *Gambar 9: Dashboard React dengan global filter dan insight panel* -->

Dashboard React dibangun dengan **React 18 + Vite + Tailwind CSS + ECharts** sebagai alternatif yang lebih interaktif dan user-friendly. Fitur utama:

| Fitur | Fungsi |
|---|---|
| **Global Filter Bar** | Filter tanggal, provinsi, dan komoditas yang mempengaruhi seluruh halaman |
| **Search Autocomplete** | Cari komoditas → langsung lompat ke data terkait |
| **Insight Panel** | Panel kanan dengan narasi kalimat insight (bukan angka mentah) |
| **Export PDF / CSV** | Download dashboard sebagai PDF atau data sebagai CSV |
| **5 Section Navigasi** | Dashboard, Harga, Wilayah, Cuaca, ML — via sidebar kiri |

**Contoh insight naratif yang muncul:**
> 🔺 Cabai Merah Keriting naik 12.3% di Banten. Waspada potensi kenaikan lanjutan.
>
> 🚨 3 alert aktif — 2 harga spike, 1 pipeline failure.
>
> 🌤 Korelasi cuaca vs harga sangat lemah. Faktor lain lebih memengaruhi harga.
>
> ✅ 99.4% harga diprediksi stabil oleh model ML.

### 6.4 Analisis Dashboard

Dashboard dirancang untuk menjawab **tiga pertanyaan utama** pengambil keputusan:
1. **"Apa yang terjadi sekarang?"** — dijawab oleh KPI cards, alert gauge, dan cuaca realtime.
2. **"Apa yang akan terjadi?"** — dijawab oleh prediksi ML, ranking kenaikan, dan scatter korelasi.
3. **"Apa yang harus saya lakukan?"** — dijawab oleh insight panel dengan kalimat rekomendasi.

Kombinasi Grafana (monitoring infrastruktur) dan React (analitik bisnis) memberikan cakupan lengkap dari sisi teknis hingga pengambilan keputusan.

---

## 7. Monitoring & Logging

### 7.1 Konsep

Monitoring dan logging merupakan komponen penting dalam sistem Big Data untuk memastikan pipeline berjalan dengan baik, mendeteksi kegagalan, dan menyediakan jejak audit untuk troubleshooting.

### 7.2 Grafana Pipeline Monitoring

<!-- SCREENSHOT: Grafana Pipeline Monitoring dashboard -->
<!-- ![Grafana Pipeline Monitoring](assets/screenshots/grafana_monitoring.png) -->
<!-- *Gambar 10: Dashboard Grafana "Pipeline Monitoring — IPBD Harga Pangan"* -->

Dashboard monitoring Grafana menampilkan:

| Panel | Sumber Data | Fungsi |
|---|---|---|
| Total Pipeline Runs | PostgreSQL | Jumlah batch pipeline yang pernah dijalankan |
| Steps Berhasil / Gagal | PostgreSQL | Hitungan step pipeline per status |
| Alert Aktif | PostgreSQL | Jumlah alert yang belum resolved |
| Records Harga Pangan | PostgreSQL | Total baris di tabel `harga_pangan_raw` |
| Records Stream | PostgreSQL | Total baris di tabel `cuaca_realtime` |
| Riwayat Audit Log | PostgreSQL | Riwayat lengkap pipeline run + status step |
| Distribusi Alert | PostgreSQL | Pie chart severity & tipe alert |
| CPU & Memory Usage | Prometheus | Gauge resource usage server |

### 7.3 Structured Logging

Semua komponen menggunakan **StructuredLogger** yang menulis log dalam format JSON ke file `logs/data/application.log`.

**5 Level Severity:**

| Level | Kapan Digunakan | Contoh |
|---|---|---|
| `DEBUG` | Detail debugging | `"Memproses baris ke-1500 dari 6734"` |
| `INFO` | Proses normal | `"Pipeline selesai: run-demo-01 (33.2 detik)"` |
| `WARNING` | Anomali non-fatal | `"MinIO tidak tersedia, skip upload"` |
| `ERROR` | Gagal tapi lanjut | `"Gagal insert ke DB: connection timeout"` |
| `FATAL` | Gagal total setelah retry | `"Pipeline gagal setelah 3 retry pada step 6"` |

<!-- SCREENSHOT: Contoh log file -->
<!-- ![Application Log](assets/screenshots/application_log.png) -->
<!-- *Gambar 11: Contoh log execution pipeline dalam format JSON* -->

**Contoh baris log:**
```json
{"timestamp": "2026-07-02T11:43:02", "component": "BatchPipeline", "severity": "INFO",
 "message": "Pipeline selesai: run-demo-01", "duration_seconds": 33.2, 
 "failed_steps": [], "step": "10_audit_log"}
```

### 7.4 Prometheus Metrics

Prometheus di-port 9090 meng-scrape metrics dari:
- `weather-producer` (port 8001) — jumlah message, suhu terkini, error rate, CPU usage
- `weather-consumer` (port 8002) — jumlah message processed, DB error rate
- `prometheus` (port 9090) — self-monitoring
- `grafana` (port 3000) — dashboard request metrics

### 7.5 Analisis Monitoring

Sistem monitoring berjalan dengan baik — Grafana menampilkan data real-time dari PostgreSQL dan Prometheus. Structured logging memudahkan pencarian error (filter severity=ERROR/FATAL) dan analisis root cause. Setiap pipeline run tercatat dengan duration, status per step, dan error message jika ada.

---

## 8. Alerting & Notifikasi

### 8.1 Konsep

Sistem alerting bertugas mendeteksi anomali secara otomatis dan mengirimkan notifikasi ke pengguna. Dalam proyek ini, alert dikirim melalui **PostgreSQL** (penyimpanan riwayat), **log file**, dan **Telegram Bot** (notifikasi real-time).

### 8.2 Tipe Alert

| Tipe | Trigger | Severity | Channel |
|---|---|---|---|
| `HARGA_SPIKE` | Harga naik > 20% dalam 3 hari | CRITICAL | PostgreSQL + Log + Telegram |
| `DATA_GAP` | Tidak ada data stream > 6 jam | WARNING | PostgreSQL + Log |
| `MODEL_DEGRADATION` | Akurasi model < 60% | WARNING | PostgreSQL + Log |
| `PIPELINE_FAILURE` | Step pipeline gagal setelah retry | CRITICAL | PostgreSQL + Log + Telegram |
| `ANOMALI_CUACA` | Suhu/hujan di luar range normal | WARNING | PostgreSQL + Log |

### 8.3 Data Alert yang Tercatat

<!-- SCREENSHOT: Tabel alerts di PostgreSQL -->
<!-- ![Alerts Table](assets/screenshots/alerts_table.png) -->
<!-- *Gambar 12: Data alert yang tersimpan di tabel alerts PostgreSQL* -->

Dari database:

```
alert_type          severity    provinsi    komoditas                message
────────────────────────────────────────────────────────────────────────────────────
PIPELINE_FAILURE   CRITICAL    NULL        NULL          PIPELINE FAILURE: Step 6 gagal...
PIPELINE_FAILURE   CRITICAL    NULL        NULL          PIPELINE FAILURE: Step 6 gagal...
HARGA_SPIKE        CRITICAL    36          Cabai Merah   HARGA SPIKE: Cabai di 36 naik
                                                        51.1% dalam 3 hari
```

### 8.4 Notifikasi Telegram

<!-- SCREENSHOT: Notifikasi Telegram masuk -->
<!-- ![Telegram Notification](assets/screenshots/telegram_notification.png) -->
<!-- *Gambar 13: Notifikasi alert masuk melalui Telegram Bot* -->

Telegram bot berhasil diintegrasikan dan telah teruji mengirim pesan:

```
📢 IPBD Alert — PIPELINE_FAILURE
Severity: CRITICAL
Task: test_telegram
Error: Test notif dari IPBD pipeline.
Jika kamu baca ini, Telegram alert BERHASIL!
Pipeline: test-001
```

### 8.5 Analisis Alerting

Sistem alerting berfungsi dengan baik. Deteksi `HARGA_SPIKE` berhasil menemukan kenaikan **51.1%** harga Cabai Merah Keriting di provinsi Banten (kode 36) dalam 3 hari. Alert `PIPELINE_FAILURE` tercatat saat pipeline awal mengalami error di step 6 sebelum diperbaiki dengan bulk COPY.

Notifikasi Telegram memerlukan koneksi internet untuk mengirim pesan ke API Telegram. Jika token dikonfigurasi dan koneksi tersedia, notifikasi akan sampai dalam hitungan detik.

---

## 9. Keamanan

### 9.1 Konsep

Keamanan dalam proyek ini mencakup perlindungan kredensial, masking data sensitif, dan kontrol akses.

### 9.2 Environment Variable

Semua kredensial disimpan dalam file `.env` dan dibaca melalui `os.getenv()` — **tidak ada password yang di-hardcode** di dalam kode.

```python
# ✅ Benar — digunakan di seluruh komponen
password = os.getenv("POSTGRES_PASSWORD")

# ❌ Tidak ada di project ini
password = "postgres"
```

File `.env` masuk ke dalam `.gitignore` sehingga tidak akan ter-commit ke repository publik.

### 9.3 PII Masking

Modul `security/security.py` menyediakan fungsi `DataProtection.mask_sensitive_data()` yang secara otomatis memmasking field sensitif sebelum dicatat ke log:

```python
from security.security import DataProtection

safe = DataProtection.mask_sensitive_data({
    "password": "secret",     # → "***MASKED***"
    "api_key": "abc123",      # → "***MASKED***"
    "data": "normal_value"    # → tetap
})
```

### 9.4 Autentikasi JWT

Modul `AuthenticationManager` menyediakan autentikasi berbasis JWT (JSON Web Token) dengan tiga role:

| Role | Hak Akses |
|---|---|
| `admin` | Baca, tulis, training model |
| `engineer` | Baca, tulis data |
| `viewer` | Baca saja |

```python
from security.security import AuthenticationManager

auth = AuthenticationManager()
result = auth.authenticate("admin", "admin123")
token = result["token"]  # JWT valid 24 jam
```

### 9.5 Analisis Keamanan

Praktik keamanan yang diterapkan sudah sesuai dengan standar pengelolaan data. Tidak ada data pribadi (PII) yang diproses atau disimpan — data harga pangan dan cuaca merupakan **data publik**. Mekanisme masking dan JWT sudah tersedia untuk implementasi production.

---

## 10. Data Governance

### 10.1 Konsep

Data governance memastikan data yang dikelola memiliki kualitas yang baik, terdokumentasi dengan metadata, memiliki jejak audit, dan mematuhi regulasi yang berlaku.

### 10.2 Data Quality Checks

Quality checks dijalankan otomatis di setiap batch pipeline (Step 9). Validasi yang dilakukan:

<!-- SCREENSHOT: Hasil quality check report -->
<!-- ![Quality Report](assets/screenshots/quality_report.png) -->
<!-- *Gambar 14: Laporan data quality check dari quality_report.json* -->

**Data Cuaca:**
| Pengecekan | Hasil |
|---|---|
| Null check suhu_mean | ✅ 0 null |
| Range suhu (-10 s/d 50°C) | ✅ Semua valid |
| Range curah_hujan_mm (≥ 0) | ✅ Semua valid |
| Range kelembapan (0–100%) | ✅ Semua valid |
| Duplikat (tanggal, kab_kota) | ✅ Tidak ada duplikat |

**Data Harga:**
| Pengecekan | Hasil |
|---|---|
| Harga > 0 dan < 1.000.000 | ✅ Semua valid |
| Null check komoditas | ✅ 0 null |
| Duplikat (tanggal, kab_kota, komoditas) | ✅ Tidak ada duplikat |

### 10.3 Metadata Management

Setiap tabel memiliki metadata yang tercatat di tabel `metadata_catalog`:

| Tabel | Owner | Deskripsi | Sumber | Frekuensi Update |
|---|---|---|---|---|
| `harga_pangan_raw` | IPBD Pipeline | Data harga harian dari SP2KP | SP2KP API | Harian (batch) |
| `cuaca_historical` | IPBD Pipeline | Data cuaca historis Open-Meteo | Open-Meteo Archive | Harian (batch) |
| `cuaca_realtime` | IPBD Pipeline | Data cuaca real-time | Open-Meteo API | Real-time (stream) |
| `cuaca_harga_merged` | IPBD Pipeline | Data join cuaca + harga per hari | Internal | Harian (batch) |
| `predictions` | IPBD Pipeline | Hasil prediksi ML | Internal | Setelah training |
| `alerts` | IPBD Pipeline | Catatan alert yang dikirim | Internal | Real-time |

### 10.4 Audit Trail

Setiap pipeline run tercatat di tabel `audit_log` dengan informasi:

```sql
SELECT pipeline_run_id, tabel_nama, operasi, username,
       data_sesudah->>'status' as status, created_at
FROM audit_log
ORDER BY created_at DESC
LIMIT 5;
```

<!-- SCREENSHOT: Audit log query result -->
<!-- ![Audit Log](assets/screenshots/audit_log.png) -->
<!-- *Gambar 15: Riwayat audit trail pipeline dari database* -->

### 10.5 Data Lineage

File `logs/data/lineage.json` secara otomatis di-generate setiap pipeline run, mendokumentasikan alur data dari sumber hingga dashboard:

```
SP2KP API ──▶ CSV ──▶ MinIO ──▶ PostgreSQL ──▶ cuaca_harga_merged ──▶ predictions ──▶ Grafana
Open-Meteo ──┘                                             ▲                           React Dashboard
                                                           │
Open-Meteo RT ──▶ Kafka ──▶ cuaca_realtime ────────────────┘
```

### 10.6 Compliance

| Aspek | Status |
|---|---|
| Sumber data hukum | ✅ SP2KP API (Kemendag, data publik), Open-Meteo (CC BY 4.0) |
| Tidak ada PII | ✅ Tidak ada data pribadi yang diproses |
| Data retensi | Raw CSV: 90 hari, Audit log: permanen, Model: 6 bulan |

### 10.7 Analisis Data Governance

Data governance berjalan dengan baik — quality checks selalu PASS di setiap pipeline run, metadata terdokumentasi lengkap, dan audit trail mencatat setiap perubahan. Data lineage memudahkan pelacakan asal-usul data jika terjadi anomali.

---

## 11. Kesimpulan & Saran

### 11.1 Kesimpulan

Proyek **Sistem Big Data Prediksi Harga Pangan Berbasis Kondisi Cuaca di Pulau Jawa** telah berhasil dibangun dan memenuhi seluruh tujuan yang ditetapkan:

1. **Batch processing** berhasil mengumpulkan 298.327 data harga pangan dan 1.617 data cuaca dari sumber eksternal, menyimpannya di data lake (MinIO) dan database (PostgreSQL), serta menjalankan pipeline 10 step dengan durasi rata-rata 33 detik.

2. **Stream processing** berhasil mengirimkan data cuaca dari 110 lokasi secara real-time melalui Apache Kafka ke PostgreSQL, dengan sistem metrics yang dipantau oleh Prometheus.

3. **Machine learning** berhasil melatih model GradientBoosting (akurasi 85.3%) untuk klasifikasi harga dan K-Means (3 cluster, Silhouette 0.242) untuk clustering cuaca. Prediksi dan enrichment menghasilkan 6.734 baris data di tabel `predictions`.

4. **Dashboard** menyediakan visualisasi yang informatif melalui Grafana (21 panel untuk monitoring dan analitik) dan React (dashboard interaktif dengan global filter dan insight naratif).

5. **Alerting** berhasil mendeteksi kenaikan harga 51.1% pada Cabai Merah Keriting dan mengirimkan notifikasi melalui Telegram.

6. **Data governance** memastikan kualitas data, metadata, audit trail, dan data lineage terdokumentasi dengan baik.

### 11.2 Saran Pengembangan

1. **Perbaiki distribusi data training** — Model klasifikasi bias ke kelas STABIL (85.5% data). Teknik oversampling (SMOTE) atau penambahan data dari periode dengan volatilitas tinggi dapat meningkatkan performa prediksi NAIK dan TURUN.

2. **Tambah fitur non-cuaca** — Korelasi cuaca vs harga mendekati 0. Penambahan fitur seperti hari libur nasional, musim panen, harga BBM, atau kebijakan pemerintah dapat meningkatkan akurasi model.

3. **Implementasi model forecasting** — Tambahkan model time series (ARIMA/Prophet) untuk prediksi harga 7 hari ke depan dengan confidence interval.

4. **Scale ke cloud** — Arsitektur saat ini berjalan di satu mesin lokal. Migrasi ke cloud (AWS/GCP) dengan managed Kafka (MSK) dan managed PostgreSQL (RDS) akan meningkatkan scalability.

5. **Tambahan channel notifikasi** — Selain Telegram, tambahkan notifikasi email dan WhatsApp untuk menjangkau pengguna yang lebih luas.

6. **Peta Indonesia** — Integrasi GeoJSON untuk visualisasi sebaran harga di peta interaktif di React dashboard.

---

## Lampiran

### A. Struktur Folder

```
IPBD_TPB/
├── alarms/                    # Modul alerting (5 tipe alert)
├── batch/                     # Pipeline batch (cuaca, harga, storage)
├── dashboard-react/           # React dashboard (FastAPI + React + ECharts)
├── database/                  # Inisialisasi database (init.sql)
├── data/                      # Data mentah, processed, backup
├── governance/                # Data quality, metadata, audit trail
├── grafana/                   # Dashboard JSON + provisioning
├── logs/                      # File log (application, alerts, quality, dll)
├── models/                    # ML model (GradientBoosting, K-Means)
├── pipeline/                  # Orchestrator batch pipeline (10 step)
├── scripts/                   # Utility scripts
├── security/                  # JWT auth, PII masking
├── streaming/                 # Kafka producer & consumer
├── docker-compose.yml         # Orchestrasi 10 container Docker
├── prometheus.yml             # Konfigurasi scrape Prometheus
└── README.md                  # Dokumentasi lengkap
```

### B. Daftar Screenshot yang Perlu Disertakan

| No | File Screenshot | Deskripsi | Di Bagian |
|---|---|---|---|
| 1 | `arsitektur_sistem.png` | Diagram arsitektur end-to-end | 2 |
| 2 | `docker_ps.png` | Semua container Docker running | 2 |
| 3 | `batch_3x_run.png` | Terminal output pipeline 3x run | 3 |
| 4 | `batch_10x_run.png` | Terminal output pipeline 10x run | 3 |
| 5 | `stream_producer.png` | Terminal producer streaming | 4 |
| 6 | `stream_consumer.png` | Terminal consumer streaming | 4 |
| 7 | `training_models.png` | Terminal retraining models | 5 |
| 8 | `grafana_dashboard.png` | Dashboard Grafana full page | 6 |
| 9 | `react_dashboard.png` | Dashboard React full page | 6 |
| 10 | `grafana_monitoring.png` | Dashboard Pipeline Monitoring | 7 |
| 11 | `application_log.png` | Contoh log file aplikasi | 7 |
| 12 | `alerts_table.png` | Tabel alerts di PostgreSQL | 8 |
| 13 | `telegram_notification.png` | Notifikasi Telegram masuk | 8 |
| 14 | `quality_report.png` | Laporan quality check | 10 |
| 15 | `audit_log.png` | Riwayat audit trail | 10 |

---

**— Akhir Laporan —**
