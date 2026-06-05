import requests
import json
import time
from kafka import KafkaProducer

producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

TOPIC = 'weather-stream'

API_KEY = 'aa910683d68af1e571aaf308fcc5899c'

cities = [

    {"province": "Aceh", "city": "Banda Aceh", "lat": 5.5483, "lon": 95.3238},
    {"province": "Sumatera Utara", "city": "Medan", "lat": 3.5952, "lon": 98.6722},
    {"province": "Sumatera Selatan", "city": "Palembang", "lat": -2.9761, "lon": 104.7754},
    {"province": "Sumatera Barat", "city": "Padang", "lat": -0.9471, "lon": 100.4172},
    {"province": "Bengkulu", "city": "Bengkulu", "lat": -3.7928, "lon": 102.2608},
    {"province": "Riau", "city": "Pekanbaru", "lat": 0.5071, "lon": 101.4478},
    {"province": "Kepulauan Riau", "city": "Tanjung Pinang", "lat": 0.9186, "lon": 104.4665},
    {"province": "Jambi", "city": "Jambi", "lat": -1.6101, "lon": 103.6131},
    {"province": "Lampung", "city": "Bandar Lampung", "lat": -5.4292, "lon": 105.2610},
    {"province": "Bangka Belitung", "city": "Pangkal Pinang", "lat": -2.1316, "lon": 106.1169},

    {"province": "Kalimantan Barat", "city": "Pontianak", "lat": -0.0263, "lon": 109.3425},
    {"province": "Kalimantan Timur", "city": "Samarinda", "lat": -0.5022, "lon": 117.1537},
    {"province": "Kalimantan Selatan", "city": "Banjarbaru", "lat": -3.4572, "lon": 114.8103},
    {"province": "Kalimantan Tengah", "city": "Palangkaraya", "lat": -2.2096, "lon": 113.9134},
    {"province": "Kalimantan Utara", "city": "Tanjung Selor", "lat": 2.8375, "lon": 117.3656},

    {"province": "Banten", "city": "Serang", "lat": -6.1201, "lon": 106.1503},
    {"province": "DKI Jakarta", "city": "Jakarta", "lat": -6.2088, "lon": 106.8456},
    {"province": "Jawa Barat", "city": "Bandung", "lat": -6.9175, "lon": 107.6191},
    {"province": "Jawa Tengah", "city": "Semarang", "lat": -6.9667, "lon": 110.4167},
    {"province": "DI Yogyakarta", "city": "Yogyakarta", "lat": -7.7956, "lon": 110.3695},
    {"province": "Jawa Timur", "city": "Surabaya", "lat": -7.2575, "lon": 112.7521},

    {"province": "Bali", "city": "Denpasar", "lat": -8.6705, "lon": 115.2126},
    {"province": "Nusa Tenggara Timur", "city": "Kupang", "lat": -10.1772, "lon": 123.6070},
    {"province": "Nusa Tenggara Barat", "city": "Mataram", "lat": -8.5833, "lon": 116.1167},

    {"province": "Gorontalo", "city": "Gorontalo", "lat": 0.5435, "lon": 123.0568},
    {"province": "Sulawesi Barat", "city": "Mamuju", "lat": -2.6814, "lon": 118.8867},
    {"province": "Sulawesi Tengah", "city": "Palu", "lat": -0.8917, "lon": 119.8707},
    {"province": "Sulawesi Utara", "city": "Manado", "lat": 1.4748, "lon": 124.8421},
    {"province": "Sulawesi Tenggara", "city": "Kendari", "lat": -3.9985, "lon": 122.5120},
    {"province": "Sulawesi Selatan", "city": "Makassar", "lat": -5.1477, "lon": 119.4327},

    {"province": "Maluku Utara", "city": "Sofifi", "lat": 0.7373, "lon": 127.5588},
    {"province": "Maluku", "city": "Ambon", "lat": -3.6547, "lon": 128.1903},

    {"province": "Papua Barat", "city": "Manokwari", "lat": -0.8615, "lon": 134.0788},
    {"province": "Papua", "city": "Jayapura", "lat": -2.5337, "lon": 140.7181},
    {"province": "Papua Tengah", "city": "Nabire", "lat": -3.3667, "lon": 135.4833},
    {"province": "Papua Pegunungan", "city": "Wamena", "lat": -4.0970, "lon": 138.9526},
    {"province": "Papua Selatan", "city": "Merauke", "lat": -8.4932, "lon": 140.4018},
    {"province": "Papua Barat Daya", "city": "Sorong", "lat": -0.8762, "lon": 131.2558}

]

while True:

    for city in cities:

        url = (
            f"https://api.openweathermap.org/data/2.5/weather?"
            f"lat={city['lat']}&"
            f"lon={city['lon']}&"
            f"appid={API_KEY}&"
            f"units=metric"
        )

        response = requests.get(url)

        data = response.json()

        weather_data = {
            "city": city["city"],
            "temperature": data["main"]["temp"],
            "humidity": data["main"]["humidity"],
            "pressure": data["main"]["pressure"],
            "windspeed": data["wind"]["speed"],
            "winddirection": data["wind"]["deg"],
            "weather": data["weather"][0]["main"],
            "description": data["weather"][0]["description"],
            "time": data["dt"]
        }

        producer.send(TOPIC, weather_data)

        print("Data dikirim:", weather_data)

    time.sleep(10)