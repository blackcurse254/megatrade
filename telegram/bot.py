"""
telegram/bot.py
----------------
ارسال پیام نهایی به تلگرام با استفاده از Bot API (فقط sendMessage).
از کتابخانه سبک requests استفاده می‌شود تا هیچ وابستگی اضافی/تداخل نام‌گذاری
با پوشه telegram/ این پروژه ایجاد نشود.

در حالت DRY_RUN=true هیچ پیامی ارسال نمی‌شود؛ فقط در ترمینال/لاگ چاپ می‌شود.
"""

import logging
from typing import Dict, Any, List

import requests

import config

logger = logging.getLogger("crypto_signal_scanner.telegram")

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"

_SIGNAL_EMOJI = {"LONG": "🟢", "SHORT": "🔴", "WAIT": "⚪"}


def _fmt_num(value: Any) -> str:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return str(value)
    if value >= 100:
        return f"{value:,.2f}"
    return f"{value:.5f}".rstrip("0").rstrip(".")


def format_signal_block(decision: Dict[str, Any]) -> str:
    signal = decision.get("signal", "WAIT")
    symbol = decision.get("symbol", "?")
    emoji = _SIGNAL_EMOJI.get(signal, "⚪")

    if signal == "WAIT":
        reason = decision.get("reason", "No confirmed setup")
        return f"{emoji} {symbol} — WAIT\n{reason}"

    lines = [
        f"{emoji} {symbol} — {signal}",
        f"Entry: {_fmt_num(decision.get('entry_low'))}–{_fmt_num(decision.get('entry_high'))}",
        f"SL: {_fmt_num(decision.get('stop_loss'))}",
        f"TP1: {_fmt_num(decision.get('tp1'))}",
        f"TP2: {_fmt_num(decision.get('tp2'))}",
    ]
    reason = decision.get("reason")
    if reason:
        lines.append(f"Confirm: {reason}")
    return "\n".join(lines)


def build_full_message(decisions: List[Dict[str, Any]], news_summary: str) -> str:
    all_wait = all(d.get("signal") == "WAIT" for d in decisions)

    if all_wait:
        lines = ["⚪ NO TRADE", ""]
        for d in decisions:
            lines.append(f"{d.get('symbol')}: WAIT")
        lines.append("")
        lines.append("No confirmed setup.")
        return "\n".join(lines)

    lines = ["📊 CRYPTO SIGNAL", f"⏱ {config.TIMEFRAME.upper()}", ""]
    for d in decisions:
        lines.append(format_signal_block(d))
        lines.append("")

    if news_summary:
        lines.append("📰 NEWS")
        lines.append(news_summary.strip()[:500])
        lines.append("")

    lines.append("⚠️ Risk: این پیام صرفاً هشدار تحلیلی است و توصیه مالی قطعی نیست.")
    return "\n".join(lines).strip()


def send_message(text: str) -> bool:
    if config.DRY_RUN:
        logger.info("[DRY_RUN] Telegram message NOT sent. Preview:\n%s", text)
        print("\n----- DRY RUN: TELEGRAM PREVIEW -----")
        print(text)
        print("--------------------------------------\n")
        return True

    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        logger.error("Telegram credentials are missing; cannot send message.")
        return False

    url = TELEGRAM_API_URL.format(token=config.TELEGRAM_BOT_TOKEN)
    payload = {"chat_id": config.TELEGRAM_CHAT_ID, "text": text}

    try:
        resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        logger.info("Telegram message sent successfully.")
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to send Telegram message: %s", exc)
        return False
