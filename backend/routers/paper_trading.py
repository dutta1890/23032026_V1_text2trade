"""Paper trading endpoints."""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field, ConfigDict
import logging

from auth import get_current_user
from database import db, strategies_collection
from paper_trading.engine import deploy_paper_trade, stop_paper_trade, pause_paper_trade

logger = logging.getLogger(__name__)
router = APIRouter()


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
    return result


@router.get("/paper-trades")
async def list_paper_trades(request: Request, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id", current_user.get("email"))
    docs = list(db.paper_trades.find(
        {"user_id": user_id}, {"_id": 0}
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
