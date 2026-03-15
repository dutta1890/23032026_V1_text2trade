"""Data access service — the ONLY interface backtest engine uses.

Reads MongoDB ONLY. Zero external API calls at runtime.
Never imports nsepython or nse.
"""

import os
import logging
from datetime import datetime
from typing import List, Optional
import pandas as pd
from pymongo import MongoClient

logger = logging.getLogger(__name__)

# MongoDB connection
_mongo_client = MongoClient(os.environ.get("MONGO_URL"))
_db = _mongo_client[os.environ.get("DB_NAME", "text2trade")]
market_data_collection = _db["market_data"]

# Create compound unique index
try:
    market_data_collection.create_index(
        [("symbol", 1), ("timeframe", 1), ("timestamp", 1)],
        unique=True
    )
except Exception as e:
    logger.warning(f"Could not create market_data index: {e}")


def get_ohlcv(symbol: str, timeframe: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """Fetch OHLCV data from MongoDB cache.

    Returns DataFrame with columns: timestamp, open, high, low, close, volume.
    Raises clear errors when data is missing.
    """
    # Check if data source is configured
    data_strategy = os.environ.get("DATA_STRATEGY")
    if not data_strategy:
        total = market_data_collection.count_documents({})
        if total == 0:
            raise ValueError(
                "Data source not configured. Run: python scripts/setup_data_source.py"
            )

    # Check if symbol exists
    available = get_available_symbols()
    if not available:
        raise ValueError(
            "No market data found. Admin: run python scripts/setup_data_source.py && python scripts/ingest_data.py"
        )

    if symbol not in available:
        raise ValueError(
            f"No data for {symbol}. Available: {', '.join(sorted(available))}"
        )

    # Check if timeframe exists for symbol
    available_tf = market_data_collection.distinct("timeframe", {"symbol": symbol})
    if timeframe not in available_tf:
        raise ValueError(
            f"No {timeframe} data for {symbol}. Available: {', '.join(sorted(available_tf))}"
        )

    # Query MongoDB
    cursor = market_data_collection.find(
        {
            "symbol": symbol,
            "timeframe": timeframe,
            "timestamp": {"$gte": start_date, "$lte": end_date},
        },
        {"_id": 0, "symbol": 0, "timeframe": 0},
    ).sort("timestamp", 1)

    rows = list(cursor)
    if not rows:
        raise ValueError(
            f"No data for {symbol} ({timeframe}) in range "
            f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}. "
            f"Run scripts/ingest_data.py to refresh data."
        )

    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def get_available_symbols() -> List[str]:
    """Return list of symbols that have data in MongoDB."""
    return sorted(market_data_collection.distinct("symbol"))


def get_data_range(symbol: str, timeframe: str) -> dict:
    """Return date range and candle count for a symbol/timeframe pair."""
    pipeline = [
        {"$match": {"symbol": symbol, "timeframe": timeframe}},
        {
            "$group": {
                "_id": None,
                "start": {"$min": "$timestamp"},
                "end": {"$max": "$timestamp"},
                "candle_count": {"$sum": 1},
            }
        },
    ]
    results = list(market_data_collection.aggregate(pipeline))
    if not results:
        return {"start": None, "end": None, "candle_count": 0}

    r = results[0]
    return {
        "start": r["start"].isoformat() if r["start"] else None,
        "end": r["end"].isoformat() if r["end"] else None,
        "candle_count": r["candle_count"],
    }


def get_data_status() -> dict:
    """Full data health report for admin endpoint."""
    total_candles = market_data_collection.count_documents({})
    symbols = get_available_symbols()
    data_strategy = os.environ.get("DATA_STRATEGY", "not_configured")

    per_symbol = {}
    for sym in symbols:
        per_symbol[sym] = {}
        for tf in ["1d", "1h", "15m", "5m"]:
            info = get_data_range(sym, tf)
            per_symbol[sym][tf] = info

    # Find last refresh timestamp
    last_doc = market_data_collection.find_one(
        {}, {"_id": 0, "timestamp": 1}, sort=[("timestamp", -1)]
    )
    last_refresh = last_doc["timestamp"].isoformat() if last_doc else None

    # Stale symbols (>5 trading days = ~7 calendar days)
    from datetime import timedelta, timezone as tz
    cutoff = datetime.now(tz.utc) - timedelta(days=7)
    stale = []
    for sym in symbols:
        latest = market_data_collection.find_one(
            {"symbol": sym, "timeframe": "1d"},
            {"_id": 0, "timestamp": 1},
            sort=[("timestamp", -1)],
        )
        if latest and latest["timestamp"].replace(tzinfo=tz.utc) < cutoff:
            stale.append(sym)

    health = "healthy"
    if total_candles == 0:
        health = "empty"
    elif stale:
        health = "stale"

    return {
        "health": health,
        "data_strategy": data_strategy,
        "total_symbols": len(symbols),
        "total_candles": total_candles,
        "last_refresh": last_refresh,
        "stale_symbols": stale,
        "symbols": per_symbol,
    }
