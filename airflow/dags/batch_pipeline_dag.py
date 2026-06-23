"""
DAG: batch_pipeline_dag
Jadwal: Setiap hari jam 06:00 WIB (23:00 UTC sebelumnya)

Menjalankan batch pipeline lengkap 10 step:
1. Download cuaca
2. Download harga
3. Clean cuaca
4. Clean harga
5. Upload ke MinIO
6. Load ke PostgreSQL
7. Merge data
8. Train model (+ clustering)
9. Quality checks
10. Audit log

Fitur keamanan:
- on_failure_callback → kirim notifikasi Telegram
- Email alert via SMTP (jika dikonfigurasi)
- Password diambil dari Airflow Variables / environment, TIDAK hardcode

Severity log: INFO, DEBUG, WARNING, ERROR/FATAL
"""

import os
import sys
import logging
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago

# ─────────────────────────────────────────
# KONFIGURASI DAG
# ─────────────────────────────────────────

PROJECT_DIR = os.getenv("AIRFLOW__CORE__DAGS_FOLDER", "/opt/airflow/dags")
PROJECT_ROOT = os.path.join(PROJECT_DIR, "..", "project")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

logger = logging.getLogger(__name__)

DEFAULT_ARGS = {
    "owner": "ipbd-team",
    "depends_on_past": False,
    "email": [],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=2),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=10),
}


# ─────────────────────────────────────────
# CALLBACK: Kirim alert saat task GAGAL
# ─────────────────────────────────────────

def on_failure_callback(context):
    """
    Dipanggil otomatis oleh Airflow saat task gagal.
    Mengirim notifikasi ke Telegram (jika dikonfigurasi).
    Severity: FATAL — task pipeline gagal setelah semua retry.
    """
    dag_id = context.get("dag").dag_id
    task_id = context.get("task_instance").task_id
    run_id = context.get("run_id", "unknown")
    execution_date = context.get("execution_date")
    exception = context.get("exception")

    # Log FATAL ke file
    logger.fatal(
        f"[FATAL] Airflow task GAGAL — DAG: {dag_id}, Task: {task_id}, "
        f"Run ID: {run_id}, Error: {exception}"
    )
    logger.warning(
        f"[WARNING] Task {task_id} telah di-retry {DEFAULT_ARGS['retries']}x dan tetap gagal"
    )

    # Kirim notifikasi Telegram
    try:
        sys.path.insert(0, PROJECT_ROOT)
        from alerts.alert_manager import PanganAlertManager

        alert = PanganAlertManager()
        alert.check_pipeline_failure(
            step_name=f"{dag_id}.{task_id}",
            error_message=f"Task gagal setelah {DEFAULT_ARGS['retries']} retry. Error: {str(exception)}",
            pipeline_run_id=run_id
        )
        logger.info(f"[INFO] Notifikasi alert dikirim untuk task gagal: {task_id}")
    except Exception as e:
        logger.error(f"[ERROR] Gagal kirim alert Telegram: {str(e)}")


def on_success_callback(context):
    """Log INFO saat seluruh DAG berhasil."""
    dag_id = context.get("dag").dag_id
    run_id = context.get("run_id", "unknown")
    logger.info(f"[INFO] DAG selesai sukses — {dag_id}, Run ID: {run_id}")


# ─────────────────────────────────────────
# TASK FUNCTIONS
# ─────────────────────────────────────────

def task_download_cuaca(**kwargs):
    """Task 1: Download data cuaca historis dari Open-Meteo."""
    logger.info("[INFO] Memulai task download cuaca...")
    sys.path.insert(0, PROJECT_ROOT)

    script = os.path.join(PROJECT_ROOT, "batch", "cuaca", "histori_cuaca.py")
    raw_dir = os.path.join(PROJECT_ROOT, "data", "raw", "cuaca")

    if os.path.exists(raw_dir) and any(
        f.endswith(".csv") for f in os.listdir(raw_dir)
    ):
        logger.info("[INFO] Data cuaca raw sudah ada, skip download")
        return "SKIPPED"

    if os.path.exists(script):
        import subprocess
        result = subprocess.run([sys.executable, script], capture_output=True, text=True, cwd=PROJECT_ROOT)
        if result.returncode != 0:
            logger.error(f"[ERROR] Download cuaca gagal: {result.stderr}")
            raise RuntimeError(f"histori_cuaca.py gagal: {result.stderr}")
        logger.info(f"[INFO] Download cuaca selesai: {result.stdout[:200]}")
    else:
        logger.warning(f"[WARNING] Script tidak ditemukan: {script}")

    return "SUCCESS"


def task_download_harga(**kwargs):
    """Task 2: Download data harga dari SP2KP API."""
    logger.info("[INFO] Memulai task download harga...")
    sys.path.insert(0, PROJECT_ROOT)

    script = os.path.join(PROJECT_ROOT, "batch", "harga", "batch_pangan.py")
    raw_dir = os.path.join(PROJECT_ROOT, "data", "raw", "harga")

    if os.path.exists(raw_dir) and any(
        f.endswith(".csv") for f in os.listdir(raw_dir)
    ):
        logger.info("[INFO] Data harga raw sudah ada, skip download")
        return "SKIPPED"

    if os.path.exists(script):
        import subprocess
        result = subprocess.run([sys.executable, script], capture_output=True, text=True, cwd=PROJECT_ROOT)
        if result.returncode != 0:
            logger.error(f"[ERROR] Download harga gagal: {result.stderr}")
            raise RuntimeError(f"batch_pangan.py gagal: {result.stderr}")
        logger.info(f"[INFO] Download harga selesai: {result.stdout[:200]}")
    else:
        logger.warning(f"[WARNING] Script tidak ditemukan: {script}")

    return "SUCCESS"


def task_clean_cuaca(**kwargs):
    """Task 3: Cleaning data cuaca."""
    logger.info("[INFO] Memulai task clean cuaca...")
    sys.path.insert(0, PROJECT_ROOT)
    script = os.path.join(PROJECT_ROOT, "batch", "cuaca", "clean_cuaca.py")
    if os.path.exists(script):
        import subprocess
        result = subprocess.run([sys.executable, script], capture_output=True, text=True, cwd=PROJECT_ROOT)
        if result.returncode != 0:
            raise RuntimeError(f"clean_cuaca.py gagal: {result.stderr}")
        logger.info("[INFO] Clean cuaca selesai")
    else:
        logger.warning("[WARNING] clean_cuaca.py tidak ditemukan, skip")
    return "SUCCESS"


def task_clean_harga(**kwargs):
    """Task 4: Cleaning data harga."""
    logger.info("[INFO] Memulai task clean harga...")
    sys.path.insert(0, PROJECT_ROOT)
    script = os.path.join(PROJECT_ROOT, "batch", "harga", "clean_harga.py")
    if os.path.exists(script):
        import subprocess
        result = subprocess.run([sys.executable, script], capture_output=True, text=True, cwd=PROJECT_ROOT)
        if result.returncode != 0:
            raise RuntimeError(f"clean_harga.py gagal: {result.stderr}")
        logger.info("[INFO] Clean harga selesai")
    else:
        logger.warning("[WARNING] clean_harga.py tidak ditemukan, skip")
    return "SUCCESS"


def task_upload_minio(**kwargs):
    """Task 5: Upload data ke MinIO."""
    logger.debug("[DEBUG] Memulai upload ke MinIO...")
    sys.path.insert(0, PROJECT_ROOT)
    try:
        from batch.storage.upload_minio import MinioStorage
        storage = MinioStorage()
        for zone in ["raw", "processed"]:
            for dtype in ["cuaca", "harga"]:
                folder = os.path.join(PROJECT_ROOT, "data", zone, dtype)
                if not os.path.exists(folder):
                    continue
                bucket = f"{zone}-zone"
                for f in os.listdir(folder):
                    if f.endswith(".csv"):
                        file_path = os.path.join(folder, f)
                        storage.upload_file(bucket, f"{dtype}/{f}", file_path)
                        logger.debug(f"[DEBUG] Upload: {dtype}/{f} → {bucket}")
        logger.info("[INFO] Upload ke MinIO selesai")
    except Exception as e:
        logger.warning(f"[WARNING] MinIO tidak tersedia: {str(e)}. Skip upload.")
    return "SUCCESS"


def task_load_postgres(**kwargs):
    """Task 6: Load CSV ke PostgreSQL."""
    logger.info("[INFO] Memulai load data ke PostgreSQL...")
    sys.path.insert(0, PROJECT_ROOT)
    from pipeline.run_batch import BatchPipeline
    pipeline = BatchPipeline()
    pipeline.step_load_postgres()
    logger.info("[INFO] Load ke PostgreSQL selesai")
    return "SUCCESS"


def task_merge_data(**kwargs):
    """Task 7: Merge cuaca + harga."""
    logger.info("[INFO] Memulai merge cuaca + harga...")
    sys.path.insert(0, PROJECT_ROOT)
    from pipeline.run_batch import BatchPipeline
    pipeline = BatchPipeline()
    pipeline.step_merge_data()
    logger.info("[INFO] Merge data selesai")
    return "SUCCESS"


def task_train_model(**kwargs):
    """Task 8: Training model ML (classification + clustering)."""
    logger.info("[INFO] Memulai training model ML...")
    sys.path.insert(0, PROJECT_ROOT)

    # 8a. Train price prediction model (classification)
    try:
        from models.price_prediction_model import train_model_from_data
        train_model_from_data()
        logger.info("[INFO] Model classification (GradientBoosting) berhasil ditraining")
    except Exception as e:
        logger.warning(f"[WARNING] Training dari data gagal, gunakan synthetic: {str(e)}")
        from models.price_prediction_model import train_synthetic_model
        train_synthetic_model()
        logger.info("[INFO] Model classification (synthetic) berhasil ditraining")

    # 8b. Run clustering
    try:
        from models.clustering_model import run_clustering_pipeline
        run_clustering_pipeline()
        logger.info("[INFO] Clustering (K-Means) berhasil dijalankan")
    except Exception as e:
        logger.warning(f"[WARNING] Clustering gagal (non-critical): {str(e)}")

    return "SUCCESS"


def task_quality_checks(**kwargs):
    """Task 9: Data quality checks."""
    logger.info("[INFO] Memulai data quality checks...")
    sys.path.insert(0, PROJECT_ROOT)
    from governance.quality_checks import run_all_quality_checks
    report = run_all_quality_checks()
    status = report.get("overall_status", "UNKNOWN")
    logger.info(f"[INFO] Quality check selesai: {status}")
    if status == "FAIL":
        logger.warning("[WARNING] Beberapa data quality check GAGAL — lihat quality_report.json")
    return status


def task_audit_log(**kwargs):
    """Task 10: Simpan audit log pipeline run."""
    logger.info("[INFO] Menyimpan audit log...")
    sys.path.insert(0, PROJECT_ROOT)
    import uuid
    from governance.audit_trail import AuditTrail

    run_id = kwargs.get("run_id", f"airflow-{uuid.uuid4().hex[:8]}")
    audit = AuditTrail()
    audit.log_pipeline_run(
        pipeline_run_id=run_id,
        tabel_nama="airflow_batch_pipeline",
        operasi="INSERT",
        username="airflow",
        status="SUCCESS",
        start_time=datetime.now().isoformat(),
    )
    audit.log_data_lineage()
    logger.info(f"[INFO] Audit log disimpan — run_id: {run_id}")
    return "SUCCESS"


# ─────────────────────────────────────────
# DEFINISI DAG
# ─────────────────────────────────────────

with DAG(
    dag_id="batch_pipeline_harga_pangan",
    description="Batch pipeline harga pangan: download → clean → MinIO → PostgreSQL → ML → quality checks",
    default_args=DEFAULT_ARGS,
    schedule_interval="0 23 * * *",   # Setiap hari jam 06:00 WIB (UTC-7 = 23:00 UTC)
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    tags=["ipbd", "batch", "harga-pangan"],
    on_success_callback=on_success_callback,
    on_failure_callback=on_failure_callback,
    doc_md="""
## Batch Pipeline — Harga Pangan

Pipeline harian untuk memproses data harga pangan dan cuaca.

### Alur:
1. Download cuaca (Open-Meteo)
2. Download harga (SP2KP Kemendag)
3. Clean cuaca
4. Clean harga
5. Upload ke MinIO (Data Lake)
6. Load ke PostgreSQL
7. Merge cuaca + harga
8. Train model ML (classification + clustering)
9. Data quality checks
10. Audit log

### Alert:
- Gagal → Notifikasi Telegram otomatis
- Log level: INFO, DEBUG, WARNING, ERROR, FATAL
    """,
) as dag:

    t1 = PythonOperator(
        task_id="download_cuaca",
        python_callable=task_download_cuaca,
        on_failure_callback=on_failure_callback,
        doc="Download data cuaca historis dari Open-Meteo Archive API",
    )

    t2 = PythonOperator(
        task_id="download_harga",
        python_callable=task_download_harga,
        on_failure_callback=on_failure_callback,
        doc="Download data harga pangan dari SP2KP Kemendag API",
    )

    t3 = PythonOperator(
        task_id="clean_cuaca",
        python_callable=task_clean_cuaca,
        on_failure_callback=on_failure_callback,
        doc="Cleaning data cuaca: handle null, normalisasi tipe data",
    )

    t4 = PythonOperator(
        task_id="clean_harga",
        python_callable=task_clean_harga,
        on_failure_callback=on_failure_callback,
        doc="Cleaning data harga: handle harga=0, ffill, drop duplikat",
    )

    t5 = PythonOperator(
        task_id="upload_minio",
        python_callable=task_upload_minio,
        on_failure_callback=on_failure_callback,
        doc="Upload raw & processed CSV ke MinIO (Data Lake)",
    )

    t6 = PythonOperator(
        task_id="load_postgres",
        python_callable=task_load_postgres,
        on_failure_callback=on_failure_callback,
        doc="Load data CSV ke tabel PostgreSQL (harga_pangan_raw, cuaca_historical)",
    )

    t7 = PythonOperator(
        task_id="merge_data",
        python_callable=task_merge_data,
        on_failure_callback=on_failure_callback,
        doc="Merge cuaca + harga ke tabel cuaca_harga_merged, buat lag features",
    )

    t8 = PythonOperator(
        task_id="train_model",
        python_callable=task_train_model,
        on_failure_callback=on_failure_callback,
        doc="Training model ML: GradientBoosting (classification) + K-Means (clustering)",
    )

    t9 = PythonOperator(
        task_id="quality_checks",
        python_callable=task_quality_checks,
        on_failure_callback=on_failure_callback,
        doc="Data quality checks: null, range, duplikat, tipe data",
    )

    t10 = PythonOperator(
        task_id="audit_log",
        python_callable=task_audit_log,
        on_failure_callback=on_failure_callback,
        doc="Simpan audit trail pipeline run ke PostgreSQL & generate lineage.json",
    )

    # ─── Dependency Chain ───────────────────
    # Download bisa paralel
    [t1, t2] >> t3
    t2 >> t4
    [t3, t4] >> t5
    t5 >> t6
    t6 >> t7
    t7 >> t8
    t8 >> t9
    t9 >> t10
