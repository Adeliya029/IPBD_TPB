import os
import json
import time
import psycopg2
import threading

from datetime import datetime
from kafka import KafkaConsumer
from dotenv import load_dotenv

load_dotenv()

# Tambahkan project root ke path agar bisa import logs.*
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

# =========================
# KONFIGURASI
# =========================

TOPIC = os.getenv("TOPIC_CUACA", "cuaca-stream")
BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5440")
POSTGRES_DB = os.getenv("POSTGRES_DB", "harga_pangan")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")

# =========================
# PROMETHEUS METRICS
# =========================

from logs.monitoring import MetricsCollector, StructuredLogger, start_metrics_server

metrics = MetricsCollector()
logger = StructuredLogger('OpenConsumer')

start_metrics_server(8002)

def update_system_metrics_periodically():
    while True:
        try:
            metrics.update_system_metrics()
        except Exception:
            pass
        time.sleep(15)

threading.Thread(target=update_system_metrics_periodically, daemon=True).start()

# =========================
# KAFKA CONSUMER
# =========================

consumer = KafkaConsumer(
    TOPIC,
    bootstrap_servers=BOOTSTRAP,
    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    auto_offset_reset="latest",
    enable_auto_commit=True,
    group_id="openmeteo-consumer-group"
)

# =========================
# DATABASE
# =========================

def get_connection():
    return psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        database=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD
    )


def simpan_ke_postgres(data):
    suhu = data.get("suhu")
    suhu_mean = data.get("suhu_mean") or suhu
    suhu_max = data.get("suhu_max") or suhu
    suhu_min = data.get("suhu_min") or suhu

    query = """
        INSERT INTO cuaca_realtime (
            waktu, provinsi, kab_kota,
            suhu, suhu_mean, suhu_max, suhu_min,
            kelembapan, curah_hujan,
            kecepatan_angin, tekanan_udara,
            kondisi_cuaca, deskripsi_cuaca,
            curah_hujan_mm, awan_persen, sumber
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
    """

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(query, (
            data.get("waktu"),
            data.get("provinsi"),
            data.get("kab_kota"),
            suhu,
            suhu_mean,
            suhu_max,
            suhu_min,
            data.get("kelembapan"),
            data.get("curah_hujan_mm"),
            data.get("kecepatan_angin"),
            data.get("tekanan_udara"),
            data.get("kondisi_cuaca"),
            data.get("kondisi_cuaca"),
            data.get("curah_hujan_mm"),
            data.get("awan_persen"),
            data.get("sumber")
        ))

        conn.commit()
        cursor.close()
        conn.close()

        return True

    except Exception as e:
        logger.error(f"DB Error: {e}")
        metrics.record_error('consumer', type(e).__name__)
        return False


# =========================
# MAIN
# =========================

def main():
    logger.info(
        "Consumer started",
        topic=TOPIC, bootstrap=BOOTSTRAP,
        postgres=f"{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )

    for message in consumer:
        data = message.value
        kab_kota = data.get('kab_kota', 'N/A')

        if simpan_ke_postgres(data):
            metrics.record_message_processed(kab_kota, 'success')
            metrics.update_weather_metrics(
                kab_kota,
                data.get('suhu') or 0,
                data.get('kecepatan_angin') or 0
            )
            logger.info(
                f"Stored: {data.get('provinsi')} - {kab_kota} - {data.get('suhu')}C",
                provinsi=data.get('provinsi'), kab_kota=kab_kota,
                suhu=data.get('suhu'), kondisi=data.get('kondisi_cuaca')
            )
        else:
            metrics.record_message_processed(kab_kota, 'failed')


if __name__ == "__main__":
    main()
