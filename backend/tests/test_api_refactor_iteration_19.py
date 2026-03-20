"""
Test suite for backend API verification post-refactoring (iteration 19).
Tests the modular router structure: strategies, screener, templates, admin, ai, backtest.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_USER_EMAIL = "testai@example.com"
TEST_USER_PASSWORD = "Password123!"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "Password123!"


@pytest.fixture(scope="module")
def user_token():
    """Authenticate test user and get token"""
    response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    assert "access_token" in data
    return data["access_token"]


@pytest.fixture(scope="module")
def admin_token():
    """Authenticate admin user and get token"""
    response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    data = response.json()
    assert "access_token" in data
    return data["access_token"]


@pytest.fixture
def auth_headers(user_token):
    """Headers with user auth"""
    return {"Authorization": f"Bearer {user_token}", "Content-Type": "application/json"}


@pytest.fixture
def admin_headers(admin_token):
    """Headers with admin auth"""
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


# =============================================================================
# Health & Root Endpoints
# =============================================================================

class TestHealthAndRoot:
    """Test /api/v1/ and /api/v1/health endpoints"""

    def test_root_endpoint(self):
        """GET /api/v1/ returns welcome message"""
        response = requests.get(f"{BASE_URL}/api/v1/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Text2trade" in data.get("message", "") or "app_name" in data
        print(f"Root endpoint response: {data}")

    def test_health_endpoint(self):
        """GET /api/v1/health returns healthy status"""
        response = requests.get(f"{BASE_URL}/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") in ["healthy", "degraded"]
        assert data.get("mongodb") == True
        assert "version" in data
        assert data.get("version") == "1.2.0"  # New version after refactor
        assert "circuit_breakers" in data
        print(f"Health status: {data['status']}, version: {data['version']}")


# =============================================================================
# Auth Endpoints
# =============================================================================

class TestAuth:
    """Test /api/v1/auth/* endpoints"""

    def test_login_success(self):
        """POST /api/v1/auth/login works for test user"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data.get("token_type") == "bearer"
        print(f"Login successful for {TEST_USER_EMAIL}")

    def test_login_invalid_credentials(self):
        """POST /api/v1/auth/login with wrong password returns 401"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": "WrongPassword123!"
        })
        assert response.status_code == 401
        print("Invalid credentials correctly returns 401")

    def test_admin_login_success(self):
        """POST /api/v1/auth/login works for admin user"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        print(f"Admin login successful for {ADMIN_EMAIL}")


# =============================================================================
# Strategies Endpoints (routers/strategies.py)
# =============================================================================

class TestStrategies:
    """Test /api/v1/strategies and /api/v1/strategy/* endpoints"""

    def test_get_strategies_list(self, auth_headers):
        """GET /api/v1/strategies returns list of user's strategies"""
        response = requests.get(f"{BASE_URL}/api/v1/strategies", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "strategies" in data
        assert "count" in data
        assert isinstance(data["strategies"], list)
        print(f"Found {data['count']} strategies for test user")

    def test_get_strategies_requires_auth(self):
        """GET /api/v1/strategies without token returns 401 or 403"""
        response = requests.get(f"{BASE_URL}/api/v1/strategies")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"


# =============================================================================
# Screener Endpoints (routers/screener_routes.py)
# =============================================================================

class TestScreener:
    """Test /api/v1/screener/* endpoints"""

    def test_get_screener_presets(self):
        """GET /api/v1/screener/presets returns 5 presets"""
        response = requests.get(f"{BASE_URL}/api/v1/screener/presets")
        assert response.status_code == 200
        data = response.json()
        assert "presets" in data
        assert "count" in data
        assert data["count"] == 5
        presets = data["presets"]
        preset_names = [p["name"] for p in presets]
        assert "Oversold" in preset_names
        assert "Trending Up" in preset_names
        print(f"Screener presets: {preset_names}")

    def test_screener_scan_with_preset(self, auth_headers):
        """POST /api/v1/screener/scan with preset works"""
        response = requests.post(f"{BASE_URL}/api/v1/screener/scan", 
            headers=auth_headers,
            json={"preset": "oversold", "timeframe": "1d"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "matches" in data or "symbols_scanned" in data
        print(f"Screener scan completed: {data.get('symbols_scanned', 'N/A')} symbols scanned")

    def test_screener_scan_requires_auth(self):
        """POST /api/v1/screener/scan without token returns 401 or 403"""
        response = requests.post(f"{BASE_URL}/api/v1/screener/scan", json={"preset": "oversold"})
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"


# =============================================================================
# Templates Endpoints (routers/templates.py)
# =============================================================================

class TestTemplates:
    """Test /api/v1/templates endpoint"""

    def test_get_templates_list(self):
        """GET /api/v1/templates returns 12 templates"""
        response = requests.get(f"{BASE_URL}/api/v1/templates")
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        assert "count" in data
        assert data["count"] == 12
        templates = data["templates"]
        assert isinstance(templates, list)
        print(f"Found {data['count']} templates")
        # Verify template structure
        if templates:
            t = templates[0]
            assert "template_id" in t
            assert "name" in t
            assert "category" in t


# =============================================================================
# Session / AI Endpoints (routers/ai.py)
# =============================================================================

class TestSessions:
    """Test /api/v1/session/* endpoints"""

    def test_start_session(self, auth_headers):
        """POST /api/v1/session/start creates a session"""
        response = requests.post(f"{BASE_URL}/api/v1/session/start", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        session_id = data["session_id"]
        assert len(session_id) > 10  # UUID format
        print(f"Session created: {session_id[:8]}...")

    def test_start_session_requires_auth(self):
        """POST /api/v1/session/start without token returns 401 or 403"""
        response = requests.post(f"{BASE_URL}/api/v1/session/start")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"

    def test_get_session(self, auth_headers):
        """GET /api/v1/session/{session_id} retrieves session"""
        # First create a session
        create_resp = requests.post(f"{BASE_URL}/api/v1/session/start", headers=auth_headers)
        assert create_resp.status_code == 200
        session_id = create_resp.json()["session_id"]
        
        # Then retrieve it
        response = requests.get(f"{BASE_URL}/api/v1/session/{session_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data or "messages" in data
        print(f"Session {session_id[:8]}... retrieved successfully")


# =============================================================================
# Admin Endpoints (routers/admin.py)
# =============================================================================

class TestAdmin:
    """Test /api/v1/admin/* endpoints"""

    def test_admin_analytics(self, admin_headers):
        """GET /api/v1/admin/analytics returns platform stats"""
        response = requests.get(f"{BASE_URL}/api/v1/admin/analytics", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert "strategies" in data
        assert "market_data" in data
        # Verify structure
        users = data["users"]
        assert "total" in users
        assert isinstance(users["total"], int)
        print(f"Admin analytics: {users['total']} users, {data['strategies'].get('total', 0)} strategies")

    def test_admin_data_status(self, admin_headers):
        """GET /api/v1/admin/data/status returns data health"""
        response = requests.get(f"{BASE_URL}/api/v1/admin/data/status", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        # Verify we get data status info
        assert "symbols" in data or "total_candles" in data or "status" in data
        print(f"Data status: {data}")

    def test_admin_users_list(self, admin_headers):
        """GET /api/v1/admin/users returns user list"""
        response = requests.get(f"{BASE_URL}/api/v1/admin/users", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert "total" in data
        users = data["users"]
        assert isinstance(users, list)
        print(f"Admin found {data['total']} users")

    def test_admin_endpoints_require_admin_role(self, auth_headers):
        """Admin endpoints return 403 for non-admin users"""
        response = requests.get(f"{BASE_URL}/api/v1/admin/analytics", headers=auth_headers)
        assert response.status_code == 403, "Non-admin should get 403"
        print("Admin endpoints correctly blocked for non-admin users")


# =============================================================================
# Backtest Endpoints (routers/backtest_routes.py)
# =============================================================================

class TestBacktest:
    """Test /api/v1/backtest endpoints"""

    def test_backtest_endpoint(self):
        """POST /api/v1/backtest runs backtest"""
        strategy = {
            "metadata": {"name": "Test Strategy"},
            "instrument": {"symbol": "RELIANCE"},
            "timeframe": {"interval": "1d"},
            "entry_conditions": [
                {"name": "RSI", "params": {"period": 14}, "operator": "<", "value": 30}
            ],
            "exit_conditions": [],
            "risk_management": {"stop_loss": {"type": "percentage", "value": 2.0}}
        }
        response = requests.post(f"{BASE_URL}/api/v1/backtest", json={"strategy": strategy})
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "metrics" in data
        assert "trades" in data
        print(f"Backtest completed: {len(data['trades'])} trades, success={data['success']}")


# =============================================================================
# Analytics Endpoint
# =============================================================================

class TestAnalytics:
    """Test /api/v1/analytics endpoint"""

    def test_get_analytics(self):
        """GET /api/v1/analytics returns platform stats"""
        response = requests.get(f"{BASE_URL}/api/v1/analytics")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "stats" in data
        stats = data["stats"]
        assert "strategies_created" in stats or "total_users" in stats
        print(f"Analytics: {stats}")


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
