"""Diagnostics API router — admin error logs, performance, and frontend crash reports."""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel

from auth import get_admin_user, get_current_user
from diagnostics import (
    error_logs, performance_logs,
    FrontendCrashReport, store_frontend_crash,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["diagnostics"])

SLOW_THRESHOLD_MS = 3000

# ── Frontend crash report (rate-limited in server.py) ────────────────────────

@router.post("/diagnostics/frontend-crash")
async def report_frontend_crash(request: Request, body: FrontendCrashReport):
    error_id = store_frontend_crash(body)
    return {"success": True, "error_id": error_id}


# ── Admin: error summary ─────────────────────────────────────────────────────

@router.get("/admin/diagnostics/summary")
async def diagnostics_summary(request: Request, admin: dict = Depends(get_admin_user)):
    now = datetime.now(timezone.utc)
    h24 = now - timedelta(hours=24)
    d7 = now - timedelta(days=7)
    h24_iso = h24.isoformat()
    d7_iso = d7.isoformat()

    # Last 24h counts by severity
    pipeline_24h = [
        {"$match": {"timestamp": {"$gte": h24_iso}}},
        {"$group": {"_id": "$severity", "count": {"$sum": 1}}},
    ]
    sev_24h = {r["_id"]: r["count"] for r in error_logs.aggregate(pipeline_24h)}
    total_24h = sum(sev_24h.values())

    # Last 7d counts by severity
    pipeline_7d = [
        {"$match": {"timestamp": {"$gte": d7_iso}}},
        {"$group": {"_id": "$severity", "count": {"$sum": 1}}},
    ]
    sev_7d = {r["_id"]: r["count"] for r in error_logs.aggregate(pipeline_7d)}
    total_7d = sum(sev_7d.values())

    # Top error types (last 7d)
    pipeline_top = [
        {"$match": {"timestamp": {"$gte": d7_iso}}},
        {"$group": {"_id": "$error_type", "count": {"$sum": 1}, "last_seen": {"$max": "$timestamp"}}},
        {"$sort": {"count": -1}},
        {"$limit": 10},
    ]
    top_errors = [{"error_type": r["_id"], "count": r["count"], "last_seen": r["last_seen"]}
                  for r in error_logs.aggregate(pipeline_top)]

    # Affected users 24h
    affected_24h = len(error_logs.distinct("user_id", {"timestamp": {"$gte": h24_iso}, "user_id": {"$ne": None}}))

    # Hourly error rate (last 24h) — bucket by hour string
    pipeline_hourly = [
        {"$match": {"timestamp": {"$gte": h24_iso}}},
        {"$addFields": {"hour": {"$substr": ["$timestamp", 11, 2]}}},
        {"$group": {"_id": "$hour", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]
    hourly = [{"hour": f"{r['_id']}:00", "count": r["count"]} for r in error_logs.aggregate(pipeline_hourly)]

    # Avg response time from perf logs last 24h
    avg_pipeline = [
        {"$match": {"timestamp": {"$gte": h24}}},
        {"$group": {"_id": None, "avg_ms": {"$avg": "$duration_ms"}}},
    ]
    avg_res = list(performance_logs.aggregate(avg_pipeline))
    avg_response_ms = round(avg_res[0]["avg_ms"], 1) if avg_res else 0

    return {
        "last_24h": {
            "total": total_24h,
            "critical": sev_24h.get("critical", 0),
            "high": sev_24h.get("high", 0),
            "medium": sev_24h.get("medium", 0),
            "low": sev_24h.get("low", 0),
        },
        "last_7d": {
            "total": total_7d,
            "critical": sev_7d.get("critical", 0),
            "high": sev_7d.get("high", 0),
            "medium": sev_7d.get("medium", 0),
            "low": sev_7d.get("low", 0),
        },
        "top_errors": top_errors,
        "affected_users_24h": affected_24h,
        "error_rate_per_hour": hourly,
        "avg_response_time_ms": avg_response_ms,
    }


# ── Admin: paginated error log ───────────────────────────────────────────────

@router.get("/admin/diagnostics/errors")
async def list_errors(
    request: Request,
    admin: dict = Depends(get_admin_user),
    severity: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    resolved: Optional[bool] = Query(None),
    user_id: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    sort_by: str = Query("timestamp"),
    order: str = Query("desc"),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
):
    query = {}
    if severity:
        query["severity"] = severity
    if source:
        query["source"] = source
    if resolved is not None:
        query["resolved"] = resolved
    if user_id:
        query["user_id"] = user_id
    if date_from or date_to:
        ts_q = {}
        if date_from:
            ts_q["$gte"] = date_from
        if date_to:
            ts_q["$lte"] = date_to
        query["timestamp"] = ts_q

    sort_dir = -1 if order == "desc" else 1
    sort_field = sort_by if sort_by in ("timestamp", "severity") else "timestamp"

    total = error_logs.count_documents(query)
    skip = (page - 1) * limit
    docs = list(
        error_logs.find(query, {"_id": 0})
        .sort(sort_field, sort_dir)
        .skip(skip)
        .limit(limit)
    )

    return {"errors": docs, "total": total, "page": page, "limit": limit}


# ── Admin: single error detail ───────────────────────────────────────────────

@router.get("/admin/diagnostics/errors/{error_id}")
async def get_error_detail(request: Request, error_id: str, admin: dict = Depends(get_admin_user)):
    doc = error_logs.find_one({"error_id": error_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Error not found")
    return doc


# ── Admin: resolve error ─────────────────────────────────────────────────────

class ResolveNote(BaseModel):
    note: Optional[str] = None

@router.put("/admin/diagnostics/errors/{error_id}/resolve")
async def resolve_error(request: Request, error_id: str, body: ResolveNote, admin: dict = Depends(get_admin_user)):
    result = error_logs.update_one(
        {"error_id": error_id},
        {"$set": {
            "resolved": True,
            "resolve_note": body.note or "",
            "resolved_at": datetime.now(timezone.utc).isoformat(),
            "resolved_by": admin.get("email", "admin"),
        }},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Error not found")
    return {"success": True, "message": "Error marked as resolved"}


# ── Admin: performance metrics ───────────────────────────────────────────────

@router.get("/admin/diagnostics/performance")
async def performance_metrics(request: Request, admin: dict = Depends(get_admin_user)):
    now = datetime.now(timezone.utc)
    h24 = now - timedelta(hours=24)

    # Average response time per endpoint (last 24h)
    avg_pipeline = [
        {"$match": {"timestamp": {"$gte": h24}}},
        {"$group": {
            "_id": {"endpoint": "$endpoint", "method": "$method"},
            "avg_ms": {"$avg": "$duration_ms"},
            "max_ms": {"$max": "$duration_ms"},
            "count": {"$sum": 1},
        }},
        {"$sort": {"avg_ms": -1}},
    ]
    avg_by_endpoint = [
        {
            "endpoint": r["_id"]["endpoint"],
            "method": r["_id"]["method"],
            "avg_ms": round(r["avg_ms"], 1),
            "max_ms": round(r["max_ms"], 1),
            "count": r["count"],
        }
        for r in performance_logs.aggregate(avg_pipeline)
    ]

    # Slowest individual requests
    slowest = list(
        performance_logs.find({"timestamp": {"$gte": h24}}, {"_id": 0})
        .sort("duration_ms", -1)
        .limit(10)
    )
    for s in slowest:
        if "timestamp" in s and hasattr(s["timestamp"], "isoformat"):
            s["timestamp"] = s["timestamp"].isoformat()

    # P95 response times per endpoint
    p95_pipeline = [
        {"$match": {"timestamp": {"$gte": h24}}},
        {"$group": {
            "_id": "$endpoint",
            "durations": {"$push": "$duration_ms"},
        }},
    ]
    p95_data = []
    for r in performance_logs.aggregate(p95_pipeline):
        durs = sorted(r["durations"])
        idx = int(len(durs) * 0.95)
        p95_data.append({
            "endpoint": r["_id"],
            "p95_ms": round(durs[min(idx, len(durs) - 1)], 1) if durs else 0,
            "sample_count": len(durs),
        })
    p95_data.sort(key=lambda x: x["p95_ms"], reverse=True)

    return {
        "avg_by_endpoint": avg_by_endpoint,
        "slowest_requests": slowest,
        "p95_by_endpoint": p95_data,
    }
