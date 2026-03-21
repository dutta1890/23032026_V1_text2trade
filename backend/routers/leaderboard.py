"""Leaderboard / Most Cloned template endpoints."""
from fastapi import APIRouter, Request
import logging

from database import templates_collection

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/templates/leaderboard")
async def template_leaderboard(request: Request):
    """Public — top templates by clone count."""
    docs = list(templates_collection.find(
        {}, {"_id": 0, "template_id": 1, "name": 1, "category": 1,
             "description": 1, "clone_count": 1, "instrument": 1}
    ).sort("clone_count", -1).limit(10))
    return {"leaderboard": docs, "count": len(docs)}
