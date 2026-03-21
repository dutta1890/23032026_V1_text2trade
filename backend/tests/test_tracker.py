"""
Test suite for Strategy Performance Tracker feature.
Tests: POST /tracker/record, GET /tracker/dashboard, GET /tracker/history
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestTrackerFeature:
    """Strategy Performance Tracker endpoint tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for test user"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": "testai@example.com",
            "password": "Password123!"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Headers with auth token"""
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    
    # =========================================================================
    # POST /tracker/record tests
    # =========================================================================
    
    def test_record_performance_success(self, auth_headers):
        """Test recording a performance entry with valid data"""
        payload = {
            "strategy_name": "TEST_Tracker_Strategy",
            "symbol": "RELIANCE",
            "timeframe": "1d",
            "source": "backtest",
            "sharpe": 1.5,
            "pnl_pct": 15.0,
            "win_rate": 60.0,
            "max_drawdown": 10.0,
            "total_trades": 30,
            "profit_factor": 2.0
        }
        response = requests.post(f"{BASE_URL}/api/v1/tracker/record", json=payload, headers=auth_headers)
        assert response.status_code == 200, f"Record failed: {response.text}"
        data = response.json()
        assert data.get("success") is True
    
    def test_record_performance_without_auth(self):
        """Test recording without authentication returns 401/403"""
        payload = {
            "strategy_name": "Unauthorized Test",
            "symbol": "RELIANCE"
        }
        response = requests.post(f"{BASE_URL}/api/v1/tracker/record", json=payload, headers={"Content-Type": "application/json"})
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    
    def test_record_performance_minimal_fields(self, auth_headers):
        """Test recording with only required fields"""
        payload = {
            "strategy_name": "TEST_Minimal_Strategy",
            "symbol": "TCS"
        }
        response = requests.post(f"{BASE_URL}/api/v1/tracker/record", json=payload, headers=auth_headers)
        assert response.status_code == 200, f"Record failed: {response.text}"
        data = response.json()
        assert data.get("success") is True
    
    def test_record_performance_paper_trade_source(self, auth_headers):
        """Test recording a paper trade entry"""
        payload = {
            "strategy_name": "TEST_Paper_Trade_Strategy",
            "symbol": "INFY",
            "source": "paper_trade",
            "sharpe": 0.8,
            "pnl_pct": 5.0,
            "win_rate": 45.0,
            "total_trades": 10
        }
        response = requests.post(f"{BASE_URL}/api/v1/tracker/record", json=payload, headers=auth_headers)
        assert response.status_code == 200, f"Record failed: {response.text}"
        data = response.json()
        assert data.get("success") is True
    
    # =========================================================================
    # GET /tracker/dashboard tests
    # =========================================================================
    
    def test_dashboard_success(self, auth_headers):
        """Test dashboard returns aggregated stats"""
        response = requests.get(f"{BASE_URL}/api/v1/tracker/dashboard", headers=auth_headers)
        assert response.status_code == 200, f"Dashboard failed: {response.text}"
        data = response.json()
        
        # Verify required fields exist
        assert "total_records" in data
        assert "total_backtests" in data
        assert "total_paper_trades" in data
        assert "avg_sharpe" in data
        assert "avg_pnl" in data
        assert "avg_win_rate" in data
        assert "best_strategy" in data
        assert "worst_strategy" in data
        assert "cumulative_pnl" in data
        assert "strategy_rankings" in data
        assert "improvement" in data
        assert "recent_activity" in data
        
        # Verify data types
        assert isinstance(data["total_records"], int)
        assert isinstance(data["avg_sharpe"], (int, float))
        assert isinstance(data["cumulative_pnl"], list)
        assert isinstance(data["strategy_rankings"], list)
        assert isinstance(data["recent_activity"], list)
    
    def test_dashboard_without_auth(self):
        """Test dashboard without authentication returns 401/403"""
        response = requests.get(f"{BASE_URL}/api/v1/tracker/dashboard")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    
    def test_dashboard_best_worst_strategy_structure(self, auth_headers):
        """Test best/worst strategy have correct structure"""
        response = requests.get(f"{BASE_URL}/api/v1/tracker/dashboard", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        if data.get("best_strategy"):
            best = data["best_strategy"]
            assert "name" in best
            assert "pnl_pct" in best
            assert "sharpe" in best
            assert "symbol" in best
        
        if data.get("worst_strategy"):
            worst = data["worst_strategy"]
            assert "name" in worst
            assert "pnl_pct" in worst
            assert "sharpe" in worst
            assert "symbol" in worst
    
    def test_dashboard_strategy_rankings_structure(self, auth_headers):
        """Test strategy rankings have correct structure"""
        response = requests.get(f"{BASE_URL}/api/v1/tracker/dashboard", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        rankings = data.get("strategy_rankings", [])
        if rankings:
            first_rank = rankings[0]
            assert "strategy_name" in first_rank
            assert "run_count" in first_rank
            assert "avg_sharpe" in first_rank
            assert "avg_pnl" in first_rank
            assert "avg_win_rate" in first_rank
            assert "total_trades" in first_rank
            assert "rank" in first_rank
            
            # Verify rankings are sorted by rank
            for i, r in enumerate(rankings):
                assert r["rank"] == i + 1
    
    def test_dashboard_cumulative_pnl_structure(self, auth_headers):
        """Test cumulative P&L data has correct structure"""
        response = requests.get(f"{BASE_URL}/api/v1/tracker/dashboard", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        cum_pnl = data.get("cumulative_pnl", [])
        if cum_pnl:
            first_entry = cum_pnl[0]
            assert "date" in first_entry
            assert "cumulative_pnl" in first_entry
            assert "strategy" in first_entry
    
    def test_dashboard_improvement_structure(self, auth_headers):
        """Test improvement insight has correct structure when available"""
        response = requests.get(f"{BASE_URL}/api/v1/tracker/dashboard", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        improvement = data.get("improvement")
        if improvement:
            assert "early_avg_sharpe" in improvement
            assert "recent_avg_sharpe" in improvement
            assert "sharpe_change_pct" in improvement
            assert "early_avg_pnl" in improvement
            assert "recent_avg_pnl" in improvement
            assert "pnl_change_pct" in improvement
            assert "early_count" in improvement
            assert "recent_count" in improvement
    
    def test_dashboard_recent_activity_structure(self, auth_headers):
        """Test recent activity has correct structure"""
        response = requests.get(f"{BASE_URL}/api/v1/tracker/dashboard", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        recent = data.get("recent_activity", [])
        if recent:
            first_activity = recent[0]
            assert "strategy_name" in first_activity
            assert "symbol" in first_activity
            assert "source" in first_activity
            assert "pnl_pct" in first_activity
            assert "sharpe" in first_activity
            assert "total_trades" in first_activity
            assert "recorded_at" in first_activity
    
    # =========================================================================
    # GET /tracker/history tests
    # =========================================================================
    
    def test_history_success(self, auth_headers):
        """Test history returns recent records"""
        response = requests.get(f"{BASE_URL}/api/v1/tracker/history", headers=auth_headers)
        assert response.status_code == 200, f"History failed: {response.text}"
        data = response.json()
        
        assert "records" in data
        assert "count" in data
        assert isinstance(data["records"], list)
        assert isinstance(data["count"], int)
        assert data["count"] == len(data["records"])
    
    def test_history_without_auth(self):
        """Test history without authentication returns 401/403"""
        response = requests.get(f"{BASE_URL}/api/v1/tracker/history")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    
    def test_history_record_structure(self, auth_headers):
        """Test history records have correct structure"""
        response = requests.get(f"{BASE_URL}/api/v1/tracker/history", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        records = data.get("records", [])
        if records:
            first_record = records[0]
            assert "user_id" in first_record
            assert "strategy_name" in first_record
            assert "symbol" in first_record
            assert "timeframe" in first_record
            assert "source" in first_record
            assert "sharpe" in first_record
            assert "pnl_pct" in first_record
            assert "win_rate" in first_record
            assert "max_drawdown" in first_record
            assert "total_trades" in first_record
            assert "profit_factor" in first_record
            assert "recorded_at" in first_record
            # Verify _id is excluded
            assert "_id" not in first_record
    
    def test_history_sorted_by_recorded_at_desc(self, auth_headers):
        """Test history records are sorted by recorded_at descending"""
        response = requests.get(f"{BASE_URL}/api/v1/tracker/history", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        records = data.get("records", [])
        if len(records) > 1:
            # Verify descending order
            for i in range(len(records) - 1):
                assert records[i]["recorded_at"] >= records[i + 1]["recorded_at"], \
                    "Records should be sorted by recorded_at descending"
    
    def test_history_limit_50(self, auth_headers):
        """Test history returns max 50 records"""
        response = requests.get(f"{BASE_URL}/api/v1/tracker/history", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert data["count"] <= 50, "History should return max 50 records"


class TestTrackerDataPersistence:
    """Test data persistence - Create then GET verification"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for test user"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": "testai@example.com",
            "password": "Password123!"
        })
        assert response.status_code == 200
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    
    def test_record_then_verify_in_history(self, auth_headers):
        """Test that recorded entry appears in history"""
        # Record a unique entry
        unique_name = "TEST_Persistence_Check_Strategy"
        payload = {
            "strategy_name": unique_name,
            "symbol": "SBIN",
            "timeframe": "1h",
            "source": "backtest",
            "sharpe": 2.5,
            "pnl_pct": 25.0,
            "win_rate": 70.0,
            "total_trades": 50
        }
        
        # Create record
        record_response = requests.post(f"{BASE_URL}/api/v1/tracker/record", json=payload, headers=auth_headers)
        assert record_response.status_code == 200
        
        # Verify in history
        history_response = requests.get(f"{BASE_URL}/api/v1/tracker/history", headers=auth_headers)
        assert history_response.status_code == 200
        records = history_response.json().get("records", [])
        
        # Find our record
        found = any(r["strategy_name"] == unique_name and r["symbol"] == "SBIN" for r in records)
        assert found, f"Recorded entry '{unique_name}' not found in history"
    
    def test_record_then_verify_in_dashboard(self, auth_headers):
        """Test that recorded entry affects dashboard stats"""
        # Get initial dashboard
        initial_response = requests.get(f"{BASE_URL}/api/v1/tracker/dashboard", headers=auth_headers)
        assert initial_response.status_code == 200
        initial_count = initial_response.json().get("total_records", 0)
        
        # Record a new entry
        payload = {
            "strategy_name": "TEST_Dashboard_Verify_Strategy",
            "symbol": "ICICIBANK",
            "sharpe": 1.0,
            "pnl_pct": 10.0
        }
        record_response = requests.post(f"{BASE_URL}/api/v1/tracker/record", json=payload, headers=auth_headers)
        assert record_response.status_code == 200
        
        # Verify dashboard count increased
        final_response = requests.get(f"{BASE_URL}/api/v1/tracker/dashboard", headers=auth_headers)
        assert final_response.status_code == 200
        final_count = final_response.json().get("total_records", 0)
        
        assert final_count > initial_count, "Dashboard total_records should increase after recording"
