"""
Food Price Prediction Consumer dengan ML Integration
Consumer untuk menerima data cuaca dan memprediksi perubahan harga pangan
"""

import json
import os
import psycopg2
from kafka import KafkaConsumer
from models.price_prediction_model import FoodPricePredictionModel
from security.security import AuthenticationManager, AuditLogger, DataProtection
from logs.monitoring import MetricsCollector, StructuredLogger, PerformanceMonitor, start_metrics_server
import sys
import time
from collections import deque
from datetime import datetime

# =========================
# DATABASE CONFIG
# =========================
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5440")
POSTGRES_DB = os.getenv("POSTGRES_DB", "harga_pangan")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")

def get_connection():
    return psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        database=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD
    )

def simpan_prediksi_ke_postgres(data, weather_data, prediction):
    query = """
        INSERT INTO predictions (
            tanggal_prediksi, provinsi, kab_kota,
            prediction_label, probabilitas_naik, probabilitas_turun, probabilitas_stabil,
            confidence, suhu_mean, curah_hujan_mm, kelembapan,
            cluster_label
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Ambil tanggal dari data_time (jika string kosongi jamnya, atau default ke now)
        tanggal_prediksi = datetime.now().date()
        
        cursor.execute(query, (
            tanggal_prediksi,
            data.get("provinsi", "Unknown"),
            data.get("kab_kota", "Unknown"),
            prediction.get("prediction"),
            prediction.get("probabilities", {}).get("NAIK", 0),
            prediction.get("probabilities", {}).get("TURUN", 0),
            prediction.get("probabilities", {}).get("STABIL", 0),
            prediction.get("confidence", 0),
            weather_data.get("suhu_mean"),
            weather_data.get("curah_hujan_mm"),
            weather_data.get("kelembapan"),
            prediction.get("cluster_id")
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"  ❌ DB Error saat menyimpan prediksi: {e}")


# Setup logging dan monitoring
logger = StructuredLogger('price_prediction_consumer')
metrics = MetricsCollector()
audit = AuditLogger()

# Setup security
auth_manager = AuthenticationManager()

# Authentication
print("="*60)
print("🍚 FOOD PRICE PREDICTION SYSTEM")
print("   Prediksi Harga Pangan Berdasarkan Cuaca")
print("="*60)
print("\n=== AUTHENTICATION ===")
username = input("Username: ")
password = input("Password: ")

auth_result = auth_manager.authenticate(username, password)
if not auth_result['success']:
    logger.error("Authentication failed", username=username)
    audit.log_authentication(username, False)
    print(f"❌ Authentication failed: {auth_result['message']}")
    sys.exit(1)

logger.info("Authentication successful", username=username)
audit.log_authentication(username, True)
metrics.record_auth_attempt(True)

# Verify permissions
token_data = auth_manager.verify_token(auth_result['token'])
if 'read' not in token_data['payload']['permissions']:
    logger.error("Permission denied", username=username, required_permission='read')
    print("❌ Error: You don't have read permission")
    sys.exit(1)

print(f"✅ Logged in as: {username} ({auth_result['role']})")
print("\nStarting Food Price Prediction Consumer...")
print()

# Start metrics server
start_metrics_server(8003)
logger.info("Metrics server started", port=8003)

# Load ML model
print("📊 Loading ML Model...")
try:
    price_predictor = FoodPricePredictionModel()
    price_predictor.load_model()
    logger.info("Price prediction model loaded successfully", user=username)
    print("✅ ML model loaded successfully\n")
except FileNotFoundError:
    logger.warning("Model not found, training new model...", user=username)
    print("⚠️  Model not found, training new model...")
    from models.price_prediction_model import train_model_from_data
    price_predictor = train_model_from_data()
    print("✅ New model trained successfully\n")
except Exception as e:
    logger.error("Failed to load ML model", error=str(e), user=username)
    print(f"❌ Error loading model: {e}")
    sys.exit(1)

# Setup Kafka consumer
TOPIC = os.getenv("TOPIC_CUACA", "cuaca-stream")
consumer = KafkaConsumer(
    TOPIC,
    bootstrap_servers='localhost:9092',
    value_deserializer=lambda x: json.loads(x.decode('utf-8')),
    auto_offset_reset='latest',
    enable_auto_commit=True
)

# Update active consumers metric
metrics.active_consumers.set(1)

# Historical rain tracking (untuk lag features)
historical_rain = {}

print('='*60)
print('🌦️  WAITING FOR WEATHER DATA...')
print('='*60)
print(f'📈 Dashboard: http://localhost:8003/metrics')
print(f'👤 User: {username}')
print('='*60)
print()

message_count = 0
predictions_summary = {'NAIK': 0, 'TURUN': 0, 'STABIL': 0}

try:
    for message in consumer:
        with PerformanceMonitor(metrics, 'consumer'):
            try:
                data = message.value
                message_count += 1
                
                city = data.get('city', 'Unknown')
                
                # Sanitize data untuk logging
                sanitized_data = DataProtection.sanitize_log_data(data)
                
                # Prepare weather data untuk ML
                weather_data = {
                    'suhu_mean': data.get('temperature', 25),
                    'curah_hujan_mm': data.get('rainfall', 0),  # Jika ada
                    'kelembapan': data.get('humidity', 80),
                    'kecepatan_angin': data.get('windspeed', 10),
                    'tekanan_udara': data.get('pressure', 1012),
                    'awan_persen': data.get('cloudcover', 50),
                    'suhu_max': data.get('temperature_max', data.get('temperature', 25) + 3),
                    'suhu_min': data.get('temperature_min', data.get('temperature', 25) - 3)
                }
                
                # Get historical rain untuk city (jika ada)
                city_rain_history = historical_rain.get(city, {'lag_1d': 0, 'lag_3d': 0, 'lag_7d': 0})
                
                # ML Prediction - Price Change
                with PerformanceMonitor(metrics, 'ml_inference'):
                    prediction = price_predictor.predict(weather_data, city_rain_history)
                
                # Update historical rain
                if city not in historical_rain:
                    historical_rain[city] = {'history': deque(maxlen=7)}
                historical_rain[city]['history'].append(weather_data['curah_hujan_mm'])
                
                # Calculate lag features
                hist = list(historical_rain[city]['history'])
                historical_rain[city]['lag_1d'] = hist[-1] if len(hist) >= 1 else 0
                historical_rain[city]['lag_3d'] = hist[-3] if len(hist) >= 3 else 0
                historical_rain[city]['lag_7d'] = hist[0] if len(hist) >= 7 else 0
                
                # Update metrics
                metrics.record_message_processed(city, 'success')
                predictions_summary[prediction['prediction']] += 1
                metrics.update_weather_metrics(
                    city,
                    weather_data['suhu_mean'],
                    weather_data['kecepatan_angin']
                )
                metrics.update_system_metrics()
                
                # Structured logging
                logger.info(
                    "Price prediction completed",
                    city=city,
                    prediction=prediction['prediction'],
                    confidence=prediction['confidence'],
                    temperature=weather_data['suhu_mean'],
                    rainfall=weather_data['curah_hujan_mm'],
                    message_id=message_count,
                    user=username
                )
                
                # Simpan ke PostgreSQL agar muncul di Grafana
                simpan_prediksi_ke_postgres(data, weather_data, prediction)
                
                # Audit log
                audit.log_data_access(username, "weather_price_prediction", "read")
                
                # Display output
                print('\n' + '='*60)
                print(f'📊 PREDIKSI HARGA PANGAN #{message_count}')
                print('='*60)
                print(f"🌍 Lokasi       : {city}")
                print(f"⏰ Waktu        : {data.get('time', '-')}")
                print(f"🌡️  Suhu         : {weather_data['suhu_mean']:.1f}°C")
                print(f"💨 Angin        : {weather_data['kecepatan_angin']:.1f} km/h")
                print(f"💧 Kelembapan   : {weather_data['kelembapan']:.1f}%")
                
                # Prediction result dengan warna
                pred_icon = {
                    'NAIK': '🔺',
                    'TURUN': '🔻',
                    'STABIL': '➡️'
                }
                
                print(f"\n{pred_icon[prediction['prediction']]} PREDIKSI: {prediction['prediction']}")
                print(f"   Confidence: {prediction['confidence']:.1%}")
                print(f"\n📈 Probabilitas:")
                print(f"   • Harga Naik   : {prediction['probabilities']['NAIK']:.1%}")
                print(f"   • Harga Stabil : {prediction['probabilities']['STABIL']:.1%}")
                print(f"   • Harga Turun  : {prediction['probabilities']['TURUN']:.1%}")
                
                print(f"\n{prediction['recommendation']}")
                
                print(f"\n📊 Summary ({message_count} predictions):")
                print(f"   🔺 Naik: {predictions_summary['NAIK']}, "
                      f"➡️  Stabil: {predictions_summary['STABIL']}, "
                      f"🔻 Turun: {predictions_summary['TURUN']}")
                print('='*60)
                
            except Exception as e:
                logger.error(
                    "Message processing failed",
                    error=str(e),
                    user=username,
                    message_count=message_count
                )
                metrics.record_error("consumer", type(e).__name__)
                print(f"\n❌ Error processing message: {e}")

except KeyboardInterrupt:
    logger.info(
        "Consumer shutting down",
        user=username,
        messages_processed=message_count,
        predictions=predictions_summary
    )
    print(f"\n\n{'='*60}")
    print("SHUTDOWN SUMMARY")
    print('='*60)
    print(f"Total messages processed: {message_count}")
    print(f"Predictions:")
    print(f"  🔺 Harga Naik   : {predictions_summary['NAIK']}")
    print(f"  ➡️  Harga Stabil : {predictions_summary['STABIL']}")
    print(f"  🔻 Harga Turun  : {predictions_summary['TURUN']}")
    print('='*60)
    
    metrics.active_consumers.set(0)
    consumer.close()
