"""Legal documents and user consent tracking API."""
import os
import logging
from datetime import datetime, timezone
from typing import Optional, Literal
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from auth import get_current_user, get_admin_user
from database import db

logger = logging.getLogger(__name__)
router = APIRouter(tags=["legal"])

LEGAL_DIR = Path(__file__).parent.parent / "legal"
legal_docs = db["legal_documents"]
user_consents = db["user_consents"]

DOC_TYPES = ("terms", "privacy", "disclaimer", "cookies")

# Index for fast lookups
try:
    legal_docs.create_index([("type", 1), ("version", 1)], unique=True)
    user_consents.create_index([("user_id", 1), ("document_type", 1)])
except Exception:
    pass

# ── Seed documents from markdown files on startup ────────────────────────────
FILE_MAP = {
    "terms": "terms_of_service.md",
    "privacy": "privacy_policy.md",
    "disclaimer": "risk_disclaimer.md",
    "cookies": "cookie_policy.md",
}


def seed_legal_documents():
    """Load markdown files into MongoDB if no version exists yet."""
    for doc_type, filename in FILE_MAP.items():
        if legal_docs.find_one({"type": doc_type}):
            continue
        filepath = LEGAL_DIR / filename
        if not filepath.exists():
            logger.warning(f"Legal file not found: {filepath}")
            continue
        content = filepath.read_text()
        legal_docs.insert_one({
            "type": doc_type,
            "version": "1.0",
            "content_md": content,
            "effective_date": datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_by": "system",
        })
        logger.info(f"Seeded legal document: {doc_type} v1.0")


seed_legal_documents()


# ── Helpers ──────────────────────────────────────────────────────────────────
def get_latest_doc(doc_type: str) -> Optional[dict]:
    """Get the latest version of a legal document (by creation time)."""
    doc = legal_docs.find_one(
        {"type": doc_type},
        {"_id": 0},
        sort=[("created_at", -1)],
    )
    return doc


def get_latest_versions() -> dict:
    """Return dict of {doc_type: latest_version}."""
    result = {}
    for dtype in DOC_TYPES:
        doc = get_latest_doc(dtype)
        if doc:
            result[dtype] = doc["version"]
    return result


def check_user_consents(user_id: str) -> dict:
    """Check which documents the user needs to accept."""
    latest = get_latest_versions()
    pending = {}
    for dtype, version in latest.items():
        if dtype == "cookies":
            continue  # Cookies consent not mandatory for app access
        consent = user_consents.find_one(
            {"user_id": user_id, "document_type": dtype, "document_version": version},
            {"_id": 0},
        )
        if not consent:
            pending[dtype] = version
    return pending


# ── Models ───────────────────────────────────────────────────────────────────
class AcceptConsentRequest(BaseModel):
    document_type: str
    document_version: str


class UpdateLegalDocRequest(BaseModel):
    content_md: str
    version: str


# ── Public endpoints (no auth required) ──────────────────────────────────────

@router.get("/api/v1/legal/terms")
async def get_terms():
    doc = get_latest_doc("terms")
    if not doc:
        raise HTTPException(status_code=404, detail="Terms of Service not found")
    return doc


@router.get("/api/v1/legal/privacy")
async def get_privacy():
    doc = get_latest_doc("privacy")
    if not doc:
        raise HTTPException(status_code=404, detail="Privacy Policy not found")
    return doc


@router.get("/api/v1/legal/disclaimer")
async def get_disclaimer():
    doc = get_latest_doc("disclaimer")
    if not doc:
        raise HTTPException(status_code=404, detail="Risk Disclaimer not found")
    return doc


@router.get("/api/v1/legal/cookies")
async def get_cookies():
    doc = get_latest_doc("cookies")
    if not doc:
        raise HTTPException(status_code=404, detail="Cookie Policy not found")
    return doc


@router.get("/api/v1/legal/versions")
async def get_legal_versions():
    """Return latest versions of all legal documents."""
    return get_latest_versions()


# ── Consent endpoints ────────────────────────────────────────────────────────

@router.get("/api/v1/legal/consent-status")
async def consent_status(request: Request, user: dict = Depends(get_current_user)):
    """Check if user has accepted all latest legal docs."""
    pending = check_user_consents(user["user_id"])
    return {
        "all_accepted": len(pending) == 0,
        "pending": pending,
    }


@router.post("/api/v1/legal/accept")
async def accept_document(request: Request, body: AcceptConsentRequest, user: dict = Depends(get_current_user)):
    """Accept a specific legal document version."""
    if body.document_type not in DOC_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid document type: {body.document_type}")

    doc = legal_docs.find_one({"type": body.document_type, "version": body.document_version})
    if not doc:
        raise HTTPException(status_code=404, detail="Document version not found")

    # Get IP address
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")

    # Upsert — don't create duplicates for same user+type+version
    existing = user_consents.find_one({
        "user_id": user["user_id"],
        "document_type": body.document_type,
        "document_version": body.document_version,
    })
    if existing:
        return {"success": True, "message": "Already accepted"}

    user_consents.insert_one({
        "user_id": user["user_id"],
        "document_type": body.document_type,
        "document_version": body.document_version,
        "accepted_at": datetime.now(timezone.utc).isoformat(),
        "ip_address": ip,
    })

    logger.info(f"[CONSENT] user={user['user_id']} accepted {body.document_type} v{body.document_version}")
    return {"success": True, "message": f"Accepted {body.document_type} v{body.document_version}"}


# ── Admin: update legal documents ────────────────────────────────────────────

@router.put("/api/v1/admin/legal/{doc_type}")
async def update_legal_document(
    request: Request, doc_type: str, body: UpdateLegalDocRequest,
    admin: dict = Depends(get_admin_user),
):
    """Create a new version of a legal document (preserves old versions)."""
    if doc_type not in DOC_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid document type: {doc_type}")

    # Check if version already exists
    existing = legal_docs.find_one({"type": doc_type, "version": body.version})
    if existing:
        raise HTTPException(status_code=409, detail=f"Version {body.version} already exists for {doc_type}")

    legal_docs.insert_one({
        "type": doc_type,
        "version": body.version,
        "content_md": body.content_md,
        "effective_date": datetime.now(timezone.utc).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": admin.get("email", "admin"),
    })

    logger.info(f"[LEGAL] Admin {admin['email']} created {doc_type} v{body.version}")
    return {"success": True, "message": f"Created {doc_type} v{body.version}"}
