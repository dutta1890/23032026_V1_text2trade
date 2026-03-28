"""Account management — demo mode, profile, export, soft delete."""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime, timezone
import uuid
import logging
import json
import re

from auth import get_current_user, users_collection, verify_password, change_password, ChangePasswordRequest
from database import db, strategies_collection

logger = logging.getLogger(__name__)
router = APIRouter()

paper_trades_col = db["paper_trades"]
performance_records_col = db["performance_records"]

VALID_TIMEZONES = [
    "Asia/Kolkata", "Asia/Tokyo", "Asia/Shanghai", "Asia/Singapore", "Asia/Dubai",
    "Europe/London", "Europe/Berlin", "Europe/Paris", "America/New_York",
    "America/Chicago", "America/Los_Angeles", "America/Sao_Paulo",
    "Australia/Sydney", "Pacific/Auckland", "UTC",
]

DEMO_STRATEGIES = [
    {
        "tag": "demo_golden_cross",
        "metadata": {
            "name": "Demo: Golden Cross on Reliance",
            "description": "Classic trend-following strategy using SMA 50/200 crossover. Already backtested for you.",
            "tags": ["demo", "trend", "sma"],
        },
        "market": {"type": "equity", "exchange": "NSE"},
        "instrument": {"symbol": "RELIANCE"},
        "timeframe": {"interval": "1d"},
        "entry_conditions": [{"name": "SMA", "params": {"short": 50, "long": 200}, "operator": "crosses_above"}],
        "exit_conditions": [{"name": "SMA", "params": {"short": 50, "long": 200}, "operator": "crosses_below"}],
        "filters": [],
        "risk_management": {
            "stop_loss": {"type": "percentage", "value": 3},
            "target_profit": None,
            "trailing_stop_loss": {"enabled": False, "type": "percentage", "value": 1.0, "activation_profit": 0},
            "time_based_exit": {"enabled": False, "exit_time": "15:10"},
            "daily_limits": {"max_loss_per_day": 5.0, "max_trades_per_day": 10},
            "position_sizing": {"method": "fixed_quantity", "value": 1},
        },
    },
    {
        "tag": "demo_rsi_reversion",
        "metadata": {
            "name": "Demo: RSI Mean Reversion on HDFCBANK",
            "description": "Buy when RSI dips below 30 (oversold), sell above 70. Ready to backtest.",
            "tags": ["demo", "mean-reversion", "rsi"],
        },
        "market": {"type": "equity", "exchange": "NSE"},
        "instrument": {"symbol": "HDFCBANK"},
        "timeframe": {"interval": "1d"},
        "entry_conditions": [{"name": "RSI", "params": {"period": 14}, "operator": "<", "value": 30}],
        "exit_conditions": [{"name": "RSI", "params": {"period": 14}, "operator": ">", "value": 70}],
        "filters": [],
        "risk_management": {
            "stop_loss": {"type": "percentage", "value": 2},
            "target_profit": None,
            "trailing_stop_loss": {"enabled": False, "type": "percentage", "value": 1.0, "activation_profit": 0},
            "time_based_exit": {"enabled": False, "exit_time": "15:10"},
            "daily_limits": {"max_loss_per_day": 5.0, "max_trades_per_day": 10},
            "position_sizing": {"method": "fixed_quantity", "value": 1},
        },
    },
    {
        "tag": "demo_supertrend",
        "metadata": {
            "name": "Demo: Supertrend Follower on INFY",
            "description": "Trend-following with Supertrend indicator. Running in paper trade mode.",
            "tags": ["demo", "trend", "supertrend"],
        },
        "market": {"type": "equity", "exchange": "NSE"},
        "instrument": {"symbol": "INFY"},
        "timeframe": {"interval": "1d"},
        "entry_conditions": [{"name": "Supertrend", "params": {"period": 10, "multiplier": 3.0}, "operator": "buy_signal"}],
        "exit_conditions": [{"name": "Supertrend", "params": {"period": 10, "multiplier": 3.0}, "operator": "sell_signal"}],
        "filters": [],
        "risk_management": {
            "stop_loss": {"type": "percentage", "value": 2},
            "target_profit": None,
            "trailing_stop_loss": {"enabled": True, "type": "percentage", "value": 1.5, "activation_profit": 1},
            "time_based_exit": {"enabled": False, "exit_time": "15:10"},
            "daily_limits": {"max_loss_per_day": 5.0, "max_trades_per_day": 10},
            "position_sizing": {"method": "fixed_quantity", "value": 1},
        },
    },
]

DEMO_BACKTEST_RESULT = {
    "trades": [
        {"entry_time": "2025-03-10", "entry_price": 1260.50, "exit_time": "2025-04-22", "exit_price": 1315.80, "pnl_points": 55.30, "pnl_percent": 4.39, "holding_candles": 31, "exit_reason": "indicator_exit"},
        {"entry_time": "2025-05-15", "entry_price": 1340.20, "exit_time": "2025-06-02", "exit_price": 1298.70, "pnl_points": -41.50, "pnl_percent": -3.10, "holding_candles": 12, "exit_reason": "stop_loss"},
        {"entry_time": "2025-07-18", "entry_price": 1476.74, "exit_time": "2025-08-05", "exit_price": 1520.30, "pnl_points": 43.56, "pnl_percent": 2.95, "holding_candles": 12, "exit_reason": "indicator_exit"},
    ],
    "metrics": {
        "total_trades": 3, "winning_trades": 2, "losing_trades": 1,
        "win_rate": 66.67, "total_pnl_pct": 4.24, "avg_pnl_per_trade": 1.41,
        "sharpe_ratio": 0.85, "max_drawdown_pct": -3.10, "profit_factor": 2.37,
        "avg_holding_candles": 18.3,
    },
    "equity_curve": [
        {"timestamp": "2025-03-10", "equity": 100000, "drawdown_pct": 0},
        {"timestamp": "2025-04-22", "equity": 104390, "drawdown_pct": 0},
        {"timestamp": "2025-06-02", "equity": 101153, "drawdown_pct": 3.10},
        {"timestamp": "2025-08-05", "equity": 104137, "drawdown_pct": 0},
    ],
}

DEMO_PAPER_TRADES = [
    {"entry_time": "2025-12-01", "entry_price": 1890.50, "exit_time": "2025-12-15", "exit_price": 1935.20, "pnl_points": 44.70, "pnl_percent": 2.36, "holding_candles": 10, "exit_reason": "indicator_exit"},
    {"entry_time": "2026-01-06", "entry_price": 1920.30, "exit_time": "2026-01-14", "exit_price": 1888.10, "pnl_points": -32.20, "pnl_percent": -1.68, "holding_candles": 6, "exit_reason": "trailing_sl"},
    {"entry_time": "2026-01-20", "entry_price": 1905.80, "exit_time": "2026-02-03", "exit_price": 1962.40, "pnl_points": 56.60, "pnl_percent": 2.97, "holding_candles": 10, "exit_reason": "indicator_exit"},
    {"entry_time": "2026-02-10", "entry_price": 1948.60, "exit_time": "2026-02-18", "exit_price": 1910.30, "pnl_points": -38.30, "pnl_percent": -1.97, "holding_candles": 6, "exit_reason": "stop_loss"},
    {"entry_time": "2026-02-24", "entry_price": 1930.10, "exit_time": "2026-03-07", "exit_price": 1985.50, "pnl_points": 55.40, "pnl_percent": 2.87, "holding_candles": 8, "exit_reason": "indicator_exit"},
    {"entry_time": "2026-03-10", "entry_price": 1970.20, "exit_time": None, "exit_price": None, "pnl_points": None, "pnl_percent": None, "holding_candles": 8, "exit_reason": None},
]


def seed_demo_data(user_id: str):
    """Seed demo strategies, backtest, and paper trade for a user. Idempotent."""
    existing = strategies_collection.count_documents({"user_id": user_id, "is_demo": True})
    if existing >= 3:
        return  # Already seeded

    now = datetime.now(timezone.utc).isoformat()
    strategy_ids = []

    for s in DEMO_STRATEGIES:
        # Check if this specific demo strategy already exists
        if strategies_collection.find_one({"user_id": user_id, "is_demo": True, "demo_tag": s["tag"]}):
            sid = strategies_collection.find_one({"user_id": user_id, "is_demo": True, "demo_tag": s["tag"]}, {"_id": 0, "id": 1})
            strategy_ids.append(sid["id"] if sid else "")
            continue

        strategy_id = str(uuid.uuid4())
        strategy_ids.append(strategy_id)
        doc = {
            "id": strategy_id,
            "user_id": user_id,
            "version": "1.0",
            "is_demo": True,
            "demo_tag": s["tag"],
            "metadata": {**s["metadata"], "created_at": now, "updated_at": now},
            "market": s["market"],
            "instrument": s["instrument"],
            "timeframe": s["timeframe"],
            "entry_conditions": s["entry_conditions"],
            "exit_conditions": s["exit_conditions"],
            "filters": s["filters"],
            "risk_management": s["risk_management"],
        }
        strategies_collection.insert_one(doc)

    # Seed backtest result for strategy #1 (Golden Cross)
    if strategy_ids and not performance_records_col.find_one({"user_id": user_id, "is_demo": True, "source": "backtest"}):
        perf = {
            "user_id": user_id,
            "strategy_id": strategy_ids[0],
            "strategy_name": "Demo: Golden Cross on Reliance",
            "symbol": "RELIANCE",
            "timeframe": "1d",
            "source": "backtest",
            "is_demo": True,
            "sharpe": 0.85,
            "pnl_pct": 4.24,
            "win_rate": 66.67,
            "max_drawdown": -3.10,
            "total_trades": 3,
            "profit_factor": 2.37,
            "recorded_at": now,
        }
        performance_records_col.insert_one(perf)

    # Seed paper trade for strategy #3 (Supertrend)
    if len(strategy_ids) >= 3 and not paper_trades_col.find_one({"user_id": user_id, "is_demo": True}):
        completed_trades = [t for t in DEMO_PAPER_TRADES if t["exit_time"] is not None]
        open_trade = next((t for t in DEMO_PAPER_TRADES if t["exit_time"] is None), None)

        current_pos = None
        if open_trade:
            current_pos = {
                "entry_time": open_trade["entry_time"],
                "entry_price": open_trade["entry_price"],
                "current_price": 1998.50,
                "unrealized_pnl_pct": 1.44,
                "unrealized_pnl_points": 28.30,
                "holding_candles": open_trade["holding_candles"],
            }

        pt_doc = {
            "paper_trade_id": str(uuid.uuid4()),
            "user_id": user_id,
            "strategy_id": strategy_ids[2],
            "status": "completed",
            "is_demo": True,
            "start_time": "2025-12-01T00:00:00",
            "current_position": current_pos,
            "trades": completed_trades,
            "equity_curve": [
                {"timestamp": "2025-12-01", "equity": 10000, "drawdown_pct": 0},
                {"timestamp": "2025-12-15", "equity": 10236, "drawdown_pct": 0},
                {"timestamp": "2026-01-14", "equity": 10064, "drawdown_pct": 1.68},
                {"timestamp": "2026-02-03", "equity": 10363, "drawdown_pct": 0},
                {"timestamp": "2026-02-18", "equity": 10159, "drawdown_pct": 1.97},
                {"timestamp": "2026-03-07", "equity": 10450, "drawdown_pct": 0},
            ],
            "metrics": {
                "total_trades": 5, "winning_trades": 3, "losing_trades": 2,
                "win_rate": 60.0, "total_pnl_pct": 4.55, "avg_pnl_per_trade": 0.91,
                "sharpe_ratio": 0.72, "max_drawdown_pct": -1.97, "profit_factor": 1.87,
            },
            "settings": {
                "symbol": "INFY", "timeframe": "1d", "initial_capital": 10000,
                "slippage_pct": 0.05, "lookback_days": 120,
            },
            "label": "Demo Paper Trade (Simulated)",
            "disclaimer": "Demo paper trade on INFY daily using pre-recorded simulation data.",
            "final_equity": 10450,
            "total_trades": 5,
            "created_at": "2025-12-01T00:00:00",
            "updated_at": now,
        }
        paper_trades_col.insert_one(pt_doc)

    # Seed demo capital tracker
    demo_cap = db["demo_capital"].find_one({"user_id": user_id})
    if not demo_cap:
        db["demo_capital"].insert_one({
            "user_id": user_id,
            "starting_capital": 10000,
            "current_capital": 10450,
            "trades_made": 6,
            "created_at": now,
            "updated_at": now,
        })

    logger.info(f"Demo data seeded for user {user_id}")


# =============================================================================
# ENDPOINTS
# =============================================================================

class ActivateDemoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

class SwitchModeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: str  # "demo" or "real"


@router.post("/account/activate-demo")
async def activate_demo(request: Request, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id")
    user_doc = users_collection.find_one({"user_id": user_id})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")

    # Set demo fields if not already
    now = datetime.now(timezone.utc).isoformat()
    updates = {
        "demo_capital": 10000,
        "demo_created_at": now,
        "account_mode": "demo",
    }
    users_collection.update_one({"user_id": user_id}, {"$set": updates})

    # Seed demo data (idempotent)
    seed_demo_data(user_id)

    return {"success": True, "message": "Demo mode activated with 10,000 virtual capital", "account_mode": "demo"}


@router.post("/account/switch-mode")
async def switch_mode(request: Request, body: SwitchModeRequest, current_user: dict = Depends(get_current_user)):
    if body.mode not in ("demo", "real"):
        raise HTTPException(status_code=400, detail="Mode must be 'demo' or 'real'")

    user_id = current_user.get("user_id")

    # If switching to demo, ensure demo data exists
    if body.mode == "demo":
        user_doc = users_collection.find_one({"user_id": user_id})
        if not user_doc.get("demo_capital"):
            seed_demo_data(user_id)
            users_collection.update_one({"user_id": user_id}, {"$set": {
                "demo_capital": 10000,
                "demo_created_at": datetime.now(timezone.utc).isoformat(),
            }})

    users_collection.update_one({"user_id": user_id}, {"$set": {"account_mode": body.mode}})
    return {"success": True, "account_mode": body.mode}


@router.get("/account/profile")
async def get_profile(request: Request, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id")
    user_doc = users_collection.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")

    mode = user_doc.get("account_mode", "real")
    demo_cap = None
    if mode == "demo":
        dc = db["demo_capital"].find_one({"user_id": user_id}, {"_id": 0})
        demo_cap = dc if dc else {"starting_capital": 10000, "current_capital": 10000, "trades_made": 0}

    email = user_doc.get("email", "")
    display_name = user_doc.get("display_name") or ""
    avatar_initial = (display_name[0] if display_name else email[0] if email else "?").upper()

    return {
        "user_id": user_doc.get("user_id"),
        "email": email,
        "display_name": display_name,
        "phone": user_doc.get("phone", ""),
        "avatar_initial": avatar_initial,
        "role": user_doc.get("role", "user"),
        "account_mode": mode,
        "demo_capital": demo_cap,
        "timezone": user_doc.get("timezone", "Asia/Kolkata"),
        "default_capital": user_doc.get("default_capital", 100000),
        "preferred_instruments": user_doc.get("preferred_instruments", []),
        "notification_preferences": user_doc.get("notification_preferences", {
            "email_on_backtest_complete": True,
            "email_on_paper_trade_signal": True,
            "email_weekly_summary": False,
        }),
        "has_completed_onboarding": user_doc.get("has_completed_onboarding", False),
        "created_at": user_doc.get("created_at"),
    }


# =============================================================================
# UPDATE PROFILE
# =============================================================================

class UpdateProfileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    display_name: Optional[str] = Field(default=None, max_length=50)
    phone: Optional[str] = Field(default=None, max_length=20)
    timezone: Optional[str] = None
    default_capital: Optional[float] = None
    preferred_instruments: Optional[List[str]] = None
    notification_preferences: Optional[dict] = None


@router.put("/account/profile")
async def update_profile(request: Request, body: UpdateProfileRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id")
    updates = {}

    if body.display_name is not None:
        updates["display_name"] = body.display_name.strip()[:50]

    if body.phone is not None:
        phone = body.phone.strip()
        if phone and not re.match(r'^\+?[\d\s\-()]{7,20}$', phone):
            raise HTTPException(status_code=400, detail="Invalid phone format")
        updates["phone"] = phone

    if body.timezone is not None:
        if body.timezone not in VALID_TIMEZONES:
            raise HTTPException(status_code=400, detail=f"Invalid timezone. Valid: {', '.join(VALID_TIMEZONES)}")
        updates["timezone"] = body.timezone

    if body.default_capital is not None:
        if body.default_capital <= 0 or body.default_capital > 100000000:
            raise HTTPException(status_code=400, detail="Capital must be between 1 and 10,00,00,000")
        updates["default_capital"] = body.default_capital

    if body.preferred_instruments is not None:
        updates["preferred_instruments"] = [s.upper().strip() for s in body.preferred_instruments[:20]]

    if body.notification_preferences is not None:
        valid_keys = {"email_on_backtest_complete", "email_on_paper_trade_signal", "email_weekly_summary"}
        prefs = {k: bool(v) for k, v in body.notification_preferences.items() if k in valid_keys}
        updates["notification_preferences"] = prefs

    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    users_collection.update_one({"user_id": user_id}, {"$set": updates})
    return {"success": True, "updated_fields": list(updates.keys())}


# =============================================================================
# CHANGE PASSWORD
# =============================================================================

@router.put("/profile/change-password")
async def change_password_endpoint(request: Request, body: ChangePasswordRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id")
    change_password(user_id, body.current_password, body.new_password)
    return {"success": True, "message": "Password changed successfully"}


# =============================================================================
# ACCOUNT SUMMARY
# =============================================================================

@router.get("/account/summary")
async def account_summary(request: Request, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id")
    user_doc = users_collection.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")

    mode = user_doc.get("account_mode", "real")
    demo_cap = None
    if mode == "demo":
        dc = db["demo_capital"].find_one({"user_id": user_id}, {"_id": 0})
        demo_cap = dc

    real_strats = strategies_collection.count_documents({"user_id": user_id, "is_demo": {"$ne": True}})
    demo_strats = strategies_collection.count_documents({"user_id": user_id, "is_demo": True})
    total_backtests = performance_records_col.count_documents({"user_id": user_id})
    total_paper = paper_trades_col.count_documents({"user_id": user_id})

    return {
        "account_mode": mode,
        "demo_capital": demo_cap,
        "total_strategies_real": real_strats,
        "total_strategies_demo": demo_strats,
        "total_backtests": total_backtests,
        "total_paper_trades": total_paper,
        "member_since": user_doc.get("created_at"),
        "email": user_doc.get("email"),
        "display_name": user_doc.get("display_name", ""),
    }


# =============================================================================
# EXPORT DATA
# =============================================================================

@router.post("/account/export-data")
async def export_data(request: Request, current_user: dict = Depends(get_current_user)):
    """Export all user data as JSON. Real mode only (no demo data). Sanitized."""
    user_id = current_user.get("user_id")
    user_doc = users_collection.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})

    # Real-mode data only (exclude demo)
    strats = list(strategies_collection.find(
        {"user_id": user_id, "is_demo": {"$ne": True}}, {"_id": 0}
    ))
    papers = list(paper_trades_col.find(
        {"user_id": user_id, "is_demo": {"$ne": True}}, {"_id": 0}
    ))
    backtests = list(db["backtests"].find(
        {"user_id": user_id, "is_demo": {"$ne": True}}, {"_id": 0}
    ))
    perfs = list(performance_records_col.find(
        {"user_id": user_id, "is_demo": {"$ne": True}}, {"_id": 0}
    ))

    export = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "user_email": current_user.get("email", ""),
        "profile": {
            "email": user_doc.get("email") if user_doc else "",
            "display_name": user_doc.get("display_name") if user_doc else "",
            "created_at": user_doc.get("created_at") if user_doc else "",
            "timezone": user_doc.get("timezone", "Asia/Kolkata") if user_doc else "",
            "phone": user_doc.get("phone") if user_doc else "",
            "preferred_instruments": user_doc.get("preferred_instruments", []) if user_doc else [],
        },
        "strategies": strats,
        "backtests": backtests,
        "paper_trades": papers,
        "performance_records": perfs,
    }
    return export


# =============================================================================
# DELETE ACCOUNT (SOFT)
# =============================================================================

class DeleteAccountRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    password: str


@router.delete("/account")
async def delete_account(request: Request, body: DeleteAccountRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id")
    user_doc = users_collection.find_one({"user_id": user_id})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(body.password, user_doc["password_hash"]):
        raise HTTPException(status_code=400, detail="Incorrect password")

    users_collection.update_one({"user_id": user_id}, {"$set": {
        "is_active": False,
        "deactivated_at": datetime.now(timezone.utc).isoformat(),
    }})
    logger.info(f"Account soft-deleted: {user_id}")
    return {"success": True, "message": "Account deactivated. Your data is preserved."}


@router.post("/account/complete-onboarding")
async def complete_onboarding(request: Request, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id")
    users_collection.update_one({"user_id": user_id}, {"$set": {"has_completed_onboarding": True}})
    return {"success": True}


@router.post("/account/restart-tour")
async def restart_tour(request: Request, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id")
    users_collection.update_one({"user_id": user_id}, {"$set": {"has_completed_onboarding": False}})
    return {"success": True}
