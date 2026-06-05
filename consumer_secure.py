"""
Secure Consumer dengan ML Inference, Monitoring, dan Security
"""

import json
from kafka import KafkaConsumer
from models.ml_model import WeatherAnomalyDetector
from security.security import AuthenticationManager, AuditLogger, DataProtection
from logs.monitoring import MetricsCollector, StructuredLogger, PerformanceMonitor, start_metrics_server
import sys
import time

# Setup logging dan monitoring
logger = StructuredLogger('secure_consumer')
metrics = MetricsCollector()
audit = AuditLogger()

# Setup security
auth_manager = AuthenticationManager()

# Authentication
print("=== WEATHER CONSUMER AUTHENTICATION ===")
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
if 'read' not in token_data['payload']['permissions']:
    logger.error("Permission denied", username=username, required_permission='read')
    print("Error: You don't have read permission")
    sys.exit(1)

print(f"Logged in as: {username} ({auth_result['role']})")
print("Starting weather data consumer...\n")

# Start metrics server
start_metrics_server(8002)
logger.info("Metrics server started", port=8002)

# Load ML model
print("Loading ML model...")
try:
    ml_detector = WeatherAnomalyDetector()
    ml_detector.load_model()
    logger.info("ML model loaded successfully", user=username)
    print("✓ ML model loaded\n")
except FileNotFoundError:
    logger.warning("ML model not found, training new model...", user=username)
    print("⚠ Model not found, training new model...")
    from models.ml_model import train_initial_model
    ml_detector = train_initial_model()
    print("✓ New model trained\n")
except Exception as e:
    logger.error("Failed to load ML model", error=str(e), user=username)
    print(f"✗ Error loading model: {e}")
    sys.exit(1)

# Setup Kafka consumer
consumer = KafkaConsumer(
    'weather-stream',
    bootstrap_servers='localhost:9092',
    value_deserializer=lambda x: json.loads(x.decode('utf-8')),
    auto_offset_reset='latest',
    enable_auto_commit=True
)

# Update active consumers metric
metrics.active_consumers.set(1)

print('=== WAITING FOR WEATHER DATA ===')
print('Monitoring: http://localhost:8002/metrics\n')

message_count = 0
anomaly_count = 0

try:
    for message in consumer:
        with PerformanceMonitor(metrics, 'consumer'):
            try:
                data = message.value
                message_count += 1
                
                # Sanitize data untuk logging
                sanitized_data = DataProtection.sanitize_log_data(data)
                
                # ML Inference - Anomaly Detection
                with PerformanceMonitor(metrics, 'ml_inference'):
                    prediction = ml_detector.predict(data)
                
                # Update metrics
                metrics.record_message_processed(data['city'], 'success')
                metrics.record_ml_prediction(prediction['is_anomaly'])
                metrics.update_weather_metrics(
                    data['city'],
                    data['temperature'],
                    data['windspeed']
                )
                metrics.update_system_metrics()
                
                if prediction['is_anomaly']:
                    anomaly_count += 1
                
                # Structured logging
                logger.info(
                    "Weather data processed",
                    city=data.get('city'),
                    temperature=data.get('temperature'),
                    windspeed=data.get('windspeed'),
                    is_anomaly=prediction['is_anomaly'],
                    anomaly_score=prediction['anomaly_score'],
                    message_id=message_count,
                    user=username
                )
                
                # Audit log
                audit.log_data_access(username, "weather_data", "read")
                
                # Display output
                print('\n' + '='*50)
                print(f'📊 WEATHER DATA #{message_count}')
                print('='*50)
                print(f"⏰ Time        : {data.get('time', '-')}")
                print(f"🏙️  City        : {data.get('city', '-')}")
                print(f"🌡️  Temperature : {data.get('temperature', '-')} °C")
                print(f"💨 Windspeed   : {data.get('windspeed', '-')} km/h")
                
                # ML Prediction result
                if prediction['is_anomaly']:
                    print(f"\n⚠️  ML ALERT: ANOMALY DETECTED!")
                    print(f"   Anomaly Score: {prediction['anomaly_score']:.4f}")
                    print(f"   Confidence: {prediction['confidence']:.2%}")
                    print(f"   Total Anomalies: {anomaly_count}/{message_count}")
                else:
                    print(f"\n✅ ML Result: Normal weather pattern")
                    print(f"   Confidence: {prediction['confidence']:.2%}")
                
                print('='*50)
                
            except Exception as e:
                logger.error(
                    "Message processing failed",
                    error=str(e),
                    user=username,
                    message_count=message_count
                )
                metrics.record_error("consumer", type(e).__name__)
                print(f"\n✗ Error processing message: {e}")

except KeyboardInterrupt:
    logger.info(
        "Consumer shutting down",
        user=username,
        messages_processed=message_count,
        anomalies_detected=anomaly_count
    )
    print(f"\n\n{'='*50}")
    print("SHUTDOWN SUMMARY")
    print('='*50)
    print(f"Total messages processed: {message_count}")
    print(f"Anomalies detected: {anomaly_count}")
    if message_count > 0:
        print(f"Anomaly rate: {anomaly_count/message_count:.2%}")
    print('='*50)
    
    metrics.active_consumers.set(0)
    consumer.close()
