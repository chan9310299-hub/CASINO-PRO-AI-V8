"""Database migration — safe schema upgrades, no data deletion."""

import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

MIGRATION_VERSION = 7

REQUIRED_TABLES = (
    "results",
    "ai_prediction_history",
    "ai_signal_weights",
    "ai_pattern_memory",
    "ai_learning_history",
    "ai_weight_history",
    "ai_backtest_results",
    "pattern_rank_cache",
    "schema_migrations",
    "ai_v6_metrics",
    "ai_backtest_v6",
    "ai_optimizer_v6",
)

TABLE_DDL = {
    "results": """
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            result TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """,
    "ai_prediction_history": """
        CREATE TABLE IF NOT EXISTS ai_prediction_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            hand_index INTEGER NOT NULL,
            history_snapshot TEXT NOT NULL,
            prediction TEXT NOT NULL,
            confidence REAL NOT NULL,
            weighted_score TEXT NOT NULL,
            signal_breakdown_json TEXT NOT NULL,
            reason_json TEXT NOT NULL,
            actual_result TEXT,
            is_correct INTEGER
        )
    """,
    "ai_signal_weights": """
        CREATE TABLE IF NOT EXISTS ai_signal_weights (
            signal_name TEXT PRIMARY KEY,
            weight REAL NOT NULL,
            total INTEGER DEFAULT 0,
            correct INTEGER DEFAULT 0,
            wrong INTEGER DEFAULT 0,
            accuracy REAL DEFAULT 0,
            updated_at TEXT
        )
    """,
    "ai_pattern_memory": """
        CREATE TABLE IF NOT EXISTS ai_pattern_memory (
            pattern_key TEXT PRIMARY KEY,
            pattern_length INTEGER,
            next_p INTEGER DEFAULT 0,
            next_b INTEGER DEFAULT 0,
            total INTEGER DEFAULT 0,
            p_rate REAL DEFAULT 0,
            b_rate REAL DEFAULT 0,
            updated_at TEXT
        )
    """,
    "ai_learning_history": """
        CREATE TABLE IF NOT EXISTS ai_learning_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            overall_accuracy REAL,
            best_signal TEXT,
            worst_signal TEXT,
            avg_confidence REAL
        )
    """,
    "ai_weight_history": """
        CREATE TABLE IF NOT EXISTS ai_weight_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            optimization_time TEXT NOT NULL,
            old_weights_json TEXT NOT NULL,
            new_weights_json TEXT NOT NULL,
            accuracy_before REAL,
            accuracy_after REAL,
            resolved_count INTEGER DEFAULT 0
        )
    """,
    "ai_backtest_results": """
        CREATE TABLE IF NOT EXISTS ai_backtest_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            window_size INTEGER NOT NULL,
            accuracy REAL,
            avg_losing_streak REAL,
            max_losing_streak INTEGER,
            pass_rate REAL,
            prediction_count INTEGER,
            win_count INTEGER,
            loss_count INTEGER,
            best_signal TEXT,
            worst_signal TEXT
        )
    """,
    "pattern_rank_cache": """
        CREATE TABLE IF NOT EXISTS pattern_rank_cache (
            pattern_key TEXT PRIMARY KEY,
            pattern_length INTEGER,
            occurrences INTEGER DEFAULT 0,
            next_p INTEGER DEFAULT 0,
            next_b INTEGER DEFAULT 0,
            p_rate REAL DEFAULT 0,
            b_rate REAL DEFAULT 0,
            confidence REAL DEFAULT 0,
            last_seen TEXT
        )
    """,
    "schema_migrations": """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version INTEGER NOT NULL,
            applied_at TEXT NOT NULL,
            notes TEXT
        )
    """,
    "ai_v6_metrics": """
        CREATE TABLE IF NOT EXISTS ai_v6_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hand_index INTEGER,
            created_at TEXT NOT NULL,
            risk_score REAL,
            risk_level TEXT,
            road_agreement REAL,
            pattern_similarity REAL,
            meta_score REAL,
            pass_flag INTEGER DEFAULT 0,
            losing_streak INTEGER DEFAULT 0,
            prediction_quality TEXT
        )
    """,
    "ai_backtest_v6": """
        CREATE TABLE IF NOT EXISTS ai_backtest_v6 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            window_size INTEGER NOT NULL,
            accuracy REAL,
            avg_losing_streak REAL,
            max_losing_streak INTEGER,
            pass_rate REAL,
            win_count INTEGER,
            loss_count INTEGER
        )
    """,
    "ai_optimizer_v6": """
        CREATE TABLE IF NOT EXISTS ai_optimizer_v6 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            optimization_time TEXT NOT NULL,
            old_weights_json TEXT NOT NULL,
            new_weights_json TEXT NOT NULL,
            accuracy_before REAL,
            accuracy_after REAL,
            resolved_count INTEGER
        )
    """,
}


def _table_exists(cur, name: str) -> bool:
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    )
    return cur.fetchone() is not None


def get_current_version(conn) -> int:
    cur = conn.cursor()
    if not _table_exists(cur, "schema_migrations"):
        return 0
    cur.execute("SELECT MAX(version) FROM schema_migrations")
    row = cur.fetchone()
    return int(row[0]) if row and row[0] is not None else 0


def verify_tables(conn) -> Dict[str, bool]:
    cur = conn.cursor()
    return {name: _table_exists(cur, name) for name in REQUIRED_TABLES}


def ensure_all_tables(conn) -> None:
    cur = conn.cursor()
    for ddl in TABLE_DDL.values():
        cur.execute(ddl)
    cur.execute("""
        CREATE VIEW IF NOT EXISTS history AS
        SELECT id, result, created_at FROM results
    """)


def run_migrations(conn, backup_fn=None) -> Dict[str, Any]:
    """Run safe migrations. backup_fn called before schema changes if provided."""
    current = get_current_version(conn)
    if current >= MIGRATION_VERSION:
        ensure_all_tables(conn)
        conn.commit()
        return {"version": current, "migrated": False}

    if backup_fn:
        backup_fn("pre_migration")

    ensure_all_tables(conn)
    cur = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute(
        "INSERT INTO schema_migrations (version, applied_at, notes) VALUES (?, ?, ?)",
        (MIGRATION_VERSION, now, "final hardening migration"),
    )
    conn.commit()
    return {"version": MIGRATION_VERSION, "migrated": True}


def get_migration_status(conn) -> Dict[str, Any]:
    tables = verify_tables(conn)
    missing = [k for k, v in tables.items() if not v]
    cur = conn.cursor()
    total_rows = 0
    for table in ("results", "ai_prediction_history", "ai_pattern_memory"):
        if tables.get(table):
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                total_rows += cur.fetchone()[0]
            except sqlite3.Error:
                pass
    return {
        "version": get_current_version(conn),
        "target_version": MIGRATION_VERSION,
        "tables_ok": len(missing) == 0,
        "missing_tables": missing,
        "total_stored_rows": total_rows,
        "status": "OK" if not missing else "NEEDS_MIGRATION",
    }
