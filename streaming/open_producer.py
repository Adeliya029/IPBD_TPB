import os
import json
import time
import requests

from datetime import datetime
from kafka import KafkaProducer
from dotenv import load_dotenv

load_dotenv()

# =========================
# KONFIGURASI
# =========================

TOPIC = os.getenv("TOPIC_CUACA", "cuaca-stream")
BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
INTERVAL_STREAM = int(os.getenv("INTERVAL_STREAM", "3600"))  # default 1 jam

# Path ke kab_kota_jawa.json (di folder streaming)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(BASE_DIR, "..")
FILE_KOTA = os.path.join(PROJECT_ROOT, "streaming", "kab_kota_jawa.json")

print(f"BASE_DIR: {BASE_DIR}")
print(f"PROJECT_ROOT: {PROJECT_ROOT}")
print(f"FILE_KOTA: {FILE_KOTA}")
print(f"File exists: {os.path.exists(FILE_KOTA)}")

with open(FILE_KOTA, "r", encoding="utf-8") as f:
    DAFTAR_KOTA = json.load(f)

print(f"Loaded {len(DAFTAR_KOTA)} kota")

# Open-Meteo API (GRATIS, no API key)
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

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
    """
    Ambil data cuaca real-time dari Open-Meteo untuk 1 kota.
    Menggunakan /v1/forecast dengan current weather.
    """

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

        # Weather code mapping (simplified)
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
        print(f"  ❌ Gagal ambil {kota['kab_kota']}: {e}")
        return None


def get_weather_desc(code):
    """Mapping weather code WMO ke deskripsi"""
    weather_map = {
        0: "Cerah",
        1: "Cerah Berawan",
        2: "Cerah Berawan",
        3: "Berawan",
        45: "Berkabut",
        48: "Berkabut",
        51: "Gerimis Ringan",
        53: "Gerimis Sedang",
        55: "Gerimis Lebat",
        61: "Hujan Ringan",
        63: "Hujan Sedang",
        65: "Hujan Lebat",
        71: "Salju Ringan",
        73: "Salju Sedang",
        75: "Salju Lebat",
        80: "Hujan Lokal Ringan",
        81: "Hujan Lokal Sedang",
        82: "Hujan Lokal Lebat",
        95: "Badai Petir",
        96: "Badai Petir + Hail",
        99: "Badai Petir + Hail Lebat",
    }
    return weather_map.get(code, "Tidak Diketahui")


# =========================
# MAIN
# =========================

def main():
    print("="*70)
    print("OPEN-METEO REAL-TIME PRODUCER")
    print("="*70)
    print(f"Total kota: {len(DAFTAR_KOTA)}")
    print(f"Topic: {TOPIC}")
    print(f"Bootstrap: {BOOTSTRAP}")
    print(f"Interval: {INTERVAL_STREAM} detik ({INTERVAL_STREAM//60} menit)")
    print("="*70)

    while True:
        total = 0

        print("" + "="*70)
        print(f"Mulai polling : {datetime.now()}")
        print("="*70)

        for kota in DAFTAR_KOTA:
            hasil = ambil_cuaca_realtime(kota)

            if hasil:
                producer.send(TOPIC, hasil)
                total += 1

                print(
                    f"[{total:03d}] "
                    f"{hasil['provinsi']} | "
                    f"{hasil['kab_kota']} | "
                    f"{hasil['suhu']}°C | "
                    f"{hasil['kondisi_cuaca']}"
                )

            # Hindari rate limit (Open-Meteo free: 10,000 calls/day)
            time.sleep(0.5)

        producer.flush()

        print(f"Total terkirim : {total}/{len(DAFTAR_KOTA)}")
        print(f"Menunggu {INTERVAL_STREAM//60} menit...")

        time.sleep(INTERVAL_STREAM)


if __name__ == "__main__":
    main()