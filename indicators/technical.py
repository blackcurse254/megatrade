"""
indicators/technical.py
------------------------
محاسبه اندیکاتورهای تکنیکال با pandas + استخراج Price Action و
حمایت/مقاومت از داده واقعی کندل‌ها.
"""

from typing import Dict, List, Any

import numpy as np
import pandas as pd


def candles_to_df(candles: List[Dict[str, float]]) -> pd.DataFrame:
    df = pd.DataFrame(candles)
    df = df.sort_values("open_time").reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# Indicators
# ---------------------------------------------------------------------------

def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    result = 100 - (100 / (1 + rs))
    return result.fillna(50)


def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def stochastic(df: pd.DataFrame, k_period: int = 14, d_period: int = 3):
    low_min = df["low"].rolling(k_period).min()
    high_max = df["high"].rolling(k_period).max()
    denom = (high_max - low_min).replace(0, np.nan)
    percent_k = 100 * (df["close"] - low_min) / denom
    percent_k = percent_k.fillna(50)
    percent_d = percent_k.rolling(d_period).mean().fillna(50)
    return percent_k, percent_d


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False).mean()


def volume_ma(series: pd.Series, period: int = 20) -> pd.Series:
    return series.rolling(period).mean()


def compute_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["ema9"] = ema(out["close"], 9)
    out["ema21"] = ema(out["close"], 21)
    out["ema50"] = ema(out["close"], 50)
    out["ema200"] = ema(out["close"], 200)
    out["rsi14"] = rsi(out["close"], 14)
    macd_line, signal_line, hist = macd(out["close"])
    out["macd"] = macd_line
    out["macd_signal"] = signal_line
    out["macd_hist"] = hist
    k, d = stochastic(out)
    out["stoch_k"] = k
    out["stoch_d"] = d
    out["atr14"] = atr(out)
    out["vol_ma20"] = volume_ma(out["volume"], 20)
    return out


# ---------------------------------------------------------------------------
# Price Action: Swing Highs/Lows, HH/HL/LH/LL, Support/Resistance
# ---------------------------------------------------------------------------

def find_swing_points(df: pd.DataFrame, lookback: int = 3) -> Dict[str, List[int]]:
    """
    تشخیص swing high/low با مقایسه هر کندل با N کندل قبل و بعد از خودش.
    """
    highs = df["high"].values
    lows = df["low"].values
    n = len(df)
    swing_high_idx, swing_low_idx = [], []

    for i in range(lookback, n - lookback):
        window_high = highs[i - lookback : i + lookback + 1]
        window_low = lows[i - lookback : i + lookback + 1]
        if highs[i] == window_high.max():
            swing_high_idx.append(i)
        if lows[i] == window_low.min():
            swing_low_idx.append(i)

    return {"highs": swing_high_idx, "lows": swing_low_idx}


def classify_structure(df: pd.DataFrame, swings: Dict[str, List[int]]) -> str:
    """
    بر اساس دو swing high آخر و دو swing low آخر، ساختار بازار را تخمین می‌زند:
    uptrend / downtrend / range
    """
    highs_idx = swings["highs"][-2:]
    lows_idx = swings["lows"][-2:]

    structure_votes = []

    if len(highs_idx) == 2:
        h1, h2 = df["high"].iloc[highs_idx[0]], df["high"].iloc[highs_idx[1]]
        structure_votes.append("HH" if h2 > h1 else "LH")

    if len(lows_idx) == 2:
        l1, l2 = df["low"].iloc[lows_idx[0]], df["low"].iloc[lows_idx[1]]
        structure_votes.append("HL" if l2 > l1 else "LL")

    if structure_votes == ["HH", "HL"]:
        return "uptrend"
    if structure_votes == ["LH", "LL"]:
        return "downtrend"
    return "range"


def extract_support_resistance(df: pd.DataFrame, swings: Dict[str, List[int]], n_levels: int = 3) -> Dict[str, List[float]]:
    """
    از swing high/low های اخیر، سطوح حمایت/مقاومت واقعی را استخراج می‌کند
    (نه اعداد تصادفی).
    """
    highs = [df["high"].iloc[i] for i in swings["highs"][-8:]]
    lows = [df["low"].iloc[i] for i in swings["lows"][-8:]]

    resistance_levels = sorted(set(round(h, 2) for h in highs), reverse=True)[:n_levels]
    support_levels = sorted(set(round(l, 2) for l in lows))[:n_levels]

    return {"resistance": resistance_levels, "support": support_levels}


def detect_breakout(df: pd.DataFrame, levels: Dict[str, List[float]]) -> Dict[str, Any]:
    """
    بررسی می‌کند آیا آخرین کندل‌ها یک سطح مقاومت/حمایت را با حجم بالا شکسته‌اند.
    """
    if len(df) < 5:
        return {"breakout": False, "breakdown": False, "level": None, "volume_confirmed": False}

    last = df.iloc[-1]
    prev_closes = df["close"].iloc[-5:-1]
    vol_ma_last = df["vol_ma20"].iloc[-1] if "vol_ma20" in df.columns else df["volume"].iloc[-20:].mean()
    volume_confirmed = bool(last["volume"] > (vol_ma_last or 0) * 1.3)

    breakout, breakdown, broken_level = False, False, None

    for level in levels.get("resistance", []):
        if prev_closes.max() < level <= last["close"]:
            breakout = True
            broken_level = level
            break

    for level in levels.get("support", []):
        if prev_closes.min() > level >= last["close"]:
            breakdown = True
            broken_level = level
            break

    return {
        "breakout": breakout,
        "breakdown": breakdown,
        "level": broken_level,
        "volume_confirmed": volume_confirmed,
    }


def detect_retest(df: pd.DataFrame, levels: Dict[str, List[float]], tolerance_pct: float = 0.15) -> Dict[str, Any]:
    """
    بررسی می‌کند قیمت اخیر به یک سطح شکسته‌شده نزدیک شده (retest) یا خیر.
    """
    if df.empty:
        return {"retest": False, "level": None}

    last_close = df["close"].iloc[-1]
    all_levels = levels.get("resistance", []) + levels.get("support", [])

    for level in all_levels:
        if level == 0:
            continue
        distance_pct = abs(last_close - level) / level * 100
        if distance_pct <= tolerance_pct:
            return {"retest": True, "level": level}

    return {"retest": False, "level": None}


def analyze_symbol_timeframe(candles: List[Dict[str, float]]) -> Dict[str, Any]:
    """
    یک تحلیل کامل (indicator + price action) برای یک تایم‌فریم مشخص برمی‌گرداند.
    """
    df = candles_to_df(candles)
    if len(df) < 30:
        return {"error": "not_enough_candles", "candles_count": len(df)}

    df = compute_all_indicators(df)
    swings = find_swing_points(df)
    structure = classify_structure(df, swings)
    levels = extract_support_resistance(df, swings)
    breakout_info = detect_breakout(df, levels)
    retest_info = detect_retest(df, levels)

    last = df.iloc[-1]

    return {
        "last_close": float(last["close"]),
        "ema9": float(last["ema9"]),
        "ema21": float(last["ema21"]),
        "ema50": float(last["ema50"]),
        "ema200": float(last["ema200"]),
        "rsi14": float(last["rsi14"]),
        "macd": float(last["macd"]),
        "macd_signal": float(last["macd_signal"]),
        "macd_hist": float(last["macd_hist"]),
        "stoch_k": float(last["stoch_k"]),
        "stoch_d": float(last["stoch_d"]),
        "atr14": float(last["atr14"]),
        "volume": float(last["volume"]),
        "volume_ma20": float(last["vol_ma20"]) if not pd.isna(last["vol_ma20"]) else None,
        "structure": structure,
        "support": levels["support"],
        "resistance": levels["resistance"],
        "breakout": breakout_info["breakout"],
        "breakdown": breakout_info["breakdown"],
        "broken_level": breakout_info["level"],
        "breakout_volume_confirmed": breakout_info["volume_confirmed"],
        "retest": retest_info["retest"],
        "retest_level": retest_info["level"],
    }
