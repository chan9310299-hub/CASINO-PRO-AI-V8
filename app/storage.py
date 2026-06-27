"""Storage layer — SQLite today, online DB ready boundaries."""

from pathlib import Path
from typing import Any, Dict, List, Optional

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


class Storage:
    """Thin facade over Database for future backend swap."""

    def __init__(self, db=None):
        if db is not None:
            self._db = db
        elif Database is not None:
            self._db = Database()
        else:
            raise RuntimeError("Database unavailable")

    @property
    def db(self):
        return self._db

    def load_history(self) -> List[str]:
        try:
            return self._db.get_results() or []
        except Exception:
            return []

    def save_history(self, result: str) -> None:
        try:
            self._db.add_result(result)
        except Exception:
            pass

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

    def save_prediction(
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

    def backup_db(self, reason: str = "manual") -> Optional[Path]:
        try:
            return backup_database(reason)
        except Exception:
            return None

    def close(self):
        try:
            self._db.close()
        except Exception:
            pass


def load_history(db=None) -> List[str]:
    return Storage(db).load_history()


def save_history(result: str, db=None) -> None:
    Storage(db).save_history(result)


def load_ai_stats(db=None) -> Dict[str, Any]:
    return Storage(db).load_ai_stats()


def save_prediction(db, hand_index, history_snapshot, prediction, confidence,
                    weighted_score, signal_breakdown, reason_list):
    return Storage(db).save_prediction(
        hand_index, history_snapshot, prediction, confidence,
        weighted_score, signal_breakdown, reason_list,
    )


def backup_db(reason: str = "manual", db=None) -> Optional[Path]:
    return Storage(db).backup_db(reason)
