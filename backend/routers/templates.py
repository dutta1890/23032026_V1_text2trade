"""Template endpoints."""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, ConfigDict
from datetime import datetime, timezone
from typing import Optional
import uuid
import logging

from auth import get_current_user
from database import strategies_collection, templates_collection, analytics_db

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/templates")
async def list_templates(request: Request):
    docs = list(templates_collection.find({}, {"_id": 0}).sort("category", 1))
    return {"templates": docs, "count": len(docs)}


@router.get("/template/{template_id}")
async def get_template(request: Request, template_id: str):
    doc = templates_collection.find_one({"template_id": template_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Template not found")
    return doc


class CloneTemplateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    symbol: Optional[str] = None
    timeframe: Optional[str] = None
    name: Optional[str] = None


@router.post("/template/{template_id}/clone")
async def clone_template(request: Request, template_id: str, body: CloneTemplateRequest = None, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id", current_user.get("email"))
    template = templates_collection.find_one({"template_id": template_id}, {"_id": 0})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    now = datetime.now(timezone.utc).isoformat()
    strategy_id = str(uuid.uuid4())
    symbol = (body.symbol.upper().strip() if body and body.symbol else template["instrument"]["symbol"])
    tf = (body.timeframe.strip() if body and body.timeframe else template["timeframe"]["interval"])
    custom_name = (body.name.strip() if body and body.name else None)

    strategy_doc = {
        "id": strategy_id, "user_id": user_id, "version": "1.0",
        "metadata": {
            "name": custom_name or f"{template['name']} - {symbol}",
            "description": template.get("description", ""),
            "tags": ["cloned", template.get("category", "").lower()],
            "created_at": now, "updated_at": now,
        },
        "market": template["market"],
        "instrument": {"symbol": symbol, "base": None, "quote": None},
        "timeframe": {"interval": tf, "candle_count": None},
        "entry_conditions": template["entry_conditions"],
        "exit_conditions": template["exit_conditions"],
        "filters": template.get("filters", []),
        "risk_management": template["risk_management"],
    }

    strategies_collection.insert_one(strategy_doc)
    strategy_doc.pop("_id", None)
    templates_collection.update_one({"template_id": template_id}, {"$inc": {"clone_count": 1}})
    analytics_db["strategies_created"] += 1
    logger.info(f"Template '{template['name']}' cloned by {user_id} -> strategy {strategy_id}")
    return {"success": True, "strategy_id": strategy_id, "strategy": strategy_doc}
