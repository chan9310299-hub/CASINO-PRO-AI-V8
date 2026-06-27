"""PostgreSQL schema bootstrap — used by database.Database."""


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


__all__ = ["init_cloud_tables"]
