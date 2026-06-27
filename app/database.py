import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Union

import db_config
from local_config import DB_PATH

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None
    RealDictCursor = None

try:
    from backup_manager import backup_database, get_last_backup_time
except Exception:
    def backup_database(reason="manual"):
        return None

    def get_last_backup_time():
        return None

try:
    from db_migration import get_migration_status, run_migrations
except Exception:
    def get_migration_status(conn):
        return {
            "version": 0,
            "target_version": 0,
            "tables_ok": True,
            "missing_tables": [],
            "total_stored_rows": 0,
            "status": "OK",
        }

    def run_migrations(conn, backup_fn=None):
        return {"version": 0, "migrated": False}


def _adapt_sql(sql: str, backend: str) -> str:
    if backend != "postgresql":
        return sql
    out = sql.replace("?", "%s")
    out = out.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
    out = out.replace("AUTOINCREMENT", "")
    out = out.replace("INSERT OR IGNORE", "INSERT")
    out = out.replace("MAX(p_rate, b_rate)", "GREATEST(p_rate, b_rate)")
    out = out.replace("MIN(1.0,", "LEAST(1.0,")
    return out


def _row_to_dict(row) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    if isinstance(row, dict):
        return dict(row)
    try:
        return dict(row)
    except Exception:
        return None


def _scalar(row) -> Any:
    if row is None:
        return None
    if isinstance(row, dict):
        return next(iter(row.values()))
    return row[0]


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

LEARNING_SIGNAL_DEFAULTS = {
    "recent_10": 0.45,
    "recent_20": 0.55,
    "recent_30": 0.65,
    "bigroad": 2.0,
    "dragon": 2.5,
    "chop": 1.75,
    "ping_pong": 1.25,
    "double_pattern": 1.25,
    "big_eye": 1.2,
    "small_road": 1.2,
    "cockroach_road": 1.2,
    "pattern_memory": 1.0,
    "streak_ai": 1.2,
    "chop_ai": 1.3,
    "dragon_ai": 1.5,
    "reversal_ai": 1.1,
    "two_side_balance_ai": 1.0,
    "road_consensus_ai": 1.4,
    "memory_similarity_ai": 1.3,
    "risk_filter_ai": 1.2,
    "meta_vote_ai": 2.0,
    "anti_six_loss_ai": 1.8,
}


class Database:
    backend = "sqlite"

    def __init__(self, force_sqlite: bool = False):
        self.database_url = None
        url = None if force_sqlite else db_config.get_database_url()
        if url and psycopg2 is not None:
            try:
                self.backend = "postgresql"
                self.database_url = url
                self.conn = psycopg2.connect(url, cursor_factory=RealDictCursor)
                self.conn.autocommit = False
                self._bootstrap_postgres()
                return
            except Exception:
                self.backend = "sqlite"
                self.database_url = None

        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        try:
            run_migrations(self.conn, backup_fn=backup_database)
        except Exception:
            pass
        self.init_db()
        try:
            self.ensure_v5_tables()
        except Exception:
            pass
        try:
            self.ensure_learning_tables()
        except Exception:
            pass
        try:
            self.ensure_v6_tables()
        except Exception:
            pass

    @property
    def is_postgres(self) -> bool:
        return self.backend == "postgresql"

    def execute(self, sql: str, params: Optional[Sequence] = None):
        cur = self.conn.cursor()
        cur.execute(_adapt_sql(sql, self.backend), tuple(params or ()))
        return cur

    def query(self, sql: str, params: Optional[Sequence] = None) -> List[Dict[str, Any]]:
        cur = self.execute(sql, params)
        return [_row_to_dict(r) for r in cur.fetchall() if _row_to_dict(r) is not None]

    def query_one(self, sql: str, params: Optional[Sequence] = None) -> Optional[Dict[str, Any]]:
        cur = self.execute(sql, params)
        return _row_to_dict(cur.fetchone())

    def _safe_rollback(self) -> None:
        if not self.conn:
            return
        if getattr(self.conn, "closed", False):
            return
        try:
            self.conn.rollback()
        except Exception:
            pass

    def _bootstrap_postgres(self) -> None:
        try:
            from pg_database import init_cloud_tables
            init_cloud_tables(self.conn)
        except Exception:
            self.init_db()
        try:
            self.ensure_v6_tables()
        except Exception:
            pass
        try:
            self.ensure_learning_tables()
        except Exception:
            pass

    def ensure_v5_tables(self, cur=None):
        """Backward-compatible V5 schema hook — no destructive changes."""
        if cur is not None:
            return
        with self._connection() as conn:
            conn.cursor()

    def ensure_learning_tables(self, cur=None):
        """Alias for adaptive learning tables (V3/V5 compatibility)."""
        self.ensure_adaptive_learning_tables(cur)

    def ensure_v6_tables(self, cur=None):
        cursor = cur if cur is not None else self.conn.cursor()
        ddl_list = [
            """
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
            """
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
            """
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
            """
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
            """
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
            """
            CREATE TABLE IF NOT EXISTS ai_learning_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                overall_accuracy REAL,
                best_signal TEXT,
                worst_signal TEXT,
                avg_confidence REAL
            )
            """,
            """
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
            """
            CREATE TABLE IF NOT EXISTS pattern_ranking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern TEXT,
                pattern_key TEXT,
                occurrences INTEGER DEFAULT 0,
                next_p INTEGER DEFAULT 0,
                next_b INTEGER DEFAULT 0,
                confidence REAL DEFAULT 0,
                last_seen TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS v6_statistics (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS anti_streak_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                risk_level TEXT,
                current_losing_streak INTEGER DEFAULT 0,
                action TEXT,
                reason TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS prediction_quality (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                prediction TEXT,
                quality_grade TEXT,
                confidence REAL DEFAULT 0,
                risk_level TEXT,
                pass_flag INTEGER DEFAULT 0
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS confidence_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                confidence REAL DEFAULT 0,
                calibrated_confidence REAL DEFAULT 0,
                reason TEXT
            )
            """,
        ]
        for ddl in ddl_list:
            cursor.execute(_adapt_sql(ddl, self.backend))

        if cur is None and not self.is_postgres:
            self.conn.commit()

    def get_last_save_time(self) -> str:
        try:
            row = self.query_one(
                """
                SELECT MAX(ts) AS last_ts FROM (
                    SELECT MAX(created_at) AS ts FROM results
                    UNION ALL
                    SELECT MAX(created_at) FROM ai_prediction_history
                    UNION ALL
                    SELECT MAX(updated_at) FROM ai_pattern_memory
                ) AS t
                """
            )
            if row:
                return row.get("last_ts") or "—"
            with self._connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT MAX(ts) FROM (
                        SELECT MAX(created_at) AS ts FROM results
                        UNION ALL
                        SELECT MAX(created_at) FROM ai_prediction_history
                        UNION ALL
                        SELECT MAX(updated_at) FROM ai_pattern_memory
                    )
                    """
                )
                return _scalar(cur.fetchone()) or "—"
        except Exception:
            return "—"

    def get_db_status(self):
        try:
            if self.is_postgres:
                status = {
                    "version": 12,
                    "target_version": 12,
                    "tables_ok": True,
                    "missing_tables": [],
                    "total_stored_rows": 0,
                    "status": "클라우드 연결됨",
                    "last_backup": "—",
                    "storage_mode": "cloud",
                    "cloud_connected": True,
                }
            else:
                status = get_migration_status(self.conn)
                status["last_backup"] = get_last_backup_time() or "—"
                status["storage_mode"] = "local"
                status["cloud_connected"] = False
            status["last_save_time"] = self.get_last_save_time()
            try:
                status["total_input_hands"] = len(self.get_results() or [])
                stats = self.get_learning_stats()
                status["total_ai_predictions"] = stats.get("total_predictions", 0)
                status["pattern_memory_count"] = self.get_pattern_memory_count()
                status["total_stored_rows"] = (
                    status.get("total_stored_rows", 0)
                    or status["total_input_hands"]
                    + status["total_ai_predictions"]
                    + status["pattern_memory_count"]
                )
            except Exception:
                pass
            return status
        except Exception:
            return {
                "version": 0,
                "target_version": 0,
                "tables_ok": True,
                "missing_tables": [],
                "total_stored_rows": 0,
                "status": "OK",
                "last_backup": "—",
                "storage_mode": "cloud" if self.is_postgres else "local",
                "cloud_connected": self.is_postgres,
                "last_save_time": "—",
            }

    @contextmanager
    def _connection(self):
        try:
            yield self.conn
            if self.conn and not getattr(self.conn, "closed", False):
                self.conn.commit()
        except Exception:
            self._safe_rollback()
            raise

    def connect(self):
        if self.is_postgres:
            if psycopg2 is None:
                raise RuntimeError("psycopg2 required")
            conn = psycopg2.connect(self.database_url, cursor_factory=RealDictCursor)
            conn.autocommit = False
            return conn
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    def init_db(self):
        with self._connection() as conn:
            cur = conn.cursor()
            cur.execute(_adapt_sql("""
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                result TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """, self.backend))
            cur.execute(_adapt_sql("""
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
            """, self.backend))
            if self.is_postgres:
                cur.execute(
                    """
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_pred_hand_unique
                    ON ai_prediction_history (hand_index)
                    """
                )
            self.ensure_adaptive_learning_tables(cur)

    def insert_v6_metrics(self, hand_index, metrics: dict):
        self.ensure_v6_tables()
        self.execute(
            """
            INSERT INTO ai_v6_metrics (
                hand_index, created_at, risk_score, risk_level, road_agreement,
                pattern_similarity, meta_score, pass_flag, losing_streak, prediction_quality
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                hand_index,
                _now_str(),
                metrics.get("risk_score"),
                metrics.get("risk_level"),
                metrics.get("road_agreement"),
                metrics.get("pattern_similarity"),
                metrics.get("meta_score"),
                1 if metrics.get("pass_flag") else 0,
                metrics.get("losing_streak", 0),
                metrics.get("prediction_quality"),
            ),
        )
        self.conn.commit()

    def save_backtest_v6(self, window_size, result: dict):
        self.ensure_v6_tables()
        self.execute(
            """
            INSERT INTO ai_backtest_v6 (
                created_at, window_size, accuracy, avg_losing_streak,
                max_losing_streak, pass_rate, win_count, loss_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _now_str(), window_size, result.get("accuracy"),
                result.get("average_losing_streak"), result.get("maximum_losing_streak"),
                result.get("pass_rate"), result.get("win_count"), result.get("loss_count"),
            ),
        )
        self.conn.commit()

    def save_optimizer_v6(self, result: dict, resolved_count: int):
        self.ensure_v6_tables()
        self.execute(
            """
            INSERT INTO ai_optimizer_v6 (
                optimization_time, old_weights_json, new_weights_json,
                accuracy_before, accuracy_after, resolved_count
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                _now_str(),
                json.dumps(result.get("old_weights", {}), ensure_ascii=False),
                json.dumps(result.get("new_weights", {}), ensure_ascii=False),
                result.get("accuracy_before"),
                result.get("accuracy_after"),
                resolved_count,
            ),
        )
        self.conn.commit()

    def count_optimizer_v6_runs(self):
        self.ensure_v6_tables()
        row = self.query_one("SELECT COUNT(*) AS c FROM ai_optimizer_v6")
        return int((row or {}).get("c") or 0)

    def get_last_optimizer_resolved_count(self):
        self.ensure_v6_tables()
        row = self.query_one(
            "SELECT resolved_count FROM ai_optimizer_v6 ORDER BY id DESC LIMIT 1"
        )
        return int((row or {}).get("resolved_count") or 0)

    def get_v6_pass_rate(self):
        self.ensure_v6_tables()
        row = self.query_one("SELECT COUNT(*) AS c FROM ai_v6_metrics")
        total = int((row or {}).get("c") or 0)
        if total == 0:
            return 0.0
        row2 = self.query_one(
            "SELECT COUNT(*) AS c FROM ai_v6_metrics WHERE pass_flag = 1"
        )
        passes = int((row2 or {}).get("c") or 0)
        return round(passes / total * 100.0, 2)

    def ensure_adaptive_learning_tables(self, cur=None):
        """Create adaptive-learning tables if missing and seed default weights."""
        if cur is not None:
            self._create_adaptive_learning_tables(cur)
            self.initialize_default_signal_weights(cur=cur)
            return

        with self._connection() as conn:
            cur = conn.cursor()
            self._create_adaptive_learning_tables(cur)
            self.initialize_default_signal_weights(cur=cur)

    def _create_adaptive_learning_tables(self, cur):
        cur.execute(_adapt_sql("""
        CREATE TABLE IF NOT EXISTS ai_signal_weights (
            signal_name TEXT PRIMARY KEY,
            weight REAL NOT NULL,
            total INTEGER DEFAULT 0,
            correct INTEGER DEFAULT 0,
            wrong INTEGER DEFAULT 0,
            accuracy REAL DEFAULT 0,
            updated_at TEXT
        )
        """, self.backend))
        cur.execute(_adapt_sql("""
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
        """, self.backend))

    def initialize_default_signal_weights(self, cur=None):
        now = _now_str()

        def _insert_defaults(cursor):
            for name, weight in LEARNING_SIGNAL_DEFAULTS.items():
                if self.is_postgres:
                    cursor.execute(
                        """
                        INSERT INTO ai_signal_weights (
                            signal_name, weight, total, correct, wrong, accuracy, updated_at
                        ) VALUES (%s, %s, 0, 0, 0, 0, %s)
                        ON CONFLICT (signal_name) DO NOTHING
                        """,
                        (name, weight, now),
                    )
                else:
                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO ai_signal_weights (
                            signal_name, weight, total, correct, wrong, accuracy, updated_at
                        ) VALUES (?, ?, 0, 0, 0, 0, ?)
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
        return {
            row["signal_name"]: row["weight"]
            for row in self.query("SELECT signal_name, weight FROM ai_signal_weights")
        }

    def get_signal_weight(self, signal_name):
        self.ensure_adaptive_learning_tables()
        return self.query_one(
            "SELECT * FROM ai_signal_weights WHERE signal_name = ?",
            (signal_name,),
        )

    def update_signal_weight(
        self,
        signal_name,
        weight,
        total=None,
        correct=None,
        wrong=None,
        accuracy=None,
    ):
        row = self.get_signal_weight(signal_name)
        if row is None:
            self.initialize_default_signal_weights()
            row = self.get_signal_weight(signal_name)
        if row is None:
            return

        new_weight = weight if weight is not None else row["weight"]
        new_total = total if total is not None else row["total"]
        new_correct = correct if correct is not None else row["correct"]
        new_wrong = wrong if wrong is not None else row["wrong"]
        new_accuracy = accuracy if accuracy is not None else row["accuracy"]
        now = _now_str()

        self.execute(
            """
            UPDATE ai_signal_weights
            SET weight = ?, total = ?, correct = ?, wrong = ?,
                accuracy = ?, updated_at = ?
            WHERE signal_name = ?
            """,
            (
                new_weight, new_total, new_correct, new_wrong,
                new_accuracy, now, signal_name,
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
        self.update_signal_weight(
            signal_name, weight, total, correct, wrong, accuracy
        )

    def lookup_pattern_memory(self, pattern_key):
        self.ensure_adaptive_learning_tables()
        return self.query_one(
            "SELECT * FROM ai_pattern_memory WHERE pattern_key = ?",
            (pattern_key,),
        )

    def upsert_pattern_memory(self, pattern_key, pattern_length, next_result):
        self.ensure_adaptive_learning_tables()
        now = _now_str()
        row = self.lookup_pattern_memory(pattern_key)
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

        self.execute(
            """
            INSERT INTO ai_pattern_memory (
                pattern_key, pattern_length, next_p, next_b, total,
                p_rate, b_rate, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(pattern_key) DO UPDATE SET
                next_p = excluded.next_p,
                next_b = excluded.next_b,
                total = excluded.total,
                p_rate = excluded.p_rate,
                b_rate = excluded.b_rate,
                updated_at = excluded.updated_at
            """,
            (
                pattern_key, pattern_length, next_p, next_b, total,
                p_rate, b_rate, now,
            ),
        )
        self.conn.commit()

    def get_pattern_memory_by_length(self, pattern_length):
        self.ensure_adaptive_learning_tables()
        return self.query(
            "SELECT * FROM ai_pattern_memory WHERE pattern_length = ?",
            (pattern_length,),
        )

    def get_pattern_memory_count(self):
        self.ensure_adaptive_learning_tables()
        row = self.query_one("SELECT COUNT(*) AS c FROM ai_pattern_memory")
        return int((row or {}).get("c") or 0)

    def reset_ai_learning(self):
        backup_database("pre_learning_reset")
        cur = self.conn.cursor()
        cur.execute("DELETE FROM ai_signal_weights")
        cur.execute("DELETE FROM ai_pattern_memory")
        cur.execute("DELETE FROM pattern_rank_cache")
        self.conn.commit()
        self.initialize_default_signal_weights()

    def refresh_pattern_rank_cache(self):
        self.ensure_v6_tables()
        cur = self.conn.cursor()
        cur.execute("DELETE FROM pattern_rank_cache")
        cur.execute("""
            INSERT INTO pattern_rank_cache (
                pattern_key, pattern_length, occurrences, next_p, next_b,
                p_rate, b_rate, confidence, last_seen
            )
            SELECT pattern_key, pattern_length, total, next_p, next_b,
                   p_rate, b_rate,
                   MAX(p_rate, b_rate) * MIN(1.0, total / 20.0),
                   updated_at
            FROM ai_pattern_memory
        """)
        self.conn.commit()

    def get_pattern_rank_top(self, limit=20):
        self.ensure_v6_tables()
        cur = self.conn.cursor()
        cur.execute("""
            SELECT * FROM pattern_rank_cache
            ORDER BY occurrences DESC LIMIT ?
        """, (limit,))
        return [dict(row) for row in cur.fetchall()]

    def save_backtest_report(self, window_size, result: dict, best_signal="—", worst_signal="—"):
        self.ensure_v6_tables()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO ai_backtest_results (
                created_at, window_size, accuracy, avg_losing_streak,
                max_losing_streak, pass_rate, prediction_count,
                win_count, loss_count, best_signal, worst_signal
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            now, window_size, result.get("accuracy"),
            result.get("average_losing_streak"), result.get("maximum_losing_streak"),
            result.get("pass_rate"), result.get("sample_size", 0),
            result.get("win_count", 0), result.get("loss_count", 0),
            best_signal, worst_signal,
        ))
        self.save_backtest_v6(window_size, result)
        self.conn.commit()

    def get_latest_backtest_reports(self, limit=4):
        self.ensure_v6_tables()
        cur = self.conn.cursor()
        cur.execute("""
            SELECT * FROM ai_backtest_results
            ORDER BY id DESC LIMIT ?
        """, (limit,))
        return [dict(row) for row in cur.fetchall()]

    def add_result(self, result):
        self.execute(
            "INSERT INTO results (result, created_at) VALUES (?, ?)",
            (result, _now_str()),
        )
        if not self.is_postgres:
            self.conn.commit()
        else:
            self.conn.commit()

    def get_results(self):
        try:
            rows = self.query("SELECT result FROM results ORDER BY id ASC")
            out = []
            for r in rows:
                val = r.get("result")
                out.append(val if val in ("P", "B", "T") else "T")
            return out
        except Exception:
            return []

    def undo_last(self):
        with self._connection() as conn:
            cur = conn.cursor()
            cur.execute(_adapt_sql("SELECT COUNT(*) FROM results", self.backend))
            count_before = _scalar(cur.fetchone()) or 0
            cur.execute(
                _adapt_sql(
                    "DELETE FROM results WHERE id = (SELECT MAX(id) FROM results)",
                    self.backend,
                )
            )
            cur.execute(
                _adapt_sql(
                    "DELETE FROM ai_prediction_history WHERE hand_index > ?",
                    self.backend,
                ),
                (count_before - 1,),
            )

    def reset_current(self):
        self.execute("DELETE FROM results")
        self.execute("DELETE FROM ai_prediction_history")
        self.conn.commit()

    # --- AI prediction history (required API) ---

    def insert_prediction_history(
        self,
        hand_index,
        history_snapshot,
        prediction,
        confidence,
        weighted_score,
        signal_breakdown_json,
        reason_json,
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
            if self.is_postgres:
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
                        _now_str(), hand_index, history_snapshot, prediction, confidence,
                        weighted_score, signal_breakdown_json, reason_json,
                    ),
                )
                row = cur.fetchone()
                return _scalar(row)
            cur.execute(
                """
                INSERT INTO ai_prediction_history (
                    created_at, hand_index, history_snapshot, prediction, confidence,
                    weighted_score, signal_breakdown_json, reason_json,
                    actual_result, is_correct
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL)
                """,
                (
                    _now_str(), hand_index, history_snapshot, prediction, confidence,
                    weighted_score, signal_breakdown_json, reason_json,
                ),
            )
            return cur.lastrowid

    def get_unresolved_prediction(self):
        return self.query_one("""
            SELECT * FROM ai_prediction_history
            WHERE actual_result IS NULL
            ORDER BY id DESC
            LIMIT 1
        """)

    def update_prediction_actual(self, hand_index, actual_result, is_correct):
        cur = self.execute(
            """
            UPDATE ai_prediction_history
            SET actual_result = ?, is_correct = ?
            WHERE hand_index = ? AND actual_result IS NULL
            """,
            (actual_result, is_correct, hand_index),
        )
        if self.is_postgres:
            self.conn.commit()
        return cur.rowcount

    def has_prediction_for_hand(self, hand_index):
        row = self.query_one(
            "SELECT 1 AS ok FROM ai_prediction_history WHERE hand_index = ? LIMIT 1",
            (hand_index,),
        )
        return row is not None

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

    # --- Helpers / backward-compatible aliases ---

    def get_pending_prediction(self):
        return self.get_unresolved_prediction()

    def log_prediction(
        self,
        hand_index,
        history_snapshot,
        prediction,
        confidence,
        weighted_score,
        signal_breakdown,
        reason_list,
    ):
        return self.insert_prediction_history(
            hand_index,
            history_snapshot,
            prediction,
            confidence,
            weighted_score,
            signal_breakdown,
            reason_list,
        )

    def resolve_pending_prediction(self, actual_result):
        pending = self.get_unresolved_prediction()
        if pending is None:
            return None

        if actual_result == "T":
            is_correct = None
        elif actual_result == pending["prediction"]:
            is_correct = 1
        else:
            is_correct = 0

        updated = self.update_prediction_actual(
            pending["hand_index"],
            actual_result,
            is_correct,
        )
        return pending["id"] if updated else None

    def get_all_predictions(self):
        return self.query("SELECT * FROM ai_prediction_history ORDER BY id ASC")

    def get_resolved_predictions_pb(self):
        return self.query("""
            SELECT * FROM ai_prediction_history
            WHERE actual_result IN ('P', 'B')
            ORDER BY id ASC
        """)

    def count_pending_predictions(self):
        row = self.query_one(
            "SELECT COUNT(*) AS c FROM ai_prediction_history WHERE actual_result IS NULL"
        )
        return int((row or {}).get("c") or 0)

    def count_all_predictions(self):
        row = self.query_one("SELECT COUNT(*) AS c FROM ai_prediction_history")
        return int((row or {}).get("c") or 0)

    # Backward-compatible aliases
    def record_signal_outcome(self, signal_name, was_correct):
        return self.update_signal_performance(signal_name, was_correct)

    def reset_adaptive_learning(self):
        return self.reset_ai_learning()

    def get_pattern_memory(self, pattern_key):
        return self.lookup_pattern_memory(pattern_key)

    def count_pattern_memory(self):
        return self.get_pattern_memory_count()


def create_database(force_sqlite: bool = False):
    """Return PostgreSQL (if DATABASE_URL set) or local SQLite database."""
    return Database(force_sqlite=force_sqlite)


def get_database(force_sqlite: bool = False):
    return create_database(force_sqlite=force_sqlite)
