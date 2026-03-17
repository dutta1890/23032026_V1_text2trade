"""Backtest engine — runs a strategy against real OHLCV data with real indicator math.

Flow: fetch OHLCV -> compute indicators -> iterate candles -> evaluate entry/exit -> collect trades.
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


@dataclass
class BacktestResult:
    success: bool
    label: str
    disclaimer: str
    trades: list
    win_rate: float
    pnl: float
    total_trades: int
    wins: int
    losses: int
    data_source: str
    candles_processed: int = 0
    message: str = ""


def _ts_str(ts) -> str:
    """Convert timestamp to string."""
    if hasattr(ts, "strftime"):
        return ts.strftime("%Y-%m-%d")
    return str(ts)[:10]


def _precompute_indicators(df: pd.DataFrame, conditions: list) -> dict:
    """Pre-compute all indicators needed by the conditions list.
    Returns dict keyed by indicator_key -> Series or dict of Series.
    """
    cache = {}

    for cond in conditions:
        name = cond.get("name", "")
        params = cond.get("params", {})

        if name in ("SMA", "EMA"):
            # Need both short and long MAs as separate series
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
    """Find the first candle index where all indicators have valid (non-NaN) values."""
    max_nan = 0
    for data in indicators.values():
        if isinstance(data, dict):
            for series in data.values():
                if isinstance(series, pd.Series):
                    first = series.first_valid_index()
                    if first is not None:
                        idx = series.index.get_loc(first)
                        max_nan = max(max_nan, idx)
        elif isinstance(data, pd.Series):
            first = data.first_valid_index()
            if first is not None:
                idx = data.index.get_loc(first)
                max_nan = max(max_nan, idx)
    return max_nan


def run_backtest(
    strategy_json: dict,
    symbol: str,
    timeframe: str = "1d",
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> BacktestResult:
    """Run a real backtest on historical OHLCV data.

    Args:
        strategy_json: full strategy dict with entry_conditions, exit_conditions, filters, risk_management
        symbol: e.g. "RELIANCE"
        timeframe: e.g. "1d"
        start_date/end_date: date range (defaults to last 3 years)
    """
    if not start_date:
        from datetime import timedelta
        end_date = end_date or datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=3 * 365)

    if not end_date:
        end_date = datetime.now(timezone.utc)

    # --- Fetch data ---
    try:
        df = get_ohlcv(symbol, timeframe, start_date, end_date)
    except ValueError as e:
        return BacktestResult(
            success=False, label="No Data", disclaimer=str(e),
            trades=[], win_rate=0, pnl=0, total_trades=0, wins=0, losses=0,
            data_source="none", message=str(e),
        )

    if df.empty or len(df) < 30:
        return BacktestResult(
            success=False, label="Insufficient Data",
            disclaimer=f"Only {len(df)} candles available for {symbol}/{timeframe}. Need at least 30.",
            trades=[], win_rate=0, pnl=0, total_trades=0, wins=0, losses=0,
            data_source=f"mongodb ({symbol}/{timeframe})",
            candles_processed=len(df), message="Insufficient data for backtest",
        )

    df = df.reset_index(drop=True)

    entry_conditions = strategy_json.get("entry_conditions", [])
    exit_conditions = strategy_json.get("exit_conditions", [])
    filters = strategy_json.get("filters", [])
    risk_mgmt = strategy_json.get("risk_management", {})

    if not entry_conditions:
        return BacktestResult(
            success=False, label="No Entry Conditions",
            disclaimer="Strategy must have at least one entry condition.",
            trades=[], win_rate=0, pnl=0, total_trades=0, wins=0, losses=0,
            data_source=f"mongodb ({symbol}/{timeframe})",
            candles_processed=len(df), message="No entry conditions defined",
        )

    # --- Pre-compute all indicators ---
    all_conditions = entry_conditions + exit_conditions + filters
    try:
        indicators = _precompute_indicators(df, all_conditions)
    except Exception as e:
        logger.error(f"Indicator computation failed: {e}")
        return BacktestResult(
            success=False, label="Indicator Error", disclaimer=str(e),
            trades=[], win_rate=0, pnl=0, total_trades=0, wins=0, losses=0,
            data_source=f"mongodb ({symbol}/{timeframe})",
            candles_processed=len(df), message=f"Indicator error: {e}",
        )

    # --- Find first valid candle (skip NaN warmup) ---
    start_idx = _first_valid_index(indicators) + 1  # +1 for crossover lookback

    sl_pct = risk_mgmt.get("stop_loss")
    tp_pct = risk_mgmt.get("take_profit")

    # --- Iterate candles ---
    trades: List[Trade] = []
    position = None  # None or {"entry_idx", "entry_price"}

    for i in range(start_idx, len(df)):
        close = df["close"].iloc[i]
        if math.isnan(close):
            continue

        if position is None:
            # Check filters first
            filters_pass = all(
                evaluate_condition(f, indicators, i, df) for f in filters
            )
            if not filters_pass:
                continue

            # Check all entry conditions (AND logic)
            entry_pass = all(
                evaluate_condition(c, indicators, i, df) for c in entry_conditions
            )
            if entry_pass:
                position = {"entry_idx": i, "entry_price": close}
        else:
            # Check exits
            entry_price = position["entry_price"]

            # Risk management exits
            if sl_pct and close <= entry_price * (1 - sl_pct / 100):
                _close_trade(trades, position, i, close, df)
                position = None
                continue

            if tp_pct and close >= entry_price * (1 + tp_pct / 100):
                _close_trade(trades, position, i, close, df)
                position = None
                continue

            # Indicator-based exits (ANY logic)
            if exit_conditions:
                exit_triggered = any(
                    evaluate_condition(c, indicators, i, df) for c in exit_conditions
                )
                if exit_triggered:
                    _close_trade(trades, position, i, close, df)
                    position = None

    # Close open position at last candle
    if position is not None:
        last_idx = len(df) - 1
        _close_trade(trades, position, last_idx, df["close"].iloc[last_idx], df)

    # --- Compute stats ---
    wins = sum(1 for t in trades if t.pnl_percent > 0)
    losses = len(trades) - wins
    total_pnl = sum(t.pnl_percent for t in trades)
    win_rate = round((wins / len(trades)) * 100, 1) if trades else 0

    return BacktestResult(
        success=True,
        label="Historical Backtest (Real Indicators)",
        disclaimer=(
            f"Backtest on {symbol} {timeframe} data from MongoDB. "
            "Does not account for fees, slippage, or market microstructure."
        ),
        trades=[asdict(t) for t in trades],
        win_rate=win_rate,
        pnl=round(total_pnl, 2),
        total_trades=len(trades),
        wins=wins,
        losses=losses,
        data_source=f"mongodb ({symbol}/{timeframe})",
        candles_processed=len(df),
        message="" if trades else "No signals generated. Strategy conditions were never met in the data range.",
    )


def _close_trade(trades: list, position: dict, exit_idx: int, exit_price: float, df: pd.DataFrame):
    """Record a closed trade."""
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
