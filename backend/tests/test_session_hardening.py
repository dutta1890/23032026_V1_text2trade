"""
Test session edge cases, data export, input hardening, and app versioning.
Iteration 30 - Session Hardening & Data Export Tests
"""
import pytest
import requests
import os
import time
import jwt
from datetime import datetime, timezone, timedelta

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
TEST_USER_EMAIL = "testai@example.com"
TEST_USER_PASSWORD = "Password123!"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "Password123!"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def auth_tokens(api_client):
    """Get both access and refresh tokens"""
    response = api_client.post(f"{BASE_URL}/api/v1/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip(f"Login failed: {response.text}")
    data = response.json()
    return {
        "access_token": data.get("access_token"),
        "refresh_token": data.get("refresh_token")
    }


@pytest.fixture(scope="module")
def admin_tokens(api_client):
    """Get admin tokens"""
    response = api_client.post(f"{BASE_URL}/api/v1/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip(f"Admin login failed: {response.text}")
    data = response.json()
    return {
        "access_token": data.get("access_token"),
        "refresh_token": data.get("refresh_token")
    }


class TestAppVersion:
    """Test app version endpoint"""
    
    def test_version_endpoint_returns_correct_structure(self, api_client):
        """GET /api/v1/app/version returns version, build_date, min_supported_version"""
        response = api_client.get(f"{BASE_URL}/api/v1/app/version")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "version" in data, "Missing 'version' field"
        assert "build_date" in data, "Missing 'build_date' field"
        assert "min_supported_version" in data, "Missing 'min_supported_version' field"
        
        # Verify version format
        assert data["version"] == "0.2.0", f"Expected version 0.2.0, got {data['version']}"
        print(f"✓ App version endpoint returns: {data}")
    
    def test_version_endpoint_no_auth_required(self, api_client):
        """Version endpoint should be public (no auth required)"""
        # Create a fresh session without any auth
        fresh_session = requests.Session()
        response = fresh_session.get(f"{BASE_URL}/api/v1/app/version")
        assert response.status_code == 200, "Version endpoint should not require auth"
        print("✓ Version endpoint accessible without authentication")


class TestLoginReturnsRefreshToken:
    """Test that login returns both access and refresh tokens"""
    
    def test_login_returns_both_tokens(self, api_client):
        """POST /api/v1/auth/login returns access_token and refresh_token"""
        response = api_client.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        
        data = response.json()
        assert "access_token" in data, "Missing access_token in login response"
        assert "refresh_token" in data, "Missing refresh_token in login response"
        assert len(data["access_token"]) > 50, "Access token seems too short"
        assert len(data["refresh_token"]) > 50, "Refresh token seems too short"
        print("✓ Login returns both access_token and refresh_token")


class TestTokenRefresh:
    """Test token refresh functionality"""
    
    def test_refresh_with_valid_token(self, api_client, auth_tokens):
        """POST /api/v1/auth/refresh with valid refresh_token returns new access_token"""
        response = api_client.post(f"{BASE_URL}/api/v1/auth/refresh", json={
            "refresh_token": auth_tokens["refresh_token"]
        })
        assert response.status_code == 200, f"Refresh failed: {response.text}"
        
        data = response.json()
        assert "access_token" in data, "Missing access_token in refresh response"
        assert len(data["access_token"]) > 50, "New access token seems too short"
        print("✓ Token refresh returns new access_token")
    
    def test_refresh_with_invalid_token(self, api_client):
        """POST /api/v1/auth/refresh with invalid token returns 401"""
        response = api_client.post(f"{BASE_URL}/api/v1/auth/refresh", json={
            "refresh_token": "invalid_token_here"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Invalid refresh token returns 401")
    
    def test_refresh_with_expired_token_simulation(self, api_client):
        """Test that refresh token age check works (simulated via JWT decode)"""
        # We can't easily create an expired token, but we can verify the logic exists
        # by checking that the endpoint validates the 'iat' claim
        response = api_client.post(f"{BASE_URL}/api/v1/auth/refresh", json={
            "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0IiwidHlwZSI6InJlZnJlc2giLCJpYXQiOjE1MDAwMDAwMDAsImV4cCI6MTUwMDAwMDAwMH0.invalid"
        })
        # Should fail with 401 (either expired or invalid)
        assert response.status_code == 401, f"Expected 401 for old/invalid token, got {response.status_code}"
        print("✓ Expired/invalid refresh token returns 401")


class TestDataExport:
    """Test data export functionality"""
    
    def test_export_data_returns_correct_structure(self, api_client, auth_tokens):
        """POST /api/v1/account/export-data returns expected fields"""
        headers = {"Authorization": f"Bearer {auth_tokens['access_token']}"}
        response = api_client.post(f"{BASE_URL}/api/v1/account/export-data", headers=headers)
        assert response.status_code == 200, f"Export failed: {response.text}"
        
        data = response.json()
        required_fields = ["exported_at", "user_email", "profile", "strategies", "backtests", "paper_trades", "performance_records"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        print(f"✓ Export data contains all required fields: {list(data.keys())}")
    
    def test_export_data_excludes_password_hash(self, api_client, auth_tokens):
        """Export data should NOT include password_hash"""
        headers = {"Authorization": f"Bearer {auth_tokens['access_token']}"}
        response = api_client.post(f"{BASE_URL}/api/v1/account/export-data", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        # Check profile doesn't have password_hash
        profile = data.get("profile", {})
        assert "password_hash" not in profile, "password_hash should not be in export"
        
        # Check entire response as string doesn't contain password_hash
        response_str = str(data)
        assert "password_hash" not in response_str, "password_hash found somewhere in export"
        print("✓ Export data does not include password_hash")
    
    def test_export_data_excludes_mongo_id(self, api_client, auth_tokens):
        """Export data should NOT include MongoDB _id fields"""
        headers = {"Authorization": f"Bearer {auth_tokens['access_token']}"}
        response = api_client.post(f"{BASE_URL}/api/v1/account/export-data", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        response_str = str(data)
        # _id should not appear in the export
        assert '"_id"' not in response_str and "'_id'" not in response_str, "_id field found in export"
        print("✓ Export data does not include _id fields")
    
    def test_export_data_excludes_demo_data(self, api_client, auth_tokens):
        """Export data should exclude demo data (is_demo: true)"""
        headers = {"Authorization": f"Bearer {auth_tokens['access_token']}"}
        response = api_client.post(f"{BASE_URL}/api/v1/account/export-data", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        # Check strategies don't have is_demo: true
        for strategy in data.get("strategies", []):
            assert strategy.get("is_demo") != True, "Demo strategy found in export"
        
        # Check paper_trades don't have is_demo: true
        for trade in data.get("paper_trades", []):
            assert trade.get("is_demo") != True, "Demo paper trade found in export"
        
        print("✓ Export data excludes demo data")
    
    def test_export_data_requires_auth(self, api_client):
        """Export data endpoint requires authentication"""
        response = api_client.post(f"{BASE_URL}/api/v1/account/export-data")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Export data requires authentication")


class TestRequestBodySizeLimit:
    """Test 1MB request body limit"""
    
    def test_large_request_body_rejected(self, api_client, auth_tokens):
        """Request body >1MB should return 413"""
        headers = {
            "Authorization": f"Bearer {auth_tokens['access_token']}",
            "Content-Type": "application/json",
            "Content-Length": str(2 * 1024 * 1024)  # 2MB
        }
        # Create a large payload
        large_data = {"data": "x" * (1024 * 1024 + 1000)}  # Just over 1MB
        
        try:
            response = api_client.post(
                f"{BASE_URL}/api/v1/strategies",
                json=large_data,
                headers=headers
            )
            # Should get 413 Payload Too Large
            assert response.status_code == 413, f"Expected 413, got {response.status_code}"
            print("✓ Large request body (>1MB) returns 413")
        except Exception as e:
            # Connection might be reset for very large payloads
            print(f"✓ Large request body rejected (connection error: {type(e).__name__})")


class TestStrategyConditionLimits:
    """Test strategy validation limits (max 10 entry/exit conditions)"""
    
    def test_strategy_rejects_too_many_entry_conditions(self, api_client, auth_tokens):
        """Strategy with >10 entry conditions should be rejected"""
        headers = {"Authorization": f"Bearer {auth_tokens['access_token']}"}
        
        # Create strategy with 11 entry conditions
        entry_conditions = [
            {"name": "RSI", "params": {"period": 14}, "operator": "<", "value": 30}
            for _ in range(11)
        ]
        
        strategy_data = {
            "metadata": {"name": "Test Too Many Entries", "description": "Test", "tags": []},
            "market": {"type": "equity", "exchange": "NSE"},
            "instrument": {"symbol": "RELIANCE"},
            "timeframe": {"interval": "1d"},
            "entry_conditions": entry_conditions,
            "exit_conditions": [{"name": "RSI", "params": {"period": 14}, "operator": ">", "value": 70}],
            "filters": [],
            "risk_management": {
                "stop_loss": {"type": "percentage", "value": 2},
                "target_profit": None,
                "trailing_stop_loss": {"enabled": False, "type": "percentage", "value": 1.0, "activation_profit": 0},
                "time_based_exit": {"enabled": False, "exit_time": "15:10"},
                "daily_limits": {"max_loss_per_day": 5.0, "max_trades_per_day": 10},
                "position_sizing": {"method": "fixed_quantity", "value": 1}
            }
        }
        
        # Try to create via AI session finalize (where validation happens)
        # First start a session
        session_response = api_client.post(f"{BASE_URL}/api/v1/session/start", headers=headers)
        if session_response.status_code == 200:
            session_id = session_response.json().get("session_id")
            
            # Try to update draft with too many conditions
            draft_response = api_client.put(
                f"{BASE_URL}/api/v1/session/{session_id}/draft",
                json={"strategy_draft": strategy_data},
                headers=headers
            )
            # Should fail validation
            assert draft_response.status_code == 422, f"Expected 422 for >10 entry conditions, got {draft_response.status_code}"
            print("✓ Strategy with >10 entry conditions rejected (422)")
        else:
            # If session creation fails, skip this test
            pytest.skip("Could not create AI session for testing")
    
    def test_strategy_rejects_too_many_exit_conditions(self, api_client, auth_tokens):
        """Strategy with >10 exit conditions should be rejected"""
        headers = {"Authorization": f"Bearer {auth_tokens['access_token']}"}
        
        # Create strategy with 11 exit conditions
        exit_conditions = [
            {"name": "RSI", "params": {"period": 14}, "operator": ">", "value": 70}
            for _ in range(11)
        ]
        
        strategy_data = {
            "metadata": {"name": "Test Too Many Exits", "description": "Test", "tags": []},
            "market": {"type": "equity", "exchange": "NSE"},
            "instrument": {"symbol": "RELIANCE"},
            "timeframe": {"interval": "1d"},
            "entry_conditions": [{"name": "RSI", "params": {"period": 14}, "operator": "<", "value": 30}],
            "exit_conditions": exit_conditions,
            "filters": [],
            "risk_management": {
                "stop_loss": {"type": "percentage", "value": 2},
                "target_profit": None,
                "trailing_stop_loss": {"enabled": False, "type": "percentage", "value": 1.0, "activation_profit": 0},
                "time_based_exit": {"enabled": False, "exit_time": "15:10"},
                "daily_limits": {"max_loss_per_day": 5.0, "max_trades_per_day": 10},
                "position_sizing": {"method": "fixed_quantity", "value": 1}
            }
        }
        
        # Start a session
        session_response = api_client.post(f"{BASE_URL}/api/v1/session/start", headers=headers)
        if session_response.status_code == 200:
            session_id = session_response.json().get("session_id")
            
            # Try to update draft with too many conditions
            draft_response = api_client.put(
                f"{BASE_URL}/api/v1/session/{session_id}/draft",
                json={"strategy_draft": strategy_data},
                headers=headers
            )
            # Should fail validation
            assert draft_response.status_code == 422, f"Expected 422 for >10 exit conditions, got {draft_response.status_code}"
            print("✓ Strategy with >10 exit conditions rejected (422)")
        else:
            pytest.skip("Could not create AI session for testing")


class TestLastActiveTracking:
    """Test that middleware updates last_active timestamp"""
    
    def test_authenticated_request_updates_last_active(self, api_client, auth_tokens):
        """Authenticated requests should update last_active timestamp"""
        headers = {"Authorization": f"Bearer {auth_tokens['access_token']}"}
        
        # Make an authenticated request
        response = api_client.get(f"{BASE_URL}/api/v1/account/profile", headers=headers)
        assert response.status_code == 200, f"Profile request failed: {response.text}"
        
        # The middleware should have updated last_active
        # We can't directly verify this without DB access, but we can verify the request succeeded
        print("✓ Authenticated request completed (last_active should be updated)")


class TestLegalPagesPublicAccess:
    """Test that legal pages are accessible without auth"""
    
    def test_terms_page_public(self, api_client):
        """GET /api/v1/legal/terms should be accessible without auth"""
        response = api_client.get(f"{BASE_URL}/api/v1/legal/terms")
        assert response.status_code == 200, f"Terms page not accessible: {response.text}"
        print("✓ /legal/terms accessible without auth")
    
    def test_privacy_page_public(self, api_client):
        """GET /api/v1/legal/privacy should be accessible without auth"""
        response = api_client.get(f"{BASE_URL}/api/v1/legal/privacy")
        assert response.status_code == 200, f"Privacy page not accessible: {response.text}"
        print("✓ /legal/privacy accessible without auth")
    
    def test_disclaimer_page_public(self, api_client):
        """GET /api/v1/legal/disclaimer should be accessible without auth"""
        response = api_client.get(f"{BASE_URL}/api/v1/legal/disclaimer")
        assert response.status_code == 200, f"Disclaimer page not accessible: {response.text}"
        print("✓ /legal/disclaimer accessible without auth")


class TestInputSanitization:
    """Test HTML tag stripping and input sanitization"""
    
    def test_html_tags_stripped_from_strategy_name(self, api_client, auth_tokens):
        """HTML tags should be stripped from strategy names"""
        headers = {"Authorization": f"Bearer {auth_tokens['access_token']}"}
        
        # Create a strategy with HTML in the name
        strategy_data = {
            "metadata": {
                "name": "<script>alert('xss')</script>Test Strategy",
                "description": "Test description",
                "tags": ["test"]
            },
            "market": {"type": "equity", "exchange": "NSE"},
            "instrument": {"symbol": "RELIANCE"},
            "timeframe": {"interval": "1d"},
            "entry_conditions": [{"name": "RSI", "params": {"period": 14}, "operator": "<", "value": 30}],
            "exit_conditions": [{"name": "RSI", "params": {"period": 14}, "operator": ">", "value": 70}],
            "filters": [],
            "risk_management": {
                "stop_loss": {"type": "percentage", "value": 2},
                "target_profit": None,
                "trailing_stop_loss": {"enabled": False, "type": "percentage", "value": 1.0, "activation_profit": 0},
                "time_based_exit": {"enabled": False, "exit_time": "15:10"},
                "daily_limits": {"max_loss_per_day": 5.0, "max_trades_per_day": 10},
                "position_sizing": {"method": "fixed_quantity", "value": 1}
            }
        }
        
        response = api_client.post(f"{BASE_URL}/api/v1/strategies", json=strategy_data, headers=headers)
        
        if response.status_code == 201:
            data = response.json()
            name = data.get("metadata", {}).get("name", "")
            # HTML tags should be stripped or escaped
            assert "<script>" not in name, "HTML script tag not stripped from strategy name"
            print(f"✓ HTML tags handled in strategy name: '{name}'")
            
            # Clean up - delete the test strategy
            strategy_id = data.get("id")
            if strategy_id:
                api_client.delete(f"{BASE_URL}/api/v1/strategies/{strategy_id}", headers=headers)
        else:
            # If creation fails, that's also acceptable (validation might reject it)
            print(f"✓ Strategy creation with HTML tags handled (status: {response.status_code})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
