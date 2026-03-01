"""
Test suite for backtest endpoint - Historical backtest using yfinance
Tests SMA/EMA strategies with yfinance data and fallback to simulated for other indicators
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestBacktestEndpoint:
    """Tests for /api/backtest endpoint"""
    
    def test_backtest_endpoint_exists(self):
        """Test that backtest endpoint exists and responds"""
        response = requests.post(f"{BASE_URL}/api/backtest", json={
            "strategy": {
                "instrument": {"symbol": "AAPL"},
                "entry_conditions": [{"name": "SMA", "params": {"short": 9, "long": 21}, "operator": "cross_above"}],
                "risk_management": {"stop_loss": 2, "take_profit": 5}
            }
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
    
    def test_sma_strategy_aapl_uses_yfinance(self):
        """Test SMA strategy with AAPL uses historical yfinance data"""
        response = requests.post(f"{BASE_URL}/api/backtest", json={
            "strategy": {
                "instrument": {"symbol": "AAPL"},
                "entry_conditions": [{"name": "SMA", "params": {"short": 9, "long": 21}, "operator": "cross_above"}],
                "risk_management": {"stop_loss": 2, "take_profit": 5}
            }
        })
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert data["success"] == True
        assert "trades" in data
        assert "win_rate" in data
        assert "pnl" in data
        assert "total_trades" in data
        assert "wins" in data
        assert "losses" in data
        assert "data_source" in data
        
        # Verify yfinance data source
        assert "yfinance" in data["data_source"]
        assert "AAPL" in data["data_source"]
        assert data["label"] == "Historical"
    
    def test_sma_strategy_btcusdt_maps_to_btc_usd(self):
        """Test BTCUSDT symbol maps to BTC-USD for yfinance"""
        response = requests.post(f"{BASE_URL}/api/backtest", json={
            "strategy": {
                "instrument": {"symbol": "BTCUSDT"},
                "entry_conditions": [{"name": "SMA", "params": {"short": 10, "long": 30}, "operator": "cross_above"}],
                "risk_management": {"stop_loss": 3, "take_profit": 6}
            }
        })
        assert response.status_code == 200
        data = response.json()
        
        # Verify BTC-USD mapping
        assert data["success"] == True
        assert "yfinance" in data["data_source"]
        assert "BTC-USD" in data["data_source"]
        assert data["label"] == "Historical"
    
    def test_sma_strategy_ethusdt_maps_to_eth_usd(self):
        """Test ETHUSDT symbol maps to ETH-USD for yfinance"""
        response = requests.post(f"{BASE_URL}/api/backtest", json={
            "strategy": {
                "instrument": {"symbol": "ETHUSDT"},
                "entry_conditions": [{"name": "SMA", "params": {"short": 9, "long": 21}, "operator": "cross_above"}],
                "risk_management": {"stop_loss": 2, "take_profit": 5}
            }
        })
        assert response.status_code == 200
        data = response.json()
        
        # Verify ETH-USD mapping
        assert data["success"] == True
        assert "yfinance" in data["data_source"]
        assert "ETH-USD" in data["data_source"]
        assert data["label"] == "Historical"
    
    def test_ema_strategy_uses_yfinance(self):
        """Test EMA strategy also uses yfinance historical data"""
        response = requests.post(f"{BASE_URL}/api/backtest", json={
            "strategy": {
                "instrument": {"symbol": "MSFT"},
                "entry_conditions": [{"name": "EMA", "params": {"short": 12, "long": 26}, "operator": "cross_above"}],
                "risk_management": {"stop_loss": 2, "take_profit": 5}
            }
        })
        assert response.status_code == 200
        data = response.json()
        
        # Verify yfinance data source for EMA
        assert data["success"] == True
        assert "yfinance" in data["data_source"]
        assert "MSFT" in data["data_source"]
        assert data["label"] == "Historical"
    
    def test_rsi_strategy_falls_back_to_simulated(self):
        """Test RSI strategy falls back to simulated backtest"""
        response = requests.post(f"{BASE_URL}/api/backtest", json={
            "strategy": {
                "instrument": {"symbol": "AAPL"},
                "entry_conditions": [{"name": "RSI", "params": {"period": 14}, "operator": ">", "value": 70}],
                "risk_management": {"stop_loss": 2, "take_profit": 5}
            }
        })
        assert response.status_code == 200
        data = response.json()
        
        # Verify simulated fallback
        assert data["success"] == True
        assert data["data_source"] == "simulated"
        assert data["label"] == "Simulated"
    
    def test_macd_strategy_falls_back_to_simulated(self):
        """Test MACD strategy falls back to simulated backtest"""
        response = requests.post(f"{BASE_URL}/api/backtest", json={
            "strategy": {
                "instrument": {"symbol": "AAPL"},
                "entry_conditions": [{"name": "MACD", "params": {"fast": 12, "slow": 26, "signal": 9}, "operator": "bullish_cross"}],
                "risk_management": {"stop_loss": 2, "take_profit": 5}
            }
        })
        assert response.status_code == 200
        data = response.json()
        
        # Verify simulated fallback
        assert data["success"] == True
        assert data["data_source"] == "simulated"
        assert data["label"] == "Simulated"
    
    def test_backtest_response_has_required_fields(self):
        """Test backtest response contains all required fields"""
        response = requests.post(f"{BASE_URL}/api/backtest", json={
            "strategy": {
                "instrument": {"symbol": "AAPL"},
                "entry_conditions": [{"name": "SMA", "params": {"short": 9, "long": 21}, "operator": "cross_above"}],
                "risk_management": {"stop_loss": 2, "take_profit": 5}
            }
        })
        assert response.status_code == 200
        data = response.json()
        
        # Verify all required fields
        required_fields = ["success", "label", "trades", "win_rate", "pnl", "total_trades", "wins", "losses", "data_source"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        # Verify trades structure
        assert isinstance(data["trades"], list)
        if len(data["trades"]) > 0:
            trade = data["trades"][0]
            trade_fields = ["id", "symbol", "entry", "exit", "pnl", "result", "date"]
            for field in trade_fields:
                assert field in trade, f"Missing trade field: {field}"
    
    def test_backtest_win_rate_calculation(self):
        """Test win rate is calculated correctly"""
        response = requests.post(f"{BASE_URL}/api/backtest", json={
            "strategy": {
                "instrument": {"symbol": "AAPL"},
                "entry_conditions": [{"name": "SMA", "params": {"short": 9, "long": 21}, "operator": "cross_above"}],
                "risk_management": {"stop_loss": 2, "take_profit": 5}
            }
        })
        assert response.status_code == 200
        data = response.json()
        
        # Verify win rate calculation
        if data["total_trades"] > 0:
            expected_win_rate = round((data["wins"] / data["total_trades"]) * 100, 1)
            assert data["win_rate"] == expected_win_rate
        
        # Verify wins + losses = total_trades
        assert data["wins"] + data["losses"] == data["total_trades"]
    
    def test_backtest_with_custom_sma_periods(self):
        """Test backtest with custom SMA periods"""
        response = requests.post(f"{BASE_URL}/api/backtest", json={
            "strategy": {
                "instrument": {"symbol": "GOOGL"},
                "entry_conditions": [{"name": "SMA", "params": {"short": 20, "long": 50}, "operator": "cross_above"}],
                "risk_management": {"stop_loss": 3, "take_profit": 8}
            }
        })
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert "yfinance" in data["data_source"]


class TestBacktestDataValidation:
    """Tests for backtest data validation"""
    
    def test_backtest_trades_have_valid_pnl(self):
        """Test that trade PnL values are valid numbers"""
        response = requests.post(f"{BASE_URL}/api/backtest", json={
            "strategy": {
                "instrument": {"symbol": "AAPL"},
                "entry_conditions": [{"name": "SMA", "params": {"short": 9, "long": 21}, "operator": "cross_above"}],
                "risk_management": {"stop_loss": 2, "take_profit": 5}
            }
        })
        assert response.status_code == 200
        data = response.json()
        
        for trade in data["trades"]:
            assert isinstance(trade["pnl"], (int, float))
            assert isinstance(trade["entry"], (int, float))
            assert isinstance(trade["exit"], (int, float))
            assert trade["result"] in ["WIN", "LOSS"]
    
    def test_backtest_total_pnl_matches_sum(self):
        """Test that total PnL matches sum of individual trade PnLs"""
        response = requests.post(f"{BASE_URL}/api/backtest", json={
            "strategy": {
                "instrument": {"symbol": "AAPL"},
                "entry_conditions": [{"name": "SMA", "params": {"short": 9, "long": 21}, "operator": "cross_above"}],
                "risk_management": {"stop_loss": 2, "take_profit": 5}
            }
        })
        assert response.status_code == 200
        data = response.json()
        
        # Calculate sum of trade PnLs
        calculated_pnl = sum(trade["pnl"] for trade in data["trades"])
        
        # Allow small floating point difference
        assert abs(data["pnl"] - calculated_pnl) < 0.1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
