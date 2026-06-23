-- ============================================================
-- IPBD_TPB — Schema Database Lengkap
-- Sistem Analisis & Prediksi Harga Pangan (Pulau Jawa)
-- ============================================================

-- ============================================================
-- 1. TABEL CUACA REALTIME (SUDAH ADA — dipertahankan)
-- ============================================================

CREATE TABLE IF NOT EXISTS cuaca_realtime (
    id SERIAL PRIMARY KEY,
    waktu TIMESTAMP,
    provinsi VARCHAR(100),
    kab_kota VARCHAR(100),
    -- Kolom cuaca dari API lama
    suhu FLOAT,
    kelembapan FLOAT,
    curah_hujan FLOAT,
    kecepatan_angin FLOAT,
    tekanan_udara FLOAT,
    kondisi_cuaca VARCHAR(100),
    deskripsi_cuaca VARCHAR(255),
    sumber VARCHAR(100),
    -- Kolom cuaca dari Open-Meteo (nama konsisten)
    suhu_mean FLOAT,
    suhu_max FLOAT,
    suhu_min FLOAT,
    curah_hujan_mm FLOAT,
    awan_persen FLOAT,
    -- Hasil clustering K-Means
    cluster_label INTEGER,
    cluster_nama VARCHAR(100)
);

-- Index untuk cuaca_realtime
CREATE INDEX IF NOT EXISTS idx_cuaca_realtime_waktu ON cuaca_realtime(waktu);
CREATE INDEX IF NOT EXISTS idx_cuaca_realtime_provinsi ON cuaca_realtime(provinsi);
CREATE INDEX IF NOT EXISTS idx_cuaca_realtime_kab_kota ON cuaca_realtime(kab_kota);

-- ============================================================
-- 2. TABEL HARGA PANGAN RAW
--    Menyimpan data harga mentah dari SP2KP API (Kemendag)
-- ============================================================

CREATE TABLE IF NOT EXISTS harga_pangan_raw (
    id SERIAL PRIMARY KEY,
    tanggal DATE,
    provinsi VARCHAR(100),
    kab_kota VARCHAR(100),
    komoditas VARCHAR(100),
    harga DECIMAL(15,2),
    satuan VARCHAR(50),
    pipeline_run_id VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index untuk query harga pangan
CREATE INDEX IF NOT EXISTS idx_harga_raw_tanggal ON harga_pangan_raw(tanggal);
CREATE INDEX IF NOT EXISTS idx_harga_raw_provinsi ON harga_pangan_raw(provinsi);
CREATE INDEX IF NOT EXISTS idx_harga_raw_komoditas ON harga_pangan_raw(komoditas);
CREATE INDEX IF NOT EXISTS idx_harga_raw_kab_kota ON harga_pangan_raw(kab_kota);
CREATE INDEX IF NOT EXISTS idx_harga_raw_tanggal_komoditas ON harga_pangan_raw(tanggal, komoditas);

-- ============================================================
-- 3. TABEL CUACA HISTORICAL
--    Menyimpan data cuaca historis dari Open-Meteo Archive API
-- ============================================================

CREATE TABLE IF NOT EXISTS cuaca_historical (
    id SERIAL PRIMARY KEY,
    tanggal DATE,
    provinsi VARCHAR(100),
    kab_kota VARCHAR(100),
    latitude FLOAT,
    longitude FLOAT,
    suhu_mean FLOAT,
    suhu_max FLOAT,
    suhu_min FLOAT,
    curah_hujan_mm FLOAT,
    kelembapan FLOAT,
    kecepatan_angin FLOAT,
    tekanan_udara FLOAT,
    awan_persen FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index untuk query cuaca historical
CREATE INDEX IF NOT EXISTS idx_cuaca_hist_tanggal ON cuaca_historical(tanggal);
CREATE INDEX IF NOT EXISTS idx_cuaca_hist_provinsi ON cuaca_historical(provinsi);
CREATE INDEX IF NOT EXISTS idx_cuaca_hist_kab_kota ON cuaca_historical(kab_kota);
CREATE INDEX IF NOT EXISTS idx_cuaca_hist_tanggal_kab ON cuaca_historical(tanggal, kab_kota);

-- ============================================================
-- 4. TABEL CUACA HARGA MERGED
--    Data gabungan cuaca + harga untuk input model ML
-- ============================================================

CREATE TABLE IF NOT EXISTS cuaca_harga_merged (
    id SERIAL PRIMARY KEY,
    tanggal DATE,
    provinsi VARCHAR(100),
    kab_kota VARCHAR(100),
    komoditas VARCHAR(100),
    harga DECIMAL(15,2),
    suhu_mean FLOAT,
    curah_hujan_mm FLOAT,
    kelembapan FLOAT,
    kecepatan_angin FLOAT,
    tekanan_udara FLOAT,
    harga_lag_7d DECIMAL(15,2),
    harga_change_pct FLOAT,
    curah_hujan_lag_7d FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index untuk query merged data
CREATE INDEX IF NOT EXISTS idx_merged_tanggal ON cuaca_harga_merged(tanggal);
CREATE INDEX IF NOT EXISTS idx_merged_provinsi ON cuaca_harga_merged(provinsi);
CREATE INDEX IF NOT EXISTS idx_merged_komoditas ON cuaca_harga_merged(komoditas);
CREATE INDEX IF NOT EXISTS idx_merged_tanggal_komoditas ON cuaca_harga_merged(tanggal, komoditas);

-- ============================================================
-- 5. TABEL PREDICTIONS
--    Menyimpan hasil prediksi model ML (NAIK/TURUN/STABIL)
-- ============================================================

CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    tanggal_prediksi DATE,
    provinsi VARCHAR(100),
    kab_kota VARCHAR(100),
    komoditas VARCHAR(100),
    -- Label prediksi (NAIK / TURUN / STABIL)
    prediksi_label VARCHAR(20),
    prediction_label VARCHAR(20),   -- alias, digunakan Grafana dashboard
    probabilitas_naik FLOAT,
    probabilitas_turun FLOAT,
    probabilitas_stabil FLOAT,
    confidence FLOAT,               -- confidence score (0.0-1.0)
    -- Fitur cuaca yang digunakan untuk prediksi
    fitur_cuaca JSONB,
    suhu_mean FLOAT,
    curah_hujan_mm FLOAT,
    kelembapan FLOAT,
    -- Hasil clustering K-Means
    cluster_label INTEGER,          -- 0, 1, 2, atau 3
    cluster_nama VARCHAR(100),      -- 'Cuaca Normal', 'Musim Hujan', dst
    model_version VARCHAR(50),
    pipeline_run_id VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index untuk query predictions
CREATE INDEX IF NOT EXISTS idx_pred_tanggal ON predictions(tanggal_prediksi);
CREATE INDEX IF NOT EXISTS idx_pred_provinsi ON predictions(provinsi);
CREATE INDEX IF NOT EXISTS idx_pred_komoditas ON predictions(komoditas);
CREATE INDEX IF NOT EXISTS idx_pred_label ON predictions(prediction_label);
CREATE INDEX IF NOT EXISTS idx_pred_cluster ON predictions(cluster_label);
CREATE INDEX IF NOT EXISTS idx_pred_created ON predictions(created_at);

-- ============================================================
-- 6. TABEL ALERTS
--    Menyimpan alert dari berbagai sumber
--    Tipe: SPIKE, DATA_GAP, MODEL_DEGRADATION, PIPELINE_FAILURE
-- ============================================================

CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    alert_type VARCHAR(50),             -- SPIKE, DATA_GAP, MODEL_DEGRADATION, PIPELINE_FAILURE
    severity VARCHAR(20),               -- INFO, WARNING, CRITICAL
    message TEXT,
    komoditas VARCHAR(100),
    provinsi VARCHAR(100),
    nilai_aktual FLOAT,
    nilai_threshold FLOAT,
    is_resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP
);

-- Index untuk query alerts
CREATE INDEX IF NOT EXISTS idx_alerts_type ON alerts(alert_type);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);
CREATE INDEX IF NOT EXISTS idx_alerts_resolved ON alerts(is_resolved);
CREATE INDEX IF NOT EXISTS idx_alerts_created ON alerts(created_at);

-- ============================================================
-- 7. TABEL AUDIT LOG
--    Menyimpan trail audit untuk setiap operasi pipeline
-- ============================================================

CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    tabel_nama VARCHAR(100),
    operasi VARCHAR(20),                -- INSERT, UPDATE, DELETE
    username VARCHAR(100),
    pipeline_run_id VARCHAR(50),
    row_id INTEGER,
    data_sebelum JSONB,
    data_sesudah JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index untuk query audit log
CREATE INDEX IF NOT EXISTS idx_audit_tabel ON audit_log(tabel_nama);
CREATE INDEX IF NOT EXISTS idx_audit_operasi ON audit_log(operasi);
CREATE INDEX IF NOT EXISTS idx_audit_pipeline ON audit_log(pipeline_run_id);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at);

-- ============================================================
-- 8. TABEL METADATA CATALOG
--    Dokumentasi metadata untuk setiap tabel dan kolom
-- ============================================================

CREATE TABLE IF NOT EXISTS metadata_catalog (
    id SERIAL PRIMARY KEY,
    nama_tabel VARCHAR(100),
    nama_kolom VARCHAR(100),
    tipe_data VARCHAR(50),
    deskripsi TEXT,
    owner VARCHAR(100),
    sumber_data VARCHAR(200),
    last_updated TIMESTAMP DEFAULT NOW()
);

-- Index untuk metadata catalog
CREATE INDEX IF NOT EXISTS idx_metadata_tabel ON metadata_catalog(nama_tabel);

-- ============================================================
-- SELESAI — Total 8 tabel dengan index yang sesuai
-- ============================================================

-- ============================================================
-- GRANT permissions (untuk Grafana datasource)
-- ============================================================
GRANT SELECT ON ALL TABLES IN SCHEMA public TO postgres;