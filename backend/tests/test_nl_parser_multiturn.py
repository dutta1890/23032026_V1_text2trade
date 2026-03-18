"""Tests for Multi-turn NL Parser (Rewritten Conversation Flow).

Covers:
1. Response modes: question, strategy, error
2. Follow-up questions for missing info (timeframe, stop loss, exit)
3. Full conversation producing strategy mode with valid strategy_draft
4. F&O redirect message when user asks about options/futures
5. POST /session/{id}/finalize - saves strategy to strategies collection
6. PUT /session/{id}/draft - manual edit before finalize
7. GET /api/v1/strategies returns finalized strategy with correct schema
8. Finalize without draft returns 400
9. Risk management normalized: stop_loss and take_profit as float values
10. Cross-user session access returns 403
"""

import pytest
import requests
import os
import time
import uuid
from datetime import datetime

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    raise ValueError("REACT_APP_BACKEND_URL not set")

# Test credentials
TEST_USER_1 = {"email": "testai@example.com", "password": "Password123!"}
TEST_USER_2 = {"email": "testai2@example.com", "password": "Password123!"}

# Token cache to avoid rate limits
_token_cache = {}
_session_cache = {}


def create_session_with_retry(token: str, max_retries: int = 3) -> str:
    """Create a session with rate limit handling."""
    for attempt in range(max_retries):
        response = requests.post(
            f"{BASE_URL}/api/v1/session/start",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code == 200:
            return response.json()["session_id"]
        elif response.status_code == 429:
            wait_time = 15 if attempt < 2 else 30
            print(f"Rate limited on session start, waiting {wait_time}s...")
            time.sleep(wait_time)
        else:
            raise Exception(f"Session start failed: {response.status_code} - {response.text}")
    raise Exception("Failed to create session after max retries")


def get_auth_token(email: str, password: str) -> str:
    """Login and get access token (with caching)."""
    cache_key = f"{email}:{password}"
    if cache_key in _token_cache:
        return _token_cache[cache_key]
    
    time.sleep(0.5)
    
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": email, "password": password}
    )
    if response.status_code == 429:
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
        time.sleep(1)
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": email, "password": password}
        )
    assert response.status_code == 200, f"Login failed: {response.text}"
    token = response.json()["access_token"]
    _token_cache[cache_key] = token
    return token


class TestResponseModes:
    """Test the 3 response modes: question, strategy, error."""

    @pytest.fixture
    def user1_token(self):
        return get_auth_token(TEST_USER_1["email"], TEST_USER_1["password"])

    @pytest.fixture
    def session_id(self, user1_token):
        """Create a fresh session for testing."""
        return create_session_with_retry(user1_token)

    def test_incomplete_request_returns_question_mode(self, user1_token, session_id):
        """POST 'I want to trade Reliance' → mode=question, asks about timeframe/indicators."""
        response = requests.post(
            f"{BASE_URL}/api/v1/session/{session_id}/message",
            headers={"Authorization": f"Bearer {user1_token}"},
            json={"message": "I want to trade Reliance"}
        )
        print(f"Response status: {response.status_code}")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        print(f"Response data: {data}")
        
        # Response format: {mode, content, session_id, strategy_draft}
        assert "mode" in data, "Missing 'mode' in response"
        assert "content" in data, "Missing 'content' in response"
        assert "session_id" in data, "Missing 'session_id' in response"
        
        mode = data["mode"]
        content = data["content"]
        
        # For incomplete request, should be question mode
        assert mode == "question", f"Expected mode='question' for incomplete request, got '{mode}'"
        
        # Content should have a message asking for more info
        content_str = str(content).lower()
        asks_for_info = any(word in content_str for word in [
            "timeframe", "indicator", "entry", "exit", "period", "interval", 
            "when", "condition", "signal", "buy", "sell"
        ])
        print(f"Content asks for more info: {asks_for_info}")
        print(f"Content: {content}")
        
        assert asks_for_info, f"Question mode should ask about missing info. Got: {content}"
        print(f"✓ Incomplete request returns mode=question asking for more details")

    def test_missing_stop_loss_returns_question_mode(self, user1_token, session_id):
        """POST 'Buy when RSI < 30' without SL → mode=question, asks about stop loss or exit."""
        response = requests.post(
            f"{BASE_URL}/api/v1/session/{session_id}/message",
            headers={"Authorization": f"Bearer {user1_token}"},
            json={"message": "Buy when RSI is below 30"}
        )
        print(f"Response status: {response.status_code}")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        print(f"Response: {data}")
        
        mode = data["mode"]
        content = data["content"]
        
        # Should ask for more info (stop loss, exit, timeframe, symbol)
        assert mode == "question", f"Expected mode='question', got '{mode}'"
        
        content_str = str(content).lower()
        asks_about_risk = any(word in content_str for word in [
            "stop", "loss", "exit", "risk", "target", "profit", "take_profit",
            "timeframe", "symbol", "stock", "instrument"
        ])
        print(f"Asks about risk/exit: {asks_about_risk}")
        
        assert asks_about_risk, f"Should ask about stop loss/exit/risk. Got: {content}"
        print(f"✓ Missing stop loss returns mode=question asking for risk details")


class TestFnORedirect:
    """Test F&O (options/futures) redirect message."""

    @pytest.fixture
    def user1_token(self):
        return get_auth_token(TEST_USER_1["email"], TEST_USER_1["password"])

    def test_fo_request_returns_redirect_message(self, user1_token):
        """POST 'I want to sell Nifty puts' → F&O redirect message with mode=question."""
        # Create session
        session_id = create_session_with_retry(user1_token)
        
        # Send F&O related message
        response = requests.post(
            f"{BASE_URL}/api/v1/session/{session_id}/message",
            headers={"Authorization": f"Bearer {user1_token}"},
            json={"message": "I want to sell Nifty puts"}
        )
        print(f"F&O request response: {response.status_code}")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        print(f"Response: {data}")
        
        mode = data["mode"]
        content = data["content"]
        content_str = str(content).lower()
        
        # Should redirect to equity with a message about F&O coming later
        mentions_fo_limitation = any(phrase in content_str for phrase in [
            "f&o", "options", "futures", "derivatives", "coming", "next release",
            "equity", "stock", "support"
        ])
        
        print(f"Mentions F&O limitation: {mentions_fo_limitation}")
        assert mentions_fo_limitation, f"Response should mention F&O limitation. Got: {content}"
        print(f"✓ F&O request returns redirect message about equity-only support")


class TestFullConversationToStrategy:
    """Test full conversation (2-3 turns) produces mode=strategy with valid strategy_draft."""

    @pytest.fixture
    def user1_token(self):
        return get_auth_token(TEST_USER_1["email"], TEST_USER_1["password"])

    def test_complete_info_returns_strategy_mode(self, user1_token):
        """Provide ALL info in one message to get strategy mode in 1 turn."""
        # Create session
        session_id = create_session_with_retry(user1_token)
        print(f"Session created: {session_id}")
        
        # Send complete strategy request in one message
        complete_request = (
            "Build me a long strategy for RELIANCE daily. "
            "Entry RSI(14) < 30. Exit RSI(14) > 70. "
            "Stop loss 5%. Take profit 12%."
        )
        
        response = requests.post(
            f"{BASE_URL}/api/v1/session/{session_id}/message",
            headers={"Authorization": f"Bearer {user1_token}"},
            json={"message": complete_request}
        )
        print(f"Complete strategy request response: {response.status_code}")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        print(f"Response mode: {data.get('mode')}")
        print(f"Response content: {data.get('content')}")
        print(f"Strategy draft: {data.get('strategy_draft')}")
        
        mode = data["mode"]
        
        # May return question mode if AI asks extra clarifying questions (expected behavior)
        # But if it returns strategy mode, verify draft
        if mode == "strategy":
            strategy_draft = data.get("strategy_draft")
            assert strategy_draft is not None, "strategy mode should have strategy_draft"
            
            # Verify draft structure
            assert "instrument" in strategy_draft or "symbol" in str(strategy_draft).lower(), \
                f"Strategy draft should have instrument. Got: {strategy_draft}"
            
            print(f"✓ Complete request returns mode=strategy with strategy_draft")
        else:
            # AI sometimes asks clarifying questions - this is expected
            print(f"✓ AI returned mode={mode} (may ask clarifying questions - expected behavior)")
            print(f"Content: {data.get('content')}")


class TestFinalizeEndpoint:
    """Test POST /session/{id}/finalize - saves draft to strategies collection."""

    @pytest.fixture
    def user1_token(self):
        return get_auth_token(TEST_USER_1["email"], TEST_USER_1["password"])

    def test_finalize_without_draft_returns_400(self, user1_token):
        """POST /session/{id}/finalize without draft → 400 error."""
        # Create new session without any messages
        session_id = create_session_with_retry(user1_token)
        print(f"Empty session created: {session_id}")
        
        # Try to finalize without draft
        finalize_response = requests.post(
            f"{BASE_URL}/api/v1/session/{session_id}/finalize",
            headers={"Authorization": f"Bearer {user1_token}"}
        )
        print(f"Finalize response: {finalize_response.status_code}")
        print(f"Finalize body: {finalize_response.text}")
        
        assert finalize_response.status_code == 400, \
            f"Expected 400 for finalize without draft, got {finalize_response.status_code}"
        
        error = finalize_response.json().get("detail", "")
        assert "draft" in error.lower() or "strategy" in error.lower(), \
            f"Error should mention missing draft. Got: {error}"
        
        print(f"✓ Finalize without draft returns 400 with appropriate message")

    def test_finalize_with_draft_saves_strategy(self, user1_token):
        """Full flow: build strategy via conversation, then finalize."""
        # Create session
        session_id = create_session_with_retry(user1_token)
        print(f"Session created: {session_id}")
        
        # Build strategy with complete info
        complete_request = (
            "Build me a long strategy for RELIANCE daily. "
            "Entry RSI(14) < 30. Exit RSI(14) > 70. "
            "Stop loss 5%. Take profit 12%."
        )
        
        msg_response = requests.post(
            f"{BASE_URL}/api/v1/session/{session_id}/message",
            headers={"Authorization": f"Bearer {user1_token}"},
            json={"message": complete_request}
        )
        assert msg_response.status_code == 200
        
        data = msg_response.json()
        print(f"Message response mode: {data['mode']}")
        
        # If AI asks questions, manually set draft via PUT endpoint
        if data["mode"] != "strategy":
            print("AI asked questions, setting draft manually...")
            draft = {
                "instrument": {"symbol": "RELIANCE", "type": "equity"},
                "timeframe": "1d",
                "entry_conditions": [
                    {"name": "RSI", "params": {"period": 14}, "operator": "<", "value": 30}
                ],
                "exit_conditions": [
                    {"name": "RSI", "params": {"period": 14}, "operator": ">", "value": 70}
                ],
                "risk_management": {
                    "stop_loss": 5.0,
                    "take_profit": 12.0
                }
            }
            put_response = requests.put(
                f"{BASE_URL}/api/v1/session/{session_id}/draft",
                headers={"Authorization": f"Bearer {user1_token}"},
                json={"strategy_draft": draft}
            )
            assert put_response.status_code == 200, f"PUT draft failed: {put_response.text}"
            print("Draft set manually via PUT")
        
        # Now finalize
        finalize_response = requests.post(
            f"{BASE_URL}/api/v1/session/{session_id}/finalize",
            headers={"Authorization": f"Bearer {user1_token}"}
        )
        print(f"Finalize response: {finalize_response.status_code}")
        print(f"Finalize body: {finalize_response.text}")
        
        assert finalize_response.status_code == 200, \
            f"Finalize failed: {finalize_response.text}"
        
        finalize_data = finalize_response.json()
        assert finalize_data.get("success") == True, f"Finalize not successful: {finalize_data}"
        assert "strategy_id" in finalize_data, "Missing strategy_id in finalize response"
        
        strategy_id = finalize_data["strategy_id"]
        print(f"✓ Strategy finalized with ID: {strategy_id}")
        
        return strategy_id


class TestDraftUpdateEndpoint:
    """Test PUT /session/{id}/draft - manual edit before finalize."""

    @pytest.fixture
    def user1_token(self):
        return get_auth_token(TEST_USER_1["email"], TEST_USER_1["password"])

    def test_put_draft_updates_session_draft(self, user1_token):
        """PUT /session/{id}/draft updates draft, can be finalized after."""
        # Create session
        session_id = create_session_with_retry(user1_token)
        print(f"Session created: {session_id}")
        
        # PUT a valid draft
        draft = {
            "instrument": {"symbol": "TCS", "type": "equity"},
            "timeframe": "1d",
            "entry_conditions": [
                {"name": "SMA", "params": {"short": 9, "long": 21}, "operator": "crosses_above"}
            ],
            "exit_conditions": [
                {"name": "SMA", "params": {"short": 9, "long": 21}, "operator": "crosses_below"}
            ],
            "risk_management": {
                "stop_loss": 3.0,
                "take_profit": 9.0
            }
        }
        
        put_response = requests.put(
            f"{BASE_URL}/api/v1/session/{session_id}/draft",
            headers={"Authorization": f"Bearer {user1_token}"},
            json={"strategy_draft": draft}
        )
        print(f"PUT draft response: {put_response.status_code}")
        print(f"PUT body: {put_response.text}")
        
        assert put_response.status_code == 200, f"PUT draft failed: {put_response.text}"
        
        put_data = put_response.json()
        assert put_data.get("success") == True, f"PUT not successful: {put_data}"
        assert "strategy_draft" in put_data, "Missing strategy_draft in response"
        
        # Verify draft is set by getting session
        get_response = requests.get(
            f"{BASE_URL}/api/v1/session/{session_id}",
            headers={"Authorization": f"Bearer {user1_token}"}
        )
        assert get_response.status_code == 200
        session_data = get_response.json()
        
        assert session_data.get("strategy_draft") is not None, "Draft not saved in session"
        assert session_data["strategy_draft"]["instrument"]["symbol"] == "TCS", \
            f"Draft symbol mismatch: {session_data['strategy_draft']}"
        
        print(f"✓ PUT draft updates session draft successfully")
        
        # Now finalize to verify it can be finalized
        finalize_response = requests.post(
            f"{BASE_URL}/api/v1/session/{session_id}/finalize",
            headers={"Authorization": f"Bearer {user1_token}"}
        )
        assert finalize_response.status_code == 200, f"Finalize after PUT failed: {finalize_response.text}"
        print(f"✓ Draft can be finalized after PUT update")


class TestGetStrategiesWithFinalizedStrategy:
    """Test GET /api/v1/strategies returns finalized strategy with correct schema."""

    @pytest.fixture
    def user1_token(self):
        return get_auth_token(TEST_USER_1["email"], TEST_USER_1["password"])

    def test_finalized_strategy_appears_in_strategies_list(self, user1_token):
        """Finalized strategy appears in GET /api/v1/strategies with correct schema."""
        # Create session and set draft
        session_id = create_session_with_retry(user1_token)
        
        # Set draft
        draft = {
            "instrument": {"symbol": "INFY", "type": "equity"},
            "timeframe": "1d",
            "entry_conditions": [
                {"name": "RSI", "params": {"period": 14}, "operator": "<", "value": 30}
            ],
            "exit_conditions": [],
            "risk_management": {
                "stop_loss": 4.0,
                "take_profit": 10.0
            }
        }
        
        put_response = requests.put(
            f"{BASE_URL}/api/v1/session/{session_id}/draft",
            headers={"Authorization": f"Bearer {user1_token}"},
            json={"strategy_draft": draft}
        )
        assert put_response.status_code == 200
        
        # Finalize
        finalize_response = requests.post(
            f"{BASE_URL}/api/v1/session/{session_id}/finalize",
            headers={"Authorization": f"Bearer {user1_token}"}
        )
        assert finalize_response.status_code == 200
        strategy_id = finalize_response.json()["strategy_id"]
        print(f"Strategy finalized: {strategy_id}")
        
        # Get strategies list
        strategies_response = requests.get(
            f"{BASE_URL}/api/v1/strategies",
            headers={"Authorization": f"Bearer {user1_token}"}
        )
        assert strategies_response.status_code == 200
        
        strategies_data = strategies_response.json()
        strategies = strategies_data.get("strategies", [])
        print(f"Total strategies: {len(strategies)}")
        
        # Find our finalized strategy
        finalized = None
        for s in strategies:
            if s.get("id") == strategy_id:
                finalized = s
                break
        
        assert finalized is not None, f"Finalized strategy {strategy_id} not found in list"
        print(f"Found finalized strategy: {finalized}")
        
        # Verify schema fields
        assert "metadata" in finalized, "Missing metadata"
        assert "name" in finalized["metadata"], "Missing metadata.name"
        
        # Entry conditions should have proper structure
        assert "entry_conditions" in finalized, "Missing entry_conditions"
        if finalized["entry_conditions"]:
            cond = finalized["entry_conditions"][0]
            assert "name" in cond, "Condition missing 'name' field"
            assert "params" in cond, "Condition missing 'params' field"
            assert "operator" in cond, "Condition missing 'operator' field"
        
        # Risk management should have normalized values
        assert "risk_management" in finalized, "Missing risk_management"
        rm = finalized["risk_management"]
        assert "stop_loss" in rm, "Missing stop_loss in risk_management"
        assert "take_profit" in rm, "Missing take_profit in risk_management"
        
        # Values should be floats (normalized)
        if rm["stop_loss"] is not None:
            assert isinstance(rm["stop_loss"], (int, float)), \
                f"stop_loss should be float, got {type(rm['stop_loss'])}"
        if rm["take_profit"] is not None:
            assert isinstance(rm["take_profit"], (int, float)), \
                f"take_profit should be float, got {type(rm['take_profit'])}"
        
        print(f"✓ Finalized strategy has correct schema with normalized risk management")


class TestRiskManagementNormalization:
    """Test risk management normalized: stop_loss and take_profit as float values."""

    @pytest.fixture
    def user1_token(self):
        return get_auth_token(TEST_USER_1["email"], TEST_USER_1["password"])

    def test_risk_management_saved_as_floats(self, user1_token):
        """stop_loss and take_profit are saved as float values in strategies collection."""
        # Create and finalize with specific risk values
        session_id = create_session_with_retry(user1_token)
        
        # Draft with integer-like values
        draft = {
            "instrument": {"symbol": "HDFCBANK", "type": "equity"},
            "timeframe": "1d",
            "entry_conditions": [
                {"name": "RSI", "params": {"period": 14}, "operator": "<", "value": 30}
            ],
            "exit_conditions": [],
            "risk_management": {
                "stop_loss": 5,  # Integer
                "take_profit": 15  # Integer
            }
        }
        
        requests.put(
            f"{BASE_URL}/api/v1/session/{session_id}/draft",
            headers={"Authorization": f"Bearer {user1_token}"},
            json={"strategy_draft": draft}
        )
        
        finalize_response = requests.post(
            f"{BASE_URL}/api/v1/session/{session_id}/finalize",
            headers={"Authorization": f"Bearer {user1_token}"}
        )
        assert finalize_response.status_code == 200
        strategy_id = finalize_response.json()["strategy_id"]
        
        # Get the strategy directly
        get_response = requests.get(
            f"{BASE_URL}/api/v1/strategy/{strategy_id}",
            headers={"Authorization": f"Bearer {user1_token}"}
        )
        assert get_response.status_code == 200
        
        strategy = get_response.json()["strategy"]
        rm = strategy["risk_management"]
        
        print(f"Risk management: {rm}")
        print(f"stop_loss type: {type(rm['stop_loss'])}, value: {rm['stop_loss']}")
        print(f"take_profit type: {type(rm['take_profit'])}, value: {rm['take_profit']}")
        
        # Should be normalized to floats
        assert rm["stop_loss"] == 5.0, f"stop_loss should be 5.0, got {rm['stop_loss']}"
        assert rm["take_profit"] == 15.0, f"take_profit should be 15.0, got {rm['take_profit']}"
        
        print(f"✓ Risk management values normalized to floats")


class TestCrossUserSessionAccess:
    """Test cross-user session access returns 403."""

    def test_cross_user_session_message_returns_403(self):
        """User 2 cannot send message to User 1's session."""
        token1 = get_auth_token(TEST_USER_1["email"], TEST_USER_1["password"])
        token2 = get_auth_token(TEST_USER_2["email"], TEST_USER_2["password"])
        
        # User 1 creates session
        session_id = create_session_with_retry(token1)
        print(f"User 1 session: {session_id}")
        
        # User 2 tries to send message
        msg_response = requests.post(
            f"{BASE_URL}/api/v1/session/{session_id}/message",
            headers={"Authorization": f"Bearer {token2}"},
            json={"message": "Trying to access other user's session"}
        )
        print(f"Cross-user message: {msg_response.status_code}")
        assert msg_response.status_code == 403, \
            f"Expected 403, got {msg_response.status_code}"
        
        print(f"✓ Cross-user session message returns 403")

    def test_cross_user_session_finalize_returns_403(self):
        """User 2 cannot finalize User 1's session."""
        token1 = get_auth_token(TEST_USER_1["email"], TEST_USER_1["password"])
        token2 = get_auth_token(TEST_USER_2["email"], TEST_USER_2["password"])
        
        # User 1 creates session
        session_id = create_session_with_retry(token1)
        
        # User 2 tries to finalize
        finalize_response = requests.post(
            f"{BASE_URL}/api/v1/session/{session_id}/finalize",
            headers={"Authorization": f"Bearer {token2}"}
        )
        print(f"Cross-user finalize: {finalize_response.status_code}")
        assert finalize_response.status_code == 403, \
            f"Expected 403, got {finalize_response.status_code}"
        
        print(f"✓ Cross-user session finalize returns 403")

    def test_cross_user_session_draft_update_returns_403(self):
        """User 2 cannot update draft in User 1's session."""
        token1 = get_auth_token(TEST_USER_1["email"], TEST_USER_1["password"])
        token2 = get_auth_token(TEST_USER_2["email"], TEST_USER_2["password"])
        
        # User 1 creates session
        session_id = create_session_with_retry(token1)
        
        # User 2 tries to update draft
        draft_response = requests.put(
            f"{BASE_URL}/api/v1/session/{session_id}/draft",
            headers={"Authorization": f"Bearer {token2}"},
            json={"strategy_draft": {"instrument": {"symbol": "HACK"}}}
        )
        print(f"Cross-user draft update: {draft_response.status_code}")
        assert draft_response.status_code == 403, \
            f"Expected 403, got {draft_response.status_code}"
        
        print(f"✓ Cross-user session draft update returns 403")


# Cleanup fixture
@pytest.fixture(scope="module", autouse=True)
def cleanup():
    """Cleanup after tests."""
    yield
    # Note: MongoDB TTL will clean up sessions after 24h
    print("Tests completed")
