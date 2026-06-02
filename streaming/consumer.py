import json
import os

import psycopg

from kafka import KafkaConsumer
from dotenv import load_dotenv

load_dotenv()

# =====================================
# KAFKA
# =====================================

consumer = KafkaConsumer(

    os.getenv(
        "TOPIC_CUACA",
        "cuaca-stream"
    ),

    bootstrap_servers=os.getenv(
        "KAFKA_BOOTSTRAP",
        "localhost:9092"
    ),

    auto_offset_reset="earliest",

    group_id="grup-cuaca",

    value_deserializer=lambda x:
    json.loads(
        x.decode("utf-8")
    )

)

# =====================================
# POSTGRES
# =====================================

conn = psycopg.connect(

    host=os.getenv(
        "POSTGRES_HOST"
    ),

    port=os.getenv(
        "POSTGRES_PORT"
    ),

    dbname=os.getenv(
        "POSTGRES_DB"
    ),

    user=os.getenv(
        "POSTGRES_USER"
    ),

    password=os.getenv(
        "POSTGRES_PASSWORD"
    )

)

cur = conn.cursor()

print(
    "Consumer aktif..."
)

counter = 0

# =====================================
# CONSUME
# =====================================

for message in consumer:

    data = message.value

    try:

        cur.execute(

            """
            INSERT INTO cuaca_realtime (

                waktu,
                provinsi,
                kab_kota,
                suhu,
                kelembapan,
                curah_hujan,
                kecepatan_angin,
                tekanan_udara,
                kondisi_cuaca,
                deskripsi_cuaca,
                sumber

            )

            VALUES (

                %s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s,%s

            )
            """,

            (

                data["waktu"],
                data["provinsi"],
                data["kab_kota"],
                data["suhu"],
                data["kelembapan"],
                data["curah_hujan"],
                data["kecepatan_angin"],
                data["tekanan_udara"],
                data["kondisi_cuaca"],
                data["deskripsi_cuaca"],
                data["sumber"]

            )

        )

        conn.commit()

        counter += 1

        print(

            f"[{counter:05d}] "

            f"{data['kab_kota']} | "

            f"{data['suhu']}°C | "

            f"BERHASIL"

        )

    except Exception as e:

        conn.rollback()

        print(

            f"GAGAL | "

            f"{data['kab_kota']} | "

            f"{e}"

        )