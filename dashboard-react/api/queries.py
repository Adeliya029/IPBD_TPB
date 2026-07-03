import os
import psycopg
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': int(os.getenv('POSTGRES_PORT', '5440')),
    'dbname': os.getenv('POSTGRES_DB', 'harga_pangan'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', 'postgres'),
}

def get_conn():
    return psycopg.connect(**DB_CONFIG)

PROV_MAP = {
    '31': 'DKI Jakarta', '32': 'Jawa Barat', '33': 'Jawa Tengah',
    '34': 'DI Yogyakarta', '35': 'Jawa Timur', '36': 'Banten',
}

def prov_case():
    return "CASE provinsi WHEN '31' THEN 'DKI Jakarta' WHEN '32' THEN 'Jawa Barat' WHEN '33' THEN 'Jawa Tengah' WHEN '34' THEN 'DI Yogyakarta' WHEN '35' THEN 'Jawa Timur' WHEN '36' THEN 'Banten' END"

def prov_name(code):
    return PROV_MAP.get(code, code)

def where_clause(start, end, provinsi=None, komoditas=None):
    clauses = ["TRUE"]
    params = {}
    if start:
        clauses.append("tanggal >= %(start)s")
        params['start'] = start
    if end:
        clauses.append("tanggal <= %(end)s")
        params['end'] = end
    if provinsi and provinsi != 'all':
        clauses.append("provinsi = %(provinsi)s")
        params['provinsi'] = provinsi
    if komoditas and komoditas != 'all':
        clauses.append("komoditas = %(komoditas)s")
        params['komoditas'] = komoditas
    return " AND ".join(clauses), params

def where_merged(start, end, provinsi=None, komoditas=None):
    clauses = ["TRUE"]
    params = {}
    if start:
        clauses.append("m.tanggal >= %(start)s")
        params['start'] = start
    if end:
        clauses.append("m.tanggal <= %(end)s")
        params['end'] = end
    if provinsi and provinsi != 'all':
        clauses.append("m.provinsi = %(provinsi)s")
        params['provinsi'] = provinsi
    if komoditas and komoditas != 'all':
        clauses.append("m.komoditas = %(komoditas)s")
        params['komoditas'] = komoditas
    return " AND ".join(clauses), params

# ─── KPI ───

def query_kpi(start, end, provinsi, komoditas):
    w, p = where_clause(start, end, provinsi, komoditas)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"SELECT ROUND(AVG(harga)) FROM harga_pangan_raw WHERE harga > 0 AND {w}", p)
    avg_harga = cur.fetchone()[0]
    cur.execute(f"SELECT COUNT(DISTINCT komoditas) FROM harga_pangan_raw WHERE {w}", p)
    komoditas_count = cur.fetchone()[0]
    cur.execute(f"SELECT COUNT(*) FROM alerts WHERE severity = 'CRITICAL'")
    alerts = cur.fetchone()[0]
    cur.execute(f"SELECT COUNT(*) FROM predictions WHERE prediksi_label = 'STABIL'")
    stabil = cur.fetchone()[0]
    cur.close()
    conn.close()
    return {
        'avg_harga': float(avg_harga) if avg_harga else 0,
        'komoditas_count': komoditas_count,
        'alerts': alerts,
        'prediksi_stabil': stabil,
    }

# ─── HARGA ───

def query_top10(start, end, provinsi, komoditas):
    w, p = where_clause(start, end, provinsi, komoditas)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT komoditas, ROUND(AVG(harga)) as value
        FROM harga_pangan_raw WHERE harga > 0 AND {w}
        GROUP BY komoditas ORDER BY value DESC LIMIT 10
    """, p)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{'komoditas': r[0], 'value': float(r[1])} for r in rows]

def query_tren(start, end, provinsi, komoditas):
    w, p = where_clause(start, end, provinsi, komoditas)
    conn = get_conn()
    cur = conn.cursor()
    if komoditas and komoditas != 'all':
        cur.execute(f"""
            SELECT tanggal, komoditas, ROUND(AVG(harga)) as value
            FROM harga_pangan_raw WHERE harga > 0 AND {w}
            GROUP BY tanggal, komoditas ORDER BY tanggal
        """, p)
    else:
        cur.execute(f"""
            SELECT tanggal, komoditas, ROUND(AVG(harga)) as value
            FROM harga_pangan_raw
            WHERE harga > 0 AND komoditas IN ('Beras Medium','Beras Premium','Cabai Merah Besar','Cabai Rawit Merah','Daging Sapi Paha Belakang','Minyak Goreng Sawit Curah')
            AND {w}
            GROUP BY tanggal, komoditas ORDER BY tanggal
        """, p)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    result = {}
    for t, kom, val in rows:
        iso = t.isoformat() if hasattr(t, 'isoformat') else str(t)
        if kom not in result:
            result[kom] = {'name': kom, 'data': []}
        result[kom]['data'].append([iso, float(val)])
    return list(result.values())

def query_heatmap(start, end, provinsi, komoditas):
    w, p = where_merged(start, end, provinsi, komoditas)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT komoditas,
            ROUND(AVG(CASE WHEN EXTRACT(MONTH FROM m.tanggal)=1 THEN m.harga_change_pct END)::numeric, 1) AS jan,
            ROUND(AVG(CASE WHEN EXTRACT(MONTH FROM m.tanggal)=2 THEN m.harga_change_pct END)::numeric, 1) AS feb,
            ROUND(AVG(CASE WHEN EXTRACT(MONTH FROM m.tanggal)=3 THEN m.harga_change_pct END)::numeric, 1) AS mar,
            ROUND(AVG(CASE WHEN EXTRACT(MONTH FROM m.tanggal)=4 THEN m.harga_change_pct END)::numeric, 1) AS apr,
            ROUND(AVG(CASE WHEN EXTRACT(MONTH FROM m.tanggal)=5 THEN m.harga_change_pct END)::numeric, 1) AS may
        FROM cuaca_harga_merged m
        WHERE m.harga_change_pct IS NOT NULL AND {w}
        GROUP BY m.komoditas ORDER BY m.komoditas
    """, p)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{'komoditas': r[0], 'Jan': r[1], 'Feb': r[2], 'Mar': r[3], 'Apr': r[4], 'May': r[5]} for r in rows]

def query_volatilitas(start, end, provinsi, komoditas):
    w, p = where_clause(start, end, provinsi, komoditas)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT komoditas, ROUND(STDDEV(harga)) as value
        FROM harga_pangan_raw WHERE harga > 0 AND {w}
        GROUP BY komoditas ORDER BY value DESC
    """, p)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{'komoditas': r[0], 'value': float(r[1])} for r in rows]

# ─── WILAYAH ───

def query_ranking_provinsi(start, end, provinsi, komoditas):
    w1, p1 = where_clause(start, end, provinsi, komoditas)
    w2, p2 = where_merged(start, end, provinsi, komoditas)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT {prov_case()} AS provinsi,
            ROUND(AVG(p.harga)) AS avg_harga,
            COUNT(DISTINCT p.komoditas) AS komoditas,
            COUNT(DISTINCT p.kab_kota) AS kab_kota,
            ROUND(AVG(m.harga_change_pct)::numeric, 1) AS avg_change
        FROM harga_pangan_raw p
        LEFT JOIN cuaca_harga_merged m ON p.tanggal = m.tanggal AND p.kab_kota = m.kab_kota AND p.komoditas = m.komoditas
        WHERE p.harga > 0 AND {w1}
        GROUP BY p.provinsi ORDER BY avg_harga DESC
    """, {**p1, **p2})
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{'provinsi': r[0], 'avg_harga': float(r[1]), 'komoditas': r[2], 'kab_kota': r[3], 'avg_change': float(r[4]) if r[4] else 0} for r in rows]

def query_detail_kabkota(start, end, provinsi, komoditas):
    w, p = where_clause(start, end, provinsi, komoditas)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT p.kab_kota, {prov_case()} AS prov, p.komoditas,
            ROUND(AVG(p.harga)) AS harga, COUNT(*) AS hari
        FROM harga_pangan_raw p
        WHERE p.harga > 0 AND {w}
        GROUP BY p.kab_kota, p.provinsi, p.komoditas
        HAVING COUNT(*) > 5
        ORDER BY harga DESC LIMIT 50
    """, p)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{'kab_kota': r[0], 'provinsi': r[1], 'komoditas': r[2], 'harga': float(r[3]), 'hari': r[4]} for r in rows]

# ─── CUACA ───

def query_scatter_hujan(start, end, provinsi, komoditas):
    w, p = where_merged(start, end, provinsi, komoditas)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT m.curah_hujan_mm AS x, m.harga AS y, m.komoditas
        FROM cuaca_harga_merged m
        WHERE m.curah_hujan_mm > 0 AND m.harga > 0 AND {w}
        ORDER BY RANDOM() LIMIT 3000
    """, p)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{'x': float(r[0]), 'y': float(r[1]), 'komoditas': r[2]} for r in rows]

def query_scatter_suhu(start, end, provinsi, komoditas):
    w, p = where_merged(start, end, provinsi, komoditas)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT m.suhu_mean AS x, m.harga AS y, m.komoditas
        FROM cuaca_harga_merged m
        WHERE m.harga > 0 AND {w}
        ORDER BY RANDOM() LIMIT 3000
    """, p)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{'x': float(r[0]), 'y': float(r[1]), 'komoditas': r[2]} for r in rows]

def query_korelasi(start, end, provinsi, komoditas):
    w, p = where_merged(start, end, provinsi, komoditas)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT ROUND(CORR(suhu_mean, harga)::numeric, 4),
               ROUND(CORR(curah_hujan_mm, harga)::numeric, 4),
               ROUND(CORR(kelembapan, harga)::numeric, 4)
        FROM cuaca_harga_merged m
        WHERE m.suhu_mean IS NOT NULL AND m.harga > 0 AND {w}
    """, p)
    r = cur.fetchone()
    cur.close()
    conn.close()
    return {
        'suhu_harga': float(r[0]) if r and r[0] else 0,
        'hujan_harga': float(r[1]) if r and r[1] else 0,
        'lembab_harga': float(r[2]) if r and r[2] else 0,
    }

def query_cuaca_realtime():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT kab_kota, {prov_case} AS prov,
            ROUND(suhu_mean::numeric,1) AS suhu_mean,
            ROUND(curah_hujan_mm::numeric,1) AS hujan_mm,
            ROUND(kelembapan::numeric,0) AS lembab,
            ROUND(kecepatan_angin::numeric,1) AS angin,
            cluster_nama, waktu::text
        FROM cuaca_realtime ORDER BY waktu DESC LIMIT 30
    """.format(prov_case=prov_case()))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{'kab_kota': r[0], 'provinsi': r[1], 'suhu_mean': float(r[2]) if r[2] else 0,
             'hujan_mm': float(r[3]) if r[3] else 0, 'lembab': float(r[4]) if r[4] else 0,
             'angin': float(r[5]) if r[5] else 0, 'cluster_nama': r[6], 'waktu': r[7]} for r in rows]

# ─── ML ───

def query_prediksi_distribusi():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT prediction_label, COUNT(*)::int FROM predictions GROUP BY prediction_label ORDER BY prediction_label")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{'label': r[0], 'value': r[1]} for r in rows]

def query_cluster_distribusi():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT CONCAT('Cluster ', cluster_label::text), COUNT(*)::int FROM predictions WHERE cluster_label IS NOT NULL GROUP BY cluster_label ORDER BY cluster_label")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{'label': r[0], 'value': r[1]} for r in rows]

def query_risiko():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM alerts WHERE severity = 'CRITICAL'")
    alert_count = cur.fetchone()[0]
    cur.close()
    conn.close()
    return {'alert_count': alert_count}

def query_ranking_kenaikan(start, end, provinsi, komoditas):
    w, p = where_merged(start, end, provinsi, komoditas)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT {prov_case()} AS provinsi, ROUND(AVG(harga_change_pct)::numeric, 1) AS avg_change
        FROM cuaca_harga_merged m
        WHERE harga_change_pct IS NOT NULL AND {w}
        GROUP BY m.provinsi ORDER BY avg_change DESC
    """, p)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{'provinsi': r[0], 'avg_change': float(r[1]) if r[1] else 0} for r in rows]

def query_prediksi_per_hari():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT tanggal_prediksi, COUNT(*)::int, prediksi_label
        FROM predictions GROUP BY tanggal_prediksi, prediksi_label ORDER BY tanggal_prediksi
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    result = {}
    for t, cnt, label in rows:
        iso = t.isoformat() if hasattr(t, 'isoformat') else str(t)
        if label not in result:
            result[label] = {'name': label, 'data': []}
        result[label]['data'].append([iso, cnt])
    return list(result.values())

# ─── INSIGHTS ───

def query_insights(start, end, provinsi, komoditas):
    w, p = where_clause(start, end, provinsi, komoditas)
    wm, pm = where_merged(start, end, provinsi, komoditas)
    conn = get_conn()
    cur = conn.cursor()
    insights = []

    cur.execute(f"""
        SELECT komoditas, {prov_case()}, ROUND(harga_change_pct::numeric, 1)
        FROM cuaca_harga_merged WHERE harga_change_pct > 10 AND {wm}
        ORDER BY harga_change_pct DESC LIMIT 1
    """, pm)
    r = cur.fetchone()
    if r:
        insights.append({
            'type': 'warning', 'emoji': '🔺',
            'text': f"{r[0]} naik {r[2]}% di {r[1]}. Waspada potensi kenaikan lanjutan."
        })

    cur.execute("SELECT alert_type, komoditas, provinsi FROM alerts ORDER BY created_at DESC LIMIT 1")
    r = cur.fetchone()
    if r:
        insights.append({
            'type': 'alert', 'emoji': '🚨',
            'text': f"Alert terbaru: {r[0]} untuk {r[1]} di {r[2] or 'seluruh wilayah'}."
        })

    cur.execute("SELECT COUNT(*) FROM alerts")
    alert_total = cur.fetchone()[0]
    if alert_total >= 3:
        insights.append({
            'type': 'alert', 'emoji': '🚨',
            'text': f"{alert_total} alert aktif. Segera periksa komoditas dengan harga spike."
        })

    kur, kp = where_merged(start, end, provinsi, komoditas)
    cur.execute(f"""
        SELECT ROUND(CORR(suhu_mean, harga)::numeric, 4) FROM cuaca_harga_merged m
        WHERE m.suhu_mean IS NOT NULL AND m.harga > 0 AND {kur}
    """, kp)
    r = cur.fetchone()
    corr = float(r[0]) if r and r[0] else 0
    if abs(corr) < 0.1:
        insights.append({
            'type': 'info', 'emoji': '🌤',
            'text': "Korelasi cuaca vs harga sangat lemah. Faktor lain lebih memengaruhi harga."
        })

    cur.execute("SELECT COUNT(*) FROM predictions WHERE prediksi_label = 'STABIL'")
    stabil = cur.fetchone()[0]
    total_pred = stabil
    cur.execute("SELECT COUNT(*) FROM predictions")
    total_pred = cur.fetchone()[0]
    if total_pred > 0:
        pct = round(stabil / total_pred * 100, 1)
        insights.append({
            'type': 'success', 'emoji': '✅',
            'text': f"{pct}% harga diprediksi stabil oleh model ML."
        })

    if provinsi and provinsi != 'all':
        cur.execute(f"""
            SELECT COUNT(DISTINCT kab_kota), COUNT(DISTINCT komoditas)
            FROM harga_pangan_raw WHERE {w}
        """, p)
        r = cur.fetchone()
        if r:
            insights.append({
                'type': 'info', 'emoji': '🎯',
                'text': f"Menampilkan data untuk {prov_name(provinsi)} — {r[0]} kab/kota, {r[1]} komoditas."
            })

    cur.close()
    conn.close()
    return insights

# ─── EXPORT ───

def query_export_csv(start, end, provinsi, komoditas):
    w, p = where_clause(start, end, provinsi, komoditas)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT tanggal, {prov_case()} AS provinsi, kab_kota, komoditas, harga, satuan
        FROM harga_pangan_raw WHERE harga > 0 AND {w}
        ORDER BY tanggal, komoditas LIMIT 50000
    """, p)
    rows = cur.fetchall()
    cols = [desc[0] for desc in cur.description]
    cur.close()
    conn.close()
    return cols, rows

# ─── FILTER OPTIONS ───

def query_filter_options():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT provinsi FROM harga_pangan_raw ORDER BY provinsi")
    provinsi = [{'kode': r[0], 'nama': prov_name(r[0])} for r in cur.fetchall()]
    cur.execute("SELECT DISTINCT komoditas FROM harga_pangan_raw ORDER BY komoditas")
    komoditas = [r[0] for r in cur.fetchall()]
    cur.execute("SELECT MIN(tanggal), MAX(tanggal) FROM harga_pangan_raw")
    r = cur.fetchone()
    date_range = {'min': r[0].isoformat() if r[0] else None, 'max': r[1].isoformat() if r[1] else None}
    cur.close()
    conn.close()
    return {'provinsi': provinsi, 'komoditas': komoditas, 'date_range': date_range}
