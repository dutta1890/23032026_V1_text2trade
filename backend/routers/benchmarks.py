"""Benchmarks router — runs and serves benchmark test results."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from auth import get_current_user
from database import db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["benchmarks"])

benchmark_results = db["benchmark_results"]
STRATEGIES_PATH = Path(__file__).parent.parent / "tests" / "benchmarks" / "strategies.json"
AUDIT_PATH = Path(__file__).parent.parent / "tests" / "lookahead_audit.md"


@router.get("/benchmarks")
async def get_benchmarks():
    """Public endpoint: return latest benchmark results + audit status."""
    # Get latest stored run
    latest = benchmark_results.find_one(
        {}, {"_id": 0}, sort=[("run_at", -1)]
    )

    # Load strategy configs for display
    strategies = []
    if STRATEGIES_PATH.exists():
        with open(STRATEGIES_PATH) as f:
            strategies = json.load(f)

    # Check audit document status
    audit_exists = AUDIT_PATH.exists()
    audit_content = ""
    if audit_exists:
        audit_content = AUDIT_PATH.read_text()

    return {
        "latest_run": latest,
        "benchmark_count": len(strategies),
        "strategies": [
            {
                "id": s["id"],
                "name": s["name"],
                "description": s["description"],
                "category": s["category"],
                "symbol": s["symbol"],
            }
            for s in strategies
        ],
        "audit": {
            "exists": audit_exists,
            "verdict": "NO LOOKAHEAD BIAS DETECTED" if audit_exists else "NOT AUDITED",
            "content": audit_content if audit_exists else "",
        },
    }


@router.post("/admin/benchmarks/run")
async def run_benchmarks(current_user: dict = Depends(get_current_user)):
    """Admin-only: trigger a fresh benchmark run and store results."""
    if current_user.get("role") != "admin":
        raise HTTPException(403, "Admin only")

    # Import runner inline to avoid circular imports at module level
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "tests" / "benchmarks"))
    from run_benchmarks import run_all_benchmarks

    try:
        summary = run_all_benchmarks()
    except Exception as e:
        logger.error(f"Benchmark run failed: {e}")
        raise HTTPException(500, f"Benchmark run failed: {str(e)}")

    # Store in MongoDB
    benchmark_results.insert_one(summary)

    # Remove _id before returning
    summary.pop("_id", None)
    return summary


@router.get("/admin/benchmarks/history")
async def get_benchmark_history(current_user: dict = Depends(get_current_user)):
    """Admin-only: return last 10 benchmark runs."""
    if current_user.get("role") != "admin":
        raise HTTPException(403, "Admin only")

    runs = list(
        benchmark_results.find(
            {}, {"_id": 0}
        ).sort("run_at", -1).limit(10)
    )
    return {"runs": runs}
