"""
storage/state.py
-----------------
ذخیره‌سازی وضعیت آخرین سیگنال هر نماد در یک فایل JSON، برای جلوگیری از
ارسال تکراری سیگنال مشابه در هر اجرای ۵ دقیقه‌ای.

معیارهای «تغییر معنادار» که باعث ارسال دوباره می‌شوند:
- تغییر signal (WAIT <-> LONG/SHORT یا LONG <-> SHORT)
- تغییر قابل‌توجه Entry zone
- تغییر مهم SL/TP
"""

import json
import logging
import os
from typing import Dict, Any

import config

logger = logging.getLogger("crypto_signal_scanner.state")

SIGNIFICANT_PRICE_CHANGE_PCT = 0.5  # درصد تغییر برای معنادار بودن


def _load_state() -> Dict[str, Any]:
    if not os.path.exists(config.STATE_FILE):
        return {}
    try:
        with open(config.STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not read state file, starting fresh: %s", exc)
        return {}


def _save_state(state: Dict[str, Any]) -> None:
    tmp_path = config.STATE_FILE + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, config.STATE_FILE)
    except OSError as exc:
        logger.error("Failed to save state file: %s", exc)


def _pct_change(old: float, new: float) -> float:
    if old in (None, 0):
        return 100.0
    return abs(new - old) / abs(old) * 100


def _is_significant_change(old: Dict[str, Any], new: Dict[str, Any]) -> bool:
    old_signal = old.get("signal")
    new_signal = new.get("signal")

    if old_signal != new_signal:
        return True

    if new_signal == "WAIT":
        return False  # WAIT -> WAIT هیچ‌وقت دوباره ارسال نمی‌شود

    fields_to_check = ["entry_low", "entry_high", "stop_loss", "tp1", "tp2"]
    for field in fields_to_check:
        old_val = old.get(field)
        new_val = new.get(field)
        if old_val is None or new_val is None:
            continue
        if _pct_change(old_val, new_val) >= SIGNIFICANT_PRICE_CHANGE_PCT:
            return True

    return False


def should_notify(symbol: str, new_decision: Dict[str, Any]) -> bool:
    state = _load_state()
    old_decision = state.get(symbol)

    if old_decision is None:
        return True  # اولین بار برای این نماد

    return _is_significant_change(old_decision, new_decision)


def save_decision(symbol: str, decision: Dict[str, Any]) -> None:
    state = _load_state()
    state[symbol] = decision
    _save_state(state)
