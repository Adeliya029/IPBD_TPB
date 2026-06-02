import os
import json
import time
import requests
import pandas as pd

from datetime import datetime, timedelta

# =========================
# KONFIGURASI
# =========================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(BASE_DIR, "..", "..")
FILE_KOTA = os.path.join(PROJECT_ROOT, "streaming", "kab_kota_jawa.json")

print(f"BASE_DIR: {BASE_DIR}")
print(f"PROJECT_ROOT: {PROJECT_ROOT}")
print(f"FILE_KOTA: {FILE_KOTA}")
print(f"File exists: {os.path.exists(FILE_KOTA)}")

with open(FILE_KOTA, "r", encoding="utf-8") as f:
    DAFTAR_KOTA = json.load(f)

print(f"Loaded {len(DAFTAR_KOTA)} kota")

# Output folder
RAW_FOLDER = os.path.join(PROJECT_ROOT, "data", "raw", "cuaca")

# Periode
START_DATE = datetime(2026, 1, 1)
END_DATE = datetime(2026, 5, 31)

# Open-Meteo API (GRATIS, no API key)
# Archive API untuk historical data
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

# Rate limiting: Open-Meteo free = 10,000 calls/day
SLEEP_INTERVAL = 1.5


def ambil_cuaca_historical(kota, tanggal_dt):
    """
    Ambil data cuaca historical dari Open-Meteo Archive API.
    Format sama kayak contoh user: /v1/archive?latitude=...&longitude=...&daily=...
    """

    tanggal_str = tanggal_dt.strftime("%Y-%m-%d")

    # Format parameter sesuai contoh user (current=... untuk forecast, daily=... untuk archive)
    params = {
        "latitude": kota["latitude"],
        "longitude": kota["longitude"],
        "start_date": tanggal_str,
        "end_date": tanggal_str,
        "daily": "temperature_2m_max,temperature_2m_min,temperature_2m_mean,apparent_temperature_max,precipitation_sum,relative_humidity_2m_mean,wind_speed_10m_max,pressure_msl_mean,cloud_cover_mean",
        "timezone": "Asia/Jakarta"
    }

    try:
        response = requests.get(ARCHIVE_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        # Open-Meteo return: {"daily": {"time": ["2026-01-01"], "temperature_2m_max": [32.5], ...}}
        daily = data.get("daily", {})

        if not daily or not daily.get("time") or len(daily["time"]) == 0:
            print(f"  ⚠️  No data in response for {tanggal_str}")
            return None

        # Index 0 karena cuma 1 hari
        idx = 0

        return {
            "tanggal": tanggal_str,
            "provinsi": kota["provinsi"],
            "kab_kota": kota["kab_kota"],
            "latitude": kota["latitude"],
            "longitude": kota["longitude"],

            "suhu_max": daily.get("temperature_2m_max", [None])[idx],
            "suhu_min": daily.get("temperature_2m_min", [None])[idx],
            "suhu_mean": daily.get("temperature_2m_mean", [None])[idx],
            "suhu_feels_like_max": daily.get("apparent_temperature_max", [None])[idx],
            "curah_hujan_mm": daily.get("precipitation_sum", [None])[idx],
            "kelembapan": daily.get("relative_humidity_2m_mean", [None])[idx],
            "kecepatan_angin": daily.get("wind_speed_10m_max", [None])[idx],
            "tekanan_udara": daily.get("pressure_msl_mean", [None])[idx],
            "awan_persen": daily.get("cloud_cover_mean", [None])[idx],

            "waktu_ingest": datetime.now().isoformat(),
            "sumber": "Open-Meteo_Archive"
        }

    except requests.exceptions.HTTPError as e:
        print(f"  ❌ HTTP Error {response.status_code}: {e}")
        print(f"  URL: {response.url[:150]}...")
        return None
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return None


def scrape_batch_mingguan(minggu_ke):
    """Scrape 1 minggu data cuaca untuk semua kota."""
    hari_awal = (minggu_ke - 1) * 7
    tanggal_awal = START_DATE + timedelta(days=hari_awal)
    tanggal_akhir = min(tanggal_awal + timedelta(days=6), END_DATE)

    total_hari_minggu = (tanggal_akhir - tanggal_awal).days + 1
    total_calls = len(DAFTAR_KOTA) * total_hari_minggu

    print(f"\n{'='*70}")
    print(f"BATCH MINGGU {minggu_ke}: {tanggal_awal.strftime('%Y-%m-%d')} s/d {tanggal_akhir.strftime('%Y-%m-%d')}")
    print(f"{'='*70}")
    print(f"Total kota: {len(DAFTAR_KOTA)}")
    print(f"Total hari: {total_hari_minggu}")
    print(f"Total calls: {total_calls}")
    print(f"Estimasi waktu: ~{total_calls * SLEEP_INTERVAL / 60:.0f} menit")
    print(f"Progress: {minggu_ke}/22 minggu")

    hasil_semua = []
    total_request = 0
    total_sukses = 0
    total_gagal = 0

    for i, kota in enumerate(DAFTAR_KOTA, 1):
        print(f"\n[{i:03d}/{len(DAFTAR_KOTA)}] {kota['provinsi']} - {kota['kab_kota']}")

        tanggal = tanggal_awal
        while tanggal <= tanggal_akhir:
            total_request += 1

            data = ambil_cuaca_historical(kota, tanggal)

            if data:
                hasil_semua.append(data)
                total_sukses += 1
                suhu_mean = data.get('suhu_mean', 'N/A')
                curah = data.get('curah_hujan_mm', 'N/A')
                print(f"  ✅ {tanggal.strftime('%Y-%m-%d')} | suhu_mean: {suhu_mean}°C | hujan: {curah}mm")
            else:
                total_gagal += 1
                print(f"  ❌ {tanggal.strftime('%Y-%m-%d')} | GAGAL")

            time.sleep(SLEEP_INTERVAL)
            tanggal += timedelta(days=1)

    # Simpan hasil
    if hasil_semua:
        os.makedirs(RAW_FOLDER, exist_ok=True)

        df = pd.DataFrame(hasil_semua)

        output_file = os.path.join(
            RAW_FOLDER,
            f"cuaca_openmeteo_minggu_{minggu_ke:02d}_{tanggal_awal.strftime('%Y%m%d')}_{tanggal_akhir.strftime('%Y%m%d')}.csv"
        )

        df.to_csv(output_file, index=False, encoding="utf-8-sig")

        print(f"\n{'='*70}")
        print(f"BATCH MINGGU {minggu_ke} SELESAI")
        print(f"{'='*70}")
        print(f"Total request : {total_request}")
        print(f"Sukses        : {total_sukses}")
        print(f"Gagal         : {total_gagal}")
        print(f"File output   : {output_file}")
        print(f"Record        : {len(df)}")

        return output_file
    else:
        print(f"\n❌ Tidak ada data yang berhasil")
        return None


def main():
    print("="*70)
    print("OPEN-METEO HISTORICAL BATCH SCRAPER")
    print("="*70)
    print(f"Periode: {START_DATE.strftime('%Y-%m-%d')} s/d {END_DATE.strftime('%Y-%m-%d')}")
    print(f"Total kota: {len(DAFTAR_KOTA)}")
    print(f"Total hari: {(END_DATE - START_DATE).days + 1}")
    print(f"Total minggu: {((END_DATE - START_DATE).days // 7) + 1}")
    print(f"Output: {RAW_FOLDER}")
    print("="*70)

    total_hari = (END_DATE - START_DATE).days + 1
    total_minggu = (total_hari // 7) + (1 if total_hari % 7 > 0 else 0)

    print(f"\n📊 PERHITUNGAN:")
    print(f"   Total calls needed: {len(DAFTAR_KOTA) * total_hari:,}")
    print(f"   Calls per minggu: ~{len(DAFTAR_KOTA) * 7:,}")
    print(f"   Estimasi selesai: {total_minggu} hari (1 minggu/hari)")

    print(f"\nPilih mode:")
    print(f"1. Scrape SEMUA minggu (1-{total_minggu})")
    print(f"2. Scrape minggu tertentu")
    print(f"3. Scrape range minggu (misal: 1-5)")
    print(f"4. Resume dari minggu terakhir yang tersimpan")

    mode = input("\nPilih (1/2/3/4) [default=1]: ").strip() or "1"

    minggu_list = []

    if mode == "1":
        minggu_list = list(range(1, total_minggu + 1))
    elif mode == "2":
        minggu_input = input(f"Masukkan nomor minggu (1-{total_minggu}): ").strip()
        minggu_list = [int(minggu_input)]
    elif mode == "3":
        range_input = input(f"Masukkan range (misal: 1-5): ").strip()
        awal, akhir = map(int, range_input.split("-"))
        minggu_list = list(range(awal, akhir + 1))
    elif mode == "4":
        existing_files = [f for f in os.listdir(RAW_FOLDER) if f.startswith("cuaca_openmeteo_minggu_")]
        if existing_files:
            existing_minggu = sorted([int(f.split("_")[3]) for f in existing_files])
            last_minggu = existing_minggu[-1]
            print(f"   Resume dari minggu {last_minggu + 1}")
            minggu_list = list(range(last_minggu + 1, total_minggu + 1))
        else:
            print("   Tidak ada file existing, mulai dari minggu 1")
            minggu_list = list(range(1, total_minggu + 1))

    print(f"\nMulai scrape {len(minggu_list)} minggu...")

    files_output = []
    for minggu in minggu_list:
        file_path = scrape_batch_mingguan(minggu)
        if file_path:
            files_output.append(file_path)

        if minggu != minggu_list[-1]:
            print(f"\n⏳ Minggu {minggu} selesai. Tekan Enter untuk lanjut ke minggu {minggu + 1}...")
            print(f"   (Atau Ctrl+C untuk pause dan lanjutkan besok)")
            try:
                input()
            except KeyboardInterrupt:
                print(f"\n\n⏸️  PAUSED. Resume nanti dengan mode 4.")
                print(f"   Sudah selesai: {len(files_output)} minggu")
                break

    print(f"\n{'='*70}")
    print("SEMUA BATCH SELESAI")
    print(f"{'='*70}")
    print(f"Total file: {len(files_output)}")
    for f in files_output:
        print(f"  - {f}")


if __name__ == "__main__":
    main()