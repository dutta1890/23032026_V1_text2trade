"""Condition evaluator — decides if a single condition is True at a given candle index.

Supports operators: >, <, >=, <=, cross_above, cross_below,
bullish_cross, bearish_cross, upper_touch, lower_touch,
buy_signal, sell_signal (Supertrend),
above_r1, below_s1, above_r2, below_s2 (Pivot Points).
"""

import math
from typing import Optional

import pandas as pd


# =============================================================================
# Core helpers
# =============================================================================

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
    return prev_a >= prev_b and curr_a < curr_b


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


def _is_cross_op(operator: str, direction: str) -> bool:
    """Check if operator is a cross type in a given direction."""
    if direction == "above":
        return operator in ("cross_above", "crosses_above")
    return operator in ("cross_below", "crosses_below")


# =============================================================================
# Per-indicator evaluators
# =============================================================================

def _eval_moving_average(
    name: str, operator: str, threshold: Optional[float],
    params: dict, indicators: dict, idx: int, df: pd.DataFrame,
) -> bool:
    """Evaluate SMA / EMA crossover or comparison."""
    short_key = _indicator_key(name, {"period": params.get("short", params.get("period", 9))})
    long_key = _indicator_key(name, {"period": params.get("long", 21)})
    short_s = indicators.get(short_key)
    long_s = indicators.get(long_key)
    if short_s is None or long_s is None:
        return False
    if _is_cross_op(operator, "above"):
        return _crosses(short_s, long_s, idx, "above")
    if _is_cross_op(operator, "below"):
        return _crosses(short_s, long_s, idx, "below")
    short_val = _safe_value(short_s, idx)
    if threshold is not None:
        return not math.isnan(short_val) and _compare(short_val, operator, float(threshold), short_s, idx)
    long_val = _safe_value(long_s, idx)
    if math.isnan(short_val) or math.isnan(long_val):
        return False
    return _compare(short_val, operator, long_val, short_s, idx)


def _eval_single_series(
    ind_data, operator: str, threshold: Optional[float], idx: int,
) -> bool:
    """Evaluate a simple single-series indicator (RSI, ATR, CCI, WilliamsR)."""
    val = _safe_value(ind_data, idx)
    if math.isnan(val) or threshold is None:
        return False
    return _compare(val, operator, float(threshold), ind_data, idx)


def _eval_macd(
    ind_data: dict, operator: str, idx: int,
) -> bool:
    """Evaluate MACD crossovers."""
    macd_line = ind_data.get("macd")
    signal_line = ind_data.get("signal")
    if macd_line is None or signal_line is None:
        return False
    if operator == "bullish_cross":
        return _crosses(macd_line, signal_line, idx, "above")
    if operator == "bearish_cross":
        return _crosses(macd_line, signal_line, idx, "below")
    return False


def _eval_bollinger(
    ind_data: dict, operator: str, threshold: Optional[float],
    idx: int, df: pd.DataFrame,
) -> bool:
    """Evaluate Bollinger Bands touch/comparison."""
    close_val = _safe_value(df["close"], idx)
    if math.isnan(close_val):
        return False
    if operator == "upper_touch":
        upper = ind_data.get("upper")
        return upper is not None and close_val >= _safe_value(upper, idx)
    if operator == "lower_touch":
        lower = ind_data.get("lower")
        return lower is not None and close_val <= _safe_value(lower, idx)
    middle = ind_data.get("middle")
    if middle is not None and threshold is None:
        val = _safe_value(middle, idx)
        return _compare(close_val, operator, val, df["close"], idx)
    return False


def _eval_adx(ind_data, operator: str, threshold: Optional[float], idx: int) -> bool:
    """Evaluate ADX trend strength."""
    adx_series = ind_data.get("adx") if isinstance(ind_data, dict) else ind_data
    if adx_series is None:
        return False
    val = _safe_value(adx_series, idx)
    if math.isnan(val) or threshold is None:
        return False
    return _compare(val, operator, float(threshold), adx_series, idx)


def _eval_stochastic(ind_data, operator: str, threshold: Optional[float], idx: int) -> bool:
    """Evaluate Stochastic oscillator."""
    k_line = ind_data.get("k") if isinstance(ind_data, dict) else ind_data
    if k_line is None:
        return False
    if _is_cross_op(operator, "above") and threshold is not None:
        return _crosses(k_line, float(threshold), idx, "above")
    if _is_cross_op(operator, "below") and threshold is not None:
        return _crosses(k_line, float(threshold), idx, "below")
    val = _safe_value(k_line, idx)
    if math.isnan(val) or threshold is None:
        return False
    return _compare(val, operator, float(threshold), k_line, idx)


def _eval_supertrend(ind_data: dict, operator: str, idx: int, df: pd.DataFrame) -> bool:
    """Evaluate Supertrend buy/sell signals or generic comparison."""
    direction = ind_data.get("direction")
    if direction is None:
        return False
    curr_dir = _safe_value(direction, idx)
    if operator == "buy_signal":
        if idx < 1:
            return False
        return _safe_value(direction, idx - 1) == -1 and curr_dir == 1
    if operator == "sell_signal":
        if idx < 1:
            return False
        return _safe_value(direction, idx - 1) == 1 and curr_dir == -1
    supertrend_line = ind_data.get("supertrend")
    if supertrend_line is not None:
        close_val = _safe_value(df["close"], idx)
        st_val = _safe_value(supertrend_line, idx)
        if not math.isnan(close_val) and not math.isnan(st_val):
            if operator == ">":
                return close_val > st_val
            if operator == "<":
                return close_val < st_val
    return False


def _eval_close_vs_series(ind_data, operator: str, idx: int, df: pd.DataFrame) -> bool:
    """Evaluate close price vs a single indicator series (VWAP, PSAR)."""
    val = _safe_value(ind_data, idx)
    close_val = _safe_value(df["close"], idx)
    if math.isnan(val) or math.isnan(close_val):
        return False
    if operator == ">":
        return close_val > val
    if operator == "<":
        return close_val < val
    if _is_cross_op(operator, "above"):
        return _crosses(df["close"], ind_data, idx, "above")
    if _is_cross_op(operator, "below"):
        return _crosses(df["close"], ind_data, idx, "below")
    return False


def _eval_pivot_points(ind_data: dict, operator: str, idx: int, df: pd.DataFrame) -> bool:
    """Evaluate Pivot Points levels."""
    close_val = _safe_value(df["close"], idx)
    if math.isnan(close_val):
        return False
    level_map = {"above_r1": "r1", "below_s1": "s1", "above_r2": "r2", "below_s2": "s2"}
    if operator in level_map:
        series = ind_data.get(level_map[operator])
        if series is None:
            return False
        lv = _safe_value(series, idx)
        return close_val > lv if "above" in operator else close_val < lv
    pivot = ind_data.get("pivot")
    if pivot is not None:
        pv = _safe_value(pivot, idx)
        if not math.isnan(pv):
            return _compare(close_val, operator, pv, df["close"], idx)
    return False


def _eval_obv(ind_data, operator: str, threshold: Optional[float], idx: int) -> bool:
    """Evaluate On-Balance Volume."""
    val = _safe_value(ind_data, idx)
    if math.isnan(val):
        return False
    if threshold is not None:
        return _compare(val, operator, float(threshold), ind_data, idx)
    return False


# =============================================================================
# Main dispatcher
# =============================================================================

def evaluate_condition(condition: dict, indicators: dict, candle_index: int, df: pd.DataFrame) -> bool:
    """Evaluate a single condition at a candle index."""
    name = condition["name"]
    operator = condition["operator"]
    threshold = condition.get("value")
    params = condition.get("params", {})

    # Moving averages use a different lookup pattern
    if name in ("SMA", "EMA"):
        return _eval_moving_average(name, operator, threshold, params, indicators, candle_index, df)

    ind_key = _indicator_key(name, params)
    ind_data = indicators.get(ind_key)
    if ind_data is None:
        return False

    # Dispatch by indicator name
    if name == "RSI":
        return _eval_single_series(ind_data, operator, threshold, candle_index)
    if name == "MACD":
        return _eval_macd(ind_data, operator, candle_index)
    if name == "Bollinger":
        return _eval_bollinger(ind_data, operator, threshold, candle_index, df)
    if name == "ADX":
        return _eval_adx(ind_data, operator, threshold, candle_index)
    if name == "ATR":
        return _eval_single_series(ind_data, operator, threshold, candle_index)
    if name == "Stochastic":
        return _eval_stochastic(ind_data, operator, threshold, candle_index)
    if name == "Supertrend":
        return _eval_supertrend(ind_data, operator, candle_index, df)
    if name in ("VWAP", "PSAR"):
        return _eval_close_vs_series(ind_data, operator, candle_index, df)
    if name == "PivotPoints":
        return _eval_pivot_points(ind_data, operator, candle_index, df)
    if name == "CCI":
        return _eval_single_series(ind_data, operator, threshold, candle_index)
    if name == "WilliamsR":
        return _eval_single_series(ind_data, operator, threshold, candle_index)
    if name == "OBV":
        return _eval_obv(ind_data, operator, threshold, candle_index)

    return False
