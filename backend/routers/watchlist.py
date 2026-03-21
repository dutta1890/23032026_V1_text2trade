"""Watchlist endpoints."""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime, timezone
import uuid
import logging

from auth import get_current_user
from database import db

logger = logging.getLogger(__name__)
router = APIRouter()

watchlist_collection = db["watchlist"]

# Ensure indexes
try:
    watchlist_collection.create_index("user_id")
    watchlist_collection.create_index([("user_id", 1), ("symbol", 1)])
except Exception:
    pass


class WatchlistAddRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    symbol: str = Field(max_length=20)
    note: Optional[str] = Field(default=None, max_length=200)
    conditions_snapshot: Optional[list] = None
    preset_name: Optional[str] = None
    indicator_values: Optional[dict] = None


class WatchlistUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    note: Optional[str] = Field(default=None, max_length=200)


@router.post("/watchlist")
async def add_to_watchlist(request: Request, body: WatchlistAddRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id", current_user.get("email"))
    symbol = body.symbol.upper().strip()

    # Check duplicate
    existing = watchlist_collection.find_one(
        {"user_id": user_id, "symbol": symbol}, {"_id": 0}
    )
    if existing:
        raise HTTPException(status_code=409, detail=f"{symbol} is already in your watchlist")

    # Limit watchlist size
    count = watchlist_collection.count_documents({"user_id": user_id})
    if count >= 20:
        raise HTTPException(status_code=400, detail="Watchlist limit reached (max 20)")

    now = datetime.now(timezone.utc).isoformat()
    item_id = str(uuid.uuid4())
    doc = {
        "item_id": item_id,
        "user_id": user_id,
        "symbol": symbol,
        "note": body.note,
        "conditions_snapshot": body.conditions_snapshot,
        "preset_name": body.preset_name,
        "indicator_values": body.indicator_values,
        "created_at": now,
    }
    watchlist_collection.insert_one(doc)
    doc.pop("_id", None)
    logger.info(f"Watchlist: {user_id} added {symbol}")
    return {"success": True, "item": doc}


@router.get("/watchlist")
async def get_watchlist(request: Request, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id", current_user.get("email"))
    items = list(watchlist_collection.find(
        {"user_id": user_id}, {"_id": 0}
    ).sort("created_at", -1))
    return {"watchlist": items, "count": len(items)}


@router.put("/watchlist/{item_id}")
async def update_watchlist_item(request: Request, item_id: str, body: WatchlistUpdateRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id", current_user.get("email"))
    result = watchlist_collection.update_one(
        {"item_id": item_id, "user_id": user_id},
        {"$set": {"note": body.note}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Watchlist item not found")
    return {"success": True}


@router.delete("/watchlist/{item_id}")
async def remove_from_watchlist(request: Request, item_id: str, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id", current_user.get("email"))
    result = watchlist_collection.delete_one({"item_id": item_id, "user_id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Watchlist item not found")
    logger.info(f"Watchlist: {user_id} removed {item_id}")
    return {"success": True}
