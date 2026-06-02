import json
import os
import time
import requests

from datetime import datetime
from kafka import KafkaProducer
from dotenv import load_dotenv

load_dotenv()

# =====================================
# KONFIGURASI
# =====================================

API_KEY = os.getenv(
    "WEATHER_API_KEY"
)

TOPIC = os.getenv(
    "TOPIC_CUACA",
    "cuaca-stream"
)

BOOTSTRAP = os.getenv(
    "KAFKA_BOOTSTRAP",
    "localhost:9092"
)

INTERVAL_STREAM = int(
    os.getenv(
        "INTERVAL_STREAM",
        3600
    )
)

# =====================================
# LOAD DATA KAB/KOTA
# =====================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

FILE_KOTA = os.path.join(
    BASE_DIR,
    "kab_kota_jawa.json"
)

with open(
    FILE_KOTA,
    "r",
    encoding="utf-8"
) as f:

    DAFTAR_KOTA = json.load(f)

# =====================================
# KAFKA PRODUCER
# =====================================

producer = KafkaProducer(

    bootstrap_servers=BOOTSTRAP,

    value_serializer=lambda x:
    json.dumps(x).encode("utf-8")

)

# =====================================
# AMBIL DATA CUACA
# =====================================

def ambil_cuaca(kota):

    try:

        response = requests.get(

            "https://api.openweathermap.org/data/2.5/weather",

            params={

                "lat": kota["latitude"],
                "lon": kota["longitude"],
                "appid": API_KEY,
                "units": "metric"

            },

            timeout=20

        )

        response.raise_for_status()

        data = response.json()

        curah_hujan = 0

        if "rain" in data:

            curah_hujan = (

                data["rain"].get("1h")
                or data["rain"].get("3h")
                or 0

            )

        return {

            "waktu":

                datetime.now().isoformat(),

            "provinsi":

                kota["provinsi"],

            "kab_kota":

                kota["kab_kota"],

            "suhu":

                data["main"]["temp"],

            "kelembapan":

                data["main"]["humidity"],

            "curah_hujan":

                curah_hujan,

            "kecepatan_angin":

                data["wind"]["speed"],

            "tekanan_udara":

                data["main"]["pressure"],

            "kondisi_cuaca":

                data["weather"][0]["main"],

            "deskripsi_cuaca":

                data["weather"][0]["description"],

            "sumber":

                "OpenWeatherMap"

        }

    except Exception as e:

        print(

            f"Gagal ambil data "
            f"{kota['kab_kota']} : {e}"

        )

        return None


# =====================================
# MAIN
# =====================================

def main():

    print(
        f"Producer aktif "
        f"({len(DAFTAR_KOTA)} kab/kota)"
    )

    while True:

        total = 0

        print(
            "\n"
            + "=" * 60
        )

        print(
            f"Mulai polling : "
            f"{datetime.now()}"
        )

        print(
            "=" * 60
        )

        for kota in DAFTAR_KOTA:

            hasil = ambil_cuaca(kota)

            if hasil:

                producer.send(
                    TOPIC,
                    hasil
                )

                total += 1

                print(

                    f"[{total:03d}] "

                    f"{hasil['provinsi']} | "

                    f"{hasil['kab_kota']} | "

                    f"{hasil['suhu']}°C"

                )

            # hindari spam API
            time.sleep(1)

        producer.flush()

        print(
            f"\nTotal terkirim : {total}"
        )

        print(
            f"Menunggu "
            f"{INTERVAL_STREAM//60} menit"
        )

        time.sleep(
            INTERVAL_STREAM
        )


if __name__ == "__main__":
    main()