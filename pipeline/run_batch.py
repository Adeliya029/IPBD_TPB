"""
Batch Pipeline Orchestrator — Menjalankan seluruh batch pipeline secara berurutan.

Urutan step:
1.  Download data cuaca (panggil histori_cuaca.py)
2.  Download data harga (panggil batch_pangan.py)
3.  Cleaning cuaca (panggil clean_cuaca.py)
4.  Cleaning harga (panggil clean_harga.py)
5.  Upload ke MinIO (upload_minio.py)
6.  Load ke PostgreSQL (insert ke tabel)
7.  Merge cuaca + harga (buat tabel cuaca_harga_merged)
8.  Training/update model (panggil price_prediction_model.py)
9.  Jalankan data quality checks (panggil quality_checks.py)
10. Log semua ke audit_trail

Fitur: pipeline_run_id UUID, logging tiap step, retry logic, alert jika gagal.
"""

import os
import sys
import uuid
import time
import subprocess
from io import StringIO
import pandas as pd
from datetime import datetime

# Tambahkan project root ke sys.path
PROJECT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, PROJECT_ROOT)

from logs.monitoring import StructuredLogger
from alerts.alert_manager import PanganAlertManager
from governance.audit_trail import AuditTrail
from governance.quality_checks import DataQualityChecker, run_all_quality_checks
from dotenv import load_dotenv

load_dotenv()

# Logger
logger = StructuredLogger('BatchPipeline')


class BatchPipeline:
    """
    Orchestrator untuk menjalankan seluruh batch pipeline.
    Setiap run memiliki UUID unik (pipeline_run_id).
    """

    def __init__(self):
        self.pipeline_run_id = f"run-{uuid.uuid4().hex[:8]}"
        self.start_time = None
        self.end_time = None
        self.steps_status = {}

        # Konfigurasi database
        self.db_config = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', '5440')),
            'dbname': os.getenv('POSTGRES_DB', 'harga_pangan'),
            'user': os.getenv('POSTGRES_USER', 'postgres'),
            'password': os.getenv('POSTGRES_PASSWORD', 'postgres'),
        }

        # Komponen pendukung
        self.alert_manager = PanganAlertManager(db_config=self.db_config)
        self.audit_trail = AuditTrail(db_config=self.db_config)

        # Retry config
        self.max_retries = 3
        self.retry_delay = 5  # detik

    # ============================================================
    # MAIN: Jalankan seluruh pipeline
    # ============================================================

    def run(self):
        """
        Jalankan seluruh batch pipeline secara berurutan.
        Jika satu step gagal setelah retry, pipeline tetap lanjut
        ke step berikutnya (dengan catatan di log).
        """
        self.start_time = datetime.now()

        logger.info(
            f"🚀 Pipeline dimulai: {self.pipeline_run_id}",
            pipeline_run_id=self.pipeline_run_id
        )

        print("=" * 60)
        print(f"BATCH PIPELINE — {self.pipeline_run_id}")
        print(f"Start: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        # Definisi semua step
        steps = [
            ("1_download_cuaca", self.step_download_cuaca),
            ("2_download_harga", self.step_download_harga),
            ("3_clean_cuaca", self.step_clean_cuaca),
            ("4_clean_harga", self.step_clean_harga),
            ("5_upload_minio", self.step_upload_minio),
            ("6_load_postgres", self.step_load_postgres),
            ("7_merge_data", self.step_merge_data),
            ("8_train_model", self.step_train_model),
            ("9_quality_checks", self.step_quality_checks),
            ("10_audit_log", self.step_audit_log),
        ]

        failed_steps = []

        for step_name, step_func in steps:
            print(f"\n{'─'*50}")
            print(f"▶ Step: {step_name}")

            success = self._run_with_retry(step_name, step_func)
            self.steps_status[step_name] = "SUCCESS" if success else "FAILED"

            if not success:
                failed_steps.append(step_name)
                # Kirim alert
                self.alert_manager.check_pipeline_failure(
                    step_name=step_name,
                    error_message=f"Step gagal setelah {self.max_retries} percobaan",
                    pipeline_run_id=self.pipeline_run_id
                )

        # Selesai
        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()

        print(f"\n{'='*60}")
        print(f"PIPELINE SELESAI — {self.pipeline_run_id}")
        print(f"Durasi: {duration:.1f} detik")
        print(f"Step berhasil: {sum(1 for s in self.steps_status.values() if s == 'SUCCESS')}/{len(steps)}")
        print(f"Step gagal: {len(failed_steps)}")
        if failed_steps:
            print(f"  ❌ {', '.join(failed_steps)}")
        print("=" * 60)

        logger.info(
            f"Pipeline selesai: {self.pipeline_run_id}",
            pipeline_run_id=self.pipeline_run_id,
            duration_seconds=duration,
            failed_steps=failed_steps
        )

        return len(failed_steps) == 0

    # ============================================================
    # RETRY LOGIC
    # ============================================================

    def _run_with_retry(self, step_name: str, step_func, max_retries: int = None):
        """
        Jalankan step dengan retry logic.

        Args:
            step_name: Nama step untuk logging
            step_func: Fungsi yang akan dijalankan
            max_retries: Override max retry (default dari self.max_retries)
        """
        retries = max_retries or self.max_retries

        for attempt in range(1, retries + 1):
            try:
                step_func()

                # Log ke audit trail
                self.audit_trail.log_step(
                    pipeline_run_id=self.pipeline_run_id,
                    step_name=step_name,
                    status="SUCCESS",
                    detail={'attempt': attempt}
                )

                print(f"  ✅ {step_name} berhasil (attempt {attempt})")
                logger.info(
                    f"Step berhasil: {step_name}",
                    step=step_name, attempt=attempt
                )
                return True

            except Exception as e:
                logger.warning(
                    f"Step gagal: {step_name} (attempt {attempt}/{retries}): {str(e)}",
                    step=step_name, attempt=attempt
                )
                print(f"  ⚠️ Attempt {attempt}/{retries} gagal: {str(e)}")

                if attempt < retries:
                    print(f"  ⏳ Retry dalam {self.retry_delay} detik...")
                    time.sleep(self.retry_delay)

        # Semua retry gagal
        self.audit_trail.log_step(
            pipeline_run_id=self.pipeline_run_id,
            step_name=step_name,
            status="FAILED",
            detail={'attempts': retries}
        )
        print(f"  ❌ {step_name} GAGAL setelah {retries} percobaan")
        return False

    # ============================================================
    # STEP 1: Download data cuaca
    # ============================================================

    def step_download_cuaca(self):
        """Download data cuaca dari Open-Meteo Archive API."""
        script = os.path.join(PROJECT_ROOT, 'batch', 'cuaca', 'histori_cuaca.py')

        # Cek apakah data sudah ada (skip jika sudah)
        raw_dir = os.path.join(PROJECT_ROOT, 'data', 'raw', 'cuaca')
        if os.path.exists(raw_dir) and any(f.endswith('.csv') for f in os.listdir(raw_dir)):
            print("  ℹ️ Data cuaca raw sudah ada, skip download")
            logger.info("Data cuaca raw sudah ada, skip download")
            return

        if os.path.exists(script):
            subprocess.run([sys.executable, script], check=True, cwd=PROJECT_ROOT)
        else:
            logger.info(f"Script tidak ditemukan: {script}. Skip step ini.")
            print(f"  ℹ️ Script {script} tidak ada, skip")

    # ============================================================
    # STEP 2: Download data harga
    # ============================================================

    def step_download_harga(self):
        """Download data harga dari SP2KP API."""
        script = os.path.join(PROJECT_ROOT, 'batch', 'harga', 'batch_pangan.py')

        # Cek apakah data sudah ada
        raw_dir = os.path.join(PROJECT_ROOT, 'data', 'raw', 'harga')
        if os.path.exists(raw_dir) and any(f.endswith('.csv') for f in os.listdir(raw_dir)):
            print("  ℹ️ Data harga raw sudah ada, skip download")
            logger.info("Data harga raw sudah ada, skip download")
            return

        if os.path.exists(script):
            subprocess.run([sys.executable, script], check=True, cwd=PROJECT_ROOT)
        else:
            logger.info(f"Script tidak ditemukan: {script}. Skip step ini.")
            print(f"  ℹ️ Script {script} tidak ada, skip")

    # ============================================================
    # STEP 3: Cleaning cuaca
    # ============================================================

    def step_clean_cuaca(self):
        """Cleaning data cuaca."""
        script = os.path.join(PROJECT_ROOT, 'batch', 'cuaca', 'clean_cuaca.py')

        if os.path.exists(script):
            subprocess.run([sys.executable, script], check=True, cwd=PROJECT_ROOT)
        else:
            logger.info("clean_cuaca.py tidak ditemukan, skip")

    # ============================================================
    # STEP 4: Cleaning harga
    # ============================================================

    def step_clean_harga(self):
        """Cleaning data harga."""
        script = os.path.join(PROJECT_ROOT, 'batch', 'harga', 'clean_harga.py')

        if os.path.exists(script):
            subprocess.run([sys.executable, script], check=True, cwd=PROJECT_ROOT)
        else:
            logger.info("clean_harga.py tidak ditemukan, skip")

    # ============================================================
    # STEP 5: Upload ke MinIO
    # ============================================================

    def step_upload_minio(self):
        """Upload data raw dan processed ke MinIO."""
        try:
            from batch.storage.upload_minio import MinioStorage

            storage = MinioStorage()

            # Upload raw files
            for zone in ['raw', 'processed']:
                for dtype in ['cuaca', 'harga']:
                    folder = os.path.join(PROJECT_ROOT, 'data', zone, dtype)
                    if not os.path.exists(folder):
                        continue

                    bucket = f"{zone}-zone"
                    for f in os.listdir(folder):
                        if f.endswith('.csv'):
                            file_path = os.path.join(folder, f)
                            object_name = f"{dtype}/{f}"
                            try:
                                storage.upload_file(bucket, object_name, file_path)
                            except Exception as e:
                                logger.warning(f"Upload gagal {f}: {str(e)}")

            logger.info("Upload ke MinIO selesai")

        except Exception as e:
            logger.warning(f"MinIO tidak tersedia: {str(e)}. Skip upload.")
            print(f"  ⚠️ MinIO tidak tersedia: {str(e)}")

    # ============================================================
    # STEP 6: Load ke PostgreSQL
    # ============================================================

    def step_load_postgres(self):
        """Load data CSV ke PostgreSQL via bulk COPY."""
        import psycopg

        conn = psycopg.connect(**self.db_config)

        # Load cuaca historical
        cuaca_dir = os.path.join(PROJECT_ROOT, 'data', 'processed', 'cuaca')
        if os.path.exists(cuaca_dir):
            for f in os.listdir(cuaca_dir):
                if f.endswith('.csv'):
                    df = pd.read_csv(os.path.join(cuaca_dir, f))
                    self._bulk_insert_cuaca(conn, df)
                    logger.info(f"Loaded cuaca: {f} ({len(df)} baris)")

        # Load harga pangan
        harga_dir = os.path.join(PROJECT_ROOT, 'data', 'processed', 'harga')
        if os.path.exists(harga_dir):
            for f in os.listdir(harga_dir):
                if f.endswith('.csv'):
                    df = pd.read_csv(os.path.join(harga_dir, f))
                    self._bulk_insert_harga(conn, df)
                    logger.info(f"Loaded harga: {f} ({len(df)} baris)")

        conn.close()
        logger.info("Load ke PostgreSQL selesai")

    def _bulk_insert_cuaca(self, conn, df):
        required = ['tanggal', 'kab_kota']
        if not all(c in df.columns for c in required):
            logger.warning(f"Kolom kurang: {df.columns.tolist()}")
            return

        cols = ['tanggal', 'provinsi', 'kab_kota', 'latitude', 'longitude',
                'suhu_mean', 'suhu_max', 'suhu_min', 'curah_hujan_mm',
                'kelembapan', 'kecepatan_angin', 'tekanan_udara', 'awan_persen']
        buf = StringIO()
        df[cols].to_csv(buf, index=False, header=False, na_rep='\\N')
        buf.seek(0)
        with conn.cursor() as cur:
            with cur.copy("COPY cuaca_historical (tanggal, provinsi, kab_kota, latitude, longitude, suhu_mean, suhu_max, suhu_min, curah_hujan_mm, kelembapan, kecepatan_angin, tekanan_udara, awan_persen) FROM STDIN WITH (FORMAT CSV, NULL '\\N')") as copy:
                for line in buf:
                    copy.write(line)
        conn.commit()
        logger.info(f"Bulk insert cuaca: {len(df)} baris")

    def _bulk_insert_harga(self, conn, df):
        out = df[['tanggal', 'provinsi_id', 'kab_kota', 'komoditas', 'harga', 'satuan']].copy()
        out['provinsi_id'] = out['provinsi_id'].astype(str)
        out.rename(columns={'provinsi_id': 'provinsi'}, inplace=True)
        out['pipeline_run_id'] = self.pipeline_run_id

        cols = ['tanggal', 'provinsi', 'kab_kota', 'komoditas', 'harga', 'satuan', 'pipeline_run_id']
        buf = StringIO()
        out[cols].to_csv(buf, index=False, header=False, na_rep='\\N')
        buf.seek(0)
        with conn.cursor() as cur:
            with cur.copy("COPY harga_pangan_raw (tanggal, provinsi, kab_kota, komoditas, harga, satuan, pipeline_run_id) FROM STDIN WITH (FORMAT CSV, NULL '\\N')") as copy:
                for line in buf:
                    copy.write(line)
        conn.commit()
        logger.info(f"Bulk insert harga: {len(df)} baris")

    # ============================================================
    # STEP 7: Merge cuaca + harga
    # ============================================================

    def step_merge_data(self):
        """Merge data cuaca dan harga ke tabel cuaca_harga_merged."""
        import psycopg

        conn = psycopg.connect(**self.db_config)
        cur = conn.cursor()

        # Merge di level PostgreSQL
        cur.execute("""
            INSERT INTO cuaca_harga_merged
                (tanggal, provinsi, kab_kota, komoditas, harga,
                 suhu_mean, curah_hujan_mm, kelembapan, kecepatan_angin,
                 tekanan_udara)
            SELECT
                h.tanggal,
                h.provinsi,
                h.kab_kota,
                h.komoditas,
                h.harga,
                c.suhu_mean,
                c.curah_hujan_mm,
                c.kelembapan,
                c.kecepatan_angin,
                c.tekanan_udara
            FROM harga_pangan_raw h
            JOIN cuaca_historical c
                ON h.tanggal = c.tanggal
                AND UPPER(h.kab_kota) = UPPER(c.kab_kota)
            ON CONFLICT DO NOTHING
        """)

        merged_count = cur.rowcount
        conn.commit()

        # Update lag features (harga_lag_7d, harga_change_pct, curah_hujan_lag_7d)
        cur.execute("""
            UPDATE cuaca_harga_merged m
            SET
                harga_lag_7d = sub.harga_lag,
                harga_change_pct = CASE
                    WHEN sub.harga_lag > 0
                    THEN ((m.harga - sub.harga_lag) / sub.harga_lag * 100)
                    ELSE 0
                END,
                curah_hujan_lag_7d = sub.hujan_lag
            FROM (
                SELECT
                    m2.id,
                    LAG(m2.harga, 7) OVER (
                        PARTITION BY m2.kab_kota, m2.komoditas
                        ORDER BY m2.tanggal
                    ) as harga_lag,
                    LAG(m2.curah_hujan_mm, 7) OVER (
                        PARTITION BY m2.kab_kota, m2.komoditas
                        ORDER BY m2.tanggal
                    ) as hujan_lag
                FROM cuaca_harga_merged m2
            ) sub
            WHERE m.id = sub.id
        """)

        conn.commit()
        cur.close()
        conn.close()

        logger.info(f"Merge selesai: {merged_count} baris baru")
        print(f"  📊 Merged {merged_count} baris ke cuaca_harga_merged")

    # ============================================================
    # STEP 8: Train model
    # ============================================================

    def step_train_model(self):
        """Training/update model prediksi harga."""
        try:
            from models.price_prediction_model import train_model_from_data
            model = train_model_from_data()
            logger.info("Model training selesai")
            print("  🤖 Model training selesai")
        except Exception as e:
            logger.warning(f"Model training gagal, gunakan synthetic: {str(e)}")
            from models.price_prediction_model import train_synthetic_model
            model = train_synthetic_model()
            print("  🤖 Model training (synthetic) selesai")

    # ============================================================
    # STEP 9: Quality checks
    # ============================================================

    def step_quality_checks(self):
        """Jalankan data quality checks."""
        report = run_all_quality_checks()
        status = report.get('overall_status', 'UNKNOWN')
        print(f"  🔍 Quality check: {status}")

        if status == 'FAIL':
            logger.warning("Quality check GAGAL — ada data yang tidak valid")

    # ============================================================
    # STEP 10: Audit log
    # ============================================================

    def step_audit_log(self):
        """Log pipeline run ke audit_trail dan generate lineage."""
        # Log pipeline run
        self.audit_trail.log_pipeline_run(
            pipeline_run_id=self.pipeline_run_id,
            tabel_nama="batch_pipeline",
            operasi="INSERT",
            username="pipeline",
            status="COMPLETED",
            start_time=self.start_time.isoformat() if self.start_time else None,
            end_time=datetime.now().isoformat(),
            data_sesudah={
                'steps': self.steps_status,
                'pipeline_run_id': self.pipeline_run_id,
            }
        )

        # Generate data lineage
        self.audit_trail.log_data_lineage()

        logger.info("Audit log dan lineage berhasil dicatat")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    pipeline = BatchPipeline()
    success = pipeline.run()

    if success:
        print("\n✅ Pipeline berhasil 100%!")
    else:
        print("\n⚠️ Pipeline selesai dengan beberapa error. Cek log untuk detail.")

    sys.exit(0 if success else 1)
