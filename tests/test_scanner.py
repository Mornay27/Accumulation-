from datetime import date
from bot.scanner import scan, SCHEDULE


def bar(o, h, l, c):
    return {"open": o, "high": h, "low": l, "close": c, "volume": 1}


def flat(n):
    return [bar(100, 101, 99, 100) for _ in range(n)]


def test_schedule_days():
    assert list(SCHEDULE) == [1, 2, 3, 4]
    assert set(SCHEDULE[4]) == {"reversal", "fake_out"}


def test_tuesday_breakout_only_on_tuesday():
    bars = flat(25) + [bar(100, 105, 100, 104)]
    assert scan({"X": bars}, date(2026, 10, 27)) == {"X": ["high_breakout"]}
    assert scan({"X": bars}, date(2026, 10, 28)) == {}


def test_friday_fakeout():
    bars = flat(25) + [bar(100, 105, 99.5, 100.5)]
    assert "fake_out" in scan({"X": bars}, date(2026, 10, 30))["X"]


def test_monday_no_scan():
    assert scan({"X": flat(30)}, date(2026, 10, 26)) == {}
