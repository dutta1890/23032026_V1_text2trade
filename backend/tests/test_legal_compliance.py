"""
Legal Compliance System Tests - Iteration 29
Tests for:
- Legal document API endpoints (public GET, admin PUT)
- User consent tracking on registration
- Consent status checking
- Re-consent flow after document updates
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "Password123!"
TEST_USER_EMAIL = "testai@example.com"
TEST_USER_PASSWORD = "Password123!"


class TestLegalDocumentsPublicEndpoints:
    """Test public legal document endpoints (no auth required)"""
    
    def test_get_terms_returns_markdown_content(self):
        """GET /api/v1/legal/terms returns markdown content, version, effective_date"""
        response = requests.get(f"{BASE_URL}/api/v1/legal/terms")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "content_md" in data, "Response should contain content_md"
        assert "version" in data, "Response should contain version"
        assert "effective_date" in data, "Response should contain effective_date"
        assert len(data["content_md"]) > 10, "Content should have some markdown"
        print(f"✓ Terms v{data['version']} returned with {len(data['content_md'])} chars")
    
    def test_get_privacy_returns_markdown_content(self):
        """GET /api/v1/legal/privacy returns privacy policy"""
        response = requests.get(f"{BASE_URL}/api/v1/legal/privacy")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "content_md" in data, "Response should contain content_md"
        assert "version" in data, "Response should contain version"
        assert "Privacy" in data["content_md"] or "privacy" in data["content_md"].lower(), "Content should mention privacy"
        print(f"✓ Privacy v{data['version']} returned")
    
    def test_get_disclaimer_returns_markdown_content(self):
        """GET /api/v1/legal/disclaimer returns risk disclaimer"""
        response = requests.get(f"{BASE_URL}/api/v1/legal/disclaimer")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "content_md" in data, "Response should contain content_md"
        assert "version" in data, "Response should contain version"
        print(f"✓ Disclaimer v{data['version']} returned")
    
    def test_get_cookies_returns_markdown_content(self):
        """GET /api/v1/legal/cookies returns cookie policy"""
        response = requests.get(f"{BASE_URL}/api/v1/legal/cookies")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "content_md" in data, "Response should contain content_md"
        print(f"✓ Cookies v{data['version']} returned")
    
    def test_get_versions_returns_all_document_versions(self):
        """GET /api/v1/legal/versions returns all 4 document versions"""
        response = requests.get(f"{BASE_URL}/api/v1/legal/versions")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "terms" in data, "Should have terms version"
        assert "privacy" in data, "Should have privacy version"
        assert "disclaimer" in data, "Should have disclaimer version"
        assert "cookies" in data, "Should have cookies version"
        print(f"✓ Versions: terms={data['terms']}, privacy={data['privacy']}, disclaimer={data['disclaimer']}, cookies={data['cookies']}")


class TestRegistrationConsentValidation:
    """Test registration requires all consents"""
    
    def test_register_without_consents_returns_400(self):
        """POST /api/v1/auth/register without accepted_terms/privacy/disclaimer returns 400"""
        unique_email = f"test_noconsent_{uuid.uuid4().hex[:8]}@example.com"
        response = requests.post(f"{BASE_URL}/api/v1/auth/register", json={
            "email": unique_email,
            "password": "Password123!",
            "accepted_terms": False,
            "accepted_privacy": False,
            "accepted_disclaimer": False,
        })
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "detail" in data, "Should have error detail"
        assert "Terms" in data["detail"] or "accept" in data["detail"].lower(), "Error should mention consent requirement"
        print(f"✓ Registration without consents rejected: {data['detail']}")
    
    def test_register_with_partial_consents_returns_400(self):
        """POST /api/v1/auth/register with only some consents returns 400"""
        unique_email = f"test_partial_{uuid.uuid4().hex[:8]}@example.com"
        response = requests.post(f"{BASE_URL}/api/v1/auth/register", json={
            "email": unique_email,
            "password": "Password123!",
            "accepted_terms": True,
            "accepted_privacy": True,
            "accepted_disclaimer": False,  # Missing disclaimer
        })
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        print("✓ Registration with partial consents rejected")
    
    def test_register_with_all_consents_succeeds(self):
        """POST /api/v1/auth/register with all consents=true succeeds"""
        unique_email = f"test_consent_{uuid.uuid4().hex[:8]}@example.com"
        response = requests.post(f"{BASE_URL}/api/v1/auth/register", json={
            "email": unique_email,
            "password": "Password123!",
            "accepted_terms": True,
            "accepted_privacy": True,
            "accepted_disclaimer": True,
        })
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "user_id" in data, "Should return user_id"
        assert "email" in data, "Should return email"
        print(f"✓ Registration with all consents succeeded: user_id={data['user_id']}")
        return data["user_id"], unique_email


class TestConsentStatusEndpoint:
    """Test consent status checking for authenticated users"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD,
        })
        if response.status_code != 200:
            pytest.skip(f"Admin login failed: {response.text}")
        return response.json()["access_token"]
    
    @pytest.fixture
    def new_user_with_consents(self):
        """Create a new user with all consents and return token"""
        unique_email = f"test_newconsent_{uuid.uuid4().hex[:8]}@example.com"
        reg_response = requests.post(f"{BASE_URL}/api/v1/auth/register", json={
            "email": unique_email,
            "password": "Password123!",
            "accepted_terms": True,
            "accepted_privacy": True,
            "accepted_disclaimer": True,
        })
        if reg_response.status_code != 201:
            pytest.skip(f"Registration failed: {reg_response.text}")
        
        login_response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": unique_email,
            "password": "Password123!",
        })
        if login_response.status_code != 200:
            pytest.skip(f"Login failed: {login_response.text}")
        
        return login_response.json()["access_token"]
    
    def test_consent_status_returns_all_accepted_for_new_user(self, new_user_with_consents):
        """GET /api/v1/legal/consent-status returns all_accepted:true for user with up-to-date consents"""
        token = new_user_with_consents
        response = requests.get(
            f"{BASE_URL}/api/v1/legal/consent-status",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "all_accepted" in data, "Should have all_accepted field"
        assert "pending" in data, "Should have pending field"
        # New user should have accepted latest versions
        assert data["all_accepted"] == True, f"New user should have all_accepted=True, got {data}"
        print(f"✓ Consent status for new user: all_accepted={data['all_accepted']}, pending={data['pending']}")
    
    def test_consent_status_requires_auth(self):
        """GET /api/v1/legal/consent-status requires authentication"""
        response = requests.get(f"{BASE_URL}/api/v1/legal/consent-status")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Consent status endpoint requires auth")


class TestAcceptConsentEndpoint:
    """Test accepting individual consent documents"""
    
    @pytest.fixture
    def user_token(self):
        """Get test user token"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD,
        })
        if response.status_code != 200:
            pytest.skip(f"Test user login failed: {response.text}")
        return response.json()["access_token"]
    
    def test_accept_consent_stores_record(self, user_token):
        """POST /api/v1/legal/accept stores consent record for specific doc+version"""
        # Get current versions
        versions_response = requests.get(f"{BASE_URL}/api/v1/legal/versions")
        versions = versions_response.json()
        
        response = requests.post(
            f"{BASE_URL}/api/v1/legal/accept",
            json={
                "document_type": "terms",
                "document_version": versions["terms"],
            },
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["success"] == True, "Should return success=True"
        print(f"✓ Accept consent returned: {data}")
    
    def test_accept_consent_requires_auth(self):
        """POST /api/v1/legal/accept requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/v1/legal/accept",
            json={"document_type": "terms", "document_version": "1.0"}
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Accept consent endpoint requires auth")
    
    def test_accept_invalid_document_type_returns_400(self, user_token):
        """POST /api/v1/legal/accept with invalid document type returns 400"""
        response = requests.post(
            f"{BASE_URL}/api/v1/legal/accept",
            json={"document_type": "invalid_type", "document_version": "1.0"},
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        print("✓ Invalid document type rejected")


class TestAdminLegalDocumentUpdate:
    """Test admin endpoints for updating legal documents"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD,
        })
        if response.status_code != 200:
            pytest.skip(f"Admin login failed: {response.text}")
        return response.json()["access_token"]
    
    @pytest.fixture
    def user_token(self):
        """Get regular user token"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD,
        })
        if response.status_code != 200:
            pytest.skip(f"User login failed: {response.text}")
        return response.json()["access_token"]
    
    def test_admin_update_terms_creates_new_version(self, admin_token):
        """PUT /api/v1/admin/legal/terms creates new version (admin only), old version preserved"""
        # Generate unique version to avoid conflicts
        new_version = f"test_{uuid.uuid4().hex[:6]}"
        
        response = requests.put(
            f"{BASE_URL}/api/v1/admin/legal/terms",
            json={
                "content_md": f"# Test Terms v{new_version}\n\nThis is a test version.",
                "version": new_version,
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["success"] == True, "Should return success=True"
        print(f"✓ Admin created new terms version: {new_version}")
        
        # Verify new version is now the latest
        versions_response = requests.get(f"{BASE_URL}/api/v1/legal/versions")
        versions = versions_response.json()
        assert versions["terms"] == new_version, f"Latest terms should be {new_version}, got {versions['terms']}"
        print(f"✓ New version is now latest: {versions['terms']}")
    
    def test_admin_update_requires_admin_role(self, user_token):
        """PUT /api/v1/admin/legal/terms requires admin role"""
        response = requests.put(
            f"{BASE_URL}/api/v1/admin/legal/terms",
            json={"content_md": "Test", "version": "test_unauthorized"},
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("✓ Non-admin user rejected from updating legal docs")
    
    def test_admin_update_duplicate_version_returns_409(self, admin_token):
        """PUT /api/v1/admin/legal/terms with existing version returns 409"""
        # First, get current version
        versions_response = requests.get(f"{BASE_URL}/api/v1/legal/versions")
        current_version = versions_response.json()["terms"]
        
        response = requests.put(
            f"{BASE_URL}/api/v1/admin/legal/terms",
            json={"content_md": "Duplicate test", "version": current_version},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 409, f"Expected 409, got {response.status_code}: {response.text}"
        print(f"✓ Duplicate version {current_version} rejected with 409")


class TestReconsentFlowAfterUpdate:
    """Test that users need to re-consent after document updates"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD,
        })
        if response.status_code != 200:
            pytest.skip(f"Admin login failed: {response.text}")
        return response.json()["access_token"]
    
    def test_consent_status_shows_pending_after_update(self, admin_token):
        """After admin updates terms, GET /api/v1/legal/consent-status returns pending:{terms: new_version}"""
        # Get current latest version BEFORE creating user
        versions_before = requests.get(f"{BASE_URL}/api/v1/legal/versions").json()
        print(f"Versions before user creation: {versions_before}")
        
        # Create a new user with current consents
        unique_email = f"test_reconsent_{uuid.uuid4().hex[:8]}@example.com"
        reg_response = requests.post(f"{BASE_URL}/api/v1/auth/register", json={
            "email": unique_email,
            "password": "Password123!",
            "accepted_terms": True,
            "accepted_privacy": True,
            "accepted_disclaimer": True,
        })
        assert reg_response.status_code == 201, f"Registration failed: {reg_response.text}"
        
        # Login as new user
        login_response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": unique_email,
            "password": "Password123!",
        })
        user_token = login_response.json()["access_token"]
        
        # Check consent status - should be all accepted
        status_response = requests.get(
            f"{BASE_URL}/api/v1/legal/consent-status",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        initial_status = status_response.json()
        print(f"Initial consent status: {initial_status}")
        assert initial_status["all_accepted"] == True, "New user should have all consents accepted initially"
        
        # Admin updates terms to new version with a version that will sort AFTER current
        # Use a version format that ensures it's "newer" in string sort (e.g., z_xxx)
        new_version = f"z_{uuid.uuid4().hex[:8]}"
        update_response = requests.put(
            f"{BASE_URL}/api/v1/admin/legal/terms",
            json={"content_md": f"# Updated Terms v{new_version}\n\nNew terms content.", "version": new_version},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert update_response.status_code == 200, f"Admin update failed: {update_response.text}"
        
        # Verify the new version is now the latest
        versions_after = requests.get(f"{BASE_URL}/api/v1/legal/versions").json()
        print(f"Versions after update: {versions_after}")
        assert versions_after["terms"] == new_version, f"Latest terms should be {new_version}, got {versions_after['terms']}"
        
        # Check consent status again - should show pending for terms
        status_response2 = requests.get(
            f"{BASE_URL}/api/v1/legal/consent-status",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        updated_status = status_response2.json()
        print(f"Updated consent status: {updated_status}")
        
        assert updated_status["all_accepted"] == False, "Should have all_accepted=False after update"
        assert "terms" in updated_status["pending"], "Should have terms in pending"
        assert updated_status["pending"]["terms"] == new_version, f"Pending terms should be {new_version}"
        print(f"✓ User needs to re-consent to terms v{new_version}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
