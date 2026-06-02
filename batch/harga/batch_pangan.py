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
# PATH CONFIG
# =========================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_FOLDER = os.path.join(BASE_DIR, "..", "..", "data", "raw", "harga")

# Mapping kode provinsi ke nama provinsi (uppercase)
MAPPING_PROVINSI = {
    "31": "DKI JAKARTA",
    "32": "JAWA BARAT",
    "33": "JAWA TENGAH",
    "34": "DI YOGYAKARTA",
    "35": "JAWA TIMUR",
    "36": "BANTEN",
}


def ambil_harga(tanggal, tanggal_pembanding, kode_provinsi, kode_kab_kota):

    payload = {
        "tanggal": tanggal,
        "tanggal_pembanding": tanggal_pembanding,
        "kode_provinsi": kode_provinsi,
        "kode_kab_kota": kode_kab_kota
    }

    try:
        response = requests.post(URL, data=payload, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Gagal {kode_kab_kota} : {e}")
        return None


def scrape_tanggal(tanggal, wilayah_list):

    hasil = []

    tanggal_pembanding = (
        datetime.strptime(tanggal, "%Y-%m-%d")
        - timedelta(days=3)
    ).strftime("%Y-%m-%d")

    print(f"Tanggal : {tanggal}")

    for wilayah in wilayah_list:

        data = ambil_harga(
            tanggal,
            tanggal_pembanding,
            wilayah["kode_provinsi"],
            wilayah["kode_kab_kota"]
        )

        if not data:
            continue

        items = data.get("data", [])

        # Ambil nama provinsi dari mapping
        nama_provinsi = MAPPING_PROVINSI.get(wilayah["kode_provinsi"], "UNKNOWN")

        for item in items:
            hasil.append({
                "tanggal": tanggal,
                "kode_provinsi": wilayah["kode_provinsi"],
                "kode_kab_kota": wilayah["kode_kab_kota"],
                "provinsi": nama_provinsi,
                "kab_kota": wilayah["nama_kab_kota"].upper(),
                "variant_id": item["variant_id"],
                "komoditas": item["variant_nama"],
                "satuan": item["satuan_display"],
                "harga": item["harga"],
                "harga_pembanding": item["harga_pembanding"],
                "delta_harga": item["delta_harga"],
                "persen_perubahan": item["persen_perubahan"],
                "status_perubahan": item["status_perubahan"],
                "waktu_ingest": datetime.now().isoformat()
            })

        print(f"OK {wilayah['kode_kab_kota']} {wilayah['nama_kab_kota']}")
        time.sleep(0.2)

    return hasil


def scrape_minggu(tanggal_mulai, tanggal_akhir):
    """Scrape 1 minggu (7 hari) untuk semua kota."""

    wilayah = ambil_semua_wilayah()
    print(f"Total wilayah: {len(wilayah)}")

    seluruh_data = []
    tanggal = tanggal_mulai

    while tanggal <= tanggal_akhir:
        data_harian = scrape_tanggal(
            tanggal.strftime("%Y-%m-%d"),
            wilayah
        )
        seluruh_data.extend(data_harian)
        tanggal += timedelta(days=1)

    return pd.DataFrame(seluruh_data)


def scrape_minggu_ini():
    """Scrape 1 minggu terakhir (7 hari)."""

    tanggal_akhir = datetime.now() - timedelta(days=1)
    tanggal_mulai = tanggal_akhir - timedelta(days=6)

    print(f"{'='*60}")
    print(f"SP2KP BATCH MINGGUAN")
    print(f"{'='*60}")
    print(f"Periode: {tanggal_mulai.strftime('%Y-%m-%d')} s/d {tanggal_akhir.strftime('%Y-%m-%d')}")
    print(f"{'='*60}")

    df = scrape_minggu(tanggal_mulai, tanggal_akhir)

    os.makedirs(RAW_FOLDER, exist_ok=True)

    output = os.path.join(
        RAW_FOLDER,
        f"harga_mingguan_{tanggal_mulai.strftime('%Y%m%d')}_{tanggal_akhir.strftime('%Y%m%d')}.csv"
    )

    df.to_csv(output, index=False, encoding="utf-8-sig")

    print(f"Selesai : {output}")
    print(f"Total record : {len(df)}")

    return output


if __name__ == "__main__":
    scrape_minggu_ini()