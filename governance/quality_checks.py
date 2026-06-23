"""
Data Quality Checks — Validasi kualitas data cuaca dan harga pangan.
Menggunakan pandas untuk pengecekan manual (tanpa Great Expectations).

Checks untuk data cuaca:
- suhu_mean: tidak null, range -10 s/d 50
- curah_hujan_mm: tidak null, >= 0
- kelembapan: range 0-100
- tidak ada duplikat berdasarkan (tanggal, kab_kota)

Checks untuk data harga:
- harga: tidak null, > 0, < 1.000.000
- komoditas: tidak null, ada dalam daftar komoditas valid
- tidak ada duplikat berdasarkan (tanggal, kab_kota, komoditas)

Output: laporan quality check ke logs/data/quality_report.json
"""

import os
import sys
import json
import pandas as pd
from datetime import datetime

# Tambahkan project root ke sys.path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from logs.monitoring import StructuredLogger

# Logger
logger = StructuredLogger('DataQualityChecker')

# Path konfigurasi
PROJECT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
REPORT_DIR = os.path.join(PROJECT_ROOT, 'logs', 'data')
REPORT_PATH = os.path.join(REPORT_DIR, 'quality_report.json')

# Daftar komoditas valid (digunakan untuk validasi data harga)
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


class DataQualityChecker:
    """
    Melakukan data quality checks pada data cuaca dan harga pangan.
    Menghasilkan laporan JSON yang bisa dilihat di dashboard.
    """

    def __init__(self):
        self.report = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'PASS',
            'checks': []
        }

    # ============================================================
    # CHECK CUACA
    # ============================================================

    def check_cuaca(self, df: pd.DataFrame, source_name: str = "cuaca") -> dict:
        """
        Jalankan semua quality checks untuk data cuaca.

        Args:
            df: DataFrame data cuaca dengan kolom:
                tanggal, provinsi, kab_kota, suhu_mean, curah_hujan_mm,
                kelembapan, kecepatan_angin, tekanan_udara, awan_persen
            source_name: Nama sumber data untuk identifikasi di laporan

        Returns:
            dict: Ringkasan hasil check
        """
        logger.info(f"Memulai quality check cuaca: {source_name} ({len(df)} baris)")
        results = {
            'source': source_name,
            'total_rows': len(df),
            'checks': [],
            'status': 'PASS'
        }

        # Check 1: suhu_mean tidak null dan range -10 s/d 50
        if 'suhu_mean' in df.columns:
            null_count = int(df['suhu_mean'].isna().sum())
            out_of_range = int(((df['suhu_mean'] < -10) | (df['suhu_mean'] > 50)).sum())
            passed = null_count == 0 and out_of_range == 0

            check_result = {
                'nama': 'suhu_mean_valid',
                'deskripsi': 'suhu_mean tidak null, range -10 s/d 50°C',
                'status': 'PASS' if passed else 'FAIL',
                'null_count': null_count,
                'out_of_range_count': out_of_range,
                'total_checked': len(df)
            }
            results['checks'].append(check_result)

            if not passed:
                results['status'] = 'FAIL'
                logger.warning(
                    f"FAIL: suhu_mean — {null_count} null, {out_of_range} out of range",
                    source=source_name
                )

        # Check 2: curah_hujan_mm tidak null dan >= 0
        if 'curah_hujan_mm' in df.columns:
            null_count = int(df['curah_hujan_mm'].isna().sum())
            negative_count = int((df['curah_hujan_mm'] < 0).sum())
            passed = null_count == 0 and negative_count == 0

            check_result = {
                'nama': 'curah_hujan_valid',
                'deskripsi': 'curah_hujan_mm tidak null, >= 0',
                'status': 'PASS' if passed else 'FAIL',
                'null_count': null_count,
                'negative_count': negative_count,
                'total_checked': len(df)
            }
            results['checks'].append(check_result)

            if not passed:
                results['status'] = 'FAIL'
                logger.warning(
                    f"FAIL: curah_hujan_mm — {null_count} null, {negative_count} negatif",
                    source=source_name
                )

        # Check 3: kelembapan range 0-100
        if 'kelembapan' in df.columns:
            null_count = int(df['kelembapan'].isna().sum())
            out_of_range = int(((df['kelembapan'] < 0) | (df['kelembapan'] > 100)).sum())
            passed = null_count == 0 and out_of_range == 0

            check_result = {
                'nama': 'kelembapan_valid',
                'deskripsi': 'kelembapan range 0-100%',
                'status': 'PASS' if passed else 'FAIL',
                'null_count': null_count,
                'out_of_range_count': out_of_range,
                'total_checked': len(df)
            }
            results['checks'].append(check_result)

            if not passed:
                results['status'] = 'FAIL'

        # Check 4: tidak ada duplikat berdasarkan (tanggal, kab_kota)
        if 'tanggal' in df.columns and 'kab_kota' in df.columns:
            dup_count = int(df.duplicated(subset=['tanggal', 'kab_kota']).sum())
            passed = dup_count == 0

            check_result = {
                'nama': 'no_duplicates_cuaca',
                'deskripsi': 'Tidak ada duplikat (tanggal, kab_kota)',
                'status': 'PASS' if passed else 'FAIL',
                'duplicate_count': dup_count,
                'total_checked': len(df)
            }
            results['checks'].append(check_result)

            if not passed:
                results['status'] = 'FAIL'
                logger.warning(
                    f"FAIL: {dup_count} baris duplikat ditemukan",
                    source=source_name
                )

        # Check 5: kecepatan_angin >= 0
        if 'kecepatan_angin' in df.columns:
            negative_count = int((df['kecepatan_angin'] < 0).sum())
            passed = negative_count == 0

            check_result = {
                'nama': 'kecepatan_angin_valid',
                'deskripsi': 'kecepatan_angin >= 0',
                'status': 'PASS' if passed else 'FAIL',
                'negative_count': negative_count,
                'total_checked': len(df)
            }
            results['checks'].append(check_result)

            if not passed:
                results['status'] = 'FAIL'

        # Simpan ke report
        self.report['checks'].append(results)
        if results['status'] == 'FAIL':
            self.report['overall_status'] = 'FAIL'

        logger.info(
            f"Quality check cuaca selesai: {results['status']}",
            source=source_name,
            total_checks=len(results['checks'])
        )

        return results

    # ============================================================
    # CHECK HARGA
    # ============================================================

    def check_harga(self, df: pd.DataFrame, source_name: str = "harga") -> dict:
        """
        Jalankan semua quality checks untuk data harga pangan.

        Args:
            df: DataFrame data harga dengan kolom:
                tanggal, kab_kota, komoditas, harga, satuan
            source_name: Nama sumber data

        Returns:
            dict: Ringkasan hasil check
        """
        logger.info(f"Memulai quality check harga: {source_name} ({len(df)} baris)")
        results = {
            'source': source_name,
            'total_rows': len(df),
            'checks': [],
            'status': 'PASS'
        }

        # Check 1: harga tidak null, > 0, < 1.000.000
        if 'harga' in df.columns:
            null_count = int(df['harga'].isna().sum())
            zero_or_neg = int((df['harga'] <= 0).sum())
            too_high = int((df['harga'] > 1_000_000).sum())
            passed = null_count == 0 and zero_or_neg == 0 and too_high == 0

            check_result = {
                'nama': 'harga_valid',
                'deskripsi': 'harga tidak null, > 0, < 1.000.000',
                'status': 'PASS' if passed else 'FAIL',
                'null_count': null_count,
                'zero_or_negative': zero_or_neg,
                'above_max': too_high,
                'total_checked': len(df)
            }
            results['checks'].append(check_result)

            if not passed:
                results['status'] = 'FAIL'
                logger.warning(
                    f"FAIL: harga — {null_count} null, {zero_or_neg} <=0, {too_high} >1jt",
                    source=source_name
                )

        # Check 2: komoditas tidak null
        if 'komoditas' in df.columns:
            null_count = int(df['komoditas'].isna().sum())
            empty_count = int((df['komoditas'].str.strip() == '').sum())

            # Cek apakah komoditas ada dalam daftar valid
            invalid_komoditas = df[~df['komoditas'].isin(KOMODITAS_VALID)]['komoditas'].unique()
            invalid_count = len(invalid_komoditas)

            passed = null_count == 0 and empty_count == 0

            check_result = {
                'nama': 'komoditas_valid',
                'deskripsi': 'komoditas tidak null dan tidak kosong',
                'status': 'PASS' if passed else 'FAIL',
                'null_count': null_count,
                'empty_count': empty_count,
                'komoditas_tidak_dikenal': invalid_count,
                'daftar_tidak_dikenal': list(invalid_komoditas)[:10],
                'total_checked': len(df)
            }
            results['checks'].append(check_result)

            if not passed:
                results['status'] = 'FAIL'

        # Check 3: tidak ada duplikat berdasarkan (tanggal, kab_kota, komoditas)
        dup_cols = []
        if 'tanggal' in df.columns:
            dup_cols.append('tanggal')
        if 'kab_kota' in df.columns:
            dup_cols.append('kab_kota')
        if 'komoditas' in df.columns:
            dup_cols.append('komoditas')

        if len(dup_cols) == 3:
            dup_count = int(df.duplicated(subset=dup_cols).sum())
            passed = dup_count == 0

            check_result = {
                'nama': 'no_duplicates_harga',
                'deskripsi': 'Tidak ada duplikat (tanggal, kab_kota, komoditas)',
                'status': 'PASS' if passed else 'FAIL',
                'duplicate_count': dup_count,
                'total_checked': len(df)
            }
            results['checks'].append(check_result)

            if not passed:
                results['status'] = 'FAIL'
                logger.warning(
                    f"FAIL: {dup_count} duplikat ditemukan di data harga",
                    source=source_name
                )

        # Check 4: tanggal tidak null dan valid
        if 'tanggal' in df.columns:
            df_temp = df.copy()
            df_temp['tanggal_parsed'] = pd.to_datetime(df_temp['tanggal'], errors='coerce')
            null_count = int(df_temp['tanggal_parsed'].isna().sum())
            passed = null_count == 0

            check_result = {
                'nama': 'tanggal_valid',
                'deskripsi': 'tanggal tidak null dan format valid',
                'status': 'PASS' if passed else 'FAIL',
                'invalid_count': null_count,
                'total_checked': len(df)
            }
            results['checks'].append(check_result)

            if not passed:
                results['status'] = 'FAIL'

        # Simpan ke report
        self.report['checks'].append(results)
        if results['status'] == 'FAIL':
            self.report['overall_status'] = 'FAIL'

        logger.info(
            f"Quality check harga selesai: {results['status']}",
            source=source_name,
            total_checks=len(results['checks'])
        )

        return results

    # ============================================================
    # SIMPAN REPORT
    # ============================================================

    def save_report(self, output_path: str = None):
        """
        Simpan laporan quality check ke file JSON.

        Args:
            output_path: Path file output. Default: logs/data/quality_report.json
        """
        path = output_path or REPORT_PATH
        os.makedirs(os.path.dirname(path), exist_ok=True)

        # Hitung statistik keseluruhan
        total_checks = sum(len(r['checks']) for r in self.report['checks'])
        passed_checks = sum(
            1 for r in self.report['checks']
            for c in r['checks'] if c['status'] == 'PASS'
        )
        failed_checks = total_checks - passed_checks

        self.report['summary'] = {
            'total_checks': total_checks,
            'passed': passed_checks,
            'failed': failed_checks,
            'pass_rate': f"{(passed_checks/total_checks*100):.1f}%" if total_checks > 0 else "N/A"
        }

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.report, f, indent=2, ensure_ascii=False, default=str)

        logger.info(
            f"Quality report disimpan ke {path}",
            total_checks=total_checks,
            passed=passed_checks,
            failed=failed_checks
        )

        return path

    # ============================================================
    # GET REPORT
    # ============================================================

    def get_report(self) -> dict:
        """Kembalikan laporan quality check saat ini."""
        return self.report

    # ============================================================
    # LOAD REPORT
    # ============================================================

    @staticmethod
    def load_report(report_path: str = None) -> dict:
        """
        Load laporan quality check dari file JSON.

        Args:
            report_path: Path ke file report. Default: logs/data/quality_report.json
        """
        path = report_path or REPORT_PATH

        if not os.path.exists(path):
            return {'error': f'Report tidak ditemukan: {path}'}

        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)


# ============================================================
# FUNGSI HELPER: Jalankan semua checks dari CSV yang ada
# ============================================================

def run_all_quality_checks():
    """
    Jalankan quality checks pada semua file CSV yang ada
    di folder data/processed/. Simpan laporan ke quality_report.json.
    """
    checker = DataQualityChecker()

    # Path ke data processed
    cuaca_dir = os.path.join(PROJECT_ROOT, 'data', 'processed', 'cuaca')
    harga_dir = os.path.join(PROJECT_ROOT, 'data', 'processed', 'harga')

    # Check semua file cuaca
    if os.path.exists(cuaca_dir):
        for f in os.listdir(cuaca_dir):
            if f.endswith('.csv'):
                path = os.path.join(cuaca_dir, f)
                try:
                    df = pd.read_csv(path)
                    checker.check_cuaca(df, source_name=f)
                except Exception as e:
                    logger.error(f"Gagal check cuaca {f}: {str(e)}")
    else:
        logger.warning(f"Folder cuaca tidak ditemukan: {cuaca_dir}")

    # Check semua file harga
    if os.path.exists(harga_dir):
        for f in os.listdir(harga_dir):
            if f.endswith('.csv'):
                path = os.path.join(harga_dir, f)
                try:
                    df = pd.read_csv(path)
                    checker.check_harga(df, source_name=f)
                except Exception as e:
                    logger.error(f"Gagal check harga {f}: {str(e)}")
    else:
        logger.warning(f"Folder harga tidak ditemukan: {harga_dir}")

    # Simpan laporan
    report_path = checker.save_report()
    print(f"\n✅ Quality report disimpan ke: {report_path}")

    return checker.get_report()


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    report = run_all_quality_checks()

    print("\n" + "=" * 60)
    print("DATA QUALITY REPORT")
    print("=" * 60)
    print(f"Status: {report.get('overall_status', 'UNKNOWN')}")

    if 'summary' in report:
        s = report['summary']
        print(f"Total Checks: {s['total_checks']}")
        print(f"Passed: {s['passed']}")
        print(f"Failed: {s['failed']}")
        print(f"Pass Rate: {s['pass_rate']}")
