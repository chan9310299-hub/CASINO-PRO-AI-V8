from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "casino_ai.db"

APP_NAME = "CASINO PRO AI"
VERSION = "v2.0 ROAD CORE"