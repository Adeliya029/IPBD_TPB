import os
import sys

# Fix: tambah path ke folder batch/ (tempat storage/ berada)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BATCH_DIR = os.path.join(BASE_DIR, "..")  # naik 1 level ke batch/
if BATCH_DIR not in sys.path:
    sys.path.insert(0, BATCH_DIR)

# Sekarang import bisa jalan
from storage.upload_minio import storage

# =========================
# PATH CONFIG
# =========================

RAW_BUCKET = "raw-zone"
FOLDER = os.path.join(BASE_DIR, "..", "..", "data", "raw", "harga")


def main():
    files = [f for f in os.listdir(FOLDER) if f.endswith(".csv")]

    if not files:
        print("❌ Tidak ada file harga di raw folder")
        return

    print(f"📁 Upload {len(files)} file harga ke MinIO...")

    for file in files:
        path = os.path.join(FOLDER, file)

        storage.upload_file(
            RAW_BUCKET,
            f"harga/{file}",
            path
        )

        print(f"✅ Uploaded: {file} -> {RAW_BUCKET}/harga/{file}")


if __name__ == "__main__":
    main()