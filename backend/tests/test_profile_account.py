"""
Test Profile & Account Management Features - Iteration 26
Tests: Profile GET/PUT, Change Password, Forgot/Reset Password (OTP), Account Summary, Export Data, Delete Account
"""
import pytest
import requests
import os
import time
import re

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
TEST_USER_EMAIL = "testai@example.com"
TEST_USER_PASSWORD = "Password123!"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "Password123!"
SACRIFICIAL_USER_EMAIL = "systest5@example.com"
SACRIFICIAL_USER_PASSWORD = "Test1234!"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def auth_token(api_client):
    """Get authentication token for test user"""
    response = api_client.post(f"{BASE_URL}/api/v1/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Authentication failed for {TEST_USER_EMAIL}")


@pytest.fixture(scope="module")
def authenticated_client(api_client, auth_token):
    """Session with auth header"""
    api_client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api_client


# =============================================================================
# PROFILE GET/PUT TESTS
# =============================================================================

class TestProfileEndpoints:
    """Profile GET and PUT endpoint tests"""

    def test_get_profile_returns_full_data(self, authenticated_client):
        """GET /api/v1/account/profile returns full profile with all expected fields"""
        response = authenticated_client.get(f"{BASE_URL}/api/v1/account/profile")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify all required fields are present
        required_fields = [
            "user_id", "email", "display_name", "phone", "timezone",
            "default_capital", "preferred_instruments", "notification_preferences",
            "avatar_initial", "account_mode", "created_at"
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        # Verify avatar_initial is computed correctly
        assert len(data["avatar_initial"]) == 1
        assert data["avatar_initial"].isupper()
        
        print(f"✓ Profile GET returns all fields: {list(data.keys())}")

    def test_update_profile_display_name(self, authenticated_client):
        """PUT /api/v1/account/profile updates display_name"""
        response = authenticated_client.put(f"{BASE_URL}/api/v1/account/profile", json={
            "display_name": "Test User Updated"
        })
        assert response.status_code == 200
        assert "display_name" in response.json().get("updated_fields", [])
        
        # Verify change persisted
        get_response = authenticated_client.get(f"{BASE_URL}/api/v1/account/profile")
        assert get_response.json()["display_name"] == "Test User Updated"
        
        # Restore original
        authenticated_client.put(f"{BASE_URL}/api/v1/account/profile", json={
            "display_name": "Test User"
        })
        print("✓ Profile display_name update works")

    def test_update_profile_phone_valid(self, authenticated_client):
        """PUT /api/v1/account/profile accepts valid phone format"""
        response = authenticated_client.put(f"{BASE_URL}/api/v1/account/profile", json={
            "phone": "+91 9876543210"
        })
        assert response.status_code == 200
        
        # Verify persisted
        get_response = authenticated_client.get(f"{BASE_URL}/api/v1/account/profile")
        assert get_response.json()["phone"] == "+91 9876543210"
        print("✓ Profile phone update works")

    def test_update_profile_phone_invalid(self, authenticated_client):
        """PUT /api/v1/account/profile rejects invalid phone format"""
        response = authenticated_client.put(f"{BASE_URL}/api/v1/account/profile", json={
            "phone": "invalid"
        })
        assert response.status_code == 400
        assert "phone" in response.json().get("detail", "").lower()
        print("✓ Invalid phone format rejected")

    def test_update_profile_timezone_valid(self, authenticated_client):
        """PUT /api/v1/account/profile accepts valid timezone"""
        response = authenticated_client.put(f"{BASE_URL}/api/v1/account/profile", json={
            "timezone": "America/New_York"
        })
        assert response.status_code == 200
        
        # Verify and restore
        get_response = authenticated_client.get(f"{BASE_URL}/api/v1/account/profile")
        assert get_response.json()["timezone"] == "America/New_York"
        
        authenticated_client.put(f"{BASE_URL}/api/v1/account/profile", json={
            "timezone": "Asia/Kolkata"
        })
        print("✓ Profile timezone update works")

    def test_update_profile_timezone_invalid(self, authenticated_client):
        """PUT /api/v1/account/profile rejects invalid timezone"""
        response = authenticated_client.put(f"{BASE_URL}/api/v1/account/profile", json={
            "timezone": "Invalid/Timezone"
        })
        assert response.status_code == 400
        assert "timezone" in response.json().get("detail", "").lower()
        print("✓ Invalid timezone rejected")

    def test_update_profile_capital_valid(self, authenticated_client):
        """PUT /api/v1/account/profile accepts valid capital > 0"""
        response = authenticated_client.put(f"{BASE_URL}/api/v1/account/profile", json={
            "default_capital": 500000
        })
        assert response.status_code == 200
        
        get_response = authenticated_client.get(f"{BASE_URL}/api/v1/account/profile")
        assert get_response.json()["default_capital"] == 500000
        
        # Restore
        authenticated_client.put(f"{BASE_URL}/api/v1/account/profile", json={
            "default_capital": 100000
        })
        print("✓ Profile capital update works")

    def test_update_profile_capital_invalid(self, authenticated_client):
        """PUT /api/v1/account/profile rejects capital <= 0"""
        response = authenticated_client.put(f"{BASE_URL}/api/v1/account/profile", json={
            "default_capital": 0
        })
        assert response.status_code == 400
        
        response2 = authenticated_client.put(f"{BASE_URL}/api/v1/account/profile", json={
            "default_capital": -1000
        })
        assert response2.status_code == 400
        print("✓ Invalid capital rejected")

    def test_update_profile_instruments(self, authenticated_client):
        """PUT /api/v1/account/profile updates preferred_instruments"""
        response = authenticated_client.put(f"{BASE_URL}/api/v1/account/profile", json={
            "preferred_instruments": ["RELIANCE", "TCS", "INFY"]
        })
        assert response.status_code == 200
        
        get_response = authenticated_client.get(f"{BASE_URL}/api/v1/account/profile")
        instruments = get_response.json()["preferred_instruments"]
        assert "RELIANCE" in instruments
        assert "TCS" in instruments
        print("✓ Profile instruments update works")

    def test_update_profile_notifications(self, authenticated_client):
        """PUT /api/v1/account/profile updates notification_preferences"""
        response = authenticated_client.put(f"{BASE_URL}/api/v1/account/profile", json={
            "notification_preferences": {
                "email_on_backtest_complete": True,
                "email_on_paper_trade_signal": False,
                "email_weekly_summary": True
            }
        })
        assert response.status_code == 200
        
        get_response = authenticated_client.get(f"{BASE_URL}/api/v1/account/profile")
        prefs = get_response.json()["notification_preferences"]
        assert prefs["email_on_backtest_complete"] == True
        assert prefs["email_on_paper_trade_signal"] == False
        assert prefs["email_weekly_summary"] == True
        print("✓ Profile notification preferences update works")


# =============================================================================
# CHANGE PASSWORD TESTS
# =============================================================================

class TestChangePassword:
    """Change password endpoint tests"""

    def test_change_password_wrong_current(self, authenticated_client):
        """PUT /api/v1/profile/change-password with wrong current password returns 400"""
        response = authenticated_client.put(f"{BASE_URL}/api/v1/profile/change-password", json={
            "current_password": "WrongPassword123!",
            "new_password": "NewPassword123!"
        })
        assert response.status_code == 400
        assert "incorrect" in response.json().get("detail", "").lower()
        print("✓ Wrong current password returns 400")

    def test_change_password_success(self, api_client):
        """PUT /api/v1/profile/change-password with correct password changes it"""
        # Login fresh
        login_resp = api_client.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]
        
        # Change password
        change_resp = api_client.put(
            f"{BASE_URL}/api/v1/profile/change-password",
            json={
                "current_password": TEST_USER_PASSWORD,
                "new_password": "NewPassword123!"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        assert change_resp.status_code == 200
        assert change_resp.json()["success"] == True
        print("✓ Password changed successfully")
        
        # Verify can login with new password
        new_login = api_client.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": "NewPassword123!"
        })
        assert new_login.status_code == 200
        print("✓ Can login with new password")
        
        # RESTORE original password
        restore_token = new_login.json()["access_token"]
        restore_resp = api_client.put(
            f"{BASE_URL}/api/v1/profile/change-password",
            json={
                "current_password": "NewPassword123!",
                "new_password": TEST_USER_PASSWORD
            },
            headers={"Authorization": f"Bearer {restore_token}"}
        )
        assert restore_resp.status_code == 200
        print("✓ Password restored to original")


# =============================================================================
# FORGOT/RESET PASSWORD (OTP) TESTS
# =============================================================================

class TestForgotResetPassword:
    """Forgot password and reset password OTP flow tests"""

    def test_forgot_password_returns_200_regardless(self, api_client):
        """POST /api/v1/auth/forgot-password returns 200 regardless of email existence"""
        # Existing email
        response1 = api_client.post(f"{BASE_URL}/api/v1/auth/forgot-password", json={
            "email": TEST_USER_EMAIL
        })
        assert response1.status_code == 200
        assert response1.json()["success"] == True
        print("✓ Forgot password returns 200 for existing email")
        
        # Non-existing email
        response2 = api_client.post(f"{BASE_URL}/api/v1/auth/forgot-password", json={
            "email": "nonexistent@example.com"
        })
        assert response2.status_code == 200
        assert response2.json()["success"] == True
        print("✓ Forgot password returns 200 for non-existing email (no leak)")

    def test_reset_password_wrong_otp(self, api_client):
        """POST /api/v1/auth/reset-password with wrong OTP returns 400"""
        response = api_client.post(f"{BASE_URL}/api/v1/auth/reset-password", json={
            "email": TEST_USER_EMAIL,
            "otp": "000000",
            "new_password": "NewPassword123!"
        })
        assert response.status_code == 400
        assert "invalid" in response.json().get("detail", "").lower() or "expired" in response.json().get("detail", "").lower()
        print("✓ Wrong OTP returns 400")

    def test_reset_password_correct_otp(self, api_client):
        """POST /api/v1/auth/reset-password with correct OTP resets password"""
        # Create a test user for this flow
        test_email = f"otp_test_{int(time.time())}@example.com"
        test_password = "InitialPass123!"
        
        # Register
        reg_resp = api_client.post(f"{BASE_URL}/api/v1/auth/register", json={
            "email": test_email,
            "password": test_password
        })
        assert reg_resp.status_code == 201
        
        # Request OTP
        forgot_resp = api_client.post(f"{BASE_URL}/api/v1/auth/forgot-password", json={
            "email": test_email
        })
        assert forgot_resp.status_code == 200
        
        # Read OTP from backend logs
        time.sleep(0.5)  # Give time for log to be written
        try:
            with open("/var/log/supervisor/backend.out.log", "r") as f:
                logs = f.read()
            # Find the OTP for this email
            pattern = rf"\[PASSWORD_RESET_OTP\] email={test_email} otp=(\d{{6}})"
            match = re.search(pattern, logs)
            if not match:
                pytest.skip("Could not find OTP in logs - EMAIL_ENABLED may be true")
            otp = match.group(1)
        except FileNotFoundError:
            pytest.skip("Backend log file not found")
        
        # Reset with correct OTP
        new_password = "ResetPass123!"
        reset_resp = api_client.post(f"{BASE_URL}/api/v1/auth/reset-password", json={
            "email": test_email,
            "otp": otp,
            "new_password": new_password
        })
        assert reset_resp.status_code == 200
        assert reset_resp.json()["success"] == True
        print(f"✓ Password reset with correct OTP for {test_email}")
        
        # Verify can login with new password
        login_resp = api_client.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": test_email,
            "password": new_password
        })
        assert login_resp.status_code == 200
        print("✓ Can login with reset password")
        
        return test_email, otp

    def test_reset_password_reused_otp(self, api_client):
        """POST /api/v1/auth/reset-password with reused OTP returns 400"""
        # Create a test user
        test_email = f"otp_reuse_{int(time.time())}@example.com"
        test_password = "InitialPass123!"
        
        # Register
        api_client.post(f"{BASE_URL}/api/v1/auth/register", json={
            "email": test_email,
            "password": test_password
        })
        
        # Request OTP
        api_client.post(f"{BASE_URL}/api/v1/auth/forgot-password", json={
            "email": test_email
        })
        
        time.sleep(0.5)
        try:
            with open("/var/log/supervisor/backend.out.log", "r") as f:
                logs = f.read()
            pattern = rf"\[PASSWORD_RESET_OTP\] email={test_email} otp=(\d{{6}})"
            match = re.search(pattern, logs)
            if not match:
                pytest.skip("Could not find OTP in logs")
            otp = match.group(1)
        except FileNotFoundError:
            pytest.skip("Backend log file not found")
        
        # First reset - should succeed
        reset1 = api_client.post(f"{BASE_URL}/api/v1/auth/reset-password", json={
            "email": test_email,
            "otp": otp,
            "new_password": "NewPass123!"
        })
        assert reset1.status_code == 200
        print("✓ First OTP use succeeds")
        
        # Second reset with same OTP - should fail
        reset2 = api_client.post(f"{BASE_URL}/api/v1/auth/reset-password", json={
            "email": test_email,
            "otp": otp,
            "new_password": "AnotherPass123!"
        })
        assert reset2.status_code == 400
        print("✓ Reused OTP returns 400")


# =============================================================================
# ACCOUNT SUMMARY TESTS
# =============================================================================

class TestAccountSummary:
    """Account summary endpoint tests"""

    def test_account_summary_returns_data(self, authenticated_client):
        """GET /api/v1/account/summary returns account stats"""
        response = authenticated_client.get(f"{BASE_URL}/api/v1/account/summary")
        assert response.status_code == 200
        
        data = response.json()
        required_fields = [
            "account_mode", "total_strategies_real", "total_strategies_demo",
            "total_backtests", "total_paper_trades", "member_since", "email"
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        assert data["email"] == TEST_USER_EMAIL
        print(f"✓ Account summary: mode={data['account_mode']}, strategies={data['total_strategies_real']}")


# =============================================================================
# EXPORT DATA TESTS
# =============================================================================

class TestExportData:
    """Export data endpoint tests"""

    def test_export_data_returns_json(self, authenticated_client):
        """POST /api/v1/account/export-data returns JSON with user data"""
        response = authenticated_client.post(f"{BASE_URL}/api/v1/account/export-data")
        assert response.status_code == 200
        
        data = response.json()
        required_fields = [
            "exported_at", "user", "strategies", "paper_trades",
            "performance_records", "total_strategies"
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        assert "email" in data["user"]
        assert isinstance(data["strategies"], list)
        assert isinstance(data["paper_trades"], list)
        assert isinstance(data["performance_records"], list)
        print(f"✓ Export data: {data['total_strategies']} strategies, {data['total_paper_trades']} paper trades")


# =============================================================================
# DELETE ACCOUNT TESTS
# =============================================================================

class TestDeleteAccount:
    """Delete account (soft delete) endpoint tests"""

    def test_delete_account_wrong_password(self, api_client):
        """DELETE /api/v1/account with wrong password returns 400"""
        # Login as sacrificial user
        login_resp = api_client.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": SACRIFICIAL_USER_EMAIL,
            "password": SACRIFICIAL_USER_PASSWORD
        })
        if login_resp.status_code != 200:
            # Create the user if doesn't exist
            reg_resp = api_client.post(f"{BASE_URL}/api/v1/auth/register", json={
                "email": SACRIFICIAL_USER_EMAIL,
                "password": SACRIFICIAL_USER_PASSWORD
            })
            if reg_resp.status_code not in [201, 409]:
                pytest.skip(f"Could not create sacrificial user: {reg_resp.text}")
            login_resp = api_client.post(f"{BASE_URL}/api/v1/auth/login", json={
                "email": SACRIFICIAL_USER_EMAIL,
                "password": SACRIFICIAL_USER_PASSWORD
            })
        
        if login_resp.status_code != 200:
            pytest.skip("Could not login as sacrificial user")
        
        token = login_resp.json()["access_token"]
        
        # Try delete with wrong password
        delete_resp = api_client.delete(
            f"{BASE_URL}/api/v1/account",
            json={"password": "WrongPassword123!"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert delete_resp.status_code == 400
        assert "incorrect" in delete_resp.json().get("detail", "").lower()
        print("✓ Delete with wrong password returns 400")

    def test_delete_account_correct_password(self, api_client):
        """DELETE /api/v1/account with correct password soft-deletes account"""
        # Create a new user specifically for deletion
        delete_email = f"delete_test_{int(time.time())}@example.com"
        delete_password = "DeleteMe123!"
        
        # Register
        reg_resp = api_client.post(f"{BASE_URL}/api/v1/auth/register", json={
            "email": delete_email,
            "password": delete_password
        })
        assert reg_resp.status_code == 201
        
        # Login
        login_resp = api_client.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": delete_email,
            "password": delete_password
        })
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]
        
        # Delete account
        delete_resp = api_client.delete(
            f"{BASE_URL}/api/v1/account",
            json={"password": delete_password},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert delete_resp.status_code == 200
        assert delete_resp.json()["success"] == True
        print(f"✓ Account {delete_email} soft-deleted")
        
        # Verify login is blocked
        blocked_login = api_client.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": delete_email,
            "password": delete_password
        })
        assert blocked_login.status_code == 401
        assert "deactivated" in blocked_login.json().get("detail", "").lower()
        print("✓ Subsequent login blocked with 'Account deactivated'")


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
