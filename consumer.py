import json
from kafka import KafkaConsumer

consumer = KafkaConsumer(
    'weather-stream',
    bootstrap_servers='localhost:9092',
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

print('Menunggu data cuaca...')

for message in consumer:

    data = message.value

    print('\n=== DATA CUACA REALTIME ===')

    print(f"Waktu       : {data.get('time', '-')}")
    print(f"Kota        : {data.get('city', '-')}")
    print(f"Suhu        : {data.get('temperature', '-')} °C")
    print(f"Kecepatan   : {data.get('windspeed', '-')} km/h")

    # Optional fields
    if 'winddirection' in data:
        print(f"Arah Angin  : {data['winddirection']}")

    if 'weathercode' in data:
        print(f"WeatherCode : {data['weathercode']}")