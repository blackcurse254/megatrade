import os
import tempfile

import config
from storage import state


def setup_function(_):
    tmp_dir = tempfile.mkdtemp()
    config.STATE_FILE = os.path.join(tmp_dir, "state.json")


def test_first_signal_always_notifies():
    decision = {"symbol": "BTCUSDT", "signal": "WAIT", "reason": "no setup"}
    assert state.should_notify("BTCUSDT", decision) is True


def test_wait_to_wait_does_not_notify():
    state.save_decision("BTCUSDT", {"symbol": "BTCUSDT", "signal": "WAIT", "reason": "a"})
    new_decision = {"symbol": "BTCUSDT", "signal": "WAIT", "reason": "b"}
    assert state.should_notify("BTCUSDT", new_decision) is False


def test_wait_to_long_notifies():
    state.save_decision("BTCUSDT", {"symbol": "BTCUSDT", "signal": "WAIT", "reason": "a"})
    new_decision = {
        "symbol": "BTCUSDT",
        "signal": "LONG",
        "entry_low": 100,
        "entry_high": 101,
        "stop_loss": 95,
        "tp1": 110,
        "tp2": 115,
        "confidence": 80,
        "reason": "breakout",
    }
    assert state.should_notify("BTCUSDT", new_decision) is True


def test_same_long_signal_small_change_does_not_notify():
    old = {
        "symbol": "BTCUSDT",
        "signal": "LONG",
        "entry_low": 100,
        "entry_high": 101,
        "stop_loss": 95,
        "tp1": 110,
        "tp2": 115,
        "confidence": 80,
        "reason": "breakout",
    }
    state.save_decision("BTCUSDT", old)
    new = dict(old)
    new["entry_low"] = 100.05  # تغییر ناچیز
    assert state.should_notify("BTCUSDT", new) is False


def test_same_long_signal_big_sl_change_notifies():
    old = {
        "symbol": "BTCUSDT",
        "signal": "LONG",
        "entry_low": 100,
        "entry_high": 101,
        "stop_loss": 95,
        "tp1": 110,
        "tp2": 115,
        "confidence": 80,
        "reason": "breakout",
    }
    state.save_decision("BTCUSDT", old)
    new = dict(old)
    new["stop_loss"] = 90  # تغییر بزرگ
    assert state.should_notify("BTCUSDT", new) is True


def test_long_to_short_notifies():
    state.save_decision(
        "BTCUSDT",
        {
            "symbol": "BTCUSDT",
            "signal": "LONG",
            "entry_low": 100,
            "entry_high": 101,
            "stop_loss": 95,
            "tp1": 110,
            "tp2": 115,
            "confidence": 80,
            "reason": "x",
        },
    )
    new_decision = {
        "symbol": "BTCUSDT",
        "signal": "SHORT",
        "entry_low": 100,
        "entry_high": 101,
        "stop_loss": 105,
        "tp1": 90,
        "tp2": 85,
        "confidence": 75,
        "reason": "reversal",
    }
    assert state.should_notify("BTCUSDT", new_decision) is True
