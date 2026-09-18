"""
market/toobit.py
-----------------
دریافت داده کندل (Kline) از API عمومی Toobit.

نکته مهم:
Toobit صرافی است که ساختار REST آن مشابه خانواده صرافی‌های Binance-style است.
Endpoint عمومی کندل:

    GET https://api.toobit.com/quote/v1/klines
    params: symbol, interval, limit

این ماژول:
- هیچ API Key نیاز ندارد (فقط داده عمومی بازار).
- فقط GET درخواست می‌دهد. هیچ سفارش خرید/فروشی ارسال نمی‌کند.
- خروجی کندل‌ها معمولاً به دو فرمت رایج بین صرافی‌های خانواده Binance می‌آید:
    1) لیست از لیست‌ها:  [openTime, open, high, low, close, volume, closeTime, ...]
    2) لیست از دیکشنری‌ها: {"t"/"openTime": ..., "o": ..., "h": ..., "l": ..., "c": ..., "v": ...}
  این ماژول هر دو فرمت را پشتیبانی می‌کند تا در برابر تغییرات جزئی API مقاوم باشد.

اگر Toobit ساختار endpoint را در آینده تغییر داد، فقط کافیست BASE_URL / KLINES_PATH
و تابع _parse_kline_row در این فایل به‌روزرسانی شود؛ بقیه پروژه بدون تغییر کار می‌کند.
"""

import logging
import time
from typing import List, Dict, Any

import requests

import config

logger = logging.getLogger("crypto_signal_scanner.market")

KLINES_PATH = "/quote/v1/klines"

# Toobit از فرمت‌های رایج بازه‌ی زمانی استفاده می‌کند: 1m,5m,15m,30m,1h,4h,1d ...
_TIMEFRAME_MAP = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1h",
    "4h": "4h",
    "1d": "1d",
}

MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2


class ToobitAPIError(Exception):
    pass


def _request_with_retry(url: str, params: Dict[str, Any]) -> Any:
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            logger.warning(
                "Toobit request failed (attempt %s/%s): %s", attempt, MAX_RETRIES, exc
            )
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)
    raise ToobitAPIError(f"Toobit request failed after {MAX_RETRIES} attempts: {last_error}")


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _parse_kline_row(row: Any) -> Dict[str, float]:
    """
    یک ردیف کندل خام را به دیکشنری استاندارد تبدیل می‌کند:
    {open_time, open, high, low, close, volume}
    """
    # فرمت لیستی (رایج‌ترین فرمت خانواده Binance-style)
    if isinstance(row, (list, tuple)):
        return {
            "open_time": int(row[0]),
            "open": _to_float(row[1]),
            "high": _to_float(row[2]),
            "low": _to_float(row[3]),
            "close": _to_float(row[4]),
            "volume": _to_float(row[5]) if len(row) > 5 else 0.0,
        }

    # فرمت دیکشنری
    if isinstance(row, dict):
        open_time = row.get("t") or row.get("openTime") or row.get("open_time") or 0
        return {
            "open_time": int(open_time),
            "open": _to_float(row.get("o") or row.get("open")),
            "high": _to_float(row.get("h") or row.get("high")),
            "low": _to_float(row.get("l") or row.get("low")),
            "close": _to_float(row.get("c") or row.get("close")),
            "volume": _to_float(row.get("v") or row.get("volume") or row.get("amount")),
        }

    raise ToobitAPIError(f"Unrecognized kline row format: {row!r}")


def get_klines(symbol: str, timeframe: str, limit: int = 200) -> List[Dict[str, float]]:
    """
    دریافت کندل‌های اخیر یک نماد از Toobit.

    Returns: لیستی از دیکشنری‌ها، مرتب شده از قدیم به جدید:
        [{open_time, open, high, low, close, volume}, ...]
    """
    interval = _TIMEFRAME_MAP.get(timeframe, timeframe)
    url = config.TOOBIT_BASE_URL.rstrip("/") + KLINES_PATH
    params = {"symbol": symbol, "interval": interval, "limit": limit}

    raw = _request_with_retry(url, params)

    # بعضی صرافی‌ها پاسخ را داخل یک dict با کلید data/list برمی‌گردانند
    if isinstance(raw, dict):
        raw_list = raw.get("data") or raw.get("list") or raw.get("result") or []
    elif isinstance(raw, list):
        raw_list = raw
    else:
        raise ToobitAPIError(f"Unexpected response type from Toobit: {type(raw)}")

    if not raw_list:
        raise ToobitAPIError(f"Empty kline response for {symbol} {timeframe}")

    candles = [_parse_kline_row(row) for row in raw_list]
    candles.sort(key=lambda c: c["open_time"])
    return candles


def get_multi_timeframe_klines(symbol: str, limit: int = 200) -> Dict[str, List[Dict[str, float]]]:
    """
    دریافت کندل هر سه تایم‌فریم مورد نیاز (5m/15m/1h) برای یک نماد.
    """
    return {
        "5m": get_klines(symbol, config.TIMEFRAME, limit),
        "15m": get_klines(symbol, config.HTF_TIMEFRAME_1, min(limit, 150)),
        "1h": get_klines(symbol, config.HTF_TIMEFRAME_2, min(limit, 150)),
    }
