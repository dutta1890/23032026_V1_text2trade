"""Optimizer API endpoints."""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import logging

from auth import get_current_user
from database import strategies_collection
from optimizer.engine import run_optimization, _detect_tunable_params

logger = logging.getLogger(__name__)
router = APIRouter()


class ParamRange(BaseModel):
    path: str
    label: Optional[str] = None
    min: float
    max: float
    steps: int = Field(default=5, ge=2, le=10)
    step_type: str = "float"


class OptimizeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    strategy_id: Optional[str] = None
    strategy: Optional[dict] = None
    param_ranges: List[ParamRange] = Field(max_length=6)
    symbol: Optional[str] = None
    timeframe: Optional[str] = None
    initial_capital: float = 100000


@router.post("/optimizer/run")
async def run_optimizer(request: Request, body: OptimizeRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id", current_user.get("email"))

    # Get strategy
    strategy = body.strategy
    if body.strategy_id and not strategy:
        doc = strategies_collection.find_one(
            {"id": body.strategy_id, "user_id": user_id}, {"_id": 0}
        )
        if not doc:
            raise HTTPException(status_code=404, detail="Strategy not found")
        strategy = doc

    if not strategy:
        raise HTTPException(status_code=400, detail="Provide strategy_id or strategy object")

    if not body.param_ranges:
        raise HTTPException(status_code=400, detail="At least 1 parameter range required")

    # Calculate total combinations
    total = 1
    for pr in body.param_ranges:
        total *= pr.steps
    if total > 500:
        raise HTTPException(status_code=400, detail=f"Too many combinations ({total}). Reduce steps or parameters (max 500).")

    try:
        result = run_optimization(
            strategy=strategy,
            param_ranges=[pr.model_dump() for pr in body.param_ranges],
            symbol=body.symbol,
            timeframe=body.timeframe,
            initial_capital=body.initial_capital,
        )
        return result
    except Exception as e:
        logger.error(f"Optimizer error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/optimizer/detect-params")
async def detect_params(request: Request, body: dict, current_user: dict = Depends(get_current_user)):
    """Auto-detect tunable parameters from a strategy."""
    user_id = current_user.get("user_id", current_user.get("email"))

    strategy = body.get("strategy")
    strategy_id = body.get("strategy_id")

    if strategy_id and not strategy:
        doc = strategies_collection.find_one(
            {"id": strategy_id, "user_id": user_id}, {"_id": 0}
        )
        if not doc:
            raise HTTPException(status_code=404, detail="Strategy not found")
        strategy = doc

    if not strategy:
        raise HTTPException(status_code=400, detail="Provide strategy_id or strategy object")

    tunables = _detect_tunable_params(strategy)
    return {"tunables": tunables, "count": len(tunables)}
