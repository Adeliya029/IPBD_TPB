import os
from minio import Minio
from dotenv import load_dotenv

# Load .env dari project root (naik 3 level dari storage/)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # → batch/harga/storage/
PROJECT_ROOT = os.path.join(BASE_DIR, "..", "..", "..")  # → project root
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")

if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH)
else:
    load_dotenv()  # fallback

# Tambah validasi env var:
class MinioStorage:
    def __init__(self):
        endpoint = os.getenv("MINIO_ENDPOINT")
        access_key = os.getenv("MINIO_ACCESS_KEY")
        secret_key = os.getenv("MINIO_SECRET_KEY")
        
        if not all([endpoint, access_key, secret_key]):
            raise ValueError(
                "MinIO credentials tidak lengkap!\n"
                "Pastikan .env ada MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY"
            )
        
        self.client = Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=os.getenv("MINIO_SECURE", "False").lower() == "true"
        )

class MinioStorage:

    def __init__(self):

        self.client = Minio(

            endpoint=os.getenv("MINIO_ENDPOINT"),

            access_key=os.getenv(
                "MINIO_ACCESS_KEY"
            ),

            secret_key=os.getenv(
                "MINIO_SECRET_KEY"
            ),

            secure=os.getenv(
                "MINIO_SECURE",
                "False"
            ).lower() == "true"

        )

    # =====================================
    # CEK BUCKET
    # =====================================

    def buat_bucket(self, nama_bucket):

        if not self.client.bucket_exists(
            nama_bucket
        ):

            self.client.make_bucket(
                nama_bucket
            )

            print(
                f"Bucket dibuat : {nama_bucket}"
            )

    # =====================================
    # UPLOAD FILE
    # =====================================

    def upload_file(

        self,
        bucket,
        object_name,
        file_path

    ):

        self.buat_bucket(bucket)

        self.client.fput_object(

            bucket,
            object_name,
            file_path

        )

        print(
            f"Upload berhasil : {object_name}"
        )

    # =====================================
    # DOWNLOAD FILE
    # =====================================

    def download_file(

        self,
        bucket,
        object_name,
        destination

    ):

        self.client.fget_object(

            bucket,
            object_name,
            destination

        )

        print(
            f"Download berhasil : {object_name}"
        )

    # =====================================
    # LIST FILE
    # =====================================

    def list_file(

        self,
        bucket,
        prefix=None

    ):

        return [

            obj.object_name

            for obj in self.client.list_objects(
                bucket,
                prefix=prefix,
                recursive=True
            )

        ]


storage = MinioStorage()