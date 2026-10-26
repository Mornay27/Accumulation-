"""Weekday-driven setup scanner that outputs actionable entries.

Tuesday   -> high breakouts
Wednesday -> trend continuation
Thursday  -> reversal setups
Friday    -> reversal setups + fake-outs (failed breakouts)

Bars are dicts {"open","high","low","close"[,"time","volume"]}, oldest first.
The last bar must be a CLOSED bar (the MT5 feed drops the forming bar).
"""
from dataclasses import dataclass
from datetime import date, datetime
from typing import Callable, Dict, List, Optional

Bar = Dict[str, float]


@dataclass
class Signal:
    setup: str
    direction: str  # "buy" or "sell"
    entry: float
    stop: float
    target: float
    note: str = ""

    @property
    def rr(self) -> float:
        risk = abs(self.entry - self.stop)
        return abs(self.target - self.entry) / risk if risk else 0.0


def _sma(vals: List[float]) -> float:
    return sum(vals) / len(vals)


def atr(bars: List[Bar], period: int = 14) -> float:
    trs = []
    for p, b in zip(bars[-period - 1:-1], bars[-period:]):
        trs.append(max(b["high"] - b["low"], abs(b["high"] - p["close"]), abs(b["low"] - p["close"])))
    return _sma(trs) if trs else 0.0


def _mk(setup, direction, entry, stop, rr, note=""):
    risk = abs(entry - stop)
    target = entry + rr * risk if direction == "buy" else entry - rr * risk
    return Signal(setup, direction, entry, stop, target, note)


def high_breakout(bars: List[Bar], lookback: int = 20, rr: float = 2.0) -> Optional[Signal]:
    """Close above the prior N-bar high (buy) or below the prior N-bar low (sell)."""
    if len(bars) < max(lookback, 15) + 1:
        return None
    prior = bars[-lookback - 1:-1]
    hi, lo = max(b["high"] for b in prior), min(b["low"] for b in prior)
    last, a = bars[-1], atr(bars)
    if last["close"] > hi:
        return _mk("high_breakout", "buy", last["close"], last["low"] - 0.25 * a, rr, f"broke {hi}")
    if last["close"] < lo:
        return _mk("high_breakout", "sell", last["close"], last["high"] + 0.25 * a, rr, f"broke {lo}")
    return None


def trend_continuation(bars: List[Bar], fast: int = 10, slow: int = 30, rr: float = 2.0) -> Optional[Signal]:
    """Trend (fast vs slow SMA), pullback to fast SMA, close back in trend direction."""
    if len(bars) < slow + 1:
        return None
    closes = [b["close"] for b in bars]
    f, s = _sma(closes[-fast:]), _sma(closes[-slow:])
    last, prev, a = bars[-1], bars[-2], atr(bars)
    if f > s and prev["low"] <= f and last["close"] > f and last["close"] > last["open"]:
        return _mk("trend_continuation", "buy", last["close"], min(prev["low"], last["low"]) - 0.25 * a, rr, "pullback in uptrend")
    if f < s and prev["high"] >= f and last["close"] < f and last["close"] < last["open"]:
        return _mk("trend_continuation", "sell", last["close"], max(prev["high"], last["high"]) + 0.25 * a, rr, "pullback in downtrend")
    return None


def reversal(bars: List[Bar], lookback: int = 10, rr: float = 2.0) -> Optional[Signal]:
    """Engulfing candle against the prior move."""
    if len(bars) < max(lookback + 2, 15):
        return None
    p, b, a = bars[-2], bars[-1], atr(bars)
    move = p["close"] - bars[-lookback - 2]["close"]
    if move < 0 and p["close"] < p["open"] and b["close"] > p["open"] and b["open"] <= p["close"]:
        return _mk("reversal", "buy", b["close"], min(p["low"], b["low"]) - 0.25 * a, rr, "bullish engulfing after decline")
    if move > 0 and p["close"] > p["open"] and b["close"] < p["open"] and b["open"] >= p["close"]:
        return _mk("reversal", "sell", b["close"], max(p["high"], b["high"]) + 0.25 * a, rr, "bearish engulfing after rally")
    return None


def fake_out(bars: List[Bar], lookback: int = 20, rr: float = 2.0) -> Optional[Signal]:
    """Wick beyond range extreme but close back inside -> trade against the failed break."""
    if len(bars) < max(lookback, 15) + 1:
        return None
    prior = bars[-lookback - 1:-1]
    hi, lo = max(b["high"] for b in prior), min(b["low"] for b in prior)
    last, a = bars[-1], atr(bars)
    if last["high"] > hi and last["close"] < hi:
        return _mk("fake_out", "sell", last["close"], last["high"] + 0.25 * a, rr, f"failed break of {hi}")
    if last["low"] < lo and last["close"] > lo:
        return _mk("fake_out", "buy", last["close"], last["low"] - 0.25 * a, rr, f"failed break of {lo}")
    return None


# Monday=0 ... Sunday=6. Monday/weekend: no scan.
SCHEDULE: Dict[int, Dict[str, Callable[[List[Bar]], Optional[Signal]]]] = {
    1: {"high_breakout": high_breakout},
    2: {"trend_continuation": trend_continuation},
    3: {"reversal": reversal},
    4: {"reversal": reversal, "fake_out": fake_out},
}


def scan(data: Dict[str, List[Bar]], today=None) -> Dict[str, List[Signal]]:
    """Return {symbol: [Signal, ...]} for today's strategies."""
    today = today or date.today()
    if isinstance(today, datetime):
        today = today.date()
    strategies = SCHEDULE.get(today.weekday(), {})
    out: Dict[str, List[Signal]] = {}
    for sym, bars in data.items():
        sigs = [s for fn in strategies.values() if (s := fn(bars))]
        if sigs:
            out[sym] = sigs
    return out
