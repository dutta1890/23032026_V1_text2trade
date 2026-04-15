"""Daily session cleanup — SEBI requirement: auto-logout before market pre-open.

Runs at 8:30 AM IST (3:00 UTC) on trading days (Mon-Fri).
Cron: 0 3 * * 1-5

Usage:
    python scripts/daily_session_cleanup.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from datetime import datetime, timezone
from database import db
from audit import log_audit

sessions_collection = db["ai_sessions"]
blacklisted_tokens = db["blacklisted_tokens"]


def cleanup():
    """Expire all active sessions and log to audit trail."""
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    # 1. Mark all active AI conversation sessions as expired
    active = sessions_collection.find({"status": "active"}, {"_id": 0, "session_id": 1, "user_id": 1})
    expired_count = 0
    for sess in active:
        sessions_collection.update_one(
            {"session_id": sess["session_id"]},
            {"$set": {"status": "expired", "expired_at": now_iso, "expired_by": "daily_cleanup"}},
        )
        expired_count += 1

    # 2. Phase 2 placeholder: disconnect all broker API sessions
    # broker_sessions_collection.update_many(
    #     {"status": "connected"},
    #     {"$set": {"status": "disconnected", "disconnected_at": now_iso, "reason": "daily_cleanup"}},
    # )

    # 3. Log to audit trail
    log_audit(
        user_id="system",
        action="session_started",
        details={
            "type": "daily_session_cleanup",
            "sessions_expired": expired_count,
            "cleanup_time": now_iso,
            "reason": "SEBI pre-market session reset",
        },
        ip_address="server",
        user_agent="daily_cleanup_cron",
    )

    print(f"[{now_iso}] Daily cleanup: {expired_count} sessions expired")
    return expired_count


if __name__ == "__main__":
    cleanup()
