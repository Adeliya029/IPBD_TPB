ipbd_tbp/
│
├── .env                          # Environment variables (API keys, credentials)
├── docker-compose.yml            # Infrastructure (Kafka, PostgreSQL, MinIO)
├── requirements.txt              # Python dependencies
├── .gitignore                    # Git ignore rules
│
├── batch/                        # 🔄 BATCH PROCESSING (Historical Data)
│   ├── harga/
│   │   ├── batch_pangan.py       # Scrape harga pangan mingguan (SP2KP)
│   │   ├── sp2kp_scraper.py      # Scrape harga pangan historical (Jan-Mei 2026)
│   │   ├── clean_harga.py        # Cleaning data harga (handle harga=0, ffill, etc)
│   │   ├── kab_kota.py           # Daftar wilayah (kode provinsi & kab/kota)
│   │   ├── upload_raw_harga.py   # Upload raw harga ke MinIO
│   │   └── upload_processed_harga.py  # Upload cleaned harga ke MinIO
│   │
│   ├── cuaca/
│   │   ├── histori_cuaca.py      # Scrape cuaca historical (Open-Meteo Archive)
│   │   ├── clean_cuaca.py         # Cleaning data cuaca
│   │   ├── upload_raw_cuaca.py    # Upload raw cuaca ke MinIO
│   │   └── upload_processed_cuaca.py  # Upload cleaned cuaca ke MinIO
│   │
│   └── storage/
│       └── upload_minio.py       # MinIO client utility
│
├── streaming/                    # ⚡ STREAM PROCESSING (Real-time Data)
│   ├── open_producer.py          # Producer: ambil cuaca real-time (Open-Meteo)
│   ├── open_consumer.py          # Consumer: simpan cuaca ke PostgreSQL
│   ├── producer.py               # Producer: cuaca real-time (OpenWeatherMap - alternatif)
│   ├── consumer.py               # Consumer: cuaca real-time (OpenWeatherMap - alternatif)
│   ├── kab_kota_jawa.json        # Daftar 119 kota dengan koordinat
│   └── cities_java.json          # Daftar kota untuk streaming
│
├── data/                         # 📊 DATA STORAGE (Auto-generated)
│   ├── raw/
│   │   ├── harga/                # Raw data harga dari SP2KP
│   │   └── cuaca/                # Raw data cuaca dari Open-Meteo
│   ├── processed/
│   │   ├── harga/                # Cleaned data harga
│   │   └── cuaca/                # Cleaned data cuaca
│   └── backup/
│       ├── harga/                # Backup sebelum cleaning
│       └── cuaca/                # Backup sebelum cleaning
│
├── database/
│   └── init.sql                  # Schema database PostgreSQL
│
└── venv/                         # Python virtual environment