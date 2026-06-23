"""
Health Check — Cek kesehatan semua layanan infrastruktur.

Layanan yang dicek:
- PostgreSQL (psycopg connect)
- Kafka (KafkaProducer test connect)
- MinIO (list buckets)
- Data freshness cuaca_realtime (< 6 jam terakhir)

Output: JSON health report + kirim ke tabel alerts jika ada issue.
"""

import os
import sys
import json
from datetime import datetime

# Tambahkan project root ke sys.path
PROJECT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, PROJECT_ROOT)

from logs.monitoring import StructuredLogger
from dotenv import load_dotenv

load_dotenv()

# Logger
logger = StructuredLogger('HealthCheck')

# Path untuk health report
REPORT_DIR = os.path.join(PROJECT_ROOT, 'logs', 'data')
REPORT_PATH = os.path.join(REPORT_DIR, 'health_report.json')


class HealthCheck:
    """
    Cek kesehatan semua layanan infrastruktur proyek IPBD_TPB.
    """

    def __init__(self):
        self.db_config = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', '5440')),
            'dbname': os.getenv('POSTGRES_DB', 'harga_pangan'),
            'user': os.getenv('POSTGRES_USER', 'postgres'),
            'password': os.getenv('POSTGRES_PASSWORD', 'postgres'),
        }

        self.results = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'HEALTHY',
            'checks': {}
        }

    # ============================================================
    # CHECK 1: PostgreSQL
    # ============================================================

    def check_postgresql(self) -> dict:
        """Cek koneksi ke PostgreSQL dan hitung jumlah tabel."""
        try:
            import psycopg

            conn = psycopg.connect(**self.db_config, connect_timeout=5)
            cur = conn.cursor()

            # Cek jumlah tabel
            cur.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public'
            """)
            tables = [row[0] for row in cur.fetchall()]

            # Cek versi PostgreSQL
            cur.execute("SELECT version()")
            version = cur.fetchone()[0]

            cur.close()
            conn.close()

            result = {
                'status': 'HEALTHY',
                'message': f'Connected. {len(tables)} tabel ditemukan.',
                'tables': tables,
                'version': version[:50],
                'host': self.db_config['host'],
                'port': self.db_config['port'],
            }

            logger.info(f"PostgreSQL: HEALTHY ({len(tables)} tabel)")

        except Exception as e:
            result = {
                'status': 'UNHEALTHY',
                'message': f'Gagal connect: {str(e)}',
                'host': self.db_config['host'],
                'port': self.db_config['port'],
            }
            self.results['overall_status'] = 'UNHEALTHY'
            logger.error(f"PostgreSQL: UNHEALTHY — {str(e)}")

        self.results['checks']['postgresql'] = result
        return result

    # ============================================================
    # CHECK 2: Kafka
    # ============================================================

    def check_kafka(self) -> dict:
        """Cek koneksi ke Kafka broker."""
        try:
            from kafka import KafkaProducer

            bootstrap = os.getenv('KAFKA_BOOTSTRAP', 'localhost:9092')

            producer = KafkaProducer(
                bootstrap_servers=bootstrap,
                request_timeout_ms=5000,
                max_block_ms=5000
            )

            # Cek metadata
            metadata = producer.partitions_for(os.getenv('TOPIC_CUACA', 'cuaca-stream'))
            producer.close()

            result = {
                'status': 'HEALTHY',
                'message': 'Connected ke Kafka broker.',
                'bootstrap': bootstrap,
                'topic_partitions': len(metadata) if metadata else 0,
            }
            logger.info(f"Kafka: HEALTHY (bootstrap={bootstrap})")

        except Exception as e:
            result = {
                'status': 'UNHEALTHY',
                'message': f'Gagal connect: {str(e)}',
                'bootstrap': os.getenv('KAFKA_BOOTSTRAP', 'localhost:9092'),
            }
            self.results['overall_status'] = 'UNHEALTHY'
            logger.error(f"Kafka: UNHEALTHY — {str(e)}")

        self.results['checks']['kafka'] = result
        return result

    # ============================================================
    # CHECK 3: MinIO
    # ============================================================

    def check_minio(self) -> dict:
        """Cek koneksi ke MinIO dan list buckets."""
        try:
            from minio import Minio

            endpoint = os.getenv('MINIO_ENDPOINT', 'localhost:9000')

            client = Minio(
                endpoint=endpoint,
                access_key=os.getenv('MINIO_ACCESS_KEY', 'minioadmin'),
                secret_key=os.getenv('MINIO_SECRET_KEY', 'minioadmin'),
                secure=os.getenv('MINIO_SECURE', 'False').lower() == 'true'
            )

            buckets = [b.name for b in client.list_buckets()]

            result = {
                'status': 'HEALTHY',
                'message': f'Connected. {len(buckets)} bucket ditemukan.',
                'buckets': buckets,
                'endpoint': endpoint,
            }
            logger.info(f"MinIO: HEALTHY ({len(buckets)} buckets)")

        except Exception as e:
            result = {
                'status': 'UNHEALTHY',
                'message': f'Gagal connect: {str(e)}',
                'endpoint': os.getenv('MINIO_ENDPOINT', 'localhost:9000'),
            }
            self.results['overall_status'] = 'UNHEALTHY'
            logger.error(f"MinIO: UNHEALTHY — {str(e)}")

        self.results['checks']['minio'] = result
        return result

    # ============================================================
    # CHECK 4: Data Freshness (cuaca_realtime)
    # ============================================================

    def check_data_freshness(self) -> dict:
        """Cek apakah data cuaca_realtime punya data < 6 jam terakhir."""
        try:
            import psycopg

            conn = psycopg.connect(**self.db_config, connect_timeout=5)
            cur = conn.cursor()

            cur.execute("""
                SELECT MAX(waktu), COUNT(*) FROM cuaca_realtime
            """)
            row = cur.fetchone()

            last_update = row[0]
            total_rows = row[1] or 0

            cur.close()
            conn.close()

            if last_update:
                now = datetime.now()
                try:
                    gap_hours = (now - last_update.replace(tzinfo=None)).total_seconds() / 3600
                except Exception:
                    gap_hours = (now - last_update).total_seconds() / 3600

                is_fresh = gap_hours < 6

                result = {
                    'status': 'HEALTHY' if is_fresh else 'WARNING',
                    'message': f'Data terakhir: {gap_hours:.1f} jam lalu ({total_rows} total baris)',
                    'last_update': last_update.isoformat(),
                    'gap_hours': round(gap_hours, 2),
                    'total_rows': total_rows,
                    'threshold_hours': 6,
                }

                if not is_fresh:
                    self.results['overall_status'] = 'WARNING'
                    logger.warning(f"Data freshness: WARNING — data {gap_hours:.1f} jam lalu")
                else:
                    logger.info(f"Data freshness: HEALTHY ({gap_hours:.1f} jam)")

            else:
                result = {
                    'status': 'WARNING',
                    'message': 'Tabel cuaca_realtime kosong (belum ada data)',
                    'last_update': None,
                    'total_rows': 0,
                }
                self.results['overall_status'] = 'WARNING'

        except Exception as e:
            result = {
                'status': 'UNHEALTHY',
                'message': f'Gagal cek freshness: {str(e)}',
            }
            self.results['overall_status'] = 'UNHEALTHY'
            logger.error(f"Data freshness: ERROR — {str(e)}")

        self.results['checks']['data_freshness'] = result
        return result

    # ============================================================
    # RUN ALL CHECKS
    # ============================================================

    def run_all(self) -> dict:
        """
        Jalankan semua health checks dan simpan hasilnya.

        Returns:
            dict: Health report lengkap
        """
        print("=" * 60)
        print("HEALTH CHECK — IPBD_TPB")
        print(f"Waktu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        # Jalankan semua checks
        checks = [
            ("PostgreSQL", self.check_postgresql),
            ("Kafka", self.check_kafka),
            ("MinIO", self.check_minio),
            ("Data Freshness", self.check_data_freshness),
        ]

        for name, check_func in checks:
            try:
                result = check_func()
                icon = "✅" if result['status'] == 'HEALTHY' else \
                       "⚠️" if result['status'] == 'WARNING' else "❌"
                print(f"  {icon} {name}: {result['status']} — {result['message']}")
            except Exception as e:
                print(f"  ❌ {name}: ERROR — {str(e)}")

        print(f"\nOverall: {self.results['overall_status']}")

        # Simpan report
        self._save_report()

        # Kirim alert jika ada issue
        self._send_alerts_if_needed()

        return self.results

    # ============================================================
    # SAVE REPORT
    # ============================================================

    def _save_report(self):
        """Simpan health report ke file JSON."""
        os.makedirs(REPORT_DIR, exist_ok=True)

        with open(REPORT_PATH, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"Health report disimpan ke {REPORT_PATH}")

    # ============================================================
    # SEND ALERTS
    # ============================================================

    def _send_alerts_if_needed(self):
        """Kirim alert ke tabel alerts jika ada layanan yang unhealthy."""
        if self.results['overall_status'] == 'HEALTHY':
            return

        try:
            from alerts.alert_manager import PanganAlertManager

            alert_mgr = PanganAlertManager(db_config=self.db_config)

            for service, result in self.results['checks'].items():
                if result.get('status') in ['UNHEALTHY', 'WARNING']:
                    severity = 'CRITICAL' if result['status'] == 'UNHEALTHY' else 'WARNING'
                    alert_mgr.send_alert(
                        alert_type='PIPELINE_FAILURE',
                        severity=severity,
                        message=f"Health Check {service}: {result['message']}",
                    )

        except Exception as e:
            logger.error(f"Gagal kirim alert dari health check: {str(e)}")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    hc = HealthCheck()
    report = hc.run_all()

    print(f"\n📄 Report: {REPORT_PATH}")
