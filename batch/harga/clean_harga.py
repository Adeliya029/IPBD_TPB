import os
import shutil
import numpy as np
import pandas as pd

# =========================
# PATH CONFIG
# =========================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_FOLDER = os.path.join(BASE_DIR, "..", "..", "data", "raw", "harga")
PROCESSED_FOLDER = os.path.join(BASE_DIR, "..", "..", "data", "processed", "harga")
BACKUP_FOLDER = os.path.join(BASE_DIR, "..", "..", "data", "backup", "harga")


def bersihkan_data(df):

    print(f"\nRecord awal : {len(df)}")
    print("Kolom:", df.columns.tolist())

    # =========================
    # NORMALISASI KOLOM WAJIB
    # =========================

    if "kode_provinsi" not in df.columns:
        raise ValueError("Dataset tidak punya kolom kode_provinsi")

    # rename biar konsisten
    df = df.rename(columns={
        "kode_provinsi": "provinsi_id"
    })

    # =========================
    # TYPE CONVERSION
    # =========================

    df["tanggal"] = pd.to_datetime(df["tanggal"], errors="coerce")

    df["harga"] = pd.to_numeric(df["harga"], errors="coerce")
    df["harga_pembanding"] = pd.to_numeric(df["harga_pembanding"], errors="coerce")

    # =========================
    # STEP 1: HARGA = 0 -> NaN
    # =========================

    harga_0_count = (df["harga"] == 0).sum()
    df["harga"] = df["harga"].replace(0, np.nan)
    print(f"harga=0 diubah ke NaN : {harga_0_count}")

    # =========================
    # STEP 2: NaN -> isi dari harga_pembanding (kalau > 0)
    # =========================

    # harga_pembanding yang 0 juga dianggap NaN
    df["harga_pembanding"] = df["harga_pembanding"].replace(0, np.nan)

    # Isi harga NaN dari harga_pembanding
    filled_from_pembanding = df["harga"].isna() & df["harga_pembanding"].notna()
    df.loc[filled_from_pembanding, "harga"] = df.loc[filled_from_pembanding, "harga_pembanding"]
    print(f"NaN diisi dari harga_pembanding : {filled_from_pembanding.sum()}")

    # =========================
    # STEP 3: SORT (penting untuk forward fill)
    # =========================

    df = df.sort_values(
        ["provinsi_id", "kode_kab_kota", "komoditas", "tanggal"]
    )

    # =========================
    # STEP 4: FORWARD FILL (per grup provinsi+kab_kota+komoditas)
    # =========================

    # Hitung sebelum ffill
    before_ffill = df["harga"].isna().sum()

    df["harga"] = df.groupby(
        ["provinsi_id", "kode_kab_kota", "komoditas"]
    )["harga"].ffill()

    after_ffill = df["harga"].isna().sum()
    print(f"NaN diisi forward fill : {before_ffill - after_ffill}")

    # =========================
    # STEP 5: BACKWARD FILL (sisa yang masih NaN)
    # =========================

    before_bfill = df["harga"].isna().sum()

    df["harga"] = df.groupby(
        ["provinsi_id", "kode_kab_kota", "komoditas"]
    )["harga"].bfill()

    after_bfill = df["harga"].isna().sum()
    print(f"NaN diisi backward fill : {before_bfill - after_bfill}")

    # =========================
    # STEP 6: CLEAN INVALID (masih NaN setelah semua fill)
    # =========================

    before = len(df)
    df = df.dropna(subset=["harga", "tanggal"])
    dropped = before - len(df)
    print(f"Missing dibuang (tidak bisa diisi) : {dropped}")
    if dropped > 0:
        print("   ⚠️  Ada data yang harganya NaN di semua tanggal dalam grup tersebut!")

    # =========================
    # STEP 7: DROP DUPLICATE
    # =========================

    before = len(df)
    df = df.drop_duplicates(
        subset=["tanggal", "komoditas", "provinsi_id", "kode_kab_kota"]
    )

    print(f"Duplicate dibuang : {before - len(df)}")

    print(f"Record akhir : {len(df)}")

    # Drop kolom harga_pembanding karena sudah tidak perlu
    df = df.drop(columns=["harga_pembanding"], errors="ignore")

    return df


def simpan_hasil(df, nama_file):

    os.makedirs(PROCESSED_FOLDER, exist_ok=True)

    output_path = os.path.join(PROCESSED_FOLDER, nama_file)

    df.to_csv(output_path, index=False, encoding="utf-8-sig")

    print(f"Saved → {output_path}")


def main():

    files = [f for f in os.listdir(RAW_FOLDER) if f.endswith(".csv")]

    if not files:
        print("Tidak ada file raw ditemukan")
        return

    # =========================
    # BACKUP SEBELUM PROCESSING
    # =========================
    os.makedirs(BACKUP_FOLDER, exist_ok=True)
    print(f"\n📁 Backup folder: {BACKUP_FOLDER}")

    for file in files:
        src = os.path.join(RAW_FOLDER, file)
        dst = os.path.join(BACKUP_FOLDER, file)
        shutil.copy2(src, dst)
        print(f"✅ Backup: {file}")

    # =========================
    # PROCESSING
    # =========================
    for file in files:

        print("\n" + "=" * 60)
        print(f"Processing : {file}")

        path = os.path.join(RAW_FOLDER, file)
        df = pd.read_csv(path)

        df_clean = bersihkan_data(df)

        simpan_hasil(df_clean, file)

    print("\nDONE: Cleaning selesai semua file")


if __name__ == "__main__":
    main()