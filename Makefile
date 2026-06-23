# ============================================================
# IPBD_TPB — Makefile
# Sistem Analisis & Prediksi Harga Pangan (Pulau Jawa)
# ============================================================

.PHONY: setup stream batch dashboard health train reset clean help

# ============================================================
# SETUP: Start infra + install dependencies
# ============================================================
setup:
	docker compose up -d
	pip install -r requirements.txt
	@echo ""
	@echo "✅ Setup selesai!"
	@echo "   PostgreSQL : localhost:5440"
	@echo "   MinIO      : localhost:9000 (console: 9001)"
	@echo "   Kafka      : localhost:9092"
	@echo "   Prometheus : localhost:9090"
	@echo "   Grafana    : localhost:3000"

# ============================================================
# STREAM: Jalankan producer + consumer cuaca realtime
# ============================================================
stream:
	@echo "▶ Menjalankan streaming cuaca..."
	python streaming/open_producer.py &
	python streaming/open_consumer.py
	@echo "Streaming aktif (Ctrl+C untuk stop)"

# ============================================================
# BATCH: Jalankan full batch pipeline
# ============================================================
batch:
	@echo "▶ Menjalankan batch pipeline..."
	python pipeline/run_batch.py

# ============================================================
# DASHBOARD: Jalankan Streamlit dashboard
# ============================================================
dashboard:
	@echo "▶ Menjalankan dashboard Streamlit..."
	streamlit run dashboard/app.py --server.port 8501

# ============================================================
# HEALTH: Cek kesehatan semua service
# ============================================================
health:
	@echo "▶ Health check..."
	python pipeline/health_check.py

# ============================================================
# TRAIN: Train ulang model ML dari data CSV
# ============================================================
train:
	@echo "▶ Training model..."
	python -c "from models.price_prediction_model import train_model_from_data; train_model_from_data()"

# ============================================================
# QUALITY: Jalankan data quality checks
# ============================================================
quality:
	@echo "▶ Data quality checks..."
	python -c "from governance.quality_checks import run_all_quality_checks; run_all_quality_checks()"

# ============================================================
# METADATA: Populate metadata catalog
# ============================================================
metadata:
	@echo "▶ Populating metadata catalog..."
	python -c "from governance.metadata_manager import MetadataManager; MetadataManager().populate_metadata_catalog()"

# ============================================================
# RESET: Stop semua + hapus data
# ============================================================
reset:
	docker compose down -v
	rm -rf logs/data/*.log logs/data/*.json
	@echo "✅ Reset selesai. Semua data Docker dihapus."

# ============================================================
# CLEAN: Hapus file sementara
# ============================================================
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Cache dibersihkan."

# ============================================================
# HELP
# ============================================================
help:
	@echo ""
	@echo "╔══════════════════════════════════════════════════════╗"
	@echo "║  IPBD_TPB — Harga Pangan Jawa                      ║"
	@echo "╠══════════════════════════════════════════════════════╣"
	@echo "║  make setup     → Start Docker + install deps       ║"
	@echo "║  make stream    → Streaming cuaca realtime          ║"
	@echo "║  make batch     → Full batch pipeline               ║"
	@echo "║  make dashboard → Streamlit dashboard (port 8501)   ║"
	@echo "║  make health    → Health check semua service        ║"
	@echo "║  make train     → Train ulang model ML              ║"
	@echo "║  make quality   → Data quality checks               ║"
	@echo "║  make metadata  → Populate metadata catalog         ║"
	@echo "║  make reset     → Docker down + hapus logs          ║"
	@echo "║  make clean     → Hapus cache Python                ║"
	@echo "║  make help      → Tampilkan bantuan ini             ║"
	@echo "╚══════════════════════════════════════════════════════╝"
	@echo ""
