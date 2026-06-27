"""Reliable access to app/config.py regardless of sys.path order."""

import importlib.util
from pathlib import Path

_CONFIG_PATH = Path(__file__).resolve().parent / "config.py"


def _load_config():
    spec = importlib.util.spec_from_file_location("casino_pro_config", _CONFIG_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load config from {_CONFIG_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_cfg = _load_config()

BASE_DIR = _cfg.BASE_DIR
DATA_DIR = _cfg.DATA_DIR
BACKUP_DIR = _cfg.BACKUP_DIR
EXPORT_DIR = _cfg.EXPORT_DIR
DB_PATH = _cfg.DB_PATH
APP_NAME = _cfg.APP_NAME
VERSION = _cfg.VERSION
APP_VERSION = _cfg.APP_VERSION
PB_RESULTS = _cfg.PB_RESULTS
TIE = _cfg.TIE
MIN_PREDICT_COUNT = _cfg.MIN_PREDICT_COUNT
MAX_PATTERN_SIZE = _cfg.MAX_PATTERN_SIZE
