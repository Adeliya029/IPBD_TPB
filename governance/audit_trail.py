"""
Audit Trail — Logging pipeline runs dan data lineage.

Fungsi utama:
- log_pipeline_run() → insert catatan pipeline run ke tabel audit_log
- log_data_lineage()  → generate file lineage.json yang mendokumentasikan
  alur data dari sumber ke tujuan akhir
"""

import os
import sys
import json
from datetime import datetime

# Tambahkan project root ke sys.path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from logs.monitoring import StructuredLogger
from dotenv import load_dotenv

load_dotenv()

# Logger
logger = StructuredLogger('AuditTrail')

# Path konfigurasi
PROJECT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
LINEAGE_PATH = os.path.join(PROJECT_ROOT, 'logs', 'data', 'lineage.json')


class AuditTrail:
    """
    Menyediakan audit trail untuk pipeline data.
    Mencatat setiap pipeline run dan menyediakan data lineage.
    """

    def __init__(self, db_config=None):
        """
        Inisialisasi AuditTrail.

        Args:
            db_config: Dict konfigurasi PostgreSQL. Jika None, ambil dari .env.
        """
        self.db_config = db_config or {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', '5440')),
            'dbname': os.getenv('POSTGRES_DB', 'harga_pangan'),
            'user': os.getenv('POSTGRES_USER', 'postgres'),
            'password': os.getenv('POSTGRES_PASSWORD', 'postgres'),
        }

    # ============================================================
    # LOG PIPELINE RUN
    # ============================================================

    def log_pipeline_run(self, pipeline_run_id: str, tabel_nama: str,
                         operasi: str, username: str = "system",
                         rows_processed: int = 0,
                         status: str = "SUCCESS",
                         start_time: str = None,
                         end_time: str = None,
                         data_sebelum: dict = None,
                         data_sesudah: dict = None):
        """
        Catat pipeline run ke tabel audit_log di PostgreSQL.

        Args:
            pipeline_run_id: UUID unik per pipeline run
            tabel_nama: Nama tabel yang di-insert/update (misalnya 'harga_pangan_raw')
            operasi: INSERT, UPDATE, atau DELETE
            username: Siapa yang menjalankan pipeline
            rows_processed: Jumlah baris yang diproses
            status: SUCCESS atau FAILED
            start_time: Waktu mulai pipeline (ISO format)
            end_time: Waktu selesai pipeline (ISO format)
            data_sebelum: Data sebelum operasi (untuk audit)
            data_sesudah: Data sesudah operasi (untuk audit)
        """
        try:
            import psycopg

            # Buat data_sesudah yang informatif
            sesudah = data_sesudah or {
                'rows_processed': rows_processed,
                'status': status,
                'start_time': start_time or datetime.now().isoformat(),
                'end_time': end_time or datetime.now().isoformat(),
            }

            conn = psycopg.connect(**self.db_config)
            cur = conn.cursor()

            cur.execute("""
                INSERT INTO audit_log (tabel_nama, operasi, username,
                                       pipeline_run_id, data_sebelum,
                                       data_sesudah, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
            """, (
                tabel_nama,
                operasi,
                username,
                pipeline_run_id,
                json.dumps(data_sebelum) if data_sebelum else None,
                json.dumps(sesudah),
            ))

            conn.commit()
            cur.close()
            conn.close()

            logger.info(
                f"Audit log recorded: {operasi} pada {tabel_nama}",
                pipeline_run_id=pipeline_run_id,
                rows_processed=rows_processed,
                status=status
            )

            return True

        except Exception as e:
            logger.error(
                f"Gagal log pipeline run: {str(e)}",
                pipeline_run_id=pipeline_run_id
            )
            return False

    # ============================================================
    # LOG STEP PIPELINE
    # ============================================================

    def log_step(self, pipeline_run_id: str, step_name: str,
                 status: str, detail: dict = None):
        """
        Catat satu step dari pipeline ke audit_log.

        Args:
            pipeline_run_id: UUID pipeline run
            step_name: Nama step (misalnya 'download_cuaca', 'clean_harga')
            status: SUCCESS atau FAILED
            detail: Detail tambahan dalam bentuk dict
        """
        data_sesudah = {
            'step': step_name,
            'status': status,
            'timestamp': datetime.now().isoformat(),
        }
        if detail:
            data_sesudah.update(detail)

        return self.log_pipeline_run(
            pipeline_run_id=pipeline_run_id,
            tabel_nama=f"pipeline_step:{step_name}",
            operasi="INSERT",
            username="pipeline",
            status=status,
            data_sesudah=data_sesudah
        )

    # ============================================================
    # DATA LINEAGE
    # ============================================================

    def log_data_lineage(self, output_path: str = None):
        """
        Generate file lineage.json yang mendokumentasikan alur data
        dari sumber ke tujuan akhir.

        Alur data:
        SP2KP API & Open-Meteo → raw CSV → MinIO raw-zone
        → PostgreSQL raw → cleaned → MinIO processed-zone
        → merged → model training → predictions → dashboard

        Args:
            output_path: Path output file. Default: logs/data/lineage.json
        """
        path = output_path or LINEAGE_PATH
        os.makedirs(os.path.dirname(path), exist_ok=True)

        lineage = {
            'generated_at': datetime.now().isoformat(),
            'project': 'IPBD_TPB — Analisis & Prediksi Harga Pangan',
            'deskripsi': 'Data lineage menunjukkan alur data dari sumber ke tujuan akhir.',

            'sumber_data': [
                {
                    'nama': 'SP2KP API (Kemendag)',
                    'url': 'https://api-sp2kp.kemendag.go.id',
                    'tipe': 'REST API',
                    'deskripsi': 'Data harga pangan harian untuk 6 provinsi di Pulau Jawa',
                    'frekuensi': 'Harian (batch mingguan)',
                    'format': 'JSON → CSV'
                },
                {
                    'nama': 'Open-Meteo Archive API',
                    'url': 'https://archive-api.open-meteo.com',
                    'tipe': 'REST API (gratis, tanpa API key)',
                    'deskripsi': 'Data cuaca historis: suhu, hujan, kelembapan, angin, tekanan, awan',
                    'frekuensi': 'Batch (periode Jan-Mei 2026)',
                    'format': 'JSON → CSV'
                },
                {
                    'nama': 'Open-Meteo Forecast API',
                    'url': 'https://api.open-meteo.com/v1/forecast',
                    'tipe': 'REST API (gratis)',
                    'deskripsi': 'Data cuaca realtime untuk 119 kab/kota di Jawa',
                    'frekuensi': 'Streaming (per jam)',
                    'format': 'JSON → Kafka → PostgreSQL'
                }
            ],

            'alur_data': [
                {
                    'step': 1,
                    'nama': 'Ingestion (Batch)',
                    'input': ['SP2KP API', 'Open-Meteo Archive API'],
                    'output': [
                        'data/raw/harga/harga_jawa_jan_mei_2026.csv',
                        'data/raw/cuaca/cuaca_openmeteo_minggu_*.csv'
                    ],
                    'script': ['batch/harga/batch_pangan.py', 'batch/cuaca/histori_cuaca.py'],
                    'deskripsi': 'Download data mentah dari API'
                },
                {
                    'step': 2,
                    'nama': 'Ingestion (Streaming)',
                    'input': ['Open-Meteo Forecast API'],
                    'output': ['Kafka topic: cuaca-stream'],
                    'script': ['streaming/open_producer.py'],
                    'deskripsi': 'Streaming data cuaca realtime ke Kafka'
                },
                {
                    'step': 3,
                    'nama': 'Storage (Data Lake)',
                    'input': ['data/raw/*'],
                    'output': ['MinIO raw-zone bucket'],
                    'script': ['batch/storage/upload_minio.py'],
                    'deskripsi': 'Upload raw data ke MinIO (raw-zone)'
                },
                {
                    'step': 4,
                    'nama': 'Cleaning',
                    'input': ['data/raw/harga/*.csv', 'data/raw/cuaca/*.csv'],
                    'output': [
                        'data/processed/harga/harga_jawa_jan_mei_2026.csv',
                        'data/processed/cuaca/cuaca_openmeteo_minggu_*.csv'
                    ],
                    'script': ['batch/harga/clean_harga.py', 'batch/cuaca/clean_cuaca.py'],
                    'deskripsi': 'Cleaning: handle harga=0, ffill, drop duplikat, type conversion'
                },
                {
                    'step': 5,
                    'nama': 'Storage (Processed)',
                    'input': ['data/processed/*'],
                    'output': ['MinIO processed-zone bucket'],
                    'script': ['batch/storage/upload_minio.py'],
                    'deskripsi': 'Upload cleaned data ke MinIO (processed-zone)'
                },
                {
                    'step': 6,
                    'nama': 'Load to PostgreSQL',
                    'input': ['data/processed/*.csv', 'Kafka cuaca-stream'],
                    'output': [
                        'PostgreSQL: harga_pangan_raw',
                        'PostgreSQL: cuaca_historical',
                        'PostgreSQL: cuaca_realtime'
                    ],
                    'script': ['pipeline/run_batch.py', 'streaming/open_consumer.py'],
                    'deskripsi': 'Load data ke PostgreSQL untuk query analitik'
                },
                {
                    'step': 7,
                    'nama': 'Merge & Feature Engineering',
                    'input': ['PostgreSQL: harga_pangan_raw', 'PostgreSQL: cuaca_historical'],
                    'output': ['PostgreSQL: cuaca_harga_merged'],
                    'script': ['pipeline/run_batch.py'],
                    'deskripsi': 'Merge data cuaca + harga, buat lag features'
                },
                {
                    'step': 8,
                    'nama': 'Model Training',
                    'input': ['PostgreSQL: cuaca_harga_merged'],
                    'output': ['models/saved/food_price_predictor.pkl'],
                    'script': ['models/price_prediction_model.py'],
                    'deskripsi': 'Train GradientBoosting: prediksi NAIK/TURUN/STABIL'
                },
                {
                    'step': 9,
                    'nama': 'Prediction',
                    'input': ['models/saved/food_price_predictor.pkl', 'cuaca_realtime'],
                    'output': ['PostgreSQL: predictions'],
                    'script': ['consumer_price_prediction.py'],
                    'deskripsi': 'Prediksi harga pangan berdasarkan cuaca terkini'
                },
                {
                    'step': 10,
                    'nama': 'Visualization',
                    'input': ['PostgreSQL: semua tabel'],
                    'output': ['Grafana Dashboard (port 3000)'],
                    'script': ['dashboard/app.py'],
                    'deskripsi': 'Dashboard interaktif: overview, analisis, prediksi, explorer, monitoring'
                }
            ],

            'quality_checks': {
                'script': 'governance/quality_checks.py',
                'report': 'logs/data/quality_report.json',
                'deskripsi': 'Validasi data setelah cleaning (suhu range, harga bounds, duplikat)'
            },

            'audit': {
                'script': 'governance/audit_trail.py',
                'tabel': 'audit_log',
                'deskripsi': 'Trail audit untuk setiap pipeline run dan operasi data'
            }
        }

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(lineage, f, indent=2, ensure_ascii=False)

        logger.info(f"Data lineage disimpan ke {path}")
        print(f"✅ Data lineage disimpan ke: {path}")

        return lineage

    # ============================================================
    # GET AUDIT HISTORY
    # ============================================================

    def get_audit_history(self, pipeline_run_id: str = None, limit: int = 50):
        """
        Ambil riwayat audit dari tabel audit_log.

        Args:
            pipeline_run_id: Filter berdasarkan run_id (opsional)
            limit: Jumlah maksimal baris

        Returns:
            list[dict]: Daftar audit entries
        """
        try:
            import psycopg

            conn = psycopg.connect(**self.db_config)
            cur = conn.cursor()

            if pipeline_run_id:
                cur.execute("""
                    SELECT id, tabel_nama, operasi, username, pipeline_run_id,
                           data_sebelum, data_sesudah, created_at
                    FROM audit_log
                    WHERE pipeline_run_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (pipeline_run_id, limit))
            else:
                cur.execute("""
                    SELECT id, tabel_nama, operasi, username, pipeline_run_id,
                           data_sebelum, data_sesudah, created_at
                    FROM audit_log
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (limit,))

            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
            cur.close()
            conn.close()

            return [dict(zip(columns, row)) for row in rows]

        except Exception as e:
            logger.error(f"Gagal ambil audit history: {str(e)}")
            return []


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    audit = AuditTrail()

    # Generate data lineage
    print("=" * 60)
    print("GENERATING DATA LINEAGE")
    print("=" * 60)
    lineage = audit.log_data_lineage()

    print(f"\nTotal steps: {len(lineage['alur_data'])}")
    for step in lineage['alur_data']:
        print(f"  Step {step['step']}: {step['nama']}")

    # Test log pipeline run
    print("\n" + "=" * 60)
    print("TESTING PIPELINE LOG")
    print("=" * 60)
    import uuid
    run_id = str(uuid.uuid4())[:8]
    audit.log_pipeline_run(
        pipeline_run_id=f"run-{run_id}",
        tabel_nama="harga_pangan_raw",
        operasi="INSERT",
        rows_processed=15000,
        status="SUCCESS",
        start_time=datetime.now().isoformat()
    )
    print(f"Pipeline run logged: run-{run_id}")
