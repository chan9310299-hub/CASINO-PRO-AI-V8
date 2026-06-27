"""PostgreSQL cloud database — CASINO PRO AI v12 (Supabase compatible)."""

import json
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from database import LEARNING_SIGNAL_DEFAULTS

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None
    RealDictCursor = None


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class PostgresDatabase:
    """PostgreSQL backend with the same public API as Database."""

    backend = "postgresql"

    def __init__(self, database_url: str):
        if psycopg2 is None:
            raise RuntimeError("psycopg2-binary is required for cloud database")
        self.database_url = database_url
        self.conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        self.conn.autocommit = False
        init_cloud_tables(self.conn)
        self.initialize_default_signal_weights()

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    @contextmanager
    def _connection(self):
        try:
            yield self.conn
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def get_db_status(self) -> Dict[str, Any]:
        try:
            history = self.get_results() or []
            stats = self.get_learning_stats()
            pattern_count = self.get_pattern_memory_count()
            total_rows = len(history) + stats.get("total_predictions", 0) + pattern_count
            return {
                "version": 12,
                "target_version": 12,
                "tables_ok": True,
                "missing_tables": [],
                "total_stored_rows": total_rows,
                "status": "클라우드 연결됨",
                "last_backup": "—",
                "storage_mode": "cloud",
                "cloud_connected": True,
                "last_save_time": self.get_last_save_time(),
                "total_input_hands": len(history),
                "total_ai_predictions": stats.get("total_predictions", 0),
                "pattern_memory_count": pattern_count,
            }
        except Exception:
            return {
                "version": 12,
                "target_version": 12,
                "tables_ok": False,
                "missing_tables": [],
                "total_stored_rows": 0,
                "status": "클라우드 오류",
                "last_backup": "—",
                "storage_mode": "cloud",
                "cloud_connected": False,
                "last_save_time": "—",
            }

    def get_last_save_time(self) -> str:
        try:
            with self._connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT GREATEST(
                        COALESCE((SELECT MAX(created_at) FROM results), ''),
                        COALESCE((SELECT MAX(created_at) FROM ai_prediction_history), ''),
                        COALESCE((SELECT MAX(updated_at) FROM ai_pattern_memory), '')
                    ) AS last_ts
                    """
                )
                row = cur.fetchone()
                return row["last_ts"] or "—"
        except Exception:
            return "—"

    def ensure_adaptive_learning_tables(self, cur=None):
        if cur is not None:
            _create_adaptive_learning_tables(cur)
            self.initialize_default_signal_weights(cur=cur)
            return
        with self._connection() as conn:
            cur = conn.cursor()
            _create_adaptive_learning_tables(cur)
            self.initialize_default_signal_weights(cur=cur)

    def ensure_v6_tables(self, cur=None):
        cursor = cur if cur is not None else self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_v6_metrics (
                id SERIAL PRIMARY KEY,
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
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_backtest_v6 (
                id SERIAL PRIMARY KEY,
                created_at TEXT NOT NULL,
                window_size INTEGER NOT NULL,
                accuracy REAL,
                avg_losing_streak REAL,
                max_losing_streak INTEGER,
                pass_rate REAL,
                win_count INTEGER,
                loss_count INTEGER
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_optimizer_v6 (
                id SERIAL PRIMARY KEY,
                optimization_time TEXT NOT NULL,
                old_weights_json TEXT NOT NULL,
                new_weights_json TEXT NOT NULL,
                accuracy_before REAL,
                accuracy_after REAL,
                resolved_count INTEGER
            )
        """)
        cursor.execute("""
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
        """)
        if cur is None:
            self.conn.commit()

    def initialize_default_signal_weights(self, cur=None):
        now = _now()

        def _insert_defaults(cursor):
            for name, weight in LEARNING_SIGNAL_DEFAULTS.items():
                cursor.execute(
                    """
                    INSERT INTO ai_signal_weights (
                        signal_name, weight, total, correct, wrong, accuracy, updated_at
                    ) VALUES (%s, %s, 0, 0, 0, 0, %s)
                    ON CONFLICT (signal_name) DO NOTHING
                    """,
                    (name, weight, now),
                )

        if cur is not None:
            _insert_defaults(cur)
        else:
            with self._connection() as conn:
                _insert_defaults(conn.cursor())

    def get_all_signal_weights(self):
        self.ensure_adaptive_learning_tables()
        cur = self.conn.cursor()
        cur.execute("SELECT signal_name, weight FROM ai_signal_weights")
        return {row["signal_name"]: row["weight"] for row in cur.fetchall()}

    def get_signal_weight(self, signal_name):
        self.ensure_adaptive_learning_tables()
        cur = self.conn.cursor()
        cur.execute(
            "SELECT * FROM ai_signal_weights WHERE signal_name = %s",
            (signal_name,),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def update_signal_weight(
        self, signal_name, weight, total=None, correct=None, wrong=None, accuracy=None,
    ):
        row = self.get_signal_weight(signal_name)
        if row is None:
            self.initialize_default_signal_weights()
            row = self.get_signal_weight(signal_name)
        if row is None:
            return
        now = _now()
        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE ai_signal_weights
            SET weight = %s, total = %s, correct = %s, wrong = %s,
                accuracy = %s, updated_at = %s
            WHERE signal_name = %s
            """,
            (
                weight if weight is not None else row["weight"],
                total if total is not None else row["total"],
                correct if correct is not None else row["correct"],
                wrong if wrong is not None else row["wrong"],
                accuracy if accuracy is not None else row["accuracy"],
                now,
                signal_name,
            ),
        )
        self.conn.commit()

    def update_signal_performance(self, signal_name, is_correct):
        from ai.adaptive_learning import adjust_weight_from_accuracy

        row = self.get_signal_weight(signal_name)
        if row is None:
            self.initialize_default_signal_weights()
            row = self.get_signal_weight(signal_name)
        if row is None:
            return
        total = row["total"] + 1
        correct = row["correct"] + (1 if is_correct else 0)
        wrong = row["wrong"] + (0 if is_correct else 1)
        accuracy = round(correct / total, 4) if total else 0.0
        weight = adjust_weight_from_accuracy(row["weight"], accuracy, total)
        self.update_signal_weight(signal_name, weight, total, correct, wrong, accuracy)

    def lookup_pattern_memory(self, pattern_key):
        self.ensure_adaptive_learning_tables()
        cur = self.conn.cursor()
        cur.execute(
            "SELECT * FROM ai_pattern_memory WHERE pattern_key = %s",
            (pattern_key,),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def upsert_pattern_memory(self, pattern_key, pattern_length, next_result):
        self.ensure_adaptive_learning_tables()
        now = _now()
        cur = self.conn.cursor()
        cur.execute(
            "SELECT * FROM ai_pattern_memory WHERE pattern_key = %s",
            (pattern_key,),
        )
        row = cur.fetchone()
        if row is None:
            next_p = 1 if next_result == "P" else 0
            next_b = 1 if next_result == "B" else 0
            total = 1
        else:
            next_p = row["next_p"] + (1 if next_result == "P" else 0)
            next_b = row["next_b"] + (1 if next_result == "B" else 0)
            total = row["total"] + 1
        p_rate = round(next_p / total, 4) if total else 0.0
        b_rate = round(next_b / total, 4) if total else 0.0
        cur.execute(
            """
            INSERT INTO ai_pattern_memory (
                pattern_key, pattern_length, next_p, next_b, total,
                p_rate, b_rate, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (pattern_key) DO UPDATE SET
                next_p = EXCLUDED.next_p,
                next_b = EXCLUDED.next_b,
                total = EXCLUDED.total,
                p_rate = EXCLUDED.p_rate,
                b_rate = EXCLUDED.b_rate,
                updated_at = EXCLUDED.updated_at
            """,
            (pattern_key, pattern_length, next_p, next_b, total, p_rate, b_rate, now),
        )
        self.conn.commit()

    def get_pattern_memory_by_length(self, pattern_length):
        self.ensure_adaptive_learning_tables()
        cur = self.conn.cursor()
        cur.execute(
            "SELECT * FROM ai_pattern_memory WHERE pattern_length = %s",
            (pattern_length,),
        )
        return [dict(row) for row in cur.fetchall()]

    def get_pattern_memory_count(self):
        self.ensure_adaptive_learning_tables()
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) AS c FROM ai_pattern_memory")
        return int(cur.fetchone()["c"])

    def reset_ai_learning(self):
        try:
            from backup_manager import backup_database
            backup_database("pre_learning_reset")
        except Exception:
            pass
        cur = self.conn.cursor()
        cur.execute("DELETE FROM ai_signal_weights")
        cur.execute("DELETE FROM ai_pattern_memory")
        cur.execute("DELETE FROM pattern_rank_cache")
        self.conn.commit()
        self.initialize_default_signal_weights()

    def add_result(self, result):
        with self._connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO results (result, created_at) VALUES (%s, %s)",
                (result, _now()),
            )

    def get_results(self):
        try:
            with self._connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT result FROM results ORDER BY id ASC")
                return [
                    r["result"] if r["result"] in ("P", "B", "T") else "T"
                    for r in cur.fetchall()
                ]
        except Exception:
            return []

    def undo_last(self):
        with self._connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) AS c FROM results")
            count_before = int(cur.fetchone()["c"])
            cur.execute("DELETE FROM results WHERE id = (SELECT MAX(id) FROM results)")
            cur.execute(
                "DELETE FROM ai_prediction_history WHERE hand_index > %s",
                (count_before - 1,),
            )

    def reset_current(self):
        with self._connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM results")
            cur.execute("DELETE FROM ai_prediction_history")

    def insert_prediction_history(
        self, hand_index, history_snapshot, prediction, confidence,
        weighted_score, signal_breakdown_json, reason_json,
    ):
        if isinstance(weighted_score, dict):
            weighted_score = json.dumps(weighted_score, ensure_ascii=False)
        if isinstance(signal_breakdown_json, dict):
            signal_breakdown_json = json.dumps(signal_breakdown_json, ensure_ascii=False)
        if isinstance(reason_json, list):
            reason_json = json.dumps(reason_json, ensure_ascii=False)
        if isinstance(history_snapshot, list):
            history_snapshot = json.dumps(history_snapshot, ensure_ascii=False)
        with self._connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO ai_prediction_history (
                    created_at, hand_index, history_snapshot, prediction, confidence,
                    weighted_score, signal_breakdown_json, reason_json,
                    actual_result, is_correct
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NULL, NULL)
                RETURNING id
                """,
                (
                    _now(), hand_index, history_snapshot, prediction, confidence,
                    weighted_score, signal_breakdown_json, reason_json,
                ),
            )
            row = cur.fetchone()
            return row["id"] if row else None

    def update_prediction_actual(self, hand_index, actual_result, is_correct):
        with self._connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE ai_prediction_history
                SET actual_result = %s, is_correct = %s
                WHERE hand_index = %s AND actual_result IS NULL
                """,
                (actual_result, is_correct, hand_index),
            )
            return cur.rowcount

    def get_unresolved_prediction(self):
        with self._connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT * FROM ai_prediction_history
                WHERE actual_result IS NULL
                ORDER BY id DESC LIMIT 1
                """
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def get_all_predictions(self):
        with self._connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM ai_prediction_history ORDER BY id ASC")
            return [dict(row) for row in cur.fetchall()]

    def get_resolved_predictions_pb(self):
        with self._connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT * FROM ai_prediction_history
                WHERE actual_result IN ('P', 'B')
                ORDER BY id ASC
                """
            )
            return [dict(row) for row in cur.fetchall()]

    def count_pending_predictions(self):
        with self._connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) AS c FROM ai_prediction_history WHERE actual_result IS NULL"
            )
            return int(cur.fetchone()["c"])

    def get_learning_stats(self):
        all_rows = self.get_all_predictions()
        resolved_pb = self.get_resolved_predictions_pb()
        pending = self.count_pending_predictions()
        correct = sum(1 for row in resolved_pb if row["is_correct"] == 1)
        wrong = sum(1 for row in resolved_pb if row["is_correct"] == 0)
        resolved_count = len(resolved_pb)
        overall_accuracy = (
            round((correct / resolved_count) * 100, 2) if resolved_count else 0.0
        )
        recent_30_rows = resolved_pb[-30:]
        recent_30_correct = sum(1 for r in recent_30_rows if r["is_correct"] == 1)
        recent_30_count = len(recent_30_rows)
        recent_30_accuracy = (
            round((recent_30_correct / recent_30_count) * 100, 2)
            if recent_30_count else 0.0
        )
        recent_100_rows = resolved_pb[-100:]
        recent_100_correct = sum(1 for r in recent_100_rows if r["is_correct"] == 1)
        recent_100_count = len(recent_100_rows)
        recent_100_accuracy = (
            round((recent_100_correct / recent_100_count) * 100, 2)
            if recent_100_count else 0.0
        )
        return {
            "total_predictions": len(all_rows),
            "total_resolved": resolved_count,
            "correct": correct,
            "wrong": wrong,
            "overall_accuracy": overall_accuracy,
            "recent_30_accuracy": recent_30_accuracy,
            "recent_100_accuracy": recent_100_accuracy,
            "pending": pending,
        }

    def insert_v6_metrics(self, hand_index, metrics: dict):
        self.ensure_v6_tables()
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO ai_v6_metrics (
                hand_index, created_at, risk_score, risk_level, road_agreement,
                pattern_similarity, meta_score, pass_flag, losing_streak, prediction_quality
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                hand_index, _now(), metrics.get("risk_score"), metrics.get("risk_level"),
                metrics.get("road_agreement"), metrics.get("pattern_similarity"),
                metrics.get("meta_score"), 1 if metrics.get("pass_flag") else 0,
                metrics.get("losing_streak", 0), metrics.get("prediction_quality"),
            ),
        )
        self.conn.commit()

    def save_backtest_v6(self, window_size, result: dict):
        self.ensure_v6_tables()
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO ai_backtest_v6 (
                created_at, window_size, accuracy, avg_losing_streak,
                max_losing_streak, pass_rate, win_count, loss_count
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                _now(), window_size, result.get("accuracy"),
                result.get("average_losing_streak"), result.get("maximum_losing_streak"),
                result.get("pass_rate"), result.get("win_count"), result.get("loss_count"),
            ),
        )
        self.conn.commit()

    def save_optimizer_v6(self, result: dict, resolved_count: int):
        self.ensure_v6_tables()
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO ai_optimizer_v6 (
                optimization_time, old_weights_json, new_weights_json,
                accuracy_before, accuracy_after, resolved_count
            ) VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                _now(),
                json.dumps(result.get("old_weights", {}), ensure_ascii=False),
                json.dumps(result.get("new_weights", {}), ensure_ascii=False),
                result.get("accuracy_before"), result.get("accuracy_after"),
                resolved_count,
            ),
        )
        self.conn.commit()

    def count_optimizer_v6_runs(self):
        self.ensure_v6_tables()
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) AS c FROM ai_optimizer_v6")
        return int(cur.fetchone()["c"])

    def get_last_optimizer_resolved_count(self):
        self.ensure_v6_tables()
        cur = self.conn.cursor()
        cur.execute(
            "SELECT resolved_count FROM ai_optimizer_v6 ORDER BY id DESC LIMIT 1"
        )
        row = cur.fetchone()
        return row["resolved_count"] if row else 0

    def get_v6_pass_rate(self):
        self.ensure_v6_tables()
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) AS c FROM ai_v6_metrics")
        total = int(cur.fetchone()["c"])
        if total == 0:
            return 0.0
        cur.execute("SELECT COUNT(*) AS c FROM ai_v6_metrics WHERE pass_flag = 1")
        passes = int(cur.fetchone()["c"])
        return round(passes / total * 100.0, 2)

    def get_pattern_rank_top(self, limit=20):
        self.ensure_v6_tables()
        cur = self.conn.cursor()
        cur.execute(
            "SELECT * FROM pattern_rank_cache ORDER BY occurrences DESC LIMIT %s",
            (limit,),
        )
        return [dict(row) for row in cur.fetchall()]

    def has_prediction_for_hand(self, hand_index):
        with self._connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT 1 FROM ai_prediction_history WHERE hand_index = %s LIMIT 1",
                (hand_index,),
            )
            return cur.fetchone() is not None


def _create_adaptive_learning_tables(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ai_signal_weights (
            signal_name TEXT PRIMARY KEY,
            weight REAL NOT NULL,
            total INTEGER DEFAULT 0,
            correct INTEGER DEFAULT 0,
            wrong INTEGER DEFAULT 0,
            accuracy REAL DEFAULT 0,
            updated_at TEXT
        )
    """)
    cur.execute("""
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
    """)


def init_cloud_tables(conn=None) -> None:
    if conn is None:
        raise ValueError("conn required")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id SERIAL PRIMARY KEY,
            result TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ai_prediction_history (
            id SERIAL PRIMARY KEY,
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
    """)
    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_pred_hand_unique
        ON ai_prediction_history (hand_index)
    """)
    _create_adaptive_learning_tables(cur)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cloud_migration_log (
            id SERIAL PRIMARY KEY,
            source_tag TEXT NOT NULL,
            migrated_at TEXT NOT NULL,
            results_count INTEGER DEFAULT 0,
            predictions_count INTEGER DEFAULT 0,
            patterns_count INTEGER DEFAULT 0,
            checksum TEXT UNIQUE
        )
    """)
    conn.commit()
