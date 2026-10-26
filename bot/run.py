"""Usage: python -m bot.run --symbols EURUSD GBPUSD XAUUSD [--tf H1] [--loop 60]

Exness symbols may carry suffixes (e.g. EURUSDm); XM uses e.g. EURUSD or EURUSD#.
Use the exact names shown in your MT5 Market Watch.
"""
import argparse
import time
from datetime import datetime

from bot.mt5_feed import fetch_bars
from bot.scanner import scan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", nargs="+", required=True)
    ap.add_argument("--tf", default="H1")
    ap.add_argument("--loop", type=int, default=0, help="re-scan every N seconds (0 = once)")
    args = ap.parse_args()
    seen = set()
    while True:
        data = fetch_bars(args.symbols, args.tf)
        for sym, sigs in scan(data, datetime.now()).items():
            for s in sigs:
                key = (sym, s.setup, s.direction, data[sym][-1]["time"])
                if key in seen:
                    continue
                seen.add(key)
                print(f"[{datetime.now():%a %H:%M}] {sym} {s.direction.upper()} ({s.setup}) "
                      f"entry {s.entry:.5f} SL {s.stop:.5f} TP {s.target:.5f} RR {s.rr:.1f} - {s.note}")
        if not args.loop:
            break
        time.sleep(args.loop)


if __name__ == "__main__":
    main()
