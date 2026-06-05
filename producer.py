import requests
import json
import time
from kafka import KafkaProducer

producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

TOPIC = 'weather-stream'

cities = [
    {
        "city": "Jakarta",
        "lat": -6.2088,
        "lon": 106.8456
    },
    {
        "city": "Surabaya",
        "lat": -7.2575,
        "lon": 112.7521
    },
    {
        "city": "Bandung",
        "lat": -6.9175,
        "lon": 107.6191
    },
    {
        "city": "Medan",
        "lat": 3.5952,
        "lon": 98.6722
    },
    {
        "city": "Makassar",
        "lat": -5.1477,
        "lon": 119.4327
    }
]

while True:

    for city in cities:

        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={city['lat']}&"
            f"longitude={city['lon']}&"
            f"current=temperature_2m,wind_speed_10m"
        )

        response = requests.get(url)
        data = response.json()

        current = data["current"]

        weather_data = {
            "city": city["city"],
            "temperature": current["temperature_2m"],
            "windspeed": current["wind_speed_10m"],
            "time": current["time"]
        }

        producer.send(TOPIC, weather_data)

        print("Data dikirim:", weather_data)

    time.sleep(3)