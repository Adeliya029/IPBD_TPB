"""
Monitoring & Logging Module
Prometheus metrics, structured logging, dan performance monitoring
"""

import logging
import json
import time
from datetime import datetime
from prometheus_client import Counter, Histogram, Gauge, Info, start_http_server
import psutil
import os

# ==================== STRUCTURED LOGGING ====================

class StructuredLogger:
    """Custom logger yang menghasilkan structured JSON logs"""
    
    def __init__(self, name, log_file='logs/data/application.log'):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Create logs directory
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # File handler for JSON logs
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(self.JSONFormatter())
        self.logger.addHandler(file_handler)
        
        # Console handler for human-readable logs
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(console_handler)
    
    class JSONFormatter(logging.Formatter):
        """Format log sebagai JSON"""
        
        def format(self, record):
            log_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'level': record.levelname,
                'logger': record.name,
                'message': record.getMessage(),
                'module': record.module,
                'function': record.funcName,
                'line': record.lineno
            }
            
            # Add extra fields jika ada
            if hasattr(record, 'extra_fields'):
                log_data.update(record.extra_fields)
            
            return json.dumps(log_data)
    
    def info(self, message, **extra_fields):
        """Log info dengan extra fields"""
        extra = {'extra_fields': extra_fields} if extra_fields else {}
        self.logger.info(message, extra=extra)
    
    def error(self, message, **extra_fields):
        """Log error dengan extra fields"""
        extra = {'extra_fields': extra_fields} if extra_fields else {}
        self.logger.error(message, extra=extra)
    
    def warning(self, message, **extra_fields):
        """Log warning dengan extra fields"""
        extra = {'extra_fields': extra_fields} if extra_fields else {}
        self.logger.warning(message, extra=extra)


# ==================== PROMETHEUS METRICS ====================

class MetricsCollector:
    """Kolektor metrics untuk Prometheus"""
    
    def __init__(self):
        # Counter metrics
        self.messages_processed = Counter(
            'weather_messages_processed_total',
            'Total number of weather messages processed',
            ['status', 'city']
        )
        
        self.ml_predictions = Counter(
            'ml_predictions_total',
            'Total ML predictions made',
            ['result']
        )
        
        self.errors = Counter(
            'pipeline_errors_total',
            'Total pipeline errors',
            ['component', 'error_type']
        )
        
        self.authentication_attempts = Counter(
            'authentication_attempts_total',
            'Total authentication attempts',
            ['status']
        )
        
        # Histogram metrics (untuk latency)
        self.processing_latency = Histogram(
            'message_processing_seconds',
            'Time spent processing messages',
            ['component']
        )
        
        self.ml_inference_latency = Histogram(
            'ml_inference_seconds',
            'Time spent on ML inference'
        )
        
        # Gauge metrics (untuk values yang bisa naik/turun)
        self.active_consumers = Gauge(
            'active_consumers',
            'Number of active Kafka consumers'
        )
        
        self.current_temperature = Gauge(
            'current_temperature_celsius',
            'Current temperature reading',
            ['city']
        )
        
        self.current_windspeed = Gauge(
            'current_windspeed_kmh',
            'Current windspeed reading',
            ['city']
        )
        
        self.system_cpu_usage = Gauge(
            'system_cpu_usage_percent',
            'System CPU usage percentage'
        )
        
        self.system_memory_usage = Gauge(
            'system_memory_usage_percent',
            'System memory usage percentage'
        )
        
        # Info metrics (untuk metadata)
        self.pipeline_info = Info(
            'pipeline_info',
            'Pipeline version and configuration info'
        )
        
        # Set pipeline info
        self.pipeline_info.info({
            'version': '1.0.0',
            'environment': 'development',
            'ml_model': 'IsolationForest'
        })
    
    def record_message_processed(self, city: str, status: str = 'success'):
        """Record processed message"""
        self.messages_processed.labels(status=status, city=city).inc()
    
    def record_ml_prediction(self, is_anomaly: bool):
        """Record ML prediction"""
        result = 'anomaly' if is_anomaly else 'normal'
        self.ml_predictions.labels(result=result).inc()
    
    def record_error(self, component: str, error_type: str):
        """Record error"""
        self.errors.labels(component=component, error_type=error_type).inc()
    
    def record_auth_attempt(self, success: bool):
        """Record authentication attempt"""
        status = 'success' if success else 'failure'
        self.authentication_attempts.labels(status=status).inc()
    
    def observe_processing_time(self, component: str, duration: float):
        """Record processing time"""
        self.processing_latency.labels(component=component).observe(duration)
    
    def observe_ml_inference_time(self, duration: float):
        """Record ML inference time"""
        self.ml_inference_latency.observe(duration)
    
    def update_weather_metrics(self, city: str, temperature: float, windspeed: float):
        """Update weather gauge metrics"""
        self.current_temperature.labels(city=city).set(temperature)
        self.current_windspeed.labels(city=city).set(windspeed)
    
    def update_system_metrics(self):
        """Update system resource metrics"""
        self.system_cpu_usage.set(psutil.cpu_percent())
        self.system_memory_usage.set(psutil.virtual_memory().percent)


# ==================== PERFORMANCE MONITOR ====================

class PerformanceMonitor:
    """Monitor performance pipeline dengan context manager"""
    
    def __init__(self, metrics_collector: MetricsCollector, component: str):
        self.metrics = metrics_collector
        self.component = component
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        self.metrics.observe_processing_time(self.component, duration)
        
        if exc_type is not None:
            # Ada error
            error_type = exc_type.__name__
            self.metrics.record_error(self.component, error_type)
        
        return False  # Don't suppress exceptions


# ==================== ERROR TRACKING ====================

class ErrorTracker:
    """Track dan analyze errors dalam pipeline"""
    
    def __init__(self, log_file='logs/data/errors.log'):
        self.error_log = log_file
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        self.logger = logging.getLogger('error_tracker')
        handler = logging.FileHandler(log_file)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - ERROR - %(message)s'
        ))
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.ERROR)
    
    def log_error(self, component: str, error: Exception, context: dict = None):
        """Log error dengan context"""
        error_data = {
            'component': component,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if context:
            error_data['context'] = context
        
        self.logger.error(json.dumps(error_data))


# ==================== HEALTH CHECK ====================

class HealthChecker:
    """Health check untuk monitoring sistem"""
    
    def __init__(self):
        self.checks = {}
    
    def register_check(self, name: str, check_func):
        """Register health check function"""
        self.checks[name] = check_func
    
    def run_checks(self) -> dict:
        """Run semua health checks"""
        results = {
            'timestamp': datetime.utcnow().isoformat(),
            'status': 'healthy',
            'checks': {}
        }
        
        for name, check_func in self.checks.items():
            try:
                check_result = check_func()
                results['checks'][name] = {
                    'status': 'pass' if check_result else 'fail',
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                if not check_result:
                    results['status'] = 'unhealthy'
                    
            except Exception as e:
                results['checks'][name] = {
                    'status': 'error',
                    'error': str(e),
                    'timestamp': datetime.utcnow().isoformat()
                }
                results['status'] = 'unhealthy'
        
        return results


# ==================== ALERTING ====================

class AlertManager:
    """Simple alerting system untuk threshold-based alerts"""
    
    def __init__(self, logger: StructuredLogger):
        self.logger = logger
        self.alert_thresholds = {
            'error_rate': 0.1,  # 10% error rate
            'cpu_usage': 80.0,  # 80% CPU
            'memory_usage': 80.0,  # 80% Memory
            'anomaly_rate': 0.3  # 30% anomaly rate
        }
        self.alert_cooldown = {}  # Prevent alert spam
    
    def check_and_alert(self, metric_name: str, current_value: float):
        """Check metric dan trigger alert jika melebihi threshold"""
        if metric_name not in self.alert_thresholds:
            return
        
        threshold = self.alert_thresholds[metric_name]
        
        if current_value > threshold:
            # Check cooldown (1 alert per 5 menit)
            last_alert = self.alert_cooldown.get(metric_name, 0)
            if time.time() - last_alert < 300:  # 5 minutes
                return
            
            self.logger.error(
                f"ALERT: {metric_name} exceeded threshold",
                metric=metric_name,
                current_value=current_value,
                threshold=threshold,
                severity='HIGH'
            )
            
            self.alert_cooldown[metric_name] = time.time()


# ==================== METRICS SERVER ====================

def start_metrics_server(port: int = 8000):
    """Start Prometheus metrics HTTP server"""
    start_http_server(port)
    logging.info(f"Metrics server started on port {port}")


# ==================== USAGE EXAMPLE ====================

if __name__ == "__main__":
    # Setup logging
    logger = StructuredLogger('monitoring_test')
    
    # Start metrics server
    print("Starting Prometheus metrics server on port 8000...")
    start_metrics_server(8000)
    
    # Initialize metrics collector
    metrics = MetricsCollector()
    
    # Simulate monitoring
    print("\nSimulating pipeline activity...")
    
    cities = ['Jakarta', 'Surabaya', 'Bandung']
    
    for i in range(10):
        city = cities[i % len(cities)]
        
        # Simulate message processing
        with PerformanceMonitor(metrics, 'consumer'):
            time.sleep(0.1)  # Simulate work
            metrics.record_message_processed(city, 'success')
            
            # Update weather metrics
            metrics.update_weather_metrics(city, 28.5 + i, 12.3 + i)
        
        # Simulate ML prediction
        with PerformanceMonitor(metrics, 'ml_inference'):
            time.sleep(0.05)
            is_anomaly = i % 5 == 0  # Every 5th is anomaly
            metrics.record_ml_prediction(is_anomaly)
        
        # Update system metrics
        metrics.update_system_metrics()
        
        # Structured logging
        logger.info(
            "Message processed",
            city=city,
            iteration=i,
            anomaly=is_anomaly
        )
    
    print("\nMetrics collected! View at http://localhost:8000/metrics")
    print("Press Ctrl+C to stop...")
    
    try:
        while True:
            time.sleep(1)
            metrics.update_system_metrics()
    except KeyboardInterrupt:
        print("\nShutting down...")
