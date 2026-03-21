"""
Test suite for Strategy Optimizer feature
Tests: POST /api/v1/optimizer/detect-params and POST /api/v1/optimizer/run
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_USER_EMAIL = "testai@example.com"
TEST_USER_PASSWORD = "Password123!"


class TestOptimizerEndpoints:
    """Tests for the Strategy Optimizer API endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Login and get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get token
        login_response = self.session.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        
        if login_response.status_code != 200:
            pytest.skip(f"Login failed: {login_response.status_code}")
        
        token = login_response.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get strategies for testing
        strat_response = self.session.get(f"{BASE_URL}/api/v1/strategies")
        if strat_response.status_code == 200:
            self.strategies = strat_response.json().get("strategies", [])
        else:
            self.strategies = []
    
    # ==================== AUTH TESTS ====================
    
    def test_login_success(self):
        """Test login works with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "token_type" in data
        print(f"✓ Login successful for {TEST_USER_EMAIL}")
    
    # ==================== DETECT PARAMS TESTS ====================
    
    def test_detect_params_with_strategy_id(self):
        """Test POST /optimizer/detect-params with strategy_id"""
        if not self.strategies:
            pytest.skip("No strategies available for testing")
        
        strategy_id = self.strategies[0].get("id")
        response = self.session.post(f"{BASE_URL}/api/v1/optimizer/detect-params", json={
            "strategy_id": strategy_id
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "tunables" in data
        assert "count" in data
        assert isinstance(data["tunables"], list)
        print(f"✓ Detect params returned {data['count']} tunable parameters")
        
        # Validate tunable structure if any exist
        if data["tunables"]:
            tunable = data["tunables"][0]
            assert "path" in tunable
            assert "label" in tunable
            assert "current" in tunable
            assert "min" in tunable
            assert "max" in tunable
            assert "step_type" in tunable
            print(f"✓ Tunable structure validated: {tunable['label']}")
    
    def test_detect_params_without_auth(self):
        """Test detect-params requires authentication"""
        response = requests.post(f"{BASE_URL}/api/v1/optimizer/detect-params", json={
            "strategy_id": "test-id"
        })
        assert response.status_code in [401, 403]
        print("✓ Detect params correctly requires authentication")
    
    def test_detect_params_invalid_strategy(self):
        """Test detect-params with non-existent strategy"""
        response = self.session.post(f"{BASE_URL}/api/v1/optimizer/detect-params", json={
            "strategy_id": "non-existent-strategy-id-12345"
        })
        assert response.status_code == 404
        print("✓ Detect params returns 404 for invalid strategy")
    
    def test_detect_params_missing_strategy(self):
        """Test detect-params without strategy_id or strategy object"""
        response = self.session.post(f"{BASE_URL}/api/v1/optimizer/detect-params", json={})
        assert response.status_code == 400
        print("✓ Detect params returns 400 when no strategy provided")
    
    # ==================== OPTIMIZER RUN TESTS ====================
    
    def test_optimizer_run_success(self):
        """Test POST /optimizer/run with valid params"""
        if not self.strategies:
            pytest.skip("No strategies available for testing")
        
        strategy_id = self.strategies[0].get("id")
        
        # First detect params
        detect_response = self.session.post(f"{BASE_URL}/api/v1/optimizer/detect-params", json={
            "strategy_id": strategy_id
        })
        
        if detect_response.status_code != 200:
            pytest.skip("Could not detect params")
        
        tunables = detect_response.json().get("tunables", [])
        if not tunables:
            pytest.skip("No tunable parameters found")
        
        # Use first tunable param with minimal steps
        param_range = {
            "path": tunables[0]["path"],
            "label": tunables[0]["label"],
            "min": tunables[0]["min"],
            "max": tunables[0]["max"],
            "steps": 3,  # Minimal steps for fast test
            "step_type": tunables[0]["step_type"]
        }
        
        response = self.session.post(f"{BASE_URL}/api/v1/optimizer/run", json={
            "strategy_id": strategy_id,
            "param_ranges": [param_range]
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate response structure
        assert data.get("success") == True
        assert "total_combinations" in data
        assert "baseline" in data
        assert "results" in data
        assert "param_impact" in data
        assert "warnings" in data
        assert "elapsed_seconds" in data
        
        # Validate baseline structure
        baseline = data["baseline"]
        assert "sharpe" in baseline
        assert "pnl_pct" in baseline
        assert "win_rate" in baseline
        assert "max_drawdown" in baseline
        assert "total_trades" in baseline
        
        # Validate results structure
        results = data["results"]
        assert isinstance(results, list)
        if results:
            result = results[0]
            assert "rank" in result
            assert "sharpe" in result
            assert "pnl_pct" in result
            assert "params" in result
        
        print(f"✓ Optimizer run completed: {data['total_combinations']} combinations in {data['elapsed_seconds']}s")
        print(f"  Baseline Sharpe: {baseline['sharpe']}, Best Sharpe: {results[0]['sharpe'] if results else 'N/A'}")
    
    def test_optimizer_run_without_auth(self):
        """Test optimizer run requires authentication"""
        response = requests.post(f"{BASE_URL}/api/v1/optimizer/run", json={
            "strategy_id": "test-id",
            "param_ranges": [{"path": "test", "min": 1, "max": 10, "steps": 3}]
        })
        assert response.status_code in [401, 403]
        print("✓ Optimizer run correctly requires authentication")
    
    def test_optimizer_run_missing_params(self):
        """Test optimizer run without param_ranges"""
        if not self.strategies:
            pytest.skip("No strategies available for testing")
        
        strategy_id = self.strategies[0].get("id")
        response = self.session.post(f"{BASE_URL}/api/v1/optimizer/run", json={
            "strategy_id": strategy_id,
            "param_ranges": []
        })
        assert response.status_code == 400
        print("✓ Optimizer run returns 400 when no param_ranges provided")
    
    def test_optimizer_run_too_many_combinations(self):
        """Test optimizer rejects >500 combinations"""
        if not self.strategies:
            pytest.skip("No strategies available for testing")
        
        strategy_id = self.strategies[0].get("id")
        
        # Create param ranges that exceed 500 combinations (e.g., 10 * 10 * 10 = 1000)
        param_ranges = [
            {"path": "entry_conditions[0].params.period", "min": 5, "max": 50, "steps": 10, "step_type": "int"},
            {"path": "entry_conditions[0].value", "min": 20, "max": 80, "steps": 10, "step_type": "float"},
            {"path": "risk_management.stop_loss.value", "min": 1, "max": 5, "steps": 10, "step_type": "float"},
        ]
        
        response = self.session.post(f"{BASE_URL}/api/v1/optimizer/run", json={
            "strategy_id": strategy_id,
            "param_ranges": param_ranges
        })
        
        assert response.status_code == 400
        data = response.json()
        assert "500" in str(data.get("detail", "")) or "combinations" in str(data.get("detail", "")).lower()
        print("✓ Optimizer correctly rejects >500 combinations")
    
    def test_optimizer_run_invalid_strategy(self):
        """Test optimizer run with non-existent strategy"""
        response = self.session.post(f"{BASE_URL}/api/v1/optimizer/run", json={
            "strategy_id": "non-existent-strategy-id-12345",
            "param_ranges": [{"path": "test", "min": 1, "max": 10, "steps": 3}]
        })
        assert response.status_code == 404
        print("✓ Optimizer run returns 404 for invalid strategy")
    
    # ==================== PARAM IMPACT & WARNINGS TESTS ====================
    
    def test_optimizer_returns_param_impact(self):
        """Test optimizer returns param_impact analysis"""
        if not self.strategies:
            pytest.skip("No strategies available for testing")
        
        strategy_id = self.strategies[0].get("id")
        
        # Detect params first
        detect_response = self.session.post(f"{BASE_URL}/api/v1/optimizer/detect-params", json={
            "strategy_id": strategy_id
        })
        
        if detect_response.status_code != 200:
            pytest.skip("Could not detect params")
        
        tunables = detect_response.json().get("tunables", [])
        if len(tunables) < 2:
            pytest.skip("Need at least 2 tunable parameters for impact analysis")
        
        # Use first 2 tunables
        param_ranges = [
            {
                "path": tunables[0]["path"],
                "label": tunables[0]["label"],
                "min": tunables[0]["min"],
                "max": tunables[0]["max"],
                "steps": 3,
                "step_type": tunables[0]["step_type"]
            },
            {
                "path": tunables[1]["path"],
                "label": tunables[1]["label"],
                "min": tunables[1]["min"],
                "max": tunables[1]["max"],
                "steps": 3,
                "step_type": tunables[1]["step_type"]
            }
        ]
        
        response = self.session.post(f"{BASE_URL}/api/v1/optimizer/run", json={
            "strategy_id": strategy_id,
            "param_ranges": param_ranges
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate param_impact
        param_impact = data.get("param_impact", [])
        assert isinstance(param_impact, list)
        
        if param_impact:
            impact = param_impact[0]
            assert "label" in impact
            assert "path" in impact
            assert "impact_score" in impact
            assert "best_value" in impact
            print(f"✓ Param impact analysis returned: {len(param_impact)} parameters analyzed")
            print(f"  Most impactful: {impact['label']} (score: {impact['impact_score']})")
    
    def test_optimizer_returns_baseline_comparison(self):
        """Test optimizer returns baseline comparison data"""
        if not self.strategies:
            pytest.skip("No strategies available for testing")
        
        strategy_id = self.strategies[0].get("id")
        
        detect_response = self.session.post(f"{BASE_URL}/api/v1/optimizer/detect-params", json={
            "strategy_id": strategy_id
        })
        
        if detect_response.status_code != 200:
            pytest.skip("Could not detect params")
        
        tunables = detect_response.json().get("tunables", [])
        if not tunables:
            pytest.skip("No tunable parameters found")
        
        param_range = {
            "path": tunables[0]["path"],
            "label": tunables[0]["label"],
            "min": tunables[0]["min"],
            "max": tunables[0]["max"],
            "steps": 3,
            "step_type": tunables[0]["step_type"]
        }
        
        response = self.session.post(f"{BASE_URL}/api/v1/optimizer/run", json={
            "strategy_id": strategy_id,
            "param_ranges": [param_range]
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate baseline comparison
        baseline = data.get("baseline", {})
        assert "sharpe" in baseline
        assert "pnl_pct" in baseline
        assert "win_rate" in baseline
        assert "max_drawdown" in baseline
        assert "total_trades" in baseline
        assert "profit_factor" in baseline
        
        print(f"✓ Baseline comparison returned:")
        print(f"  Sharpe: {baseline['sharpe']}, P&L: {baseline['pnl_pct']}%, Trades: {baseline['total_trades']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
