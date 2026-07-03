import os
import json
import time
import requests
import threading

from datetime import datetime
from kafka import KafkaProducer
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
INTERVAL_STREAM = int(os.getenv("INTERVAL_STREAM", "3600"))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(BASE_DIR, "..")
FILE_KOTA = os.path.join(PROJECT_ROOT, "streaming", "kab_kota_jawa.json")

with open(FILE_KOTA, "r", encoding="utf-8") as f:
    DAFTAR_KOTA = json.load(f)

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# =========================
# PROMETHEUS METRICS
# =========================

from logs.monitoring import MetricsCollector, StructuredLogger, start_metrics_server

metrics = MetricsCollector()
logger = StructuredLogger('OpenProducer')

start_metrics_server(8001)

def update_system_metrics_periodically():
    while True:
        try:
            metrics.update_system_metrics()
        except Exception:
            pass
        time.sleep(15)

threading.Thread(target=update_system_metrics_periodically, daemon=True).start()

# =========================
# KAFKA PRODUCER
# =========================

producer = KafkaProducer(
    bootstrap_servers=BOOTSTRAP,
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

# =========================
# AMBIL DATA CUACA REAL-TIME
# =========================

def ambil_cuaca_realtime(kota):
    params = {
        "latitude": kota["latitude"],
        "longitude": kota["longitude"],
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,rain,weather_code,cloud_cover,pressure_msl,surface_pressure,wind_speed_10m,wind_direction_10m,wind_gusts_10m",
        "timezone": "Asia/Jakarta"
    }

    try:
        response = requests.get(FORECAST_URL, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()

        current = data.get("current", {})

        if not current:
            return None

        weather_code = current.get("weather_code", -1)
        weather_desc = get_weather_desc(weather_code)

        return {
            "waktu": datetime.now().isoformat(),
            "provinsi": kota["provinsi"],
            "kab_kota": kota["kab_kota"],
            "latitude": kota["latitude"],
            "longitude": kota["longitude"],

            "suhu": current.get("temperature_2m"),
            "suhu_feels_like": current.get("apparent_temperature"),
            "kelembapan": current.get("relative_humidity_2m"),
            "curah_hujan_mm": current.get("precipitation") or current.get("rain") or 0,

            "kode_cuaca": weather_code,
            "kondisi_cuaca": weather_desc,

            "awan_persen": current.get("cloud_cover"),
            "tekanan_udara": current.get("pressure_msl"),
            "tekanan_permukaan": current.get("surface_pressure"),

            "kecepatan_angin": current.get("wind_speed_10m"),
            "arah_angin": current.get("wind_direction_10m"),
            "kecepatan_angin_gust": current.get("wind_gusts_10m"),

            "waktu_data": current.get("time"),
            "sumber": "Open-Meteo_Realtime"
        }

    except Exception as e:
        logger.error(f"Gagal ambil {kota['kab_kota']}: {e}")
        metrics.record_error('producer', type(e).__name__)
        return None


def get_weather_desc(code):
    weather_map = {
        0: "Cerah", 1: "Cerah Berawan", 2: "Cerah Berawan", 3: "Berawan",
        45: "Berkabut", 48: "Berkabut",
        51: "Gerimis Ringan", 53: "Gerimis Sedang", 55: "Gerimis Lebat",
        61: "Hujan Ringan", 63: "Hujan Sedang", 65: "Hujan Lebat",
        71: "Salju Ringan", 73: "Salju Sedang", 75: "Salju Lebat",
        80: "Hujan Lokal Ringan", 81: "Hujan Lokal Sedang", 82: "Hujan Lokal Lebat",
        95: "Badai Petir", 96: "Badai Petir + Hail", 99: "Badai Petir + Hail Lebat",
    }
    return weather_map.get(code, "Tidak Diketahui")


# =========================
# MAIN
# =========================

def main():
    logger.info(
        "Producer started",
        topic=TOPIC, bootstrap=BOOTSTRAP,
        interval=INTERVAL_STREAM, cities=len(DAFTAR_KOTA)
    )

    while True:
        total = 0

        logger.info("Mulai polling cuaca", cities=len(DAFTAR_KOTA))

        for kota in DAFTAR_KOTA:
            with metrics.processing_latency.labels(component='fetch_weather').time():
                hasil = ambil_cuaca_realtime(kota)

            if hasil:
                producer.send(TOPIC, hasil)
                total += 1

                metrics.update_weather_metrics(
                    kota['kab_kota'],
                    hasil.get('suhu') or 0,
                    hasil.get('kecepatan_angin') or 0
                )
                metrics.record_message_processed(kota['kab_kota'], 'success')

                logger.info(
                    f"Sent: {hasil['provinsi']} - {hasil['kab_kota']} - {hasil['suhu']}C",
                    provinsi=hasil['provinsi'], kab_kota=hasil['kab_kota'],
                    suhu=hasil['suhu'], kondisi=hasil['kondisi_cuaca']
                )
            else:
                metrics.record_message_processed(kota['kab_kota'], 'failed')

            time.sleep(0.5)

        producer.flush()

        logger.info(f"Polling selesai: {total}/{len(DAFTAR_KOTA)} terkirim")
        print(f"Menunggu {INTERVAL_STREAM//60} menit...")

        time.sleep(INTERVAL_STREAM)


if __name__ == "__main__":
    main()
