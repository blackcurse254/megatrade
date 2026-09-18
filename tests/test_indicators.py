import random

from indicators import technical


def make_fake_candles(n=250, start_price=100.0, trend=0.05, seed=42):
    random.seed(seed)
    candles = []
    price = start_price
    for i in range(n):
        price += trend + random.uniform(-1, 1)
        high = price + random.uniform(0, 1)
        low = price - random.uniform(0, 1)
        open_ = price - random.uniform(-0.5, 0.5)
        close = price
        volume = random.uniform(100, 1000)
        candles.append(
            {
                "open_time": i * 300000,
                "open": open_,
                "high": max(open_, close, high),
                "low": min(open_, close, low),
                "close": close,
                "volume": volume,
            }
        )
    return candles


def test_candles_to_df_sorted():
    candles = make_fake_candles(50)
    df = technical.candles_to_df(candles)
    assert list(df["open_time"]) == sorted(df["open_time"])


def test_ema_length_matches_input():
    candles = make_fake_candles(60)
    df = technical.candles_to_df(candles)
    ema9 = technical.ema(df["close"], 9)
    assert len(ema9) == len(df)


def test_rsi_bounds():
    candles = make_fake_candles(100)
    df = technical.candles_to_df(candles)
    rsi_values = technical.rsi(df["close"])
    assert rsi_values.min() >= 0
    assert rsi_values.max() <= 100


def test_analyze_symbol_timeframe_not_enough_candles():
    candles = make_fake_candles(5)
    result = technical.analyze_symbol_timeframe(candles)
    assert result.get("error") == "not_enough_candles"


def test_analyze_symbol_timeframe_full_output_keys():
    candles = make_fake_candles(250)
    result = technical.analyze_symbol_timeframe(candles)
    expected_keys = {
        "last_close",
        "ema9",
        "ema21",
        "ema50",
        "ema200",
        "rsi14",
        "macd",
        "structure",
        "support",
        "resistance",
        "breakout",
        "breakdown",
    }
    assert expected_keys.issubset(result.keys())


def test_support_resistance_are_real_values_from_data():
    candles = make_fake_candles(250)
    df = technical.candles_to_df(candles)
    df = technical.compute_all_indicators(df)
    swings = technical.find_swing_points(df)
    levels = technical.extract_support_resistance(df, swings)
    all_highs = set(round(h, 2) for h in df["high"])
    all_lows = set(round(l, 2) for l in df["low"])
    for level in levels["resistance"]:
        assert level in all_highs
    for level in levels["support"]:
        assert level in all_lows
