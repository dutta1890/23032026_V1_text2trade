"""Strategy Alerts — rule-based monitoring with in-app notifications."""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Literal
from datetime import datetime, timezone
import uuid
import logging

from auth import get_current_user
from database import db

logger = logging.getLogger(__name__)
router = APIRouter()

alerts_collection = db["alert_rules"]
notifications_collection = db["alert_notifications"]
records_collection = db["performance_records"]

try:
    alerts_collection.create_index("user_id")
    notifications_collection.create_index("user_id")
    notifications_collection.create_index([("user_id", 1), ("triggered_at", -1)])
except Exception:
    pass


VALID_METRICS = ["sharpe", "pnl_pct", "win_rate", "max_drawdown"]
VALID_OPERATORS = ["lt", "gt", "lte", "gte"]
OPERATOR_LABELS = {"lt": "<", "gt": ">", "lte": "<=", "gte": ">="}
METRIC_LABELS = {
    "sharpe": "Sharpe Ratio",
    "pnl_pct": "P&L %",
    "win_rate": "Win Rate %",
    "max_drawdown": "Max Drawdown %",
}


class CreateAlertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    strategy_name: str = Field(max_length=120)
    metric: Literal["sharpe", "pnl_pct", "win_rate", "max_drawdown"]
    operator: Literal["lt", "gt", "lte", "gte"]
    threshold: float = Field(ge=-1000, le=1000)


class UpdateAlertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool


def _compare(value: float, operator: str, threshold: float) -> bool:
    if operator == "lt":
        return value < threshold
    elif operator == "gt":
        return value > threshold
    elif operator == "lte":
        return value <= threshold
    elif operator == "gte":
        return value >= threshold
    return False


@router.post("/alerts")
async def create_alert(request: Request, body: CreateAlertRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id", current_user.get("email"))

    existing = alerts_collection.count_documents({"user_id": user_id})
    if existing >= 20:
        raise HTTPException(status_code=400, detail="Maximum 20 alert rules allowed")

    alert_id = str(uuid.uuid4())[:12]
    doc = {
        "alert_id": alert_id,
        "user_id": user_id,
        "strategy_name": body.strategy_name.strip(),
        "metric": body.metric,
        "operator": body.operator,
        "threshold": body.threshold,
        "enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    alerts_collection.insert_one(doc)
    doc.pop("_id", None)
    return {"success": True, "alert": doc}


@router.get("/alerts")
async def list_alerts(request: Request, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id", current_user.get("email"))
    rules = list(alerts_collection.find({"user_id": user_id}, {"_id": 0}).sort("created_at", -1))
    return {"alerts": rules, "count": len(rules)}


@router.put("/alerts/{alert_id}")
async def update_alert(request: Request, alert_id: str, body: UpdateAlertRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id", current_user.get("email"))
    result = alerts_collection.update_one(
        {"alert_id": alert_id, "user_id": user_id},
        {"$set": {"enabled": body.enabled}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"success": True}


@router.delete("/alerts/{alert_id}")
async def delete_alert(request: Request, alert_id: str, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id", current_user.get("email"))
    result = alerts_collection.delete_one({"alert_id": alert_id, "user_id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"success": True}


@router.post("/alerts/evaluate")
async def evaluate_alerts(request: Request, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id", current_user.get("email"))
    rules = list(alerts_collection.find({"user_id": user_id, "enabled": True}, {"_id": 0}))

    if not rules:
        return {"triggered": 0, "notifications": []}

    records = list(records_collection.find({"user_id": user_id}, {"_id": 0}))
    if not records:
        return {"triggered": 0, "notifications": []}

    # Group records by strategy_name and compute averages
    strat_metrics = {}
    for r in records:
        name = r.get("strategy_name", "")
        if name not in strat_metrics:
            strat_metrics[name] = []
        strat_metrics[name].append(r)

    strat_avgs = {}
    for name, runs in strat_metrics.items():
        strat_avgs[name] = {
            "sharpe": sum(r.get("sharpe", 0) for r in runs) / len(runs),
            "pnl_pct": sum(r.get("pnl_pct", 0) for r in runs) / len(runs),
            "win_rate": sum(r.get("win_rate", 0) for r in runs) / len(runs),
            "max_drawdown": min(r.get("max_drawdown", 0) for r in runs),
            "run_count": len(runs),
            "last_value": {
                "sharpe": runs[-1].get("sharpe", 0),
                "pnl_pct": runs[-1].get("pnl_pct", 0),
                "win_rate": runs[-1].get("win_rate", 0),
                "max_drawdown": runs[-1].get("max_drawdown", 0),
            }
        }

    triggered = []
    now = datetime.now(timezone.utc).isoformat()

    for rule in rules:
        sname = rule["strategy_name"]
        if sname not in strat_avgs:
            continue

        avg_data = strat_avgs[sname]
        metric_val = avg_data.get(rule["metric"], 0)
        latest_val = avg_data["last_value"].get(rule["metric"], 0)

        # Check against the latest run value
        if _compare(latest_val, rule["operator"], rule["threshold"]):
            metric_label = METRIC_LABELS.get(rule["metric"], rule["metric"])
            op_label = OPERATOR_LABELS.get(rule["operator"], rule["operator"])
            severity = "critical" if rule["metric"] in ("sharpe", "pnl_pct") and rule["operator"] in ("lt", "lte") else "warning"

            notif = {
                "notification_id": str(uuid.uuid4())[:12],
                "user_id": user_id,
                "alert_id": rule["alert_id"],
                "strategy_name": sname,
                "metric": rule["metric"],
                "metric_label": metric_label,
                "operator": rule["operator"],
                "operator_label": op_label,
                "threshold": rule["threshold"],
                "actual_value": round(latest_val, 4),
                "avg_value": round(metric_val, 4),
                "severity": severity,
                "message": f"{sname}: {metric_label} is {latest_val:.2f} ({op_label} {rule['threshold']})",
                "read": False,
                "triggered_at": now,
            }
            notifications_collection.insert_one(notif)
            notif.pop("_id", None)
            triggered.append(notif)

    # Send email notification if alerts triggered
    if triggered:
        try:
            import asyncio
            from email_service import send_email, alert_triggered_html, EMAIL_ENABLED
            if EMAIL_ENABLED:
                email = current_user.get("email")
                if email:
                    html = alert_triggered_html(triggered)
                    asyncio.ensure_future(send_email(email, f"{len(triggered)} Alert(s) Triggered — Text2trade", html))
        except Exception as e:
            logger.warning(f"Alert email failed: {e}")

    return {"triggered": len(triggered), "notifications": triggered}


@router.get("/alerts/notifications")
async def get_notifications(request: Request, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id", current_user.get("email"))
    notifs = list(notifications_collection.find(
        {"user_id": user_id}, {"_id": 0}
    ).sort("triggered_at", -1).limit(50))
    unread = sum(1 for n in notifs if not n.get("read"))
    return {"notifications": notifs, "count": len(notifs), "unread": unread}


@router.put("/alerts/notifications/{notification_id}/read")
async def mark_notification_read(request: Request, notification_id: str, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id", current_user.get("email"))
    result = notifications_collection.update_one(
        {"notification_id": notification_id, "user_id": user_id},
        {"$set": {"read": True}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"success": True}


@router.put("/alerts/notifications/read-all")
async def mark_all_read(request: Request, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id", current_user.get("email"))
    notifications_collection.update_many(
        {"user_id": user_id, "read": False},
        {"$set": {"read": True}}
    )
    return {"success": True}
