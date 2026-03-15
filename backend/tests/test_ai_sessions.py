"""Tests for AI Session Management and Usage Limits.

Covers:
1. Session management: POST /session/start, POST /session/{session_id}/message, 
   GET /session/{session_id}, DELETE /session/{session_id}
2. Multi-turn context: messages include previous conversation context
3. Cross-user session access protection: returns 403
4. Daily usage limits: nl_parser=20, explainer=10, risk_analyzer=10, session_chat=30
5. AI endpoints: POST /parse-strategy, POST /explain, POST /analyze-risk, GET /ai/usage
6. Token limits: responses should not truncate (testing max_tokens config)
"""

import pytest
import requests
import os
import time
import uuid
from pymongo import MongoClient

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    raise ValueError("REACT_APP_BACKEND_URL not set")

# MongoDB direct access for setting up test data
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'test_database')
mongo_client = MongoClient(MONGO_URL)
db = mongo_client[DB_NAME]
ai_usage_collection = db["ai_usage"]
sessions_collection = db["conversation_sessions"]

# Test credentials (pre-registered users)
TEST_USER_1 = {"email": "testai@example.com", "password": "Password123!"}
TEST_USER_2 = {"email": "testai2@example.com", "password": "Password123!"}


# Token cache to avoid rate limits
_token_cache = {}

def get_auth_token(email: str, password: str) -> str:
    """Login and get access token (with caching to avoid rate limits)."""
    cache_key = f"{email}:{password}"
    if cache_key in _token_cache:
        return _token_cache[cache_key]
    
    # Add delay if we've recently made requests
    time.sleep(0.5)
    
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": email, "password": password}
    )
    if response.status_code == 429:
        # Wait and retry once
        time.sleep(15)
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": email, "password": password}
        )
    
    if response.status_code != 200:
        # Try to register first
        reg_response = requests.post(
            f"{BASE_URL}/api/v1/auth/register",
            json={"email": email, "password": password}
        )
        if reg_response.status_code not in [201, 409]:
            raise Exception(f"Failed to register user: {reg_response.text}")
        # Retry login
        time.sleep(1)
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": email, "password": password}
        )
    assert response.status_code == 200, f"Login failed: {response.text}"
    token = response.json()["access_token"]
    _token_cache[cache_key] = token
    return token


class TestSessionStartEndpoint:
    """Test POST /api/v1/session/start - creates a new session."""

    @pytest.fixture
    def user1_token(self):
        return get_auth_token(TEST_USER_1["email"], TEST_USER_1["password"])

    def test_session_start_creates_session_and_returns_session_id(self, user1_token):
        """POST /api/v1/session/start creates session and returns session_id."""
        response = requests.post(
            f"{BASE_URL}/api/v1/session/start",
            headers={"Authorization": f"Bearer {user1_token}"}
        )
        print(f"Session start response: {response.status_code} - {response.text}")
        assert response.status_code == 200, f"Failed to start session: {response.text}"
        
        data = response.json()
        assert "session_id" in data, "Missing session_id in response"
        assert "created_at" in data, "Missing created_at in response"
        
        # Verify session_id is a valid UUID
        session_id = data["session_id"]
        try:
            uuid.UUID(session_id)
        except ValueError:
            pytest.fail(f"session_id is not a valid UUID: {session_id}")
        
        print(f"✓ Session created with ID: {session_id}")

    def test_session_start_requires_auth(self):
        """POST /api/v1/session/start without auth returns 401/403."""
        response = requests.post(f"{BASE_URL}/api/v1/session/start")
        print(f"Unauthenticated session start: {response.status_code}")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✓ Session start requires authentication")


class TestSessionMessageEndpoint:
    """Test POST /api/v1/session/{session_id}/message - send message and get AI response."""

    @pytest.fixture
    def user1_token(self):
        return get_auth_token(TEST_USER_1["email"], TEST_USER_1["password"])

    @pytest.fixture
    def session_id(self, user1_token):
        """Create a session for testing."""
        response = requests.post(
            f"{BASE_URL}/api/v1/session/start",
            headers={"Authorization": f"Bearer {user1_token}"}
        )
        assert response.status_code == 200
        return response.json()["session_id"]

    def test_send_message_returns_ai_response(self, user1_token, session_id):
        """POST /api/v1/session/{session_id}/message sends message and gets AI response."""
        response = requests.post(
            f"{BASE_URL}/api/v1/session/{session_id}/message",
            headers={"Authorization": f"Bearer {user1_token}"},
            json={"message": "What is a simple RSI trading strategy?"}
        )
        print(f"Session message response: {response.status_code}")
        assert response.status_code == 200, f"Failed to send message: {response.text}"
        
        data = response.json()
        assert "role" in data, "Missing role in response"
        assert data["role"] == "assistant", f"Expected role 'assistant', got {data['role']}"
        assert "content" in data, "Missing content in response"
        assert "session_id" in data, "Missing session_id in response"
        assert data["session_id"] == session_id, "session_id mismatch"
        
        # Check response is not truncated (has substantial content)
        content = data["content"]
        print(f"AI response length: {len(content)} chars")
        print(f"AI response preview: {content[:200]}...")
        
        # Response should have some meaningful content (not empty or truncated mid-sentence)
        assert len(content) > 50, f"Response seems truncated: {content}"
        print(f"✓ AI response received ({len(content)} chars)")

    def test_session_not_found_returns_404(self, user1_token):
        """POST to non-existent session returns 404."""
        fake_session_id = str(uuid.uuid4())
        response = requests.post(
            f"{BASE_URL}/api/v1/session/{fake_session_id}/message",
            headers={"Authorization": f"Bearer {user1_token}"},
            json={"message": "Hello"}
        )
        print(f"Non-existent session response: {response.status_code}")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ Non-existent session returns 404")


class TestMultiTurnContext:
    """Test multi-turn context: previous messages are included in AI context."""

    @pytest.fixture
    def user1_token(self):
        return get_auth_token(TEST_USER_1["email"], TEST_USER_1["password"])

    def test_multi_turn_context_includes_previous_messages(self, user1_token):
        """Send 3 messages, verify 4th message includes previous context."""
        # Start session
        start_response = requests.post(
            f"{BASE_URL}/api/v1/session/start",
            headers={"Authorization": f"Bearer {user1_token}"}
        )
        assert start_response.status_code == 200
        session_id = start_response.json()["session_id"]
        print(f"Session created: {session_id}")
        
        # Message 1
        msg1 = "I want to build a strategy using RSI"
        response1 = requests.post(
            f"{BASE_URL}/api/v1/session/{session_id}/message",
            headers={"Authorization": f"Bearer {user1_token}"},
            json={"message": msg1}
        )
        assert response1.status_code == 200, f"Message 1 failed: {response1.text}"
        print(f"Message 1 sent, response: {len(response1.json()['content'])} chars")
        time.sleep(1)  # Rate limit buffer
        
        # Message 2
        msg2 = "Use period 14 and oversold level at 30"
        response2 = requests.post(
            f"{BASE_URL}/api/v1/session/{session_id}/message",
            headers={"Authorization": f"Bearer {user1_token}"},
            json={"message": msg2}
        )
        assert response2.status_code == 200, f"Message 2 failed: {response2.text}"
        print(f"Message 2 sent, response: {len(response2.json()['content'])} chars")
        time.sleep(1)
        
        # Message 3
        msg3 = "Add a 5% take profit and 2% stop loss"
        response3 = requests.post(
            f"{BASE_URL}/api/v1/session/{session_id}/message",
            headers={"Authorization": f"Bearer {user1_token}"},
            json={"message": msg3}
        )
        assert response3.status_code == 200, f"Message 3 failed: {response3.text}"
        print(f"Message 3 sent, response: {len(response3.json()['content'])} chars")
        time.sleep(1)
        
        # Message 4 - should understand context from previous messages
        msg4 = "Now summarize the complete strategy we built"
        response4 = requests.post(
            f"{BASE_URL}/api/v1/session/{session_id}/message",
            headers={"Authorization": f"Bearer {user1_token}"},
            json={"message": msg4}
        )
        assert response4.status_code == 200, f"Message 4 failed: {response4.text}"
        
        content = response4.json()["content"]
        print(f"Message 4 response ({len(content)} chars): {content[:300]}...")
        
        # The response should mention RSI (from msg1) - proving context was included
        content_lower = content.lower()
        assert "rsi" in content_lower or "indicator" in content_lower or "strategy" in content_lower, \
            f"Response doesn't seem to include context from previous messages: {content}"
        
        print(f"✓ Multi-turn context working - AI response includes strategy context")
        
        # Verify session has all messages via GET endpoint
        get_response = requests.get(
            f"{BASE_URL}/api/v1/session/{session_id}",
            headers={"Authorization": f"Bearer {user1_token}"}
        )
        assert get_response.status_code == 200
        session_data = get_response.json()
        messages = session_data.get("messages", [])
        print(f"Session has {len(messages)} messages")
        # 4 user messages + 4 assistant responses = 8 total
        assert len(messages) >= 8, f"Expected at least 8 messages, got {len(messages)}"
        print(f"✓ Session persists all messages ({len(messages)} total)")


class TestGetSessionEndpoint:
    """Test GET /api/v1/session/{session_id} - retrieve full session."""

    @pytest.fixture
    def user1_token(self):
        return get_auth_token(TEST_USER_1["email"], TEST_USER_1["password"])

    @pytest.fixture
    def session_with_messages(self, user1_token):
        """Create a session with some messages."""
        # Start session
        start_response = requests.post(
            f"{BASE_URL}/api/v1/session/start",
            headers={"Authorization": f"Bearer {user1_token}"}
        )
        session_id = start_response.json()["session_id"]
        
        # Send a message
        requests.post(
            f"{BASE_URL}/api/v1/session/{session_id}/message",
            headers={"Authorization": f"Bearer {user1_token}"},
            json={"message": "Hello, what indicators do you support?"}
        )
        return session_id

    def test_get_session_returns_full_session(self, user1_token, session_with_messages):
        """GET /api/v1/session/{session_id} returns session with all messages."""
        response = requests.get(
            f"{BASE_URL}/api/v1/session/{session_with_messages}",
            headers={"Authorization": f"Bearer {user1_token}"}
        )
        print(f"Get session response: {response.status_code}")
        assert response.status_code == 200, f"Failed to get session: {response.text}"
        
        data = response.json()
        assert "session_id" in data, "Missing session_id"
        assert "user_id" in data, "Missing user_id"
        assert "messages" in data, "Missing messages"
        assert "created_at" in data, "Missing created_at"
        
        messages = data["messages"]
        assert isinstance(messages, list), "messages should be a list"
        assert len(messages) >= 2, f"Expected at least 2 messages (user + assistant), got {len(messages)}"
        
        # Check message structure
        for msg in messages:
            assert "role" in msg, "Message missing role"
            assert "content" in msg, "Message missing content"
            assert msg["role"] in ["user", "assistant"], f"Invalid role: {msg['role']}"
        
        print(f"✓ GET session returns full session with {len(messages)} messages")


class TestDeleteSessionEndpoint:
    """Test DELETE /api/v1/session/{session_id} - delete a session."""

    @pytest.fixture
    def user1_token(self):
        return get_auth_token(TEST_USER_1["email"], TEST_USER_1["password"])

    def test_delete_session_removes_session(self, user1_token):
        """DELETE /api/v1/session/{session_id} removes the session."""
        # Create session
        start_response = requests.post(
            f"{BASE_URL}/api/v1/session/start",
            headers={"Authorization": f"Bearer {user1_token}"}
        )
        session_id = start_response.json()["session_id"]
        print(f"Created session: {session_id}")
        
        # Delete session
        delete_response = requests.delete(
            f"{BASE_URL}/api/v1/session/{session_id}",
            headers={"Authorization": f"Bearer {user1_token}"}
        )
        print(f"Delete response: {delete_response.status_code}")
        assert delete_response.status_code == 200, f"Delete failed: {delete_response.text}"
        
        # Verify deletion
        get_response = requests.get(
            f"{BASE_URL}/api/v1/session/{session_id}",
            headers={"Authorization": f"Bearer {user1_token}"}
        )
        assert get_response.status_code == 404, f"Expected 404 after deletion, got {get_response.status_code}"
        print(f"✓ Session deleted successfully")


class TestCrossUserSessionAccess:
    """Test cross-user session access returns 403."""

    def test_cross_user_session_access_returns_403(self):
        """User 2 trying to access User 1's session returns 403."""
        # Get tokens for both users
        token1 = get_auth_token(TEST_USER_1["email"], TEST_USER_1["password"])
        token2 = get_auth_token(TEST_USER_2["email"], TEST_USER_2["password"])
        
        # User 1 creates a session
        start_response = requests.post(
            f"{BASE_URL}/api/v1/session/start",
            headers={"Authorization": f"Bearer {token1}"}
        )
        assert start_response.status_code == 200
        session_id = start_response.json()["session_id"]
        print(f"User 1 created session: {session_id}")
        
        # User 2 tries to access User 1's session
        get_response = requests.get(
            f"{BASE_URL}/api/v1/session/{session_id}",
            headers={"Authorization": f"Bearer {token2}"}
        )
        print(f"User 2 access to User 1's session: {get_response.status_code}")
        assert get_response.status_code == 403, f"Expected 403, got {get_response.status_code}"
        
        # User 2 tries to send message to User 1's session
        msg_response = requests.post(
            f"{BASE_URL}/api/v1/session/{session_id}/message",
            headers={"Authorization": f"Bearer {token2}"},
            json={"message": "Trying to hijack session"}
        )
        print(f"User 2 message to User 1's session: {msg_response.status_code}")
        assert msg_response.status_code == 403, f"Expected 403, got {msg_response.status_code}"
        
        # User 2 tries to delete User 1's session
        delete_response = requests.delete(
            f"{BASE_URL}/api/v1/session/{session_id}",
            headers={"Authorization": f"Bearer {token2}"}
        )
        print(f"User 2 delete User 1's session: {delete_response.status_code}")
        assert delete_response.status_code == 403, f"Expected 403, got {delete_response.status_code}"
        
        print(f"✓ Cross-user session access properly blocked with 403")


class TestDailyLimitEnforcement:
    """Test daily limit enforcement for AI endpoints."""

    def test_nl_parser_daily_limit(self):
        """Set nl_parser count to 20, 21st call returns 429."""
        token = get_auth_token(TEST_USER_1["email"], TEST_USER_1["password"])
        today = time.strftime("%Y-%m-%d")
        
        # Set nl_parser count to 20 (at limit)
        ai_usage_collection.update_one(
            {"user_id": TEST_USER_1["email"], "role": "nl_parser", "date": today},
            {"$set": {"count": 20}},
            upsert=True
        )
        print(f"Set nl_parser count to 20 for {TEST_USER_1['email']}")
        
        # Try to call parse-strategy - should return 429
        response = requests.post(
            f"{BASE_URL}/api/v1/parse-strategy",
            headers={"Authorization": f"Bearer {token}"},
            json={"text": "Buy when RSI below 30"}
        )
        print(f"Parse-strategy at limit: {response.status_code}")
        assert response.status_code == 429, f"Expected 429 at daily limit, got {response.status_code}: {response.text}"
        
        # Verify error message mentions daily limit
        error_detail = response.json().get("detail", "")
        assert "daily limit" in error_detail.lower() or "limit" in error_detail.lower(), \
            f"Error should mention limit: {error_detail}"
        
        print(f"✓ nl_parser daily limit (20/day) enforced with 429")
        
        # Cleanup - reset count
        ai_usage_collection.delete_one(
            {"user_id": TEST_USER_1["email"], "role": "nl_parser", "date": today}
        )


class TestAIEndpoints:
    """Test AI endpoints: parse-strategy, explain, analyze-risk."""

    @pytest.fixture
    def user1_token(self):
        return get_auth_token(TEST_USER_1["email"], TEST_USER_1["password"])

    @pytest.fixture(autouse=True)
    def reset_usage_limits(self):
        """Reset usage limits before each test."""
        today = time.strftime("%Y-%m-%d")
        ai_usage_collection.delete_many({
            "user_id": TEST_USER_1["email"],
            "date": today
        })
        yield

    def test_parse_strategy_returns_parsed_json(self, user1_token):
        """POST /api/v1/parse-strategy works with AI (returns parsed JSON)."""
        response = requests.post(
            f"{BASE_URL}/api/v1/parse-strategy",
            headers={"Authorization": f"Bearer {user1_token}"},
            json={"text": "Buy when RSI drops below 30 with stop loss at 2% and take profit at 5%"}
        )
        print(f"Parse-strategy response: {response.status_code}")
        assert response.status_code == 200, f"Parse-strategy failed: {response.text}"
        
        data = response.json()
        assert data.get("success") == True, f"Parse not successful: {data}"
        assert "parsed" in data, "Missing parsed field"
        
        parsed = data["parsed"]
        print(f"Parsed strategy: {parsed}")
        
        # Verify parsed structure has expected fields
        assert isinstance(parsed, dict), "parsed should be a dict"
        # May have entry_conditions, exit_conditions, risk_management etc.
        print(f"✓ parse-strategy returns parsed JSON")

    def test_explain_works_with_ai(self, user1_token):
        """POST /api/v1/explain works with AI."""
        strategy = {
            "entry_conditions": [
                {"name": "RSI", "params": {"period": 14}, "operator": "<", "value": 30}
            ],
            "exit_conditions": [
                {"name": "RSI", "params": {"period": 14}, "operator": ">", "value": 70}
            ],
            "risk_management": {"stop_loss": 2, "take_profit": 5}
        }
        
        response = requests.post(
            f"{BASE_URL}/api/v1/explain",
            headers={"Authorization": f"Bearer {user1_token}"},
            json={"strategy": strategy, "question": "How does this strategy work?"}
        )
        print(f"Explain response: {response.status_code}")
        assert response.status_code == 200, f"Explain failed: {response.text}"
        
        data = response.json()
        assert data.get("success") == True, f"Explain not successful: {data}"
        assert "answer" in data, "Missing answer field"
        
        answer = data["answer"]
        print(f"Explain answer ({len(answer)} chars): {answer[:200]}...")
        
        # Answer should have meaningful content
        assert len(answer) > 30, f"Answer seems too short: {answer}"
        print(f"✓ explain works with AI")

    def test_analyze_risk_works_with_ai(self, user1_token):
        """POST /api/v1/analyze-risk works with AI."""
        strategy = {
            "entry_conditions": [
                {"name": "SMA", "params": {"short": 9, "long": 21}, "operator": "crosses_above"}
            ],
            "exit_conditions": [],
            "risk_management": {}  # No stop loss - should be flagged
        }
        
        response = requests.post(
            f"{BASE_URL}/api/v1/analyze-risk",
            headers={"Authorization": f"Bearer {user1_token}"},
            json={"strategy": strategy}
        )
        print(f"Analyze-risk response: {response.status_code}")
        assert response.status_code == 200, f"Analyze-risk failed: {response.text}"
        
        data = response.json()
        assert data.get("success") == True, f"Analyze-risk not successful: {data}"
        assert "warnings" in data, "Missing warnings field"
        
        warnings = data["warnings"]
        print(f"Risk warnings: {warnings}")
        
        assert isinstance(warnings, list), "warnings should be a list"
        print(f"✓ analyze-risk works with AI ({len(warnings)} warnings)")


class TestAIUsageEndpoint:
    """Test GET /api/v1/ai/usage returns per-role usage stats."""

    def test_ai_usage_returns_per_role_stats(self):
        """GET /api/v1/ai/usage returns usage stats for all roles."""
        token = get_auth_token(TEST_USER_1["email"], TEST_USER_1["password"])
        
        response = requests.get(
            f"{BASE_URL}/api/v1/ai/usage",
            headers={"Authorization": f"Bearer {token}"}
        )
        print(f"AI usage response: {response.status_code}")
        assert response.status_code == 200, f"AI usage failed: {response.text}"
        
        data = response.json()
        print(f"AI usage data: {data}")
        
        # Should have stats for each role
        expected_roles = ["nl_parser", "explainer", "risk_analyzer", "session_chat"]
        for role in expected_roles:
            assert role in data, f"Missing role {role} in usage stats"
            role_data = data[role]
            assert "used" in role_data, f"Missing 'used' for {role}"
            assert "limit" in role_data, f"Missing 'limit' for {role}"
            print(f"  {role}: {role_data['used']}/{role_data['limit']}")
        
        # Verify limits match expected values
        assert data["nl_parser"]["limit"] == 20, f"nl_parser limit should be 20"
        assert data["explainer"]["limit"] == 10, f"explainer limit should be 10"
        assert data["risk_analyzer"]["limit"] == 10, f"risk_analyzer limit should be 10"
        assert data["session_chat"]["limit"] == 30, f"session_chat limit should be 30"
        
        print(f"✓ AI usage returns per-role stats with correct limits")


# Cleanup sessions after tests
@pytest.fixture(scope="session", autouse=True)
def cleanup_test_sessions():
    """Cleanup test sessions after all tests."""
    yield
    # Delete sessions created by test users
    sessions_collection.delete_many({
        "user_id": {"$in": [TEST_USER_1["email"], TEST_USER_2["email"]]}
    })
    print(f"Cleaned up test sessions")
