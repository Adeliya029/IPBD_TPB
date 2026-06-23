"""
DAG: stream_monitor_dag
Jadwal: Setiap jam (cek health stream pipeline)

Monitoring pipeline streaming Kafka:
- Cek apakah consumer Kafka masih aktif
- Cek apakah data cuaca_realtime masih masuk (tidak ada data gap > 2 jam)
- Kirim alert jika ada anomali

Fitur:
- on_failure_callback → Telegram alert
- Log level: INFO, WARNING, ERROR, FATAL
"""

import os
import sys
import logging
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

PROJECT_ROOT = os.path.join(
    os.getenv("AIRFLOW__CORE__DAGS_FOLDER", "/opt/airflow/dags"), "..", "project"
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

logger = logging.getLogger(__name__)

DEFAULT_ARGS = {
    "owner": "ipbd-team",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


def on_failure_callback(context):
    """Alert ke Telegram saat stream monitor gagal."""
    task_id = context.get("task_instance").task_id
    exception = context.get("exception")
    logger.fatal(
        f"[FATAL] Stream Monitor task GAGAL: {task_id}, Error: {exception}"
    )
    try:
        from alerts.alert_manager import PanganAlertManager
        alert = PanganAlertManager()
        alert.check_pipeline_failure(
            step_name=f"stream_monitor.{task_id}",
            error_message=f"Stream monitor gagal: {str(exception)}",
            pipeline_run_id=context.get("run_id", "unknown"),
        )
    except Exception as e:
        logger.error(f"[ERROR] Gagal kirim alert: {str(e)}")


def task_check_data_gap(**kwargs):
    """
    Cek apakah ada data gap pada stream cuaca_realtime.
    Jika tidak ada data > 2 jam, kirim alert WARNING.
    """
    logger.info("[INFO] Memulai pengecekan data gap stream...")
    sys.path.insert(0, PROJECT_ROOT)

    try:
        from alerts.alert_manager import PanganAlertManager
        alert = PanganAlertManager()
        has_gap = alert.check_data_gap()

        if has_gap:
            logger.warning("[WARNING] Data gap terdeteksi pada stream cuaca_realtime!")
        else:
            logger.info("[INFO] Stream cuaca_realtime OK — tidak ada data gap")
    except Exception as e:
        logger.error(f"[ERROR] Gagal cek data gap: {str(e)}")
        raise

    return "SUCCESS"


def task_check_stream_health(**kwargs):
    """
    Cek jumlah record cuaca_realtime yang masuk dalam 1 jam terakhir.
    Harapkan minimal 1 record per jam.
    """
    logger.info("[INFO] Memulai health check stream pipeline...")
    sys.path.insert(0, PROJECT_ROOT)

    try:
        import psycopg
        from dotenv import load_dotenv
        load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

        db_config = {
            "host": os.getenv("POSTGRES_HOST", "postgres"),
            "port": int(os.getenv("POSTGRES_PORT", "5432")),
            "dbname": os.getenv("POSTGRES_DB", "harga_pangan"),
            "user": os.getenv("POSTGRES_USER", "postgres"),
            "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
        }

        conn = psycopg.connect(**db_config)
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) FROM cuaca_realtime
            WHERE waktu >= NOW() - INTERVAL '1 hour'
        """)
        count = cur.fetchone()[0]
        cur.close()
        conn.close()

        logger.info(f"[INFO] Records masuk 1 jam terakhir: {count}")

        if count == 0:
            logger.warning(
                "[WARNING] Tidak ada data stream masuk dalam 1 jam terakhir! "
                "Stream consumer mungkin tidak aktif."
            )
            # Kirim alert
            from alerts.alert_manager import PanganAlertManager
            alert = PanganAlertManager()
            alert.send_alert(
                alert_type="DATA_GAP",
                severity="WARNING",
                message="Stream health: 0 record masuk dalam 1 jam terakhir. Consumer mungkin down.",
            )
        else:
            logger.info(f"[INFO] Stream pipeline sehat — {count} record dalam 1 jam")

    except Exception as e:
        logger.error(f"[ERROR] Stream health check gagal: {str(e)}")
        raise

    return count


def task_check_harga_spike(**kwargs):
    """
    Jalankan batch check harga spike untuk semua komoditas.
    """
    logger.info("[INFO] Memulai batch check harga spike...")
    sys.path.insert(0, PROJECT_ROOT)

    try:
        from alerts.alert_manager import PanganAlertManager
        alert = PanganAlertManager()
        triggered = alert.batch_check_harga_spike_from_db()
        logger.info(f"[INFO] Harga spike check selesai: {triggered} alert dikirim")
    except Exception as e:
        logger.warning(f"[WARNING] Harga spike check gagal (non-critical): {str(e)}")

    return "SUCCESS"


with DAG(
    dag_id="stream_monitor_harga_pangan",
    description="Monitoring stream pipeline — cek data gap, health check, dan harga spike",
    default_args=DEFAULT_ARGS,
    schedule_interval="0 * * * *",   # Setiap jam
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    tags=["ipbd", "stream", "monitoring"],
    on_failure_callback=on_failure_callback,
    doc_md="""
## Stream Monitor DAG — Harga Pangan

Dijalankan setiap jam untuk memastikan stream pipeline berjalan normal.

### Tasks:
1. `check_data_gap` — Cek apakah ada jeda data > 2 jam di cuaca_realtime
2. `check_stream_health` — Cek jumlah record masuk dalam 1 jam terakhir
3. `check_harga_spike` — Cek harga spike pada semua komoditas

### Alert Channel:
- Telegram (jika TELEGRAM_BOT_TOKEN dikonfigurasi di .env)
    """,
) as dag:

    t1 = PythonOperator(
        task_id="check_data_gap",
        python_callable=task_check_data_gap,
        on_failure_callback=on_failure_callback,
        doc="Cek data gap pada tabel cuaca_realtime",
    )

    t2 = PythonOperator(
        task_id="check_stream_health",
        python_callable=task_check_stream_health,
        on_failure_callback=on_failure_callback,
        doc="Cek jumlah record stream masuk dalam 1 jam terakhir",
    )

    t3 = PythonOperator(
        task_id="check_harga_spike",
        python_callable=task_check_harga_spike,
        on_failure_callback=on_failure_callback,
        doc="Cek harga spike pada semua komoditas dari database",
    )

    t1 >> t2 >> t3
