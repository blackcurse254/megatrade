"""
analysis/gemini.py
-------------------
ارتباط با Gemini API برای گرفتن تصمیم تحلیلی نهایی به‌صورت JSON ساختاریافته.

- Gemini هرگز مستقیم سفارش نمی‌دهد؛ فقط JSON تحلیلی برمی‌گرداند.
- اگر پاسخ Gemini خراب یا غیر-JSON بود، سیستم crash نمی‌کند و آن نماد WAIT در نظر گرفته می‌شود.
- کلید API هرگز در کد یا لاگ ذخیره نمی‌شود؛ فقط از متغیر محیطی خوانده می‌شود.
"""

import json
import logging
import re
from typing import Dict, Any, Optional

import requests

import config

logger = logging.getLogger("crypto_signal_scanner.gemini")

GEMINI_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)

SYSTEM_PROMPT = """تو یک تحلیلگر تکنیکال و بازار کریپتو هستی که برای یک سیستم هشدار (نه معامله خودکار) کار می‌کنی.

هدف تو پیش‌بینی قطعی قیمت نیست؛ هدف شناسایی setupهای دارای تأیید چندگانه (Confluence) است.

قوانین سخت‌گیرانه‌ای که باید رعایت کنی:
1. هرگز فقط بر اساس یک اندیکاتور تصمیم نگیر. باید حداقل چند تأییدیه مستقل (ساختار بازار، EMA، RSI، MACD، Stochastic، حجم، Price Action) هم‌جهت باشند.
2. اگر setup واضح و قابل دفاع نیست، سیگنال باید WAIT باشد. WAIT کاملاً قابل قبول و اغلب ترجیح داده‌شده است.
3. اگر قیمت دقیقاً روی یک حمایت مهم است، بدون شکست و تأیید معتبر، سیگنال SHORT نده.
4. اگر قیمت دقیقاً روی یک مقاومت مهم است، بدون شکست و تأیید معتبر، سیگنال LONG نده.
5. اگر حجم شکست (breakout volume) کافی نیست، WAIT بده.
6. اگر Risk/Reward پیشنهادی کمتر از حداقل مجاز است، WAIT بده.
7. اگر تایم‌فریم‌های بالاتر (15m و 1h) به‌شدت مخالف جهت سیگنال 5m هستند، سیگنال را WAIT کن یا اعتبار آن را به‌وضوح در reason کاهش بده.
8. اگر خبر مهم، پرریسک یا رویداد اقتصادی حساس (FOMC, CPI, نرخ بهره, هک بزرگ, رگولاتوری بزرگ) در چند ساعت اخیر/آینده نزدیک وجود دارد، محافظه‌کارانه‌تر عمل کن و در شرایط مبهم WAIT بده.
9. هرگز سیگنال را به‌عنوان تضمینی یا قطعی معرفی نکن؛ در reason این را با لحنی حرفه‌ای و کوتاه منعکس کن.
10. خروجی تو همیشه فقط یک JSON معتبر است، بدون هیچ متن اضافه، بدون Markdown، بدون توضیح خارج از JSON.

فرمت خروجی الزامی (فقط یکی از این دو حالت):

حالت سیگنال معتبر:
{"symbol": "BTCUSDT", "signal": "LONG", "entry_low": 0, "entry_high": 0, "stop_loss": 0, "tp1": 0, "tp2": 0, "confidence": 0, "reason": "..."}

حالت WAIT:
{"symbol": "BTCUSDT", "signal": "WAIT", "reason": "..."}

signal فقط می‌تواند یکی از این سه مقدار باشد: LONG, SHORT, WAIT.
confidence عددی بین 0 تا 100 است و نباید به‌عنوان احتمال قطعی موفقیت معامله تفسیر شود.
reason باید کوتاه (حداکثر ۲۵۰ کاراکتر) و فارسی یا انگلیسی روان باشد.
"""


class GeminiResponseError(Exception):
    pass


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    """
    تلاش برای استخراج و parse کردن JSON از متن پاسخ مدل،
    حتی اگر مدل اشتباهاً متن اضافه یا Markdown fence دور آن گذاشته باشد.
    """
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text.strip(), flags=re.IGNORECASE).strip()
    text = re.sub(r"```$", "", text.strip()).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return None


def _validate_decision(data: Dict[str, Any], symbol: str) -> Dict[str, Any]:
    """
    اعتبارسنجی ساختار JSON بازگشتی. در صورت نامعتبر بودن، WAIT ایمن برمی‌گرداند.
    """
    if not isinstance(data, dict):
        return {"symbol": symbol, "signal": "WAIT", "reason": "invalid_response_structure"}

    signal = str(data.get("signal", "WAIT")).upper()
    if signal not in ("LONG", "SHORT", "WAIT"):
        return {"symbol": symbol, "signal": "WAIT", "reason": "invalid_signal_value"}

    result = {
        "symbol": data.get("symbol", symbol),
        "signal": signal,
        "reason": str(data.get("reason", ""))[:400],
    }

    if signal in ("LONG", "SHORT"):
        required = ["entry_low", "entry_high", "stop_loss", "tp1", "tp2", "confidence"]
        for field in required:
            val = data.get(field)
            if val is None:
                return {"symbol": symbol, "signal": "WAIT", "reason": f"missing_field:{field}"}
            try:
                result[field] = float(val)
            except (TypeError, ValueError):
                return {"symbol": symbol, "signal": "WAIT", "reason": f"invalid_field:{field}"}

        result["confidence"] = max(0, min(100, result["confidence"]))

    return result


def _call_gemini_raw(prompt: str, timeout: int = None) -> str:
    if not config.GEMINI_API_KEY:
        raise GeminiResponseError("GEMINI_API_KEY is not set")

    url = GEMINI_ENDPOINT.format(model=config.GEMINI_MODEL)
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
        },
    }
    headers = {"Content-Type": "application/json"}
    params = {"key": config.GEMINI_API_KEY}

    resp = requests.post(
        url,
        params=params,
        headers=headers,
        json=payload,
        timeout=timeout or config.GEMINI_TIMEOUT,
    )
    resp.raise_for_status()
    body = resp.json()

    try:
        return body["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as exc:
        raise GeminiResponseError(f"Unexpected Gemini response shape: {body}") from exc


def get_final_decision(symbol: str, pre_analysis: Dict[str, Any], news_summary: str) -> Dict[str, Any]:
    """
    ارسال داده خام+محاسبه‌شده به Gemini و دریافت تصمیم نهایی JSON.
    در هر خطایی، به‌جای crash، یک WAIT ایمن برمی‌گرداند.
    """
    user_prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"=== DATA FOR {symbol} ===\n"
        f"{json.dumps(pre_analysis, ensure_ascii=False, default=str)}\n\n"
        f"=== RECENT NEWS SUMMARY ===\n"
        f"{news_summary}\n\n"
        f"حالا فقط JSON خروجی را برای {symbol} برگردان."
    )

    try:
        raw_text = _call_gemini_raw(user_prompt)
    except Exception as exc:  # noqa: BLE001
        logger.error("Gemini call failed for %s: %s", symbol, exc)
        return {"symbol": symbol, "signal": "WAIT", "reason": "gemini_call_failed"}

    parsed = _extract_json(raw_text)
    if parsed is None:
        logger.error("Gemini returned non-JSON response for %s", symbol)
        return {"symbol": symbol, "signal": "WAIT", "reason": "gemini_invalid_json"}

    return _validate_decision(parsed, symbol)
