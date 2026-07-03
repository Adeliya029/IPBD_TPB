import csv
import io
from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from queries import (
    query_kpi, query_top10, query_tren, query_heatmap, query_volatilitas,
    query_ranking_provinsi, query_detail_kabkota,
    query_scatter_hujan, query_scatter_suhu, query_korelasi, query_cuaca_realtime,
    query_prediksi_distribusi, query_cluster_distribusi, query_risiko,
    query_ranking_kenaikan, query_prediksi_per_hari,
    query_insights, query_export_csv, query_filter_options,
)

app = FastAPI(title="IPBD Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def filters(start: str = None, end: str = None, provinsi: str = None, komoditas: str = None):
    return start, end, provinsi, komoditas

@app.get("/api/filter-options")
def get_filter_options():
    return query_filter_options()

@app.get("/api/kpi")
def get_kpi(start: str = None, end: str = None, provinsi: str = None, komoditas: str = None):
    return query_kpi(start, end, provinsi, komoditas)

@app.get("/api/harga/top10")
def get_top10(start: str = None, end: str = None, provinsi: str = None, komoditas: str = None):
    return query_top10(start, end, provinsi, komoditas)

@app.get("/api/harga/tren")
def get_tren(start: str = None, end: str = None, provinsi: str = None, komoditas: str = None):
    return query_tren(start, end, provinsi, komoditas)

@app.get("/api/harga/heatmap")
def get_heatmap(start: str = None, end: str = None, provinsi: str = None, komoditas: str = None):
    return query_heatmap(start, end, provinsi, komoditas)

@app.get("/api/harga/volatilitas")
def get_volatilitas(start: str = None, end: str = None, provinsi: str = None, komoditas: str = None):
    return query_volatilitas(start, end, provinsi, komoditas)

@app.get("/api/wilayah/ranking")
def get_ranking_provinsi(start: str = None, end: str = None, provinsi: str = None, komoditas: str = None):
    return query_ranking_provinsi(start, end, provinsi, komoditas)

@app.get("/api/wilayah/detail")
def get_detail_kabkota(start: str = None, end: str = None, provinsi: str = None, komoditas: str = None):
    return query_detail_kabkota(start, end, provinsi, komoditas)

@app.get("/api/cuaca/scatter-hujan")
def get_scatter_hujan(start: str = None, end: str = None, provinsi: str = None, komoditas: str = None):
    return query_scatter_hujan(start, end, provinsi, komoditas)

@app.get("/api/cuaca/scatter-suhu")
def get_scatter_suhu(start: str = None, end: str = None, provinsi: str = None, komoditas: str = None):
    return query_scatter_suhu(start, end, provinsi, komoditas)

@app.get("/api/cuaca/korelasi")
def get_korelasi(start: str = None, end: str = None, provinsi: str = None, komoditas: str = None):
    return query_korelasi(start, end, provinsi, komoditas)

@app.get("/api/cuaca/realtime")
def get_realtime():
    return query_cuaca_realtime()

@app.get("/api/ml/prediksi")
def get_prediksi():
    return query_prediksi_distribusi()

@app.get("/api/ml/cluster")
def get_cluster():
    return query_cluster_distribusi()

@app.get("/api/ml/risiko")
def get_risiko():
    return query_risiko()

@app.get("/api/ml/ranking-kenaikan")
def get_ranking_kenaikan(start: str = None, end: str = None, provinsi: str = None, komoditas: str = None):
    return query_ranking_kenaikan(start, end, provinsi, komoditas)

@app.get("/api/ml/prediksi-per-hari")
def get_prediksi_per_hari():
    return query_prediksi_per_hari()

@app.get("/api/insights")
def get_insights(start: str = None, end: str = None, provinsi: str = None, komoditas: str = None):
    return query_insights(start, end, provinsi, komoditas)

@app.get("/api/export/csv")
def export_csv(start: str = None, end: str = None, provinsi: str = None, komoditas: str = None):
    cols, rows = query_export_csv(start, end, provinsi, komoditas)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(cols)
    writer.writerows(rows)
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=harga_pangan.csv"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8050)
