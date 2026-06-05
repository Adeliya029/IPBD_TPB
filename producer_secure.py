"""
Secure Producer dengan ML Integration, Monitoring, dan Security
"""

import requests
import json
import time
from kafka import KafkaProducer
from security import AuthenticationManager, DataEncryption, AuditLogger, DataProtection
from monitoring import MetricsCollector, StructuredLogger, PerformanceMonitor, start_metrics_server
import sys

# Setup logging dan monitoring
logger = StructuredLogger('secure_producer')
metrics = MetricsCollector()
audit = AuditLogger()

# Setup security
auth_manager = AuthenticationManager()
encryptor = DataEncryption()

# Authentication
print("=== WEATHER PRODUCER AUTHENTICATION ===")
username = input("Username: ")
password = input("Password: ")

auth_result = auth_manager.authenticate(username, password)
if not auth_result['success']:
    logger.error("Authentication failed", username=username)
    audit.log_authentication(username, False)
    print(f"Authentication failed: {auth_result['message']}")
    sys.exit(1)

logger.info("Authentication successful", username=username)
audit.log_authentication(username, True)
metrics.record_auth_attempt(True)

# Verify permissions
token_data = auth_manager.verify_token(auth_result['token'])
if 'write' not in token_data['payload']['permissions']:
    logger.error("Permission denied", username=username, required_permission='write')
    print("Error: You don't have write permission")
    sys.exit(1)

print(f"Logged in as: {username} ({auth_result['role']})")
print("Starting weather data producer...\n")

# Start metrics server
start_metrics_server(8001)
logger.info("Metrics server started", port=8001)

# Setup Kafka producer
producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

TOPIC = 'weather-stream'

cities = [
    {"city": "Jakarta", "lat": -6.2088, "lon": 106.8456},
    {"city": "Surabaya", "lat": -7.2575, "lon": 112.7521},
    {"city": "Bandung", "lat": -6.9175, "lon": 107.6191},
    {"city": "Medan", "lat": 3.5952, "lon": 98.6722},
    {"city": "Makassar", "lat": -5.1477, "lon": 119.4327}
]

message_count = 0

try:
    while True:
        for city in cities:
            with PerformanceMonitor(metrics, 'producer'):
                try:
                    # Fetch weather data
                    url = (
                        f"https://api.open-meteo.com/v1/forecast?"
                        f"latitude={city['lat']}&"
                        f"longitude={city['lon']}&"
                        f"current=temperature_2m,wind_speed_10m"
                    )
                    
                    response = requests.get(url, timeout=5)
                    response.raise_for_status()
                    data = response.json()
                    
                    current = data["current"]
                    
                    weather_data = {
                        "city": city["city"],
                        "temperature": current["temperature_2m"],
                        "windspeed": current["wind_speed_10m"],
                        "time": current["time"],
                        "producer_user": username,
                        "message_id": message_count
                    }
                    
                    # Send to Kafka
                    producer.send(TOPIC, weather_data)
                    message_count += 1
                    
                    # Update metrics
                    metrics.record_message_processed(city["city"], "success")
                    metrics.update_weather_metrics(
                        city["city"],
                        weather_data["temperature"],
                        weather_data["windspeed"]
                    )
                    metrics.update_system_metrics()
                    
                    # Log with structured logging
                    logger.info(
                        "Weather data sent",
                        city=city["city"],
                        temperature=weather_data["temperature"],
                        windspeed=weather_data["windspeed"],
                        message_id=message_count,
                        user=username
                    )
                    
                    # Audit log
                    audit.log_data_access(username, "weather_data", "write")
                    
                    # Sanitize untuk display (mask sensitive data)
                    display_data = DataProtection.mask_sensitive_data(
                        weather_data.copy(),
                        ['producer_user']
                    )
                    print(f"✓ Data sent: {display_data}")
                    
                except requests.exceptions.RequestException as e:
                    logger.error(
                        "API request failed",
                        city=city["city"],
                        error=str(e),
                        user=username
                    )
                    metrics.record_error("producer", "api_error")
                    print(f"✗ API Error for {city['city']}: {e}")
                    
                except Exception as e:
                    logger.error(
                        "Message send failed",
                        city=city["city"],
                        error=str(e),
                        user=username
                    )
                    metrics.record_error("producer", type(e).__name__)
                    print(f"✗ Error for {city['city']}: {e}")
        
        time.sleep(3)

except KeyboardInterrupt:
    logger.info("Producer shutting down", user=username, messages_sent=message_count)
    print(f"\n\nShutting down... Total messages sent: {message_count}")
    producer.close()
