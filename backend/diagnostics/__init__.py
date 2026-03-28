"""Diagnostics error tracker — captures unhandled exceptions & frontend crashes."""
import uuid
import traceback
import logging
from datetime import datetime, timezone
from typing import Optional, Literal
from pydantic import BaseModel, Field

from database import db

logger = logging.getLogger(__name__)

# ── Collections ──────────────────────────────────────────────────────────────
error_logs = db["error_logs"]
performance_logs = db["performance_logs"]

# ── TTL Indexes ──────────────────────────────────────────────────────────────
try:
    error_logs.create_index("timestamp", expireAfterSeconds=90 * 86400)  # 90 days
    error_logs.create_index("severity")
    error_logs.create_index("source")
    error_logs.create_index("user_id")
    error_logs.create_index("resolved")
except Exception:
    pass

try:
    performance_logs.create_index("timestamp", expireAfterSeconds=30 * 86400)  # 30 days
    performance_logs.create_index("endpoint")
except Exception:
    pass

# ── Sensitive field sanitization ─────────────────────────────────────────────
SENSITIVE_KEYS = {"password", "current_password", "new_password", "confirm_password",
                  "token", "access_token", "refresh_token", "api_key", "secret",
                  "authorization", "otp", "password_hash"}


def sanitize_dict(data: dict) -> dict:
    """Strip passwords, tokens, and secrets from a dict (shallow + nested)."""
    if not isinstance(data, dict):
        return data
    cleaned = {}
    for k, v in data.items():
        if k.lower() in SENSITIVE_KEYS:
            cleaned[k] = "***REDACTED***"
        elif isinstance(v, dict):
            cleaned[k] = sanitize_dict(v)
        else:
            cleaned[k] = v
    return cleaned


# ── Severity mapping ─────────────────────────────────────────────────────────
SEVERITY_MAP = {
    "TimeoutError": "medium",
    "asyncio.TimeoutError": "medium",
    "ValidationError": "low",
    "RequestValidationError": "low",
    "ValueError": "low",
    "TypeError": "low",
    "KeyError": "medium",
    "ServerSelectionTimeoutError": "high",
    "ConnectionFailure": "high",
    "OperationFailure": "high",
    "pymongo.errors.ServerSelectionTimeoutError": "high",
}


def classify_severity(error_type: str) -> str:
    return SEVERITY_MAP.get(error_type, "critical")


# ── Models ───────────────────────────────────────────────────────────────────
class ErrorRecord(BaseModel):
    error_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    user_id: Optional[str] = None
    endpoint: str = ""
    method: str = ""
    request_body: Optional[dict] = None
    error_type: str = ""
    error_message: str = ""
    stack_trace: str = ""
    request_id: str = ""
    severity: Literal["low", "medium", "high", "critical"] = "critical"
    source: Literal["backend", "frontend"] = "backend"
    resolved: bool = False
    resolve_note: Optional[str] = None
    resolved_at: Optional[str] = None
    resolved_by: Optional[str] = None


class FrontendCrashReport(BaseModel):
    error_message: str
    component_stack: Optional[str] = None
    page_url: Optional[str] = None
    browser_info: Optional[str] = None
    user_id: Optional[str] = None
    timestamp: Optional[str] = None


# ── Core functions ───────────────────────────────────────────────────────────
def store_error(record: ErrorRecord) -> str:
    """Persist an error record to MongoDB. Returns error_id."""
    doc = record.model_dump()
    error_logs.insert_one(doc)
    doc.pop("_id", None)
    logger.warning(f"[DIAG] Error stored: {record.error_id} severity={record.severity} type={record.error_type}")
    return record.error_id


def store_frontend_crash(report: FrontendCrashReport) -> str:
    """Convert a frontend crash report into an ErrorRecord and store it."""
    record = ErrorRecord(
        user_id=report.user_id,
        endpoint=report.page_url or "unknown",
        method="RENDER",
        error_type="ReactCrash",
        error_message=report.error_message,
        stack_trace=report.component_stack or "",
        request_id="",
        severity="high",
        source="frontend",
    )
    if report.timestamp:
        record.timestamp = report.timestamp
    if report.browser_info:
        record.request_body = {"browser_info": report.browser_info}
    return store_error(record)


def store_slow_request(endpoint: str, method: str, duration_ms: float,
                       user_id: Optional[str], request_id: str):
    """Log a slow request to performance_logs."""
    doc = {
        "endpoint": endpoint,
        "method": method,
        "duration_ms": round(duration_ms, 2),
        "user_id": user_id,
        "request_id": request_id,
        "timestamp": datetime.now(timezone.utc),
    }
    performance_logs.insert_one(doc)
    logger.warning(f"[DIAG] Slow request: {method} {endpoint} {duration_ms:.0f}ms")
