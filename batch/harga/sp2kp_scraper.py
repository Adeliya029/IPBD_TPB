import os
import time
import requests
import pandas as pd

from datetime import datetime, timedelta

from kab_kota import ambil_semua_wilayah


URL = (
    "https://api-sp2kp.kemendag.go.id/"
    "report/api/average-price/"
    "generate-perbandingan-harga"
)


# =========================
# PATH CONFIG (FIXED)
# =========================

# Base path relatif dari lokasi script ini
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(BASE_DIR, "..", "..")
FILE_KOTA = os.path.join(PROJECT_ROOT, "streaming", "kab_kota_jawa.json")

# Output ke data/raw/harga (relative dari project root)
RAW_FOLDER = os.path.join(BASE_DIR, "..", "..", "data", "raw", "harga")


def ambil_harga(
    tanggal,
    tanggal_pembanding,
    kode_provinsi,
    kode_kab_kota
):

    payload = {
        "tanggal": tanggal,
        "tanggal_pembanding": tanggal_pembanding,
        "kode_provinsi": kode_provinsi,
        "kode_kab_kota": kode_kab_kota
    }

    try:

        response = requests.post(
            URL,
            data=payload,
            timeout=30
        )

        response.raise_for_status()

        return response.json()

    except Exception as e:

        print(
            f"Gagal {kode_kab_kota} : {e}"
        )

        return None


def scrape_tanggal(
    tanggal,
    wilayah_list
):

    hasil = []

    tanggal_pembanding = (
        datetime.strptime(
            tanggal,
            "%Y-%m-%d"
        )
        - timedelta(days=3)
    ).strftime("%Y-%m-%d")

    print(
        f"\nTanggal : {tanggal}"
    )

    for wilayah in wilayah_list:

        data = ambil_harga(
            tanggal,
            tanggal_pembanding,
            wilayah["kode_provinsi"],
            wilayah["kode_kab_kota"]
        )

        if not data:
            continue

        items = data.get(
            "data",
            []
        )

        for item in items:

            hasil.append({

                "tanggal":
                    tanggal,

                "kode_provinsi":
                    wilayah["kode_provinsi"],

                "kode_kab_kota":
                    wilayah["kode_kab_kota"],

                "kab_kota":
                    wilayah["nama_kab_kota"],

                "variant_id":
                    item["variant_id"],

                "komoditas":
                    item["variant_nama"],

                "satuan":
                    item["satuan_display"],

                "harga":
                    item["harga"],

                "harga_pembanding":
                    item["harga_pembanding"],

                "delta_harga":
                    item["delta_harga"],

                "persen_perubahan":
                    item["persen_perubahan"],

                "status_perubahan":
                    item["status_perubahan"],

                "waktu_ingest":
                    datetime.now().isoformat()

            })

        print(
            f"OK {wilayah['kode_kab_kota']} "
            f"{wilayah['nama_kab_kota']}"
        )

        time.sleep(0.2)

    return hasil


def scrape_periode():

    wilayah = ambil_semua_wilayah()

    print(
        f"Total wilayah: {len(wilayah)}"
    )

    seluruh_data = []

    start = datetime(
        2026,
        1,
        1
    )

    end = datetime(
        2026,
        5,
        31
    )

    tanggal = start

    while tanggal <= end:

        data_harian = scrape_tanggal(
            tanggal.strftime("%Y-%m-%d"),
            wilayah
        )

        seluruh_data.extend(
            data_harian
        )

        tanggal += timedelta(days=1)

    return pd.DataFrame(
        seluruh_data
    )


def main():

    df = scrape_periode()

    # FIXED: pakai path absolut yang benar
    os.makedirs(
        RAW_FOLDER,
        exist_ok=True
    )

    output = os.path.join(
        RAW_FOLDER,
        "harga_jawa_jan_mei_2026.csv"
    )

    df.to_csv(
        output,
        index=False,
        encoding="utf-8-sig"
    )

    print(
        f"\nSelesai : {output}"
    )

    print(
        f"Total record : {len(df)}"
    )


if __name__ == "__main__":
    main()