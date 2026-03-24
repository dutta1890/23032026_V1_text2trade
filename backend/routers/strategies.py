"""Strategy CRUD endpoints."""
from fastapi import APIRouter, HTTPException, Depends, Request
from datetime import datetime, timezone
import uuid
import logging

from auth import get_current_user
from indicator_registry import validate_condition
from logging_config import set_user_id
from database import strategies_collection, analytics_db
from models import Strategy, StrategyResponse, StrategiesListResponse

logger = logging.getLogger(__name__)
router = APIRouter()


def _is_demo_mode(current_user: dict) -> bool:
    """Check if user is currently in demo mode."""
    return current_user.get("account_mode", "real") == "demo"


def validate_strategy(strategy: Strategy):
    errors = []
    if not strategy.entry_conditions:
        errors.append("At least one entry condition is required")
    if not strategy.timeframe or not strategy.timeframe.interval:
        errors.append("Timeframe is required")

    rm = strategy.risk_management
    if rm:
        if rm.trailing_stop_loss and rm.trailing_stop_loss.enabled and rm.stop_loss is None:
            errors.append("Trailing stop loss requires a base stop loss")
        if rm.position_sizing and rm.position_sizing.method == "risk_per_trade" and rm.stop_loss is None:
            errors.append("risk_per_trade position sizing requires a stop loss")
        if rm.time_based_exit and rm.time_based_exit.enabled:
            tf = strategy.timeframe.interval if strategy.timeframe else ""
            if tf in ("1d", "1wk", "1mo"):
                errors.append("Time-based exit is only meaningful for intraday timeframes")

    for cond in strategy.entry_conditions:
        if not validate_condition(cond.model_dump()):
            errors.append(f"Invalid entry condition: {cond.name}")
    for cond in strategy.exit_conditions:
        if not validate_condition(cond.model_dump()):
            errors.append(f"Invalid exit condition: {cond.name}")
    for cond in strategy.filters:
        if not validate_condition(cond.model_dump()):
            errors.append(f"Invalid filter: {cond.name}")
    return errors


def get_next_version(name: str, user_id: str) -> str:
    existing = list(strategies_collection.find(
        {"metadata.name": name, "user_id": user_id}, {"version": 1, "_id": 0}
    ))
    if not existing:
        return "1.0"
    versions = [float(s.get("version", "1.0")) for s in existing]
    return str(max(versions) + 1.0)


@router.post("/strategy", response_model=StrategyResponse)
async def create_strategy(request: Request, strategy: Strategy, current_user: dict = Depends(get_current_user)):
    set_user_id(current_user.get("email", ""))
    errors = validate_strategy(strategy)
    if errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))

    try:
        user_id = current_user.get("user_id", current_user.get("email"))
        demo = _is_demo_mode(current_user)
        now = datetime.now(timezone.utc).isoformat()
        strategy_id = str(uuid.uuid4())

        strategy_doc = strategy.model_dump()
        strategy_doc["id"] = strategy_id
        strategy_doc["user_id"] = user_id
        strategy_doc["is_demo"] = demo
        strategy_doc["version"] = get_next_version(strategy.metadata.name, user_id)
        strategy_doc["metadata"]["created_at"] = now
        strategy_doc["metadata"]["updated_at"] = now

        strategies_collection.insert_one(strategy_doc)
        strategy_doc.pop("_id", None)
        analytics_db["strategies_created"] += 1
        logger.info(f"Strategy created: {strategy_id} by {user_id} (demo={demo})")
        return {"success": True, "strategy": strategy_doc}
    except Exception as e:
        logger.error(f"Strategy creation failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/strategies", response_model=StrategiesListResponse)
async def get_strategies(request: Request, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id", current_user.get("email"))
    demo = _is_demo_mode(current_user)
    query = {"user_id": user_id}
    if demo:
        query["is_demo"] = True
    else:
        query["is_demo"] = {"$ne": True}
    docs = list(strategies_collection.find(
        query, {"_id": 0}
    ).sort("metadata.created_at", -1).limit(50))

    for d in docs:
        if "risk_management" in d and isinstance(d["risk_management"], dict):
            rm = d["risk_management"]
            if "trailing_stop_loss" not in rm:
                rm["trailing_stop_loss"] = {"enabled": False, "type": "percentage", "value": 1.0, "activation_profit": 0}
            if "time_based_exit" not in rm:
                rm["time_based_exit"] = {"enabled": False, "exit_time": "15:10"}
            if "daily_limits" not in rm:
                rm["daily_limits"] = {"max_loss_per_day": 5.0, "max_trades_per_day": 10}
            if "position_sizing" not in rm:
                rm["position_sizing"] = {"method": "fixed_quantity", "value": 1}

    return {"success": True, "strategies": docs, "count": len(docs)}


@router.get("/strategy/{strategy_id}")
async def get_strategy(request: Request, strategy_id: str, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id", current_user.get("email"))
    doc = strategies_collection.find_one(
        {"id": strategy_id, "user_id": user_id}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Strategy not found")

    if "risk_management" in doc and isinstance(doc["risk_management"], dict):
        rm = doc["risk_management"]
        if "trailing_stop_loss" not in rm:
            rm["trailing_stop_loss"] = {"enabled": False, "type": "percentage", "value": 1.0, "activation_profit": 0}
        if "time_based_exit" not in rm:
            rm["time_based_exit"] = {"enabled": False, "exit_time": "15:10"}
        if "daily_limits" not in rm:
            rm["daily_limits"] = {"max_loss_per_day": 5.0, "max_trades_per_day": 10}
        if "position_sizing" not in rm:
            rm["position_sizing"] = {"method": "fixed_quantity", "value": 1}

    return {"success": True, "strategy": doc}


@router.put("/strategy/{strategy_id}")
async def update_strategy(request: Request, strategy_id: str, strategy: Strategy, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id", current_user.get("email"))
    existing = strategies_collection.find_one(
        {"id": strategy_id, "user_id": user_id}, {"_id": 0}
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Strategy not found")

    errors = validate_strategy(strategy)
    if errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))

    try:
        now = datetime.now(timezone.utc).isoformat()
        update_doc = strategy.model_dump()
        update_doc["metadata"]["updated_at"] = now
        update_doc["metadata"]["created_at"] = existing.get("metadata", {}).get("created_at", now)
        update_doc["user_id"] = user_id
        update_doc["id"] = strategy_id

        current_ver = float(existing.get("version", "1.0"))
        update_doc["version"] = str(current_ver + 0.1)

        strategies_collection.update_one(
            {"id": strategy_id, "user_id": user_id},
            {"$set": update_doc}
        )
        logger.info(f"Strategy updated: {strategy_id}")
        return {"success": True, "strategy": update_doc}
    except Exception as e:
        logger.error(f"Strategy update failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/strategy/{strategy_id}")
async def delete_strategy(request: Request, strategy_id: str, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id", current_user.get("email"))
    # Check if strategy exists and is deletable
    doc = strategies_collection.find_one({"id": strategy_id, "user_id": user_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Strategy not found or not owned by user")
    if doc.get("demo_tag"):
        raise HTTPException(status_code=403, detail="Demo seed strategies cannot be deleted")
    result = strategies_collection.delete_one({"id": strategy_id, "user_id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Strategy not found or not owned by user")
    logger.info(f"Strategy deleted: {strategy_id}")
    return {"success": True, "message": "Strategy deleted"}
