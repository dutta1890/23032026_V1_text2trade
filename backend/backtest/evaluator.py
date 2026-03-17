"""Condition evaluator — decides if a single condition is True at a given candle index.

Supports operators: >, <, >=, <=, cross_above, cross_below,
bullish_cross, bearish_cross, upper_touch, lower_touch.
"""

import math
from typing import Any

import pandas as pd


def _safe_value(series: pd.Series, idx: int) -> float:
    """Get value from series at index, returning NaN if out of bounds."""
    if idx < 0 or idx >= len(series):
        return float("nan")
    v = series.iloc[idx]
    if isinstance(v, float) and math.isnan(v):
        return float("nan")
    return float(v)


def _crosses(series_a: pd.Series, series_b_or_val, idx: int, direction: str) -> bool:
    """Check if series_a crosses above/below series_b_or_val at index idx.
    direction: 'above' or 'below'.
    """
    if idx < 1:
        return False

    if isinstance(series_b_or_val, pd.Series):
        curr_b = _safe_value(series_b_or_val, idx)
        prev_b = _safe_value(series_b_or_val, idx - 1)
    else:
        curr_b = float(series_b_or_val)
        prev_b = curr_b

    curr_a = _safe_value(series_a, idx)
    prev_a = _safe_value(series_a, idx - 1)

    if any(math.isnan(v) for v in [curr_a, prev_a, curr_b, prev_b]):
        return False

    if direction == "above":
        return prev_a <= prev_b and curr_a > curr_b
    else:  # below
        return prev_a >= prev_b and curr_a < curr_b


def evaluate_condition(condition: dict, indicators: dict, candle_index: int, df: pd.DataFrame) -> bool:
    """Evaluate a single condition at a candle index.

    Args:
        condition: {"name": str, "params": dict, "operator": str, "value": float|None}
        indicators: pre-computed indicators keyed by (name, param_key) -> Series or dict
        candle_index: current bar index in the DataFrame
        df: the OHLCV DataFrame (for price references)

    Returns True if condition is met.
    """
    name = condition["name"]
    operator = condition["operator"]
    threshold = condition.get("value")
    params = condition.get("params", {})

    # Build a hashable key for the indicator cache
    ind_key = _indicator_key(name, params)
    ind_data = indicators.get(ind_key)

    # --- SMA / EMA (crossover between short and long) ---
    # These use two separate series keyed by period, not the composite key
    if name in ("SMA", "EMA"):
        short_key = _indicator_key(name, {"period": params.get("short", params.get("period", 9))})
        long_key = _indicator_key(name, {"period": params.get("long", 21)})
        short_s = indicators.get(short_key)
        long_s = indicators.get(long_key)
        if short_s is None or long_s is None:
            return False
        if operator in ("cross_above", "crosses_above"):
            return _crosses(short_s, long_s, candle_index, "above")
        if operator in ("cross_below", "crosses_below"):
            return _crosses(short_s, long_s, candle_index, "below")
        # Fallback: compare short MA to threshold
        val = _safe_value(short_s, candle_index)
        if math.isnan(val) or threshold is None:
            return False
        return _compare(val, operator, float(threshold), short_s, candle_index)

    # For other indicators, ind_data must exist
    if ind_data is None:
        return False

    # --- RSI ---
    if name == "RSI":
        val = _safe_value(ind_data, candle_index)
        if math.isnan(val) or threshold is None:
            return False
        return _compare(val, operator, float(threshold), ind_data, candle_index)

    # --- MACD ---
    if name == "MACD":
        macd_line = ind_data.get("macd")
        signal_line = ind_data.get("signal")
        if macd_line is None or signal_line is None:
            return False
        if operator == "bullish_cross":
            return _crosses(macd_line, signal_line, candle_index, "above")
        if operator == "bearish_cross":
            return _crosses(macd_line, signal_line, candle_index, "below")
        return False

    # --- Bollinger Bands ---
    if name == "Bollinger":
        upper = ind_data.get("upper")
        lower = ind_data.get("lower")
        close_val = _safe_value(df["close"], candle_index)
        if math.isnan(close_val):
            return False
        if operator == "upper_touch":
            return upper is not None and close_val >= _safe_value(upper, candle_index)
        if operator == "lower_touch":
            return lower is not None and close_val <= _safe_value(lower, candle_index)
        # Generic comparison against middle band
        middle = ind_data.get("middle")
        if middle is not None and threshold is None:
            val = _safe_value(middle, candle_index)
            return _compare(close_val, operator, val, df["close"], candle_index)
        return False

    # --- ADX (filter) ---
    if name == "ADX":
        val = _safe_value(ind_data, candle_index)
        if math.isnan(val) or threshold is None:
            return False
        return _compare(val, operator, float(threshold), ind_data, candle_index)

    # --- Stochastic ---
    if name == "Stochastic":
        k_line = ind_data.get("k") if isinstance(ind_data, dict) else ind_data
        if k_line is None:
            return False
        if operator in ("cross_above", "crosses_above") and threshold is not None:
            return _crosses(k_line, float(threshold), candle_index, "above")
        if operator in ("cross_below", "crosses_below") and threshold is not None:
            return _crosses(k_line, float(threshold), candle_index, "below")
        val = _safe_value(k_line, candle_index)
        if math.isnan(val) or threshold is None:
            return False
        return _compare(val, operator, float(threshold), k_line, candle_index)

    return False


def _compare(val: float, operator: str, threshold: float, series: pd.Series, idx: int) -> bool:
    """Simple numeric comparison, with cross support."""
    if operator == ">":
        return val > threshold
    if operator == "<":
        return val < threshold
    if operator == ">=":
        return val >= threshold
    if operator == "<=":
        return val <= threshold
    if operator == "==":
        return abs(val - threshold) < 1e-9
    if operator in ("cross_above", "crosses_above"):
        return _crosses(series, threshold, idx, "above")
    if operator in ("cross_below", "crosses_below"):
        return _crosses(series, threshold, idx, "below")
    return False


def _indicator_key(name: str, params: dict) -> str:
    """Create a hashable key for indicator cache lookup."""
    sorted_params = sorted(params.items())
    return f"{name}|{'|'.join(f'{k}={v}' for k, v in sorted_params)}"
