"""Compliance & Audit API endpoints."""

import csv
import io
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from auth import get_current_user, get_admin_user
from config import COMPLIANCE_STATUS, SEBI_COMPLIANCE
from audit import audit_collection, log_audit, get_request_meta
from monitoring import get_all_users_ops_summary
from database import db, strategies_collection

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["compliance"])


# ─── Public compliance status ────────────────────────────────────────────────

@router.get("/compliance/status")
async def compliance_status():
    """Public endpoint — returns SEBI compliance posture."""
    return COMPLIANCE_STATUS


# ─── Admin: Audit trail stats ────────────────────────────────────────────────

@router.get("/admin/compliance/audit-stats")
async def audit_stats(admin: dict = Depends(get_admin_user)):
    """Aggregate stats for the admin compliance dashboard."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total = audit_collection.count_documents({})
    today = audit_collection.count_documents({"timestamp": {"$gte": today_start}})
    this_month = audit_collection.count_documents({"timestamp": {"$gte": month_start}})

    oldest = audit_collection.find_one({}, {"_id": 0, "timestamp": 1}, sort=[("timestamp", 1)])
    oldest_date = oldest["timestamp"].isoformat() if oldest else None

    # Action breakdown (top 10)
    action_pipeline = [
        {"$group": {"_id": "$action", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10},
        {"$project": {"_id": 0, "action": "$_id", "count": 1}},
    ]
    action_breakdown = list(audit_collection.aggregate(action_pipeline))

    return {
        "total_entries": total,
        "entries_today": today,
        "entries_this_month": this_month,
        "oldest_entry": oldest_date,
        "retention_years": SEBI_COMPLIANCE["audit_retention_years"],
        "action_breakdown": action_breakdown,
    }


# ─── Admin: Audit trail query ────────────────────────────────────────────────

@router.get("/admin/compliance/audit-trail")
async def query_audit_trail(
    admin: dict = Depends(get_admin_user),
    user_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    strategy_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
):
    """Query audit trail with filters. No delete/update — read only."""
    query = {}
    if user_id:
        query["user_id"] = user_id
    if action:
        query["action"] = action
    if strategy_id:
        query["strategy_id"] = strategy_id
    if start_date or end_date:
        ts_query = {}
        if start_date:
            ts_query["$gte"] = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        if end_date:
            ts_query["$lte"] = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        if ts_query:
            query["timestamp"] = ts_query

    skip = (page - 1) * limit
    total = audit_collection.count_documents(query)
    entries = list(
        audit_collection.find(query, {"_id": 0})
        .sort("timestamp", -1)
        .skip(skip)
        .limit(limit)
    )
    # Convert datetime objects to ISO strings for JSON
    for e in entries:
        if isinstance(e.get("timestamp"), datetime):
            e["timestamp"] = e["timestamp"].isoformat()

    return {
        "entries": entries,
        "total": total,
        "page": page,
        "pages": max(1, (total + limit - 1) // limit),
    }


# ─── Admin: Export audit trail CSV ────────────────────────────────────────────

@router.get("/admin/compliance/audit-export")
async def export_audit_csv(
    admin: dict = Depends(get_admin_user),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
):
    """Export audit trail as CSV for regulatory reporting."""
    query = {}
    if start_date or end_date:
        ts_query = {}
        if start_date:
            ts_query["$gte"] = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        if end_date:
            ts_query["$lte"] = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        if ts_query:
            query["timestamp"] = ts_query

    cursor = audit_collection.find(query, {"_id": 0}).sort("timestamp", -1).limit(10000)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "audit_id", "timestamp", "user_id", "action", "details",
        "ip_address", "user_agent", "session_id", "strategy_id",
        "algo_id", "request_id",
    ])
    for e in cursor:
        ts = e.get("timestamp")
        if isinstance(ts, datetime):
            ts = ts.isoformat()
        writer.writerow([
            e.get("audit_id", ""),
            ts or "",
            e.get("user_id", ""),
            e.get("action", ""),
            str(e.get("details", {})),
            e.get("ip_address", ""),
            e.get("user_agent", ""),
            e.get("session_id", ""),
            e.get("strategy_id", ""),
            e.get("algo_id", ""),
            e.get("request_id", ""),
        ])

    output.seek(0)
    filename = f"audit_trail_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ─── Admin: OPS monitoring ───────────────────────────────────────────────────

@router.get("/admin/compliance/ops")
async def ops_monitoring(admin: dict = Depends(get_admin_user)):
    """Show users approaching OPS threshold."""
    users = get_all_users_ops_summary()
    return {
        "threshold": SEBI_COMPLIANCE["ops_threshold"],
        "users": users,
        "total_active_users": len(users),
    }


# ─── Admin: Strategy classification breakdown ────────────────────────────────

@router.get("/admin/compliance/strategy-classification")
async def strategy_classification(admin: dict = Depends(get_admin_user)):
    """Breakdown of white-box vs black-box strategies."""
    total = strategies_collection.count_documents({})
    white_box = strategies_collection.count_documents({"classification": {"$ne": "black_box"}})
    black_box = strategies_collection.count_documents({"classification": "black_box"})
    return {
        "total": total,
        "white_box": white_box,
        "black_box": black_box,
    }
