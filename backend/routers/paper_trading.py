"""Paper trading endpoints."""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field, ConfigDict
import logging

from auth import get_current_user
from database import db, strategies_collection
from paper_trading.engine import deploy_paper_trade, stop_paper_trade, pause_paper_trade
from audit import log_audit, get_request_meta
from logging_config import get_request_id
from monitoring import record_order

logger = logging.getLogger(__name__)
router = APIRouter()


def _is_demo_mode(current_user: dict) -> bool:
    return current_user.get("account_mode", "real") == "demo"


class PaperTradeDeployRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    strategy_id: str
    symbol: str = "RELIANCE"
    timeframe: str = "1d"
    initial_capital: float = Field(default=100000, ge=1000, le=10000000)
    lookback_days: int = Field(default=60, ge=7, le=365)
    slippage_pct: float = Field(default=0.05, ge=0, le=1)


@router.post("/paper-trade/deploy")
async def deploy_paper_trade_endpoint(request: Request, body: PaperTradeDeployRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id", current_user.get("email"))
    demo = _is_demo_mode(current_user)
    strategy_doc = strategies_collection.find_one(
        {"id": body.strategy_id, "user_id": user_id}, {"_id": 0}
    )
    if not strategy_doc:
        raise HTTPException(status_code=404, detail="Strategy not found")

    result = deploy_paper_trade(
        strategy=strategy_doc, symbol=body.symbol, timeframe=body.timeframe,
        initial_capital=body.initial_capital, user_id=user_id, db=db,
        lookback_days=body.lookback_days, slippage_pct=body.slippage_pct,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    # Tag with demo mode
    db.paper_trades.update_one(
        {"paper_trade_id": result["paper_trade_id"]},
        {"$set": {"is_demo": demo}}
    )
    result["is_demo"] = demo
    meta = get_request_meta(request)
    log_audit(
        user_id=user_id, action="paper_trade_deployed",
        details={
            "strategy_id": body.strategy_id, "symbol": body.symbol,
            "capital": body.initial_capital, "paper_trade_id": result.get("paper_trade_id"),
        },
        ip_address=meta["ip"], user_agent=meta["ua"],
        request_id=get_request_id() or "", strategy_id=body.strategy_id,
    )
    record_order(user_id, "paper")
    return result


@router.get("/paper-trades")
async def list_paper_trades(request: Request, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id", current_user.get("email"))
    demo = _is_demo_mode(current_user)
    query = {"user_id": user_id}
    if demo:
        query["is_demo"] = True
    else:
        query["is_demo"] = {"$ne": True}
    docs = list(db.paper_trades.find(
        query, {"_id": 0}
    ).sort("created_at", -1))
    return {"paper_trades": docs, "count": len(docs)}


@router.get("/paper-trade/{paper_trade_id}")
async def get_paper_trade(request: Request, paper_trade_id: str, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id", current_user.get("email"))
    doc = db.paper_trades.find_one(
        {"paper_trade_id": paper_trade_id, "user_id": user_id}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Paper trade not found")
    return doc


@router.post("/paper-trade/{paper_trade_id}/pause")
async def pause_paper_trade_endpoint(request: Request, paper_trade_id: str, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id", current_user.get("email"))
    result = pause_paper_trade(paper_trade_id, user_id, db)
    if not result:
        raise HTTPException(status_code=404, detail="Paper trade not found")
    return {"success": True, "status": result.get("status"), "paper_trade_id": paper_trade_id}


@router.post("/paper-trade/{paper_trade_id}/stop")
async def stop_paper_trade_endpoint(request: Request, paper_trade_id: str, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id", current_user.get("email"))
    result = stop_paper_trade(paper_trade_id, user_id, db)
    if not result:
        raise HTTPException(status_code=404, detail="Paper trade not found")
    return result
