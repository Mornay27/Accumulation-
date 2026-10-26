from datetime import date
from bot.scanner import scan, SCHEDULE


def bar(o, h, l, c):
    return {"open": o, "high": h, "low": l, "close": c, "volume": 1}


def flat(n):
    return [bar(100, 101, 99, 100) for _ in range(n)]


def test_schedule_days():
    assert list(SCHEDULE) == [1, 2, 3, 4]
    assert set(SCHEDULE[4]) == {"reversal", "fake_out"}


def test_tuesday_breakout_entry():
    bars = flat(25) + [bar(100, 105, 100, 104)]
    s = scan({"X": bars}, date(2026, 10, 27))["X"][0]
    assert (s.setup, s.direction, s.entry) == ("high_breakout", "buy", 104)
    assert s.stop < s.entry < s.target
    assert scan({"X": bars}, date(2026, 10, 28)) == {}


def test_friday_fakeout_sell():
    bars = flat(25) + [bar(100, 105, 99.5, 100.5)]
    sigs = scan({"X": bars}, date(2026, 10, 30))["X"]
    s = [x for x in sigs if x.setup == "fake_out"][0]
    assert s.direction == "sell" and s.target < s.entry < s.stop


def test_monday_no_scan():
    assert scan({"X": flat(30)}, date(2026, 10, 26)) == {}
