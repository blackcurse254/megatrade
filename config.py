"""
Config
------
تمام تنظیمات پروژه از اینجا خوانده می‌شود.
هیچ API Key در این فایل هاردکد نشده؛ همه چیز از .env خوانده می‌شود.
"""

import os
from dotenv import load_dotenv

load_dotenv()


def _get_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


def _get_float(name: str, default: float) -> float:
    val = os.getenv(name)
    try:
        return float(val) if val is not None else default
    except ValueError:
        return default


def _get_int(name: str, default: int) -> int:
    val = os.getenv(name)
    try:
        return int(val) if val is not None else default
    except ValueError:
        return default


# ---------------------------------------------------------------------------
# Secrets (فقط از env خوانده می‌شوند - هرگز هاردکد نشوند)
# ---------------------------------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ---------------------------------------------------------------------------
# Market
# ---------------------------------------------------------------------------
SYMBOLS = [s.strip() for s in os.getenv("SYMBOLS", "BTCUSDT,ETHUSDT,SOLUSDT").split(",") if s.strip()]
TIMEFRAME = os.getenv("TIMEFRAME", "5m")
HTF_TIMEFRAME_1 = os.getenv("HTF_TIMEFRAME_1", "15m")
HTF_TIMEFRAME_2 = os.getenv("HTF_TIMEFRAME_2", "1h")

CANDLE_LIMIT = _get_int("CANDLE_LIMIT", 200)
TOOBIT_BASE_URL = os.getenv("TOOBIT_BASE_URL", "https://api.toobit.com")

# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------
ANALYSIS_INTERVAL = _get_int("ANALYSIS_INTERVAL", 300)  # seconds (5 min)

# ---------------------------------------------------------------------------
# Signal thresholds
# ---------------------------------------------------------------------------
MIN_CONFIDENCE = _get_int("MIN_CONFIDENCE", 70)
MIN_RISK_REWARD = _get_float("MIN_RISK_REWARD", 1.5)

# ---------------------------------------------------------------------------
# Gemini
# ---------------------------------------------------------------------------
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
GEMINI_TIMEOUT = _get_int("GEMINI_TIMEOUT", 30)

# ---------------------------------------------------------------------------
# Safety / Mode
# ---------------------------------------------------------------------------
DRY_RUN = _get_bool("DRY_RUN", True)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, "app.log")
STATE_FILE = os.path.join(BASE_DIR, "storage", "state.json")

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
