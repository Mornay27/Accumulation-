"""Weekday-driven setup scanner.

Tuesday   -> high breakouts
Wednesday -> trend continuation
Thursday  -> reversal setups
Friday    -> reversal setups + fake-outs (failed breakouts)

Bars are dicts: {"open","high","low","close","volume"}, oldest first.
"""
from datetime import date, datetime
from typing import Callable, Dict, List

Bar = Dict[str, float]


def _sma(vals: List[float]) -> float:
    return sum(vals) / len(vals)


def high_breakout(bars: List[Bar], lookback: int = 20) -> bool:
    """Close above the highest high of the prior `lookback` bars."""
    if len(bars) < lookback + 1:
        return False
    prior_high = max(b["high"] for b in bars[-lookback - 1:-1])
    return bars[-1]["close"] > prior_high


def trend_continuation(bars: List[Bar], fast: int = 10, slow: int = 30) -> bool:
    """Uptrend (fast SMA > slow SMA), pullback to fast SMA, then close back above it."""
    if len(bars) < slow + 1:
        return False
    closes = [b["close"] for b in bars]
    f, s = _sma(closes[-fast:]), _sma(closes[-slow:])
    last, prev = bars[-1], bars[-2]
    return f > s and prev["low"] <= f and last["close"] > f and last["close"] > last["open"]


def reversal(bars: List[Bar], lookback: int = 10) -> bool:
    """Bullish engulfing after a decline, or bearish engulfing after a rally."""
    if len(bars) < lookback + 2:
        return False
    a, b = bars[-2], bars[-1]
    move = bars[-2]["close"] - bars[-lookback - 2]["close"]
    bull = move < 0 and a["close"] < a["open"] and b["close"] > a["open"] and b["open"] <= a["close"]
    bear = move > 0 and a["close"] > a["open"] and b["close"] < a["open"] and b["open"] >= a["close"]
    return bull or bear


def fake_out(bars: List[Bar], lookback: int = 20) -> bool:
    """Bar pokes above the prior range high (or below the low) but closes back inside."""
    if len(bars) < lookback + 1:
        return False
    prior = bars[-lookback - 1:-1]
    hi, lo = max(b["high"] for b in prior), min(b["low"] for b in prior)
    last = bars[-1]
    return (last["high"] > hi and last["close"] < hi) or (last["low"] < lo and last["close"] > lo)


# Monday=0 ... Sunday=6. Monday/weekend: no scan.
SCHEDULE: Dict[int, Dict[str, Callable[[List[Bar]], bool]]] = {
    1: {"high_breakout": high_breakout},
    2: {"trend_continuation": trend_continuation},
    3: {"reversal": reversal},
    4: {"reversal": reversal, "fake_out": fake_out},
}


def scan(data: Dict[str, List[Bar]], today=None) -> Dict[str, List[str]]:
    """Return {symbol: [matched setup names]} for today's strategies."""
    today = today or date.today()
    if isinstance(today, datetime):
        today = today.date()
    strategies = SCHEDULE.get(today.weekday(), {})
    out: Dict[str, List[str]] = {}
    for sym, bars in data.items():
        hits = [n for n, fn in strategies.items() if fn(bars)]
        if hits:
            out[sym] = hits
    return out
