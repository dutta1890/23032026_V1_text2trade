#!/usr/bin/env python3
"""Data ingestion engine for Text2trade.

Downloads historical OHLCV data from NSE India and stores in MongoDB.
Run after market hours (post 4 PM IST) for best reliability.

Usage:
    python scripts/ingest_data.py
    python scripts/ingest_data.py --symbols RELIANCE,TCS
    python scripts/ingest_data.py --daily-only
"""

import os
import sys
import time
import argparse
import logging
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

import pandas as pd
from pymongo import MongoClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# MongoDB
mongo_client = MongoClient(os.environ.get("MONGO_URL"))
db = mongo_client[os.environ.get("DB_NAME", "text2trade")]
market_data = db["market_data"]

# Create compound unique index
market_data.create_index(
    [("symbol", 1), ("timeframe", 1), ("timestamp", 1)],
    unique=True,
)

# Instruments
EQUITY_SYMBOLS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
    "HINDUNILVR", "ITC", "SBIN", "BHARTIARTL", "KOTAKBANK",
    "LT", "AXISBANK", "ASIANPAINT", "MARUTI", "BAJFINANCE",
    "TITAN", "SUNPHARMA", "HCLTECH", "WIPRO", "TATAMOTORS",
]
INDEX_SYMBOLS = ["NIFTY 50", "NIFTY BANK"]
ALL_SYMBOLS = EQUITY_SYMBOLS + INDEX_SYMBOLS

# Timeframe -> (source_priority, lookback_days)
# nseindia_api is PRIMARY since nsepython's equity_history endpoint is broken
TIMEFRAME_CONFIG = {
    "1d": {"lookback_days": 3 * 365, "sources": ["nseindia_api", "nsepython", "bhavcopy"]},
    "1h": {"lookback_days": 365, "sources": ["nseindia_api"]},
    "15m": {"lookback_days": 180, "sources": ["nseindia_api"]},
    "5m": {"lookback_days": 90, "sources": ["nseindia_api"]},
}


def get_source(name: str):
    """Factory to get a data source by name."""
    if name == "nsepython":
        from data.sources.nsepython_source import NSEPythonSource
        return NSEPythonSource()
    elif name == "nseindia_api":
        from data.sources.nseindia_api_source import NseIndiaApiSource
        return NseIndiaApiSource()
    elif name == "bhavcopy":
        from data.sources.nse_bhavcopy_source import NSEBhavcopySource
        return NSEBhavcopySource()
    else:
        raise ValueError(f"Unknown data source: {name}")


def upsert_candles(symbol: str, timeframe: str, df: pd.DataFrame) -> int:
    """Upsert candles into MongoDB. Returns count of upserted docs."""
    if df.empty:
        return 0

    from pymongo import UpdateOne

    ops = []
    for _, row in df.iterrows():
        ts = row["timestamp"]
        if pd.isna(ts):
            continue
        # Convert to python datetime
        if isinstance(ts, pd.Timestamp):
            ts = ts.to_pydatetime()

        doc = {
            "symbol": symbol,
            "timeframe": timeframe,
            "timestamp": ts,
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "volume": int(row["volume"]),
        }
        ops.append(
            UpdateOne(
                {"symbol": symbol, "timeframe": timeframe, "timestamp": ts},
                {"$set": doc},
                upsert=True,
            )
        )

    if not ops:
        return 0

    # Batch in chunks of 1000
    total = 0
    for i in range(0, len(ops), 1000):
        result = market_data.bulk_write(ops[i : i + 1000], ordered=False)
        total += result.upserted_count + result.modified_count

    return len(ops)


def ingest_symbol(symbol: str, timeframes: dict, daily_only: bool = False) -> dict:
    """Ingest all timeframes for a single symbol. Returns results dict."""
    results = {}
    now = datetime.now()

    for tf, config in timeframes.items():
        if daily_only and tf != "1d":
            results[tf] = {"status": "skipped", "candles": 0, "source": "-", "time": 0}
            continue

        start = now - timedelta(days=config["lookback_days"])
        end = now
        sources = config["sources"]

        fetched = False
        for source_name in sources:
            t0 = time.time()
            try:
                source = get_source(source_name)

                # nsepython only supports 1d
                if source_name == "nsepython" and tf != "1d":
                    continue
                # bhavcopy only supports 1d
                if source_name == "bhavcopy" and tf != "1d":
                    continue

                df = source.fetch_historical(symbol, tf, start, end)
                elapsed = time.time() - t0

                if df is not None and not df.empty:
                    count = upsert_candles(symbol, tf, df)
                    results[tf] = {
                        "status": "ok",
                        "candles": len(df),
                        "source": source_name,
                        "time": round(elapsed, 1),
                    }
                    fetched = True
                    break
                else:
                    logger.debug(f"  {symbol} {tf}: {source_name} returned empty data")
            except Exception as e:
                elapsed = time.time() - t0
                logger.debug(f"  {symbol} {tf}: {source_name} failed ({elapsed:.1f}s): {e}")
                continue

        if not fetched:
            results[tf] = {"status": "failed", "candles": 0, "source": "-", "time": 0}

    return results


def main():
    parser = argparse.ArgumentParser(description="Ingest NSE market data into MongoDB")
    parser.add_argument("--symbols", type=str, help="Comma-separated symbols (default: all 22)")
    parser.add_argument("--daily-only", action="store_true", help="Only download daily data")
    args = parser.parse_args()

    strategy = os.environ.get("DATA_STRATEGY", "full")
    daily_only = args.daily_only or strategy == "daily_only"

    symbols = ALL_SYMBOLS
    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(",")]

    print()
    print("=" * 52)
    print("  DATA INGESTION")
    print("=" * 52)
    print(f"  Strategy: {'daily_only' if daily_only else 'full'}")
    print(f"  Symbols: {len(symbols)}")
    print(f"  Timeframes: {'1d only' if daily_only else '1d, 1h, 15m, 5m'}")
    print(f"  Rate limit: 1.5s between requests")
    print()

    start_time = time.time()
    all_results = {}
    failures = []

    for idx, symbol in enumerate(symbols, 1):
        print(f"  Ingesting {symbol}...")
        try:
            results = ingest_symbol(symbol, TIMEFRAME_CONFIG, daily_only)
            all_results[symbol] = results

            for tf, r in results.items():
                status_icon = "[ok]" if r["status"] == "ok" else "[skip]" if r["status"] == "skipped" else "[FAIL]"
                print(f"    {tf}: {r['candles']:>6} candles {status_icon} ({r['source']}, {r['time']}s)")

                if r["status"] == "failed":
                    failures.append(f"{symbol}/{tf}")

        except Exception as e:
            logger.error(f"  {symbol}: ERROR - {e}")
            failures.append(f"{symbol} (all)")
            all_results[symbol] = {"error": str(e)}

        progress = f"[{idx}/{len(symbols)} symbols"
        elapsed = time.time() - start_time
        if idx > 1:
            remaining = (elapsed / idx) * (len(symbols) - idx)
            progress += f" - ~{int(remaining // 60)}m {int(remaining % 60)}s remaining"
        progress += "]"
        print(f"  {progress}")
        print()

    # Summary
    total_elapsed = time.time() - start_time
    total_candles = sum(
        r.get("candles", 0)
        for sym_results in all_results.values()
        if isinstance(sym_results, dict)
        for r in sym_results.values()
        if isinstance(r, dict)
    )

    print("=" * 52)
    print("  DATA INGESTION COMPLETE")
    print("=" * 52)
    print(f"  Total symbols: {len(symbols)}")
    print(f"  Total candles loaded: {total_candles:,}")
    print()

    # Per-symbol table
    print(f"  {'Symbol':<16} | {'1d':>6} | {'1h':>6} | {'15m':>6} | {'5m':>6}")
    print(f"  {'-'*16}-+-{'-'*6}-+-{'-'*6}-+-{'-'*6}-+-{'-'*6}")
    for sym, res in all_results.items():
        if not isinstance(res, dict) or "error" in res:
            print(f"  {sym:<16} | ERROR")
            continue
        cols = []
        for tf in ["1d", "1h", "15m", "5m"]:
            r = res.get(tf, {})
            c = r.get("candles", 0)
            cols.append(f"{c:>6}" if c > 0 else "     -")
        print(f"  {sym:<16} | {' | '.join(cols)}")

    print()
    print(f"  Failures: {len(failures)}")
    if failures:
        for f in failures:
            print(f"    - {f}")
    print(f"  Time taken: {int(total_elapsed // 60)}m {int(total_elapsed % 60)}s")
    print("=" * 52)
    print()


if __name__ == "__main__":
    main()
