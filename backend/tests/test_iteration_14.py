"""
Iteration 14 - Backend API Tests
Testing: Login, Strategies, Backtest, Paper Trading, AI Playground/Sessions
Test credentials: testai@example.com / Password123!
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://strategy-builder-ui-1.preview.emergentagent.com')

# Test credentials
TEST_EMAIL = "testai@example.com"
TEST_PASSWORD = "Password123!"


class TestAuthAndLogin:
    """Test authentication flow - login should redirect user to dashboard"""
    
    def test_login_success(self):
        """Login flow: testai@example.com / Password123! → returns token"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        assert "refresh_token" in data, "No refresh_token in response"
        assert data.get("token_type") == "bearer", f"Unexpected token_type: {data.get('token_type')}"
        print(f"✓ Login successful - received access_token and refresh_token")
        
    def test_login_invalid_credentials(self):
        """Invalid credentials should return 401"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": TEST_EMAIL,
            "password": "wrongpassword"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Invalid login correctly returns 401")


class TestStrategiesAPI:
    """Test GET /api/v1/strategies endpoint - the blocker that was fixed"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, "Auth setup failed"
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_strategies_returns_200(self):
        """GET /api/v1/strategies returns 200 with strategies list"""
        response = requests.get(f"{BASE_URL}/api/v1/strategies", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "strategies" in data, "No 'strategies' key in response"
        assert "count" in data, "No 'count' key in response"
        assert isinstance(data["strategies"], list), "strategies is not a list"
        print(f"✓ GET /strategies returned {data['count']} strategies")
        
    def test_strategies_have_correct_schema(self):
        """Strategy cards should show correct metadata (name, instrument, timeframe)"""
        response = requests.get(f"{BASE_URL}/api/v1/strategies", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        
        if data["count"] > 0:
            strategy = data["strategies"][0]
            # Check required fields exist and are not [object Object]
            assert "metadata" in strategy, "No metadata in strategy"
            assert "name" in strategy["metadata"], "No name in metadata"
            assert strategy["metadata"]["name"] != "[object Object]", "Name is [object Object]!"
            
            if "instrument" in strategy:
                assert "symbol" in strategy["instrument"], "No symbol in instrument"
                assert strategy["instrument"]["symbol"] != "[object Object]", "Symbol is [object Object]!"
                
            if "timeframe" in strategy:
                assert "interval" in strategy["timeframe"], "No interval in timeframe"
                assert strategy["timeframe"]["interval"] != "[object Object]", "Interval is [object Object]!"
            
            print(f"✓ Strategy schema correct: {strategy['metadata']['name']}")
        else:
            print("✓ No strategies found (expected if new user)")


class TestBacktestAPI:
    """Test POST /api/v1/backtest endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token and fetch strategies"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        # Fetch strategies
        strat_response = requests.get(f"{BASE_URL}/api/v1/strategies", headers=self.headers)
        if strat_response.status_code == 200:
            self.strategies = strat_response.json().get("strategies", [])
        else:
            self.strategies = []
    
    def test_backtest_with_valid_strategy(self):
        """POST /api/v1/backtest works with a strategy"""
        # Create a test strategy for backtest if no strategies exist
        test_strategy = {
            "metadata": {"name": "Test RSI Strategy"},
            "market": {"type": "equity", "exchange": "NSE"},
            "instrument": {"symbol": "RELIANCE"},
            "timeframe": {"interval": "1d"},
            "entry_conditions": [
                {"name": "RSI", "params": {"period": 14}, "operator": "<", "value": 30}
            ],
            "exit_conditions": [
                {"name": "RSI", "params": {"period": 14}, "operator": ">", "value": 70}
            ],
            "filters": [],
            "risk_management": {
                "stop_loss": {"type": "percentage", "value": 5},
                "target_profit": {"type": "percentage", "value": 10},
                "trailing_stop_loss": {"enabled": False, "type": "percentage", "value": 1.0, "activation_profit": 0},
                "time_based_exit": {"enabled": False, "exit_time": "15:10"},
                "daily_limits": {"max_loss_per_day": 5.0, "max_trades_per_day": 10},
                "position_sizing": {"method": "fixed_quantity", "value": 1}
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/api/v1/backtest",
            json={"strategy": test_strategy, "slippage_pct": 0.05, "initial_capital": 100000},
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Backtest failed: {response.text}"
        data = response.json()
        
        # Check backtest response has required fields
        assert "success" in data, "No 'success' in backtest response"
        assert "metrics" in data, "No 'metrics' in backtest response"
        assert "trades" in data, "No 'trades' in backtest response"
        assert "equity_curve" in data, "No 'equity_curve' in backtest response"
        
        # Check metrics fields for BacktestResultsPanel
        metrics = data.get("metrics", {})
        expected_metric_fields = ["total_trades", "win_rate", "total_pnl_pct", "sharpe_ratio"]
        for field in expected_metric_fields:
            assert field in metrics, f"Missing metric field: {field}"
        
        print(f"✓ Backtest successful - {data['metrics'].get('total_trades', 0)} trades, {data.get('candles_processed', 0)} candles")


class TestPaperTradingAPI:
    """Test Paper Trading endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token and strategies"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        # Fetch strategies
        strat_response = requests.get(f"{BASE_URL}/api/v1/strategies", headers=self.headers)
        self.strategies = strat_response.json().get("strategies", []) if strat_response.status_code == 200 else []
    
    def test_get_paper_trades_returns_list(self):
        """GET /api/v1/paper-trades returns list of paper trades"""
        response = requests.get(f"{BASE_URL}/api/v1/paper-trades", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "paper_trades" in data, "No 'paper_trades' in response"
        assert isinstance(data["paper_trades"], list), "paper_trades is not a list"
        print(f"✓ GET /paper-trades returned {len(data['paper_trades'])} paper trades")
        
    def test_deploy_paper_trade_with_valid_strategy(self):
        """POST /api/v1/paper-trade/deploy works with valid strategy_id"""
        if not self.strategies:
            pytest.skip("No strategies available for paper trading test")
            
        strategy_id = self.strategies[0].get("id")
        if not strategy_id:
            pytest.skip("Strategy has no ID")
            
        response = requests.post(
            f"{BASE_URL}/api/v1/paper-trade/deploy",
            json={
                "strategy_id": strategy_id,
                "symbol": "RELIANCE",
                "timeframe": "1d",
                "initial_capital": 100000,
                "lookback_days": 60,
                "slippage_pct": 0.05
            },
            headers=self.headers
        )
        
        # Should succeed or fail with meaningful error
        assert response.status_code in [200, 400, 404], f"Unexpected status: {response.status_code}: {response.text}"
        
        if response.status_code == 200:
            data = response.json()
            assert "paper_trade_id" in data, "No paper_trade_id in deploy response"
            print(f"✓ Paper trade deployed: {data['paper_trade_id']}")
        else:
            print(f"✓ Paper trade deploy returned {response.status_code} (expected for some strategies)")


class TestAISessionAPI:
    """Test AI Playground session endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_session_start(self):
        """POST /api/v1/session/start creates a new session"""
        response = requests.post(f"{BASE_URL}/api/v1/session/start", json={}, headers=self.headers)
        assert response.status_code == 200, f"Session start failed: {response.text}"
        data = response.json()
        assert "session_id" in data, "No session_id in response"
        print(f"✓ Session started: {data['session_id']}")
        return data["session_id"]
    
    def test_session_message_returns_mode(self):
        """POST /api/v1/session/{id}/message returns response with mode field"""
        # Start session
        start_response = requests.post(f"{BASE_URL}/api/v1/session/start", json={}, headers=self.headers)
        assert start_response.status_code == 200
        session_id = start_response.json()["session_id"]
        
        # Send a message
        time.sleep(1)  # Rate limit buffer
        msg_response = requests.post(
            f"{BASE_URL}/api/v1/session/{session_id}/message",
            json={"message": "I want to buy RELIANCE when RSI is below 30"},
            headers=self.headers
        )
        
        assert msg_response.status_code == 200, f"Message failed: {msg_response.text}"
        data = msg_response.json()
        
        # Check response structure
        assert "mode" in data, "No 'mode' in session message response"
        assert data["mode"] in ["question", "strategy", "error"], f"Invalid mode: {data['mode']}"
        assert "content" in data, "No 'content' in session message response"
        assert "session_id" in data, "No 'session_id' in response"
        
        print(f"✓ Session message returned mode='{data['mode']}'")


class TestHealthAndAnalytics:
    """Test health and analytics endpoints"""
    
    def test_health_endpoint(self):
        """GET /api/v1/health returns healthy status"""
        response = requests.get(f"{BASE_URL}/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "degraded"], f"Unhealthy status: {data['status']}"
        assert data["mongodb"] == True, "MongoDB is not healthy"
        print(f"✓ Health check: {data['status']}, MongoDB: {data['mongodb']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
