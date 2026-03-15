"""AI usage tracking and conversation session management."""

import os
import logging
from datetime import datetime, timezone
from typing import List, Optional
from pymongo import MongoClient, ASCENDING

logger = logging.getLogger(__name__)

# MongoDB connection
_client = MongoClient(os.environ.get("MONGO_URL"))
_db = _client[os.environ.get("DB_NAME", "text2trade")]

# ai_usage collection: per-user per-role daily limits
ai_usage_collection = _db["ai_usage"]
ai_usage_collection.create_index([("user_id", 1), ("role", 1), ("date", 1)], unique=True)

# conversation_sessions collection
sessions_collection = _db["conversation_sessions"]
sessions_collection.create_index("user_id")
sessions_collection.create_index("updated_at", expireAfterSeconds=86400)  # TTL 24h

# Role-specific token and daily limits
# Note: GPT-5.2 only supports temperature=1
AI_CONFIG = {
    "nl_parser": {"max_tokens": 800, "temperature": 1, "daily_limit": 20},
    "explainer": {"max_tokens": 400, "temperature": 1, "daily_limit": 10},
    "risk_analyzer": {"max_tokens": 400, "temperature": 1, "daily_limit": 10},
    "session_chat": {"max_tokens": 600, "temperature": 1, "daily_limit": 30},
}


def get_ai_config(role: str) -> dict:
    """Get token/temperature config for an AI role."""
    return AI_CONFIG.get(role, {"max_tokens": 400, "temperature": 0.2, "daily_limit": 10})


def check_and_increment_usage(user_id: str, role: str) -> bool:
    """Check if user is within daily limit for a role. Increments count if allowed.
    Returns True if allowed, False if limit exceeded.
    """
    config = get_ai_config(role)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    doc = ai_usage_collection.find_one_and_update(
        {"user_id": user_id, "role": role, "date": today},
        {"$inc": {"count": 1}, "$setOnInsert": {"user_id": user_id, "role": role, "date": today}},
        upsert=True,
        return_document=True,  # return after update
    )

    # doc["count"] is already incremented; check against limit
    if doc and doc.get("count", 0) > config["daily_limit"]:
        # Undo the increment
        ai_usage_collection.update_one(
            {"user_id": user_id, "role": role, "date": today},
            {"$inc": {"count": -1}},
        )
        return False
    return True


def get_usage_stats(user_id: str) -> dict:
    """Get today's usage stats for a user."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    stats = {}
    for role, config in AI_CONFIG.items():
        doc = ai_usage_collection.find_one(
            {"user_id": user_id, "role": role, "date": today},
            {"_id": 0},
        )
        stats[role] = {
            "used": doc["count"] if doc else 0,
            "limit": config["daily_limit"],
        }
    return stats


# =============================================================================
# SESSION MANAGEMENT
# =============================================================================

def create_session(user_id: str) -> dict:
    """Create a new conversation session."""
    import uuid
    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    doc = {
        "session_id": session_id,
        "user_id": user_id,
        "messages": [],
        "strategy_draft": None,
        "created_at": now,
        "updated_at": now,
    }
    sessions_collection.insert_one(doc)
    return {"session_id": session_id, "created_at": now.isoformat()}


def get_session(session_id: str, user_id: str) -> Optional[dict]:
    """Get a session. Returns None if not found or not owned by user."""
    doc = sessions_collection.find_one(
        {"session_id": session_id},
        {"_id": 0},
    )
    if not doc:
        return None
    if doc["user_id"] != user_id:
        return "forbidden"
    # Convert datetimes to ISO strings for JSON
    doc["created_at"] = doc["created_at"].isoformat() if doc.get("created_at") else None
    doc["updated_at"] = doc["updated_at"].isoformat() if doc.get("updated_at") else None
    for msg in doc.get("messages", []):
        if isinstance(msg.get("timestamp"), datetime):
            msg["timestamp"] = msg["timestamp"].isoformat()
    return doc


def append_message(session_id: str, user_id: str, role: str, content: str) -> bool:
    """Append a message to a session. Returns True if successful."""
    now = datetime.now(timezone.utc)
    result = sessions_collection.update_one(
        {"session_id": session_id, "user_id": user_id},
        {
            "$push": {"messages": {"role": role, "content": content, "timestamp": now}},
            "$set": {"updated_at": now},
        },
    )
    return result.modified_count > 0


def update_strategy_draft(session_id: str, user_id: str, draft: dict):
    """Update the strategy draft in a session."""
    sessions_collection.update_one(
        {"session_id": session_id, "user_id": user_id},
        {"$set": {"strategy_draft": draft, "updated_at": datetime.now(timezone.utc)}},
    )


def delete_session(session_id: str, user_id: str) -> bool:
    """Delete a session. Returns True if deleted."""
    result = sessions_collection.delete_one({"session_id": session_id, "user_id": user_id})
    return result.deleted_count > 0


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token."""
    return len(text) // 4 + 1


def get_context_messages(session_id: str, user_id: str, max_messages: int = 6, token_budget: int = 500) -> List[dict]:
    """Get last N messages for context window, trimmed to fit token_budget.
    Returns list of {role, content}. Trims oldest messages first if over budget.
    """
    doc = sessions_collection.find_one(
        {"session_id": session_id, "user_id": user_id},
        {"_id": 0, "messages": 1},
    )
    if not doc or not doc.get("messages"):
        return []

    messages = doc["messages"][-max_messages:]
    result = [{"role": m["role"], "content": m["content"]} for m in messages]

    # Trim oldest messages until total fits within token_budget
    total_tokens = sum(estimate_tokens(m["content"]) for m in result)
    while total_tokens > token_budget and len(result) > 1:
        removed = result.pop(0)
        total_tokens -= estimate_tokens(removed["content"])

    return result
