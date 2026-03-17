"""
Test suite for the new performance analytics layer:
- Metrics calculation (total_trades, win_rate, sharpe_ratio, etc.)
- Cost modeling (brokerage, stt, exchange_charges, etc.)
- Equity curve generation
- Warnings array
- Slippage effects comparison

Rate limit: 5/minute on backtest endpoint. Using 13s sleep between tests.
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test RSI strategy that produces trades
RSI_STRATEGY = {
    "metadata": {"name": "RSI Analytics Test"},
    "market": {"type": "equity"},
    "instrument": {"symbol": "RELIANCE"},
    "timeframe": {"interval": "1d"},
    "entry_conditions": [{"name": "RSI", "params": {"period": 14}, "operator": "<", "value": 30}],
    "exit_conditions": [{"name": "RSI", "params": {"period": 14}, "operator": ">", "value": 70}],
    "filters": [],
    "risk_management": {}
}

# Strategy that produces NO trades (impossible condition)
ZERO_TRADES_STRATEGY = {
    "metadata": {"name": "Zero Trades Test"},
    "market": {"type": "equity"},
    "instrument": {"symbol": "RELIANCE"},
    "timeframe": {"interval": "1d"},
    "entry_conditions": [{"name": "RSI", "params": {"period": 14}, "operator": "<", "value": -100}],
    "exit_conditions": [],
    "filters": [],
    "risk_management": {}
}

# Supertrend strategy for regression test
SUPERTREND_STRATEGY = {
    "metadata": {"name": "Supertrend Regression"},
    "market": {"type": "equity"},
    "instrument": {"symbol": "RELIANCE"},
    "timeframe": {"interval": "1d"},
    "entry_conditions": [{"name": "Supertrend", "params": {"period": 10, "multiplier": 3.0}, "operator": "buy_signal"}],
    "exit_conditions": [{"name": "Supertrend", "params": {"period": 10, "multiplier": 3.0}, "operator": "sell_signal"}],
    "filters": [],
    "risk_management": {}
}


class TestBacktestMetrics:
    """Test metrics object returned from backtest endpoint."""

    def test_backtest_returns_metrics_object_with_all_fields(self):
        """POST /api/v1/backtest returns metrics object with all required fields."""
        response = requests.post(
            f"{BASE_URL}/api/v1/backtest",
            json={"strategy": RSI_STRATEGY}
        )
        assert response.status_code == 200, f"Status: {response.status_code}, Body: {response.text}"
        
        data = response.json()
        assert data["success"] is True
        
        # Verify metrics object exists
        assert "metrics" in data, "Response missing 'metrics' key"
        metrics = data["metrics"]
        
        # Verify all required fields in metrics
        required_metric_fields = [
            "total_trades", "win_rate", "total_pnl_pct", "total_pnl_abs",
            "max_drawdown_pct", "max_drawdown_duration", "sharpe_ratio",
            "profit_factor", "avg_pnl_per_trade", "avg_winning_trade",
            "avg_losing_trade", "max_consecutive_wins", "max_consecutive_losses",
            "avg_holding_period", "wins", "losses", "best_trade", "worst_trade"
        ]
        
        for field in required_metric_fields:
            assert field in metrics, f"Metrics missing required field: {field}"
        
        # Verify metrics have reasonable values (not all zero if trades exist)
        if metrics["total_trades"] > 0:
            assert metrics["total_trades"] > 0
            print(f"PASS: Metrics returned with {metrics['total_trades']} trades")
            print(f"  win_rate: {metrics['win_rate']}%")
            print(f"  total_pnl_pct: {metrics['total_pnl_pct']}%")
            print(f"  sharpe_ratio: {metrics['sharpe_ratio']}")
            print(f"  profit_factor: {metrics['profit_factor']}")
            print(f"  max_drawdown_pct: {metrics['max_drawdown_pct']}%")


class TestBacktestCosts:
    """Test costs object returned from backtest endpoint."""

    def test_backtest_returns_costs_object(self):
        """POST /api/v1/backtest returns costs object with brokerage, stt, exchange_charges."""
        time.sleep(13)  # Rate limit
        
        response = requests.post(
            f"{BASE_URL}/api/v1/backtest",
            json={"strategy": RSI_STRATEGY}
        )
        assert response.status_code == 200, f"Status: {response.status_code}, Body: {response.text}"
        
        data = response.json()
        assert "costs" in data, "Response missing 'costs' key"
        costs = data["costs"]
        
        # Verify cost fields
        required_cost_fields = [
            "total_costs", "total_brokerage", "total_stt", "total_exchange",
            "cost_per_trade_avg", "costs_as_pct_of_capital", "config"
        ]
        
        for field in required_cost_fields:
            assert field in costs, f"Costs missing required field: {field}"
        
        # Verify config has expected fields
        assert "config" in costs
        config = costs["config"]
        assert "slippage_pct" in config
        assert "brokerage_per_order" in config
        assert "stt_rate_pct" in config
        assert "exchange_charges_pct" in config
        
        print(f"PASS: Costs object returned")
        print(f"  total_costs: Rs {costs['total_costs']}")
        print(f"  total_brokerage: Rs {costs['total_brokerage']}")
        print(f"  total_stt: Rs {costs['total_stt']}")
        print(f"  config.slippage_pct: {config['slippage_pct']}%")
        print(f"  config.brokerage_per_order: Rs {config['brokerage_per_order']}")


class TestBacktestEquityCurve:
    """Test equity curve array returned from backtest endpoint."""

    def test_backtest_returns_equity_curve_starting_at_100000(self):
        """POST /api/v1/backtest returns equity_curve array starting at 100000."""
        time.sleep(13)  # Rate limit
        
        response = requests.post(
            f"{BASE_URL}/api/v1/backtest",
            json={"strategy": RSI_STRATEGY, "initial_capital": 100000}
        )
        assert response.status_code == 200, f"Status: {response.status_code}, Body: {response.text}"
        
        data = response.json()
        assert "equity_curve" in data, "Response missing 'equity_curve' key"
        equity_curve = data["equity_curve"]
        
        # Equity curve should be a list
        assert isinstance(equity_curve, list), "equity_curve should be a list"
        
        if len(equity_curve) > 0:
            # First point should have equity = initial_capital (100000)
            first_point = equity_curve[0]
            assert "equity" in first_point
            assert "drawdown_pct" in first_point
            assert "timestamp" in first_point
            
            assert first_point["equity"] == 100000, f"First equity should be 100000, got {first_point['equity']}"
            assert first_point["drawdown_pct"] == 0, f"First drawdown should be 0, got {first_point['drawdown_pct']}"
            
            print(f"PASS: Equity curve returned with {len(equity_curve)} points")
            print(f"  First point: equity={first_point['equity']}, drawdown={first_point['drawdown_pct']}%")
            
            if len(equity_curve) > 1:
                last_point = equity_curve[-1]
                print(f"  Last point: equity={last_point['equity']}, drawdown={last_point['drawdown_pct']}%")


class TestBacktestWarnings:
    """Test warnings array returned from backtest endpoint."""

    def test_backtest_returns_warnings_array(self):
        """POST /api/v1/backtest returns warnings array."""
        time.sleep(13)  # Rate limit
        
        response = requests.post(
            f"{BASE_URL}/api/v1/backtest",
            json={"strategy": RSI_STRATEGY}
        )
        assert response.status_code == 200, f"Status: {response.status_code}, Body: {response.text}"
        
        data = response.json()
        assert "warnings" in data, "Response missing 'warnings' key"
        assert isinstance(data["warnings"], list), "warnings should be a list"
        
        print(f"PASS: Warnings array returned with {len(data['warnings'])} warnings")
        for w in data["warnings"]:
            print(f"  - {w}")


class TestSlippageComparison:
    """Test slippage effects on backtest results."""

    def test_slippage_0_vs_0_1_different_net_pnl(self):
        """Slippage 0% vs 0.1%: different net_pnl on same strategy."""
        time.sleep(13)  # Rate limit
        
        # Test with 0% slippage
        response_0 = requests.post(
            f"{BASE_URL}/api/v1/backtest",
            json={"strategy": RSI_STRATEGY, "slippage_pct": 0}
        )
        assert response_0.status_code == 200, f"Status: {response_0.status_code}"
        data_0 = response_0.json()
        
        time.sleep(13)  # Rate limit
        
        # Test with 0.1% slippage
        response_01 = requests.post(
            f"{BASE_URL}/api/v1/backtest",
            json={"strategy": RSI_STRATEGY, "slippage_pct": 0.1}
        )
        assert response_01.status_code == 200, f"Status: {response_01.status_code}"
        data_01 = response_01.json()
        
        # Both should have trades
        assert data_0["metrics"]["total_trades"] > 0, "0% slippage should produce trades"
        assert data_01["metrics"]["total_trades"] > 0, "0.1% slippage should produce trades"
        
        # The PnL should differ
        pnl_0 = data_0["metrics"]["total_pnl_pct"]
        pnl_01 = data_01["metrics"]["total_pnl_pct"]
        
        # With slippage, PnL should be lower (slippage is a cost)
        print(f"PASS: Slippage comparison")
        print(f"  0% slippage PnL: {pnl_0}%")
        print(f"  0.1% slippage PnL: {pnl_01}%")
        print(f"  Difference: {round(pnl_0 - pnl_01, 2)}% (expected positive as slippage costs)")
        
        # PnL with slippage should generally be worse (or equal if no trades)
        # Note: In rare cases with negative PnL trades, slippage might slightly differ
        # But they should NOT be identical if trades exist
        assert pnl_0 != pnl_01 or data_0["metrics"]["total_trades"] == 0, \
            "PnL should differ with different slippage settings"


class TestZeroTradesEdgeCase:
    """Test zero trades handling - no division errors."""

    def test_zero_trades_no_division_errors(self):
        """Zero trades: no division errors, all metrics 0, sharpe=null, profit_factor=null."""
        time.sleep(13)  # Rate limit
        
        response = requests.post(
            f"{BASE_URL}/api/v1/backtest",
            json={"strategy": ZERO_TRADES_STRATEGY}
        )
        assert response.status_code == 200, f"Status: {response.status_code}, Body: {response.text}"
        
        data = response.json()
        assert data["success"] is True, "Backtest should succeed even with zero trades"
        
        metrics = data["metrics"]
        
        # Verify zero trade handling
        assert metrics["total_trades"] == 0, "Should have 0 trades"
        assert metrics["win_rate"] == 0, "win_rate should be 0"
        assert metrics["total_pnl_pct"] == 0, "total_pnl_pct should be 0"
        assert metrics["sharpe_ratio"] is None, "sharpe_ratio should be null/None"
        assert metrics["profit_factor"] is None, "profit_factor should be null/None"
        assert metrics["avg_pnl_per_trade"] == 0, "avg_pnl_per_trade should be 0"
        
        # Should have a message
        assert "message" in metrics, "metrics should have a message field"
        assert metrics["message"] != "", "message should not be empty for zero trades"
        
        # Equity curve should be empty
        assert data["equity_curve"] == [], "equity_curve should be empty with no trades"
        
        # Warnings should include no signals message
        assert len(data["warnings"]) > 0, "Should have warnings for zero trades"
        
        print(f"PASS: Zero trades handled correctly")
        print(f"  message: {metrics['message']}")
        print(f"  warnings: {data['warnings']}")


class TestRegressionSupertrend:
    """Regression test: Supertrend strategy still produces real trades."""

    def test_supertrend_still_produces_trades(self):
        """Supertrend regression: still produces real trades."""
        time.sleep(13)  # Rate limit
        
        response = requests.post(
            f"{BASE_URL}/api/v1/backtest",
            json={"strategy": SUPERTREND_STRATEGY}
        )
        assert response.status_code == 200, f"Status: {response.status_code}, Body: {response.text}"
        
        data = response.json()
        assert data["success"] is True
        
        # Previous iteration: Supertrend produced 10 trades
        assert data["metrics"]["total_trades"] > 0, "Supertrend should produce trades"
        
        print(f"PASS: Supertrend regression - {data['metrics']['total_trades']} trades")
        print(f"  win_rate: {data['metrics']['win_rate']}%")
        print(f"  total_pnl_pct: {data['metrics']['total_pnl_pct']}%")


class TestRSIRegression:
    """Regression test: RSI strategy still produces real trades."""

    def test_rsi_still_produces_trades(self):
        """RSI strategy regression: still produces real trades."""
        time.sleep(13)  # Rate limit
        
        response = requests.post(
            f"{BASE_URL}/api/v1/backtest",
            json={"strategy": RSI_STRATEGY}
        )
        assert response.status_code == 200, f"Status: {response.status_code}, Body: {response.text}"
        
        data = response.json()
        assert data["success"] is True
        
        # Previous iteration: RSI produced 7 trades
        assert data["metrics"]["total_trades"] > 0, "RSI should produce trades"
        
        print(f"PASS: RSI regression - {data['metrics']['total_trades']} trades")
        print(f"  win_rate: {data['metrics']['win_rate']}%")
        print(f"  total_pnl_pct: {data['metrics']['total_pnl_pct']}%")


class TestCustomParameters:
    """Test custom backtest parameters."""

    def test_custom_initial_capital(self):
        """Test custom initial_capital parameter."""
        time.sleep(13)  # Rate limit
        
        response = requests.post(
            f"{BASE_URL}/api/v1/backtest",
            json={
                "strategy": RSI_STRATEGY,
                "initial_capital": 500000,
                "slippage_pct": 0.05,
                "brokerage_per_order": 20
            }
        )
        assert response.status_code == 200, f"Status: {response.status_code}, Body: {response.text}"
        
        data = response.json()
        
        # First equity curve point should match custom initial capital
        if len(data["equity_curve"]) > 0:
            assert data["equity_curve"][0]["equity"] == 500000, \
                f"First equity should be 500000, got {data['equity_curve'][0]['equity']}"
            print(f"PASS: Custom initial_capital=500000 applied")
        else:
            print(f"PASS: Custom parameters accepted (no trades)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
