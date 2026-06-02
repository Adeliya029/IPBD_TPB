import os
import shutil
import numpy as np
import pandas as pd

# =========================
# PATH CONFIG
# =========================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_FOLDER = os.path.join(BASE_DIR, "..", "..", "data", "raw", "cuaca")
PROCESSED_FOLDER = os.path.join(BASE_DIR, "..", "..", "data", "processed", "cuaca")
BACKUP_FOLDER = os.path.join(BASE_DIR, "..", "..", "data", "backup", "cuaca")


def bersihkan_data_cuaca(df):
    """
    Cleaning data cuaca historical dari Open-Meteo.
    - Type conversion
    - Pastikan provinsi & kab_kota uppercase
    - Sort by kab_kota + tanggal
    - Tidak perlu handle missing (Open-Meteo data sudah lengkap)
    """

    print(f"\nRecord awal : {len(df)}")
    print("Kolom:", df.columns.tolist())

    # =========================
    # TYPE CONVERSION
    # =========================
    df["tanggal"] = pd.to_datetime(df["tanggal"], errors="coerce")

    # Convert semua numeric
    numeric_cols = [
        "latitude", "longitude",
        "suhu_max", "suhu_min", "suhu_mean", "suhu_feels_like_max",
        "curah_hujan_mm", "kelembapan", "kecepatan_angin",
        "tekanan_udara", "awan_persen"
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # =========================
    # UPPERCASE PROVINSI & KAB_KOTA
    # =========================
    if "provinsi" in df.columns:
        df["provinsi"] = df["provinsi"].str.upper().str.strip()

    if "kab_kota" in df.columns:
        df["kab_kota"] = df["kab_kota"].str.upper().str.strip()

    # =========================
    # SORT
    # =========================
    df = df.sort_values(["provinsi", "kab_kota", "tanggal"])

    # =========================
    # DROP DUPLICATE (kalau ada)
    # =========================
    before = len(df)
    df = df.drop_duplicates(subset=["tanggal", "kab_kota"])
    print(f"Duplicate dibuang : {before - len(df)}")

    print(f"Record akhir : {len(df)}")

    return df


def simpan_hasil(df, nama_file):
    os.makedirs(PROCESSED_FOLDER, exist_ok=True)
    output_path = os.path.join(PROCESSED_FOLDER, nama_file)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"Saved → {output_path}")


def main():
    files = [f for f in os.listdir(RAW_FOLDER) if f.endswith(".csv")]

    if not files:
        print("Tidak ada file cuaca raw ditemukan")
        return

    # BACKUP
    os.makedirs(BACKUP_FOLDER, exist_ok=True)
    print(f"\n📁 Backup folder: {BACKUP_FOLDER}")
    for file in files:
        src = os.path.join(RAW_FOLDER, file)
        dst = os.path.join(BACKUP_FOLDER, file)
        shutil.copy2(src, dst)
        print(f"✅ Backup: {file}")

    # PROCESSING
    for file in files:
        print("\n" + "=" * 60)
        print(f"Processing : {file}")

        path = os.path.join(RAW_FOLDER, file)
        df = pd.read_csv(path)

        df_clean = bersihkan_data_cuaca(df)
        simpan_hasil(df_clean, file)

    print("\nDONE: Cleaning cuaca selesai semua file")


if __name__ == "__main__":
    main()