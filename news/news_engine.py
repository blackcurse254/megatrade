"""
news/news_engine.py
--------------------
دریافت خلاصه اخبار مهم بازار کریپتو با استفاده از Gemini + Google Search grounding.

این تابع یک‌بار در هر چرخه اسکن صدا زده می‌شود (نه به‌ازای هر نماد) تا در
تعداد درخواست‌ها صرفه‌جویی شود، و خروجی آن به همه نمادها داده می‌شود.

اگر grounding در دسترس نبود یا خطا داد، سیستم crash نمی‌کند؛ فقط یک پیام
خنثی برمی‌گرداند و تحلیل بدون اخبار تازه ادامه می‌یابد (Gemini در prompt
نهایی محافظه‌کارتر عمل می‌کند).
"""

import logging
from typing import Any, Dict

import requests

import config

logger = logging.getLogger("crypto_signal_scanner.news")

GEMINI_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)

NEWS_PROMPT = """با استفاده از جستجوی وب، مهم‌ترین اخبار و رویدادهای چند ساعت اخیر (حداکثر ۱۲ ساعت گذشته)
مرتبط با موضوعات زیر را بررسی کن:

Bitcoin, Ethereum, Solana, Crypto market, Federal Reserve, Interest rates, CPI, PPI, FOMC, ETF,
SEC, Major regulations, Major hacks, Exchange incidents, Major economic releases.

فقط اخبار واقعاً تازه را گزارش کن؛ اخبار قدیمی یا تکراری را به‌عنوان خبر جدید معرفی نکن.
اگر هیچ خبر مهمی وجود ندارد، همین را به‌صراحت بگو.

خروجی: حداکثر ۵ خط، کوتاه، خلاصه و به فارسی. برای هر خبر مهم بگو که ریسک آن
برای بازار کریپتو بالا/متوسط/پایین است.
"""

DEFAULT_NEWS_SUMMARY = "اخبار مهم و تازه‌ای در دسترس نبود یا سرویس اخبار موقتاً در دسترس نیست. تحلیل بدون فاکتور خبری ادامه یافت."


def get_market_news_summary() -> str:
    if not config.GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set; skipping news lookup")
        return DEFAULT_NEWS_SUMMARY

    url = GEMINI_ENDPOINT.format(model=config.GEMINI_MODEL)
    payload: Dict[str, Any] = {
        "contents": [{"role": "user", "parts": [{"text": NEWS_PROMPT}]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {"temperature": 0.1},
    }
    headers = {"Content-Type": "application/json"}
    params = {"key": config.GEMINI_API_KEY}

    try:
        resp = requests.post(url, params=params, headers=headers, json=payload, timeout=config.GEMINI_TIMEOUT)
        resp.raise_for_status()
        body = resp.json()
        text = body["candidates"][0]["content"]["parts"][0]["text"]
        return text.strip() or DEFAULT_NEWS_SUMMARY
    except Exception as exc:  # noqa: BLE001
        logger.error("News lookup failed: %s", exc)
        return DEFAULT_NEWS_SUMMARY
