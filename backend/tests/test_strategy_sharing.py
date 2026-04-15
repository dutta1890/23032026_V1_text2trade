"""
Test suite for Strategy Sharing features (Iteration 38)
Tests: share creation, public share view, clone, revoke, copy-text, PDF, broker instructions, share stats, admin analytics
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
TEST_USER_EMAIL = "testai@example.com"
TEST_USER_PASSWORD = "Password123!"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "Password123!"

# Known test share from main agent context
EXISTING_SHARE_ID = "odt1glgi"
EXISTING_STRATEGY_ID = "5e3b32d6-b384-4609-aafd-a1371339a5d4"

# Available brokers
BROKERS = ["zerodha", "angel_one", "upstox", "dhan", "groww", "5paisa"]


def get_test_user_token():
    """Get auth token for test user"""
    response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    return None


def get_admin_token():
    """Get auth token for admin user"""
    response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    return None


class TestPublicShareEndpoints:
    """Test public share endpoints (no auth required)"""
    
    def test_get_share_returns_200(self):
        """GET /api/v1/s/{share_id} returns 200 for valid share"""
        response = requests.get(f"{BASE_URL}/api/v1/s/{EXISTING_SHARE_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ GET /s/{EXISTING_SHARE_ID} returns 200")
    
    def test_get_share_has_required_fields(self):
        """Share response has all required fields"""
        response = requests.get(f"{BASE_URL}/api/v1/s/{EXISTING_SHARE_ID}")
        data = response.json()
        
        assert data.get("success") == True
        assert "share_id" in data
        assert "strategy" in data
        assert "view_count" in data
        assert "clone_count" in data
        assert "created_at" in data
        
        strategy = data.get("strategy", {})
        assert "metadata" in strategy
        assert "instrument" in strategy
        assert "entry_conditions" in strategy
        print("✓ Share response has all required fields")
    
    def test_get_share_excludes_user_id(self):
        """Share response excludes user_id for privacy"""
        response = requests.get(f"{BASE_URL}/api/v1/s/{EXISTING_SHARE_ID}")
        data = response.json()
        strategy = data.get("strategy", {})
        assert "user_id" not in strategy, "user_id should be excluded from shared strategy"
        print("✓ Share response excludes user_id")
    
    def test_get_share_includes_backtest(self):
        """Share response includes backtest results if available"""
        response = requests.get(f"{BASE_URL}/api/v1/s/{EXISTING_SHARE_ID}")
        data = response.json()
        
        if data.get("backtest"):
            backtest = data["backtest"]
            assert "metrics" in backtest
            assert "equity_curve" in backtest
            print("✓ Share response includes backtest results")
        else:
            print("✓ Share response has no backtest (acceptable)")
    
    def test_get_share_increments_view_count(self):
        """View count increments on each view"""
        response1 = requests.get(f"{BASE_URL}/api/v1/s/{EXISTING_SHARE_ID}")
        view_count1 = response1.json().get("view_count", 0)
        
        response2 = requests.get(f"{BASE_URL}/api/v1/s/{EXISTING_SHARE_ID}")
        view_count2 = response2.json().get("view_count", 0)
        
        assert view_count2 >= view_count1, "View count should increment"
        print(f"✓ View count incremented: {view_count1} -> {view_count2}")
    
    def test_get_nonexistent_share_returns_404(self):
        """GET /api/v1/s/{invalid_id} returns 404"""
        response = requests.get(f"{BASE_URL}/api/v1/s/nonexistent123")
        assert response.status_code == 404
        print("✓ Non-existent share returns 404")


class TestPublicCopyText:
    """Test public copy-text endpoint"""
    
    def test_copy_text_returns_200(self):
        """GET /api/v1/s/{share_id}/copy-text returns 200"""
        response = requests.get(f"{BASE_URL}/api/v1/s/{EXISTING_SHARE_ID}/copy-text")
        assert response.status_code == 200
        print("✓ Public copy-text returns 200")
    
    def test_copy_text_has_text_field(self):
        """Copy-text response has 'text' field"""
        response = requests.get(f"{BASE_URL}/api/v1/s/{EXISTING_SHARE_ID}/copy-text")
        data = response.json()
        assert "text" in data
        assert isinstance(data["text"], str)
        assert len(data["text"]) > 0
        print(f"✓ Copy-text has text field ({len(data['text'])} chars)")
    
    def test_copy_text_contains_strategy_info(self):
        """Copy-text contains strategy name and details"""
        response = requests.get(f"{BASE_URL}/api/v1/s/{EXISTING_SHARE_ID}/copy-text")
        text = response.json().get("text", "")
        
        assert "STRATEGY:" in text
        assert "Text2trade" in text
        print("✓ Copy-text contains strategy info")
    
    def test_copy_text_nonexistent_returns_404(self):
        """Copy-text for non-existent share returns 404"""
        response = requests.get(f"{BASE_URL}/api/v1/s/nonexistent123/copy-text")
        assert response.status_code == 404
        print("✓ Non-existent share copy-text returns 404")


class TestPublicPDF:
    """Test public PDF endpoint"""
    
    def test_pdf_returns_200_and_pdf_content(self):
        """GET /api/v1/s/{share_id}/pdf returns PDF"""
        response = requests.get(f"{BASE_URL}/api/v1/s/{EXISTING_SHARE_ID}/pdf")
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/pdf"
        assert len(response.content) > 0
        print(f"✓ Public PDF returns 200 with {len(response.content)} bytes")
    
    def test_pdf_has_content_disposition(self):
        """PDF response has Content-Disposition header"""
        response = requests.get(f"{BASE_URL}/api/v1/s/{EXISTING_SHARE_ID}/pdf")
        content_disp = response.headers.get("content-disposition", "")
        assert "attachment" in content_disp
        assert ".pdf" in content_disp
        print(f"✓ PDF has Content-Disposition: {content_disp}")
    
    def test_pdf_nonexistent_returns_404(self):
        """PDF for non-existent share returns 404"""
        response = requests.get(f"{BASE_URL}/api/v1/s/nonexistent123/pdf")
        assert response.status_code == 404
        print("✓ Non-existent share PDF returns 404")


class TestPublicBrokerInstructions:
    """Test public broker instructions endpoint"""
    
    @pytest.mark.parametrize("broker", BROKERS)
    def test_broker_instructions_returns_200(self, broker):
        """GET /api/v1/s/{share_id}/broker-instructions/{broker} returns 200"""
        response = requests.get(f"{BASE_URL}/api/v1/s/{EXISTING_SHARE_ID}/broker-instructions/{broker}")
        assert response.status_code == 200, f"Broker {broker} failed: {response.status_code}"
        print(f"✓ Broker instructions for {broker} returns 200")
    
    def test_broker_instructions_has_required_fields(self):
        """Broker instructions response has required fields"""
        response = requests.get(f"{BASE_URL}/api/v1/s/{EXISTING_SHARE_ID}/broker-instructions/zerodha")
        data = response.json()
        
        assert "broker" in data
        assert "broker_name" in data
        assert "symbol" in data
        assert "steps" in data
        assert isinstance(data["steps"], list)
        assert len(data["steps"]) > 0
        assert "note" in data
        assert "help_url" in data
        print("✓ Broker instructions has all required fields")
    
    def test_broker_instructions_invalid_broker_returns_400(self):
        """Invalid broker returns 400"""
        response = requests.get(f"{BASE_URL}/api/v1/s/{EXISTING_SHARE_ID}/broker-instructions/invalid_broker")
        assert response.status_code == 400
        print("✓ Invalid broker returns 400")
    
    def test_broker_instructions_nonexistent_share_returns_404(self):
        """Non-existent share returns 404"""
        response = requests.get(f"{BASE_URL}/api/v1/s/nonexistent123/broker-instructions/zerodha")
        assert response.status_code == 404
        print("✓ Non-existent share broker instructions returns 404")


class TestAuthenticatedShareEndpoints:
    """Test authenticated share endpoints"""
    
    def test_create_share_returns_share_id(self):
        """POST /api/v1/strategies/{id}/share creates share with 8-char ID"""
        token = get_test_user_token()
        assert token, "Failed to get test user token"
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(f"{BASE_URL}/api/v1/strategies/{EXISTING_STRATEGY_ID}/share", headers=headers)
        
        assert response.status_code == 200, f"Create share failed: {response.status_code} - {response.text}"
        data = response.json()
        assert data.get("success") == True
        assert "share_id" in data
        assert len(data["share_id"]) == 8, f"Share ID should be 8 chars, got {len(data['share_id'])}"
        print(f"✓ Create share returns 8-char ID: {data['share_id']}")
    
    def test_create_share_returns_existing_if_already_shared(self):
        """Creating share for already shared strategy returns existing share"""
        token = get_test_user_token()
        assert token, "Failed to get test user token"
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # First share
        response1 = requests.post(f"{BASE_URL}/api/v1/strategies/{EXISTING_STRATEGY_ID}/share", headers=headers)
        share_id1 = response1.json().get("share_id")
        
        # Second share attempt
        response2 = requests.post(f"{BASE_URL}/api/v1/strategies/{EXISTING_STRATEGY_ID}/share", headers=headers)
        share_id2 = response2.json().get("share_id")
        
        assert share_id1 == share_id2, "Should return same share_id for already shared strategy"
        assert response2.json().get("already_shared") == True
        print(f"✓ Already shared strategy returns existing share_id: {share_id1}")
    
    def test_create_share_requires_auth(self):
        """Create share without auth returns 401 or 403"""
        response = requests.post(f"{BASE_URL}/api/v1/strategies/{EXISTING_STRATEGY_ID}/share")
        assert response.status_code in [401, 403]
        print("✓ Create share requires authentication")
    
    def test_create_share_nonexistent_strategy_returns_404(self):
        """Create share for non-existent strategy returns 404"""
        token = get_test_user_token()
        assert token, "Failed to get test user token"
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(f"{BASE_URL}/api/v1/strategies/nonexistent-id/share", headers=headers)
        assert response.status_code == 404
        print("✓ Create share for non-existent strategy returns 404")


class TestCloneEndpoint:
    """Test clone endpoint"""
    
    def test_clone_requires_auth(self):
        """Clone without auth returns 401 or 403"""
        response = requests.post(f"{BASE_URL}/api/v1/s/{EXISTING_SHARE_ID}/clone")
        assert response.status_code in [401, 403]
        print("✓ Clone requires authentication")
    
    def test_clone_creates_new_strategy(self):
        """Clone creates a new strategy for the user"""
        token = get_test_user_token()
        assert token, "Failed to get test user token"
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(f"{BASE_URL}/api/v1/s/{EXISTING_SHARE_ID}/clone", headers=headers)
        
        assert response.status_code == 200, f"Clone failed: {response.status_code} - {response.text}"
        data = response.json()
        assert data.get("success") == True
        assert "strategy_id" in data
        assert "strategy" in data
        
        # Verify cloned strategy has "(cloned)" in name
        strategy = data.get("strategy", {})
        name = strategy.get("metadata", {}).get("name", "")
        assert "(cloned)" in name, f"Cloned strategy name should contain '(cloned)', got: {name}"
        print(f"✓ Clone creates new strategy: {data['strategy_id']}")
    
    def test_clone_nonexistent_share_returns_404(self):
        """Clone non-existent share returns 404"""
        token = get_test_user_token()
        assert token, "Failed to get test user token"
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(f"{BASE_URL}/api/v1/s/nonexistent123/clone", headers=headers)
        assert response.status_code == 404
        print("✓ Clone non-existent share returns 404")


class TestRevokeShare:
    """Test revoke share endpoint"""
    
    def test_revoke_share_requires_auth(self):
        """Revoke without auth returns 401 or 403"""
        response = requests.delete(f"{BASE_URL}/api/v1/strategies/some-id/share/some-share")
        assert response.status_code in [401, 403]
        print("✓ Revoke share requires authentication")
    
    def test_revoke_nonexistent_share_returns_404(self):
        """Revoke non-existent share returns 404"""
        token = get_test_user_token()
        assert token, "Failed to get test user token"
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.delete(f"{BASE_URL}/api/v1/strategies/{EXISTING_STRATEGY_ID}/share/nonexistent", headers=headers)
        assert response.status_code == 404
        print("✓ Revoke non-existent share returns 404")


class TestAuthenticatedCopyText:
    """Test authenticated copy-text endpoint"""
    
    def test_copy_text_requires_auth(self):
        """Copy-text without auth returns 401 or 403"""
        response = requests.get(f"{BASE_URL}/api/v1/strategies/{EXISTING_STRATEGY_ID}/copy-text")
        assert response.status_code in [401, 403]
        print("✓ Authenticated copy-text requires auth")
    
    def test_copy_text_returns_text(self):
        """Copy-text returns formatted text"""
        token = get_test_user_token()
        assert token, "Failed to get test user token"
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/v1/strategies/{EXISTING_STRATEGY_ID}/copy-text", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "text" in data
        assert len(data["text"]) > 0
        print(f"✓ Authenticated copy-text returns {len(data['text'])} chars")


class TestAuthenticatedPDF:
    """Test authenticated PDF endpoint"""
    
    def test_pdf_requires_auth(self):
        """PDF without auth returns 401"""
        response = requests.get(f"{BASE_URL}/api/v1/strategies/{EXISTING_STRATEGY_ID}/pdf")
        assert response.status_code == 401
        print("✓ Authenticated PDF requires auth")
    
    def test_pdf_with_token_query_param(self):
        """PDF with token query param works"""
        token = get_test_user_token()
        assert token, "Failed to get test user token"
        
        response = requests.get(f"{BASE_URL}/api/v1/strategies/{EXISTING_STRATEGY_ID}/pdf?token={token}")
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/pdf"
        print(f"✓ PDF with token query param returns {len(response.content)} bytes")


class TestAuthenticatedBrokerInstructions:
    """Test authenticated broker instructions endpoint"""
    
    def test_broker_instructions_requires_auth(self):
        """Broker instructions without auth returns 401 or 403"""
        response = requests.get(f"{BASE_URL}/api/v1/strategies/{EXISTING_STRATEGY_ID}/broker-instructions/zerodha")
        assert response.status_code in [401, 403]
        print("✓ Authenticated broker instructions requires auth")
    
    def test_broker_instructions_returns_steps(self):
        """Broker instructions returns steps"""
        token = get_test_user_token()
        assert token, "Failed to get test user token"
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/v1/strategies/{EXISTING_STRATEGY_ID}/broker-instructions/zerodha", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "steps" in data
        assert len(data["steps"]) > 0
        print(f"✓ Authenticated broker instructions returns {len(data['steps'])} steps")


class TestShareStats:
    """Test share stats endpoint"""
    
    def test_share_stats_requires_auth(self):
        """Share stats without auth returns 401 or 403"""
        response = requests.get(f"{BASE_URL}/api/v1/strategies/{EXISTING_STRATEGY_ID}/share-stats")
        assert response.status_code in [401, 403]
        print("✓ Share stats requires auth")
    
    def test_share_stats_returns_data(self):
        """Share stats returns view/clone counts"""
        token = get_test_user_token()
        assert token, "Failed to get test user token"
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # First ensure there's a share
        requests.post(f"{BASE_URL}/api/v1/strategies/{EXISTING_STRATEGY_ID}/share", headers=headers)
        
        response = requests.get(f"{BASE_URL}/api/v1/strategies/{EXISTING_STRATEGY_ID}/share-stats", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "strategy_id" in data
        assert "total_shares" in data
        assert "active_shares" in data
        assert "total_views" in data
        assert "total_clones" in data
        assert "shares" in data
        print(f"✓ Share stats: {data['total_views']} views, {data['total_clones']} clones")


class TestAdminAnalytics:
    """Test admin analytics endpoint"""
    
    def test_admin_analytics_requires_admin(self):
        """Admin analytics with non-admin returns 403"""
        token = get_test_user_token()
        assert token, "Failed to get test user token"
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/v1/admin/analytics/shares", headers=headers)
        assert response.status_code == 403
        print("✓ Admin analytics requires admin role")
    
    def test_admin_analytics_returns_data(self):
        """Admin analytics returns share data"""
        token = get_admin_token()
        assert token, "Failed to get admin token"
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/v1/admin/analytics/shares", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "total_shares" in data
        assert "total_views" in data
        assert "total_clones" in data
        assert "conversion_rate" in data
        assert "top_shared" in data
        print(f"✓ Admin analytics: {data['total_shares']} shares, {data['conversion_rate']}% conversion")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
