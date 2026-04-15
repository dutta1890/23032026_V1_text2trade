"""OPS (Orders Per Second) monitoring for SEBI compliance."""

import logging
from datetime import datetime, timezone, timedelta
from database import db
from config import SEBI_COMPLIANCE

logger = logging.getLogger(__name__)

ops_collection = db["ops_logs"]

try:
    ops_collection.create_index([("user_id", 1), ("timestamp", -1)])
    ops_collection.create_index([("timestamp", -1)])
except Exception:
    pass

OPS_THRESHOLD = SEBI_COMPLIANCE["ops_threshold"]


def record_order(user_id: str, exchange: str = "paper"):
    """Record a single order event for OPS tracking."""
    ops_collection.insert_one({
        "user_id": user_id,
        "exchange": exchange,
        "timestamp": datetime.now(timezone.utc),
    })


def get_current_ops(user_id: str, exchange: str = "paper") -> float:
    """Calculate orders per second over the last 60 seconds."""
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=60)
    count = ops_collection.count_documents({
        "user_id": user_id,
        "exchange": exchange,
        "timestamp": {"$gte": cutoff},
    })
    return round(count / 60.0, 4)


def is_above_threshold(user_id: str, exchange: str = "paper") -> bool:
    """Check if a user's OPS exceeds SEBI threshold."""
    return get_current_ops(user_id, exchange) > OPS_THRESHOLD


def get_ops_history(user_id: str, period: str = "1h") -> list:
    """Get OPS snapshots over a period."""
    periods = {"1h": 1, "6h": 6, "24h": 24, "7d": 168}
    hours = periods.get(period, 1)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    pipeline = [
        {"$match": {"user_id": user_id, "timestamp": {"$gte": cutoff}}},
        {"$group": {
            "_id": {
                "$dateTrunc": {"date": "$timestamp", "unit": "minute"}
            },
            "count": {"$sum": 1},
            "exchange": {"$first": "$exchange"},
        }},
        {"$sort": {"_id": 1}},
        {"$project": {
            "_id": 0,
            "timestamp": {"$dateToString": {"format": "%Y-%m-%dT%H:%M:%SZ", "date": "$_id"}},
            "orders": "$count",
            "ops": {"$divide": ["$count", 60]},
            "exchange": 1,
        }},
    ]
    return list(ops_collection.aggregate(pipeline))


def get_all_users_ops_summary() -> list:
    """Admin: get OPS summary for all users with recent activity."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
    pipeline = [
        {"$match": {"timestamp": {"$gte": cutoff}}},
        {"$group": {
            "_id": "$user_id",
            "total_orders": {"$sum": 1},
            "last_order": {"$max": "$timestamp"},
            "exchange": {"$last": "$exchange"},
        }},
        {"$project": {
            "_id": 0,
            "user_id": "$_id",
            "total_orders_1h": "$total_orders",
            "avg_ops": {"$round": [{"$divide": ["$total_orders", 3600]}, 4]},
            "last_order": {"$dateToString": {"format": "%Y-%m-%dT%H:%M:%SZ", "date": "$last_order"}},
            "exchange": 1,
            "above_threshold": {"$gt": [{"$divide": ["$total_orders", 3600]}, OPS_THRESHOLD]},
        }},
        {"$sort": {"total_orders_1h": -1}},
    ]
    return list(ops_collection.aggregate(pipeline))
