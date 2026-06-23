import os
import json
import psycopg2

from datetime import datetime
from kafka import KafkaConsumer
from dotenv import load_dotenv

load_dotenv()

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
    """Simpan data cuaca real-time ke PostgreSQL"""

    query = """
        INSERT INTO cuaca_realtime (
            waktu, provinsi, kab_kota,
            suhu, kelembapan, curah_hujan,
            kecepatan_angin, tekanan_udara,
            kondisi_cuaca, deskripsi_cuaca,
            curah_hujan_mm, awan_persen, sumber
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
    """

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(query, (
            data.get("waktu"),
            data.get("provinsi"),
            data.get("kab_kota"),
            data.get("suhu"),
            data.get("kelembapan"),
            data.get("curah_hujan_mm"),          # curah_hujan
            data.get("kecepatan_angin"),
            data.get("tekanan_udara"),
            data.get("kondisi_cuaca"),
            data.get("kondisi_cuaca"),            # deskripsi_cuaca (fallback)
            data.get("curah_hujan_mm"),
            data.get("awan_persen"),
            data.get("sumber")
        ))

        conn.commit()
        cursor.close()
        conn.close()

        return True

    except Exception as e:
        print(f"  ❌ DB Error: {e}")
        return False


# =========================
# MAIN
# =========================

def main():
    print("="*70)
    print("OPEN-METEO REAL-TIME CONSUMER")
    print("="*70)
    print(f"Topic: {TOPIC}")
    print(f"Bootstrap: {BOOTSTRAP}")
    print(f"PostgreSQL: {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")
    print("="*70)
    print("\nMenunggu data dari Kafka...")

    for message in consumer:
        data = message.value

        print(
            f"\n[{datetime.now().strftime('%H:%M:%S')}] "
            f"{data.get('provinsi', 'N/A')} | "
            f"{data.get('kab_kota', 'N/A')} | "
            f"{data.get('suhu', 'N/A')}°C | "
            f"{data.get('kondisi_cuaca', 'N/A')}"
        )

        if simpan_ke_postgres(data):
            print("  ✅ Tersimpan ke PostgreSQL")
        else:
            print("  ❌ Gagal simpan ke PostgreSQL")


if __name__ == "__main__":
    main()