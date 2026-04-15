"""Backtest engine — runs a strategy against real OHLCV data with real indicator math.

Supports: trailing SL, time-based exit, daily limits, position sizing, slippage, costs.
"""

import hashlib
import json
import logging
import math
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import List, Optional

import pandas as pd

from data.service import get_ohlcv
from indicators.calculator import compute_indicator, CALCULATOR_REGISTRY
from backtest.evaluator import evaluate_condition, _indicator_key
from backtest.metrics import calculate_metrics
from backtest.costs import CostConfig, apply_slippage, calculate_all_costs

logger = logging.getLogger(__name__)

ENGINE_VERSION = "0.2.0"


def compute_data_hash(df: pd.DataFrame) -> str:
    """SHA-256 hash of OHLCV data for reproducibility verification."""
    cols = ["timestamp", "open", "high", "low", "close", "volume"]
    present = [c for c in cols if c in df.columns]
    subset = df[present].copy()
    if "timestamp" in subset.columns:
        subset["timestamp"] = subset["timestamp"].astype(str)
    raw = subset.to_csv(index=False)
    return hashlib.sha256(raw.encode()).hexdigest()


@dataclass
class Trade:
    entry_time: str
    entry_price: float
    exit_time: str
    exit_price: float
    pnl_points: float
    pnl_percent: float
    holding_candles: int
    exit_reason: str = ""


def _ts_str(ts) -> str:
    if hasattr(ts, "strftime"):
        return ts.strftime("%Y-%m-%d")
    return str(ts)[:10]


def _ts_time_str(ts) -> str:
    """Get HH:MM from timestamp."""
    if hasattr(ts, "strftime"):
        return ts.strftime("%H:%M")
    return ""


def _precompute_indicators(df: pd.DataFrame, conditions: list) -> dict:
    cache = {}
    for cond in conditions:
        name = cond.get("name", "")
        params = cond.get("params", {})
        if name in ("SMA", "EMA"):
            short_p = params.get("short", params.get("period", 9))
            long_p = params.get("long", 21)
            for p in [short_p, long_p]:
                key = _indicator_key(name, {"period": p})
                if key not in cache:
                    cache[key] = compute_indicator(df, name, {"period": p})
        elif name in CALCULATOR_REGISTRY:
            key = _indicator_key(name, params)
            if key not in cache:
                cache[key] = compute_indicator(df, name, params)
    return cache


def _first_valid_index(indicators: dict) -> int:
    max_nan = 0
    for data in indicators.values():
        if isinstance(data, dict):
            for series in data.values():
                if isinstance(series, pd.Series):
                    first = series.first_valid_index()
                    if first is not None:
                        max_nan = max(max_nan, series.index.get_loc(first))
        elif isinstance(data, pd.Series):
            first = data.first_valid_index()
            if first is not None:
                max_nan = max(max_nan, data.index.get_loc(first))
    return max_nan


def _build_equity_curve(trades: list, initial_capital: float) -> list:
    if not trades:
        return []
    equity = initial_capital
    peak = equity
    curve = [{"timestamp": "start", "equity": round(equity, 2), "drawdown_pct": 0}]
    for t in trades:
        pnl_abs = equity * (t["pnl_percent"] / 100)
        equity += pnl_abs
        peak = max(peak, equity)
        dd = round((peak - equity) / peak * 100, 2) if peak > 0 else 0
        curve.append({
            "timestamp": t["exit_time"],
            "equity": round(equity, 2),
            "drawdown_pct": dd,
        })
    return curve


def _make_error_result(label, message, data_source="none", candles=0):
    return {
        "success": False, "label": label, "disclaimer": message,
        "trades": [], "metrics": calculate_metrics([]),
        "costs": {}, "equity_curve": [], "warnings": [message],
        "data_source": data_source, "candles_processed": candles,
    }


def _parse_risk_management(risk_mgmt: dict) -> dict:
    """Parse the new risk management schema into flat engine params."""
    sl_cfg = risk_mgmt.get("stop_loss")
    tp_cfg = risk_mgmt.get("target_profit")
    tsl_cfg = risk_mgmt.get("trailing_stop_loss", {})
    time_exit = risk_mgmt.get("time_based_exit", {})
    daily_lim = risk_mgmt.get("daily_limits", {})
    # pos_size reserved for future position sizing feature

    # --- Stop loss ---
    sl_pct = None
    sl_points = None
    sl_type = "percentage"
    if sl_cfg:
        sl_type = sl_cfg.get("type", "percentage") if isinstance(sl_cfg, dict) else "percentage"
        sl_val = sl_cfg.get("value") if isinstance(sl_cfg, dict) else sl_cfg
        if sl_type == "percentage":
            sl_pct = float(sl_val) if sl_val else None
        elif sl_type == "points":
            sl_points = float(sl_val) if sl_val else None
        elif sl_type == "atr_multiple":
            sl_pct = None  # handled separately via ATR indicator
            sl_points = None

    # --- Target profit ---
    tp_pct = None
    tp_points = None
    if tp_cfg:
        tp_type = tp_cfg.get("type", "percentage") if isinstance(tp_cfg, dict) else "percentage"
        tp_val = tp_cfg.get("value") if isinstance(tp_cfg, dict) else tp_cfg
        if tp_type == "percentage":
            tp_pct = float(tp_val) if tp_val else None
        elif tp_type == "points":
            tp_points = float(tp_val) if tp_val else None

    # --- Trailing SL ---
    trailing_enabled = tsl_cfg.get("enabled", False) if isinstance(tsl_cfg, dict) else False
    trailing_pct = None
    trailing_points = None
    trailing_activation = 0
    if trailing_enabled:
        tsl_type = tsl_cfg.get("type", "percentage")
        tsl_val = tsl_cfg.get("value", 1.0)
        trailing_activation = tsl_cfg.get("activation_profit", 0)
        if tsl_type == "percentage":
            trailing_pct = float(tsl_val)
        else:
            trailing_points = float(tsl_val)

    # --- Time exit ---
    time_exit_enabled = time_exit.get("enabled", False) if isinstance(time_exit, dict) else False
    time_exit_str = time_exit.get("exit_time", "15:10") if isinstance(time_exit, dict) else "15:10"

    # --- Daily limits ---
    max_loss_day = daily_lim.get("max_loss_per_day", 5.0) if isinstance(daily_lim, dict) else 5.0
    max_trades_day = daily_lim.get("max_trades_per_day", 10) if isinstance(daily_lim, dict) else 10

    return {
        "sl_pct": sl_pct, "sl_points": sl_points, "sl_type": sl_type,
        "tp_pct": tp_pct, "tp_points": tp_points,
        "trailing_enabled": trailing_enabled,
        "trailing_pct": trailing_pct, "trailing_points": trailing_points,
        "trailing_activation": trailing_activation,
        "time_exit_enabled": time_exit_enabled, "time_exit_str": time_exit_str,
        "max_loss_day": max_loss_day, "max_trades_day": max_trades_day,
    }


def _open_position(close: float, idx: int, slippage_pct: float, rp: dict) -> dict:
    """Create a new position dict with optional trailing SL initialization."""
    slipped_entry = apply_slippage(close, slippage_pct, is_entry=True)
    position = {
        "entry_idx": idx,
        "entry_price": slipped_entry,
        "raw_entry": close,
        "trailing_sl": None,
        "highest_since_entry": close,
    }
    if rp["trailing_enabled"]:
        if rp["trailing_pct"]:
            position["trailing_sl"] = slipped_entry * (1 - rp["trailing_pct"] / 100)
        elif rp["trailing_points"]:
            position["trailing_sl"] = slipped_entry - rp["trailing_points"]
    return position


def _check_exit(
    position: dict, close: float, idx: int, rp: dict,
    is_intraday: bool, df: pd.DataFrame,
    exit_conditions: list, indicators: dict,
) -> str:
    """Check all exit conditions, returning the exit reason or empty string."""
    raw_entry = position["raw_entry"]

    # Update highest price for trailing SL
    if close > position["highest_since_entry"]:
        position["highest_since_entry"] = close

    # Time-based exit
    if rp["time_exit_enabled"] and is_intraday:
        candle_time = _ts_time_str(df["timestamp"].iloc[idx])
        if candle_time >= rp["time_exit_str"]:
            return "time_exit"

    # Trailing SL update and check
    if rp["trailing_enabled"] and position["trailing_sl"] is not None:
        high = position["highest_since_entry"]
        profit_pct = ((high - raw_entry) / raw_entry) * 100
        if profit_pct >= rp["trailing_activation"]:
            if rp["trailing_pct"]:
                new_tsl = high * (1 - rp["trailing_pct"] / 100)
            else:
                new_tsl = high - (rp["trailing_points"] or 0)
            position["trailing_sl"] = max(position["trailing_sl"], new_tsl)
        if close <= position["trailing_sl"]:
            return "trailing_sl"

    # Fixed stop loss
    if rp["sl_pct"] and close <= raw_entry * (1 - rp["sl_pct"] / 100):
        return "stop_loss"
    if rp["sl_points"] and close <= raw_entry - rp["sl_points"]:
        return "stop_loss"

    # Target profit
    if rp["tp_pct"] and close >= raw_entry * (1 + rp["tp_pct"] / 100):
        return "target_profit"
    if rp["tp_points"] and close >= raw_entry + rp["tp_points"]:
        return "target_profit"

    # Indicator-based exit
    if exit_conditions:
        if any(evaluate_condition(c, indicators, idx, df) for c in exit_conditions):
            return "indicator_exit"

    return ""


def run_backtest(
    strategy_json: dict,
    symbol: str,
    timeframe: str = "1d",
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    slippage_pct: float = 0.05,
    initial_capital: float = 100000,
    brokerage_per_order: float = 20,
) -> dict:
    if not start_date:
        from datetime import timedelta
        end_date = end_date or datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=3 * 365)
    if not end_date:
        end_date = datetime.now(timezone.utc)

    ds_label = f"mongodb ({symbol}/{timeframe})"

    try:
        df = get_ohlcv(symbol, timeframe, start_date, end_date)
    except ValueError as e:
        return _make_error_result("No Data", str(e))

    if df.empty or len(df) < 30:
        msg = f"Only {len(df)} candles available for {symbol}/{timeframe}. Need at least 30."
        return _make_error_result("Insufficient Data", msg, ds_label, len(df))

    df = df.reset_index(drop=True)

    entry_conditions = strategy_json.get("entry_conditions", [])
    exit_conditions = strategy_json.get("exit_conditions", [])
    filters = strategy_json.get("filters", [])
    risk_mgmt = strategy_json.get("risk_management", {})

    if not entry_conditions:
        return _make_error_result("No Entry Conditions",
                                  "Strategy must have at least one entry condition.",
                                  ds_label, len(df))

    # --- Parse risk management ---
    rp = _parse_risk_management(risk_mgmt)

    # --- Pre-compute indicators ---
    all_conditions = entry_conditions + exit_conditions + filters
    try:
        indicators = _precompute_indicators(df, all_conditions)
    except Exception as e:
        logger.error(f"Indicator computation failed: {e}")
        return _make_error_result("Indicator Error", str(e), ds_label, len(df))

    start_idx = _first_valid_index(indicators) + 1

    is_intraday = timeframe not in ("1d", "1wk", "1mo")
    cost_cfg = CostConfig(
        slippage_pct=slippage_pct,
        brokerage_per_order=brokerage_per_order,
        is_intraday=is_intraday,
    )

    # --- Iterate candles ---
    trades: List[Trade] = []
    position = None
    warnings = []

    # Daily tracking
    daily_loss = 0.0
    daily_trades = 0
    current_date = None

    for i in range(start_idx, len(df)):
        close = df["close"].iloc[i]
        if math.isnan(close):
            continue

        # Reset daily counters
        candle_date = df["timestamp"].iloc[i]
        cd = candle_date.date() if hasattr(candle_date, "date") else str(candle_date)[:10]
        if cd != current_date:
            current_date = cd
            daily_loss = 0.0
            daily_trades = 0

        if position is None:
            # Check daily limits
            if daily_loss >= rp["max_loss_day"] or daily_trades >= rp["max_trades_day"]:
                continue
            # Check filters
            if not all(evaluate_condition(f, indicators, i, df) for f in filters):
                continue
            # Check entry conditions
            if all(evaluate_condition(c, indicators, i, df) for c in entry_conditions):
                position = _open_position(close, i, slippage_pct, rp)
        else:
            exit_reason = _check_exit(
                position, close, i, rp, is_intraday, df, exit_conditions, indicators,
            )
            if exit_reason:
                slipped_exit = apply_slippage(close, slippage_pct, is_entry=False)
                _close_trade(trades, position, i, slipped_exit, df, exit_reason)
                pnl = ((slipped_exit - position["entry_price"]) / position["entry_price"]) * 100
                if pnl < 0:
                    daily_loss += abs(pnl)
                daily_trades += 1
                position = None

    # Close open position at last candle
    if position is not None:
        last_idx = len(df) - 1
        slipped_exit = apply_slippage(df["close"].iloc[last_idx], slippage_pct, is_entry=False)
        _close_trade(trades, position, last_idx, slipped_exit, df, "end_of_data")
        warnings.append("Open position force-closed at last candle.")

    trade_dicts = [asdict(t) for t in trades]
    metrics = calculate_metrics(trade_dicts, initial_capital)
    costs = calculate_all_costs(trade_dicts, initial_capital, cost_cfg)
    equity_curve = _build_equity_curve(trade_dicts, initial_capital)

    # Compute data hash for reproducibility
    data_hash = compute_data_hash(df)

    if not trade_dicts:
        warnings.append("No signals generated. Strategy conditions were never met in the data range.")
    if slippage_pct == 0:
        warnings.append("Slippage set to 0%. Real execution will have slippage.")

    # Determine actual date range from data
    data_start = str(df["timestamp"].iloc[0])[:10] if len(df) > 0 else None
    data_end = str(df["timestamp"].iloc[-1])[:10] if len(df) > 0 else None

    return {
        "success": True,
        "label": "Historical Backtest (Real Indicators)",
        "disclaimer": (
            f"Backtest on {symbol} {timeframe} data from MongoDB. "
            f"Slippage: {slippage_pct}%. Brokerage: Rs {brokerage_per_order}/order."
        ),
        "trades": trade_dicts,
        "metrics": metrics,
        "costs": costs,
        "equity_curve": equity_curve,
        "warnings": warnings,
        "data_source": ds_label,
        "candles_processed": len(df),
        "engine_version": ENGINE_VERSION,
        "data_snapshot_hash": data_hash,
        "data_start": data_start,
        "data_end": data_end,
    }


def _close_trade(trades: list, position: dict, exit_idx: int, exit_price: float, df: pd.DataFrame, exit_reason: str = ""):
    entry_price = position["entry_price"]
    entry_idx = position["entry_idx"]
    pnl_points = round(exit_price - entry_price, 2)
    pnl_percent = round(((exit_price - entry_price) / entry_price) * 100, 2)
    trades.append(Trade(
        entry_time=_ts_str(df["timestamp"].iloc[entry_idx]),
        entry_price=round(entry_price, 2),
        exit_time=_ts_str(df["timestamp"].iloc[exit_idx]),
        exit_price=round(exit_price, 2),
        pnl_points=pnl_points,
        pnl_percent=pnl_percent,
        holding_candles=exit_idx - entry_idx,
        exit_reason=exit_reason,
    ))
