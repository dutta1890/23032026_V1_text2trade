"""Migrate old flat risk_management schema to new structured schema.

Old format:
    { "stop_loss": 5.0, "take_profit": 10.0, "trailing_stop": 2.0, ... }

New format:
    { "stop_loss": {"type": "percentage", "value": 5.0},
      "target_profit": {"type": "percentage", "value": 10.0},
      "trailing_stop_loss": {"enabled": true, "type": "percentage", "value": 2.0, "activation_profit": 0},
      "time_based_exit": {"enabled": false, "exit_time": "15:10"},
      "daily_limits": {"max_loss_per_day": 5.0, "max_trades_per_day": 10},
      "position_sizing": {"method": "fixed_quantity", "value": 1} }
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from pymongo import MongoClient

MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME", "test_database")


def migrate_risk_schema():
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    strategies = db.strategies

    cursor = strategies.find({})
    migrated = 0
    skipped = 0

    for doc in cursor:
        rm = doc.get("risk_management", {})
        if rm is None:
            rm = {}

        # Detect if already new format (has "stop_loss" as dict or null)
        sl = rm.get("stop_loss")
        if isinstance(sl, dict) or (sl is None and "trailing_stop_loss" in rm):
            skipped += 1
            continue

        # Old format: flat fields
        old_sl = rm.get("stop_loss")
        old_tp = rm.get("take_profit")
        old_trailing = rm.get("trailing_stop")
        old_sl_type = rm.get("stop_loss_type", "fixed")

        new_rm = {}

        # Stop loss
        if old_sl is not None and old_sl > 0:
            sl_type = "atr_multiple" if old_sl_type == "atr" else "percentage"
            new_rm["stop_loss"] = {"type": sl_type, "value": float(old_sl)}
        else:
            new_rm["stop_loss"] = None

        # Target profit
        if old_tp is not None and old_tp > 0:
            new_rm["target_profit"] = {"type": "percentage", "value": float(old_tp)}
        else:
            new_rm["target_profit"] = None

        # Trailing SL
        if old_trailing and old_trailing > 0:
            new_rm["trailing_stop_loss"] = {
                "enabled": True,
                "type": "percentage",
                "value": float(old_trailing),
                "activation_profit": 0,
            }
        else:
            new_rm["trailing_stop_loss"] = {
                "enabled": False,
                "type": "percentage",
                "value": 1.0,
                "activation_profit": 0,
            }

        # Defaults
        new_rm["time_based_exit"] = {"enabled": False, "exit_time": "15:10"}

        max_loss = rm.get("max_daily_loss", 5.0) or 5.0
        new_rm["daily_limits"] = {"max_loss_per_day": max_loss, "max_trades_per_day": 10}

        pos_size = rm.get("position_size")
        pos_type = rm.get("position_size_type", "fixed_quantity")
        if pos_type not in ("fixed_quantity", "percent_capital", "risk_per_trade"):
            pos_type = "fixed_quantity"
        new_rm["position_sizing"] = {
            "method": pos_type,
            "value": float(pos_size) if pos_size and pos_size > 0 else 1,
        }

        strategies.update_one(
            {"_id": doc["_id"]},
            {"$set": {"risk_management": new_rm}},
        )
        migrated += 1

    print(f"Migration complete: {migrated} migrated, {skipped} already new format.")
    client.close()


if __name__ == "__main__":
    migrate_risk_schema()
