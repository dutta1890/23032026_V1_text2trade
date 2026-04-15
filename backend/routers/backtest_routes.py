"""Backtest, multi-stock, and comparison endpoints."""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import logging
from datetime import datetime, timezone

from auth import get_current_user, get_optional_user
from database import db, analytics_db
from data.service import get_available_symbols, get_data_status
from backtest.engine import run_backtest as engine_run_backtest
from audit import log_audit, get_request_meta
from logging_config import get_request_id

logger = logging.getLogger(__name__)
router = APIRouter()

performance_records = db["performance_records"]


def _auto_record(user_id: str, result: dict, strategy: dict, symbol: str, timeframe: str, is_demo: bool = False):
    """Auto-record a successful backtest result to the performance tracker."""
    if not user_id or not result.get("success"):
        return
    metrics = result.get("metrics", {})
    try:
        performance_records.insert_one({
            "user_id": user_id,
            "strategy_id": strategy.get("id"),
            "strategy_name": strategy.get("metadata", {}).get("name", "Unnamed"),
            "symbol": symbol.upper().strip(),
            "timeframe": timeframe,
            "source": "backtest",
            "is_demo": is_demo,
            "sharpe": metrics.get("sharpe_ratio") or 0,
            "pnl_pct": metrics.get("total_pnl_pct") or 0,
            "win_rate": metrics.get("win_rate") or 0,
            "max_drawdown": metrics.get("max_drawdown_pct") or 0,
            "total_trades": metrics.get("total_trades") or 0,
            "profit_factor": metrics.get("profit_factor") or 0,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        logger.warning(f"Auto-record tracker failed: {e}")


def _send_backtest_email(current_user: dict, strategy: dict, symbol: str, result: dict):
    """Send backtest completion email if user has opted in."""
    try:
        from auth import users_collection
        uid = current_user.get("user_id")
        user_doc = users_collection.find_one({"user_id": uid}, {"_id": 0})
        prefs = user_doc.get("notification_preferences", {}) if user_doc else {}
        if not prefs.get("email_on_backtest_complete", True):
            return
        email = current_user.get("email") or (user_doc or {}).get("email")
        if not email:
            return
        import asyncio
        from email_service import send_email, backtest_complete_html, EMAIL_ENABLED
        if not EMAIL_ENABLED:
            return
        metrics = result.get("metrics", {})
        html = backtest_complete_html(
            strategy.get("metadata", {}).get("name", "Strategy"),
            symbol, metrics.get("total_pnl_pct", 0),
            metrics.get("win_rate", 0), metrics.get("total_trades", 0),
        )
        asyncio.ensure_future(send_email(email, f"Backtest Complete: {strategy.get('metadata',{}).get('name','Strategy')}", html))
    except Exception as e:
        logger.warning(f"Backtest email failed: {e}")


class BacktestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    strategy: dict
    slippage_pct: float = 0.05
    initial_capital: float = 100000
    brokerage_per_order: float = 20

class BacktestResponse(BaseModel):
    success: bool
    label: str
    disclaimer: str
    trades: list
    metrics: dict
    costs: dict
    equity_curve: list
    warnings: list
    data_source: str
    candles_processed: int = 0


@router.post("/backtest", response_model=BacktestResponse)
async def run_backtest_endpoint(request: Request, body: BacktestRequest, current_user: dict = Depends(get_optional_user)):
    import time as _time
    t0 = _time.time()
    try:
        strategy = body.strategy
        symbol = strategy.get("instrument", {}).get("symbol", "RELIANCE")
        timeframe = strategy.get("timeframe", {}).get("interval", "1d")
        strategy_id = strategy.get("id")
        user_id = current_user.get("user_id", current_user.get("email")) if current_user else "anonymous"
        meta = get_request_meta(request)

        log_audit(
            user_id=user_id, action="backtest_run",
            details={"strategy_id": strategy_id, "symbol": symbol, "timeframe": timeframe},
            ip_address=meta["ip"], user_agent=meta["ua"],
            request_id=get_request_id() or "", strategy_id=strategy_id,
        )

        result = engine_run_backtest(
            strategy, symbol, timeframe,
            slippage_pct=body.slippage_pct,
            initial_capital=body.initial_capital,
            brokerage_per_order=body.brokerage_per_order,
        )

        analytics_db["backtests_run"] += 1
        if result["success"] and result["trades"]:
            analytics_db["backtest_types"]["historical"] += 1
            is_demo = current_user.get("account_mode", "real") == "demo" if current_user else False
            _auto_record(user_id if user_id != "anonymous" else None, result, strategy, symbol, timeframe, is_demo)
            if current_user and not is_demo:
                _send_backtest_email(current_user, strategy, symbol, result)

        duration_ms = round((_time.time() - t0) * 1000)
        m = result.get("metrics", {})
        log_audit(
            user_id=user_id, action="backtest_completed",
            details={
                "strategy_id": strategy_id, "trade_count": m.get("total_trades", 0),
                "net_pnl": m.get("total_pnl_pct"), "sharpe": m.get("sharpe_ratio"),
                "duration_ms": duration_ms,
            },
            ip_address=meta["ip"], user_agent=meta["ua"],
            request_id=get_request_id() or "", strategy_id=strategy_id,
        )

        return result
    except Exception as e:
        logger.error(f"Backtest endpoint error: {e}")
        from backtest.metrics import calculate_metrics
        return {
            "success": False, "label": "Backtest Error",
            "disclaimer": str(e), "trades": [],
            "metrics": calculate_metrics([]), "costs": {},
            "equity_curve": [], "warnings": [str(e)],
            "data_source": "error", "candles_processed": 0,
        }


class MultiBacktestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    strategy: dict
    symbols: List[str] = Field(max_length=10)
    timeframe: str = "1d"
    initial_capital: float = 100000.0


@router.post("/backtest/multi")
async def multi_stock_backtest(request: Request, body: MultiBacktestRequest, current_user: dict = Depends(get_current_user)):
    if len(body.symbols) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 symbols allowed")
    if len(body.symbols) == 0:
        raise HTTPException(status_code=400, detail="At least 1 symbol required")

    from backtest.engine import run_backtest

    results = []
    for symbol in body.symbols:
        strat_copy = {**body.strategy}
        sym = symbol.upper().strip()
        tf = body.timeframe
        if "timeframe" in strat_copy and strat_copy.get("timeframe"):
            tf = strat_copy["timeframe"].get("interval", body.timeframe)

        try:
            bt_result = run_backtest(strat_copy, symbol=sym, timeframe=tf, initial_capital=body.initial_capital)
            bt_result["symbol"] = sym
            results.append(bt_result)
        except Exception as e:
            results.append({
                "symbol": sym, "success": False, "error": str(e),
                "metrics": {}, "trades": [],
            })

    results.sort(key=lambda r: r.get("metrics", {}).get("total_pnl_pct", float("-inf")) or float("-inf"), reverse=True)

    return {
        "results": results,
        "total_symbols": len(body.symbols),
        "successful": sum(1 for r in results if r.get("success")),
        "strategy_name": body.strategy.get("metadata", {}).get("name", "Unnamed"),
    }


class CompareBacktestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    strategies: List[dict] = Field(max_length=5)
    symbol: str
    timeframe: str = "1d"
    initial_capital: float = 100000.0


@router.post("/backtest/compare")
async def compare_strategies(request: Request, body: CompareBacktestRequest, current_user: dict = Depends(get_current_user)):
    if len(body.strategies) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 strategies allowed")
    if len(body.strategies) == 0:
        raise HTTPException(status_code=400, detail="At least 1 strategy required")

    from backtest.engine import run_backtest

    results = []
    for i, strat in enumerate(body.strategies):
        strat_name = strat.get("metadata", {}).get("name", f"Strategy {i+1}")
        sym = body.symbol.upper().strip()
        tf = body.timeframe
        if "timeframe" in strat and strat.get("timeframe"):
            tf = strat["timeframe"].get("interval", body.timeframe)

        try:
            bt_result = run_backtest(strat, symbol=sym, timeframe=tf, initial_capital=body.initial_capital)
            bt_result["strategy_name"] = strat_name
            bt_result["rank"] = 0
            results.append(bt_result)
        except Exception as e:
            results.append({
                "strategy_name": strat_name, "success": False, "error": str(e),
                "metrics": {}, "trades": [], "rank": 0,
            })

    def sort_key(r):
        if not r.get("success"):
            return (float("-inf"), float("-inf"))
        m = r.get("metrics", {})
        sharpe = m.get("sharpe_ratio", float("-inf"))
        if sharpe is None:
            sharpe = float("-inf")
        pnl = m.get("total_pnl_pct", 0) or 0
        return (sharpe, pnl)

    results.sort(key=sort_key, reverse=True)
    for i, r in enumerate(results):
        r["rank"] = i + 1

    return {
        "results": results,
        "symbol": body.symbol.upper().strip(),
        "total_strategies": len(body.strategies),
        "successful": sum(1 for r in results if r.get("success")),
        "best_strategy": results[0]["strategy_name"] if results and results[0].get("success") else None,
        "best_sharpe": results[0].get("metrics", {}).get("sharpe_ratio") if results and results[0].get("success") else None,
    }
