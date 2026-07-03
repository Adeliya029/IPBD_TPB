import os
import sys
import json
import joblib
import psycopg
import numpy as np
import pandas as pd
from datetime import datetime, date, timedelta
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
load_dotenv()

DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': int(os.getenv('POSTGRES_PORT', '5440')),
    'dbname': os.getenv('POSTGRES_DB', 'harga_pangan'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', 'postgres'),
}

MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'models', 'saved', 'food_price_predictor.pkl')
CLUSTER_PATH = os.path.join(os.path.dirname(__file__), '..', 'models', 'saved', 'weather_clustering.pkl')

PRICE_FEATURES = [
    'suhu_mean', 'curah_hujan_mm', 'kelembapan',
    'kecepatan_angin', 'tekanan_udara', 'curah_hujan_lag_7d',
]

CLUSTER_FEATURES = [
    'suhu_mean', 'curah_hujan_mm', 'kelembapan',
    'kecepatan_angin', 'tekanan_udara',
]

def load_model_obj(path, label="model"):
    if not os.path.exists(path):
        print(f"  ? File tidak ditemukan: {path}")
        return None
    obj = joblib.load(path)
    print(f"  ? {label} dimuat dari {path}")
    return obj

def extract_pipeline_model(obj):
    if isinstance(obj, dict):
        return (obj.get('model'), obj.get('scaler'),
                obj.get('feature_names'), obj.get('target_classes'))
    return obj, None, None, None

def get_merged_data(conn):
    df = pd.read_sql("""
        SELECT id, tanggal, provinsi, kab_kota, komoditas, harga,
               suhu_mean, curah_hujan_mm, kelembapan,
               kecepatan_angin, tekanan_udara,
               curah_hujan_lag_7d, harga_lag_7d, harga_change_pct
        FROM cuaca_harga_merged
        ORDER BY tanggal DESC
    """, conn)
    print(f"  ? Data merged: {len(df)} baris")
    return df

def predict_all(model, scaler, target_classes, df):
    available = [f for f in PRICE_FEATURES if f in df.columns]
    X = df[available].fillna(0).values
    if scaler:
        X = scaler.transform(X)

    raw_labels = model.predict(X)
    probs_all = model.predict_proba(X) if hasattr(model, 'predict_proba') else None

    results = []
    for i in range(len(X)):
        raw = int(raw_labels[i])
        label = target_classes[raw] if target_classes and raw < len(target_classes) else str(raw)
        confidence = float(np.max(probs_all[i])) if probs_all is not None else 0.0
        prob_dict = {}
        if probs_all is not None and target_classes:
            for j, c in enumerate(target_classes):
                prob_dict[c.lower()] = float(probs_all[i][j])

        results.append({
            'prediksi_label': label,
            'prob_naik': prob_dict.get('naik'),
            'prob_turun': prob_dict.get('turun'),
            'prob_stabil': prob_dict.get('stabil'),
            'confidence': confidence,
        })
    return results

def assign_cluster_to_cuaca(conn, cluster_model, scaler):
    print("\n  ? Update cluster label di cuaca_realtime...")
    cur = conn.cursor()
    cur.execute("""
        SELECT id, suhu_mean, curah_hujan_mm, kelembapan,
               kecepatan_angin, tekanan_udara
        FROM cuaca_realtime
    """)
    rows = cur.fetchall()
    if not rows:
        print("  ? Tidak ada data cuaca_realtime")
        cur.close()
        return 0

    cols = ['id'] + CLUSTER_FEATURES
    df = pd.DataFrame(rows, columns=cols).fillna(0)
    X = df[CLUSTER_FEATURES].values
    if scaler:
        X = scaler.transform(X)
    labels = cluster_model.predict(X)

    updated = 0
    cluster_names = {0: 'Cuaca Normal', 1: 'Suhu Tinggi - Kering',
                     2: 'Musim Hujan Lebat', 3: 'Cuaca Ekstrem'}
    for i, row_id in enumerate(df['id']):
        label = int(labels[i])
        cur.execute("""
            UPDATE cuaca_realtime
            SET cluster_label = %s, cluster_nama = %s
            WHERE id = %s
        """, (label, cluster_names.get(label, f'Cluster {label}'), row_id))
        updated += 1
        if updated % 200 == 0:
            print(f"    ... {updated} baris diupdate")

    conn.commit()
    cur.close()
    print(f"  ? {updated} baris cuaca_realtime diupdate dengan cluster label")
    return updated

def assign_cluster_to_merged(conn, cluster_model, scaler, df_merged):
    """Assign cluster labels to merged data rows using the clustering model."""
    print("\n  ? Assign cluster label ke data merged...")
    available = [f for f in CLUSTER_FEATURES if f in df_merged.columns]
    X = df_merged[available].fillna(0).values
    if scaler:
        X = scaler.transform(X)
    labels = cluster_model.predict(X)
    return labels

def store_predictions(conn, df_merged, pred_results, cluster_labels):
    cur = conn.cursor()
    inserted = 0

    cluster_names = {0: 'Cuaca Normal', 1: 'Suhu Tinggi - Kering',
                     2: 'Musim Hujan Lebat', 3: 'Cuaca Ekstrem'}

    for i, (_, row) in enumerate(df_merged.iterrows()):
        pred = pred_results[i]
        cl = int(cluster_labels[i]) if cluster_labels is not None else -1
        cn = cluster_names.get(cl, f'Cluster {cl}')

        try:
            cur.execute("""
                INSERT INTO predictions
                    (tanggal_prediksi, provinsi, kab_kota, komoditas,
                     prediksi_label, prediction_label, probabilitas_naik,
                     probabilitas_turun, probabilitas_stabil, confidence,
                     suhu_mean, curah_hujan_mm, kelembapan,
                     cluster_label, cluster_nama, model_version,
                     pipeline_run_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (
                row.get('tanggal') or date.today(),
                row.get('provinsi'),
                row.get('kab_kota'),
                row.get('komoditas'),
                pred['prediksi_label'],
                pred['prediksi_label'],
                pred['prob_naik'],
                pred['prob_turun'],
                pred['prob_stabil'],
                pred['confidence'],
                row.get('suhu_mean'),
                row.get('curah_hujan_mm'),
                row.get('kelembapan'),
                cl,
                cn,
                'food_price_predictor_v2',
                'predict_and_store'
            ))
            inserted += 1
        except Exception as e:
            print(f"    ? Insert error: {e}")

    conn.commit()
    cur.close()
    return inserted

def main():
    print("=" * 60)
    print("  PREDICT & STORE — Isi tabel predictions")
    print("=" * 60)

    model_obj = load_model_obj(MODEL_PATH, "Model prediksi harga")
    cluster_obj = load_model_obj(CLUSTER_PATH, "Model clustering cuaca")
    if model_obj is None and cluster_obj is None:
        print("\n  ? Tidak ada model. Selesai.")
        return

    model, scaler, fn, target_classes = extract_pipeline_model(model_obj) if model_obj else (None, None, None, None)
    if model and not hasattr(model, 'predict'):
        model = model_obj
        target_classes = None
    if fn:
        print(f"  ? Model expects {len(fn)} features: {fn}")

    conn = psycopg.connect(**DB_CONFIG)
    print("\n  ? Terhubung ke PostgreSQL")

    # --- Clustering ---
    cluster_model = None
    cluster_scaler = None
    if cluster_obj:
        cr = extract_pipeline_model(cluster_obj)
        cluster_model, cluster_scaler, _, _ = cr
        if not (cluster_model and hasattr(cluster_model, 'predict')):
            if hasattr(cluster_obj, 'predict'):
                cluster_model = cluster_obj

    # Assign cluster to cuaca_realtime
    if cluster_model:
        assign_cluster_to_cuaca(conn, cluster_model, cluster_scaler)

    if model is None:
        conn.close()
        print("\n? Selesai (hanya cluster).")
        return

    # --- Load merged data ---
    print("\n  ? Ambil data merged...")
    df_merged = get_merged_data(conn)
    if df_merged.empty:
        conn.close()
        return

    # --- Predict all rows at once ---
    print("  ? Prediksi harga...")
    pred_results = predict_all(model, scaler, target_classes, df_merged)

    # --- Cluster the merged data ---
    cluster_labels = None
    if cluster_model:
        cluster_labels = assign_cluster_to_merged(conn, cluster_model, cluster_scaler, df_merged)

    # --- Summary ---
    labels = [p['prediksi_label'] for p in pred_results]
    from collections import Counter
    cnt = Counter(labels)
    print(f"\n  ? Distribusi prediksi: {dict(cnt)}")

    confs = [p['confidence'] for p in pred_results]
    print(f"  ? Confidence: min={min(confs):.4f}, max={max(confs):.4f}, avg={np.mean(confs):.4f}")
    conf_buckets = Counter(round(c, 2) for c in confs)
    for k in sorted(conf_buckets):
        print(f"      confidence {k:.2f}: {conf_buckets[k]} rows")

    if cluster_labels is not None:
        clust_cnt = Counter(int(cluster_labels[i]) for i in range(len(cluster_labels)))
        print(f"  ? Cluster distribution: {dict(clust_cnt)}")

    # --- Truncate and re-insert predictions ---
    cur = conn.cursor()
    cur.execute("TRUNCATE TABLE predictions RESTART IDENTITY")
    conn.commit()
    cur.close()
    print("  ? Tabel predictions dikosongkan")

    inserted = store_predictions(conn, df_merged, pred_results, cluster_labels)
    print(f"\n  ? {inserted} prediksi baru disimpan ke tabel predictions")

    conn.close()
    print("\n? Selesai!")

if __name__ == "__main__":
    main()
