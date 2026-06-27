from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
BACKUP_DIR = DATA_DIR / "backups"
EXPORT_DIR = DATA_DIR / "exports"

DATA_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "casino_ai.db"

APP_NAME = "CASINO PRO AI"
VERSION = "v12 Persistent Cloud Database"
APP_VERSION = VERSION

PB_RESULTS = ("P", "B")
TIE = "T"
MIN_PREDICT_COUNT = 6
MAX_PATTERN_SIZE = 8
