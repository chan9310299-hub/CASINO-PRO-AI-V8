"""Storage layer — SQLite local + optional PostgreSQL cloud (v12)."""

from pathlib import Path
from typing import Any, Dict, List, Optional

import db_config
from local_config import DB_PATH

try:
    from backup_manager import backup_database
except Exception:
    def backup_database(reason="manual"):
        return None

try:
    from database import Database
except Exception:
    Database = None

try:
    from pg_database import PostgresDatabase, init_cloud_tables
except Exception:
    PostgresDatabase = None
    init_cloud_tables = None

_backend_instance = None


class StorageBackend:
    """Unified storage facade over SQLite or PostgreSQL."""

    def __init__(self, db=None, *, cloud: Optional[bool] = None):
        if db is not None:
            self._db = db
            self._cloud = getattr(db, "backend", "") == "postgresql"
        elif cloud is True and PostgresDatabase is not None:
            url = db_config.get_database_url()
            if not url:
                raise RuntimeError("DATABASE_URL not configured")
            self._db = PostgresDatabase(url)
            self._cloud = True
        elif cloud is False or not db_config.is_cloud_db_enabled():
            if Database is None:
                raise RuntimeError("Database unavailable")
            self._db = Database()
            self._cloud = False
        else:
            try:
                url = db_config.get_database_url()
                if url and PostgresDatabase is not None:
                    self._db = PostgresDatabase(url)
                    self._cloud = True
                else:
                    self._db = Database()
                    self._cloud = False
            except Exception:
                self._db = Database()
                self._cloud = False

    @property
    def db(self):
        return self._db

    @property
    def is_cloud(self) -> bool:
        return self._cloud

    def save_hand(self, result: str) -> None:
        try:
            self._db.add_result(result)
        except Exception:
            pass

    def save_history(self, result: str) -> None:
        self.save_hand(result)

    def load_history(self) -> List[str]:
        try:
            return self._db.get_results() or []
        except Exception:
            return []

    def save_ai_prediction(
        self,
        hand_index: int,
        history_snapshot,
        prediction,
        confidence,
        weighted_score,
        signal_breakdown,
        reason_list,
    ) -> Optional[int]:
        try:
            return self._db.insert_prediction_history(
                hand_index,
                history_snapshot,
                prediction,
                confidence,
                weighted_score,
                signal_breakdown,
                reason_list,
            )
        except Exception:
            return None

    def update_prediction_result(
        self, hand_index: int, actual_result: str, is_correct: Optional[int],
    ) -> int:
        try:
            return self._db.update_prediction_actual(hand_index, actual_result, is_correct)
        except Exception:
            return 0

    def load_ai_stats(self) -> Dict[str, Any]:
        try:
            return self._db.get_learning_stats()
        except Exception:
            return {
                "total_predictions": 0,
                "total_resolved": 0,
                "correct": 0,
                "wrong": 0,
                "overall_accuracy": 0.0,
                "recent_30_accuracy": 0.0,
                "recent_100_accuracy": 0.0,
                "pending": 0,
            }

    def save_pattern_memory(self, pattern_key: str, pattern_length: int, next_result: str) -> None:
        try:
            self._db.upsert_pattern_memory(pattern_key, pattern_length, next_result)
        except Exception:
            pass

    def load_pattern_memory(self, pattern_key: str) -> Optional[Dict[str, Any]]:
        try:
            return self._db.lookup_pattern_memory(pattern_key)
        except Exception:
            return None

    def backup_db(self, reason: str = "manual") -> Optional[Path]:
        try:
            return backup_database(reason)
        except Exception:
            return None

    def get_status(self) -> Dict[str, Any]:
        status = {}
        try:
            status = self._db.get_db_status() or {}
        except Exception:
            status = {}
        history = self.load_history()
        stats = self.load_ai_stats()
        pattern_count = 0
        try:
            pattern_count = self._db.get_pattern_memory_count()
        except Exception:
            pass
        last_save = status.get("last_save_time")
        if not last_save and hasattr(self._db, "get_last_save_time"):
            try:
                last_save = self._db.get_last_save_time()
            except Exception:
                last_save = "—"
        return {
            **status,
            "storage_mode": "cloud" if self._cloud else "local",
            "cloud_connected": self._cloud,
            "total_input_hands": len(history),
            "total_ai_predictions": stats.get("total_predictions", 0),
            "pattern_memory_count": pattern_count,
            "last_save_time": last_save or "—",
        }

    def close(self):
        try:
            self._db.close()
        except Exception:
            pass


def get_storage_backend(db=None, *, force_cloud: bool = False) -> StorageBackend:
    global _backend_instance
    if db is not None:
        return StorageBackend(db)
    if _backend_instance is not None and not force_cloud:
        return _backend_instance
    if force_cloud:
        return StorageBackend(cloud=True)
    _backend_instance = StorageBackend()
    return _backend_instance


def get_database():
    """Factory used by app entrypoint."""
    return get_storage_backend().db


# Backward-compatible aliases
Storage = StorageBackend


def load_history(db=None) -> List[str]:
    return get_storage_backend(db).load_history()


def save_hand(result: str, db=None) -> None:
    get_storage_backend(db).save_hand(result)


def save_history(result: str, db=None) -> None:
    save_hand(result, db)


def load_ai_stats(db=None) -> Dict[str, Any]:
    return get_storage_backend(db).load_ai_stats()


def save_prediction(db, hand_index, history_snapshot, prediction, confidence,
                    weighted_score, signal_breakdown, reason_list):
    return get_storage_backend(db).save_ai_prediction(
        hand_index, history_snapshot, prediction, confidence,
        weighted_score, signal_breakdown, reason_list,
    )


def backup_db(reason: str = "manual", db=None) -> Optional[Path]:
    return get_storage_backend(db).backup_db(reason)


def is_cloud_db_enabled() -> bool:
    return db_config.is_cloud_db_enabled()
