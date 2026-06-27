import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime

from backup_manager import backup_database, get_last_backup_time
from config import DB_PATH
from db_migration import get_migration_status, run_migrations

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
}


class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        run_migrations(self.conn, backup_fn=backup_database)
        self.init_db()

    def get_db_status(self):
        status = get_migration_status(self.conn)
        status["last_backup"] = get_last_backup_time() or "—"
        return status

    @contextmanager
    def _connection(self):
        try:
            yield self.conn
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def connect(self):
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
            cur.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                result TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """)
            cur.execute("""
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
            """)
            self.ensure_adaptive_learning_tables(cur)
            self.ensure_v6_tables(cur)

    def ensure_v6_tables(self, cur=None):
        def _create(cursor):
            cursor.execute("""
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
            """)
            cursor.execute("""
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
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_optimizer_v6 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                optimization_time TEXT NOT NULL,
                old_weights_json TEXT NOT NULL,
                new_weights_json TEXT NOT NULL,
                accuracy_before REAL,
                accuracy_after REAL,
                resolved_count INTEGER
            )
            """)

        if cur is not None:
            _create(cur)
        else:
            with self._connection() as conn:
                _create(conn.cursor())

    def insert_v6_metrics(self, hand_index, metrics: dict):
        self.ensure_v6_tables()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO ai_v6_metrics (
                hand_index, created_at, risk_score, risk_level, road_agreement,
                pattern_similarity, meta_score, pass_flag, losing_streak, prediction_quality
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            hand_index,
            now,
            metrics.get("risk_score"),
            metrics.get("risk_level"),
            metrics.get("road_agreement"),
            metrics.get("pattern_similarity"),
            metrics.get("meta_score"),
            1 if metrics.get("pass_flag") else 0,
            metrics.get("losing_streak", 0),
            metrics.get("prediction_quality"),
        ))
        self.conn.commit()

    def save_backtest_v6(self, window_size, result: dict):
        self.ensure_v6_tables()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO ai_backtest_v6 (
                created_at, window_size, accuracy, avg_losing_streak,
                max_losing_streak, pass_rate, win_count, loss_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            now, window_size, result.get("accuracy"), result.get("average_losing_streak"),
            result.get("maximum_losing_streak"), result.get("pass_rate"),
            result.get("win_count"), result.get("loss_count"),
        ))
        self.conn.commit()

    def save_optimizer_v6(self, result: dict, resolved_count: int):
        self.ensure_v6_tables()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO ai_optimizer_v6 (
                optimization_time, old_weights_json, new_weights_json,
                accuracy_before, accuracy_after, resolved_count
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            now,
            json.dumps(result.get("old_weights", {}), ensure_ascii=False),
            json.dumps(result.get("new_weights", {}), ensure_ascii=False),
            result.get("accuracy_before"),
            result.get("accuracy_after"),
            resolved_count,
        ))
        self.conn.commit()

    def count_optimizer_v6_runs(self):
        self.ensure_v6_tables()
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM ai_optimizer_v6")
        return cur.fetchone()[0]

    def get_last_optimizer_resolved_count(self):
        self.ensure_v6_tables()
        cur = self.conn.cursor()
        cur.execute(
            "SELECT resolved_count FROM ai_optimizer_v6 ORDER BY id DESC LIMIT 1"
        )
        row = cur.fetchone()
        return row[0] if row else 0

    def get_v6_pass_rate(self):
        self.ensure_v6_tables()
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM ai_v6_metrics")
        total = cur.fetchone()[0]
        if total == 0:
            return 0.0
        cur.execute("SELECT COUNT(*) FROM ai_v6_metrics WHERE pass_flag = 1")
        passes = cur.fetchone()[0]
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

    def initialize_default_signal_weights(self, cur=None):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        def _insert_defaults(cursor):
            for name, weight in LEARNING_SIGNAL_DEFAULTS.items():
                cursor.execute("""
                    INSERT OR IGNORE INTO ai_signal_weights (
                        signal_name, weight, total, correct, wrong, accuracy, updated_at
                    ) VALUES (?, ?, 0, 0, 0, 0, ?)
                """, (name, weight, now))

        if cur is not None:
            _insert_defaults(cur)
        else:
            with self._connection() as conn:
                _insert_defaults(conn.cursor())

    def get_all_signal_weights(self):
        self.ensure_adaptive_learning_tables()
        cur = self.conn.cursor()
        cur.execute("SELECT signal_name, weight FROM ai_signal_weights")
        rows = cur.fetchall()
        return {row["signal_name"]: row["weight"] for row in rows}

    def get_signal_weight(self, signal_name):
        self.ensure_adaptive_learning_tables()
        cur = self.conn.cursor()
        cur.execute(
            "SELECT * FROM ai_signal_weights WHERE signal_name = ?",
            (signal_name,),
        )
        row = cur.fetchone()
        return dict(row) if row else None

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
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cur = self.conn.cursor()
        cur.execute("""
            UPDATE ai_signal_weights
            SET weight = ?, total = ?, correct = ?, wrong = ?,
                accuracy = ?, updated_at = ?
            WHERE signal_name = ?
        """, (
            new_weight, new_total, new_correct, new_wrong,
            new_accuracy, now, signal_name,
        ))
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
        cur = self.conn.cursor()
        cur.execute(
            "SELECT * FROM ai_pattern_memory WHERE pattern_key = ?",
            (pattern_key,),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def upsert_pattern_memory(self, pattern_key, pattern_length, next_result):
        self.ensure_adaptive_learning_tables()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur = self.conn.cursor()
        cur.execute(
            "SELECT * FROM ai_pattern_memory WHERE pattern_key = ?",
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

        cur.execute("""
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
        """, (
            pattern_key, pattern_length, next_p, next_b, total,
            p_rate, b_rate, now,
        ))
        self.conn.commit()

    def get_pattern_memory_by_length(self, pattern_length):
        self.ensure_adaptive_learning_tables()
        cur = self.conn.cursor()
        cur.execute(
            "SELECT * FROM ai_pattern_memory WHERE pattern_length = ?",
            (pattern_length,),
        )
        return [dict(row) for row in cur.fetchall()]

    def get_pattern_memory_count(self):
        self.ensure_adaptive_learning_tables()
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM ai_pattern_memory")
        return cur.fetchone()[0]

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
        with self._connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO results (result, created_at) VALUES (?, ?)",
                (result, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            )

    def get_results(self):
        try:
            with self._connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT result FROM results ORDER BY id ASC")
                rows = cur.fetchall()
                return [r[0] if r[0] in ("P", "B", "T") else "T" for r in rows]
        except sqlite3.Error:
            return []

    def undo_last(self):
        with self._connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM results")
            count_before = cur.fetchone()[0]
            cur.execute("DELETE FROM results WHERE id = (SELECT MAX(id) FROM results)")
            cur.execute(
                "DELETE FROM ai_prediction_history WHERE hand_index > ?",
                (count_before - 1,),
            )

    def reset_current(self):
        with self._connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM results")
            cur.execute("DELETE FROM ai_prediction_history")

    # --- AI prediction history (required API) ---

    def has_prediction_for_hand(self, hand_index):
        with self._connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT 1 FROM ai_prediction_history WHERE hand_index = ? LIMIT 1",
                (hand_index,),
            )
            return cur.fetchone() is not None

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
            cur.execute("""
                INSERT INTO ai_prediction_history (
                    created_at,
                    hand_index,
                    history_snapshot,
                    prediction,
                    confidence,
                    weighted_score,
                    signal_breakdown_json,
                    reason_json,
                    actual_result,
                    is_correct
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL)
            """, (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                hand_index,
                history_snapshot,
                prediction,
                confidence,
                weighted_score,
                signal_breakdown_json,
                reason_json,
            ))
            return cur.lastrowid

    def update_prediction_actual(self, hand_index, actual_result, is_correct):
        with self._connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE ai_prediction_history
                SET actual_result = ?, is_correct = ?
                WHERE hand_index = ? AND actual_result IS NULL
            """, (actual_result, is_correct, hand_index))
            return cur.rowcount

    def get_unresolved_prediction(self):
        with self._connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM ai_prediction_history
                WHERE actual_result IS NULL
                ORDER BY id DESC
                LIMIT 1
            """)
            row = cur.fetchone()
            return dict(row) if row else None

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
        with self._connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM ai_prediction_history ORDER BY id ASC"
            )
            return [dict(row) for row in cur.fetchall()]

    def get_resolved_predictions_pb(self):
        with self._connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM ai_prediction_history
                WHERE actual_result IN ('P', 'B')
                ORDER BY id ASC
            """)
            return [dict(row) for row in cur.fetchall()]

    def count_pending_predictions(self):
        with self._connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM ai_prediction_history WHERE actual_result IS NULL"
            )
            return cur.fetchone()[0]

    def count_all_predictions(self):
        with self._connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM ai_prediction_history")
            return cur.fetchone()[0]

    # Backward-compatible aliases
    def record_signal_outcome(self, signal_name, was_correct):
        return self.update_signal_performance(signal_name, was_correct)

    def reset_adaptive_learning(self):
        return self.reset_ai_learning()

    def get_pattern_memory(self, pattern_key):
        return self.lookup_pattern_memory(pattern_key)

    def count_pattern_memory(self):
        return self.get_pattern_memory_count()
