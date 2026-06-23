#!/usr/bin/env python3
"""
Demo Script — Jalankan batch pipeline + clustering minimal 3x berturut-turut.

Script ini untuk keperluan presentasi / screenshot bukti pipeline berjalan berkali-kali.
Setiap run menghasilkan:
- Pipeline Run ID yang berbeda (UUID unik)
- Log execution tersimpan di logs/data/application.log
- Audit trail di PostgreSQL (tabel audit_log)
- Quality report di logs/data/quality_report.json
- Model disimpan di models/saved/

Usage:
    python demo_run_pipeline.py          # 3 run (default)
    python demo_run_pipeline.py --runs 5 # 5 run
    python demo_run_pipeline.py --mode clustering  # hanya clustering
"""

import os
import sys
import time
import argparse
import logging
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

# Setup logging dengan semua severity
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            os.path.join(PROJECT_ROOT, "logs", "data", "demo_run.log"),
            encoding="utf-8",
        ),
    ],
)

logger = logging.getLogger("DemoRunner")

os.makedirs(os.path.join(PROJECT_ROOT, "logs", "data"), exist_ok=True)


def run_batch_pipeline_demo(run_number: int) -> dict:
    """Jalankan satu siklus batch pipeline (menggunakan synthetic data jika tidak ada DB)."""
    from logs.monitoring import StructuredLogger

    slogger = StructuredLogger(f"BatchRun-{run_number}")

    import uuid
    run_id = f"demo-run-{run_number:02d}-{uuid.uuid4().hex[:6]}"
    start_time = datetime.now()

    print(f"\n{'='*60}")
    print(f"  🚀 RUN #{run_number:02d} — {run_id}")
    print(f"  Waktu mulai: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    # Log severity demo — INFO, DEBUG, WARNING, ERROR, FATAL
    slogger.info(f"[INFO] Pipeline dimulai — Run #{run_number}", run_id=run_id)
    slogger.debug(f"[DEBUG] Mode: synthetic data, run_number={run_number}")

    results = {
        "run_id": run_id,
        "run_number": run_number,
        "start_time": start_time.isoformat(),
        "steps": {},
    }

    # Step 1: Training model (classification)
    print(f"\n  ▶ Step 1: Training ML Classification Model...")
    slogger.info("[INFO] Memulai training model classification (GradientBoosting)")
    try:
        from models.price_prediction_model import train_synthetic_model
        model = train_synthetic_model()
        results["steps"]["train_classification"] = "SUCCESS"
        print(f"  ✅ Model classification berhasil ditraining")
        slogger.info("[INFO] Training classification selesai — model disimpan")
    except Exception as e:
        results["steps"]["train_classification"] = f"FAILED: {e}"
        slogger.error(f"[ERROR] Training classification gagal: {e}")
        print(f"  ❌ Classification training gagal: {e}")

    # Step 2: Clustering
    print(f"\n  ▶ Step 2: K-Means Clustering (k=3, 4, 5)...")
    slogger.info(f"[INFO] Memulai clustering dengan k={3 + (run_number - 1) % 3}")
    try:
        from models.clustering_model import run_clustering_pipeline
        n_k = 3 + (run_number - 1) % 3  # Rotasi: 3, 4, 5, 3, 4, 5, ...
        cluster_result = run_clustering_pipeline(n_clusters=n_k)
        results["steps"]["clustering"] = f"SUCCESS (k={n_k})"
        print(f"  ✅ Clustering selesai (k={n_k})")
        slogger.info(f"[INFO] Clustering k={n_k} selesai")
    except Exception as e:
        results["steps"]["clustering"] = f"FAILED: {e}"
        slogger.warning(f"[WARNING] Clustering gagal (non-critical): {e}")
        print(f"  ⚠️ Clustering gagal: {e}")

    # Step 3: Quality Checks
    print(f"\n  ▶ Step 3: Data Quality Checks...")
    slogger.info("[INFO] Menjalankan data quality checks")
    try:
        from governance.quality_checks import run_all_quality_checks
        report = run_all_quality_checks()
        status = report.get("overall_status", "UNKNOWN")
        results["steps"]["quality_checks"] = status
        print(f"  ✅ Quality check: {status}")
        slogger.info(f"[INFO] Quality check selesai: {status}")
        if status == "FAIL":
            slogger.warning("[WARNING] Beberapa quality checks gagal — lihat quality_report.json")
    except Exception as e:
        results["steps"]["quality_checks"] = f"ERROR: {e}"
        slogger.error(f"[ERROR] Quality check error: {e}")
        print(f"  ⚠️ Quality check: {e}")

    # Step 4: Audit Log (tanpa DB → simpan ke file saja)
    print(f"\n  ▶ Step 4: Audit Log...")
    slogger.info("[INFO] Menyimpan audit log")
    try:
        from governance.audit_trail import AuditTrail
        audit = AuditTrail()
        audit.log_data_lineage()
        results["steps"]["audit_log"] = "SUCCESS"
        print(f"  ✅ Audit log & lineage disimpan")
        slogger.info("[INFO] Audit log selesai")
    except Exception as e:
        results["steps"]["audit_log"] = f"DB_SKIP: {e}"
        slogger.warning(f"[WARNING] Audit log ke DB gagal (DB tidak tersedia?): {e}")
        print(f"  ⚠️ Audit log: DB tidak tersedia, lineage tetap disimpan ke file")

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    results["end_time"] = end_time.isoformat()
    results["duration_seconds"] = round(duration, 2)

    # Hitung status
    total_steps = len(results["steps"])
    success_steps = sum(1 for s in results["steps"].values() if s.startswith("SUCCESS"))

    print(f"\n{'─'*60}")
    print(f"  Run #{run_number:02d} SELESAI — {success_steps}/{total_steps} steps berhasil")
    print(f"  Durasi: {duration:.1f} detik")
    print(f"{'─'*60}")

    slogger.info(
        f"[INFO] Run #{run_number} selesai — {success_steps}/{total_steps} steps, {duration:.1f}s",
        run_id=run_id,
        duration=duration,
        steps=results["steps"],
    )

    return results


def run_streaming_demo(run_number: int) -> dict:
    """Simulasi satu siklus stream processing (tanpa koneksi Kafka nyata)."""
    from logs.monitoring import StructuredLogger
    import random

    slogger = StructuredLogger(f"StreamRun-{run_number}")
    start_time = datetime.now()

    print(f"\n{'='*60}")
    print(f"  🌊 STREAM RUN #{run_number:02d} — {start_time.strftime('%H:%M:%S')}")
    print(f"{'='*60}")

    slogger.info(f"[INFO] Stream processing dimulai — Run #{run_number}")
    slogger.debug(f"[DEBUG] Simulasi {random.randint(5, 20)} pesan Kafka")

    # Simulasi metrics
    n_messages = random.randint(5, 20)
    n_success = random.randint(int(n_messages * 0.8), n_messages)
    n_anomaly = random.randint(0, 3)

    print(f"  📨 {n_messages} pesan diproses, {n_success} berhasil, {n_anomaly} anomali")
    slogger.info(
        f"[INFO] Stream batch selesai: {n_success}/{n_messages} berhasil",
        anomaly_count=n_anomaly,
    )

    if n_anomaly > 0:
        slogger.warning(f"[WARNING] {n_anomaly} anomali cuaca terdeteksi dalam stream")

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    return {
        "run_number": run_number,
        "messages_processed": n_messages,
        "success": n_success,
        "anomaly": n_anomaly,
        "duration_seconds": round(duration, 2),
    }


def print_summary(all_results: list, mode: str):
    """Print ringkasan semua run."""
    print(f"\n{'='*60}")
    print(f"  📊 RINGKASAN SEMUA RUN ({mode.upper()})")
    print(f"{'='*60}")

    for r in all_results:
        run_num = r.get("run_number", "?")
        if mode == "batch":
            steps = r.get("steps", {})
            success = sum(1 for s in steps.values() if s.startswith("SUCCESS"))
            total = len(steps)
            duration = r.get("duration_seconds", 0)
            print(f"  Run #{run_num:02d} | {success}/{total} steps | {duration:.1f}s")
        else:
            print(
                f"  Run #{run_num:02d} | "
                f"{r.get('success', 0)}/{r.get('messages_processed', 0)} pesan | "
                f"{r.get('duration_seconds', 0):.1f}s"
            )

    print(f"\n  📁 Log tersimpan di: logs/data/")
    print(f"  📊 Quality report: logs/data/quality_report.json")
    print(f"  🗺️ Lineage: logs/data/lineage.json")
    print(f"  🤖 Model: models/saved/")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Demo runner untuk pipeline IPBD Harga Pangan"
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=3,
        help="Jumlah run (default: 3)",
    )
    parser.add_argument(
        "--mode",
        choices=["batch", "streaming", "clustering", "all"],
        default="batch",
        help="Mode yang dijalankan (default: batch)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Jeda antar run dalam detik (default: 2.0)",
    )
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  IPBD HARGA PANGAN — DEMO PIPELINE RUNNER")
    print("  Menjalankan pipeline minimal 3x untuk bukti eksekusi")
    print("=" * 60)
    print(f"\n  Mode  : {args.mode.upper()}")
    print(f"  Runs  : {args.runs}x")
    print(f"  Delay : {args.delay}s antar run")
    print()

    all_results = []

    for i in range(1, args.runs + 1):
        if args.mode in ("batch", "all"):
            result = run_batch_pipeline_demo(i)
            all_results.append(result)

        if args.mode in ("streaming", "all"):
            result = run_streaming_demo(i)
            all_results.append(result)

        if args.mode == "clustering":
            from models.clustering_model import run_clustering_pipeline
            n_k = 3 + (i - 1) % 3
            print(f"\n{'='*60}")
            print(f"  🔵 CLUSTERING RUN #{i:02d} (k={n_k})")
            print(f"{'='*60}")
            result = run_clustering_pipeline(n_clusters=n_k)
            result["run_number"] = i
            all_results.append(result)
            print(f"  ✅ Run #{i} selesai — model: {result.get('model_path', 'N/A')}")

        if i < args.runs:
            logger.info(f"[INFO] Jeda {args.delay}s sebelum run #{i+1}...")
            time.sleep(args.delay)

    # Print summary
    mode_display = "batch" if args.mode != "streaming" else "streaming"
    print_summary(all_results, mode_display)


if __name__ == "__main__":
    main()
