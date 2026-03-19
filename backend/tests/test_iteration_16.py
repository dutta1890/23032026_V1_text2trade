"""
Iteration 16 Tests: Screener, Multi-Stock Backtest, and Strategy Comparison
============================================================================
Tests for:
- GET /api/v1/screener/presets - 5 presets (no auth required)
- POST /api/v1/screener/scan - with preset/custom conditions (auth required)
- POST /api/v1/backtest/multi - multi-stock backtest up to 10 symbols
- POST /api/v1/backtest/compare - strategy comparison up to 5 strategies
- GET /api/v1/admin/screener/stats - admin analytics
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
TEST_USER_EMAIL = "testai@example.com"
TEST_USER_PASSWORD = "Password123!"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "Password123!"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def user_token(api_client):
    """Get authentication token for test user."""
    response = api_client.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
    )
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"User login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def admin_token(api_client):
    """Get authentication token for admin user."""
    # Wait a bit to avoid rate limiting
    time.sleep(1)
    response = api_client.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def authenticated_client(api_client, user_token):
    """Session with user auth header."""
    api_client.headers.update({"Authorization": f"Bearer {user_token}"})
    return api_client


# =============================================================================
# SCREENER PRESETS TESTS (No Auth Required)
# =============================================================================

class TestScreenerPresets:
    """Tests for GET /api/v1/screener/presets (no auth)."""

    def test_list_presets_returns_5(self, api_client):
        """GET /api/v1/screener/presets returns 5 presets."""
        response = api_client.get(f"{BASE_URL}/api/v1/screener/presets")
        assert response.status_code == 200
        data = response.json()
        assert "presets" in data
        assert data["count"] == 5
        assert len(data["presets"]) == 5

    def test_presets_have_expected_ids(self, api_client):
        """Presets include oversold, trending_up, vwap_breakout, bollinger_squeeze, momentum_surge."""
        response = api_client.get(f"{BASE_URL}/api/v1/screener/presets")
        assert response.status_code == 200
        presets = response.json()["presets"]
        preset_ids = [p["id"] for p in presets]
        
        expected = ["oversold", "trending_up", "vwap_breakout", "bollinger_squeeze", "momentum_surge"]
        for exp_id in expected:
            assert exp_id in preset_ids, f"Expected preset '{exp_id}' not found in {preset_ids}"

    def test_presets_have_required_fields(self, api_client):
        """Each preset has id, name, description, conditions_count."""
        response = api_client.get(f"{BASE_URL}/api/v1/screener/presets")
        assert response.status_code == 200
        presets = response.json()["presets"]
        
        for preset in presets:
            assert "id" in preset
            assert "name" in preset
            assert "description" in preset
            assert "conditions_count" in preset
            assert isinstance(preset["conditions_count"], int)
            assert preset["conditions_count"] >= 1


# =============================================================================
# SCREENER SCAN TESTS (Auth Required)
# =============================================================================

class TestScreenerScan:
    """Tests for POST /api/v1/screener/scan."""

    def test_scan_without_auth_returns_401(self, api_client):
        """POST /api/v1/screener/scan without auth returns 401."""
        # Clear any auth header
        headers = {"Content-Type": "application/json"}
        response = requests.post(
            f"{BASE_URL}/api/v1/screener/scan",
            json={"preset": "oversold"},
            headers=headers
        )
        assert response.status_code in [401, 403]

    def test_scan_with_preset_oversold(self, api_client, user_token):
        """POST /api/v1/screener/scan with preset='oversold' returns valid response."""
        response = requests.post(
            f"{BASE_URL}/api/v1/screener/scan",
            json={"preset": "oversold"},
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "matches" in data
        assert "total_scanned" in data
        assert "scan_time_ms" in data
        assert data["preset"] == "oversold"
        assert data["preset_name"] == "Oversold"
        # matches can be empty or have items
        assert isinstance(data["matches"], list)

    def test_scan_with_preset_trending_up(self, api_client, user_token):
        """POST /api/v1/screener/scan with preset='trending_up' returns valid response."""
        time.sleep(1)  # Rate limit consideration
        response = requests.post(
            f"{BASE_URL}/api/v1/screener/scan",
            json={"preset": "trending_up"},
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["preset"] == "trending_up"
        assert data["preset_name"] == "Trending Up"
        assert "matches" in data

    def test_scan_with_preset_vwap_breakout(self, api_client, user_token):
        """POST /api/v1/screener/scan with preset='vwap_breakout' returns valid response."""
        time.sleep(1)
        response = requests.post(
            f"{BASE_URL}/api/v1/screener/scan",
            json={"preset": "vwap_breakout"},
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["preset"] == "vwap_breakout"
        assert data["preset_name"] == "VWAP Breakout"
        assert "matches" in data

    def test_scan_with_preset_bollinger_squeeze(self, api_client, user_token):
        """POST /api/v1/screener/scan with preset='bollinger_squeeze' returns valid response."""
        time.sleep(1)
        response = requests.post(
            f"{BASE_URL}/api/v1/screener/scan",
            json={"preset": "bollinger_squeeze"},
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["preset"] == "bollinger_squeeze"
        assert data["preset_name"] == "Bollinger Squeeze"
        assert "matches" in data

    def test_scan_with_preset_momentum_surge(self, api_client, user_token):
        """POST /api/v1/screener/scan with preset='momentum_surge' returns valid response."""
        time.sleep(1)
        response = requests.post(
            f"{BASE_URL}/api/v1/screener/scan",
            json={"preset": "momentum_surge"},
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["preset"] == "momentum_surge"
        assert data["preset_name"] == "Momentum Surge"
        assert "matches" in data

    def test_scan_with_custom_conditions_rsi_below_40(self, api_client, user_token):
        """POST /api/v1/screener/scan with custom conditions (RSI < 40) returns matches."""
        time.sleep(1)
        response = requests.post(
            f"{BASE_URL}/api/v1/screener/scan",
            json={
                "conditions": [
                    {"name": "RSI", "params": {"period": 14}, "operator": "<", "value": 40}
                ]
            },
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "matches" in data
        assert "total_scanned" in data
        assert isinstance(data["matches"], list)
        # If matches exist, verify structure
        if data["matches"]:
            match = data["matches"][0]
            assert "symbol" in match
            assert "indicator_values" in match
            assert "RSI" in match["indicator_values"] or any("RSI" in k for k in match["indicator_values"].keys())

    def test_scan_with_invalid_preset_returns_400(self, api_client, user_token):
        """POST /api/v1/screener/scan with invalid preset returns 400."""
        time.sleep(1)
        response = requests.post(
            f"{BASE_URL}/api/v1/screener/scan",
            json={"preset": "invalid_preset_name"},
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "Unknown preset" in data["detail"]

    def test_scan_without_conditions_or_preset_returns_400(self, api_client, user_token):
        """POST /api/v1/screener/scan without conditions or preset returns 400."""
        time.sleep(1)
        response = requests.post(
            f"{BASE_URL}/api/v1/screener/scan",
            json={},
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 400


# =============================================================================
# MULTI-STOCK BACKTEST TESTS (Auth Required)
# =============================================================================

class TestMultiStockBacktest:
    """Tests for POST /api/v1/backtest/multi."""

    def test_multi_backtest_with_5_symbols(self, api_client, user_token):
        """POST /api/v1/backtest/multi with 5 symbols returns 5 independent results."""
        # RSI Mean Reversion strategy that generates trades
        strategy = {
            "metadata": {"name": "RSI Mean Reversion Test"},
            "entry_conditions": [
                {"name": "RSI", "params": {"period": 14}, "operator": "<", "value": 30}
            ],
            "exit_conditions": [
                {"name": "RSI", "params": {"period": 14}, "operator": ">", "value": 70}
            ],
            "risk_management": {
                "stop_loss": {"type": "percentage", "value": 3},
                "target_profit": None,
                "trailing_stop_loss": {"enabled": False}
            }
        }
        
        symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"]
        
        response = requests.post(
            f"{BASE_URL}/api/v1/backtest/multi",
            json={
                "strategy": strategy,
                "symbols": symbols,
                "timeframe": "1d",
                "initial_capital": 100000
            },
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {user_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "results" in data
        assert len(data["results"]) == 5
        assert data["total_symbols"] == 5
        assert "successful" in data
        
        # Each result should have symbol
        for result in data["results"]:
            assert "symbol" in result
            assert result["symbol"] in symbols

    def test_multi_backtest_results_sorted_by_pnl(self, api_client, user_token):
        """POST /api/v1/backtest/multi results are sorted by P&L descending."""
        time.sleep(1)
        strategy = {
            "metadata": {"name": "RSI Mean Reversion Test"},
            "entry_conditions": [
                {"name": "RSI", "params": {"period": 14}, "operator": "<", "value": 35}
            ],
            "exit_conditions": [
                {"name": "RSI", "params": {"period": 14}, "operator": ">", "value": 65}
            ],
            "risk_management": {
                "stop_loss": {"type": "percentage", "value": 4},
                "target_profit": None,
                "trailing_stop_loss": {"enabled": False}
            }
        }
        
        symbols = ["RELIANCE", "TCS", "INFY"]
        
        response = requests.post(
            f"{BASE_URL}/api/v1/backtest/multi",
            json={
                "strategy": strategy,
                "symbols": symbols,
                "timeframe": "1d"
            },
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {user_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check results are sorted by total_pnl_pct descending
        results = data["results"]
        pnl_values = []
        for r in results:
            pnl = r.get("metrics", {}).get("total_pnl_pct")
            if pnl is None:
                pnl = float("-inf")
            pnl_values.append(pnl)
        
        # Verify descending order
        for i in range(len(pnl_values) - 1):
            assert pnl_values[i] >= pnl_values[i + 1], f"Results not sorted: {pnl_values}"

    def test_multi_backtest_more_than_10_symbols_returns_error(self, api_client, user_token):
        """POST /api/v1/backtest/multi with >10 symbols returns 400 or 422."""
        time.sleep(1)
        strategy = {
            "metadata": {"name": "Test Strategy"},
            "entry_conditions": [
                {"name": "RSI", "params": {"period": 14}, "operator": "<", "value": 30}
            ],
            "exit_conditions": [],
            "risk_management": {}
        }
        
        # 11 symbols - should fail
        symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", 
                   "ITC", "HINDUNILVR", "SBIN", "BHARTIARTL", "KOTAKBANK", "LT"]
        
        response = requests.post(
            f"{BASE_URL}/api/v1/backtest/multi",
            json={
                "strategy": strategy,
                "symbols": symbols,
                "timeframe": "1d"
            },
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {user_token}"}
        )
        
        # 400 if caught by endpoint logic, 422 if caught by Pydantic validation (max_length=10)
        assert response.status_code in [400, 422], f"Expected 400/422 but got {response.status_code}"


# =============================================================================
# STRATEGY COMPARISON TESTS (Auth Required)
# =============================================================================

class TestStrategyComparison:
    """Tests for POST /api/v1/backtest/compare."""

    def test_compare_2_strategies_on_reliance(self, api_client, user_token):
        """POST /api/v1/backtest/compare with 2 strategies on RELIANCE returns ranked results."""
        # RSI Mean Reversion
        strategy1 = {
            "metadata": {"name": "RSI Mean Reversion"},
            "entry_conditions": [
                {"name": "RSI", "params": {"period": 14}, "operator": "<", "value": 30}
            ],
            "exit_conditions": [
                {"name": "RSI", "params": {"period": 14}, "operator": ">", "value": 70}
            ],
            "risk_management": {
                "stop_loss": {"type": "percentage", "value": 3}
            }
        }
        
        # MACD Momentum
        strategy2 = {
            "metadata": {"name": "MACD Momentum"},
            "entry_conditions": [
                {"name": "MACD", "params": {"fast": 12, "slow": 26, "signal": 9}, "operator": "bullish_cross"}
            ],
            "exit_conditions": [
                {"name": "MACD", "params": {"fast": 12, "slow": 26, "signal": 9}, "operator": "bearish_cross"}
            ],
            "risk_management": {
                "stop_loss": {"type": "percentage", "value": 2.5}
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/api/v1/backtest/compare",
            json={
                "strategies": [strategy1, strategy2],
                "symbol": "RELIANCE",
                "timeframe": "1d",
                "initial_capital": 100000
            },
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {user_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "results" in data
        assert len(data["results"]) == 2
        assert data["total_strategies"] == 2
        assert data["symbol"] == "RELIANCE"
        assert "successful" in data
        assert "best_strategy" in data
        
        # Check ranking is present
        for result in data["results"]:
            assert "rank" in result
            assert "strategy_name" in result

    def test_compare_results_ranked_by_sharpe_ratio(self, api_client, user_token):
        """POST /api/v1/backtest/compare results ranked by Sharpe ratio."""
        time.sleep(1)
        strategies = [
            {
                "metadata": {"name": "Strategy A"},
                "entry_conditions": [
                    {"name": "RSI", "params": {"period": 14}, "operator": "<", "value": 30}
                ],
                "exit_conditions": [
                    {"name": "RSI", "params": {"period": 14}, "operator": ">", "value": 70}
                ],
                "risk_management": {"stop_loss": {"type": "percentage", "value": 3}}
            },
            {
                "metadata": {"name": "Strategy B"},
                "entry_conditions": [
                    {"name": "SMA", "params": {"short": 9, "long": 21}, "operator": "crosses_above"}
                ],
                "exit_conditions": [
                    {"name": "SMA", "params": {"short": 9, "long": 21}, "operator": "crosses_below"}
                ],
                "risk_management": {"stop_loss": {"type": "percentage", "value": 2}}
            }
        ]
        
        response = requests.post(
            f"{BASE_URL}/api/v1/backtest/compare",
            json={
                "strategies": strategies,
                "symbol": "TCS",
                "timeframe": "1d"
            },
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {user_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify rankings are 1, 2 (sorted by Sharpe)
        results = data["results"]
        ranks = [r["rank"] for r in results]
        assert ranks == [1, 2]
        
        # First result (rank 1) should have best/equal Sharpe
        sharpe_values = []
        for r in results:
            sharpe = r.get("metrics", {}).get("sharpe_ratio")
            if sharpe is None:
                sharpe = float("-inf")
            sharpe_values.append(sharpe)
        
        # Verify descending order by Sharpe
        assert sharpe_values[0] >= sharpe_values[1]

    def test_compare_more_than_5_strategies_returns_error(self, api_client, user_token):
        """POST /api/v1/backtest/compare with >5 strategies returns 400 or 422."""
        time.sleep(1)
        # Create 6 strategies
        strategies = []
        for i in range(6):
            strategies.append({
                "metadata": {"name": f"Strategy {i+1}"},
                "entry_conditions": [
                    {"name": "RSI", "params": {"period": 14}, "operator": "<", "value": 30 + i}
                ],
                "exit_conditions": [],
                "risk_management": {}
            })
        
        response = requests.post(
            f"{BASE_URL}/api/v1/backtest/compare",
            json={
                "strategies": strategies,
                "symbol": "RELIANCE",
                "timeframe": "1d"
            },
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {user_token}"}
        )
        
        # 400 if caught by endpoint logic, 422 if caught by Pydantic validation (max_length=5)
        assert response.status_code in [400, 422], f"Expected 400/422 but got {response.status_code}"


# =============================================================================
# ADMIN SCREENER STATS TESTS
# =============================================================================

class TestAdminScreenerStats:
    """Tests for GET /api/v1/admin/screener/stats."""

    def test_admin_stats_as_admin_returns_data(self, api_client, admin_token):
        """GET /api/v1/admin/screener/stats as admin returns most_run_presets and most_scanned_symbols."""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/screener/stats",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # API returns most_run_presets, most_scanned_symbols, total_preset_runs, total_symbol_matches
        assert "most_run_presets" in data
        assert "most_scanned_symbols" in data
        assert "total_preset_runs" in data
        assert "total_symbol_matches" in data
        assert isinstance(data["most_run_presets"], list)
        assert isinstance(data["most_scanned_symbols"], list)

    def test_admin_stats_as_non_admin_returns_403(self, api_client, user_token):
        """GET /api/v1/admin/screener/stats as non-admin returns 403."""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/screener/stats",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {user_token}"}
        )
        
        assert response.status_code == 403


# =============================================================================
# RUN TESTS DIRECTLY
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
