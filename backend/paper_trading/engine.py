"""Paper Trading Engine — simulates live execution by replaying cached OHLCV data.

This is a "forward backtest" on the most recent data. It uses the same indicator
calculator and condition evaluator as the backtest engine, but presents results
as a simulated live portfolio.
"""

import logging
import math
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from typing import Optional

import pandas as pd

from data.service import get_ohlcv
from indicators.calculator import compute_indicator, CALCULATOR_REGISTRY
from backtest.evaluator import evaluate_condition, _indicator_key
from backtest.engine import (
    _precompute_indicators, _first_valid_index, _parse_risk_management, _ts_str, _ts_time_str
)
from backtest.costs import apply_slippage, CostConfig, calculate_trade_costs
from backtest.metrics import calculate_metrics

logger = logging.getLogger(__name__)


def deploy_paper_trade(
    strategy: dict,
    symbol: str,
    timeframe: str,
    initial_capital: float,
    user_id: str,
    db,
    lookback_days: int = 60,
    slippage_pct: float = 0.05,
) -> dict:
    """Deploy a strategy for paper trading.

    Replays the last `lookback_days` of cached OHLCV data, evaluating conditions
    candle by candle to simulate live execution.

    Returns the paper_trade document that was inserted into MongoDB.
    """
    paper_trade_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=lookback_days)

    # Fetch data
    try:
        df = get_ohlcv(symbol, timeframe, start_date, now)
    except ValueError as e:
        return {"error": str(e)}

    if df.empty or len(df) < 10:
        return {"error": f"Insufficient data for {symbol}/{timeframe}. Only {len(df)} candles."}

    df = df.reset_index(drop=True)

    # Parse strategy
    entry_conditions = strategy.get("entry_conditions", [])
    exit_conditions = strategy.get("exit_conditions", [])
    filters = strategy.get("filters", [])
    risk_mgmt = strategy.get("risk_management", {})

    if not entry_conditions:
        return {"error": "Strategy has no entry conditions."}

    rp = _parse_risk_management(risk_mgmt)

    # Pre-compute indicators
    all_conditions = entry_conditions + exit_conditions + filters
    try:
        indicators = _precompute_indicators(df, all_conditions)
    except Exception as e:
        return {"error": f"Indicator computation failed: {e}"}

    start_idx = _first_valid_index(indicators) + 1
    is_intraday = timeframe not in ("1d", "1wk", "1mo")

    # --- Simulate execution ---
    trades = []
    position = None
    equity = initial_capital
    equity_curve = [{"timestamp": _ts_str(df["timestamp"].iloc[0]), "equity": round(equity, 2), "drawdown_pct": 0}]
    peak_equity = equity
    daily_loss = 0.0
    daily_trades = 0
    current_date = None

    for i in range(start_idx, len(df)):
        close = df["close"].iloc[i]
        if math.isnan(close):
            continue

        candle_ts = df["timestamp"].iloc[i]
        cd = candle_ts.date() if hasattr(candle_ts, "date") else str(candle_ts)[:10]
        if cd != current_date:
            current_date = cd
            daily_loss = 0.0
            daily_trades = 0

        if position is None:
            if daily_loss >= rp["max_loss_day"] or daily_trades >= rp["max_trades_day"]:
                continue

            filters_ok = all(evaluate_condition(f, indicators, i, df) for f in filters)
            if not filters_ok:
                continue

            entry_ok = all(evaluate_condition(c, indicators, i, df) for c in entry_conditions)
            if entry_ok:
                slipped = apply_slippage(close, slippage_pct, is_entry=True)
                position = {
                    "entry_idx": i, "entry_price": slipped, "raw_entry": close,
                    "entry_time": _ts_str(candle_ts),
                    "trailing_sl": None, "highest_since_entry": close,
                }
                if rp["trailing_enabled"] and rp["trailing_pct"]:
                    position["trailing_sl"] = slipped * (1 - rp["trailing_pct"] / 100)
        else:
            entry_price = position["entry_price"]
            raw_entry = position["raw_entry"]
            exit_reason = ""

            if close > position["highest_since_entry"]:
                position["highest_since_entry"] = close

            # Time exit
            if rp["time_exit_enabled"] and is_intraday:
                if _ts_time_str(candle_ts) >= rp["time_exit_str"]:
                    exit_reason = "time_exit"

            # Trailing SL
            if not exit_reason and rp["trailing_enabled"] and position["trailing_sl"] is not None:
                high = position["highest_since_entry"]
                profit_pct = ((high - raw_entry) / raw_entry) * 100
                if profit_pct >= rp["trailing_activation"]:
                    if rp["trailing_pct"]:
                        new_tsl = high * (1 - rp["trailing_pct"] / 100)
                        position["trailing_sl"] = max(position["trailing_sl"], new_tsl)
                if close <= position["trailing_sl"]:
                    exit_reason = "trailing_sl"

            # Fixed SL
            if not exit_reason:
                if rp["sl_pct"] and close <= raw_entry * (1 - rp["sl_pct"] / 100):
                    exit_reason = "stop_loss"
                elif rp["sl_points"] and close <= raw_entry - rp["sl_points"]:
                    exit_reason = "stop_loss"

            # Target profit
            if not exit_reason:
                if rp["tp_pct"] and close >= raw_entry * (1 + rp["tp_pct"] / 100):
                    exit_reason = "target_profit"
                elif rp["tp_points"] and close >= raw_entry + rp["tp_points"]:
                    exit_reason = "target_profit"

            # Indicator exit
            if not exit_reason and exit_conditions:
                if any(evaluate_condition(c, indicators, i, df) for c in exit_conditions):
                    exit_reason = "indicator_exit"

            if exit_reason:
                slipped_exit = apply_slippage(close, slippage_pct, is_entry=False)
                pnl_pct = round(((slipped_exit - entry_price) / entry_price) * 100, 2)
                pnl_pts = round(slipped_exit - entry_price, 2)
                trades.append({
                    "entry_time": position["entry_time"],
                    "entry_price": round(entry_price, 2),
                    "exit_time": _ts_str(candle_ts),
                    "exit_price": round(slipped_exit, 2),
                    "pnl_points": pnl_pts,
                    "pnl_percent": pnl_pct,
                    "holding_candles": i - position["entry_idx"],
                    "exit_reason": exit_reason,
                })
                equity += equity * (pnl_pct / 100)
                peak_equity = max(peak_equity, equity)
                dd = round((peak_equity - equity) / peak_equity * 100, 2) if peak_equity > 0 else 0
                equity_curve.append({
                    "timestamp": _ts_str(candle_ts),
                    "equity": round(equity, 2),
                    "drawdown_pct": dd,
                })
                if pnl_pct < 0:
                    daily_loss += abs(pnl_pct)
                daily_trades += 1
                position = None

    # Build current position info
    current_pos = None
    if position is not None:
        last_close = df["close"].iloc[-1]
        unrealized_pnl = round(((last_close - position["entry_price"]) / position["entry_price"]) * 100, 2)
        current_pos = {
            "entry_time": position["entry_time"],
            "entry_price": round(position["entry_price"], 2),
            "current_price": round(last_close, 2),
            "unrealized_pnl_pct": unrealized_pnl,
            "unrealized_pnl_points": round(last_close - position["entry_price"], 2),
            "holding_candles": len(df) - 1 - position["entry_idx"],
        }

    metrics = calculate_metrics(trades, initial_capital)

    # Create paper trade document
    doc = {
        "paper_trade_id": paper_trade_id,
        "user_id": user_id,
        "strategy_id": strategy.get("id", "manual"),
        "status": "completed",
        "start_time": now.isoformat(),
        "current_position": current_pos,
        "trades": trades,
        "equity_curve": equity_curve,
        "metrics": metrics,
        "settings": {
            "symbol": symbol,
            "timeframe": timeframe,
            "initial_capital": initial_capital,
            "slippage_pct": slippage_pct,
            "lookback_days": lookback_days,
        },
        "label": "Paper Trade (Simulated)",
        "disclaimer": (
            f"Simulated paper trade on {symbol} {timeframe} using cached data from last {lookback_days} days. "
            "Not real-time. Does not account for live market conditions."
        ),
        "final_equity": round(equity, 2),
        "total_trades": len(trades),
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    db.paper_trades.insert_one(doc)

    # Return without _id
    doc.pop("_id", None)
    return doc


def stop_paper_trade(paper_trade_id: str, user_id: str, db) -> dict:
    """Stop a paper trade and close any open position."""
    doc = db.paper_trades.find_one(
        {"paper_trade_id": paper_trade_id, "user_id": user_id},
        {"_id": 0}
    )
    if not doc:
        return None

    now = datetime.now(timezone.utc)

    # If there's an open position, close it at current price
    if doc.get("current_position"):
        pos = doc["current_position"]
        closed_trade = {
            "entry_time": pos["entry_time"],
            "entry_price": pos["entry_price"],
            "exit_time": now.isoformat()[:10],
            "exit_price": pos["current_price"],
            "pnl_points": pos["unrealized_pnl_points"],
            "pnl_percent": pos["unrealized_pnl_pct"],
            "holding_candles": pos["holding_candles"],
            "exit_reason": "manual_stop",
        }
        db.paper_trades.update_one(
            {"paper_trade_id": paper_trade_id},
            {
                "$push": {"trades": closed_trade},
                "$set": {
                    "current_position": None,
                    "status": "stopped",
                    "updated_at": now.isoformat(),
                },
            },
        )
    else:
        db.paper_trades.update_one(
            {"paper_trade_id": paper_trade_id},
            {"$set": {"status": "stopped", "updated_at": now.isoformat()}},
        )

    return db.paper_trades.find_one(
        {"paper_trade_id": paper_trade_id}, {"_id": 0}
    )


def pause_paper_trade(paper_trade_id: str, user_id: str, db) -> dict:
    """Pause a paper trade."""
    result = db.paper_trades.find_one_and_update(
        {"paper_trade_id": paper_trade_id, "user_id": user_id},
        {"$set": {"status": "paused", "updated_at": datetime.now(timezone.utc).isoformat()}},
        return_document=True,
    )
    if result:
        result.pop("_id", None)
    return result
