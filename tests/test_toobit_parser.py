import pytest

from market import toobit


def test_parse_kline_row_list_format():
    row = [1699999999000, "100.5", "101.2", "99.8", "100.9", "1234.5", 1700000299999]
    parsed = toobit._parse_kline_row(row)
    assert parsed["open"] == 100.5
    assert parsed["high"] == 101.2
    assert parsed["low"] == 99.8
    assert parsed["close"] == 100.9
    assert parsed["volume"] == 1234.5
    assert parsed["open_time"] == 1699999999000


def test_parse_kline_row_dict_format():
    row = {"t": 1699999999000, "o": "100.5", "h": "101.2", "l": "99.8", "c": "100.9", "v": "1234.5"}
    parsed = toobit._parse_kline_row(row)
    assert parsed["close"] == 100.9
    assert parsed["open_time"] == 1699999999000


def test_parse_kline_row_dict_alt_keys():
    row = {"openTime": 1000, "open": "1", "high": "2", "low": "0.5", "close": "1.5", "volume": "10"}
    parsed = toobit._parse_kline_row(row)
    assert parsed["open_time"] == 1000
    assert parsed["close"] == 1.5


def test_parse_kline_row_unrecognized_raises():
    with pytest.raises(toobit.ToobitAPIError):
        toobit._parse_kline_row("not-a-row")


def test_to_float_handles_invalid():
    assert toobit._to_float("abc") == 0.0
    assert toobit._to_float(None) == 0.0
    assert toobit._to_float("12.5") == 12.5
