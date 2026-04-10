"""Shared consent utilities — breaks circular dependency between auth.py and routers/legal.py."""
from datetime import datetime, timezone
from database import db

user_consents = db["user_consents"]
legal_docs = db["legal_documents"]

DOC_TYPES = ("terms", "privacy", "disclaimer", "cookies")


def get_latest_versions() -> dict:
    """Return dict of {doc_type: latest_version}."""
    result = {}
    for dtype in DOC_TYPES:
        doc = legal_docs.find_one(
            {"type": dtype},
            {"_id": 0, "version": 1},
            sort=[("created_at", -1)],
        )
        if doc:
            result[dtype] = doc["version"]
    return result


def record_registration_consents(user_id: str, ip_address: str, consent_time: str):
    """Store consent records at registration time."""
    versions = get_latest_versions()
    for dtype in ("terms", "privacy", "disclaimer"):
        ver = versions.get(dtype, "1.0")
        user_consents.insert_one({
            "user_id": user_id,
            "document_type": dtype,
            "document_version": ver,
            "accepted_at": consent_time,
            "ip_address": ip_address,
        })
