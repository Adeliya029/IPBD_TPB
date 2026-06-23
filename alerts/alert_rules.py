"""
Alert Rules — Konfigurasi threshold untuk sistem alerting harga pangan.
Semua threshold bisa di-override melalui environment variable (.env).
"""

import os
from dotenv import load_dotenv

# Load .env dari project root
load_dotenv()


# ============================================================
# DEFAULT THRESHOLD — bisa di-override via .env
# ============================================================

ALERT_THRESHOLDS = {

    # HARGA_SPIKE: harga naik > X% dalam 3 hari → CRITICAL
    "HARGA_SPIKE_PCT": float(os.getenv("ALERT_HARGA_SPIKE_PCT", "20.0")),
    "HARGA_SPIKE_DAYS": int(os.getenv("ALERT_HARGA_SPIKE_DAYS", "3")),

    # DATA_GAP: data cuaca tidak masuk > X jam → WARNING
    "DATA_GAP_HOURS": float(os.getenv("ALERT_DATA_GAP_HOURS", "6.0")),

    # MODEL_DEGRADATION: akurasi model di bawah X% → WARNING
    "MODEL_MIN_ACCURACY": float(os.getenv("ALERT_MODEL_MIN_ACCURACY", "0.60")),

    # ANOMALI_CUACA: threshold untuk IsolationForest → INFO
    "ANOMALI_SUHU_MIN": float(os.getenv("ALERT_ANOMALI_SUHU_MIN", "-10.0")),
    "ANOMALI_SUHU_MAX": float(os.getenv("ALERT_ANOMALI_SUHU_MAX", "50.0")),
    "ANOMALI_CURAH_HUJAN_MAX": float(os.getenv("ALERT_ANOMALI_CURAH_HUJAN_MAX", "200.0")),

    # SYSTEM RESOURCE → WARNING
    "CPU_THRESHOLD": float(os.getenv("ALERT_CPU_THRESHOLD", "80.0")),
    "MEMORY_THRESHOLD": float(os.getenv("ALERT_MEMORY_THRESHOLD", "80.0")),

    # HARGA BATAS WAJAR → WARNING
    "HARGA_MIN": float(os.getenv("ALERT_HARGA_MIN", "100")),
    "HARGA_MAX": float(os.getenv("ALERT_HARGA_MAX", "1000000")),

    # Alert cooldown (detik) — mencegah spam
    "COOLDOWN_SECONDS": int(os.getenv("ALERT_COOLDOWN_SECONDS", "300")),
}


# ============================================================
# DAFTAR KOMODITAS VALID (untuk validasi)
# ============================================================

KOMODITAS_VALID = [
    "Beras Medium", "Beras Premium",
    "Cabai Merah Besar", "Cabai Merah Keriting", "Cabai Rawit Merah", "Cabai Rawit Hijau",
    "Bawang Merah", "Bawang Putih Bonggol",
    "Minyak Goreng Curah", "Minyak Goreng Kemasan Sederhana",
    "Gula Pasir Lokal", "Gula Pasir Premium",
    "Daging Sapi Murni", "Daging Ayam Ras",
    "Telur Ayam Ras",
    "Tepung Terigu Curah",
    "Kedelai Biji Kering (Impor)",
    "Jagung Pipilan Kering",
    "Ikan Kembung", "Ikan Tongkol",
    "Susu Kental Manis",
]


# ============================================================
# SEVERITY MAPPING
# ============================================================

SEVERITY_MAP = {
    "HARGA_SPIKE": "CRITICAL",
    "DATA_GAP": "WARNING",
    "MODEL_DEGRADATION": "WARNING",
    "PIPELINE_FAILURE": "CRITICAL",
    "ANOMALI_CUACA": "INFO",
    "SYSTEM_RESOURCE": "WARNING",
}


class AlertRules:
    """
    Kelas helper untuk mengevaluasi alert rules.
    Semua method mengembalikan tuple (is_triggered: bool, message: str).
    """

    @staticmethod
    def check_harga_spike(harga_sekarang: float, harga_3_hari_lalu: float,
                          komoditas: str = "", provinsi: str = "") -> tuple:
        """
        Cek apakah harga naik lebih dari threshold dalam 3 hari.
        Returns: (is_triggered, message)
        """
        if harga_3_hari_lalu <= 0:
            return False, ""

        pct_change = ((harga_sekarang - harga_3_hari_lalu) / harga_3_hari_lalu) * 100
        threshold = ALERT_THRESHOLDS["HARGA_SPIKE_PCT"]

        if pct_change > threshold:
            msg = (
                f"HARGA SPIKE: {komoditas} di {provinsi} naik {pct_change:.1f}% "
                f"dalam {ALERT_THRESHOLDS['HARGA_SPIKE_DAYS']} hari "
                f"(Rp {harga_3_hari_lalu:,.0f} → Rp {harga_sekarang:,.0f})"
            )
            return True, msg

        return False, ""

    @staticmethod
    def check_data_gap(jam_sejak_update: float) -> tuple:
        """
        Cek apakah data cuaca tidak masuk lebih dari threshold jam.
        Returns: (is_triggered, message)
        """
        threshold = ALERT_THRESHOLDS["DATA_GAP_HOURS"]

        if jam_sejak_update > threshold:
            msg = (
                f"DATA GAP: Data cuaca realtime tidak masuk selama "
                f"{jam_sejak_update:.1f} jam (threshold: {threshold} jam)"
            )
            return True, msg

        return False, ""

    @staticmethod
    def check_model_degradation(current_accuracy: float) -> tuple:
        """
        Cek apakah akurasi model di bawah threshold.
        Returns: (is_triggered, message)
        """
        threshold = ALERT_THRESHOLDS["MODEL_MIN_ACCURACY"]

        if current_accuracy < threshold:
            msg = (
                f"MODEL DEGRADATION: Akurasi model turun ke {current_accuracy:.2%} "
                f"(minimum: {threshold:.2%}). Perlu re-training."
            )
            return True, msg

        return False, ""

    @staticmethod
    def check_pipeline_failure(step_name: str, error_message: str) -> tuple:
        """
        Generate alert untuk pipeline failure.
        Returns: (is_triggered, message)
        """
        msg = (
            f"PIPELINE FAILURE: Step '{step_name}' gagal. "
            f"Error: {error_message}"
        )
        return True, msg

    @staticmethod
    def check_anomali_cuaca(suhu: float = None, curah_hujan: float = None) -> tuple:
        """
        Cek apakah data cuaca di luar range normal.
        Returns: (is_triggered, message)
        """
        alerts = []

        if suhu is not None:
            if suhu < ALERT_THRESHOLDS["ANOMALI_SUHU_MIN"]:
                alerts.append(f"Suhu terlalu rendah: {suhu}°C")
            elif suhu > ALERT_THRESHOLDS["ANOMALI_SUHU_MAX"]:
                alerts.append(f"Suhu terlalu tinggi: {suhu}°C")

        if curah_hujan is not None:
            if curah_hujan > ALERT_THRESHOLDS["ANOMALI_CURAH_HUJAN_MAX"]:
                alerts.append(f"Curah hujan ekstrem: {curah_hujan} mm")

        if alerts:
            msg = "ANOMALI CUACA: " + "; ".join(alerts)
            return True, msg

        return False, ""


# ============================================================
# USAGE EXAMPLE
# ============================================================

if __name__ == "__main__":
    print("=== Alert Rules Configuration ===")
    for key, value in ALERT_THRESHOLDS.items():
        print(f"  {key}: {value}")

    print("\n=== Testing Rules ===")

    # Test harga spike
    triggered, msg = AlertRules.check_harga_spike(15000, 12000, "Beras Medium", "DKI JAKARTA")
    print(f"Harga Spike: triggered={triggered}, msg={msg}")

    # Test data gap
    triggered, msg = AlertRules.check_data_gap(8.5)
    print(f"Data Gap: triggered={triggered}, msg={msg}")

    # Test model degradation
    triggered, msg = AlertRules.check_model_degradation(0.45)
    print(f"Model Degradation: triggered={triggered}, msg={msg}")
