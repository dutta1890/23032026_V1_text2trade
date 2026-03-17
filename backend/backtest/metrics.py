"""Performance metrics calculator for backtest trades.

Turns a raw trade list into comprehensive performance analytics.
"""

import math
from typing import Optional


def calculate_metrics(trades: list, initial_capital: float = 100000.0) -> dict:
    """Calculate performance metrics from a list of trade dicts.

    Each trade: {entry_price, exit_price, pnl_percent, pnl_points, holding_candles, entry_time, exit_time}
    Returns a flat dict of all metrics.
    """
    if not trades:
        return {
            "total_trades": 0,
            "win_rate": 0,
            "total_pnl_pct": 0,
            "total_pnl_abs": 0,
            "max_drawdown_pct": 0,
            "max_drawdown_duration": 0,
            "sharpe_ratio": None,
            "profit_factor": None,
            "avg_pnl_per_trade": 0,
            "avg_winning_trade": 0,
            "avg_losing_trade": 0,
            "max_consecutive_wins": 0,
            "max_consecutive_losses": 0,
            "avg_holding_period": 0,
            "wins": 0,
            "losses": 0,
            "best_trade": 0,
            "worst_trade": 0,
            "message": "No trades to analyze.",
        }

    wins = [t for t in trades if t["pnl_percent"] > 0]
    losses = [t for t in trades if t["pnl_percent"] <= 0]
    n = len(trades)

    total_pnl_pct = sum(t["pnl_percent"] for t in trades)

    # --- Equity curve for drawdown ---
    equity = initial_capital
    peak = equity
    max_dd_pct = 0.0
    max_dd_duration = 0
    dd_start = 0
    pnl_list = []

    for i, t in enumerate(trades):
        trade_pnl_abs = equity * (t["pnl_percent"] / 100)
        equity += trade_pnl_abs
        pnl_list.append(t["pnl_percent"])

        if equity > peak:
            peak = equity
            dd_start = i

        dd = (peak - equity) / peak * 100 if peak > 0 else 0
        if dd > max_dd_pct:
            max_dd_pct = dd
            max_dd_duration = i - dd_start

    total_pnl_abs = round(equity - initial_capital, 2)

    # --- Sharpe Ratio (annualized, risk-free 6% India) ---
    risk_free_daily = 6.0 / 252  # ~0.0238% per trading day
    if len(pnl_list) > 1:
        mean_ret = sum(pnl_list) / len(pnl_list)
        variance = sum((r - mean_ret) ** 2 for r in pnl_list) / (len(pnl_list) - 1)
        std_ret = math.sqrt(variance) if variance > 0 else 0
        if std_ret > 0:
            sharpe = ((mean_ret - risk_free_daily) / std_ret) * math.sqrt(252)
            sharpe = round(sharpe, 2)
        else:
            sharpe = None
    else:
        sharpe = None

    # --- Profit Factor ---
    gross_profit = sum(t["pnl_percent"] for t in wins)
    gross_loss = abs(sum(t["pnl_percent"] for t in losses))
    profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else None

    # --- Consecutive wins/losses ---
    max_consec_w, max_consec_l = 0, 0
    curr_w, curr_l = 0, 0
    for t in trades:
        if t["pnl_percent"] > 0:
            curr_w += 1
            curr_l = 0
        else:
            curr_l += 1
            curr_w = 0
        max_consec_w = max(max_consec_w, curr_w)
        max_consec_l = max(max_consec_l, curr_l)

    # --- Averages ---
    avg_pnl = round(total_pnl_pct / n, 2)
    avg_win = round(sum(t["pnl_percent"] for t in wins) / len(wins), 2) if wins else 0
    avg_loss = round(sum(t["pnl_percent"] for t in losses) / len(losses), 2) if losses else 0
    avg_hold = round(sum(t["holding_candles"] for t in trades) / n, 1)
    best = round(max(t["pnl_percent"] for t in trades), 2)
    worst = round(min(t["pnl_percent"] for t in trades), 2)

    return {
        "total_trades": n,
        "win_rate": round((len(wins) / n) * 100, 1),
        "total_pnl_pct": round(total_pnl_pct, 2),
        "total_pnl_abs": total_pnl_abs,
        "max_drawdown_pct": round(max_dd_pct, 2),
        "max_drawdown_duration": max_dd_duration,
        "sharpe_ratio": sharpe,
        "profit_factor": profit_factor,
        "avg_pnl_per_trade": avg_pnl,
        "avg_winning_trade": avg_win,
        "avg_losing_trade": avg_loss,
        "max_consecutive_wins": max_consec_w,
        "max_consecutive_losses": max_consec_l,
        "avg_holding_period": avg_hold,
        "wins": len(wins),
        "losses": len(losses),
        "best_trade": best,
        "worst_trade": worst,
        "message": "",
    }
