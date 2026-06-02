import os
import sys

# Fix: tambah path ke folder batch/ (tempat storage/ berada)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BATCH_DIR = os.path.join(BASE_DIR, "..")
if BATCH_DIR not in sys.path:
    sys.path.insert(0, BATCH_DIR)

from storage.upload_minio import storage

# =========================
# PATH CONFIG
# =========================

PROCESSED_BUCKET = "processed-zone"
FOLDER = os.path.join(BASE_DIR, "..", "..", "data", "processed", "cuaca")


def main():
    files = [f for f in os.listdir(FOLDER) if f.endswith(".csv")]

    if not files:
        print("❌ Tidak ada file cuaca di processed folder")
        return

    print(f"📁 Upload {len(files)} file cuaca processed ke MinIO...")

    for file in files:
        path = os.path.join(FOLDER, file)

        storage.upload_file(
            PROCESSED_BUCKET,
            f"cuaca/{file}",
            path
        )

        print(f"✅ Uploaded: {file} -> {PROCESSED_BUCKET}/cuaca/{file}")


if __name__ == "__main__":
    main()