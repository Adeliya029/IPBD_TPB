CREATE TABLE IF NOT EXISTS cuaca_realtime (

    id SERIAL PRIMARY KEY,

    waktu TIMESTAMP,

    provinsi VARCHAR(100),

    kab_kota VARCHAR(100),

    suhu FLOAT,

    kelembapan FLOAT,

    curah_hujan FLOAT,

    kecepatan_angin FLOAT,

    tekanan_udara FLOAT,

    kondisi_cuaca VARCHAR(100),

    deskripsi_cuaca VARCHAR(255),

    sumber VARCHAR(100)

);