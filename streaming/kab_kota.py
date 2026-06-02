import json

# =====================================
# LOAD DATA
# =====================================

with open(
    "../database/provinsi.json",
    "r",
    encoding="utf-8"
) as f:
    provinces = json.load(f)

with open(
    "../database/kab_kota.json",
    "r",
    encoding="utf-8"
) as f:
    regencies = json.load(f)

# =====================================
# MAPPING PROVINSI
# =====================================

province_map = {
    p["id"]: p["name"]
    for p in provinces
}

# =====================================
# FILTER PULAU JAWA
# =====================================

kode_provinsi_jawa = [
    "31",  # DKI Jakarta
    "32",  # Jawa Barat
    "33",  # Jawa Tengah
    "34",  # DIY
    "35",  # Jawa Timur
    "36"   # Banten
]

hasil = []

for regency in regencies:

    if regency["province_id"] in kode_provinsi_jawa:

        hasil.append({

            "provinsi":
                province_map[
                    regency["province_id"]
                ],

            "kab_kota":
                regency["name"],

            "latitude":
                regency["latitude"],

            "longitude":
                regency["longitude"]

        })

# =====================================
# SIMPAN FILE
# =====================================

output_file = "kab_kota_jawa.json"

with open(
    output_file,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        hasil,
        f,
        indent=2,
        ensure_ascii=False
    )

# =====================================
# INFO
# =====================================

print(
    f"Total Kab/Kota Jawa : {len(hasil)}"
)

print(
    f"File tersimpan : {output_file}"
)

print("\nContoh Data:")

for i, item in enumerate(hasil[:5], start=1):

    print(

        f"{i}. "
        f"{item['provinsi']} | "
        f"{item['kab_kota']} | "
        f"({item['latitude']}, {item['longitude']})"

    )