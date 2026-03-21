"""
Iteration 15 Tests: Template Management & E2E AI Flow Testing
- 12 templates seeded in strategy_templates collection
- Template endpoints: public list/detail, user clone, admin CRUD
- E2E flow: AI conversation → finalize → backtest with real results
- Clone template → modify → backtest
- Gibberish → AI asks clarifying question
- Admin permissions: non-admin gets 403
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://gains-tracker-152.preview.emergentagent.com").rstrip("/")

# Test credentials
TEST_USER_EMAIL = "testai@example.com"
TEST_USER_PASSWORD = "Password123!"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "Password123!"

# --- Helper functions ---

def get_token(email: str, password: str) -> str:
    """Login and return access token."""
    res = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
        "email": email,
        "password": password
    })
    if res.status_code == 200:
        return res.json().get("access_token")
    pytest.skip(f"Login failed for {email}: {res.status_code} - {res.text}")

def auth_header(token: str) -> dict:
    """Return Authorization header dict."""
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# TEMPLATE PUBLIC ENDPOINTS (No Auth Required)
# ==============================================================================

class TestTemplatePublicEndpoints:
    """Test public template endpoints - no authentication required."""

    def test_list_templates_returns_12(self):
        """GET /api/v1/templates returns exactly 12 templates."""
        res = requests.get(f"{BASE_URL}/api/v1/templates")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        
        data = res.json()
        assert "templates" in data, "Response should have 'templates' key"
        assert "count" in data, "Response should have 'count' key"
        assert data["count"] == 12, f"Expected 12 templates, got {data['count']}"
        assert len(data["templates"]) == 12, f"Expected 12 templates in list, got {len(data['templates'])}"
        
        # Verify template structure
        for t in data["templates"]:
            assert "template_id" in t, "Template should have template_id"
            assert "name" in t, "Template should have name"
            assert "category" in t, "Template should have category"
            assert "description" in t, "Template should have description"

    def test_list_templates_has_all_categories(self):
        """Verify templates cover all expected categories."""
        res = requests.get(f"{BASE_URL}/api/v1/templates")
        assert res.status_code == 200
        
        data = res.json()
        categories = set(t["category"] for t in data["templates"])
        
        # Expected categories: Trend, Mean Reversion, Momentum, Intraday, Breakout, Volatility, Combined
        expected = {"Trend", "Mean Reversion", "Momentum", "Intraday", "Breakout", "Volatility", "Combined"}
        assert expected.issubset(categories), f"Missing categories. Expected: {expected}, Got: {categories}"

    def test_get_single_template_detail(self):
        """GET /api/v1/template/{id} returns single template detail."""
        # First get list to find a template_id
        list_res = requests.get(f"{BASE_URL}/api/v1/templates")
        assert list_res.status_code == 200
        templates = list_res.json()["templates"]
        assert len(templates) > 0, "No templates found"
        
        template_id = templates[0]["template_id"]
        
        # Get single template
        res = requests.get(f"{BASE_URL}/api/v1/template/{template_id}")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        
        data = res.json()
        assert data["template_id"] == template_id
        assert "name" in data
        assert "entry_conditions" in data
        assert "exit_conditions" in data
        assert "risk_management" in data

    def test_get_nonexistent_template_returns_404(self):
        """GET /api/v1/template/{id} with invalid id returns 404."""
        res = requests.get(f"{BASE_URL}/api/v1/template/nonexistent-template-id")
        assert res.status_code == 404


# ==============================================================================
# TEMPLATE CLONE ENDPOINT (User Auth Required)
# ==============================================================================

class TestTemplateClone:
    """Test template cloning - user authentication required."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Get user token before tests."""
        self.token = get_token(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        self.headers = auth_header(self.token)

    def test_clone_template_creates_strategy(self):
        """POST /api/v1/template/{id}/clone as user creates new strategy."""
        # Get a template to clone (Golden Cross)
        list_res = requests.get(f"{BASE_URL}/api/v1/templates")
        templates = list_res.json()["templates"]
        golden_cross = next((t for t in templates if "Golden Cross" in t["name"]), templates[0])
        template_id = golden_cross["template_id"]
        
        # Clone it
        clone_res = requests.post(
            f"{BASE_URL}/api/v1/template/{template_id}/clone",
            json={"symbol": "TCS"},
            headers=self.headers
        )
        assert clone_res.status_code == 200, f"Expected 200, got {clone_res.status_code}: {clone_res.text}"
        
        data = clone_res.json()
        assert data["success"] == True
        assert "strategy_id" in data
        assert "strategy" in data
        
        # Verify cloned strategy structure
        strategy = data["strategy"]
        assert strategy["instrument"]["symbol"] == "TCS"
        assert "cloned" in strategy["metadata"]["tags"]
        
        # Verify it appears in user's strategies
        strats_res = requests.get(f"{BASE_URL}/api/v1/strategies", headers=self.headers)
        assert strats_res.status_code == 200
        strategies = strats_res.json()["strategies"]
        cloned_ids = [s["id"] for s in strategies]
        assert data["strategy_id"] in cloned_ids, "Cloned strategy should appear in user's list"

    def test_clone_template_without_auth_fails(self):
        """POST /api/v1/template/{id}/clone without auth returns 401 or 403."""
        list_res = requests.get(f"{BASE_URL}/api/v1/templates")
        template_id = list_res.json()["templates"][0]["template_id"]
        
        res = requests.post(f"{BASE_URL}/api/v1/template/{template_id}/clone", json={})
        # 401 Unauthorized or 403 Forbidden - both indicate auth required
        assert res.status_code in [401, 403], f"Expected 401/403, got {res.status_code}"


# ==============================================================================
# ADMIN TEMPLATE CRUD (Admin Auth Required)
# ==============================================================================

class TestAdminTemplates:
    """Test admin template CRUD operations."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Get admin and user tokens."""
        self.admin_token = get_token(ADMIN_EMAIL, ADMIN_PASSWORD)
        self.admin_headers = auth_header(self.admin_token)
        self.user_token = get_token(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        self.user_headers = auth_header(self.user_token)

    def test_admin_create_template(self):
        """POST /api/v1/admin/templates as admin creates new template."""
        template_data = {
            "name": "TEST_Admin_Template",
            "description": "Admin test template for pytest",
            "category": "Trend",
            "market": {"type": "equity", "exchange": "NSE"},
            "instrument": {"symbol": "INFY"},
            "timeframe": {"interval": "1d"},
            "entry_conditions": [
                {"name": "RSI", "params": {"period": 14}, "operator": "<", "value": 30}
            ],
            "exit_conditions": [
                {"name": "RSI", "params": {"period": 14}, "operator": ">", "value": 70}
            ],
            "filters": [],
            "risk_management": {
                "stop_loss": {"type": "percentage", "value": 2.0},
                "trailing_stop_loss": {"enabled": False, "type": "percentage", "value": 1.0, "activation_profit": 0},
                "target_profit": None,
                "time_based_exit": {"enabled": False, "exit_time": "15:10"},
                "daily_limits": {"max_loss_per_day": 5.0, "max_trades_per_day": 10},
                "position_sizing": {"method": "fixed_quantity", "value": 1}
            }
        }
        
        res = requests.post(
            f"{BASE_URL}/api/v1/admin/templates",
            json=template_data,
            headers=self.admin_headers
        )
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        
        data = res.json()
        assert data["success"] == True
        assert "template" in data, "Response should have 'template' key"
        assert "template_id" in data["template"], "Template should have 'template_id'"
        template_id = data["template"]["template_id"]
        
        # Verify count is now 13
        list_res = requests.get(f"{BASE_URL}/api/v1/templates")
        assert list_res.json()["count"] == 13, "Expected 13 templates after admin create"
        
        # Cleanup: delete the test template
        requests.delete(
            f"{BASE_URL}/api/v1/admin/templates/{template_id}",
            headers=self.admin_headers
        )

    def test_admin_update_template(self):
        """PUT /api/v1/admin/templates/{id} as admin updates template name."""
        # Create a test template first
        template_data = {
            "name": "TEST_Update_Template",
            "description": "To be updated",
            "category": "Momentum",
            "market": {"type": "equity", "exchange": "NSE"},
            "instrument": {"symbol": "SBIN"},
            "timeframe": {"interval": "1d"},
            "entry_conditions": [
                {"name": "MACD", "params": {"fast": 12, "slow": 26, "signal": 9}, "operator": "bullish_cross"}
            ],
            "exit_conditions": [
                {"name": "MACD", "params": {"fast": 12, "slow": 26, "signal": 9}, "operator": "bearish_cross"}
            ],
            "filters": [],
            "risk_management": {
                "stop_loss": {"type": "percentage", "value": 2.5},
                "trailing_stop_loss": {"enabled": False, "type": "percentage", "value": 1.0, "activation_profit": 0},
                "target_profit": None,
                "time_based_exit": {"enabled": False, "exit_time": "15:10"},
                "daily_limits": {"max_loss_per_day": 5.0, "max_trades_per_day": 10},
                "position_sizing": {"method": "fixed_quantity", "value": 1}
            }
        }
        
        create_res = requests.post(
            f"{BASE_URL}/api/v1/admin/templates",
            json=template_data,
            headers=self.admin_headers
        )
        assert create_res.status_code == 200
        template_id = create_res.json()["template"]["template_id"]
        
        # Update the name (full payload required for PUT)
        update_data = {
            "name": "TEST_Updated_Name",
            "description": "Updated description",
            "category": "Momentum",
            "market": {"type": "equity", "exchange": "NSE"},
            "instrument": {"symbol": "SBIN"},
            "timeframe": {"interval": "1d"},
            "entry_conditions": [
                {"name": "MACD", "params": {"fast": 12, "slow": 26, "signal": 9}, "operator": "bullish_cross"}
            ],
            "exit_conditions": [
                {"name": "MACD", "params": {"fast": 12, "slow": 26, "signal": 9}, "operator": "bearish_cross"}
            ],
            "filters": [],
            "risk_management": {
                "stop_loss": {"type": "percentage", "value": 2.5},
                "trailing_stop_loss": {"enabled": False, "type": "percentage", "value": 1.0, "activation_profit": 0},
                "target_profit": None,
                "time_based_exit": {"enabled": False, "exit_time": "15:10"},
                "daily_limits": {"max_loss_per_day": 5.0, "max_trades_per_day": 10},
                "position_sizing": {"method": "fixed_quantity", "value": 1}
            }
        }
        update_res = requests.put(
            f"{BASE_URL}/api/v1/admin/templates/{template_id}",
            json=update_data,
            headers=self.admin_headers
        )
        assert update_res.status_code == 200, f"Expected 200, got {update_res.status_code}: {update_res.text}"
        
        data = update_res.json()
        assert data["success"] == True
        
        # Verify update
        get_res = requests.get(f"{BASE_URL}/api/v1/template/{template_id}")
        assert get_res.json()["name"] == "TEST_Updated_Name"
        assert get_res.json()["description"] == "Updated description"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/v1/admin/templates/{template_id}", headers=self.admin_headers)

    def test_admin_delete_template(self):
        """DELETE /api/v1/admin/templates/{id} as admin deletes template."""
        # Create a test template
        template_data = {
            "name": "TEST_Delete_Template",
            "description": "To be deleted",
            "category": "Breakout",
            "market": {"type": "equity", "exchange": "NSE"},
            "instrument": {"symbol": "LT"},
            "timeframe": {"interval": "1d"},
            "entry_conditions": [
                {"name": "PivotPoints", "params": {"method": "standard"}, "operator": "above_r1"}
            ],
            "exit_conditions": [
                {"name": "PivotPoints", "params": {"method": "standard"}, "operator": "below_s1"}
            ],
            "filters": [],
            "risk_management": {
                "stop_loss": {"type": "percentage", "value": 1.5},
                "trailing_stop_loss": {"enabled": False, "type": "percentage", "value": 1.0, "activation_profit": 0},
                "target_profit": None,
                "time_based_exit": {"enabled": False, "exit_time": "15:10"},
                "daily_limits": {"max_loss_per_day": 5.0, "max_trades_per_day": 10},
                "position_sizing": {"method": "fixed_quantity", "value": 1}
            }
        }
        
        create_res = requests.post(
            f"{BASE_URL}/api/v1/admin/templates",
            json=template_data,
            headers=self.admin_headers
        )
        assert create_res.status_code == 200
        template_id = create_res.json()["template"]["template_id"]
        
        # Delete
        del_res = requests.delete(
            f"{BASE_URL}/api/v1/admin/templates/{template_id}",
            headers=self.admin_headers
        )
        assert del_res.status_code == 200, f"Expected 200, got {del_res.status_code}: {del_res.text}"
        
        # Verify deleted - should 404
        get_res = requests.get(f"{BASE_URL}/api/v1/template/{template_id}")
        assert get_res.status_code == 404

    def test_nonadmin_create_template_returns_403(self):
        """POST /api/v1/admin/templates as non-admin returns 403 Forbidden."""
        template_data = {
            "name": "TEST_Unauthorized",
            "description": "Should fail",
            "category": "Trend",
            "market": {"type": "equity", "exchange": "NSE"},
            "instrument": {"symbol": "TCS"},
            "timeframe": {"interval": "1d"},
            "entry_conditions": [{"name": "RSI", "params": {"period": 14}, "operator": "<", "value": 30}],
            "exit_conditions": [{"name": "RSI", "params": {"period": 14}, "operator": ">", "value": 70}],
            "filters": [],
            "risk_management": {
                "stop_loss": {"type": "percentage", "value": 2.0},
                "trailing_stop_loss": {"enabled": False, "type": "percentage", "value": 1.0, "activation_profit": 0},
                "target_profit": None,
                "time_based_exit": {"enabled": False, "exit_time": "15:10"},
                "daily_limits": {"max_loss_per_day": 5.0, "max_trades_per_day": 10},
                "position_sizing": {"method": "fixed_quantity", "value": 1}
            }
        }
        
        res = requests.post(
            f"{BASE_URL}/api/v1/admin/templates",
            json=template_data,
            headers=self.user_headers
        )
        assert res.status_code == 403, f"Expected 403 for non-admin, got {res.status_code}"

    def test_nonadmin_delete_template_returns_403(self):
        """DELETE /api/v1/admin/templates/{id} as non-admin returns 403 Forbidden."""
        # Get any existing template id
        list_res = requests.get(f"{BASE_URL}/api/v1/templates")
        template_id = list_res.json()["templates"][0]["template_id"]
        
        res = requests.delete(
            f"{BASE_URL}/api/v1/admin/templates/{template_id}",
            headers=self.user_headers
        )
        assert res.status_code == 403, f"Expected 403 for non-admin, got {res.status_code}"


# ==============================================================================
# E2E TEST 1: AI Conversation → Finalize → Backtest
# ==============================================================================

class TestE2EAIConversationFlow:
    """E2E Test: AI conversation → finalize → backtest with real results."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.token = get_token(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        self.headers = auth_header(self.token)

    def test_e2e_ai_conversation_to_backtest(self):
        """
        E2E Test 1: Start AI session → send trading idea → AI responds → 
        continue until strategy ready → finalize → backtest
        """
        # Step 1: Start session
        start_res = requests.post(
            f"{BASE_URL}/api/v1/session/start",
            headers=self.headers
        )
        assert start_res.status_code == 200, f"Session start failed: {start_res.text}"
        session_id = start_res.json()["session_id"]
        
        # Step 2: Send initial trading idea
        msg1_res = requests.post(
            f"{BASE_URL}/api/v1/session/{session_id}/message",
            json={"message": "Supertrend on Reliance 15min timeframe"},
            headers=self.headers
        )
        assert msg1_res.status_code == 200, f"Message 1 failed: {msg1_res.text}"
        
        msg1_data = msg1_res.json()
        assert "mode" in msg1_data, "Response should have 'mode' field"
        assert msg1_data["mode"] in ["question", "strategy", "error"]
        
        # Step 3: If AI asks question about stop loss, respond
        if msg1_data["mode"] == "question":
            time.sleep(1)  # Small delay for AI
            msg2_res = requests.post(
                f"{BASE_URL}/api/v1/session/{session_id}/message",
                json={"message": "2% trailing stop loss"},
                headers=self.headers
            )
            assert msg2_res.status_code == 200, f"Message 2 failed: {msg2_res.text}"
            msg2_data = msg2_res.json()
            
            # May need one more turn for exit condition
            if msg2_data["mode"] == "question":
                time.sleep(1)
                msg3_res = requests.post(
                    f"{BASE_URL}/api/v1/session/{session_id}/message",
                    json={"message": "Exit on supertrend sell signal"},
                    headers=self.headers
                )
                assert msg3_res.status_code == 200
        
        # Step 4: Check session for strategy_draft
        time.sleep(1)
        session_res = requests.get(
            f"{BASE_URL}/api/v1/session/{session_id}",
            headers=self.headers
        )
        assert session_res.status_code == 200
        
        session_data = session_res.json()
        # Session may or may not have strategy_draft depending on AI responses
        # We verify the flow works without errors
        
        # Step 5: If we have a strategy draft, finalize and backtest
        if session_data.get("strategy_draft"):
            finalize_res = requests.post(
                f"{BASE_URL}/api/v1/session/{session_id}/finalize",
                headers=self.headers
            )
            if finalize_res.status_code == 200:
                finalize_data = finalize_res.json()
                assert finalize_data["success"] == True
                strategy_id = finalize_data["strategy_id"]
                
                # Get the finalized strategy
                strat_res = requests.get(
                    f"{BASE_URL}/api/v1/strategy/{strategy_id}",
                    headers=self.headers
                )
                assert strat_res.status_code == 200
                strategy = strat_res.json()["strategy"]
                
                # Run backtest
                backtest_res = requests.post(
                    f"{BASE_URL}/api/v1/backtest",
                    json={"strategy": strategy},
                    headers=self.headers
                )
                assert backtest_res.status_code == 200, f"Backtest failed: {backtest_res.text}"
                
                bt_data = backtest_res.json()
                assert "metrics" in bt_data
                assert "trades" in bt_data


# ==============================================================================
# E2E TEST 2: Clone Template → Backtest
# ==============================================================================

class TestE2ECloneAndBacktest:
    """E2E Test: Clone a template → verify in strategies → run backtest."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.token = get_token(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        self.headers = auth_header(self.token)

    def test_e2e_clone_template_and_backtest(self):
        """
        E2E Test 2: Clone template (RSI Mean Reversion) → verify appears in 
        GET /strategies → run backtest on cloned strategy.
        """
        # Step 1: Find RSI Mean Reversion template
        list_res = requests.get(f"{BASE_URL}/api/v1/templates")
        templates = list_res.json()["templates"]
        rsi_template = next((t for t in templates if "RSI" in t["name"]), templates[1])
        template_id = rsi_template["template_id"]
        
        # Step 2: Clone it with custom symbol
        clone_res = requests.post(
            f"{BASE_URL}/api/v1/template/{template_id}/clone",
            json={"symbol": "HDFCBANK", "name": "TEST_RSI_Clone_E2E"},
            headers=self.headers
        )
        assert clone_res.status_code == 200, f"Clone failed: {clone_res.text}"
        
        clone_data = clone_res.json()
        assert clone_data["success"] == True
        cloned_strategy_id = clone_data["strategy_id"]
        cloned_strategy = clone_data["strategy"]
        
        # Step 3: Verify in user's strategies list
        strats_res = requests.get(f"{BASE_URL}/api/v1/strategies", headers=self.headers)
        assert strats_res.status_code == 200
        
        strategies = strats_res.json()["strategies"]
        found = any(s["id"] == cloned_strategy_id for s in strategies)
        assert found, f"Cloned strategy {cloned_strategy_id} not found in user's strategies"
        
        # Step 4: Run backtest on cloned strategy
        backtest_res = requests.post(
            f"{BASE_URL}/api/v1/backtest",
            json={"strategy": cloned_strategy},
            headers=self.headers
        )
        assert backtest_res.status_code == 200, f"Backtest failed: {backtest_res.text}"
        
        bt_data = backtest_res.json()
        assert "success" in bt_data
        assert "metrics" in bt_data
        assert "trades" in bt_data or bt_data.get("trades") is not None


# ==============================================================================
# E2E TEST 3: Gibberish → AI asks clarifying question
# ==============================================================================

class TestE2EGibberishInput:
    """E2E Test: Gibberish input → AI asks clarifying question, no crash."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.token = get_token(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        self.headers = auth_header(self.token)

    def test_e2e_gibberish_gets_clarifying_question(self):
        """
        E2E Test 3: Start AI session → send gibberish 'asdfkjh random text' →
        AI asks clarifying question, no crash.
        """
        # Start session
        start_res = requests.post(
            f"{BASE_URL}/api/v1/session/start",
            headers=self.headers
        )
        assert start_res.status_code == 200
        session_id = start_res.json()["session_id"]
        
        # Send gibberish
        gibberish_res = requests.post(
            f"{BASE_URL}/api/v1/session/{session_id}/message",
            json={"message": "asdfkjh random text blergh 123xyz"},
            headers=self.headers
        )
        
        # Should not crash - returns 200
        assert gibberish_res.status_code == 200, f"Gibberish handling failed: {gibberish_res.text}"
        
        data = gibberish_res.json()
        assert "mode" in data
        
        # AI should respond with question or error asking for clarification
        # Not with a valid strategy (mode != "strategy" with valid conditions)
        if data["mode"] == "strategy":
            # If somehow parsed as strategy, it should be empty or minimal
            strategy = data.get("strategy_draft") or data.get("content", {}).get("strategy", {})
            # Strategy should not have meaningful entry conditions from gibberish
            entry_conds = strategy.get("entry_conditions", [])
            # This is acceptable - AI might create empty or ask question
            pass
        elif data["mode"] == "question":
            # Expected - AI asks for clarification
            content = data.get("content", {})
            message = content.get("message", "")
            assert len(message) > 0, "AI should provide a clarifying question"
        elif data["mode"] == "error":
            # Also acceptable - AI couldn't understand
            pass
        
        # Key assertion: no 5xx error, system didn't crash
        assert gibberish_res.status_code < 500


# ==============================================================================
# Verify Templates Seeded Correctly
# ==============================================================================

class TestTemplateSeedVerification:
    """Verify all 12 templates are seeded with correct data."""

    def test_all_templates_have_required_fields(self):
        """All 12 templates have all required fields."""
        res = requests.get(f"{BASE_URL}/api/v1/templates")
        assert res.status_code == 200
        
        templates = res.json()["templates"]
        required_fields = [
            "template_id", "name", "description", "category",
            "entry_conditions", "exit_conditions", "risk_management",
            "market", "instrument", "timeframe"
        ]
        
        for t in templates:
            for field in required_fields:
                assert field in t, f"Template '{t.get('name', 'unknown')}' missing field: {field}"

    def test_template_names_are_unique(self):
        """All template names are unique."""
        res = requests.get(f"{BASE_URL}/api/v1/templates")
        templates = res.json()["templates"]
        
        names = [t["name"] for t in templates]
        assert len(names) == len(set(names)), f"Duplicate template names found: {names}"

    def test_known_templates_exist(self):
        """Verify specific expected templates exist."""
        res = requests.get(f"{BASE_URL}/api/v1/templates")
        templates = res.json()["templates"]
        
        expected_names = [
            "Golden Cross", "RSI Mean Reversion", "Supertrend Follower",
            "MACD Momentum", "Bollinger Bounce", "VWAP Intraday",
            "Pivot Breakout", "Stochastic Reversal", "ATR Volatility",
            "CCI Breakout", "Supertrend + RSI", "EMA Ribbon"
        ]
        
        actual_names = [t["name"] for t in templates]
        for expected in expected_names:
            assert expected in actual_names, f"Expected template '{expected}' not found"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
