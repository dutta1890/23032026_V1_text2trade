"""Backtest engine — runs a strategy against real OHLCV data with real indicator math.

Flow: fetch OHLCV -> compute indicators -> iterate candles -> evaluate entry/exit -> collect trades.
Now includes: slippage, brokerage costs, performance metrics, equity curve.
"""

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


@dataclass
class Trade:
    entry_time: str
    entry_price: float
    exit_time: str
    exit_price: float
    pnl_points: float
    pnl_percent: float
    holding_candles: int


def _ts_str(ts) -> str:
    if hasattr(ts, "strftime"):
        return ts.strftime("%Y-%m-%d")
    return str(ts)[:10]


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
    """Build equity curve from trade list.
    Returns [{timestamp, equity, drawdown_pct}].
    """
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
    """Run a real backtest on historical OHLCV data.

    Returns a dict with: trades, metrics, costs, equity_curve, warnings.
    """
    if not start_date:
        from datetime import timedelta
        end_date = end_date or datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=3 * 365)
    if not end_date:
        end_date = datetime.now(timezone.utc)

    ds_label = f"mongodb ({symbol}/{timeframe})"

    # --- Fetch data ---
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

    # --- Pre-compute indicators ---
    all_conditions = entry_conditions + exit_conditions + filters
    try:
        indicators = _precompute_indicators(df, all_conditions)
    except Exception as e:
        logger.error(f"Indicator computation failed: {e}")
        return _make_error_result("Indicator Error", str(e), ds_label, len(df))

    start_idx = _first_valid_index(indicators) + 1
    sl_pct = risk_mgmt.get("stop_loss")
    tp_pct = risk_mgmt.get("take_profit")

    # --- Cost config ---
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

    for i in range(start_idx, len(df)):
        close = df["close"].iloc[i]
        if math.isnan(close):
            continue

        if position is None:
            filters_pass = all(
                evaluate_condition(f, indicators, i, df) for f in filters
            )
            if not filters_pass:
                continue

            entry_pass = all(
                evaluate_condition(c, indicators, i, df) for c in entry_conditions
            )
            if entry_pass:
                # Apply slippage to entry (buy higher)
                slipped_entry = apply_slippage(close, slippage_pct, is_entry=True)
                position = {"entry_idx": i, "entry_price": slipped_entry, "raw_entry": close}
        else:
            # Risk management exits
            if sl_pct and close <= position["raw_entry"] * (1 - sl_pct / 100):
                slipped_exit = apply_slippage(close, slippage_pct, is_entry=False)
                _close_trade(trades, position, i, slipped_exit, df)
                position = None
                continue

            if tp_pct and close >= position["raw_entry"] * (1 + tp_pct / 100):
                slipped_exit = apply_slippage(close, slippage_pct, is_entry=False)
                _close_trade(trades, position, i, slipped_exit, df)
                position = None
                continue

            if exit_conditions:
                exit_triggered = any(
                    evaluate_condition(c, indicators, i, df) for c in exit_conditions
                )
                if exit_triggered:
                    slipped_exit = apply_slippage(close, slippage_pct, is_entry=False)
                    _close_trade(trades, position, i, slipped_exit, df)
                    position = None

    # Close open position at last candle
    if position is not None:
        last_idx = len(df) - 1
        slipped_exit = apply_slippage(df["close"].iloc[last_idx], slippage_pct, is_entry=False)
        _close_trade(trades, position, last_idx, slipped_exit, df)
        warnings.append("Open position force-closed at last candle.")

    trade_dicts = [asdict(t) for t in trades]

    # --- Metrics ---
    metrics = calculate_metrics(trade_dicts, initial_capital)

    # --- Costs ---
    costs = calculate_all_costs(trade_dicts, initial_capital, cost_cfg)

    # --- Equity curve ---
    equity_curve = _build_equity_curve(trade_dicts, initial_capital)

    # --- Warnings ---
    if not trade_dicts:
        warnings.append("No signals generated. Strategy conditions were never met in the data range.")
    if slippage_pct == 0:
        warnings.append("Slippage set to 0%. Real execution will have slippage.")

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
    }


def _close_trade(trades: list, position: dict, exit_idx: int, exit_price: float, df: pd.DataFrame):
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
    ))
