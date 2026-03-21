"""Strategy sharing endpoints."""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime, timezone
import secrets
import uuid
import logging

from auth import get_current_user
from database import db, strategies_collection, analytics_db

logger = logging.getLogger(__name__)
router = APIRouter()

shares_collection = db["shared_strategies"]

# Ensure index
try:
    shares_collection.create_index("share_token", unique=True)
except Exception:
    pass


@router.post("/strategy/{strategy_id}/share")
async def share_strategy(request: Request, strategy_id: str, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id", current_user.get("email"))
    strategy = strategies_collection.find_one(
        {"id": strategy_id, "user_id": user_id}, {"_id": 0}
    )
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    # Check if already shared
    existing = shares_collection.find_one(
        {"strategy_id": strategy_id, "owner_id": user_id}, {"_id": 0}
    )
    if existing:
        return {
            "success": True,
            "share_token": existing["share_token"],
            "already_shared": True,
        }

    share_token = secrets.token_urlsafe(16)
    now = datetime.now(timezone.utc).isoformat()
    shares_collection.insert_one({
        "share_token": share_token,
        "strategy_id": strategy_id,
        "owner_id": user_id,
        "owner_email": current_user.get("email", ""),
        "strategy_snapshot": strategy,
        "views": 0,
        "clones": 0,
        "created_at": now,
    })
    logger.info(f"Strategy {strategy_id} shared by {user_id} -> {share_token}")
    return {"success": True, "share_token": share_token, "already_shared": False}


@router.get("/shared/{share_token}")
async def get_shared_strategy(request: Request, share_token: str):
    """Public endpoint - no auth required."""
    doc = shares_collection.find_one({"share_token": share_token}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Shared strategy not found")

    shares_collection.update_one({"share_token": share_token}, {"$inc": {"views": 1}})

    strategy = doc["strategy_snapshot"]
    # Sanitize: remove user_id from public view
    strategy.pop("user_id", None)

    return {
        "success": True,
        "strategy": strategy,
        "shared_by": doc.get("owner_email", "").split("@")[0] + "@...",
        "shared_at": doc.get("created_at"),
        "views": doc.get("views", 0) + 1,
        "clones": doc.get("clones", 0),
    }


class CloneSharedRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Optional[str] = None
    symbol: Optional[str] = None


@router.post("/shared/{share_token}/clone")
async def clone_shared_strategy(request: Request, share_token: str, body: CloneSharedRequest = None, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id", current_user.get("email"))
    doc = shares_collection.find_one({"share_token": share_token}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Shared strategy not found")

    strategy = doc["strategy_snapshot"]
    now = datetime.now(timezone.utc).isoformat()
    strategy_id = str(uuid.uuid4())
    original_name = strategy.get("metadata", {}).get("name", "Shared Strategy")

    new_strat = {
        "id": strategy_id, "user_id": user_id, "version": "1.0",
        "metadata": {
            "name": (body.name if body and body.name else f"{original_name} (cloned)"),
            "description": strategy.get("metadata", {}).get("description", ""),
            "tags": ["cloned", "shared"],
            "created_at": now, "updated_at": now,
        },
        "market": strategy.get("market", {"type": "equity", "exchange": "NSE"}),
        "instrument": strategy.get("instrument", {"symbol": "RELIANCE"}),
        "timeframe": strategy.get("timeframe", {"interval": "1d"}),
        "entry_conditions": strategy.get("entry_conditions", []),
        "exit_conditions": strategy.get("exit_conditions", []),
        "filters": strategy.get("filters", []),
        "risk_management": strategy.get("risk_management", {}),
    }

    if body and body.symbol:
        new_strat["instrument"]["symbol"] = body.symbol.upper().strip()

    strategies_collection.insert_one(new_strat)
    new_strat.pop("_id", None)
    shares_collection.update_one({"share_token": share_token}, {"$inc": {"clones": 1}})
    analytics_db["strategies_created"] += 1

    logger.info(f"Shared strategy {share_token} cloned by {user_id} -> {strategy_id}")
    return {"success": True, "strategy_id": strategy_id, "strategy": new_strat}


@router.delete("/strategy/{strategy_id}/share")
async def unshare_strategy(request: Request, strategy_id: str, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id", current_user.get("email"))
    result = shares_collection.delete_one({"strategy_id": strategy_id, "owner_id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Share not found")
    return {"success": True, "message": "Strategy unshared"}
