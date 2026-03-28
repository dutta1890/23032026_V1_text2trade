"""Knowledge base API — trading term glossary with tooltips."""
import logging
from typing import Optional, Literal
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from database import db
from auth import get_admin_user

logger = logging.getLogger(__name__)
router = APIRouter(tags=["knowledge"])

knowledge_col = db["knowledge_base"]

try:
    knowledge_col.create_index("term_id", unique=True)
    knowledge_col.create_index("category")
except Exception:
    pass


class KnowledgeEntry(BaseModel):
    term_id: str
    term: str
    category: Literal["indicator", "risk_management", "order_type", "general", "strategy_concept"]
    short_description: str
    example: str
    learn_more_url: Optional[str] = None


# ── Public endpoints ─────────────────────────────────────────────────────────

@router.get("/api/v1/knowledge")
async def get_all_terms():
    docs = list(knowledge_col.find({}, {"_id": 0}).sort("term_id", 1))
    return {"entries": docs, "total": len(docs)}


@router.get("/api/v1/knowledge/{term_id}")
async def get_term(term_id: str):
    doc = knowledge_col.find_one({"term_id": term_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail=f"Term '{term_id}' not found")
    return doc


@router.get("/api/v1/knowledge/category/{category}")
async def get_by_category(category: str):
    docs = list(knowledge_col.find({"category": category}, {"_id": 0}).sort("term_id", 1))
    return {"entries": docs, "total": len(docs)}


# ── Admin CRUD ───────────────────────────────────────────────────────────────

@router.post("/api/v1/admin/knowledge")
async def add_term(request: Request, body: KnowledgeEntry, admin: dict = Depends(get_admin_user)):
    if knowledge_col.find_one({"term_id": body.term_id}):
        raise HTTPException(status_code=409, detail="Term already exists")
    knowledge_col.insert_one(body.model_dump())
    return {"success": True, "term_id": body.term_id}


@router.put("/api/v1/admin/knowledge/{term_id}")
async def update_term(request: Request, term_id: str, body: KnowledgeEntry, admin: dict = Depends(get_admin_user)):
    result = knowledge_col.replace_one({"term_id": term_id}, body.model_dump())
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Term not found")
    return {"success": True}


@router.delete("/api/v1/admin/knowledge/{term_id}")
async def delete_term(request: Request, term_id: str, admin: dict = Depends(get_admin_user)):
    result = knowledge_col.delete_one({"term_id": term_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Term not found")
    return {"success": True}
