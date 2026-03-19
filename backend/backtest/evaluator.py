"""Condition evaluator — decides if a single condition is True at a given candle index.

Supports operators: >, <, >=, <=, cross_above, cross_below,
bullish_cross, bearish_cross, upper_touch, lower_touch,
buy_signal, sell_signal (Supertrend),
above_r1, below_s1, above_r2, below_s2 (Pivot Points).
"""

import math

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
    """Check if series_a crosses above/below series_b_or_val at index idx."""
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
    else:
        return prev_a >= prev_b and curr_a < curr_b


def evaluate_condition(condition: dict, indicators: dict, candle_index: int, df: pd.DataFrame) -> bool:
    """Evaluate a single condition at a candle index."""
    name = condition["name"]
    operator = condition["operator"]
    threshold = condition.get("value")
    params = condition.get("params", {})

    ind_key = _indicator_key(name, params)
    ind_data = indicators.get(ind_key)

    # --- SMA / EMA (crossover between short and long) ---
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
        short_val = _safe_value(short_s, candle_index)
        if threshold is not None:
            if math.isnan(short_val):
                return False
            return _compare(short_val, operator, float(threshold), short_s, candle_index)
        # No threshold → compare short vs long directly
        long_val = _safe_value(long_s, candle_index)
        if math.isnan(short_val) or math.isnan(long_val):
            return False
        return _compare(short_val, operator, long_val, short_s, candle_index)

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
        middle = ind_data.get("middle")
        if middle is not None and threshold is None:
            val = _safe_value(middle, candle_index)
            return _compare(close_val, operator, val, df["close"], candle_index)
        return False

    # --- ADX ---
    if name == "ADX":
        adx_series = ind_data.get("adx") if isinstance(ind_data, dict) else ind_data
        if adx_series is None:
            return False
        val = _safe_value(adx_series, candle_index)
        if math.isnan(val) or threshold is None:
            return False
        return _compare(val, operator, float(threshold), adx_series, candle_index)

    # --- ATR ---
    if name == "ATR":
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

    # --- Supertrend ---
    if name == "Supertrend":
        direction = ind_data.get("direction")
        supertrend_line = ind_data.get("supertrend")
        if direction is None:
            return False
        curr_dir = _safe_value(direction, candle_index)
        if operator == "buy_signal":
            # Direction flips from -1 to 1
            if candle_index < 1:
                return False
            prev_dir = _safe_value(direction, candle_index - 1)
            return prev_dir == -1 and curr_dir == 1
        if operator == "sell_signal":
            if candle_index < 1:
                return False
            prev_dir = _safe_value(direction, candle_index - 1)
            return prev_dir == 1 and curr_dir == -1
        # Generic: compare close vs supertrend line
        if supertrend_line is not None:
            close_val = _safe_value(df["close"], candle_index)
            st_val = _safe_value(supertrend_line, candle_index)
            if math.isnan(close_val) or math.isnan(st_val):
                return False
            if operator == ">":
                return close_val > st_val
            if operator == "<":
                return close_val < st_val
        return False

    # --- VWAP ---
    if name == "VWAP":
        val = _safe_value(ind_data, candle_index)
        close_val = _safe_value(df["close"], candle_index)
        if math.isnan(val) or math.isnan(close_val):
            return False
        if operator == ">":
            return close_val > val
        if operator == "<":
            return close_val < val
        if operator in ("cross_above", "crosses_above"):
            return _crosses(df["close"], ind_data, candle_index, "above")
        if operator in ("cross_below", "crosses_below"):
            return _crosses(df["close"], ind_data, candle_index, "below")
        return False

    # --- Pivot Points ---
    if name == "PivotPoints":
        close_val = _safe_value(df["close"], candle_index)
        if math.isnan(close_val):
            return False
        if operator == "above_r1":
            r1 = ind_data.get("r1")
            return r1 is not None and close_val > _safe_value(r1, candle_index)
        if operator == "below_s1":
            s1 = ind_data.get("s1")
            return s1 is not None and close_val < _safe_value(s1, candle_index)
        if operator == "above_r2":
            r2 = ind_data.get("r2")
            return r2 is not None and close_val > _safe_value(r2, candle_index)
        if operator == "below_s2":
            s2 = ind_data.get("s2")
            return s2 is not None and close_val < _safe_value(s2, candle_index)
        # Generic comparison against pivot
        pivot = ind_data.get("pivot")
        if pivot is not None:
            pv = _safe_value(pivot, candle_index)
            if not math.isnan(pv):
                return _compare(close_val, operator, pv, df["close"], candle_index)
        return False

    # --- PSAR ---
    if name == "PSAR":
        val = _safe_value(ind_data, candle_index)
        close_val = _safe_value(df["close"], candle_index)
        if math.isnan(val) or math.isnan(close_val):
            return False
        if operator == ">":
            return close_val > val
        if operator == "<":
            return close_val < val
        if operator in ("cross_above", "crosses_above"):
            return _crosses(df["close"], ind_data, candle_index, "above")
        if operator in ("cross_below", "crosses_below"):
            return _crosses(df["close"], ind_data, candle_index, "below")
        return False

    # --- CCI ---
    if name == "CCI":
        val = _safe_value(ind_data, candle_index)
        if math.isnan(val) or threshold is None:
            return False
        return _compare(val, operator, float(threshold), ind_data, candle_index)

    # --- Williams %R ---
    if name == "WilliamsR":
        val = _safe_value(ind_data, candle_index)
        if math.isnan(val) or threshold is None:
            return False
        return _compare(val, operator, float(threshold), ind_data, candle_index)

    # --- OBV ---
    if name == "OBV":
        val = _safe_value(ind_data, candle_index)
        if math.isnan(val):
            return False
        if threshold is not None:
            return _compare(val, operator, float(threshold), ind_data, candle_index)
        # Cross-based: compare OBV to its own SMA (not implemented without extra params)
        return False

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
