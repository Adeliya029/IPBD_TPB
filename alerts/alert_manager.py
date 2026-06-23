"""
Pangan Alert Manager — Sistem alerting khusus domain harga pangan.
Mengelola 5 tipe alert: HARGA_SPIKE, DATA_GAP, MODEL_DEGRADATION,
PIPELINE_FAILURE, dan ANOMALI_CUACA.

Output alert ke:
1. Tabel alerts di PostgreSQL (wajib)
2. Log file: logs/data/alerts.log (wajib)
3. Telegram Bot (opsional, via env var TELEGRAM_BOT_TOKEN & TELEGRAM_CHAT_ID)
"""

import os
import sys
import json
import time
import logging
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Tambahkan project root ke sys.path agar bisa import modul internal
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from alerts.alert_rules import AlertRules, ALERT_THRESHOLDS, SEVERITY_MAP
from logs.monitoring import StructuredLogger

load_dotenv()

# Logger khusus untuk alert
alert_logger = logging.getLogger('pangan_alert')
alert_logger.setLevel(logging.INFO)

# File handler untuk alerts.log
_log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs', 'data')
os.makedirs(_log_dir, exist_ok=True)
_file_handler = logging.FileHandler(os.path.join(_log_dir, 'alerts.log'))
_file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
))
alert_logger.addHandler(_file_handler)


class PanganAlertManager:
    """
    Alert manager khusus untuk domain harga pangan.
    Mengintegrasikan alert rules dengan output ke PostgreSQL, log file, dan Telegram.
    """

    def __init__(self, db_config=None):
        """
        Inisialisasi PanganAlertManager.

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

        # Telegram config (opsional)
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID', '')

        # Cooldown tracker — mencegah alert spam
        self._cooldown = {}
        self._cooldown_seconds = ALERT_THRESHOLDS.get('COOLDOWN_SECONDS', 300)

        # Structured logger dari modul monitoring yang sudah ada
        self.logger = StructuredLogger('PanganAlertManager')

    # ============================================================
    # CORE: Kirim alert ke semua channel
    # ============================================================

    def send_alert(self, alert_type: str, severity: str, message: str,
                   komoditas: str = None, provinsi: str = None,
                   nilai_aktual: float = None, nilai_threshold: float = None):
        """
        Kirim alert ke semua channel yang dikonfigurasi.

        Args:
            alert_type: Tipe alert (HARGA_SPIKE, DATA_GAP, dll)
            severity: INFO, WARNING, CRITICAL
            message: Pesan deskriptif
            komoditas: Nama komoditas (opsional)
            provinsi: Nama provinsi (opsional)
            nilai_aktual: Nilai aktual yang memicu alert
            nilai_threshold: Nilai threshold yang dilanggar
        """
        # Cek cooldown — hindari spam
        cooldown_key = f"{alert_type}:{komoditas}:{provinsi}"
        now = time.time()
        last_sent = self._cooldown.get(cooldown_key, 0)

        if now - last_sent < self._cooldown_seconds:
            self.logger.info(
                f"Alert di-skip (cooldown): {cooldown_key}",
                alert_type=alert_type
            )
            return False

        # Update cooldown
        self._cooldown[cooldown_key] = now

        # 1. Simpan ke PostgreSQL
        self._save_to_db(alert_type, severity, message,
                         komoditas, provinsi, nilai_aktual, nilai_threshold)

        # 2. Tulis ke log file
        self._write_to_log(alert_type, severity, message,
                           komoditas, provinsi, nilai_aktual)

        # 3. Kirim ke Telegram (jika dikonfigurasi)
        if self.telegram_token and self.telegram_chat_id:
            self._send_telegram(alert_type, severity, message)

        return True

    # ============================================================
    # OUTPUT 1: PostgreSQL
    # ============================================================

    def _save_to_db(self, alert_type, severity, message,
                    komoditas, provinsi, nilai_aktual, nilai_threshold):
        """Simpan alert ke tabel alerts di PostgreSQL."""
        try:
            import psycopg

            conn = psycopg.connect(**self.db_config)
            cur = conn.cursor()

            cur.execute("""
                INSERT INTO alerts (alert_type, severity, message, komoditas,
                                    provinsi, nilai_aktual, nilai_threshold,
                                    is_resolved, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, FALSE, NOW())
            """, (alert_type, severity, message, komoditas,
                  provinsi, nilai_aktual, nilai_threshold))

            conn.commit()
            cur.close()
            conn.close()

            self.logger.info(
                f"Alert disimpan ke PostgreSQL: {alert_type}",
                alert_type=alert_type, severity=severity
            )

        except Exception as e:
            # Jangan gagalkan seluruh proses jika DB tidak tersedia
            self.logger.error(
                f"Gagal simpan alert ke PostgreSQL: {str(e)}",
                alert_type=alert_type
            )

    # ============================================================
    # OUTPUT 2: Log File
    # ============================================================

    def _write_to_log(self, alert_type, severity, message,
                      komoditas, provinsi, nilai_aktual):
        """Tulis alert ke logs/data/alerts.log."""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'alert_type': alert_type,
            'severity': severity,
            'message': message,
            'komoditas': komoditas,
            'provinsi': provinsi,
            'nilai_aktual': nilai_aktual,
        }

        # Log sesuai severity
        log_msg = json.dumps(log_entry, ensure_ascii=False)
        if severity == 'CRITICAL':
            alert_logger.critical(log_msg)
        elif severity == 'WARNING':
            alert_logger.warning(log_msg)
        else:
            alert_logger.info(log_msg)

    # ============================================================
    # OUTPUT 3: Telegram (opsional)
    # ============================================================

    def _send_telegram(self, alert_type, severity, message):
        """
        Kirim alert ke Telegram Bot.
        Membutuhkan env var: TELEGRAM_BOT_TOKEN dan TELEGRAM_CHAT_ID.
        """
        try:
            # Emoji berdasarkan severity
            emoji = {"CRITICAL": "🚨", "WARNING": "⚠️", "INFO": "ℹ️"}.get(severity, "📌")

            text = (
                f"{emoji} *ALERT [{severity}]*\n"
                f"Tipe: `{alert_type}`\n"
                f"Pesan: {message}\n"
                f"Waktu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )

            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            payload = {
                'chat_id': self.telegram_chat_id,
                'text': text,
                'parse_mode': 'Markdown'
            }

            response = requests.post(url, json=payload, timeout=10)

            if response.status_code == 200:
                self.logger.info(f"Alert Telegram terkirim: {alert_type}")
            else:
                self.logger.warning(
                    f"Telegram gagal: HTTP {response.status_code}",
                    alert_type=alert_type
                )

        except Exception as e:
            self.logger.error(
                f"Gagal kirim Telegram: {str(e)}",
                alert_type=alert_type
            )

    # ============================================================
    # RULE 1: HARGA SPIKE
    # ============================================================

    def check_harga_spike(self, harga_sekarang: float, harga_3_hari_lalu: float,
                          komoditas: str = "", provinsi: str = ""):
        """
        Cek apakah harga naik > 20% dalam 3 hari.
        Jika ya, kirim alert CRITICAL.
        """
        triggered, msg = AlertRules.check_harga_spike(
            harga_sekarang, harga_3_hari_lalu, komoditas, provinsi
        )

        if triggered:
            pct = ((harga_sekarang - harga_3_hari_lalu) / harga_3_hari_lalu) * 100
            self.send_alert(
                alert_type="HARGA_SPIKE",
                severity=SEVERITY_MAP["HARGA_SPIKE"],
                message=msg,
                komoditas=komoditas,
                provinsi=provinsi,
                nilai_aktual=pct,
                nilai_threshold=ALERT_THRESHOLDS["HARGA_SPIKE_PCT"]
            )

        return triggered

    # ============================================================
    # RULE 2: DATA GAP
    # ============================================================

    def check_data_gap(self):
        """
        Cek apakah data cuaca_realtime terakhir sudah > 6 jam yang lalu.
        Query ke PostgreSQL tabel cuaca_realtime.
        """
        try:
            import psycopg

            conn = psycopg.connect(**self.db_config)
            cur = conn.cursor()

            cur.execute("""
                SELECT MAX(waktu) FROM cuaca_realtime
            """)
            result = cur.fetchone()
            cur.close()
            conn.close()

            if result and result[0]:
                last_update = result[0]
                gap_hours = (datetime.now() - last_update).total_seconds() / 3600

                triggered, msg = AlertRules.check_data_gap(gap_hours)

                if triggered:
                    self.send_alert(
                        alert_type="DATA_GAP",
                        severity=SEVERITY_MAP["DATA_GAP"],
                        message=msg,
                        nilai_aktual=gap_hours,
                        nilai_threshold=ALERT_THRESHOLDS["DATA_GAP_HOURS"]
                    )
                    return True
            else:
                # Tidak ada data sama sekali
                self.send_alert(
                    alert_type="DATA_GAP",
                    severity="CRITICAL",
                    message="DATA GAP: Tabel cuaca_realtime kosong. Belum ada data masuk.",
                    nilai_aktual=None,
                    nilai_threshold=ALERT_THRESHOLDS["DATA_GAP_HOURS"]
                )
                return True

        except Exception as e:
            self.logger.error(f"Gagal cek data gap: {str(e)}")

        return False

    # ============================================================
    # RULE 3: MODEL DEGRADATION
    # ============================================================

    def check_model_degradation(self, current_accuracy: float):
        """
        Cek apakah akurasi model di bawah threshold minimum.
        Dipanggil setelah evaluasi model.
        """
        triggered, msg = AlertRules.check_model_degradation(current_accuracy)

        if triggered:
            self.send_alert(
                alert_type="MODEL_DEGRADATION",
                severity=SEVERITY_MAP["MODEL_DEGRADATION"],
                message=msg,
                nilai_aktual=current_accuracy,
                nilai_threshold=ALERT_THRESHOLDS["MODEL_MIN_ACCURACY"]
            )

        return triggered

    # ============================================================
    # RULE 4: PIPELINE FAILURE
    # ============================================================

    def check_pipeline_failure(self, step_name: str, error_message: str,
                               pipeline_run_id: str = ""):
        """
        Kirim alert CRITICAL saat pipeline step gagal.
        """
        triggered, msg = AlertRules.check_pipeline_failure(step_name, error_message)

        if pipeline_run_id:
            msg += f" (Run ID: {pipeline_run_id})"

        self.send_alert(
            alert_type="PIPELINE_FAILURE",
            severity=SEVERITY_MAP["PIPELINE_FAILURE"],
            message=msg,
            nilai_aktual=None,
            nilai_threshold=None
        )

        return triggered

    # ============================================================
    # RULE 5: ANOMALI CUACA
    # ============================================================

    def check_anomali_cuaca(self, suhu: float = None, curah_hujan: float = None,
                            kab_kota: str = "", provinsi: str = ""):
        """
        Cek apakah data cuaca di luar range normal.
        Bisa juga dipanggil setelah IsolationForest mendeteksi anomali.
        """
        triggered, msg = AlertRules.check_anomali_cuaca(suhu, curah_hujan)

        if triggered:
            if kab_kota:
                msg += f" di {kab_kota}, {provinsi}"

            self.send_alert(
                alert_type="ANOMALI_CUACA",
                severity=SEVERITY_MAP["ANOMALI_CUACA"],
                message=msg,
                provinsi=provinsi,
                nilai_aktual=suhu or curah_hujan,
                nilai_threshold=None
            )

        return triggered

    # ============================================================
    # HELPER: Resolve alert
    # ============================================================

    def resolve_alert(self, alert_id: int):
        """Tandai alert sebagai resolved di PostgreSQL."""
        try:
            import psycopg

            conn = psycopg.connect(**self.db_config)
            cur = conn.cursor()

            cur.execute("""
                UPDATE alerts
                SET is_resolved = TRUE, resolved_at = NOW()
                WHERE id = %s
            """, (alert_id,))

            conn.commit()
            cur.close()
            conn.close()

            self.logger.info(f"Alert #{alert_id} di-resolve")
            return True

        except Exception as e:
            self.logger.error(f"Gagal resolve alert #{alert_id}: {str(e)}")
            return False

    # ============================================================
    # HELPER: Ambil alert aktif dari PostgreSQL
    # ============================================================

    def get_active_alerts(self, limit: int = 20):
        """Ambil alert yang belum resolved, urutkan dari terbaru."""
        try:
            import psycopg

            conn = psycopg.connect(**self.db_config)
            cur = conn.cursor()

            cur.execute("""
                SELECT id, alert_type, severity, message, komoditas,
                       provinsi, nilai_aktual, nilai_threshold,
                       is_resolved, created_at
                FROM alerts
                WHERE is_resolved = FALSE
                ORDER BY created_at DESC
                LIMIT %s
            """, (limit,))

            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
            cur.close()
            conn.close()

            return [dict(zip(columns, row)) for row in rows]

        except Exception as e:
            self.logger.error(f"Gagal ambil active alerts: {str(e)}")
            return []

    # ============================================================
    # HELPER: Ambil semua alert terbaru
    # ============================================================

    def get_recent_alerts(self, limit: int = 20):
        """Ambil alert terbaru (resolved maupun belum)."""
        try:
            import psycopg

            conn = psycopg.connect(**self.db_config)
            cur = conn.cursor()

            cur.execute("""
                SELECT id, alert_type, severity, message, komoditas,
                       provinsi, nilai_aktual, nilai_threshold,
                       is_resolved, created_at, resolved_at
                FROM alerts
                ORDER BY created_at DESC
                LIMIT %s
            """, (limit,))

            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
            cur.close()
            conn.close()

            return [dict(zip(columns, row)) for row in rows]

        except Exception as e:
            self.logger.error(f"Gagal ambil recent alerts: {str(e)}")
            return []

    # ============================================================
    # BATCH CHECK: Cek harga spike untuk semua komoditas dari DB
    # ============================================================

    def batch_check_harga_spike_from_db(self):
        """
        Jalankan pengecekan harga spike untuk semua komoditas
        berdasarkan data di tabel harga_pangan_raw.
        """
        try:
            import psycopg

            conn = psycopg.connect(**self.db_config)
            cur = conn.cursor()

            # Ambil harga terbaru vs 3 hari lalu per komoditas per provinsi
            cur.execute("""
                WITH latest AS (
                    SELECT komoditas, provinsi, harga, tanggal,
                           ROW_NUMBER() OVER (
                               PARTITION BY komoditas, provinsi
                               ORDER BY tanggal DESC
                           ) as rn
                    FROM harga_pangan_raw
                ),
                harga_terbaru AS (
                    SELECT komoditas, provinsi, harga as harga_now, tanggal as tgl_now
                    FROM latest WHERE rn = 1
                ),
                harga_lama AS (
                    SELECT komoditas, provinsi, harga as harga_old, tanggal as tgl_old
                    FROM latest WHERE rn = 4
                )
                SELECT t.komoditas, t.provinsi, t.harga_now, l.harga_old
                FROM harga_terbaru t
                JOIN harga_lama l ON t.komoditas = l.komoditas
                                  AND t.provinsi = l.provinsi
                WHERE l.harga_old > 0
            """)

            rows = cur.fetchall()
            cur.close()
            conn.close()

            triggered_count = 0
            for komoditas, provinsi, harga_now, harga_old in rows:
                if self.check_harga_spike(
                    float(harga_now), float(harga_old), komoditas, provinsi
                ):
                    triggered_count += 1

            self.logger.info(
                f"Batch harga spike check selesai: {triggered_count} alert triggered "
                f"dari {len(rows)} kombinasi komoditas-provinsi"
            )

            return triggered_count

        except Exception as e:
            self.logger.error(f"Gagal batch check harga spike: {str(e)}")
            return 0


# ============================================================
# USAGE EXAMPLE
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("TESTING PANGAN ALERT MANAGER")
    print("=" * 60)

    manager = PanganAlertManager()

    # Test 1: Harga spike
    print("\n--- Test Harga Spike ---")
    manager.check_harga_spike(
        harga_sekarang=18000,
        harga_3_hari_lalu=12000,
        komoditas="Cabai Merah Besar",
        provinsi="DKI JAKARTA"
    )

    # Test 2: Model degradation
    print("\n--- Test Model Degradation ---")
    manager.check_model_degradation(current_accuracy=0.45)

    # Test 3: Pipeline failure
    print("\n--- Test Pipeline Failure ---")
    manager.check_pipeline_failure(
        step_name="download_cuaca",
        error_message="ConnectionTimeout: Open-Meteo API tidak merespons",
        pipeline_run_id="run-12345"
    )

    # Test 4: Anomali cuaca
    print("\n--- Test Anomali Cuaca ---")
    manager.check_anomali_cuaca(
        suhu=55.0,
        curah_hujan=250.0,
        kab_kota="KOTA SURABAYA",
        provinsi="JAWA TIMUR"
    )

    print("\n✅ Testing selesai. Cek logs/data/alerts.log untuk hasil.")
