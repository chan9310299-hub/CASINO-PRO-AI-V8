"""Export / import helpers."""

import csv
import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from config import DATA_DIR, DB_PATH, EXPORT_DIR


def ensure_export_dir():
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)


def export_db_copy() -> Path:
    ensure_export_dir()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = EXPORT_DIR / f"casino_ai_export_{stamp}.db"
    if DB_PATH.exists():
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute("PRAGMA wal_checkpoint(FULL)")
            conn.close()
        except sqlite3.Error:
            pass
        shutil.copy2(DB_PATH, dest)
    else:
        dest.touch()
    return dest


def export_history_csv(db) -> Path:
    ensure_export_dir()
    path = EXPORT_DIR / "history.csv"
    rows = db.get_results()
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["index", "result"])
        for i, r in enumerate(rows, 1):
            writer.writerow([i, r])
    return path


def export_predictions_csv(db) -> Path:
    ensure_export_dir()
    path = EXPORT_DIR / "ai_prediction_history.csv"
    rows = db.get_all_predictions()
    fields = [
        "id", "created_at", "hand_index", "prediction", "confidence",
        "actual_result", "is_correct",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k) for k in fields})
    return path


def import_db_safe(source: Path, backup_fn) -> Dict[str, Any]:
    if not source.exists():
        return {"ok": False, "error": "file not found"}
    if backup_fn:
        backup_fn("pre_import")
    for suffix in ("-wal", "-shm"):
        sidecar = Path(str(DB_PATH) + suffix)
        if sidecar.exists():
            sidecar.unlink()
    shutil.copy2(source, DB_PATH)
    return {"ok": True, "path": str(source)}
