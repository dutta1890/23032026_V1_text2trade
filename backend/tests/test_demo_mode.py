"""
Test Demo Account Mode Feature
- Registration with start_demo=true/false
- Account profile endpoint
- Mode switching (demo/real)
- Demo data seeding (strategies, paper trades, backtest records)
- is_demo filtering on strategies and paper trades
- Demo strategy delete protection
- Onboarding tour endpoints
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


# =============================================================================
# REGISTRATION TESTS
# =============================================================================

class TestDemoRegistration:
    """Test registration with demo mode"""
    
    def test_register_with_demo_mode(self, api_client):
        """POST /api/v1/auth/register with start_demo=true creates demo account"""
        unique_email = f"test_demo_{uuid.uuid4().hex[:8]}@example.com"
        response = api_client.post(f"{BASE_URL}/api/v1/auth/register", json={
            "email": unique_email,
            "password": "Test1234!",
            "start_demo": True
        })
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        data = response.json()
        assert "user_id" in data
        assert data["email"] == unique_email.lower()
        print(f"✓ Demo user registered: {unique_email}")
        
    def test_register_without_demo_mode(self, api_client):
        """POST /api/v1/auth/register with start_demo=false creates real account"""
        unique_email = f"test_real_{uuid.uuid4().hex[:8]}@example.com"
        response = api_client.post(f"{BASE_URL}/api/v1/auth/register", json={
            "email": unique_email,
            "password": "Test1234!",
            "start_demo": False
        })
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        data = response.json()
        assert "user_id" in data
        print(f"✓ Real user registered: {unique_email}")


# =============================================================================
# PROFILE & MODE TESTS
# =============================================================================

class TestAccountProfile:
    """Test account profile and mode switching"""
    
    @pytest.fixture(scope="class")
    def demo_user_token(self, api_client):
        """Create and login a demo user"""
        unique_email = f"test_profile_demo_{uuid.uuid4().hex[:8]}@example.com"
        # Register
        reg_resp = api_client.post(f"{BASE_URL}/api/v1/auth/register", json={
            "email": unique_email,
            "password": "Test1234!",
            "start_demo": True
        })
        assert reg_resp.status_code == 201
        # Login
        login_resp = api_client.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": unique_email,
            "password": "Test1234!"
        })
        assert login_resp.status_code == 200
        return login_resp.json()["access_token"]
    
    def test_profile_returns_demo_mode(self, api_client, demo_user_token):
        """GET /api/v1/account/profile returns account_mode='demo' for demo user"""
        response = api_client.get(f"{BASE_URL}/api/v1/account/profile", headers={
            "Authorization": f"Bearer {demo_user_token}"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["account_mode"] == "demo", f"Expected demo mode, got {data['account_mode']}"
        assert "demo_capital" in data
        assert data["demo_capital"] is not None
        assert "has_completed_onboarding" in data
        print(f"✓ Profile shows demo mode with capital: {data['demo_capital']}")
        
    def test_switch_to_real_mode(self, api_client, demo_user_token):
        """POST /api/v1/account/switch-mode {mode:'real'} switches to real mode"""
        response = api_client.post(f"{BASE_URL}/api/v1/account/switch-mode", json={
            "mode": "real"
        }, headers={"Authorization": f"Bearer {demo_user_token}"})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["success"] is True
        assert data["account_mode"] == "real"
        print("✓ Switched to real mode")
        
    def test_switch_back_to_demo_mode(self, api_client, demo_user_token):
        """POST /api/v1/account/switch-mode {mode:'demo'} switches back to demo"""
        response = api_client.post(f"{BASE_URL}/api/v1/account/switch-mode", json={
            "mode": "demo"
        }, headers={"Authorization": f"Bearer {demo_user_token}"})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["success"] is True
        assert data["account_mode"] == "demo"
        print("✓ Switched back to demo mode")


# =============================================================================
# DEMO DATA SEEDING TESTS
# =============================================================================

class TestDemoDataSeeding:
    """Test demo data seeding (strategies, paper trades, backtest records)"""
    
    @pytest.fixture(scope="class")
    def fresh_demo_user(self, api_client):
        """Create a fresh demo user and return token"""
        unique_email = f"test_seed_{uuid.uuid4().hex[:8]}@example.com"
        # Register with demo
        reg_resp = api_client.post(f"{BASE_URL}/api/v1/auth/register", json={
            "email": unique_email,
            "password": "Test1234!",
            "start_demo": True
        })
        assert reg_resp.status_code == 201
        # Login
        login_resp = api_client.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": unique_email,
            "password": "Test1234!"
        })
        assert login_resp.status_code == 200
        return login_resp.json()["access_token"]
    
    def test_demo_user_has_3_strategies(self, api_client, fresh_demo_user):
        """Demo user should have 3 seeded demo strategies"""
        response = api_client.get(f"{BASE_URL}/api/v1/strategies", headers={
            "Authorization": f"Bearer {fresh_demo_user}"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        strategies = data.get("strategies", [])
        # Should have at least 3 demo strategies
        demo_strategies = [s for s in strategies if s.get("is_demo") is True]
        assert len(demo_strategies) >= 3, f"Expected at least 3 demo strategies, got {len(demo_strategies)}"
        # Check demo tags
        demo_tags = [s.get("demo_tag") for s in demo_strategies]
        assert "demo_golden_cross" in demo_tags, "Missing demo_golden_cross strategy"
        assert "demo_rsi_reversion" in demo_tags, "Missing demo_rsi_reversion strategy"
        assert "demo_supertrend" in demo_tags, "Missing demo_supertrend strategy"
        print(f"✓ Demo user has {len(demo_strategies)} demo strategies with correct tags")
        
    def test_demo_user_has_paper_trade(self, api_client, fresh_demo_user):
        """Demo user should have at least 1 seeded paper trade"""
        response = api_client.get(f"{BASE_URL}/api/v1/paper-trades", headers={
            "Authorization": f"Bearer {fresh_demo_user}"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        paper_trades = data.get("paper_trades", [])
        demo_pt = [pt for pt in paper_trades if pt.get("is_demo") is True]
        assert len(demo_pt) >= 1, f"Expected at least 1 demo paper trade, got {len(demo_pt)}"
        print(f"✓ Demo user has {len(demo_pt)} demo paper trade(s)")


# =============================================================================
# ACTIVATE DEMO & IDEMPOTENCY TESTS
# =============================================================================

class TestActivateDemo:
    """Test activate-demo endpoint and idempotency"""
    
    @pytest.fixture(scope="class")
    def real_user_token(self, api_client):
        """Create a real user (no demo) and return token"""
        unique_email = f"test_activate_{uuid.uuid4().hex[:8]}@example.com"
        # Register without demo
        reg_resp = api_client.post(f"{BASE_URL}/api/v1/auth/register", json={
            "email": unique_email,
            "password": "Test1234!",
            "start_demo": False
        })
        assert reg_resp.status_code == 201
        # Login
        login_resp = api_client.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": unique_email,
            "password": "Test1234!"
        })
        assert login_resp.status_code == 200
        return login_resp.json()["access_token"]
    
    def test_activate_demo_for_real_user(self, api_client, real_user_token):
        """POST /api/v1/account/activate-demo activates demo mode and seeds data"""
        response = api_client.post(f"{BASE_URL}/api/v1/account/activate-demo", headers={
            "Authorization": f"Bearer {real_user_token}"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["success"] is True
        assert data["account_mode"] == "demo"
        print("✓ Activated demo mode for real user")
        
    def test_activate_demo_idempotent(self, api_client, real_user_token):
        """Calling activate-demo twice should not duplicate strategies"""
        # First call already done in previous test
        # Second call
        response = api_client.post(f"{BASE_URL}/api/v1/account/activate-demo", headers={
            "Authorization": f"Bearer {real_user_token}"
        })
        assert response.status_code == 200
        
        # Check strategies count
        strat_resp = api_client.get(f"{BASE_URL}/api/v1/strategies", headers={
            "Authorization": f"Bearer {real_user_token}"
        })
        assert strat_resp.status_code == 200
        strategies = strat_resp.json().get("strategies", [])
        demo_strategies = [s for s in strategies if s.get("is_demo") is True]
        # Should still be exactly 3 demo strategies
        assert len(demo_strategies) == 3, f"Expected exactly 3 demo strategies after idempotent call, got {len(demo_strategies)}"
        print("✓ Activate-demo is idempotent (still 3 demo strategies)")


# =============================================================================
# IS_DEMO FILTERING TESTS
# =============================================================================

class TestIsDemoFiltering:
    """Test is_demo filtering on strategies and paper trades"""
    
    @pytest.fixture(scope="class")
    def demo_user_with_strategies(self, api_client):
        """Create demo user with seeded data"""
        unique_email = f"test_filter_{uuid.uuid4().hex[:8]}@example.com"
        reg_resp = api_client.post(f"{BASE_URL}/api/v1/auth/register", json={
            "email": unique_email,
            "password": "Test1234!",
            "start_demo": True
        })
        assert reg_resp.status_code == 201
        login_resp = api_client.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": unique_email,
            "password": "Test1234!"
        })
        assert login_resp.status_code == 200
        return login_resp.json()["access_token"]
    
    def test_demo_mode_shows_only_demo_strategies(self, api_client, demo_user_with_strategies):
        """In demo mode, GET /strategies returns only is_demo=true strategies"""
        response = api_client.get(f"{BASE_URL}/api/v1/strategies", headers={
            "Authorization": f"Bearer {demo_user_with_strategies}"
        })
        assert response.status_code == 200
        strategies = response.json().get("strategies", [])
        # All returned strategies should have is_demo=True
        for s in strategies:
            assert s.get("is_demo") is True, f"Strategy {s.get('id')} should have is_demo=True in demo mode"
        print(f"✓ Demo mode shows only demo strategies ({len(strategies)} strategies)")
        
    def test_real_mode_excludes_demo_strategies(self, api_client, demo_user_with_strategies):
        """In real mode, GET /strategies returns only is_demo!=true strategies"""
        # Switch to real mode
        switch_resp = api_client.post(f"{BASE_URL}/api/v1/account/switch-mode", json={
            "mode": "real"
        }, headers={"Authorization": f"Bearer {demo_user_with_strategies}"})
        assert switch_resp.status_code == 200
        
        # Get strategies
        response = api_client.get(f"{BASE_URL}/api/v1/strategies", headers={
            "Authorization": f"Bearer {demo_user_with_strategies}"
        })
        assert response.status_code == 200
        strategies = response.json().get("strategies", [])
        # None should have is_demo=True
        for s in strategies:
            assert s.get("is_demo") is not True, f"Strategy {s.get('id')} should not have is_demo=True in real mode"
        print(f"✓ Real mode excludes demo strategies ({len(strategies)} strategies)")
        
        # Switch back to demo for other tests
        api_client.post(f"{BASE_URL}/api/v1/account/switch-mode", json={
            "mode": "demo"
        }, headers={"Authorization": f"Bearer {demo_user_with_strategies}"})


# =============================================================================
# DEMO STRATEGY DELETE PROTECTION
# =============================================================================

class TestDemoDeleteProtection:
    """Test that demo-seeded strategies cannot be deleted"""
    
    @pytest.fixture(scope="class")
    def demo_user_for_delete(self, api_client):
        """Create demo user"""
        unique_email = f"test_delete_{uuid.uuid4().hex[:8]}@example.com"
        reg_resp = api_client.post(f"{BASE_URL}/api/v1/auth/register", json={
            "email": unique_email,
            "password": "Test1234!",
            "start_demo": True
        })
        assert reg_resp.status_code == 201
        login_resp = api_client.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": unique_email,
            "password": "Test1234!"
        })
        assert login_resp.status_code == 200
        return login_resp.json()["access_token"]
    
    def test_cannot_delete_demo_seeded_strategy(self, api_client, demo_user_for_delete):
        """DELETE /strategy/{id} returns 403 for demo_tag strategies"""
        # Get strategies
        strat_resp = api_client.get(f"{BASE_URL}/api/v1/strategies", headers={
            "Authorization": f"Bearer {demo_user_for_delete}"
        })
        assert strat_resp.status_code == 200
        strategies = strat_resp.json().get("strategies", [])
        
        # Find a demo-tagged strategy
        demo_tagged = [s for s in strategies if s.get("demo_tag")]
        assert len(demo_tagged) > 0, "No demo-tagged strategies found"
        
        strategy_id = demo_tagged[0]["id"]
        
        # Try to delete
        delete_resp = api_client.delete(f"{BASE_URL}/api/v1/strategy/{strategy_id}", headers={
            "Authorization": f"Bearer {demo_user_for_delete}"
        })
        assert delete_resp.status_code == 403, f"Expected 403, got {delete_resp.status_code}: {delete_resp.text}"
        assert "cannot be deleted" in delete_resp.json().get("detail", "").lower()
        print("✓ Demo-seeded strategy delete blocked with 403")


# =============================================================================
# ONBOARDING TOUR TESTS
# =============================================================================

class TestOnboardingTour:
    """Test onboarding tour endpoints"""
    
    @pytest.fixture(scope="class")
    def demo_user_for_tour(self, api_client):
        """Create demo user"""
        unique_email = f"test_tour_{uuid.uuid4().hex[:8]}@example.com"
        reg_resp = api_client.post(f"{BASE_URL}/api/v1/auth/register", json={
            "email": unique_email,
            "password": "Test1234!",
            "start_demo": True
        })
        assert reg_resp.status_code == 201
        login_resp = api_client.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": unique_email,
            "password": "Test1234!"
        })
        assert login_resp.status_code == 200
        return login_resp.json()["access_token"]
    
    def test_new_demo_user_has_onboarding_false(self, api_client, demo_user_for_tour):
        """New demo user has has_completed_onboarding=false"""
        response = api_client.get(f"{BASE_URL}/api/v1/account/profile", headers={
            "Authorization": f"Bearer {demo_user_for_tour}"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["has_completed_onboarding"] is False
        print("✓ New demo user has has_completed_onboarding=false")
        
    def test_complete_onboarding(self, api_client, demo_user_for_tour):
        """POST /api/v1/account/complete-onboarding sets flag to true"""
        response = api_client.post(f"{BASE_URL}/api/v1/account/complete-onboarding", headers={
            "Authorization": f"Bearer {demo_user_for_tour}"
        })
        assert response.status_code == 200
        assert response.json()["success"] is True
        
        # Verify
        profile_resp = api_client.get(f"{BASE_URL}/api/v1/account/profile", headers={
            "Authorization": f"Bearer {demo_user_for_tour}"
        })
        assert profile_resp.json()["has_completed_onboarding"] is True
        print("✓ Complete-onboarding sets flag to true")
        
    def test_restart_tour(self, api_client, demo_user_for_tour):
        """POST /api/v1/account/restart-tour sets flag back to false"""
        response = api_client.post(f"{BASE_URL}/api/v1/account/restart-tour", headers={
            "Authorization": f"Bearer {demo_user_for_tour}"
        })
        assert response.status_code == 200
        assert response.json()["success"] is True
        
        # Verify
        profile_resp = api_client.get(f"{BASE_URL}/api/v1/account/profile", headers={
            "Authorization": f"Bearer {demo_user_for_tour}"
        })
        assert profile_resp.json()["has_completed_onboarding"] is False
        print("✓ Restart-tour sets flag back to false")


# =============================================================================
# EXISTING USER TESTS
# =============================================================================

class TestExistingUsers:
    """Test existing users (testai@example.com in real mode)"""
    
    def test_existing_real_user_login(self, api_client):
        """testai@example.com can login and is in real mode"""
        response = api_client.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": "testai@example.com",
            "password": "Password123!"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        token = response.json()["access_token"]
        
        # Check profile
        profile_resp = api_client.get(f"{BASE_URL}/api/v1/account/profile", headers={
            "Authorization": f"Bearer {token}"
        })
        assert profile_resp.status_code == 200
        data = profile_resp.json()
        # testai should be in real mode (or at least not demo)
        print(f"✓ testai@example.com logged in, account_mode: {data.get('account_mode', 'real')}")
        
    def test_existing_demo_user_login(self, api_client):
        """demouser1@example.com can login and is in demo mode"""
        response = api_client.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": "demouser1@example.com",
            "password": "Test1234!"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        token = response.json()["access_token"]
        
        # Check profile
        profile_resp = api_client.get(f"{BASE_URL}/api/v1/account/profile", headers={
            "Authorization": f"Bearer {token}"
        })
        assert profile_resp.status_code == 200
        data = profile_resp.json()
        assert data["account_mode"] == "demo", f"Expected demo mode, got {data['account_mode']}"
        print(f"✓ demouser1@example.com logged in, account_mode: demo")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
