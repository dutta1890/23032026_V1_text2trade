"""Admin-only endpoints."""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
import os
import logging

from auth import get_admin_user, users_collection
from database import (
    db, strategies_collection, templates_collection,
    analytics_db, screener_analytics
)
from data.service import get_data_status

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/data/status")
async def admin_data_status(request: Request, admin: dict = Depends(get_admin_user)):
    try:
        return get_data_status()
    except Exception as e:
        logger.error(f"Data status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/data/refresh")
async def admin_data_refresh(request: Request, admin: dict = Depends(get_admin_user)):
    import subprocess, sys
    try:
        script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts", "refresh_data.py")
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True, text=True, timeout=600,
            cwd=os.path.dirname(os.path.dirname(__file__)),
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout[-2000:] if result.stdout else "",
            "stderr": result.stderr[-500:] if result.stderr else "",
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Refresh timed out (10 min limit)"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users")
async def admin_list_users(request: Request, admin: dict = Depends(get_admin_user)):
    users = list(users_collection.find({}, {"_id": 0, "password_hash": 0}))
    for u in users:
        email = u.get("email", "")
        u["strategy_count"] = strategies_collection.count_documents({"user_id": email})
    return {"users": users, "total": len(users)}


@router.get("/analytics")
async def admin_analytics(request: Request, admin: dict = Depends(get_admin_user)):
    from data.service import market_data_collection
    return {
        "users": {"total": users_collection.count_documents({}), "admins": users_collection.count_documents({"role": "admin"})},
        "strategies": {"total": strategies_collection.count_documents({})},
        "market_data": {
            "total_candles": market_data_collection.count_documents({}),
            "symbols": len(market_data_collection.distinct("symbol")),
            "timeframes": market_data_collection.distinct("timeframe"),
        },
        "usage": analytics_db,
    }


# --- Admin template management ---

class AdminTemplateCreate(BaseModel):
    name: str = Field(max_length=100)
    description: str = Field(max_length=500)
    category: str = Field(max_length=50)
    instrument: dict
    timeframe: dict
    entry_conditions: list
    exit_conditions: list = Field(default_factory=list)
    filters: list = Field(default_factory=list)
    risk_management: dict


@router.post("/templates")
async def admin_create_template(request: Request, body: AdminTemplateCreate, admin: dict = Depends(get_admin_user)):
    import uuid
    from datetime import datetime, timezone
    template_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "template_id": template_id, "name": body.name,
        "description": body.description, "category": body.category,
        "market": {"type": "equity", "exchange": "NSE"},
        "instrument": body.instrument, "timeframe": body.timeframe,
        "entry_conditions": body.entry_conditions,
        "exit_conditions": body.exit_conditions,
        "filters": body.filters, "risk_management": body.risk_management,
        "clone_count": 0, "created_at": now, "updated_at": now,
    }
    templates_collection.insert_one(doc)
    doc.pop("_id", None)
    logger.info(f"Admin created template: {template_id}")
    return {"success": True, "template": doc}


@router.put("/templates/{template_id}")
async def admin_update_template(request: Request, template_id: str, body: AdminTemplateCreate, admin: dict = Depends(get_admin_user)):
    from datetime import datetime, timezone
    existing = templates_collection.find_one({"template_id": template_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Template not found")
    now = datetime.now(timezone.utc).isoformat()
    update_fields = {
        "name": body.name, "description": body.description,
        "category": body.category, "instrument": body.instrument,
        "timeframe": body.timeframe, "entry_conditions": body.entry_conditions,
        "exit_conditions": body.exit_conditions, "filters": body.filters,
        "risk_management": body.risk_management, "updated_at": now,
    }
    templates_collection.update_one({"template_id": template_id}, {"$set": update_fields})
    logger.info(f"Admin updated template: {template_id}")
    return {"success": True, "template": {**existing, **update_fields}}


@router.delete("/templates/{template_id}")
async def admin_delete_template(request: Request, template_id: str, admin: dict = Depends(get_admin_user)):
    result = templates_collection.delete_one({"template_id": template_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")
    logger.info(f"Admin deleted template: {template_id}")
    return {"success": True, "message": f"Template {template_id} deleted"}


@router.get("/screener/stats")
async def admin_screener_stats(request: Request, admin: dict = Depends(get_admin_user)):
    preset_runs = screener_analytics.get("preset_runs", {})
    symbol_scans = screener_analytics.get("symbol_scans", {})
    top_presets = sorted(preset_runs.items(), key=lambda x: x[1], reverse=True)
    top_symbols = sorted(symbol_scans.items(), key=lambda x: x[1], reverse=True)
    return {
        "most_run_presets": [{"preset": k, "count": v} for k, v in top_presets],
        "most_scanned_symbols": [{"symbol": k, "match_count": v} for k, v in top_symbols[:20]],
        "total_preset_runs": sum(preset_runs.values()),
        "total_symbol_matches": sum(symbol_scans.values()),
    }
