"""Screener engine — scans all symbols against indicator conditions on latest candles.

Pure computation on cached MongoDB data. No AI, no API credits.
"""

import math
import time
import logging
from typing import List, Optional
from datetime import datetime, timedelta, timezone

import pandas as pd

from data.service import get_available_symbols, market_data_collection
from indicators.calculator import compute_indicator, CALCULATOR_REGISTRY
from backtest.evaluator import evaluate_condition, _indicator_key, _safe_value

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# PRESETS
# ---------------------------------------------------------------------------

SCREENER_PRESETS = {
    "oversold": {
        "name": "Oversold",
        "description": "RSI below 30 — potential reversal candidates",
        "conditions": [
            {"name": "RSI", "params": {"period": 14}, "operator": "<", "value": 30}
        ],
    },
    "trending_up": {
        "name": "Trending Up",
        "description": "50-day SMA above 200-day SMA with strong trend (ADX > 20)",
        "conditions": [
            {"name": "SMA", "params": {"short": 50, "long": 200}, "operator": ">"},
            {"name": "ADX", "params": {"period": 14}, "operator": ">", "value": 20},
        ],
    },
    "vwap_breakout": {
        "name": "VWAP Breakout",
        "description": "Price trading above VWAP — bullish intraday momentum",
        "conditions": [
            {"name": "VWAP", "params": {}, "operator": ">"}
        ],
    },
    "bollinger_squeeze": {
        "name": "Bollinger Squeeze",
        "description": "Bollinger bandwidth below 10% — volatility contraction, breakout imminent",
        "conditions": [
            {"name": "Bollinger", "params": {"period": 20, "std_dev": 2}, "operator": "squeeze", "value": 0.1}
        ],
    },
    "momentum_surge": {
        "name": "Momentum Surge",
        "description": "MACD bullish crossover confirmed by strong trend (ADX > 25)",
        "conditions": [
            {"name": "MACD", "params": {"fast": 12, "slow": 26, "signal": 9}, "operator": "bullish_cross"},
            {"name": "ADX", "params": {"period": 14}, "operator": ">", "value": 25},
        ],
    },
}


def _get_latest_candles(symbol: str, timeframe: str = "1d", count: int = 250) -> pd.DataFrame:
    """Fetch the most recent `count` candles for a symbol from MongoDB."""
    cursor = market_data_collection.find(
        {"symbol": symbol, "timeframe": timeframe},
        {"_id": 0, "symbol": 0, "timeframe": 0},
    ).sort("timestamp", -1).limit(count)

    rows = list(cursor)
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


def _compute_all_needed_indicators(df: pd.DataFrame, conditions: list) -> dict:
    """Compute all indicators required by the given conditions."""
    indicators = {}
    for cond in conditions:
        name = cond["name"]
        params = cond.get("params", {})

        if name in ("SMA", "EMA"):
            for key in ("short", "long", "period"):
                if key in params:
                    period_val = params[key]
                    single_params = {"period": period_val}
                    ind_key = _indicator_key(name, single_params)
                    if ind_key not in indicators:
                        indicators[ind_key] = compute_indicator(df, name, single_params)
        else:
            ind_key = _indicator_key(name, params)
            if ind_key not in indicators:
                indicators[ind_key] = compute_indicator(df, name, params)

    return indicators


def _evaluate_screener_condition(condition: dict, indicators: dict, idx: int, df: pd.DataFrame) -> bool:
    """Extended evaluator that handles screener-specific operators like 'squeeze'."""
    name = condition["name"]
    operator = condition["operator"]
    params = condition.get("params", {})
    threshold = condition.get("value")

    # Bollinger squeeze: bandwidth < threshold
    if name == "Bollinger" and operator == "squeeze":
        ind_key = _indicator_key(name, params)
        ind_data = indicators.get(ind_key)
        if ind_data is None:
            return False
        upper = ind_data.get("upper")
        middle = ind_data.get("middle")
        lower = ind_data.get("lower")
        if upper is None or middle is None or lower is None:
            return False
        u = _safe_value(upper, idx)
        m = _safe_value(middle, idx)
        l_val = _safe_value(lower, idx)
        if math.isnan(u) or math.isnan(m) or math.isnan(l_val) or m == 0:
            return False
        bandwidth = (u - l_val) / m
        return bandwidth < (threshold or 0.1)

    # Everything else → standard evaluator
    return evaluate_condition(condition, indicators, idx, df)


def _extract_indicator_values(conditions: list, indicators: dict, idx: int, df: pd.DataFrame) -> dict:
    """Extract readable indicator values for the matched symbol."""
    values = {}
    for cond in conditions:
        name = cond["name"]
        params = cond.get("params", {})

        if name in ("SMA", "EMA"):
            for key in ("short", "long"):
                if key in params:
                    period_val = params[key]
                    ind_key = _indicator_key(name, {"period": period_val})
                    series = indicators.get(ind_key)
                    if series is not None:
                        val = _safe_value(series, idx)
                        if not math.isnan(val):
                            values[f"{name}({period_val})"] = round(val, 2)
        elif name == "MACD":
            ind_key = _indicator_key(name, params)
            ind_data = indicators.get(ind_key)
            if ind_data and isinstance(ind_data, dict):
                for k in ("macd", "signal", "histogram"):
                    s = ind_data.get(k)
                    if s is not None:
                        val = _safe_value(s, idx)
                        if not math.isnan(val):
                            values[f"MACD_{k}"] = round(val, 2)
        elif name == "Bollinger":
            ind_key = _indicator_key(name, params)
            ind_data = indicators.get(ind_key)
            if ind_data and isinstance(ind_data, dict):
                for k in ("upper", "middle", "lower"):
                    s = ind_data.get(k)
                    if s is not None:
                        val = _safe_value(s, idx)
                        if not math.isnan(val):
                            values[f"BB_{k}"] = round(val, 2)
                u = values.get("BB_upper", 0)
                m = values.get("BB_middle", 1)
                l_v = values.get("BB_lower", 0)
                if m > 0:
                    values["BB_bandwidth"] = round((u - l_v) / m, 4)
        elif name == "ADX":
            ind_key = _indicator_key(name, params)
            ind_data = indicators.get(ind_key)
            if ind_data and isinstance(ind_data, dict):
                adx_s = ind_data.get("adx")
                if adx_s is not None:
                    val = _safe_value(adx_s, idx)
                    if not math.isnan(val):
                        values["ADX"] = round(val, 2)
            elif ind_data is not None:
                val = _safe_value(ind_data, idx)
                if not math.isnan(val):
                    values["ADX"] = round(val, 2)
        elif name == "Stochastic":
            ind_key = _indicator_key(name, params)
            ind_data = indicators.get(ind_key)
            if ind_data and isinstance(ind_data, dict):
                for k in ("k", "d"):
                    s = ind_data.get(k)
                    if s is not None:
                        val = _safe_value(s, idx)
                        if not math.isnan(val):
                            values[f"Stoch_{k}"] = round(val, 2)
        else:
            ind_key = _indicator_key(name, params)
            ind_data = indicators.get(ind_key)
            if ind_data is not None:
                if isinstance(ind_data, dict):
                    for k, s in ind_data.items():
                        if isinstance(s, pd.Series):
                            val = _safe_value(s, idx)
                            if not math.isnan(val):
                                values[f"{name}_{k}"] = round(val, 2)
                elif isinstance(ind_data, pd.Series):
                    val = _safe_value(ind_data, idx)
                    if not math.isnan(val):
                        values[name] = round(val, 2)

    # Always include close price
    close_val = _safe_value(df["close"], idx)
    if not math.isnan(close_val):
        values["close"] = round(close_val, 2)

    return values


def run_screener(
    conditions: list,
    timeframe: str = "1d",
    symbols: Optional[List[str]] = None,
) -> dict:
    """Scan all (or specified) symbols against conditions on the latest candle.

    Returns dict with matches, scan metadata, and timing.
    """
    start_time = time.time()

    all_symbols = symbols or get_available_symbols()
    if not all_symbols:
        return {"matches": [], "total_scanned": 0, "scan_time_ms": 0, "error": "No symbols available"}

    matches = []
    errors = []

    for symbol in all_symbols:
        try:
            df = _get_latest_candles(symbol, timeframe, 250)
            if df.empty or len(df) < 50:
                continue

            indicators = _compute_all_needed_indicators(df, conditions)
            last_idx = len(df) - 1

            # All conditions must be true on the latest candle
            all_pass = True
            for cond in conditions:
                if not _evaluate_screener_condition(cond, indicators, last_idx, df):
                    all_pass = False
                    break

            if all_pass:
                values = _extract_indicator_values(conditions, indicators, last_idx, df)
                matches.append({
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "last_timestamp": df["timestamp"].iloc[last_idx].isoformat(),
                    "indicator_values": values,
                })

        except Exception as e:
            errors.append({"symbol": symbol, "error": str(e)})

    elapsed_ms = round((time.time() - start_time) * 1000)

    return {
        "matches": matches,
        "match_count": len(matches),
        "total_scanned": len(all_symbols),
        "scan_time_ms": elapsed_ms,
        "timeframe": timeframe,
        "conditions_count": len(conditions),
        "errors": errors if errors else None,
    }
