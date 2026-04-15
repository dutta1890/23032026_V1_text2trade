"""Immutable audit trail for SEBI compliance — write-only, 5+ year retention."""

import uuid
import logging
from datetime import datetime, timezone
from database import db

logger = logging.getLogger(__name__)

audit_collection = db["audit_trail"]

# Indexes — NO TTL index (data retained 5+ years per SEBI)
try:
    audit_collection.create_index([("user_id", 1), ("timestamp", -1)])
    audit_collection.create_index([("action", 1), ("timestamp", -1)])
    audit_collection.create_index([("strategy_id", 1)], sparse=True)
    audit_collection.create_index([("request_id", 1)])
except Exception:
    pass


def log_audit(
    user_id: str,
    action: str,
    details: dict,
    ip_address: str = "unknown",
    user_agent: str = "unknown",
    request_id: str = "",
    session_id: str = None,
    strategy_id: str = None,
    algo_id: str = None,
):
    """Write a single immutable audit entry. Never raises — failures are logged."""
    entry = {
        "audit_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc),
        "user_id": user_id,
        "action": action,
        "details": details,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "session_id": session_id,
        "strategy_id": strategy_id,
        "algo_id": algo_id,
        "request_id": request_id,
    }
    try:
        audit_collection.insert_one(entry)
    except Exception as e:
        logger.error(f"Audit write failed: {e} | action={action} user={user_id}")


def get_request_meta(request) -> dict:
    """Extract IP and user-agent from a FastAPI Request."""
    ip = "unknown"
    ua = "unknown"
    try:
        ip = request.headers.get("x-forwarded-for", "")
        if ip:
            ip = ip.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"
        ua = request.headers.get("user-agent", "unknown")
    except Exception:
        pass
    return {"ip": ip, "ua": ua}
