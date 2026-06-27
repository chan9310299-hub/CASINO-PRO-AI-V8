from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
BACKUP_DIR = DATA_DIR / "backups"
EXPORT_DIR = DATA_DIR / "exports"

DATA_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "casino_ai.db"

APP_NAME = "CASINO PRO AI v9 모바일 프로"
VERSION = "v9.2 모바일 간소화"
APP_VERSION = VERSION

PB_RESULTS = ("P", "B")
TIE = "T"
MIN_PREDICT_COUNT = 6
MAX_PATTERN_SIZE = 8
