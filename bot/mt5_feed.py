"""MetaTrader 5 data feed (works with Exness and XM MT5 accounts).

Requires: Windows, MetaTrader5 terminal installed and logged in to the broker,
and `pip install MetaTrader5`. Read-only: no orders are placed.
"""
from typing import Dict, List, Optional


def fetch_bars(symbols: List[str], timeframe: str = "H1", count: int = 200,
               login: Optional[int] = None, password: Optional[str] = None,
               server: Optional[str] = None) -> Dict[str, List[dict]]:
    import MetaTrader5 as mt5  # imported lazily so the scanner works without it

    kwargs = {}
    if login:
        kwargs = {"login": login, "password": password, "server": server}
    if not mt5.initialize(**kwargs):
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
    try:
        tf = getattr(mt5, f"TIMEFRAME_{timeframe.upper()}")
        out = {}
        for sym in symbols:
            mt5.symbol_select(sym, True)
            rates = mt5.copy_rates_from_pos(sym, tf, 0, count + 1)
            if rates is None or len(rates) < 2:
                continue
            # drop the still-forming bar so signals use closed candles only
            out[sym] = [{"time": int(r["time"]), "open": float(r["open"]), "high": float(r["high"]),
                         "low": float(r["low"]), "close": float(r["close"]),
                         "volume": float(r["tick_volume"])} for r in rates[:-1]]
        return out
    finally:
        mt5.shutdown()
