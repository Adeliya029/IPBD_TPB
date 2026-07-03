import os
import sys
import json
import pickle
import numpy as np
import pandas as pd
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from dotenv import load_dotenv
load_dotenv()

from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': int(os.getenv('POSTGRES_PORT', '5440')),
    'dbname': os.getenv('POSTGRES_DB', 'harga_pangan'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', 'postgres'),
}

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..')

# Only 6 features that actually exist in cuaca_harga_merged
PRICE_FEATURES = [
    'suhu_mean', 'curah_hujan_mm', 'kelembapan',
    'kecepatan_angin', 'tekanan_udara', 'curah_hujan_lag_7d',
]

CLUSTER_FEATURES = [
    'suhu_mean', 'curah_hujan_mm', 'kelembapan',
    'kecepatan_angin', 'tekanan_udara',
]

TARGET_CLASSES = ['TURUN', 'STABIL', 'NAIK']

CLUSTER_LABELS = {
    0: 'Cuaca Normal',
    1: 'Suhu Tinggi - Kering',
    2: 'Musim Hujan Lebat',
    3: 'Kemarau Ekstrem',
}


def load_merged_data():
    import psycopg
    conn = psycopg.connect(**DB_CONFIG)
    df = pd.read_sql("""
        SELECT suhu_mean, curah_hujan_mm, kelembapan,
               kecepatan_angin, tekanan_udara, harga_change_pct,
               curah_hujan_lag_7d, tanggal, provinsi, kab_kota, komoditas
        FROM cuaca_harga_merged
        WHERE suhu_mean IS NOT NULL
    """, conn)
    conn.close()
    print(f"  ? Loaded {len(df)} rows from cuaca_harga_merged")
    return df


def retrain_price_model(df):
    print("\n===== RETRAIN PRICE PREDICTION MODEL =====")
    print(f"  Features: {PRICE_FEATURES}")

    df = df.copy()

    # Build target from harga_change_pct
    def categorize(pct):
        if pd.isna(pct):
            return None
        if pct > 2:
            return 2
        elif pct < -2:
            return 0
        else:
            return 1

    df['target'] = df['harga_change_pct'].apply(categorize)
    df = df.dropna(subset=['target'])
    print(f"  After dropping NA target: {len(df)} rows")

    # Check target distribution
    print(f"  Target distribution:")
    for t, name in [(0, 'TURUN'), (1, 'STABIL'), (2, 'NAIK')]:
        cnt = (df['target'] == t).sum()
        print(f"    {name}: {cnt}")

    if len(df) < 100:
        print("  ? Not enough data, using synthetic fallback")
        return retrain_price_model_synthetic()

    X = df[PRICE_FEATURES].fillna(0).values
    y = df['target'].values.astype(int)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.2, random_state=42, stratify=y
    )

    model = GradientBoostingClassifier(
        n_estimators=200, learning_rate=0.1, max_depth=5, random_state=42
    )
    model.fit(X_train, y_train)

    train_acc = model.score(X_train, y_train)
    test_acc = model.score(X_test, y_test)
    print(f"  Train accuracy: {train_acc:.3f}")
    print(f"  Test accuracy:  {test_acc:.3f}")

    y_pred = model.predict(X_test)
    print(f"\n  Classification Report:")
    print(f"  {classification_report(y_test, y_pred, target_names=TARGET_CLASSES)}")

    # Save
    model_path = os.path.join(PROJECT_ROOT, 'models', 'saved', 'food_price_predictor.pkl')
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    with open(model_path, 'wb') as f:
        pickle.dump({
            'model': model,
            'scaler': scaler,
            'feature_names': PRICE_FEATURES,
            'target_classes': TARGET_CLASSES,
            'timestamp': datetime.now().isoformat(),
        }, f)
    print(f"  ? Model saved to {model_path}")

    return model, scaler


def retrain_price_model_synthetic():
    print("  Generating synthetic training data...")
    np.random.seed(42)

    training_data = []
    # Scenario 1: Hujan tinggi → NAIK
    for _ in range(150):
        training_data.append({
            'features': {
                'suhu_mean': np.random.normal(25, 2),
                'curah_hujan_mm': np.random.normal(80, 20),
                'kelembapan': np.random.normal(90, 5),
                'kecepatan_angin': np.random.normal(15, 5),
                'tekanan_udara': np.random.normal(1008, 3),
                'curah_hujan_lag_7d': np.random.normal(50, 15),
            },
            'target': 2
        })
    # Scenario 2: Cuaca ideal → STABIL
    for _ in range(200):
        training_data.append({
            'features': {
                'suhu_mean': np.random.normal(27, 2),
                'curah_hujan_mm': np.random.normal(10, 5),
                'kelembapan': np.random.normal(75, 5),
                'kecepatan_angin': np.random.normal(10, 3),
                'tekanan_udara': np.random.normal(1012, 2),
                'curah_hujan_lag_7d': np.random.normal(12, 5),
            },
            'target': 1
        })
    # Scenario 3: Kering → TURUN
    for _ in range(150):
        training_data.append({
            'features': {
                'suhu_mean': np.random.normal(28, 2),
                'curah_hujan_mm': np.random.normal(0, 2),
                'kelembapan': np.random.normal(65, 5),
                'kecepatan_angin': np.random.normal(8, 3),
                'tekanan_udara': np.random.normal(1014, 2),
                'curah_hujan_lag_7d': np.random.normal(2, 3),
            },
            'target': 0
        })

    rows = []
    for s in training_data:
        rows.append([s['features'][f] for f in PRICE_FEATURES])
    X = np.array(rows)
    y = np.array([s['target'] for s in training_data])

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = GradientBoostingClassifier(
        n_estimators=200, learning_rate=0.1, max_depth=5, random_state=42
    )
    model.fit(X_scaled, y)

    model_path = os.path.join(PROJECT_ROOT, 'models', 'saved', 'food_price_predictor.pkl')
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    with open(model_path, 'wb') as f:
        pickle.dump({
            'model': model,
            'scaler': scaler,
            'feature_names': PRICE_FEATURES,
            'target_classes': TARGET_CLASSES,
            'timestamp': datetime.now().isoformat(),
        }, f)
    print(f"  ? Synthetic model saved to {model_path}")
    return model, scaler


def retrain_clustering_model(df):
    print("\n===== RETRAIN CLUSTERING MODEL =====")
    print(f"  Features: {CLUSTER_FEATURES}")

    X = df[CLUSTER_FEATURES].fillna(df[CLUSTER_FEATURES].median()).values
    print(f"  Data: {len(X)} rows")

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    n_clusters = 3
    model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10, max_iter=300)
    labels = model.fit_predict(X_scaled)

    try:
        sil = silhouette_score(X_scaled, labels)
        print(f"  Silhouette score: {sil:.4f}")
    except Exception:
        sil = None

    df_result = df[CLUSTER_FEATURES].copy()
    df_result['cluster'] = labels

    cluster_stats = {}
    for cid in range(n_clusters):
        cd = df_result[df_result['cluster'] == cid]
        stats = {
            'n_samples': int(len(cd)),
            'pct': round(len(cd) / len(X) * 100, 1),
            'label': CLUSTER_LABELS.get(cid, f'Cluster {cid}'),
        }
        for feat in CLUSTER_FEATURES:
            stats[f'{feat}_mean'] = round(float(cd[feat].mean()), 2)
        cluster_stats[cid] = stats
        print(f"  Cluster {cid} ({stats['label']}): {stats['n_samples']} ({stats['pct']}%)")

    model_path = os.path.join(PROJECT_ROOT, 'models', 'saved', 'weather_clustering.pkl')
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    with open(model_path, 'wb') as f:
        pickle.dump({
            'model': model,
            'scaler': scaler,
            'cluster_stats': cluster_stats,
            'feature_names': CLUSTER_FEATURES,
            'n_clusters': n_clusters,
            'trained_at': datetime.now().isoformat(),
            'training_samples': len(X),
        }, f)
    print(f"  ? Clustering model saved to {model_path}")

    return model, scaler, cluster_stats


def main():
    print("=" * 60)
    print("  RETRAIN BOTH MODELS WITH MERGED DATA")
    print("=" * 60)

    df = load_merged_data()
    if df.empty:
        print("  ? No data available. Running synthetic fallback.")
        retrain_price_model_synthetic()
        return

    retrain_price_model(df)
    retrain_clustering_model(df)

    print("\n" + "=" * 60)
    print("  RETRAIN COMPLETE")
    print("=" * 60)


if __name__ == '__main__':
    main()
