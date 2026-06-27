"""SQLite → PostgreSQL migration — CASINO PRO AI v12."""

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, Optional

from database import Database


def _checksum(results_count: int, predictions_count: int, patterns_count: int) -> str:
    raw = f"{results_count}:{predictions_count}:{patterns_count}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _migration_already_done(pg_db, checksum: str) -> bool:
    try:
        cur = pg_db.conn.cursor()
        cur.execute(
            "SELECT 1 FROM cloud_migration_log WHERE checksum = %s LIMIT 1",
            (checksum,),
        )
        return cur.fetchone() is not None
    except Exception:
        return False


def migrate_sqlite_to_postgres(
    sqlite_db: Optional[Database] = None,
    pg_db=None,
    source_tag: str = "local_sqlite",
) -> Dict[str, Any]:
    sqlite_db = sqlite_db or Database()
    if pg_db is None:
        from storage import get_storage_backend

        backend = get_storage_backend(force_cloud=True)
        pg_db = backend.db

    results = sqlite_db.get_results() or []
    predictions = sqlite_db.get_all_predictions() or []
    patterns = []
    try:
        sqlite_db.ensure_adaptive_learning_tables()
        cur = sqlite_db.conn.cursor()
        cur.execute("SELECT * FROM ai_pattern_memory")
        patterns = [dict(row) for row in cur.fetchall()]
    except Exception:
        patterns = []

    checksum = _checksum(len(results), len(predictions), len(patterns))
    if _migration_already_done(pg_db, checksum):
        return {
            "ok": True,
            "skipped": True,
            "message": "이미 동일 데이터가 이전되었습니다.",
            "results_imported": 0,
            "predictions_imported": 0,
            "patterns_imported": 0,
            "checksum": checksum,
        }

    try:
        from backup_manager import backup_database
        backup_database("pre_cloud_migration")
    except Exception:
        pass

    results_imported = 0
    predictions_imported = 0
    patterns_imported = 0

    pg_cur = pg_db.conn.cursor()

    pg_cur.execute("SELECT COUNT(*) AS c FROM results")
    existing_results = int(pg_cur.fetchone()["c"])

    if existing_results == 0:
        sqlite_cur = sqlite_db.conn.cursor()
        sqlite_cur.execute("SELECT result, created_at FROM results ORDER BY id ASC")
        for row in sqlite_cur.fetchall():
            pg_cur.execute(
                "INSERT INTO results (result, created_at) VALUES (%s, %s)",
                (row["result"], row["created_at"]),
            )
            results_imported += 1
    else:
        results_imported = existing_results

    for pred in predictions:
        pg_cur.execute(
            "SELECT 1 FROM ai_prediction_history WHERE hand_index = %s LIMIT 1",
            (pred["hand_index"],),
        )
        if pg_cur.fetchone():
            continue
        pg_cur.execute(
            """
            INSERT INTO ai_prediction_history (
                created_at, hand_index, history_snapshot, prediction, confidence,
                weighted_score, signal_breakdown_json, reason_json,
                actual_result, is_correct
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                pred.get("created_at"),
                pred.get("hand_index"),
                pred.get("history_snapshot"),
                pred.get("prediction"),
                pred.get("confidence"),
                pred.get("weighted_score"),
                pred.get("signal_breakdown_json"),
                pred.get("reason_json"),
                pred.get("actual_result"),
                pred.get("is_correct"),
            ),
        )
        predictions_imported += 1

    for pat in patterns:
        pg_cur.execute(
            "SELECT 1 FROM ai_pattern_memory WHERE pattern_key = %s LIMIT 1",
            (pat.get("pattern_key"),),
        )
        if pg_cur.fetchone():
            continue
        pg_cur.execute(
            """
            INSERT INTO ai_pattern_memory (
                pattern_key, pattern_length, next_p, next_b, total,
                p_rate, b_rate, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (pattern_key) DO NOTHING
            """,
            (
                pat.get("pattern_key"),
                pat.get("pattern_length"),
                pat.get("next_p", 0),
                pat.get("next_b", 0),
                pat.get("total", 0),
                pat.get("p_rate", 0),
                pat.get("b_rate", 0),
                pat.get("updated_at"),
            ),
        )
        patterns_imported += 1

    try:
        weights = sqlite_db.get_all_signal_weights()
        for name, weight in weights.items():
            row = sqlite_db.get_signal_weight(name)
            if not row:
                continue
            pg_cur.execute(
                """
                INSERT INTO ai_signal_weights (
                    signal_name, weight, total, correct, wrong, accuracy, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (signal_name) DO UPDATE SET
                    weight = EXCLUDED.weight,
                    total = EXCLUDED.total,
                    correct = EXCLUDED.correct,
                    wrong = EXCLUDED.wrong,
                    accuracy = EXCLUDED.accuracy,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    name, weight, row.get("total", 0), row.get("correct", 0),
                    row.get("wrong", 0), row.get("accuracy", 0), row.get("updated_at"),
                ),
            )
    except Exception:
        pass

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pg_cur.execute(
        """
        INSERT INTO cloud_migration_log (
            source_tag, migrated_at, results_count, predictions_count,
            patterns_count, checksum
        ) VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (checksum) DO NOTHING
        """,
        (
            source_tag, now, len(results), len(predictions), len(patterns), checksum,
        ),
    )
    pg_db.conn.commit()

    return {
        "ok": True,
        "skipped": False,
        "message": "SQLite → 클라우드 DB 이전 완료",
        "results_imported": results_imported,
        "predictions_imported": predictions_imported,
        "patterns_imported": patterns_imported,
        "checksum": checksum,
    }


def get_migration_status(pg_db=None) -> Dict[str, Any]:
    if pg_db is None:
        return {"migrated": False, "last_migration": "—", "checksum": "—"}
    try:
        cur = pg_db.conn.cursor()
        cur.execute(
            """
            SELECT migrated_at, results_count, predictions_count, patterns_count, checksum
            FROM cloud_migration_log
            ORDER BY id DESC LIMIT 1
            """
        )
        row = cur.fetchone()
        if not row:
            return {"migrated": False, "last_migration": "—", "checksum": "—"}
        return {
            "migrated": True,
            "last_migration": row["migrated_at"],
            "results_count": row["results_count"],
            "predictions_count": row["predictions_count"],
            "patterns_count": row["patterns_count"],
            "checksum": row["checksum"],
        }
    except Exception:
        return {"migrated": False, "last_migration": "—", "checksum": "—"}
