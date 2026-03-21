"""
Test P2 Backlog Features:
1. Token blacklist for secure logout + password reset flow
2. Strategy sharing via public links
3. Watchlist for screener results
4. Strategy leaderboard / most cloned templates
"""
import pytest
import requests
import os
import time
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "testai@example.com"
TEST_PASSWORD = "Password123!"


class TestAuthLogoutAndPasswordReset:
    """Test token blacklist and password reset flow"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get token before each test"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
    def get_auth_token(self):
        """Helper to get auth token"""
        response = self.session.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json()["access_token"]
    
    def test_01_login_success(self):
        """Test login works with valid credentials"""
        response = self.session.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        print(f"Login successful for {TEST_EMAIL}")
    
    def test_02_logout_blacklists_token(self):
        """Test POST /auth/logout blacklists token"""
        # Get token
        token = self.get_auth_token()
        
        # Verify token works before logout
        response = self.session.get(
            f"{BASE_URL}/api/v1/strategies",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, "Token should work before logout"
        
        # Logout
        response = self.session.post(
            f"{BASE_URL}/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print("Logout successful")
        
        # Verify token is blacklisted - subsequent requests should fail
        response = self.session.get(
            f"{BASE_URL}/api/v1/strategies",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 401, f"Blacklisted token should return 401, got {response.status_code}"
        print("Token blacklist verified - subsequent request returned 401")
    
    def test_03_forgot_password_generates_token(self):
        """Test POST /auth/forgot-password generates reset token"""
        response = self.session.post(f"{BASE_URL}/api/v1/auth/forgot-password", json={
            "email": TEST_EMAIL
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "reset_token" in data
        assert data["reset_token"] is not None
        print(f"Reset token generated: {data['reset_token'][:20]}...")
    
    def test_04_forgot_password_nonexistent_email(self):
        """Test forgot-password with non-existent email still returns success (security)"""
        response = self.session.post(f"{BASE_URL}/api/v1/auth/forgot-password", json={
            "email": "nonexistent@example.com"
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        # Token should be None for non-existent email
        print("Forgot password for non-existent email handled securely")
    
    def test_05_reset_password_with_valid_token(self):
        """Test POST /auth/reset-password resets password with valid token"""
        # First generate a reset token
        response = self.session.post(f"{BASE_URL}/api/v1/auth/forgot-password", json={
            "email": TEST_EMAIL
        })
        if response.status_code == 429:
            pytest.skip("Rate limited - skipping test")
        assert response.status_code == 200
        reset_token = response.json().get("reset_token")
        
        if not reset_token:
            pytest.skip("No reset token returned (email may not exist)")
        
        # Reset password to same password (to avoid breaking other tests)
        response = self.session.post(f"{BASE_URL}/api/v1/auth/reset-password", json={
            "token": reset_token,
            "new_password": TEST_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print("Password reset successful (reset to same password)")
        
        # Verify can still login
        response = self.session.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        print("Login after password reset successful")
    
    def test_06_reset_password_invalid_token(self):
        """Test reset-password with invalid token fails"""
        response = self.session.post(f"{BASE_URL}/api/v1/auth/reset-password", json={
            "token": "invalid_token_12345",
            "new_password": "NewPassword123!"
        })
        assert response.status_code == 400
        print("Invalid reset token correctly rejected")


class TestStrategySharing:
    """Test strategy sharing via public links"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup session and auth"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        # Login
        response = self.session.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        else:
            pytest.skip("Login failed")
    
    def get_or_create_strategy(self):
        """Get existing strategy or create one"""
        response = self.session.get(f"{BASE_URL}/api/v1/strategies")
        if response.status_code == 200:
            strategies = response.json().get("strategies", [])
            if strategies:
                return strategies[0]["id"]
        
        # Create a new strategy
        response = self.session.post(f"{BASE_URL}/api/v1/strategy", json={
            "metadata": {"name": f"TEST_Share_Strategy_{uuid.uuid4().hex[:8]}"},
            "instrument": {"symbol": "RELIANCE"},
            "timeframe": {"interval": "1d"},
            "entry_conditions": [{"name": "RSI", "params": {"period": 14}, "operator": "<", "value": 30}],
            "exit_conditions": [],
            "risk_management": {"stop_loss": {"type": "percentage", "value": 2}}
        })
        if response.status_code == 201:
            return response.json().get("strategy_id") or response.json().get("id")
        return None
    
    def test_01_share_strategy_generates_token(self):
        """Test POST /strategy/{id}/share generates share token"""
        strategy_id = self.get_or_create_strategy()
        if not strategy_id:
            pytest.skip("No strategy available")
        
        response = self.session.post(f"{BASE_URL}/api/v1/strategy/{strategy_id}/share")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "share_token" in data
        self.share_token = data["share_token"]
        print(f"Share token generated: {self.share_token}")
    
    def test_02_get_shared_strategy_public(self):
        """Test GET /shared/{token} returns shared strategy (public, no auth)"""
        # First share a strategy
        strategy_id = self.get_or_create_strategy()
        if not strategy_id:
            pytest.skip("No strategy available")
        
        response = self.session.post(f"{BASE_URL}/api/v1/strategy/{strategy_id}/share")
        share_token = response.json().get("share_token")
        
        # Access shared strategy without auth
        public_session = requests.Session()
        response = public_session.get(f"{BASE_URL}/api/v1/shared/{share_token}")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "strategy" in data
        assert "shared_by" in data
        assert "views" in data
        print(f"Shared strategy accessed publicly, views: {data['views']}")
    
    def test_03_get_shared_strategy_invalid_token(self):
        """Test GET /shared/{token} with invalid token returns 404"""
        response = self.session.get(f"{BASE_URL}/api/v1/shared/invalid_token_xyz")
        assert response.status_code == 404
        print("Invalid share token correctly returns 404")
    
    def test_04_clone_shared_strategy(self):
        """Test POST /shared/{token}/clone clones strategy to authenticated user"""
        # First share a strategy
        strategy_id = self.get_or_create_strategy()
        if not strategy_id:
            pytest.skip("No strategy available")
        
        response = self.session.post(f"{BASE_URL}/api/v1/strategy/{strategy_id}/share")
        share_token = response.json().get("share_token")
        
        # Clone the shared strategy
        response = self.session.post(f"{BASE_URL}/api/v1/shared/{share_token}/clone", json={
            "name": "Cloned Strategy Test"
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "strategy_id" in data
        print(f"Strategy cloned successfully, new ID: {data['strategy_id']}")
    
    def test_05_clone_shared_strategy_no_auth(self):
        """Test clone without auth returns 401/403"""
        # First share a strategy
        strategy_id = self.get_or_create_strategy()
        if not strategy_id:
            pytest.skip("No strategy available")
        
        response = self.session.post(f"{BASE_URL}/api/v1/strategy/{strategy_id}/share")
        share_token = response.json().get("share_token")
        
        # Try to clone without auth
        public_session = requests.Session()
        public_session.headers.update({"Content-Type": "application/json"})
        response = public_session.post(f"{BASE_URL}/api/v1/shared/{share_token}/clone", json={})
        assert response.status_code in [401, 403]
        print("Clone without auth correctly rejected")


class TestWatchlist:
    """Test watchlist CRUD operations"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup session and auth"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        # Login
        response = self.session.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        else:
            pytest.skip("Login failed")
    
    def test_01_add_to_watchlist(self):
        """Test POST /watchlist adds symbol to watchlist"""
        # Use unique symbol to avoid duplicates
        symbol = f"TEST{uuid.uuid4().hex[:4].upper()}"
        response = self.session.post(f"{BASE_URL}/api/v1/watchlist", json={
            "symbol": symbol,
            "note": "Test watchlist item",
            "preset_name": "RSI Oversold"
        })
        # Could be 200 or 409 if already exists
        if response.status_code == 409:
            print(f"Symbol {symbol} already in watchlist")
            return
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "item" in data
        assert data["item"]["symbol"] == symbol
        print(f"Added {symbol} to watchlist")
    
    def test_02_get_watchlist(self):
        """Test GET /watchlist returns user's watchlist"""
        response = self.session.get(f"{BASE_URL}/api/v1/watchlist")
        assert response.status_code == 200
        data = response.json()
        assert "watchlist" in data
        assert "count" in data
        print(f"Watchlist has {data['count']} items")
    
    def test_03_add_duplicate_fails(self):
        """Test adding duplicate symbol fails with 409"""
        # First add
        symbol = "RELIANCE"
        response = self.session.post(f"{BASE_URL}/api/v1/watchlist", json={
            "symbol": symbol,
            "note": "First add"
        })
        
        # Try to add again
        response = self.session.post(f"{BASE_URL}/api/v1/watchlist", json={
            "symbol": symbol,
            "note": "Duplicate add"
        })
        assert response.status_code == 409
        print("Duplicate symbol correctly rejected with 409")
    
    def test_04_remove_from_watchlist(self):
        """Test DELETE /watchlist/{id} removes from watchlist"""
        # First add an item
        symbol = f"DEL{uuid.uuid4().hex[:4].upper()}"
        response = self.session.post(f"{BASE_URL}/api/v1/watchlist", json={
            "symbol": symbol,
            "note": "To be deleted"
        })
        if response.status_code != 200:
            pytest.skip("Could not add item to watchlist")
        
        item_id = response.json()["item"]["item_id"]
        
        # Delete it
        response = self.session.delete(f"{BASE_URL}/api/v1/watchlist/{item_id}")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print(f"Removed item {item_id} from watchlist")
        
        # Verify it's gone
        response = self.session.delete(f"{BASE_URL}/api/v1/watchlist/{item_id}")
        assert response.status_code == 404
        print("Deleted item correctly returns 404 on second delete")
    
    def test_05_watchlist_no_auth(self):
        """Test watchlist endpoints require auth"""
        public_session = requests.Session()
        public_session.headers.update({"Content-Type": "application/json"})
        
        response = public_session.get(f"{BASE_URL}/api/v1/watchlist")
        assert response.status_code in [401, 403]
        
        response = public_session.post(f"{BASE_URL}/api/v1/watchlist", json={"symbol": "TEST"})
        assert response.status_code in [401, 403]
        print("Watchlist endpoints correctly require auth")


class TestLeaderboard:
    """Test template leaderboard endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_01_get_leaderboard_public(self):
        """Test GET /templates/leaderboard returns top templates (public)"""
        response = self.session.get(f"{BASE_URL}/api/v1/templates/leaderboard")
        assert response.status_code == 200
        data = response.json()
        assert "leaderboard" in data
        assert "count" in data
        print(f"Leaderboard has {data['count']} templates")
        
        # Verify structure
        if data["leaderboard"]:
            template = data["leaderboard"][0]
            assert "template_id" in template or "name" in template
            print(f"Top template: {template.get('name', 'N/A')}, clones: {template.get('clone_count', 0)}")
    
    def test_02_leaderboard_sorted_by_clone_count(self):
        """Test leaderboard is sorted by clone_count descending"""
        response = self.session.get(f"{BASE_URL}/api/v1/templates/leaderboard")
        assert response.status_code == 200
        data = response.json()
        
        leaderboard = data.get("leaderboard", [])
        if len(leaderboard) >= 2:
            clone_counts = [t.get("clone_count", 0) for t in leaderboard]
            assert clone_counts == sorted(clone_counts, reverse=True), "Leaderboard should be sorted by clone_count desc"
            print(f"Leaderboard correctly sorted: {clone_counts[:5]}")
        else:
            print("Not enough templates to verify sorting")


# Cleanup fixture
@pytest.fixture(scope="module", autouse=True)
def cleanup_test_data():
    """Cleanup test data after all tests"""
    yield
    # Cleanup could be added here if needed
    print("Test cleanup complete")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
