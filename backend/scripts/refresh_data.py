#!/usr/bin/env python3
"""Refresh market data — appends new candles since last ingested timestamp.

Designed to run daily after market close:
    Cron: 0 18 * * 1-5  (6 PM IST, weekdays only)

Usage:
    python scripts/refresh_data.py
    python scripts/refresh_data.py --symbols RELIANCE,TCS
"""

import os
import sys
import time
import argparse
import logging
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

import pandas as pd
from pymongo import MongoClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

mongo_client = MongoClient(os.environ.get("MONGO_URL"))
db = mongo_client[os.environ.get("DB_NAME", "text2trade")]
market_data = db["market_data"]

EQUITY_SYMBOLS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
    "HINDUNILVR", "ITC", "SBIN", "BHARTIARTL", "KOTAKBANK",
    "LT", "AXISBANK", "ASIANPAINT", "MARUTI", "BAJFINANCE",
    "TITAN", "SUNPHARMA", "HCLTECH", "WIPRO", "TATAMOTORS",
]
INDEX_SYMBOLS = ["NIFTY 50", "NIFTY BANK"]
ALL_SYMBOLS = EQUITY_SYMBOLS + INDEX_SYMBOLS

TIMEFRAME_SOURCES = {
    "1d": ["nsepython", "bhavcopy"],
    "1h": ["nseindia_api"],
    "15m": ["nseindia_api"],
    "5m": ["nseindia_api"],
}


def get_source(name: str):
    if name == "nsepython":
        from data.sources.nsepython_source import NSEPythonSource
        return NSEPythonSource()
    elif name == "nseindia_api":
        from data.sources.nseindia_api_source import NseIndiaApiSource
        return NseIndiaApiSource()
    elif name == "bhavcopy":
        from data.sources.nse_bhavcopy_source import NSEBhavcopySource
        return NSEBhavcopySource()
    raise ValueError(f"Unknown source: {name}")


def get_last_timestamp(symbol: str, timeframe: str):
    doc = market_data.find_one(
        {"symbol": symbol, "timeframe": timeframe},
        {"_id": 0, "timestamp": 1},
        sort=[("timestamp", -1)],
    )
    return doc["timestamp"] if doc else None


def upsert_candles(symbol, timeframe, df):
    if df.empty:
        return 0
    from pymongo import UpdateOne
    ops = []
    for _, row in df.iterrows():
        ts = row["timestamp"]
        if pd.isna(ts):
            continue
        if isinstance(ts, pd.Timestamp):
            ts = ts.to_pydatetime()
        doc = {
            "symbol": symbol, "timeframe": timeframe, "timestamp": ts,
            "open": float(row["open"]), "high": float(row["high"]),
            "low": float(row["low"]), "close": float(row["close"]),
            "volume": int(row["volume"]),
        }
        ops.append(UpdateOne(
            {"symbol": symbol, "timeframe": timeframe, "timestamp": ts},
            {"$set": doc}, upsert=True,
        ))
    if ops:
        market_data.bulk_write(ops, ordered=False)
    return len(ops)


def main():
    parser = argparse.ArgumentParser(description="Refresh market data (incremental)")
    parser.add_argument("--symbols", type=str, help="Comma-separated symbols")
    args = parser.parse_args()

    strategy = os.environ.get("DATA_STRATEGY", "full")
    daily_only = strategy == "daily_only"

    symbols = ALL_SYMBOLS
    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(",")]

    print()
    print("=" * 52)
    print("  DATA REFRESH (Incremental)")
    print("=" * 52)

    total_new = 0
    errors = []

    for symbol in symbols:
        timeframes = ["1d"] if daily_only else ["1d", "1h", "15m", "5m"]
        for tf in timeframes:
            last_ts = get_last_timestamp(symbol, tf)
            if last_ts is None:
                logger.info(f"  {symbol}/{tf}: No existing data, skipping (run full ingest first)")
                continue

            start = last_ts + timedelta(seconds=1)
            end = datetime.now()

            sources = TIMEFRAME_SOURCES.get(tf, [])
            for source_name in sources:
                try:
                    source = get_source(source_name)
                    if source_name == "nsepython" and tf != "1d":
                        continue
                    if source_name == "bhavcopy" and tf != "1d":
                        continue

                    df = source.fetch_historical(symbol, tf, start, end)
                    if df is not None and not df.empty:
                        count = upsert_candles(symbol, tf, df)
                        total_new += count
                        print(f"  {symbol}/{tf}: +{count} new candles ({source_name})")
                        break
                except Exception as e:
                    logger.debug(f"  {symbol}/{tf}: {source_name} failed: {e}")
                    continue
            else:
                if (end - start).days > 1:
                    errors.append(f"{symbol}/{tf}")

    print()
    print(f"  Total new candles: {total_new}")
    if errors:
        print(f"  Errors ({len(errors)}):")
        for e in errors:
            print(f"    - {e}")
    print("=" * 52)


if __name__ == "__main__":
    main()
