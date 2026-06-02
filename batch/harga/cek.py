import requests
import json

url = (
    "https://api-sp2kp.kemendag.go.id/"
    "report/api/average-price/"
    "generate-perbandingan-harga"
)

payload = {
    "tanggal": "2026-05-29",
    "tanggal_pembanding": "2026-05-26",
    "kode_provinsi": "32",
    "kode_kab_kota": "3207"
}

r = requests.post(url, data=payload)

print(r.status_code)

data = r.json()

print(len(data["data"]))

for item in data["data"][:5]:
    print(
        item["variant_id"],
        item["variant_nama"],
        item["harga"]
    )