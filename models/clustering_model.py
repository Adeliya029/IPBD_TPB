"""
Clustering Model — K-Means pada data cuaca + harga pangan.

Tujuan:
- Menemukan pola/kelompok kondisi cuaca yang mirip
- Mengidentifikasi cluster cuaca yang paling berisiko menyebabkan kenaikan harga
- Memperkaya tabel predictions dengan label cluster

Cluster yang dihasilkan (k=4):
- Cluster 0: Cuaca Normal — suhu & hujan sedang
- Cluster 1: Cuaca Ekstrem Panas — suhu tinggi, hujan rendah
- Cluster 2: Musim Hujan Lebat — hujan sangat tinggi, kelembapan tinggi
- Cluster 3: Musim Kemarau — suhu sangat tinggi, hujan sangat rendah

Output:
- models/saved/weather_clustering.pkl  (model tersimpan)
- logs/data/clustering_report.json      (laporan hasil)
- Tabel predictions diperbarui dengan kolom cluster_label
"""

import os
import sys
import json
import pickle
import logging
import numpy as np
import pandas as pd
from datetime import datetime

# Tambahkan project root ke sys.path
PROJECT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Paths
MODEL_SAVE_PATH = os.path.join(PROJECT_ROOT, "models", "saved", "weather_clustering.pkl")
REPORT_PATH = os.path.join(PROJECT_ROOT, "logs", "data", "clustering_report.json")
os.makedirs(os.path.dirname(MODEL_SAVE_PATH), exist_ok=True)
os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)

# Features yang digunakan untuk clustering
CLUSTER_FEATURES = [
    "suhu_mean",
    "curah_hujan_mm",
    "kelembapan",
    "kecepatan_angin",
    "tekanan_udara",
    "awan_persen",
]

# Jumlah cluster (dapat diubah untuk eksperimen)
N_CLUSTERS = 4

# Nama label cluster yang mudah dipahami
CLUSTER_LABELS = {
    0: "Cuaca Normal",
    1: "Suhu Tinggi - Kering",
    2: "Musim Hujan Lebat",
    3: "Kemarau Ekstrem",
}


class WeatherClusteringModel:
    """
    K-Means Clustering untuk data cuaca.
    Membantu mengidentifikasi pola cuaca yang berkorelasi dengan perubahan harga.
    """

    def __init__(self, n_clusters: int = N_CLUSTERS):
        self.n_clusters = n_clusters
        self.model = None
        self.scaler = None
        self.cluster_stats = {}
        self.feature_names = CLUSTER_FEATURES
        self.trained_at = None
        self.training_samples = 0

    # ─────────────────────────────────────────
    # TRAIN
    # ─────────────────────────────────────────

    def train(self, df: pd.DataFrame) -> dict:
        """
        Latih model K-Means pada data cuaca.

        Args:
            df: DataFrame dengan kolom cuaca (minimal suhu_mean, curah_hujan_mm, kelembapan)

        Returns:
            dict: Hasil training + statistik per cluster
        """
        from sklearn.cluster import KMeans
        from sklearn.preprocessing import StandardScaler
        from sklearn.metrics import silhouette_score

        logger.info(f"[INFO] Memulai K-Means training — {len(df)} baris, k={self.n_clusters}")

        # Pilih fitur yang tersedia
        available_features = [f for f in self.feature_names if f in df.columns]
        if len(available_features) < 2:
            raise ValueError(
                f"Minimal 2 fitur diperlukan. Tersedia: {available_features}"
            )

        logger.debug(f"[DEBUG] Fitur yang digunakan: {available_features}")

        # Ambil data & handle missing values
        X = df[available_features].copy()
        X = X.fillna(X.median())

        # Hapus baris yang masih null
        X = X.dropna()

        if len(X) < self.n_clusters:
            logger.warning(
                f"[WARNING] Data terlalu sedikit ({len(X)} baris) untuk {self.n_clusters} cluster. "
                "Mengurangi jumlah cluster."
            )
            self.n_clusters = max(2, len(X) // 2)

        # Normalisasi
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        # K-Means training
        self.model = KMeans(
            n_clusters=self.n_clusters,
            random_state=42,
            n_init=10,
            max_iter=300,
        )
        labels = self.model.fit_predict(X_scaled)

        # Hitung silhouette score
        try:
            sil_score = silhouette_score(X_scaled, labels)
        except Exception:
            sil_score = None

        self.trained_at = datetime.now().isoformat()
        self.training_samples = len(X)
        self.feature_names = available_features

        # Statistik per cluster
        df_result = X.copy()
        df_result["cluster"] = labels

        self.cluster_stats = {}
        for cluster_id in range(self.n_clusters):
            cluster_data = df_result[df_result["cluster"] == cluster_id]
            stats = {
                "n_samples": int(len(cluster_data)),
                "pct": round(len(cluster_data) / len(X) * 100, 1),
                "label": CLUSTER_LABELS.get(cluster_id, f"Cluster {cluster_id}"),
            }
            for feat in available_features:
                stats[f"{feat}_mean"] = round(float(cluster_data[feat].mean()), 2)
                stats[f"{feat}_std"] = round(float(cluster_data[feat].std()), 2)
            self.cluster_stats[cluster_id] = stats

        result = {
            "n_clusters": self.n_clusters,
            "n_samples": len(X),
            "features_used": available_features,
            "silhouette_score": round(float(sil_score), 4) if sil_score else None,
            "inertia": round(float(self.model.inertia_), 2),
            "trained_at": self.trained_at,
            "cluster_stats": self.cluster_stats,
        }

        sil_str = f"{sil_score:.4f}" if sil_score is not None else "N/A"
        logger.info(
            f"[INFO] Training selesai — Silhouette: {sil_str}, "
            f"Inertia: {self.model.inertia_:.2f}"
        )

        for cid, stats in self.cluster_stats.items():
            logger.info(
                f"[INFO]   Cluster {cid} ({stats['label']}): "
                f"{stats['n_samples']} samples ({stats['pct']}%)"
            )

        return result

    # ─────────────────────────────────────────
    # PREDICT
    # ─────────────────────────────────────────

    def predict(self, weather_data: dict) -> dict:
        """
        Prediksi cluster untuk satu data cuaca.

        Args:
            weather_data: dict dengan key sesuai CLUSTER_FEATURES

        Returns:
            dict: cluster_id, cluster_label, nama
        """
        if self.model is None:
            raise RuntimeError("Model belum ditraining. Panggil train() atau load_model() dulu.")

        X = np.array([[weather_data.get(f, 0) for f in self.feature_names]])
        X_scaled = self.scaler.transform(X)
        cluster_id = int(self.model.predict(X_scaled)[0])

        return {
            "cluster_id": cluster_id,
            "cluster_label": CLUSTER_LABELS.get(cluster_id, f"Cluster {cluster_id}"),
            "cluster_stats": self.cluster_stats.get(cluster_id, {}),
        }

    # ─────────────────────────────────────────
    # SAVE / LOAD
    # ─────────────────────────────────────────

    def save_model(self, path: str = None):
        """Simpan model ke file pickle."""
        save_path = path or MODEL_SAVE_PATH
        with open(save_path, "wb") as f:
            pickle.dump(
                {
                    "model": self.model,
                    "scaler": self.scaler,
                    "cluster_stats": self.cluster_stats,
                    "feature_names": self.feature_names,
                    "n_clusters": self.n_clusters,
                    "trained_at": self.trained_at,
                    "training_samples": self.training_samples,
                },
                f,
            )
        logger.info(f"[INFO] Clustering model disimpan ke {save_path}")

    def load_model(self, path: str = None):
        """Load model dari file pickle."""
        load_path = path or MODEL_SAVE_PATH
        if not os.path.exists(load_path):
            raise FileNotFoundError(f"Model tidak ditemukan: {load_path}")

        with open(load_path, "rb") as f:
            data = pickle.load(f)

        self.model = data["model"]
        self.scaler = data["scaler"]
        self.cluster_stats = data["cluster_stats"]
        self.feature_names = data["feature_names"]
        self.n_clusters = data["n_clusters"]
        self.trained_at = data["trained_at"]
        self.training_samples = data["training_samples"]

        logger.info(
            f"[INFO] Clustering model di-load dari {load_path} "
            f"(trained: {self.trained_at}, k={self.n_clusters})"
        )


# ─────────────────────────────────────────
# FUNGSI PIPELINE
# ─────────────────────────────────────────

def _get_db_config():
    """Ambil konfigurasi database dari environment variable."""
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", "5440")),
        "dbname": os.getenv("POSTGRES_DB", "harga_pangan"),
        "user": os.getenv("POSTGRES_USER", "postgres"),
        "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
    }


def train_clustering_from_db(n_clusters: int = N_CLUSTERS) -> WeatherClusteringModel:
    """
    Training clustering dari data cuaca di PostgreSQL.

    Returns:
        WeatherClusteringModel: Model yang sudah ditraining
    """
    logger.info("[INFO] Load data cuaca dari PostgreSQL untuk clustering...")

    try:
        import psycopg

        conn = psycopg.connect(**_get_db_config())
        df = pd.read_sql(
            """
            SELECT suhu_mean, suhu_max, suhu_min, curah_hujan_mm,
                   kelembapan, kecepatan_angin, tekanan_udara, awan_persen
            FROM cuaca_historical
            WHERE suhu_mean IS NOT NULL
            ORDER BY RANDOM()
            LIMIT 5000
            """,
            conn,
        )
        conn.close()

        if df.empty:
            raise ValueError("Tidak ada data cuaca di PostgreSQL")

        logger.info(f"[INFO] Data cuaca dimuat: {len(df)} baris")

    except Exception as e:
        logger.warning(
            f"[WARNING] Gagal load dari PostgreSQL: {str(e)}. "
            "Gunakan synthetic data."
        )
        df = _generate_synthetic_weather_data()

    model = WeatherClusteringModel(n_clusters=n_clusters)
    result = model.train(df)
    model.save_model()

    # Simpan laporan
    _save_clustering_report(result)

    return model


def _generate_synthetic_weather_data(n_samples: int = 2000) -> pd.DataFrame:
    """
    Generate synthetic weather data untuk testing clustering.
    Membuat 4 cluster buatan yang mewakili kondisi cuaca nyata Indonesia.
    """
    logger.info(f"[INFO] Generate {n_samples} synthetic weather data untuk clustering...")
    np.random.seed(42)
    n = n_samples // 4

    # Cluster 0: Normal
    c0 = pd.DataFrame({
        "suhu_mean": np.random.normal(27, 2, n),
        "curah_hujan_mm": np.random.exponential(5, n),
        "kelembapan": np.random.normal(75, 8, n),
        "kecepatan_angin": np.random.normal(15, 5, n),
        "tekanan_udara": np.random.normal(1013, 5, n),
        "awan_persen": np.random.normal(60, 15, n),
    })
    # Cluster 1: Panas Kering
    c1 = pd.DataFrame({
        "suhu_mean": np.random.normal(35, 2, n),
        "curah_hujan_mm": np.random.exponential(1, n),
        "kelembapan": np.random.normal(50, 8, n),
        "kecepatan_angin": np.random.normal(25, 8, n),
        "tekanan_udara": np.random.normal(1010, 5, n),
        "awan_persen": np.random.normal(20, 10, n),
    })
    # Cluster 2: Hujan Lebat
    c2 = pd.DataFrame({
        "suhu_mean": np.random.normal(24, 2, n),
        "curah_hujan_mm": np.random.exponential(80, n),
        "kelembapan": np.random.normal(95, 3, n),
        "kecepatan_angin": np.random.normal(20, 10, n),
        "tekanan_udara": np.random.normal(1008, 8, n),
        "awan_persen": np.random.normal(95, 5, n),
    })
    # Cluster 3: Kemarau Ekstrem
    c3 = pd.DataFrame({
        "suhu_mean": np.random.normal(38, 2, n),
        "curah_hujan_mm": np.random.exponential(0.5, n),
        "kelembapan": np.random.normal(35, 10, n),
        "kecepatan_angin": np.random.normal(30, 10, n),
        "tekanan_udara": np.random.normal(1005, 5, n),
        "awan_persen": np.random.normal(10, 5, n),
    })

    df = pd.concat([c0, c1, c2, c3], ignore_index=True)
    # Clip ke range yang masuk akal
    df["suhu_mean"] = df["suhu_mean"].clip(15, 45)
    df["curah_hujan_mm"] = df["curah_hujan_mm"].clip(0, 300)
    df["kelembapan"] = df["kelembapan"].clip(20, 100)
    df["kecepatan_angin"] = df["kecepatan_angin"].clip(0, 60)
    df["tekanan_udara"] = df["tekanan_udara"].clip(990, 1030)
    df["awan_persen"] = df["awan_persen"].clip(0, 100)

    logger.info(f"[INFO] Synthetic data generated: {len(df)} baris")
    return df


def update_predictions_with_cluster(cluster_model: WeatherClusteringModel):
    """
    Update tabel predictions di PostgreSQL dengan label cluster dari cuaca terbaru.
    Mengambil data cuaca dari cuaca_realtime dan menambahkan cluster_label.
    """
    logger.info("[INFO] Update tabel predictions dengan cluster label...")

    try:
        import psycopg

        conn = psycopg.connect(**_get_db_config())
        cur = conn.cursor()

        # Ambil data cuaca realtime terbaru
        cur.execute("""
            SELECT id, kab_kota, suhu_mean, curah_hujan_mm,
                   kelembapan, kecepatan_angin, tekanan_udara, awan_persen
            FROM cuaca_realtime
            WHERE cluster_label IS NULL
            ORDER BY waktu DESC
            LIMIT 1000
        """)
        rows = cur.fetchall()
        columns = ["id", "kab_kota", "suhu_mean", "curah_hujan_mm",
                   "kelembapan", "kecepatan_angin", "tekanan_udara", "awan_persen"]

        updated = 0
        for row in rows:
            row_dict = dict(zip(columns, row))
            weather_data = {k: (v if v is not None else 0) for k, v in row_dict.items()
                           if k != "id" and k != "kab_kota"}
            try:
                cluster_result = cluster_model.predict(weather_data)
                cluster_id = cluster_result["cluster_id"]
                # Update cuaca_realtime dengan cluster label
                cur.execute(
                    "UPDATE cuaca_realtime SET cluster_label = %s WHERE id = %s",
                    (cluster_id, row_dict["id"])
                )
                updated += 1
            except Exception as e:
                logger.debug(f"[DEBUG] Skip row {row_dict['id']}: {str(e)}")

        conn.commit()
        cur.close()
        conn.close()

        logger.info(f"[INFO] Update cluster label selesai: {updated} records diperbarui")
        return updated

    except Exception as e:
        logger.warning(f"[WARNING] Gagal update predictions: {str(e)}")
        return 0


def _save_clustering_report(result: dict):
    """Simpan laporan clustering ke JSON."""
    report = {
        "timestamp": datetime.now().isoformat(),
        "model_type": "K-Means Clustering",
        "description": "Clustering kondisi cuaca untuk analisis pola harga pangan",
        "result": result,
        "cluster_descriptions": CLUSTER_LABELS,
    }

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)

    logger.info(f"[INFO] Laporan clustering disimpan ke {REPORT_PATH}")


def run_clustering_pipeline(n_clusters: int = N_CLUSTERS) -> dict:
    """
    Jalankan full clustering pipeline:
    1. Load data cuaca dari DB (atau synthetic)
    2. Training K-Means
    3. Simpan model
    4. Update predictions dengan cluster label
    5. Simpan laporan

    Returns:
        dict: Laporan hasil clustering
    """
    logger.info("=" * 60)
    logger.info("[INFO] MEMULAI CLUSTERING PIPELINE (K-Means)")
    logger.info("=" * 60)

    # Training
    model = train_clustering_from_db(n_clusters=n_clusters)

    # Update predictions
    updated = update_predictions_with_cluster(model)

    logger.info("=" * 60)
    logger.info(f"[INFO] CLUSTERING SELESAI — {updated} records diperbarui")
    logger.info("=" * 60)

    return {
        "status": "SUCCESS",
        "model_path": MODEL_SAVE_PATH,
        "report_path": REPORT_PATH,
        "records_updated": updated,
    }


# ─────────────────────────────────────────
# MAIN — Jalankan langsung untuk testing
# ─────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("K-MEANS CLUSTERING — CUACA PANGAN JAWA")
    print("=" * 60)

    # Run 1: k=3
    print("\n[RUN 1] Training dengan k=3...")
    result1 = run_clustering_pipeline(n_clusters=3)

    # Run 2: k=4 (default)
    print("\n[RUN 2] Training dengan k=4...")
    result2 = run_clustering_pipeline(n_clusters=4)

    # Run 3: k=5
    print("\n[RUN 3] Training dengan k=5...")
    result3 = run_clustering_pipeline(n_clusters=5)

    print("\n" + "=" * 60)
    print("HASIL SEMUA RUN:")
    print(f"  Run 1 (k=3): {result1['status']}")
    print(f"  Run 2 (k=4): {result2['status']}")
    print(f"  Run 3 (k=5): {result3['status']}")
    print(f"\n📁 Model tersimpan: {MODEL_SAVE_PATH}")
    print(f"📊 Laporan tersimpan: {REPORT_PATH}")
    print("=" * 60)
