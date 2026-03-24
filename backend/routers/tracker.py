"""Strategy Performance Tracker — aggregated backtest/paper-trade analytics."""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import logging

from auth import get_current_user
from database import db

logger = logging.getLogger(__name__)
router = APIRouter()

records_collection = db["performance_records"]

try:
    records_collection.create_index("user_id")
    records_collection.create_index([("user_id", 1), ("recorded_at", -1)])
except Exception:
    pass


class RecordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    strategy_id: Optional[str] = None
    strategy_name: str = Field(max_length=120)
    symbol: str = Field(max_length=20)
    timeframe: str = Field(max_length=10, default="1d")
    source: str = Field(default="backtest")  # backtest | paper_trade
    sharpe: float = 0
    pnl_pct: float = 0
    win_rate: float = 0
    max_drawdown: float = 0
    total_trades: int = 0
    profit_factor: float = 0


def _is_demo_mode(current_user: dict) -> bool:
    return current_user.get("account_mode", "real") == "demo"


@router.post("/tracker/record")
async def record_performance(request: Request, body: RecordRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id", current_user.get("email"))
    demo = _is_demo_mode(current_user)
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "user_id": user_id,
        "strategy_id": body.strategy_id,
        "strategy_name": body.strategy_name,
        "symbol": body.symbol.upper().strip(),
        "timeframe": body.timeframe,
        "source": body.source,
        "is_demo": demo,
        "sharpe": body.sharpe,
        "pnl_pct": body.pnl_pct,
        "win_rate": body.win_rate,
        "max_drawdown": body.max_drawdown,
        "total_trades": body.total_trades,
        "profit_factor": body.profit_factor,
        "recorded_at": now,
    }
    records_collection.insert_one(doc)
    doc.pop("_id", None)
    return {"success": True}


@router.get("/tracker/dashboard")
async def tracker_dashboard(request: Request, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id", current_user.get("email"))
    demo = _is_demo_mode(current_user)
    q = {"user_id": user_id}
    if demo:
        q["is_demo"] = True
    else:
        q["is_demo"] = {"$ne": True}
    records = list(records_collection.find(
        q, {"_id": 0}
    ).sort("recorded_at", -1))

    if not records:
        return {
            "total_records": 0, "total_backtests": 0, "total_paper_trades": 0,
            "avg_sharpe": 0, "avg_pnl": 0, "avg_win_rate": 0,
            "best_strategy": None, "worst_strategy": None,
            "cumulative_pnl": [], "strategy_rankings": [],
            "improvement": None, "recent_activity": [],
        }

    bt = [r for r in records if r.get("source") == "backtest"]
    pt = [r for r in records if r.get("source") == "paper_trade"]

    # Averages
    all_sharpes = [r["sharpe"] for r in records if r.get("sharpe")]
    all_pnl = [r["pnl_pct"] for r in records]
    all_wr = [r["win_rate"] for r in records if r.get("win_rate")]
    avg_sharpe = sum(all_sharpes) / len(all_sharpes) if all_sharpes else 0
    avg_pnl = sum(all_pnl) / len(all_pnl) if all_pnl else 0
    avg_wr = sum(all_wr) / len(all_wr) if all_wr else 0

    # Best/worst by P&L
    sorted_by_pnl = sorted(records, key=lambda r: r.get("pnl_pct", 0), reverse=True)
    best = sorted_by_pnl[0] if sorted_by_pnl else None
    worst = sorted_by_pnl[-1] if len(sorted_by_pnl) > 1 else None

    # Cumulative P&L over time (chronological)
    chrono = sorted(records, key=lambda r: r.get("recorded_at", ""))
    cum_pnl = []
    running = 0
    for r in chrono:
        running += r.get("pnl_pct", 0)
        cum_pnl.append({
            "date": r["recorded_at"][:10] if r.get("recorded_at") else "",
            "cumulative_pnl": round(running, 2),
            "strategy": r.get("strategy_name", ""),
        })

    # Strategy rankings (group by strategy_name, avg metrics)
    strat_groups = {}
    for r in records:
        name = r.get("strategy_name", "Unknown")
        if name not in strat_groups:
            strat_groups[name] = {"runs": [], "strategy_id": r.get("strategy_id")}
        strat_groups[name]["runs"].append(r)

    rankings = []
    for name, group in strat_groups.items():
        runs = group["runs"]
        rankings.append({
            "strategy_name": name,
            "strategy_id": group["strategy_id"],
            "run_count": len(runs),
            "avg_sharpe": round(sum(r["sharpe"] for r in runs) / len(runs), 4) if runs else 0,
            "avg_pnl": round(sum(r["pnl_pct"] for r in runs) / len(runs), 2) if runs else 0,
            "best_pnl": round(max(r["pnl_pct"] for r in runs), 2) if runs else 0,
            "avg_win_rate": round(sum(r["win_rate"] for r in runs) / len(runs), 2) if runs else 0,
            "total_trades": sum(r["total_trades"] for r in runs),
            "symbols": list(set(r["symbol"] for r in runs)),
            "last_run": max(r.get("recorded_at", "") for r in runs),
        })
    rankings.sort(key=lambda r: r["avg_sharpe"], reverse=True)
    for i, r in enumerate(rankings):
        r["rank"] = i + 1

    # Improvement insight: compare first half vs second half
    improvement = None
    if len(chrono) >= 4:
        mid = len(chrono) // 2
        first_half = chrono[:mid]
        second_half = chrono[mid:]
        fh_sharpe = sum(r["sharpe"] for r in first_half) / len(first_half) if first_half else 0
        sh_sharpe = sum(r["sharpe"] for r in second_half) / len(second_half) if second_half else 0
        fh_pnl = sum(r["pnl_pct"] for r in first_half) / len(first_half) if first_half else 0
        sh_pnl = sum(r["pnl_pct"] for r in second_half) / len(second_half) if second_half else 0
        improvement = {
            "early_avg_sharpe": round(fh_sharpe, 4),
            "recent_avg_sharpe": round(sh_sharpe, 4),
            "sharpe_change_pct": round(((sh_sharpe - fh_sharpe) / abs(fh_sharpe) * 100) if fh_sharpe else 0, 1),
            "early_avg_pnl": round(fh_pnl, 2),
            "recent_avg_pnl": round(sh_pnl, 2),
            "pnl_change_pct": round(((sh_pnl - fh_pnl) / abs(fh_pnl) * 100) if fh_pnl else 0, 1),
            "early_count": len(first_half),
            "recent_count": len(second_half),
        }

    # Recent activity (last 10)
    recent = [{
        "strategy_name": r.get("strategy_name"),
        "symbol": r.get("symbol"),
        "source": r.get("source"),
        "pnl_pct": r.get("pnl_pct", 0),
        "sharpe": r.get("sharpe", 0),
        "total_trades": r.get("total_trades", 0),
        "recorded_at": r.get("recorded_at"),
    } for r in records[:10]]

    return {
        "total_records": len(records),
        "total_backtests": len(bt),
        "total_paper_trades": len(pt),
        "avg_sharpe": round(avg_sharpe, 4),
        "avg_pnl": round(avg_pnl, 2),
        "avg_win_rate": round(avg_wr, 2),
        "best_strategy": {
            "name": best.get("strategy_name"), "pnl_pct": best.get("pnl_pct"),
            "sharpe": best.get("sharpe"), "symbol": best.get("symbol"),
        } if best else None,
        "worst_strategy": {
            "name": worst.get("strategy_name"), "pnl_pct": worst.get("pnl_pct"),
            "sharpe": worst.get("sharpe"), "symbol": worst.get("symbol"),
        } if worst else None,
        "cumulative_pnl": cum_pnl,
        "strategy_rankings": rankings,
        "improvement": improvement,
        "recent_activity": recent,
    }


@router.get("/tracker/history")
async def tracker_history(request: Request, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id", current_user.get("email"))
    demo = _is_demo_mode(current_user)
    q = {"user_id": user_id}
    if demo:
        q["is_demo"] = True
    else:
        q["is_demo"] = {"$ne": True}
    records = list(records_collection.find(
        q, {"_id": 0}
    ).sort("recorded_at", -1).limit(50))
    return {"records": records, "count": len(records)}
