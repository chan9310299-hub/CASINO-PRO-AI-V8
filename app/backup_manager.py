"""Database backup and restore."""

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from local_config import BACKUP_DIR, DB_PATH


def _ensure_backup_dir():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def backup_database(reason: str = "manual") -> Optional[Path]:
    if not DB_PATH.exists():
        return None
    _ensure_backup_dir()
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA wal_checkpoint(FULL)")
        conn.close()
    except sqlite3.Error:
        pass
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_DIR / f"casino_ai_{stamp}_{reason}.db"
    shutil.copy2(DB_PATH, dest)
    return dest


def list_backups(limit: int = 20) -> List[Path]:
    _ensure_backup_dir()
    files = sorted(BACKUP_DIR.glob("casino_ai_*.db"), reverse=True)
    return files[:limit]


def get_last_backup_time() -> Optional[str]:
    backups = list_backups(1)
    if not backups:
        return None
    ts = datetime.fromtimestamp(backups[0].stat().st_mtime)
    return ts.strftime("%Y-%m-%d %H:%M:%S")


def restore_backup(backup_path: Path) -> bool:
    if not backup_path.exists():
        return False
    if DB_PATH.exists():
        backup_database("pre_restore")
        for suffix in ("-wal", "-shm"):
            sidecar = Path(str(DB_PATH) + suffix)
            if sidecar.exists():
                sidecar.unlink()
    shutil.copy2(backup_path, DB_PATH)
    return True


def daily_backup_if_needed(marker_path: Optional[Path] = None) -> Optional[Path]:
    _ensure_backup_dir()
    marker = marker_path or (BACKUP_DIR / ".last_daily_backup")
    today = datetime.now().strftime("%Y-%m-%d")
    if marker.exists() and marker.read_text(encoding="utf-8").strip() == today:
        return None
    result = backup_database("daily")
    if result:
        marker.write_text(today, encoding="utf-8")
    return result


def verify_db_integrity() -> bool:
    if not DB_PATH.exists():
        return True
    try:
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute("PRAGMA integrity_check").fetchone()
        conn.close()
        return row and row[0] == "ok"
    except sqlite3.Error:
        return False
