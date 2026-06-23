"""
Metadata Manager — Mengelola metadata catalog untuk semua tabel dan kolom.

Fungsi utama:
- populate_metadata_catalog() → Isi tabel metadata_catalog dengan deskripsi
  semua tabel dan kolom secara otomatis
- get_data_freshness() → Cek kapan data terakhir diupdate per tabel
"""

import os
import sys
from datetime import datetime

# Tambahkan project root ke sys.path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from logs.monitoring import StructuredLogger
from dotenv import load_dotenv

load_dotenv()

# Logger
logger = StructuredLogger('MetadataManager')


# ============================================================
# DEFINISI METADATA — Deskripsi semua tabel dan kolom
# ============================================================

METADATA_DEFINITIONS = {
    'cuaca_realtime': {
        'owner': 'streaming',
        'sumber_data': 'Open-Meteo Forecast API (real-time)',
        'kolom': {
            'id': ('SERIAL', 'Primary key auto-increment'),
            'waktu': ('TIMESTAMP', 'Waktu pengambilan data cuaca'),
            'provinsi': ('VARCHAR(100)', 'Nama provinsi di Pulau Jawa'),
            'kab_kota': ('VARCHAR(100)', 'Nama kabupaten/kota'),
            'suhu': ('FLOAT', 'Suhu udara saat ini (°C)'),
            'kelembapan': ('FLOAT', 'Kelembapan udara (%)'),
            'curah_hujan': ('FLOAT', 'Curah hujan saat ini (mm)'),
            'kecepatan_angin': ('FLOAT', 'Kecepatan angin (km/h)'),
            'tekanan_udara': ('FLOAT', 'Tekanan udara permukaan laut (hPa)'),
            'kondisi_cuaca': ('VARCHAR(100)', 'Kondisi cuaca (Cerah, Hujan, dll)'),
            'deskripsi_cuaca': ('VARCHAR(255)', 'Deskripsi detail cuaca'),
            'sumber': ('VARCHAR(100)', 'Sumber data: Open-Meteo atau OpenWeatherMap'),
        }
    },

    'harga_pangan_raw': {
        'owner': 'batch',
        'sumber_data': 'SP2KP API Kemendag (api-sp2kp.kemendag.go.id)',
        'kolom': {
            'id': ('SERIAL', 'Primary key auto-increment'),
            'tanggal': ('DATE', 'Tanggal harga berlaku'),
            'provinsi': ('VARCHAR(100)', 'Nama provinsi (6 provinsi Jawa)'),
            'kab_kota': ('VARCHAR(100)', 'Nama kabupaten/kota'),
            'komoditas': ('VARCHAR(100)', 'Nama komoditas pangan (beras, cabai, dll)'),
            'harga': ('DECIMAL(15,2)', 'Harga komoditas dalam Rupiah'),
            'satuan': ('VARCHAR(50)', 'Satuan harga (kg, liter, butir)'),
            'pipeline_run_id': ('VARCHAR(50)', 'ID pipeline run saat data di-insert'),
            'created_at': ('TIMESTAMP', 'Waktu data masuk ke database'),
        }
    },

    'cuaca_historical': {
        'owner': 'batch',
        'sumber_data': 'Open-Meteo Archive API (archive-api.open-meteo.com)',
        'kolom': {
            'id': ('SERIAL', 'Primary key auto-increment'),
            'tanggal': ('DATE', 'Tanggal data cuaca'),
            'provinsi': ('VARCHAR(100)', 'Nama provinsi'),
            'kab_kota': ('VARCHAR(100)', 'Nama kabupaten/kota'),
            'latitude': ('FLOAT', 'Koordinat lintang (latitude)'),
            'longitude': ('FLOAT', 'Koordinat bujur (longitude)'),
            'suhu_mean': ('FLOAT', 'Suhu rata-rata harian (°C)'),
            'suhu_max': ('FLOAT', 'Suhu maksimum harian (°C)'),
            'suhu_min': ('FLOAT', 'Suhu minimum harian (°C)'),
            'curah_hujan_mm': ('FLOAT', 'Total curah hujan harian (mm)'),
            'kelembapan': ('FLOAT', 'Kelembapan rata-rata harian (%)'),
            'kecepatan_angin': ('FLOAT', 'Kecepatan angin rata-rata (km/h)'),
            'tekanan_udara': ('FLOAT', 'Tekanan udara rata-rata (hPa)'),
            'awan_persen': ('FLOAT', 'Persentase tutupan awan (%)'),
            'created_at': ('TIMESTAMP', 'Waktu data masuk ke database'),
        }
    },

    'cuaca_harga_merged': {
        'owner': 'pipeline',
        'sumber_data': 'Gabungan tabel cuaca_historical + harga_pangan_raw',
        'kolom': {
            'id': ('SERIAL', 'Primary key auto-increment'),
            'tanggal': ('DATE', 'Tanggal data gabungan'),
            'provinsi': ('VARCHAR(100)', 'Nama provinsi'),
            'kab_kota': ('VARCHAR(100)', 'Nama kabupaten/kota'),
            'komoditas': ('VARCHAR(100)', 'Nama komoditas pangan'),
            'harga': ('DECIMAL(15,2)', 'Harga komoditas (Rupiah)'),
            'suhu_mean': ('FLOAT', 'Suhu rata-rata pada tanggal tersebut (°C)'),
            'curah_hujan_mm': ('FLOAT', 'Curah hujan pada tanggal tersebut (mm)'),
            'kelembapan': ('FLOAT', 'Kelembapan rata-rata (%)'),
            'kecepatan_angin': ('FLOAT', 'Kecepatan angin rata-rata (km/h)'),
            'tekanan_udara': ('FLOAT', 'Tekanan udara rata-rata (hPa)'),
            'harga_lag_7d': ('DECIMAL(15,2)', 'Harga 7 hari yang lalu (Rupiah)'),
            'harga_change_pct': ('FLOAT', 'Persentase perubahan harga dari 7 hari lalu'),
            'curah_hujan_lag_7d': ('FLOAT', 'Curah hujan 7 hari yang lalu (mm)'),
            'created_at': ('TIMESTAMP', 'Waktu data masuk ke database'),
        }
    },

    'predictions': {
        'owner': 'models',
        'sumber_data': 'Model ML FoodPricePredictionModel (GradientBoosting)',
        'kolom': {
            'id': ('SERIAL', 'Primary key auto-increment'),
            'tanggal_prediksi': ('DATE', 'Tanggal prediksi dibuat'),
            'provinsi': ('VARCHAR(100)', 'Provinsi target prediksi'),
            'kab_kota': ('VARCHAR(100)', 'Kabupaten/kota target prediksi'),
            'komoditas': ('VARCHAR(100)', 'Komoditas yang diprediksi'),
            'prediksi_label': ('VARCHAR(20)', 'Hasil prediksi: NAIK / TURUN / STABIL'),
            'probabilitas_naik': ('FLOAT', 'Probabilitas harga naik (0-1)'),
            'probabilitas_turun': ('FLOAT', 'Probabilitas harga turun (0-1)'),
            'probabilitas_stabil': ('FLOAT', 'Probabilitas harga stabil (0-1)'),
            'fitur_cuaca': ('JSONB', 'Fitur cuaca yang digunakan sebagai input model'),
            'model_version': ('VARCHAR(50)', 'Versi model yang digunakan'),
            'created_at': ('TIMESTAMP', 'Waktu prediksi dibuat'),
        }
    },

    'alerts': {
        'owner': 'alerts',
        'sumber_data': 'PanganAlertManager (alerts/alert_manager.py)',
        'kolom': {
            'id': ('SERIAL', 'Primary key auto-increment'),
            'alert_type': ('VARCHAR(50)', 'Tipe: SPIKE, DATA_GAP, MODEL_DEGRADATION, PIPELINE_FAILURE'),
            'severity': ('VARCHAR(20)', 'Severity: INFO, WARNING, CRITICAL'),
            'message': ('TEXT', 'Pesan deskriptif tentang alert'),
            'komoditas': ('VARCHAR(100)', 'Komoditas terkait (opsional)'),
            'provinsi': ('VARCHAR(100)', 'Provinsi terkait (opsional)'),
            'nilai_aktual': ('FLOAT', 'Nilai yang memicu alert'),
            'nilai_threshold': ('FLOAT', 'Threshold yang dilanggar'),
            'is_resolved': ('BOOLEAN', 'Status resolved (TRUE/FALSE)'),
            'created_at': ('TIMESTAMP', 'Waktu alert dibuat'),
            'resolved_at': ('TIMESTAMP', 'Waktu alert di-resolve'),
        }
    },

    'audit_log': {
        'owner': 'governance',
        'sumber_data': 'AuditTrail (governance/audit_trail.py)',
        'kolom': {
            'id': ('SERIAL', 'Primary key auto-increment'),
            'tabel_nama': ('VARCHAR(100)', 'Nama tabel yang dioperasikan'),
            'operasi': ('VARCHAR(20)', 'Jenis operasi: INSERT, UPDATE, DELETE'),
            'username': ('VARCHAR(100)', 'User yang menjalankan operasi'),
            'pipeline_run_id': ('VARCHAR(50)', 'ID pipeline run terkait'),
            'row_id': ('INTEGER', 'ID baris yang dioperasikan'),
            'data_sebelum': ('JSONB', 'Snapshot data sebelum operasi'),
            'data_sesudah': ('JSONB', 'Snapshot data sesudah operasi'),
            'created_at': ('TIMESTAMP', 'Waktu operasi dilakukan'),
        }
    },

    'metadata_catalog': {
        'owner': 'governance',
        'sumber_data': 'MetadataManager (governance/metadata_manager.py)',
        'kolom': {
            'id': ('SERIAL', 'Primary key auto-increment'),
            'nama_tabel': ('VARCHAR(100)', 'Nama tabel di database'),
            'nama_kolom': ('VARCHAR(100)', 'Nama kolom dalam tabel'),
            'tipe_data': ('VARCHAR(50)', 'Tipe data kolom (VARCHAR, FLOAT, dll)'),
            'deskripsi': ('TEXT', 'Deskripsi kolom dalam bahasa Indonesia'),
            'owner': ('VARCHAR(100)', 'Pemilik/pengelola tabel'),
            'sumber_data': ('VARCHAR(200)', 'Sumber data asli'),
            'last_updated': ('TIMESTAMP', 'Terakhir metadata diupdate'),
        }
    },
}


class MetadataManager:
    """
    Mengelola metadata catalog untuk dokumentasi tabel dan kolom database.
    """

    def __init__(self, db_config=None):
        """
        Inisialisasi MetadataManager.

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
    # POPULATE METADATA CATALOG
    # ============================================================

    def populate_metadata_catalog(self):
        """
        Isi tabel metadata_catalog dengan deskripsi semua tabel dan kolom
        dari definisi METADATA_DEFINITIONS.

        Jika data sudah ada, akan di-update (upsert berdasarkan nama_tabel + nama_kolom).
        """
        try:
            import psycopg

            conn = psycopg.connect(**self.db_config)
            cur = conn.cursor()

            total_inserted = 0

            for tabel_nama, tabel_info in METADATA_DEFINITIONS.items():
                owner = tabel_info['owner']
                sumber = tabel_info['sumber_data']

                for kolom_nama, (tipe_data, deskripsi) in tabel_info['kolom'].items():
                    # Cek apakah sudah ada
                    cur.execute("""
                        SELECT id FROM metadata_catalog
                        WHERE nama_tabel = %s AND nama_kolom = %s
                    """, (tabel_nama, kolom_nama))

                    existing = cur.fetchone()

                    if existing:
                        # Update
                        cur.execute("""
                            UPDATE metadata_catalog
                            SET tipe_data = %s, deskripsi = %s, owner = %s,
                                sumber_data = %s, last_updated = NOW()
                            WHERE nama_tabel = %s AND nama_kolom = %s
                        """, (tipe_data, deskripsi, owner, sumber,
                              tabel_nama, kolom_nama))
                    else:
                        # Insert
                        cur.execute("""
                            INSERT INTO metadata_catalog
                                (nama_tabel, nama_kolom, tipe_data, deskripsi,
                                 owner, sumber_data, last_updated)
                            VALUES (%s, %s, %s, %s, %s, %s, NOW())
                        """, (tabel_nama, kolom_nama, tipe_data, deskripsi,
                              owner, sumber))
                        total_inserted += 1

            conn.commit()
            cur.close()
            conn.close()

            logger.info(
                f"Metadata catalog populated: {total_inserted} entries baru",
                total_tables=len(METADATA_DEFINITIONS)
            )

            return total_inserted

        except Exception as e:
            logger.error(f"Gagal populate metadata catalog: {str(e)}")
            return 0

    # ============================================================
    # GET DATA FRESHNESS
    # ============================================================

    def get_data_freshness(self):
        """
        Cek kapan data terakhir diupdate per tabel.
        Mengembalikan dict dengan info freshness setiap tabel.

        Returns:
            dict: {
                'tabel_nama': {
                    'last_update': datetime,
                    'total_rows': int,
                    'freshness_hours': float
                }
            }
        """
        # Tabel dan kolom timestamp masing-masing
        tables_config = {
            'cuaca_realtime': 'waktu',
            'harga_pangan_raw': 'created_at',
            'cuaca_historical': 'created_at',
            'cuaca_harga_merged': 'created_at',
            'predictions': 'created_at',
            'alerts': 'created_at',
            'audit_log': 'created_at',
        }

        freshness = {}

        try:
            import psycopg

            conn = psycopg.connect(**self.db_config)
            cur = conn.cursor()

            for tabel, ts_col in tables_config.items():
                try:
                    cur.execute(f"""
                        SELECT MAX({ts_col}), COUNT(*) FROM {tabel}
                    """)
                    result = cur.fetchone()

                    last_update = result[0]
                    total_rows = result[1] or 0

                    if last_update:
                        # Hitung berapa jam sejak update terakhir
                        now = datetime.now()
                        if hasattr(last_update, 'replace'):
                            # Handle timezone-aware datetime
                            try:
                                delta = now - last_update.replace(tzinfo=None)
                            except Exception:
                                delta = now - last_update
                        else:
                            delta = now - last_update
                        hours = delta.total_seconds() / 3600
                    else:
                        hours = None

                    freshness[tabel] = {
                        'last_update': last_update.isoformat() if last_update else None,
                        'total_rows': total_rows,
                        'freshness_hours': round(hours, 2) if hours else None,
                        'status': self._freshness_status(tabel, hours)
                    }

                except Exception as e:
                    freshness[tabel] = {
                        'last_update': None,
                        'total_rows': 0,
                        'freshness_hours': None,
                        'status': 'ERROR',
                        'error': str(e)
                    }

            cur.close()
            conn.close()

        except Exception as e:
            logger.error(f"Gagal cek data freshness: {str(e)}")
            return {'error': str(e)}

        logger.info("Data freshness check selesai", tables_checked=len(freshness))
        return freshness

    def _freshness_status(self, tabel: str, hours: float = None) -> str:
        """Tentukan status freshness berdasarkan umur data."""
        if hours is None:
            return 'EMPTY'

        # cuaca_realtime harus lebih segar (< 6 jam)
        if tabel == 'cuaca_realtime':
            if hours < 6:
                return 'FRESH'
            elif hours < 24:
                return 'STALE'
            else:
                return 'OUTDATED'

        # Tabel lain: < 24 jam = FRESH, < 72 jam = STALE
        if hours < 24:
            return 'FRESH'
        elif hours < 72:
            return 'STALE'
        else:
            return 'OUTDATED'

    # ============================================================
    # GET METADATA untuk tabel tertentu
    # ============================================================

    def get_table_metadata(self, tabel_nama: str) -> dict:
        """
        Ambil metadata untuk tabel tertentu dari database.

        Args:
            tabel_nama: Nama tabel

        Returns:
            dict: Metadata tabel termasuk daftar kolom
        """
        try:
            import psycopg

            conn = psycopg.connect(**self.db_config)
            cur = conn.cursor()

            cur.execute("""
                SELECT nama_kolom, tipe_data, deskripsi, owner, sumber_data
                FROM metadata_catalog
                WHERE nama_tabel = %s
                ORDER BY id
            """, (tabel_nama,))

            rows = cur.fetchall()
            cur.close()
            conn.close()

            if not rows:
                # Fallback ke definisi lokal
                if tabel_nama in METADATA_DEFINITIONS:
                    return METADATA_DEFINITIONS[tabel_nama]
                return {'error': f'Metadata tidak ditemukan untuk tabel: {tabel_nama}'}

            columns = [desc[0] for desc in cur.description] if hasattr(cur, 'description') else \
                       ['nama_kolom', 'tipe_data', 'deskripsi', 'owner', 'sumber_data']

            return {
                'nama_tabel': tabel_nama,
                'kolom': [dict(zip(columns, row)) for row in rows]
            }

        except Exception as e:
            logger.error(f"Gagal ambil metadata {tabel_nama}: {str(e)}")
            # Fallback ke definisi lokal
            if tabel_nama in METADATA_DEFINITIONS:
                return METADATA_DEFINITIONS[tabel_nama]
            return {'error': str(e)}

    # ============================================================
    # GET ALL TABLE NAMES
    # ============================================================

    def get_all_tables(self) -> list:
        """Kembalikan daftar semua tabel yang terdefinisi."""
        return list(METADATA_DEFINITIONS.keys())


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    manager = MetadataManager()

    print("=" * 60)
    print("METADATA MANAGER")
    print("=" * 60)

    # Populate metadata catalog
    print("\n--- Populating Metadata Catalog ---")
    count = manager.populate_metadata_catalog()
    print(f"Entries baru: {count}")

    # Cek data freshness
    print("\n--- Data Freshness ---")
    freshness = manager.get_data_freshness()
    for tabel, info in freshness.items():
        if isinstance(info, dict) and 'status' in info:
            print(f"  {tabel}: {info['status']} "
                  f"(rows={info.get('total_rows', 0)}, "
                  f"hours={info.get('freshness_hours', 'N/A')})")

    # List semua tabel
    print("\n--- Daftar Tabel ---")
    for t in manager.get_all_tables():
        info = METADATA_DEFINITIONS[t]
        print(f"  {t} ({info['owner']}) — {len(info['kolom'])} kolom")
