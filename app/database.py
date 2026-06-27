import sqlite3
from datetime import datetime
from config import DB_PATH


class Database:
    def __init__(self):
        self.init_db()

    def connect(self):
        return sqlite3.connect(DB_PATH)

    def init_db(self):
        conn = self.connect()
        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            result TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """)

        conn.commit()
        conn.close()

    def add_result(self, result):
        conn = self.connect()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO results (result, created_at) VALUES (?, ?)",
            (result, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
        conn.close()

    def get_results(self):
        conn = self.connect()
        cur = conn.cursor()
        cur.execute("SELECT result FROM results ORDER BY id ASC")
        rows = cur.fetchall()
        conn.close()
        return [r[0] for r in rows]

    def undo_last(self):
        conn = self.connect()
        cur = conn.cursor()
        cur.execute("DELETE FROM results WHERE id = (SELECT MAX(id) FROM results)")
        conn.commit()
        conn.close()

    def reset_current(self):
        conn = self.connect()
        cur = conn.cursor()
        cur.execute("DELETE FROM results")
        conn.commit()
        conn.close()