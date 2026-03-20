"""Shared database connections, collections, and in-memory state."""
import os
import logging
from pymongo import MongoClient

logger = logging.getLogger(__name__)

# MongoDB connection
mongo_client = MongoClient(os.environ.get("MONGO_URL"), serverSelectionTimeoutMS=5000)
db = mongo_client[os.environ.get("DB_NAME", "text2trade")]
strategies_collection = db["strategies"]
templates_collection = db["strategy_templates"]

# Create indexes
try:
    strategies_collection.create_index("user_id")
    strategies_collection.create_index("metadata.created_at")
except Exception as e:
    logger.warning(f"Could not create indexes: {e}")

# In-memory analytics
analytics_db = {
    "strategies_created": 0,
    "backtests_run": 0,
    "indicator_usage": {},
    "backtest_types": {"historical": 0},
}

feedback_db: list = []
waitlist_db: list = []
screener_analytics = {"preset_runs": {}, "symbol_scans": {}}


def track_indicator(indicator_name: str):
    if indicator_name not in analytics_db["indicator_usage"]:
        analytics_db["indicator_usage"][indicator_name] = 0
    analytics_db["indicator_usage"][indicator_name] += 1
