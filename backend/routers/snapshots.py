"""Backtest snapshots, strategy versions, verify-export, and comparison endpoints."""

import csv
import io
import json
import logging
import os
import uuid
import zipfile
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from auth import get_current_user, get_optional_user
from database import db, strategies_collection

logger = logging.getLogger(__name__)
router = APIRouter()

backtest_snapshots = db["backtest_snapshots"]
strategy_versions = db["strategy_versions"]

# Indexes
try:
    backtest_snapshots.create_index("snapshot_id", unique=True)
    backtest_snapshots.create_index("user_id")
    backtest_snapshots.create_index("strategy_id")
    strategy_versions.create_index([("strategy_id", 1), ("version", 1)], unique=True)
except Exception as e:
    logger.warning(f"Could not create snapshot/version indexes: {e}")

ENGINE_VERSION = os.environ.get("APP_VERSION", "0.2.0")


# ── Helpers ──────────────────────────────────────────────────────────────────

def create_snapshot(
    user_id: str,
    strategy_id: Optional[str],
    strategy_json: dict,
    strategy_version: int,
    symbol: str,
    timeframe: str,
    result: dict,
) -> str:
    """Create an immutable backtest snapshot. Returns snapshot_id."""
    snapshot_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    doc = {
        "snapshot_id": snapshot_id,
        "user_id": user_id,
        "strategy_id": strategy_id or "",
        "strategy_version": strategy_version,
        "strategy_json_snapshot": strategy_json,
        "symbol": symbol,
        "timeframe": timeframe,
        "start_date": result.get("data_start"),
        "end_date": result.get("data_end"),
        "engine_version": result.get("engine_version", ENGINE_VERSION),
        "data_snapshot_hash": result.get("data_snapshot_hash", ""),
        "results": {
            "metrics": result.get("metrics", {}),
            "costs": result.get("costs", {}),
            "warnings": result.get("warnings", []),
            "candles_processed": result.get("candles_processed", 0),
        },
        "trades": result.get("trades", []),
        "equity_curve": result.get("equity_curve", []),
        "created_at": now,
        "is_immutable": True,
    }
    backtest_snapshots.insert_one(doc)
    return snapshot_id


def save_strategy_version(strategy_id: str, user_id: str, old_doc: dict, changed_fields: list):
    """Save a strategy version snapshot before an update."""
    current_ver = old_doc.get("strategy_version", 1)
    strategy_versions.insert_one({
        "strategy_id": strategy_id,
        "version": current_ver,
        "json_snapshot": {
            k: v for k, v in old_doc.items()
            if k not in ("_id", "user_id")
        },
        "changed_fields": changed_fields,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": user_id,
    })


# ── Public snapshot endpoint ─────────────────────────────────────────────────

@router.get("/backtest/snapshot/{snapshot_id}")
async def get_snapshot(snapshot_id: str):
    """Public: retrieve an immutable backtest snapshot by ID."""
    doc = backtest_snapshots.find_one(
        {"snapshot_id": snapshot_id}, {"_id": 0, "user_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Backtest snapshot not found")
    return doc


# ── User's snapshot list ─────────────────────────────────────────────────────

@router.get("/backtest/snapshots")
async def list_snapshots(
    strategy_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """List user's backtest snapshots, optionally filtered by strategy."""
    user_id = current_user.get("user_id", current_user.get("email"))
    query = {"user_id": user_id}
    if strategy_id:
        query["strategy_id"] = strategy_id
    docs = list(
        backtest_snapshots.find(query, {"_id": 0, "user_id": 0, "trades": 0, "equity_curve": 0})
        .sort("created_at", -1)
        .limit(50)
    )
    return {"snapshots": docs, "count": len(docs)}


# ── Verify / export as ZIP ───────────────────────────────────────────────────

@router.get("/backtest/snapshot/{snapshot_id}/verify")
async def verify_export(snapshot_id: str):
    """Download a ZIP file containing everything needed to reproduce this backtest."""
    doc = backtest_snapshots.find_one(
        {"snapshot_id": snapshot_id}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Backtest snapshot not found")

    # Build ZIP in memory
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1) strategy.json
        strat = doc.get("strategy_json_snapshot", {})
        zf.writestr("strategy.json", json.dumps(strat, indent=2, default=str))

        # 2) backtest_params.json
        params = {
            "snapshot_id": doc["snapshot_id"],
            "symbol": doc["symbol"],
            "timeframe": doc["timeframe"],
            "start_date": doc.get("start_date"),
            "end_date": doc.get("end_date"),
            "engine_version": doc.get("engine_version"),
            "data_snapshot_hash": doc.get("data_snapshot_hash"),
            "strategy_version": doc.get("strategy_version"),
            "created_at": doc.get("created_at"),
        }
        zf.writestr("backtest_params.json", json.dumps(params, indent=2, default=str))

        # 3) data_used.csv — fetch actual OHLCV from database
        try:
            from data.service import get_ohlcv
            from datetime import datetime as dt
            s = doc.get("start_date") or "2020-01-01"
            e = doc.get("end_date") or "2030-12-31"
            sd = dt.fromisoformat(s) if "T" in str(s) else dt.strptime(str(s)[:10], "%Y-%m-%d")
            ed = dt.fromisoformat(e) if "T" in str(e) else dt.strptime(str(e)[:10], "%Y-%m-%d")
            sd = sd.replace(tzinfo=timezone.utc)
            ed = ed.replace(tzinfo=timezone.utc)
            df = get_ohlcv(doc["symbol"], doc["timeframe"], sd, ed)
            csv_buf = io.StringIO()
            df.to_csv(csv_buf, index=False)
            zf.writestr("data_used.csv", csv_buf.getvalue())
        except Exception as ex:
            zf.writestr("data_used.csv", f"# Could not fetch data: {ex}")

        # 4) expected_results.json
        results = {
            "metrics": doc.get("results", {}).get("metrics", {}),
            "costs": doc.get("results", {}).get("costs", {}),
            "trades": doc.get("trades", []),
            "equity_curve": doc.get("equity_curve", []),
        }
        zf.writestr("expected_results.json", json.dumps(results, indent=2, default=str))

        # 5) README.txt
        readme = f"""BACKTEST VERIFICATION PACKAGE
============================
Snapshot ID: {doc['snapshot_id']}
Created:     {doc.get('created_at')}
Engine:      v{doc.get('engine_version')}

Symbol:      {doc['symbol']}
Timeframe:   {doc['timeframe']}
Date Range:  {doc.get('start_date')} to {doc.get('end_date')}
Data Hash:   {doc.get('data_snapshot_hash')}

HOW TO VERIFY
-------------
1. Load data_used.csv into your backtesting platform
2. Apply the strategy from strategy.json
3. Use the parameters from backtest_params.json
4. Compare your results with expected_results.json
5. If the data_snapshot_hash matches, results must be identical

Files in this archive:
  strategy.json          — exact strategy configuration
  backtest_params.json   — symbol, timeframe, dates, engine version
  data_used.csv          — OHLCV candles used in this backtest
  expected_results.json  — trades, metrics, equity curve
  README.txt             — this file

Engine version {doc.get('engine_version')} changelog:
  https://your-domain.com/legal/engine-changelog
"""
        zf.writestr("README.txt", readme)

    buf.seek(0)
    filename = f"backtest_verify_{snapshot_id[:8]}.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ── Snapshot comparison ──────────────────────────────────────────────────────

@router.get("/backtest/compare-snapshots")
async def compare_snapshots(
    a: str = Query(..., description="First snapshot ID"),
    b: str = Query(..., description="Second snapshot ID"),
):
    """Public: side-by-side comparison of two backtest snapshots."""
    snap_a = backtest_snapshots.find_one({"snapshot_id": a}, {"_id": 0, "user_id": 0})
    snap_b = backtest_snapshots.find_one({"snapshot_id": b}, {"_id": 0, "user_id": 0})
    if not snap_a:
        raise HTTPException(404, f"Snapshot {a} not found")
    if not snap_b:
        raise HTTPException(404, f"Snapshot {b} not found")

    ma = snap_a.get("results", {}).get("metrics", {})
    mb = snap_b.get("results", {}).get("metrics", {})

    def _diff(key):
        va = ma.get(key, 0) or 0
        vb = mb.get(key, 0) or 0
        return {"a": va, "b": vb, "delta": round(vb - va, 4)}

    return {
        "snapshot_a": {
            "snapshot_id": snap_a["snapshot_id"],
            "symbol": snap_a["symbol"],
            "timeframe": snap_a["timeframe"],
            "engine_version": snap_a.get("engine_version"),
            "data_snapshot_hash": snap_a.get("data_snapshot_hash"),
            "strategy_version": snap_a.get("strategy_version"),
            "created_at": snap_a.get("created_at"),
            "strategy_name": snap_a.get("strategy_json_snapshot", {}).get("metadata", {}).get("name", ""),
        },
        "snapshot_b": {
            "snapshot_id": snap_b["snapshot_id"],
            "symbol": snap_b["symbol"],
            "timeframe": snap_b["timeframe"],
            "engine_version": snap_b.get("engine_version"),
            "data_snapshot_hash": snap_b.get("data_snapshot_hash"),
            "strategy_version": snap_b.get("strategy_version"),
            "created_at": snap_b.get("created_at"),
            "strategy_name": snap_b.get("strategy_json_snapshot", {}).get("metadata", {}).get("name", ""),
        },
        "same_data": snap_a.get("data_snapshot_hash") == snap_b.get("data_snapshot_hash"),
        "same_engine": snap_a.get("engine_version") == snap_b.get("engine_version"),
        "metrics_diff": {
            "total_trades": _diff("total_trades"),
            "win_rate": _diff("win_rate"),
            "total_pnl_pct": _diff("total_pnl_pct"),
            "max_drawdown_pct": _diff("max_drawdown_pct"),
            "sharpe_ratio": _diff("sharpe_ratio"),
            "profit_factor": _diff("profit_factor"),
            "avg_pnl_per_trade": _diff("avg_pnl_per_trade"),
        },
        "trades_a_count": len(snap_a.get("trades", [])),
        "trades_b_count": len(snap_b.get("trades", [])),
    }


# ── Strategy version history ─────────────────────────────────────────────────

@router.get("/strategy/{strategy_id}/versions")
async def get_strategy_versions(
    strategy_id: str,
    current_user: dict = Depends(get_current_user),
):
    """List version history for a strategy."""
    user_id = current_user.get("user_id", current_user.get("email"))
    # Verify ownership
    strat = strategies_collection.find_one(
        {"id": strategy_id, "user_id": user_id}, {"_id": 0, "id": 1}
    )
    if not strat:
        raise HTTPException(404, "Strategy not found")

    versions = list(
        strategy_versions.find(
            {"strategy_id": strategy_id},
            {"_id": 0}
        ).sort("version", -1).limit(50)
    )
    return {"strategy_id": strategy_id, "versions": versions, "count": len(versions)}
