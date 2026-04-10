"""
Test suite for Iteration 33 - Code Quality Refactor
Tests:
1. Auth module refactored (login, register)
2. Circular import resolved (legal.py imports from consent_utils.py)
3. Knowledge base returns 30 entries
4. Legal endpoints work correctly
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
TEST_USER_EMAIL = "testai@example.com"
TEST_USER_PASSWORD = "Password123!"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "Password123!"


class TestAuthModuleRefactored:
    """Test auth.py after refactoring (moved logger/secrets to top, OTP uses secrets.randbelow)"""
    
    def test_login_success(self):
        """POST /api/v1/auth/login works after auth module refactored"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "Missing access_token in response"
        assert "refresh_token" in data, "Missing refresh_token in response"
        assert data.get("token_type") == "bearer"
        print(f"PASS: Login successful, got access_token")
    
    def test_login_invalid_credentials(self):
        """Login with wrong password returns 401"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": TEST_USER_EMAIL, "password": "WrongPassword123!"}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print(f"PASS: Invalid credentials correctly rejected")
    
    def test_admin_login_success(self):
        """Admin login works"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        print(f"PASS: Admin login successful")


class TestConsentUtilsExtracted:
    """Test that consent_utils.py extraction resolved circular import"""
    
    def test_legal_versions_endpoint(self):
        """GET /api/v1/legal/versions returns 4 docs (circular import resolved)"""
        response = requests.get(f"{BASE_URL}/api/v1/legal/versions")
        assert response.status_code == 200, f"Legal versions failed: {response.text}"
        data = response.json()
        # Should have terms, privacy, disclaimer, cookies
        expected_types = {"terms", "privacy", "disclaimer", "cookies"}
        actual_types = set(data.keys())
        assert expected_types.issubset(actual_types), f"Missing doc types. Got: {actual_types}"
        print(f"PASS: Legal versions returns {len(data)} document types: {list(data.keys())}")
    
    def test_legal_terms_endpoint(self):
        """GET /api/v1/legal/terms returns terms document"""
        response = requests.get(f"{BASE_URL}/api/v1/legal/terms")
        assert response.status_code == 200, f"Terms endpoint failed: {response.text}"
        data = response.json()
        assert "content_md" in data, "Missing content_md"
        assert "version" in data, "Missing version"
        print(f"PASS: Terms document returned, version: {data.get('version')}")
    
    def test_legal_privacy_endpoint(self):
        """GET /api/v1/legal/privacy returns privacy document"""
        response = requests.get(f"{BASE_URL}/api/v1/legal/privacy")
        assert response.status_code == 200, f"Privacy endpoint failed: {response.text}"
        data = response.json()
        assert "content_md" in data
        print(f"PASS: Privacy document returned")
    
    def test_legal_disclaimer_endpoint(self):
        """GET /api/v1/legal/disclaimer returns disclaimer document"""
        response = requests.get(f"{BASE_URL}/api/v1/legal/disclaimer")
        assert response.status_code == 200, f"Disclaimer endpoint failed: {response.text}"
        data = response.json()
        assert "content_md" in data
        print(f"PASS: Disclaimer document returned")


class TestLegalConsentWithAuth:
    """Test consent endpoints that require authentication"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token for test user"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        if response.status_code != 200:
            pytest.skip("Could not authenticate test user")
        return response.json()["access_token"]
    
    def test_consent_status_with_auth(self, auth_token):
        """GET /api/v1/legal/consent-status works with auth token"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/v1/legal/consent-status", headers=headers)
        assert response.status_code == 200, f"Consent status failed: {response.text}"
        data = response.json()
        assert "all_accepted" in data, "Missing all_accepted field"
        assert "pending" in data, "Missing pending field"
        print(f"PASS: Consent status returned, all_accepted: {data.get('all_accepted')}")
    
    def test_accept_consent(self, auth_token):
        """POST /api/v1/legal/accept works"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        # First get the latest version
        versions_resp = requests.get(f"{BASE_URL}/api/v1/legal/versions")
        versions = versions_resp.json()
        
        # Accept terms
        response = requests.post(
            f"{BASE_URL}/api/v1/legal/accept",
            headers=headers,
            json={
                "document_type": "terms",
                "document_version": versions.get("terms", "1.0")
            }
        )
        assert response.status_code == 200, f"Accept consent failed: {response.text}"
        data = response.json()
        assert data.get("success") == True
        print(f"PASS: Accept consent endpoint works")


class TestKnowledgeBase:
    """Test knowledge base returns 30 entries"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        if response.status_code != 200:
            pytest.skip("Could not authenticate")
        return response.json()["access_token"]
    
    def test_knowledge_returns_30_entries(self, auth_token):
        """GET /api/v1/knowledge returns 30 entries"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/v1/knowledge", headers=headers)
        assert response.status_code == 200, f"Knowledge endpoint failed: {response.text}"
        data = response.json()
        entries = data.get("entries", [])
        assert len(entries) == 30, f"Expected 30 entries, got {len(entries)}"
        print(f"PASS: Knowledge base returns {len(entries)} entries")
    
    def test_knowledge_entry_structure(self, auth_token):
        """Knowledge entries have correct structure"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/v1/knowledge", headers=headers)
        assert response.status_code == 200
        data = response.json()
        entries = data.get("entries", [])
        if entries:
            entry = entries[0]
            assert "term_id" in entry, "Missing term_id"
            assert "term" in entry, "Missing term"
            assert "short_description" in entry, "Missing short_description"
            assert "category" in entry, "Missing category"
            print(f"PASS: Knowledge entry structure is correct")


class TestRegisterEndpoint:
    """Test registration endpoint (consent_utils extracted)"""
    
    def test_register_requires_consents(self):
        """POST /api/v1/auth/register requires legal consents"""
        import uuid
        test_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/register",
            json={
                "email": test_email,
                "password": "TestPass123!",
                "accepted_terms": False,
                "accepted_privacy": False,
                "accepted_disclaimer": False
            }
        )
        # Should fail because consents not accepted
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print(f"PASS: Register correctly requires legal consents")


class TestHealthAndBasics:
    """Basic health checks"""
    
    def test_health_endpoint(self):
        """Health endpoint works"""
        response = requests.get(f"{BASE_URL}/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"PASS: Health endpoint returns healthy")
    
    def test_strategies_endpoint(self):
        """Strategies endpoint works with auth"""
        # Login first
        login_resp = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        if login_resp.status_code != 200:
            pytest.skip("Could not authenticate")
        token = login_resp.json()["access_token"]
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/v1/strategies", headers=headers)
        assert response.status_code == 200, f"Strategies failed: {response.text}"
        data = response.json()
        assert "strategies" in data
        print(f"PASS: Strategies endpoint works, found {len(data.get('strategies', []))} strategies")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
