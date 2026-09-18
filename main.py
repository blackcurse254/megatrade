"""
main.py
-------
نقطه ورود اصلی CryptoSignalScanner.

هر ۵ دقیقه (هم‌زمان با بسته شدن کندل 5m) اجرا می‌شود:
1) دریافت داده بازار از Toobit (5m/15m/1h) برای BTCUSDT, ETHUSDT, SOLUSDT
2) محاسبه اندیکاتورها + Price Action
3) پیش‌تحلیل و امتیازدهی داخلی (signal_engine)
4) دریافت خلاصه اخبار (یک‌بار در هر چرخه)
5) تصمیم نهایی از Gemini برای هر نماد (خروجی JSON معتبرشده)
6) فیلتر سیگنال تکراری (storage/state)
7) ارسال یک پیام واحد به تلگرام (یا فقط چاپ در DRY_RUN)

⚠️ این پروژه فقط ابزار هشدار/تحلیل است.
هیچ Order/Buy/Sell/Position/Leverage در این کد وجود ندارد و نباید اضافه شود.
"""

import logging
import logging.handlers
import threading
import time
from datetime import datetime, timezone
from typing import Dict, Any, List

import config
from market import toobit
from indicators import technical
from analysis import signal_engine, gemini
from news import news_engine
from telegram import bot as telegram_bot
from storage import state


# ---------------------------------------------------------------------------
# Logging setup (بدون هیچ‌گونه API key/token در لاگ)
# ---------------------------------------------------------------------------
def setup_logging() -> logging.Logger:
    logger = logging.getLogger("crypto_signal_scanner")
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    file_handler = logging.handlers.RotatingFileHandler(
        config.LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


logger = setup_logging()

_run_lock = threading.Lock()


def analyze_one_symbol(symbol: str, news_summary: str) -> Dict[str, Any]:
    """
    تحلیل کامل یک نماد: داده بازار -> اندیکاتور -> پیش‌تحلیل -> تصمیم Gemini.
    هر خطا در یک نماد باعث توقف کل برنامه نمی‌شود؛ فقط آن نماد WAIT می‌شود.
    """
    try:
        raw_candles = toobit.get_multi_timeframe_klines(symbol, limit=config.CANDLE_LIMIT)
    except Exception as exc:  # noqa: BLE001
        logger.error("[%s] Market data fetch failed: %s", symbol, exc)
        return {"symbol": symbol, "signal": "WAIT", "reason": "market_data_unavailable"}

    try:
        mtf_analysis = {
            tf: technical.analyze_symbol_timeframe(candles)
            for tf, candles in raw_candles.items()
        }
    except Exception as exc:  # noqa: BLE001
        logger.error("[%s] Indicator calculation failed: %s", symbol, exc)
        return {"symbol": symbol, "signal": "WAIT", "reason": "indicator_error"}

    try:
        pre_analysis = signal_engine.build_pre_analysis(symbol, mtf_analysis)
    except Exception as exc:  # noqa: BLE001
        logger.error("[%s] Pre-analysis failed: %s", symbol, exc)
        return {"symbol": symbol, "signal": "WAIT", "reason": "pre_analysis_error"}

    logger.info(
        "[%s] pre-analysis candidate=%s score=%s",
        symbol,
        pre_analysis.get("candidate_direction"),
        pre_analysis.get("confidence_score"),
    )

    decision = gemini.get_final_decision(symbol, pre_analysis, news_summary)
    logger.info("[%s] Gemini decision: %s", symbol, decision.get("signal"))
    return decision


def run_analysis_cycle() -> None:
    if not _run_lock.acquire(blocking=False):
        logger.warning("Previous analysis cycle still running; skipping this tick.")
        return

    try:
        cycle_start = datetime.now(timezone.utc)
        logger.info("=== Starting analysis cycle at %s UTC ===", cycle_start.isoformat())

        try:
            news_summary = news_engine.get_market_news_summary()
        except Exception as exc:  # noqa: BLE001
            logger.error("News engine failed: %s", exc)
            news_summary = ""

        decisions: List[Dict[str, Any]] = []
        for symbol in config.SYMBOLS:
            decision = analyze_one_symbol(symbol, news_summary)
            decisions.append(decision)

        # فیلتر سیگنال تکراری: فقط نمادهایی که تغییر معنادار داشته‌اند اهمیت دارند،
        # اما پیام تلگرام همیشه شامل خلاصه هر سه نماد است.
        any_significant_change = False
        for decision in decisions:
            symbol = decision.get("symbol")
            try:
                if state.should_notify(symbol, decision):
                    any_significant_change = True
                state.save_decision(symbol, decision)
            except Exception as exc:  # noqa: BLE001
                logger.error("[%s] State handling failed: %s", symbol, exc)
                any_significant_change = True  # ایمن: در شک، ارسال کن

        if any_significant_change:
            message = telegram_bot.build_full_message(decisions, news_summary)
            telegram_bot.send_message(message)
        else:
            logger.info("No significant change since last cycle; Telegram message skipped.")

        logger.info("=== Analysis cycle finished ===")
    finally:
        _run_lock.release()


def seconds_until_next_slot(interval_seconds: int) -> float:
    """
    محاسبه زمان باقی‌مانده تا نزدیک‌ترین مضرب interval (مثلاً 00,05,10,...دقیقه)
    تا تحلیل هم‌زمان با بسته شدن کندل انجام شود.
    """
    now = time.time()
    return interval_seconds - (now % interval_seconds)


def main_loop() -> None:
    logger.info(
        "CryptoSignalScanner starting. DRY_RUN=%s | Symbols=%s | Interval=%ss",
        config.DRY_RUN,
        config.SYMBOLS,
        config.ANALYSIS_INTERVAL,
    )

    while True:
        wait_seconds = seconds_until_next_slot(config.ANALYSIS_INTERVAL)
        logger.info("Waiting %.1f seconds until next scheduled run...", wait_seconds)
        time.sleep(max(wait_seconds, 1))

        try:
            run_analysis_cycle()
        except Exception as exc:  # noqa: BLE001
            # هرگز اجازه نده یک خطای پیش‌بینی‌نشده کل برنامه را متوقف کند
            logger.exception("Unhandled error in analysis cycle: %s", exc)


if __name__ == "__main__":
    main_loop()
