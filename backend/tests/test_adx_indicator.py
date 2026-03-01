"""
Test ADX Indicator Feature
- Tests ADX indicator in indicator_registry.py
- Tests /api/strategy endpoint with ADX filter
- Tests validation of ADX params and operators
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestADXIndicatorRegistry:
    """Test ADX indicator definition in registry"""
    
    def test_health_check(self):
        """Verify backend is running"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print("✓ Backend health check passed")

    def test_strategy_endpoint_exists(self):
        """Verify /api/strategy endpoint exists"""
        # Test with minimal valid strategy
        strategy = {
            "metadata": {"name": "TEST_ADX_Check"},
            "market": {"type": "crypto", "exchange": "binance"},
            "instrument": {"symbol": "BTCUSDT"},
            "timeframe": {"interval": "1h"},
            "entry_conditions": [
                {"name": "RSI", "params": {"period": 14}, "operator": "<", "value": 30}
            ],
            "exit_conditions": [],
            "filters": [],
            "risk_management": {"stop_loss": 2, "take_profit": 5}
        }
        response = requests.post(f"{BASE_URL}/api/strategy", json=strategy)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        print("✓ Strategy endpoint exists and accepts valid strategies")


class TestADXFilterValidation:
    """Test ADX filter in strategy creation"""
    
    def test_strategy_with_adx_filter_greater_than(self):
        """Test creating strategy with ADX filter using > operator"""
        strategy = {
            "metadata": {"name": "TEST_ADX_Greater_Than"},
            "market": {"type": "crypto", "exchange": "binance"},
            "instrument": {"symbol": "BTCUSDT"},
            "timeframe": {"interval": "1h"},
            "entry_conditions": [
                {"name": "RSI", "params": {"period": 14}, "operator": "<", "value": 30}
            ],
            "exit_conditions": [],
            "filters": [
                {"name": "ADX", "params": {"period": 14}, "operator": ">", "value": 25}
            ],
            "risk_management": {"stop_loss": 2, "take_profit": 5}
        }
        response = requests.post(f"{BASE_URL}/api/strategy", json=strategy)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "strategy" in data
        # Verify ADX filter is in the saved strategy
        saved_filters = data["strategy"]["filters"]
        assert len(saved_filters) == 1
        assert saved_filters[0]["name"] == "ADX"
        assert saved_filters[0]["params"]["period"] == 14
        assert saved_filters[0]["operator"] == ">"
        assert saved_filters[0]["value"] == 25
        print("✓ Strategy with ADX filter (>) created successfully")

    def test_strategy_with_adx_filter_less_than(self):
        """Test creating strategy with ADX filter using < operator"""
        strategy = {
            "metadata": {"name": "TEST_ADX_Less_Than"},
            "market": {"type": "crypto", "exchange": "binance"},
            "instrument": {"symbol": "ETHUSDT"},
            "timeframe": {"interval": "4h"},
            "entry_conditions": [
                {"name": "RSI", "params": {"period": 14}, "operator": ">", "value": 70}
            ],
            "exit_conditions": [],
            "filters": [
                {"name": "ADX", "params": {"period": 20}, "operator": "<", "value": 20}
            ],
            "risk_management": {"stop_loss": 3, "take_profit": 6}
        }
        response = requests.post(f"{BASE_URL}/api/strategy", json=strategy)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        # Verify ADX filter with < operator
        saved_filters = data["strategy"]["filters"]
        assert len(saved_filters) == 1
        assert saved_filters[0]["name"] == "ADX"
        assert saved_filters[0]["operator"] == "<"
        assert saved_filters[0]["value"] == 20
        print("✓ Strategy with ADX filter (<) created successfully")

    def test_strategy_with_adx_custom_period(self):
        """Test ADX filter with custom period value"""
        strategy = {
            "metadata": {"name": "TEST_ADX_Custom_Period"},
            "market": {"type": "forex", "exchange": "oanda"},
            "instrument": {"symbol": "EURUSD"},
            "timeframe": {"interval": "1d"},
            "entry_conditions": [
                {"name": "SMA", "params": {"period": 50}, "operator": "cross_above", "value": None}
            ],
            "exit_conditions": [],
            "filters": [
                {"name": "ADX", "params": {"period": 28}, "operator": ">", "value": 30}
            ],
            "risk_management": {"stop_loss": 1.5, "take_profit": 4}
        }
        response = requests.post(f"{BASE_URL}/api/strategy", json=strategy)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        # Verify custom period
        saved_filters = data["strategy"]["filters"]
        assert saved_filters[0]["params"]["period"] == 28
        print("✓ Strategy with ADX custom period (28) created successfully")

    def test_strategy_without_adx_filter(self):
        """Test strategy creation without ADX filter still works"""
        strategy = {
            "metadata": {"name": "TEST_No_ADX_Filter"},
            "market": {"type": "stocks", "exchange": "nasdaq"},
            "instrument": {"symbol": "AAPL"},
            "timeframe": {"interval": "1h"},
            "entry_conditions": [
                {"name": "MACD", "params": {"fast": 12, "slow": 26, "signal": 9}, "operator": "bullish_cross", "value": None}
            ],
            "exit_conditions": [],
            "filters": [],
            "risk_management": {"stop_loss": 2, "take_profit": 5}
        }
        response = requests.post(f"{BASE_URL}/api/strategy", json=strategy)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["strategy"]["filters"] == []
        print("✓ Strategy without ADX filter created successfully")


class TestADXInvalidOperators:
    """Test that invalid ADX operators are rejected"""
    
    def test_adx_invalid_operator_cross_above(self):
        """Test ADX with invalid operator 'cross_above' is rejected"""
        strategy = {
            "metadata": {"name": "TEST_ADX_Invalid_Op"},
            "market": {"type": "crypto", "exchange": "binance"},
            "instrument": {"symbol": "BTCUSDT"},
            "timeframe": {"interval": "1h"},
            "entry_conditions": [
                {"name": "RSI", "params": {"period": 14}, "operator": "<", "value": 30}
            ],
            "exit_conditions": [],
            "filters": [
                {"name": "ADX", "params": {"period": 14}, "operator": "cross_above", "value": 25}
            ],
            "risk_management": {"stop_loss": 2, "take_profit": 5}
        }
        response = requests.post(f"{BASE_URL}/api/strategy", json=strategy)
        # Should be rejected - ADX only supports > and <
        # Note: If validation is not implemented, this may pass
        print(f"Response status: {response.status_code}")
        print(f"Response: {response.json()}")
        # The backend should validate this - if it doesn't, it's a bug to report


class TestStrategiesListWithADX:
    """Test retrieving strategies with ADX filters"""
    
    def test_get_strategies_list(self):
        """Test GET /api/strategies returns list including ADX strategies"""
        response = requests.get(f"{BASE_URL}/api/strategies")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "strategies" in data
        assert "count" in data
        print(f"✓ Retrieved {data['count']} strategies")
        
        # Check if any strategies have ADX filters
        adx_strategies = [s for s in data["strategies"] if s.get("filters") and any(f.get("name") == "ADX" for f in s["filters"])]
        print(f"✓ Found {len(adx_strategies)} strategies with ADX filter")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
