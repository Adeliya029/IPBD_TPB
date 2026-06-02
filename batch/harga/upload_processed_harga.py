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

PROCESSED_BUCKET = "processed-zone"
FOLDER = os.path.join(BASE_DIR, "..", "..", "data", "processed", "harga")


def main():
    files = [f for f in os.listdir(FOLDER) if f.endswith(".csv")]

    if not files:
        print("❌ Tidak ada file harga di processed folder")
        return

    print(f"📁 Upload {len(files)} file harga processed ke MinIO...")

    for file in files:
        path = os.path.join(FOLDER, file)

        storage.upload_file(
            PROCESSED_BUCKET,
            f"harga/{file}",
            path
        )

        print(f"✅ Uploaded: {file} -> {PROCESSED_BUCKET}/harga/{file}")


if __name__ == "__main__":
    main()