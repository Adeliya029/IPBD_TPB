import requests

PROVINSI_JAWA = [
    "31",
    "32",
    "33",
    "34",
    "35",
    "36"
]


def ambil_semua_wilayah():

    semua = []

    for kode_provinsi in PROVINSI_JAWA:

        url = (
            "https://api-sp2kp.kemendag.go.id/"
            f"master/api/wilayah/kab-kota/{kode_provinsi}"
        )

        response = requests.get(url)

        data = response.json()

        for item in data["data"]:

            semua.append({
                "kode_provinsi": kode_provinsi,
                "kode_kab_kota": item["kode_kab_kota"],
                "nama_kab_kota": item["nama_kab_kota"]
            })

    return semua


if __name__ == "__main__":

    wilayah = ambil_semua_wilayah()

    print(len(wilayah))