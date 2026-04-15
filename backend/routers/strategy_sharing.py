"""Enhanced strategy sharing — short URLs, copy-as-text, PDF export, broker instructions, analytics."""

import io
import json
import logging
import secrets
import string
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict

from auth import get_current_user, get_optional_user
from database import db, strategies_collection, analytics_db

logger = logging.getLogger(__name__)
router = APIRouter()

strategy_shares = db["strategy_shares"]
backtest_snapshots = db["backtest_snapshots"]

try:
    strategy_shares.create_index("share_id", unique=True)
    strategy_shares.create_index("strategy_id")
    strategy_shares.create_index("user_id")
except Exception:
    pass


# ── Helpers ──────────────────────────────────────────────────────────────────

def _gen_short_id(length=8) -> str:
    """Generate a URL-friendly short ID (e.g., x7k9m2q4)."""
    alphabet = string.ascii_lowercase + string.digits
    while True:
        sid = "".join(secrets.choice(alphabet) for _ in range(length))
        if not strategy_shares.find_one({"share_id": sid}):
            return sid


def _condition_to_english(cond: dict) -> str:
    """Convert a condition dict to plain English."""
    name = cond.get("name", "?")
    op = cond.get("operator", "")
    val = cond.get("value")
    params = cond.get("params", {})
    period = params.get("period", params.get("short", ""))

    period_str = f"({period})" if period else ""
    op_map = {
        "<": "is below", ">": "is above", "<=": "is at or below", ">=": "is at or above",
        "crosses_above": "crosses above", "cross_above": "crosses above",
        "crosses_below": "crosses below", "cross_below": "crosses below",
        "bullish_cross": "bullish crossover", "bearish_cross": "bearish crossover",
        "buy_signal": "buy signal", "sell_signal": "sell signal",
        "upper_touch": "touches upper band", "lower_touch": "touches lower band",
    }
    op_text = op_map.get(op, op)

    if name in ("SMA", "EMA"):
        short_p = params.get("short", params.get("period", "?"))
        long_p = params.get("long", "?")
        return f"{name}({short_p}) {op_text} {name}({long_p})"
    if val is not None:
        return f"{name}{period_str} {op_text} {val}"
    return f"{name}{period_str} {op_text}"


def _get_latest_backtest(strategy_id: str, user_id: str) -> Optional[dict]:
    """Get most recent backtest snapshot for a strategy."""
    snap = backtest_snapshots.find_one(
        {"strategy_id": strategy_id, "user_id": user_id},
        {"_id": 0, "user_id": 0},
        sort=[("created_at", -1)],
    )
    return snap


# ── CRUD ─────────────────────────────────────────────────────────────────────

@router.post("/strategies/{strategy_id}/share")
async def create_share(strategy_id: str, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id", current_user.get("email"))
    strategy = strategies_collection.find_one({"id": strategy_id, "user_id": user_id}, {"_id": 0})
    if not strategy:
        raise HTTPException(404, "Strategy not found")

    existing = strategy_shares.find_one({"strategy_id": strategy_id, "user_id": user_id, "is_public": True}, {"_id": 0})
    if existing:
        return {"success": True, "share_id": existing["share_id"], "already_shared": True,
                "view_count": existing.get("view_count", 0), "clone_count": existing.get("clone_count", 0)}

    share_id = _gen_short_id()
    now = datetime.now(timezone.utc).isoformat()
    strategy_shares.insert_one({
        "share_id": share_id,
        "strategy_id": strategy_id,
        "strategy_version": strategy.get("strategy_version", int(float(strategy.get("version", "1")))),
        "user_id": user_id,
        "is_public": True,
        "view_count": 0,
        "clone_count": 0,
        "expires_at": None,
        "created_at": now,
        "strategy_snapshot": strategy,
    })
    return {"success": True, "share_id": share_id, "already_shared": False, "view_count": 0, "clone_count": 0}


@router.get("/s/{share_id}")
async def get_share(share_id: str):
    """Public endpoint — returns shared strategy details."""
    doc = strategy_shares.find_one({"share_id": share_id, "is_public": True}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Share not found or has been revoked")

    strategy_shares.update_one({"share_id": share_id}, {"$inc": {"view_count": 1}})
    strat = doc.get("strategy_snapshot", {})
    strat.pop("user_id", None)

    # Get latest backtest
    backtest = None
    snap = backtest_snapshots.find_one(
        {"strategy_id": doc["strategy_id"]},
        {"_id": 0, "user_id": 0},
        sort=[("created_at", -1)],
    )
    if snap:
        backtest = {
            "snapshot_id": snap.get("snapshot_id"),
            "metrics": snap.get("results", {}).get("metrics", {}),
            "equity_curve": snap.get("equity_curve", []),
            "trades_count": len(snap.get("trades", [])),
            "engine_version": snap.get("engine_version"),
            "data_start": snap.get("start_date"),
            "data_end": snap.get("end_date"),
        }

    return {
        "success": True,
        "share_id": share_id,
        "strategy": strat,
        "backtest": backtest,
        "view_count": doc.get("view_count", 0) + 1,
        "clone_count": doc.get("clone_count", 0),
        "created_at": doc.get("created_at"),
        "strategy_version": doc.get("strategy_version"),
    }


@router.post("/s/{share_id}/clone")
async def clone_share(share_id: str, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id", current_user.get("email"))
    doc = strategy_shares.find_one({"share_id": share_id, "is_public": True}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Share not found")

    strat = doc.get("strategy_snapshot", {})
    now = datetime.now(timezone.utc).isoformat()
    new_id = str(uuid.uuid4())
    original_name = strat.get("metadata", {}).get("name", "Shared Strategy")

    new_strat = {
        "id": new_id, "user_id": user_id, "version": "1", "strategy_version": 1,
        "metadata": {
            "name": f"{original_name} (cloned)",
            "description": strat.get("metadata", {}).get("description", ""),
            "tags": ["cloned"], "created_at": now, "updated_at": now,
        },
        "market": strat.get("market", {"type": "equity", "exchange": "NSE"}),
        "instrument": strat.get("instrument", {"symbol": "RELIANCE"}),
        "timeframe": strat.get("timeframe", {"interval": "1d"}),
        "entry_conditions": strat.get("entry_conditions", []),
        "exit_conditions": strat.get("exit_conditions", []),
        "filters": strat.get("filters", []),
        "risk_management": strat.get("risk_management", {}),
    }
    strategies_collection.insert_one(new_strat)
    new_strat.pop("_id", None)
    strategy_shares.update_one({"share_id": share_id}, {"$inc": {"clone_count": 1}})
    analytics_db["strategies_created"] += 1
    return {"success": True, "strategy_id": new_id, "strategy": new_strat}


@router.delete("/strategies/{strategy_id}/share/{share_id}")
async def revoke_share(strategy_id: str, share_id: str, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id", current_user.get("email"))
    result = strategy_shares.update_one(
        {"share_id": share_id, "strategy_id": strategy_id, "user_id": user_id},
        {"$set": {"is_public": False}},
    )
    if result.modified_count == 0:
        raise HTTPException(404, "Share not found or not owned by you")
    return {"success": True, "message": "Share revoked"}


# ── Copy as Text ─────────────────────────────────────────────────────────────

@router.get("/strategies/{strategy_id}/copy-text")
async def copy_as_text(strategy_id: str, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id", current_user.get("email"))
    strat = strategies_collection.find_one({"id": strategy_id, "user_id": user_id}, {"_id": 0})
    if not strat:
        raise HTTPException(404, "Strategy not found")

    return {"text": _build_text(strat, user_id)}


@router.get("/s/{share_id}/copy-text")
async def copy_shared_text(share_id: str):
    """Public — get copy text for a shared strategy."""
    doc = strategy_shares.find_one({"share_id": share_id, "is_public": True}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Share not found")
    strat = doc.get("strategy_snapshot", {})
    return {"text": _build_text(strat, doc.get("user_id", ""), share_id)}


def _build_text(strat: dict, user_id: str, share_id: str = None) -> str:
    meta = strat.get("metadata", {})
    symbol = strat.get("instrument", {}).get("symbol", "?")
    tf = strat.get("timeframe", {}).get("interval", "?")
    rm = strat.get("risk_management", {})

    lines = [f"STRATEGY: {meta.get('name', 'Unnamed')}", f"Stock: {symbol} (NSE)", f"Timeframe: {tf}", ""]

    entries = strat.get("entry_conditions", [])
    if entries:
        lines.append("ENTRY:")
        for c in entries:
            lines.append(f"  When {_condition_to_english(c)}")
        lines.append("")

    exits = strat.get("exit_conditions", [])
    if exits:
        lines.append("EXIT:")
        for c in exits:
            lines.append(f"  When {_condition_to_english(c)}")
        lines.append("")

    if rm.get("stop_loss"):
        sl = rm["stop_loss"]
        lines.append(f"STOP LOSS: {sl.get('value', '?')}% ({sl.get('type', 'percentage')})")
    if rm.get("target_profit"):
        tp = rm["target_profit"]
        lines.append(f"TARGET: {tp.get('value', '?')}% ({tp.get('type', 'percentage')})")
    if rm.get("trailing_stop_loss", {}).get("enabled"):
        tsl = rm["trailing_stop_loss"]
        lines.append(f"TRAILING SL: {tsl.get('value', '?')}%")

    # Backtest results if available
    snap = backtest_snapshots.find_one(
        {"strategy_id": strat.get("id", ""), "user_id": user_id},
        {"_id": 0}, sort=[("created_at", -1)],
    )
    if snap:
        m = snap.get("results", {}).get("metrics", {})
        if m.get("total_trades"):
            lines.append("")
            lines.append(f"Last backtest: {m['total_trades']} trades, {m.get('win_rate', 0)}% win rate, "
                         f"{'+' if (m.get('total_pnl_pct', 0) or 0) >= 0 else ''}{m.get('total_pnl_pct', 0)}% total return")
            lines.append(f"Max drawdown: {m.get('max_drawdown_pct', 0)}%")

    lines.append("")
    lines.append("Created on Text2trade")
    if share_id:
        lines.append(f"View full strategy: /s/{share_id}")
    lines.append("")
    lines.append("Backtest has known limitations. Past performance does not guarantee future results.")

    return "\n".join(lines)


# ── PDF Export ───────────────────────────────────────────────────────────────

@router.get("/strategies/{strategy_id}/pdf")
async def export_pdf(request: Request, strategy_id: str, token: Optional[str] = None, current_user: dict = Depends(get_optional_user)):
    """PDF export — supports both header auth and query param token."""
    if not current_user and token:
        # Try to decode the token from query param
        try:
            import jwt as pyjwt
            import os
            payload = pyjwt.decode(token, os.environ.get("JWT_SECRET", ""), algorithms=["HS256"])
            user_id = payload.get("user_id", payload.get("sub", ""))
        except Exception:
            raise HTTPException(401, "Invalid token")
    elif current_user:
        user_id = current_user.get("user_id", current_user.get("email"))
    else:
        raise HTTPException(401, "Authentication required")

    strat = strategies_collection.find_one({"id": strategy_id, "user_id": user_id}, {"_id": 0})
    if not strat:
        raise HTTPException(404, "Strategy not found")

    snap = _get_latest_backtest(strategy_id, user_id)
    buf = _generate_pdf(strat, snap)
    name = strat.get("metadata", {}).get("name", "strategy").replace(" ", "_")
    date = datetime.now(timezone.utc).strftime("%Y%m%d")
    filename = f"{name}_{date}.pdf"

    return StreamingResponse(buf, media_type="application/pdf",
                             headers={"Content-Disposition": f"attachment; filename={filename}"})


@router.get("/s/{share_id}/pdf")
async def export_shared_pdf(share_id: str):
    """Public PDF download for shared strategies."""
    doc = strategy_shares.find_one({"share_id": share_id, "is_public": True}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Share not found")

    strat = doc.get("strategy_snapshot", {})
    snap = backtest_snapshots.find_one(
        {"strategy_id": doc["strategy_id"]},
        {"_id": 0, "user_id": 0}, sort=[("created_at", -1)],
    )
    buf = _generate_pdf(strat, snap)
    name = strat.get("metadata", {}).get("name", "strategy").replace(" ", "_")
    date = datetime.now(timezone.utc).strftime("%Y%m%d")
    return StreamingResponse(buf, media_type="application/pdf",
                             headers={"Content-Disposition": f"attachment; filename={name}_{date}.pdf"})


def _generate_pdf(strat: dict, snap: Optional[dict]) -> io.BytesIO:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=15*mm, bottomMargin=15*mm,
                            leftMargin=15*mm, rightMargin=15*mm)
    styles = getSampleStyleSheet()
    green = HexColor("#00e676")
    dark = HexColor("#1a1a2e")
    gray = HexColor("#888888")

    title_s = ParagraphStyle("Title2", parent=styles["Title"], fontSize=18, textColor=dark, spaceAfter=4)
    h2_s = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=12, textColor=dark, spaceBefore=10, spaceAfter=4)
    body_s = ParagraphStyle("Body2", parent=styles["Normal"], fontSize=9, textColor=HexColor("#333333"), leading=13)
    small_s = ParagraphStyle("Small", parent=styles["Normal"], fontSize=8, textColor=gray, leading=11)

    meta = strat.get("metadata", {})
    symbol = strat.get("instrument", {}).get("symbol", "?")
    tf = strat.get("timeframe", {}).get("interval", "?")
    rm = strat.get("risk_management", {})
    elems = []

    # Header
    elems.append(Paragraph("Text2trade", ParagraphStyle("Logo", parent=styles["Normal"], fontSize=10, textColor=green)))
    elems.append(Spacer(1, 3*mm))
    elems.append(Paragraph(meta.get("name", "Unnamed Strategy"), title_s))
    elems.append(Paragraph(f"{symbol} &bull; {tf} &bull; v{strat.get('version', '1')}", small_s))
    if meta.get("description"):
        elems.append(Spacer(1, 2*mm))
        elems.append(Paragraph(meta["description"], body_s))
    elems.append(Spacer(1, 4*mm))

    # Entry conditions
    entries = strat.get("entry_conditions", [])
    if entries:
        elems.append(Paragraph("Entry Conditions", h2_s))
        for c in entries:
            elems.append(Paragraph(f"&bull; {_condition_to_english(c)}", body_s))

    # Exit conditions
    exits = strat.get("exit_conditions", [])
    if exits:
        elems.append(Paragraph("Exit Conditions", h2_s))
        for c in exits:
            elems.append(Paragraph(f"&bull; {_condition_to_english(c)}", body_s))

    # Risk
    risk_lines = []
    if rm.get("stop_loss"):
        risk_lines.append(f"Stop Loss: {rm['stop_loss'].get('value', '?')}% ({rm['stop_loss'].get('type', 'pct')})")
    if rm.get("target_profit"):
        risk_lines.append(f"Target Profit: {rm['target_profit'].get('value', '?')}% ({rm['target_profit'].get('type', 'pct')})")
    if rm.get("trailing_stop_loss", {}).get("enabled"):
        risk_lines.append(f"Trailing SL: {rm['trailing_stop_loss'].get('value', '?')}%")
    if risk_lines:
        elems.append(Paragraph("Risk Management", h2_s))
        for rl in risk_lines:
            elems.append(Paragraph(f"&bull; {rl}", body_s))

    # Backtest results
    if snap:
        m = snap.get("results", {}).get("metrics", {})
        if m.get("total_trades"):
            elems.append(Paragraph("Backtest Results", h2_s))
            data = [
                ["Total Trades", str(m.get("total_trades", 0)), "Win Rate", f"{m.get('win_rate', 0)}%"],
                ["Total P&L", f"{m.get('total_pnl_pct', 0)}%", "Max Drawdown", f"{m.get('max_drawdown_pct', 0)}%"],
                ["Sharpe Ratio", str(m.get("sharpe_ratio", "N/A")), "Profit Factor", str(m.get("profit_factor", "N/A"))],
            ]
            t = Table(data, colWidths=[35*mm, 30*mm, 35*mm, 30*mm])
            t.setStyle(TableStyle([
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("TEXTCOLOR", (0, 0), (-1, -1), HexColor("#333333")),
                ("TEXTCOLOR", (0, 0), (0, -1), gray),
                ("TEXTCOLOR", (2, 0), (2, -1), gray),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#dddddd")),
            ]))
            elems.append(t)

    # Disclaimer
    elems.append(Spacer(1, 8*mm))
    elems.append(Paragraph("Limitations", h2_s))
    elems.append(Paragraph(
        "Past performance does not guarantee future results. Backtests use historical data with known limitations "
        "including but not limited to: no slippage variation, no liquidity modeling, and simplified fill assumptions. "
        "This strategy is for educational purposes only and does not constitute financial advice.", small_s))
    elems.append(Spacer(1, 3*mm))
    elems.append(Paragraph(f"Generated by Text2trade on {datetime.now(timezone.utc).strftime('%Y-%m-%d')}", small_s))

    doc.build(elems)
    buf.seek(0)
    return buf


# ── Broker Instructions ──────────────────────────────────────────────────────

BROKER_INSTRUCTIONS = {
    "zerodha": {
        "name": "Zerodha Kite",
        "steps": [
            "Open Kite (web at kite.zerodha.com or mobile app)",
            'Search for "{symbol}" in the market watch',
            'Click "Buy" (B) to open the order window',
            "Enter quantity: {qty} shares",
            "Order type: Limit -> enter your desired entry price",
            "Place the order",
            "Set up a GTT (Good Till Triggered) order for stop loss at your SL price",
            "Set up another GTT for target profit at your TP price",
            "Monitor indicator values in Kite's chart (add {indicators} to your chart)",
        ],
        "note": "GTT orders remain active until triggered or 1 year. You can set both SL and target as a GTT OCO (One Cancels Other).",
        "help_url": "https://support.zerodha.com/category/trading-and-markets/gtt",
    },
    "angel_one": {
        "name": "Angel One",
        "steps": [
            "Open Angel One app or web platform (angelone.in)",
            'Search for "{symbol}" in the search bar',
            'Tap "Buy" to open the order form',
            "Enter quantity: {qty} shares",
            "Select order type: Limit and enter entry price",
            "Place the order",
            "Go to Orders -> set a Stop Loss order at your SL price",
            "Set a Target order at your TP price",
            "Use the chart section to add {indicators} for monitoring",
        ],
        "note": "Angel One supports bracket orders for automatic SL and target placement on intraday trades.",
        "help_url": "https://www.angelone.in/knowledge-center",
    },
    "upstox": {
        "name": "Upstox",
        "steps": [
            "Open Upstox Pro (web or mobile app)",
            'Search for "{symbol}" in the watchlist',
            'Click "Buy" to open the order window',
            "Enter quantity: {qty} shares",
            "Order type: Limit -> enter entry price",
            "Place the order",
            "Set a GTT order for stop loss and target",
            "Use Upstox charts to monitor {indicators}",
        ],
        "note": "Upstox supports GTT orders for delivery trades. For intraday, use bracket orders.",
        "help_url": "https://help.upstox.com",
    },
    "dhan": {
        "name": "Dhan",
        "steps": [
            "Open Dhan app or web (dhan.co)",
            'Search for "{symbol}"',
            'Tap "Buy" to place an order',
            "Enter quantity: {qty} shares",
            "Select Limit order and enter entry price",
            "Place the order",
            "Use Forever Orders for SL and target (similar to GTT)",
            "Monitor {indicators} in Dhan's TradingView charts",
        ],
        "note": "Dhan provides TradingView-powered charts with all major indicators built in.",
        "help_url": "https://help.dhan.co",
    },
    "groww": {
        "name": "Groww",
        "steps": [
            "Open Groww app or web (groww.in)",
            'Search for "{symbol}" in stocks section',
            'Tap "Buy"',
            "Enter quantity: {qty} shares",
            "Select Limit order and set entry price",
            "Place the order",
            "Note: Groww does not support GTT/bracket orders yet",
            "You will need to manually monitor and place SL/target orders",
            "Use an external charting tool to track {indicators}",
        ],
        "note": "Groww has limited order types. Manual monitoring is required for this strategy.",
        "help_url": "https://support.groww.in",
    },
    "5paisa": {
        "name": "5paisa",
        "steps": [
            "Open 5paisa app or web (5paisa.com)",
            'Search for "{symbol}" in the trading section',
            'Click "Buy"',
            "Enter quantity: {qty} shares",
            "Choose Limit order type and set price",
            "Place the order",
            "Set up bracket order or cover order for automatic SL",
            "Monitor {indicators} in the chart section",
        ],
        "note": "5paisa supports bracket and cover orders for intraday. Use GTT for delivery.",
        "help_url": "https://www.5paisa.com/knowledge-center",
    },
}


@router.get("/strategies/{strategy_id}/broker-instructions/{broker}")
async def get_broker_instructions(strategy_id: str, broker: str, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id", current_user.get("email"))
    strat = strategies_collection.find_one({"id": strategy_id, "user_id": user_id}, {"_id": 0})
    if not strat:
        raise HTTPException(404, "Strategy not found")

    return _build_broker_instructions(strat, broker)


@router.get("/s/{share_id}/broker-instructions/{broker}")
async def get_shared_broker_instructions(share_id: str, broker: str):
    doc = strategy_shares.find_one({"share_id": share_id, "is_public": True}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Share not found")
    return _build_broker_instructions(doc.get("strategy_snapshot", {}), broker)


def _build_broker_instructions(strat: dict, broker: str) -> dict:
    broker = broker.lower()
    tmpl = BROKER_INSTRUCTIONS.get(broker)
    if not tmpl:
        raise HTTPException(400, f"Unknown broker. Available: {', '.join(BROKER_INSTRUCTIONS.keys())}")

    symbol = strat.get("instrument", {}).get("symbol", "RELIANCE")
    indicators = ", ".join(set(c.get("name", "") for c in
                               strat.get("entry_conditions", []) + strat.get("exit_conditions", [])))
    qty = "100"  # default display quantity

    steps = [s.format(symbol=symbol, qty=qty, indicators=indicators or "your indicators") for s in tmpl["steps"]]

    return {
        "broker": broker,
        "broker_name": tmpl["name"],
        "symbol": symbol,
        "steps": steps,
        "note": tmpl["note"],
        "help_url": tmpl["help_url"],
    }


# ── Share Analytics ──────────────────────────────────────────────────────────

@router.get("/strategies/{strategy_id}/share-stats")
async def get_share_stats(strategy_id: str, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id", current_user.get("email"))
    shares = list(strategy_shares.find(
        {"strategy_id": strategy_id, "user_id": user_id}, {"_id": 0}
    ))
    total_views = sum(s.get("view_count", 0) for s in shares)
    total_clones = sum(s.get("clone_count", 0) for s in shares)
    active_shares = [s for s in shares if s.get("is_public")]

    return {
        "strategy_id": strategy_id,
        "total_shares": len(shares),
        "active_shares": len(active_shares),
        "total_views": total_views,
        "total_clones": total_clones,
        "shares": [{
            "share_id": s["share_id"],
            "is_public": s.get("is_public", True),
            "view_count": s.get("view_count", 0),
            "clone_count": s.get("clone_count", 0),
            "created_at": s.get("created_at"),
        } for s in shares],
    }


@router.get("/admin/analytics/shares")
async def admin_share_analytics(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(403, "Admin only")

    pipeline = [
        {"$group": {
            "_id": "$strategy_id",
            "total_views": {"$sum": "$view_count"},
            "total_clones": {"$sum": "$clone_count"},
            "share_count": {"$sum": 1},
        }},
        {"$sort": {"total_views": -1}},
        {"$limit": 20},
    ]
    top = list(strategy_shares.aggregate(pipeline))
    total_shares = strategy_shares.count_documents({})
    total_views = sum(s["total_views"] for s in top)
    total_clones = sum(s["total_clones"] for s in top)

    return {
        "total_shares": total_shares,
        "total_views": total_views,
        "total_clones": total_clones,
        "conversion_rate": round(total_clones / max(total_views, 1) * 100, 1),
        "top_shared": [{
            "strategy_id": s["_id"],
            "views": s["total_views"],
            "clones": s["total_clones"],
            "shares": s["share_count"],
        } for s in top],
    }


# ── Broker Login Links + Audit ───────────────────────────────────────────────

BROKER_LOGIN_LINKS = {
    "zerodha": {
        "name": "Zerodha Kite",
        "url": "https://kite.zerodha.com/",
        "description": "Opens Zerodha Kite web trading platform",
        "has_deep_link": False,
    },
    "angel_one": {
        "name": "Angel One",
        "url": "https://trade.angelone.in/",
        "description": "Opens Angel One web trading platform",
        "has_deep_link": False,
    },
    "upstox": {
        "name": "Upstox",
        "url": "https://pro.upstox.com/",
        "description": "Opens Upstox Pro web trading platform",
        "has_deep_link": False,
    },
    "dhan": {
        "name": "Dhan",
        "url": "https://web.dhan.co/",
        "description": "Opens Dhan web trading platform",
        "has_deep_link": False,
    },
    "groww": {
        "name": "Groww",
        "url": "https://groww.in/stocks",
        "description": "Opens Groww stocks section",
        "has_deep_link": False,
    },
    "5paisa": {
        "name": "5paisa",
        "url": "https://trade.5paisa.com/",
        "description": "Opens 5paisa web trading platform",
        "has_deep_link": False,
    },
}


@router.get("/broker-links")
async def get_all_broker_links():
    """Public: returns all broker login URLs."""
    return {
        "brokers": [
            {"id": k, **v} for k, v in BROKER_LOGIN_LINKS.items()
        ]
    }


@router.post("/broker-link/generate")
async def generate_broker_link(
    request: Request,
    body: dict,
    current_user: dict = Depends(get_current_user),
):
    """Generate a broker link and log it to audit trail for SEBI compliance."""
    from audit import log_audit, get_request_meta
    from logging_config import get_request_id

    broker_id = body.get("broker", "").lower()
    if broker_id not in BROKER_LOGIN_LINKS:
        raise HTTPException(400, f"Unknown broker. Available: {', '.join(BROKER_LOGIN_LINKS.keys())}")

    broker = BROKER_LOGIN_LINKS[broker_id]
    user_id = current_user.get("user_id", current_user.get("email"))
    meta = get_request_meta(request)

    # Log to audit trail
    log_audit(
        user_id=user_id,
        action="broker_link_generated",
        details={
            "broker": broker_id,
            "broker_name": broker["name"],
            "symbol": body.get("symbol", ""),
            "strategy_id": body.get("strategy_id", ""),
        },
        ip_address=meta["ip"],
        user_agent=meta["ua"],
        request_id=get_request_id() or "",
    )

    return {
        "success": True,
        "broker": broker_id,
        "broker_name": broker["name"],
        "url": broker["url"],
        "description": broker["description"],
    }
