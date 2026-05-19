import json
from kafka import KafkaConsumer

consumer = KafkaConsumer(
    'weather-stream',
    bootstrap_servers='localhost:9092',
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

print('Menunggu data cuaca realtime...')

for message in consumer:

    data = message.value

    print('\n=== DATA CUACA ===')

    print(f"Kota         : {data.get('city')}")
    print(f"Suhu         : {data.get('temperature')} °C")
    print(f"Humidity     : {data.get('humidity')} %")
    print(f"Pressure     : {data.get('pressure')} hPa")
    print(f"Wind Speed   : {data.get('windspeed')} m/s")
    print(f"Arah Angin   : {data.get('winddirection')}°")
    print(f"Cuaca        : {data.get('weather')}")
    print(f"Deskripsi    : {data.get('description')}")