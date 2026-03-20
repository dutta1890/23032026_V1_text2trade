"""Screener endpoints."""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
import logging

from auth import get_current_user
from screener.engine import run_screener, SCREENER_PRESETS
from database import screener_analytics

logger = logging.getLogger(__name__)
router = APIRouter()


class ScreenerScanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    conditions: Optional[list] = None
    preset: Optional[str] = None
    timeframe: str = "1d"
    symbols: Optional[List[str]] = None


@router.post("/screener/scan")
async def screener_scan(request: Request, body: ScreenerScanRequest, current_user: dict = Depends(get_current_user)):
    if not body.conditions and not body.preset:
        raise HTTPException(status_code=400, detail="Provide 'conditions' or 'preset'")

    conditions = body.conditions
    if body.preset:
        preset = SCREENER_PRESETS.get(body.preset)
        if not preset:
            raise HTTPException(status_code=400, detail=f"Unknown preset: {body.preset}. Available: {list(SCREENER_PRESETS.keys())}")
        conditions = preset["conditions"]
        screener_analytics["preset_runs"][body.preset] = screener_analytics["preset_runs"].get(body.preset, 0) + 1

    result = run_screener(conditions, body.timeframe, body.symbols)

    for m in result.get("matches", []):
        sym = m["symbol"]
        screener_analytics["symbol_scans"][sym] = screener_analytics["symbol_scans"].get(sym, 0) + 1

    if body.preset:
        result["preset"] = body.preset
        result["preset_name"] = SCREENER_PRESETS[body.preset]["name"]
        result["preset_description"] = SCREENER_PRESETS[body.preset]["description"]

    return result


@router.get("/screener/presets")
async def list_screener_presets(request: Request):
    presets = []
    for key, val in SCREENER_PRESETS.items():
        presets.append({
            "id": key, "name": val["name"],
            "description": val["description"],
            "conditions_count": len(val["conditions"]),
        })
    return {"presets": presets, "count": len(presets)}
