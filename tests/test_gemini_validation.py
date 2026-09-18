from analysis import gemini


def test_extract_json_plain():
    text = '{"symbol": "BTCUSDT", "signal": "WAIT", "reason": "no setup"}'
    result = gemini._extract_json(text)
    assert result["signal"] == "WAIT"


def test_extract_json_with_markdown_fence():
    text = '```json\n{"symbol": "BTCUSDT", "signal": "LONG", "confidence": 80}\n```'
    result = gemini._extract_json(text)
    assert result["signal"] == "LONG"


def test_extract_json_invalid_returns_none():
    text = "این یک پاسخ خراب و غیر JSON است"
    result = gemini._extract_json(text)
    assert result is None


def test_validate_decision_wait_minimal():
    data = {"symbol": "ETHUSDT", "signal": "wait", "reason": "sideways"}
    result = gemini._validate_decision(data, "ETHUSDT")
    assert result["signal"] == "WAIT"
    assert result["symbol"] == "ETHUSDT"


def test_validate_decision_invalid_signal_falls_back_to_wait():
    data = {"symbol": "SOLUSDT", "signal": "BUY_NOW", "reason": "x"}
    result = gemini._validate_decision(data, "SOLUSDT")
    assert result["signal"] == "WAIT"


def test_validate_decision_missing_required_field_falls_back_to_wait():
    data = {"symbol": "BTCUSDT", "signal": "LONG", "entry_low": 100}
    result = gemini._validate_decision(data, "BTCUSDT")
    assert result["signal"] == "WAIT"


def test_validate_decision_valid_long():
    data = {
        "symbol": "BTCUSDT",
        "signal": "LONG",
        "entry_low": 75600,
        "entry_high": 75700,
        "stop_loss": 75420,
        "tp1": 75950,
        "tp2": 76200,
        "confidence": 82,
        "reason": "breakout confirmed",
    }
    result = gemini._validate_decision(data, "BTCUSDT")
    assert result["signal"] == "LONG"
    assert result["confidence"] == 82


def test_validate_decision_confidence_clamped():
    data = {
        "symbol": "BTCUSDT",
        "signal": "SHORT",
        "entry_low": 100,
        "entry_high": 101,
        "stop_loss": 105,
        "tp1": 95,
        "tp2": 90,
        "confidence": 250,
        "reason": "x",
    }
    result = gemini._validate_decision(data, "BTCUSDT")
    assert result["confidence"] == 100


def test_non_dict_input_returns_wait():
    result = gemini._validate_decision(["not", "a", "dict"], "BTCUSDT")
    assert result["signal"] == "WAIT"
