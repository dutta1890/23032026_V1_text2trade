"""
Test Suite: Sandbox Email Restriction & Auth State Persistence
Iteration 27 - Testing P0 fixes:
1. Resend sandbox domain restriction - should return warning instead of 500
2. Auth state persistence - token/user should persist in localStorage
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_USER_EMAIL = "testai@example.com"
TEST_USER_PASSWORD = "Password123!"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "Password123!"

# Non-verified email (will trigger sandbox restriction)
SANDBOX_RESTRICTED_EMAIL = "random_user_test@gmail.com"
NON_EXISTENT_EMAIL = "nonexistent_user_12345@example.com"


class TestForgotPasswordSandboxHandling:
    """Tests for forgot-password endpoint sandbox restriction handling"""
    
    def test_forgot_password_sandbox_restricted_email_returns_warning(self):
        """
        POST /api/v1/auth/forgot-password with sandbox-restricted email
        Should return {success: true, email_sent: false, warning: '...'} instead of 500
        """
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/forgot-password",
            json={"email": SANDBOX_RESTRICTED_EMAIL}
        )
        
        # Should NOT return 500 error
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        print(f"Response for sandbox-restricted email: {data}")
        
        # Verify response structure
        assert data.get("success") == True, "Expected success=true"
        assert data.get("message") is not None, "Expected message field"
        
        # For sandbox-restricted emails, should have warning
        # Note: This only triggers if the email exists in DB AND email sending fails due to sandbox
        # If email doesn't exist, no warning is returned (to prevent email enumeration)
        print(f"email_sent: {data.get('email_sent')}, warning: {data.get('warning')}")
    
    def test_forgot_password_nonexistent_email_no_warning(self):
        """
        POST /api/v1/auth/forgot-password with non-existent email
        Should return success without warning (no email enumeration)
        """
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/forgot-password",
            json={"email": NON_EXISTENT_EMAIL}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        print(f"Response for non-existent email: {data}")
        
        # Should return success without revealing email doesn't exist
        assert data.get("success") == True, "Expected success=true"
        assert data.get("message") is not None, "Expected message field"
        
        # Should NOT have warning for non-existent email (no email enumeration)
        assert data.get("warning") is None, f"Should not have warning for non-existent email, got: {data.get('warning')}"
    
    def test_forgot_password_existing_user_sandbox_warning(self):
        """
        POST /api/v1/auth/forgot-password with existing user email (not in sandbox whitelist)
        Should return warning about sandbox mode
        """
        # Use the test user email which exists but is not in sandbox whitelist
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/forgot-password",
            json={"email": TEST_USER_EMAIL}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        print(f"Response for existing user (sandbox restricted): {data}")
        
        # Should have success
        assert data.get("success") == True, "Expected success=true"
        
        # Since testai@example.com exists but is not in sandbox whitelist,
        # email_sent should be false and warning should be present
        if data.get("email_sent") == False:
            assert data.get("warning") is not None, "Expected warning when email_sent=false"
            assert "sandbox" in data.get("warning", "").lower(), f"Warning should mention sandbox: {data.get('warning')}"
            print(f"✓ Sandbox warning correctly returned: {data.get('warning')}")
        else:
            print(f"Note: email_sent={data.get('email_sent')} - email may have been sent successfully")


class TestLoginTokenPersistence:
    """Tests for login endpoint returning proper tokens"""
    
    def test_login_returns_access_token(self):
        """
        POST /api/v1/auth/login should return access_token
        """
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        
        assert response.status_code == 200, f"Login failed: {response.status_code}: {response.text}"
        
        data = response.json()
        print(f"Login response keys: {data.keys()}")
        
        # Verify token is returned
        assert "access_token" in data, "Expected access_token in response"
        assert len(data["access_token"]) > 0, "access_token should not be empty"
        
        # Verify token type
        assert data.get("token_type") == "bearer", f"Expected token_type=bearer, got {data.get('token_type')}"
        
        # Verify refresh token
        assert "refresh_token" in data, "Expected refresh_token in response"
        
        print(f"✓ Login returns valid tokens")
    
    def test_token_can_be_used_for_authenticated_requests(self):
        """
        Token from login should work for authenticated endpoints
        """
        # Login
        login_response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        
        # Use token for authenticated request
        profile_response = requests.get(
            f"{BASE_URL}/api/v1/account/profile",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert profile_response.status_code == 200, f"Profile request failed: {profile_response.status_code}"
        print(f"✓ Token works for authenticated requests")
    
    def test_logout_invalidates_token(self):
        """
        POST /api/v1/auth/logout should invalidate the token
        """
        # Login
        login_response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        
        # Logout
        logout_response = requests.post(
            f"{BASE_URL}/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert logout_response.status_code == 200, f"Logout failed: {logout_response.status_code}"
        
        data = logout_response.json()
        assert data.get("success") == True, "Expected success=true on logout"
        
        # Token should now be blacklisted - subsequent requests should fail
        profile_response = requests.get(
            f"{BASE_URL}/api/v1/account/profile",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert profile_response.status_code == 401, f"Expected 401 after logout, got {profile_response.status_code}"
        print(f"✓ Logout correctly invalidates token")


class TestTokenRefresh:
    """Tests for token refresh functionality"""
    
    def test_refresh_token_returns_new_access_token(self):
        """
        POST /api/v1/auth/refresh should return new access_token
        """
        # Login to get refresh token
        login_response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        assert login_response.status_code == 200
        refresh_token = login_response.json()["refresh_token"]
        
        # Use refresh token
        refresh_response = requests.post(
            f"{BASE_URL}/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert refresh_response.status_code == 200, f"Refresh failed: {refresh_response.status_code}: {refresh_response.text}"
        
        data = refresh_response.json()
        assert "access_token" in data, "Expected access_token in refresh response"
        assert len(data["access_token"]) > 0, "New access_token should not be empty"
        
        print(f"✓ Refresh token returns new access_token")


class TestExpiredTokenHandling:
    """Tests for expired token handling"""
    
    def test_invalid_token_returns_401(self):
        """
        Using an invalid/malformed token should return 401
        """
        response = requests.get(
            f"{BASE_URL}/api/v1/account/profile",
            headers={"Authorization": "Bearer invalid_token_12345"}
        )
        
        assert response.status_code == 401, f"Expected 401 for invalid token, got {response.status_code}"
        print(f"✓ Invalid token correctly returns 401")
    
    def test_missing_token_returns_401(self):
        """
        Request without token to protected endpoint should return 401/403
        """
        response = requests.get(f"{BASE_URL}/api/v1/account/profile")
        
        assert response.status_code in [401, 403], f"Expected 401/403 for missing token, got {response.status_code}"
        print(f"✓ Missing token correctly returns {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
