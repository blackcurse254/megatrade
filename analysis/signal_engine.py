"""
analysis/signal_engine.py
--------------------------
منطق پیش-پردازش سیگنال (قبل از ارسال به Gemini):
- ترکیب چند تأییدیه (نه فقط یک اندیکاتور)
- فیلتر Multi-timeframe (5m / 15m / 1h)
- محاسبه Confidence Score داخلی (0-100) - فقط برای فیلتر داخلی، در تلگرام نمایش داده نمی‌شود
- محاسبه Entry / SL / TP بر اساس ساختار بازار + ATR + Risk/Reward

خروجی این ماژول به‌عنوان "داده خام و محاسبه‌شده" به Gemini داده می‌شود تا
Gemini تصمیم تحلیلی نهایی را بگیرد. این ماژول خودش تصمیم قطعی نمی‌گیرد.
"""

from typing import Dict, Any

import config


def _trend_bias(tf_data: Dict[str, Any]) -> str:
    """
    bias صعودی/نزولی/خنثی یک تایم‌فریم را بر اساس EMA ها و ساختار تخمین می‌زند.
    """
    if tf_data.get("error"):
        return "unknown"

    price = tf_data["last_close"]
    ema50 = tf_data["ema50"]
    ema200 = tf_data["ema200"]
    structure = tf_data["structure"]

    bullish_votes = 0
    bearish_votes = 0

    if price > ema50:
        bullish_votes += 1
    else:
        bearish_votes += 1

    if ema50 > ema200:
        bullish_votes += 1
    else:
        bearish_votes += 1

    if structure == "uptrend":
        bullish_votes += 1
    elif structure == "downtrend":
        bearish_votes += 1

    if bullish_votes >= 2 and bullish_votes > bearish_votes:
        return "bullish"
    if bearish_votes >= 2 and bearish_votes > bullish_votes:
        return "bearish"
    return "neutral"


def score_long_setup(tf5: Dict[str, Any], tf15_bias: str, tf1h_bias: str) -> Dict[str, Any]:
    checks = {}
    checks["structure_up"] = tf5["structure"] == "uptrend"
    checks["price_above_ema"] = tf5["last_close"] > tf5["ema50"]
    checks["rsi_ok"] = 45 <= tf5["rsi14"] <= 70
    checks["macd_confirm"] = tf5["macd_hist"] > 0
    checks["stoch_confirm"] = tf5["stoch_k"] > tf5["stoch_d"] and tf5["stoch_k"] < 85
    checks["volume_confirm"] = tf5["breakout_volume_confirmed"] or (
        tf5["volume_ma20"] and tf5["volume"] > tf5["volume_ma20"]
    )
    checks["breakout_or_retest"] = tf5["breakout"] or (tf5["retest"] and tf5["last_close"] > (tf5["retest_level"] or 0))
    checks["support_valid"] = len(tf5["support"]) > 0
    checks["htf_confirm"] = tf15_bias in ("bullish", "neutral") and tf1h_bias in ("bullish", "neutral")
    checks["htf_strong_confirm"] = tf15_bias == "bullish" and tf1h_bias == "bullish"

    weights = {
        "structure_up": 15,
        "price_above_ema": 10,
        "rsi_ok": 10,
        "macd_confirm": 10,
        "stoch_confirm": 8,
        "volume_confirm": 12,
        "breakout_or_retest": 15,
        "support_valid": 5,
        "htf_confirm": 10,
        "htf_strong_confirm": 5,
    }

    score = sum(weights[k] for k, v in checks.items() if v)
    return {"direction": "LONG", "score": score, "checks": checks}


def score_short_setup(tf5: Dict[str, Any], tf15_bias: str, tf1h_bias: str) -> Dict[str, Any]:
    checks = {}
    checks["structure_down"] = tf5["structure"] == "downtrend"
    checks["price_below_ema"] = tf5["last_close"] < tf5["ema50"]
    checks["rsi_ok"] = 30 <= tf5["rsi14"] <= 55
    checks["macd_confirm"] = tf5["macd_hist"] < 0
    checks["stoch_confirm"] = tf5["stoch_k"] < tf5["stoch_d"] and tf5["stoch_k"] > 15
    checks["volume_confirm"] = tf5["breakout_volume_confirmed"] or (
        tf5["volume_ma20"] and tf5["volume"] > tf5["volume_ma20"]
    )
    checks["breakout_or_retest"] = tf5["breakdown"] or (tf5["retest"] and tf5["last_close"] < (tf5["retest_level"] or float("inf")))
    checks["resistance_valid"] = len(tf5["resistance"]) > 0
    checks["htf_confirm"] = tf15_bias in ("bearish", "neutral") and tf1h_bias in ("bearish", "neutral")
    checks["htf_strong_confirm"] = tf15_bias == "bearish" and tf1h_bias == "bearish"

    weights = {
        "structure_down": 15,
        "price_below_ema": 10,
        "rsi_ok": 10,
        "macd_confirm": 10,
        "stoch_confirm": 8,
        "volume_confirm": 12,
        "breakout_or_retest": 15,
        "resistance_valid": 5,
        "htf_confirm": 10,
        "htf_strong_confirm": 5,
    }

    score = sum(weights[k] for k, v in checks.items() if v)
    return {"direction": "SHORT", "score": score, "checks": checks}


def compute_entry_sl_tp(direction: str, tf5: Dict[str, Any]) -> Dict[str, Any]:
    """
    Entry/SL/TP بر اساس ساختار بازار + ATR (نه درصد ثابت).
    """
    price = tf5["last_close"]
    atr_val = tf5["atr14"] or (price * 0.003)
    support = tf5["support"]
    resistance = tf5["resistance"]

    if direction == "LONG":
        entry_low = price
        entry_high = price * 1.0015
        structural_sl = max(support) if support else price - atr_val * 1.5
        sl = min(structural_sl, price - atr_val * 1.2)
        sl = min(sl, price - atr_val * 0.5)  # اطمینان از فاصله معنادار
        risk = price - sl
        tp1 = price + max(risk * config.MIN_RISK_REWARD, atr_val * 1.5)
        tp2 = price + max(risk * (config.MIN_RISK_REWARD + 0.5), atr_val * 2.5)
        if resistance:
            nearest_res = min([r for r in resistance if r > price], default=None)
            if nearest_res:
                tp1 = min(tp1, nearest_res)
    elif direction == "SHORT":
        entry_low = price * 0.9985
        entry_high = price
        structural_sl = min(resistance) if resistance else price + atr_val * 1.5
        sl = max(structural_sl, price + atr_val * 1.2)
        sl = max(sl, price + atr_val * 0.5)
        risk = sl - price
        tp1 = price - max(risk * config.MIN_RISK_REWARD, atr_val * 1.5)
        tp2 = price - max(risk * (config.MIN_RISK_REWARD + 0.5), atr_val * 2.5)
        if support:
            nearest_sup = max([s for s in support if s < price], default=None)
            if nearest_sup:
                tp1 = max(tp1, nearest_sup)
    else:
        return {}

    risk = abs(price - sl)
    reward = abs(tp1 - price)
    rr = round(reward / risk, 2) if risk > 0 else 0

    return {
        "entry_low": round(min(entry_low, entry_high), 6),
        "entry_high": round(max(entry_low, entry_high), 6),
        "stop_loss": round(sl, 6),
        "tp1": round(tp1, 6),
        "tp2": round(tp2, 6),
        "risk_reward": rr,
    }


def build_pre_analysis(symbol: str, mtf_analysis: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    خروجی نهایی این ماژول: یک بسته کامل داده خام + محاسبه‌شده که به Gemini داده می‌شود.
    """
    tf5 = mtf_analysis.get("5m", {})
    tf15 = mtf_analysis.get("15m", {})
    tf1h = mtf_analysis.get("1h", {})

    if tf5.get("error"):
        return {"symbol": symbol, "signal": "WAIT", "reason": "insufficient_candle_data"}

    tf15_bias = _trend_bias(tf15)
    tf1h_bias = _trend_bias(tf1h)

    long_result = score_long_setup(tf5, tf15_bias, tf1h_bias)
    short_result = score_short_setup(tf5, tf15_bias, tf1h_bias)

    best = long_result if long_result["score"] >= short_result["score"] else short_result

    candidate_direction = "WAIT"
    trade_levels = {}

    if best["score"] >= config.MIN_CONFIDENCE:
        candidate_direction = best["direction"]
        trade_levels = compute_entry_sl_tp(candidate_direction, tf5)
        if trade_levels and trade_levels.get("risk_reward", 0) < config.MIN_RISK_REWARD:
            candidate_direction = "WAIT"
            trade_levels = {}

    return {
        "symbol": symbol,
        "candidate_direction": candidate_direction,
        "confidence_score": best["score"],
        "checks": best["checks"],
        "trade_levels": trade_levels,
        "timeframe_5m": tf5,
        "timeframe_15m": tf15,
        "timeframe_1h": tf1h,
        "htf_bias": {"15m": tf15_bias, "1h": tf1h_bias},
    }
