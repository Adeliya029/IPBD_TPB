# 📊 Logs Package

Package ini berisi implementasi monitoring, logging, dan performance tracking.

## 📁 Struktur

```
logs/
├── __init__.py          # Package initialization
├── monitoring.py        # Monitoring implementation
├── data/                # Direktori untuk log files (GITIGNORED)
│   ├── application.log  # Structured JSON logs
│   ├── errors.log       # Error tracking
│   └── audit.log        # Security audit logs
└── README.md
```

## 📈 Fitur

### 1. Structured Logging

```python
from logs import StructuredLogger

logger = StructuredLogger('my_service')

# Log with extra fields
logger.info(
    "Message processed",
    city="Jakarta",
    temperature=28.5,
    user="admin"
)
```

Output (JSON):
```json
{
  "timestamp": "2026-06-05T10:30:45.123456",
  "level": "INFO",
  "message": "Message processed",
  "extra_fields": {
    "city": "Jakarta",
    "temperature": 28.5,
    "user": "admin"
  }
}
```

### 2. Prometheus Metrics

```python
from logs import MetricsCollector, start_metrics_server

# Start metrics server
start_metrics_server(8000)

# Collect metrics
metrics = MetricsCollector()
metrics.record_message_processed('Jakarta', 'success')
metrics.record_ml_prediction(is_anomaly=False)
metrics.update_weather_metrics('Jakarta', 28.5, 12.3)
```

View metrics: http://localhost:8000/metrics

### 3. Performance Monitoring

```python
from logs import PerformanceMonitor, MetricsCollector

metrics = MetricsCollector()

# Automatic timing
with PerformanceMonitor(metrics, 'consumer'):
    # Your code here
    process_message(data)
# Duration automatically recorded
```

## 📊 Metrics Available

### Counters
- `weather_messages_processed_total` - Total messages processed
- `ml_predictions_total` - Total ML predictions
- `pipeline_errors_total` - Total errors
- `authentication_attempts_total` - Auth attempts

### Histograms
- `message_processing_seconds` - Processing latency
- `ml_inference_seconds` - ML inference time

### Gauges
- `current_temperature_celsius` - Current temperature per city
- `current_windspeed_kmh` - Current windspeed per city
- `system_cpu_usage_percent` - CPU usage
- `system_memory_usage_percent` - Memory usage
