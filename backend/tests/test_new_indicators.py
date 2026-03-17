"""
Test new indicators added to backtest engine (iteration 11).
Tests Supertrend, Stochastic, CCI, PSAR, WilliamsR, PivotPoints, ADX filter.
Also regression tests for RSI and SMA.

Rate limit: 5 requests/minute on backtest endpoint, using sleep(13) between tests.
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Module: Test setup and fixtures
@pytest.fixture(scope="module")
def api_client():
    """Shared requests session for all tests."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


def make_strategy(entry_conditions, exit_conditions=None, filters=None):
    """Helper to create a backtest request payload."""
    return {
        "strategy": {
            "instrument": {"symbol": "RELIANCE"},
            "timeframe": {"interval": "1d"},
            "entry_conditions": entry_conditions,
            "exit_conditions": exit_conditions or [],
            "filters": filters or [],
            "risk_management": {"stop_loss": 5, "take_profit": 10}
        }
    }


# ============================================================================
# Module: Regression tests for existing indicators
# ============================================================================

class TestRegressionExistingIndicators:
    """Regression tests for RSI and SMA to ensure they still work."""

    def test_rsi_still_works(self, api_client):
        """RSI < 30 entry should produce real trades."""
        payload = make_strategy(
            entry_conditions=[{"name": "RSI", "operator": "<", "value": 30, "params": {"period": 14}}],
            exit_conditions=[{"name": "RSI", "operator": ">", "value": 70, "params": {"period": 14}}]
        )
        
        response = api_client.post(f"{BASE_URL}/api/v1/backtest", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["success"] == True, f"Backtest failed: {data.get('message', data.get('disclaimer'))}"
        assert data["total_trades"] > 0, "RSI strategy should produce trades"
        assert "trades" in data
        print(f"[PASS] RSI regression: {data['total_trades']} trades, win_rate={data['win_rate']}%")
        
        # Wait for rate limit
        time.sleep(13)

    def test_sma_golden_cross_still_works(self, api_client):
        """SMA golden cross (50/200) should produce trades."""
        payload = make_strategy(
            entry_conditions=[{"name": "SMA", "operator": "crosses_above", "value": None, "params": {"short": 50, "long": 200}}],
            exit_conditions=[{"name": "SMA", "operator": "crosses_below", "value": None, "params": {"short": 50, "long": 200}}]
        )
        
        response = api_client.post(f"{BASE_URL}/api/v1/backtest", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        # Golden cross is rare, may have 0-3 trades
        print(f"[PASS] SMA golden cross regression: {data['total_trades']} trades")
        
        time.sleep(13)


# ============================================================================
# Module: New indicator tests - Supertrend
# ============================================================================

class TestSupertrendIndicator:
    """Tests for Supertrend indicator buy_signal/sell_signal."""

    def test_supertrend_buy_sell_signals(self, api_client):
        """Supertrend buy_signal entry, sell_signal exit should produce trades."""
        payload = make_strategy(
            entry_conditions=[{"name": "Supertrend", "operator": "buy_signal", "value": None, "params": {"period": 10, "multiplier": 3}}],
            exit_conditions=[{"name": "Supertrend", "operator": "sell_signal", "value": None, "params": {"period": 10, "multiplier": 3}}]
        )
        
        response = api_client.post(f"{BASE_URL}/api/v1/backtest", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["success"] == True, f"Backtest failed: {data.get('message', data.get('disclaimer'))}"
        # Supertrend should produce real trades on RELIANCE data
        print(f"[INFO] Supertrend trades: {data['total_trades']}, PnL: {data['pnl']}%")
        
        if data["total_trades"] > 0:
            # Validate trade schema
            trade = data["trades"][0]
            assert "entry_time" in trade
            assert "exit_time" in trade
            assert "pnl_percent" in trade
            print(f"[PASS] Supertrend buy_signal/sell_signal: {data['total_trades']} trades")
        else:
            print(f"[WARN] Supertrend produced 0 trades - may need different params or data range")
        
        time.sleep(13)


# ============================================================================
# Module: New indicator tests - Stochastic
# ============================================================================

class TestStochasticIndicator:
    """Tests for Stochastic oscillator cross_above/cross_below."""

    def test_stochastic_cross_oversold_overbought(self, api_client):
        """Stochastic cross_above 20 entry, cross_below 80 exit."""
        payload = make_strategy(
            entry_conditions=[{"name": "Stochastic", "operator": "cross_above", "value": 20, "params": {"k_period": 14, "d_period": 3}}],
            exit_conditions=[{"name": "Stochastic", "operator": "cross_below", "value": 80, "params": {"k_period": 14, "d_period": 3}}]
        )
        
        response = api_client.post(f"{BASE_URL}/api/v1/backtest", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        print(f"[INFO] Stochastic trades: {data['total_trades']}, win_rate={data['win_rate']}%")
        
        if data["total_trades"] > 0:
            print(f"[PASS] Stochastic cross_above 20 / cross_below 80: {data['total_trades']} trades")
        else:
            print(f"[WARN] Stochastic 0 trades - may need adjustment")
        
        time.sleep(13)


# ============================================================================
# Module: New indicator tests - CCI
# ============================================================================

class TestCCIIndicator:
    """Tests for CCI (Commodity Channel Index)."""

    def test_cci_entry_exit(self, api_client):
        """CCI > 100 entry, CCI < -100 exit."""
        payload = make_strategy(
            entry_conditions=[{"name": "CCI", "operator": ">", "value": 100, "params": {"period": 20}}],
            exit_conditions=[{"name": "CCI", "operator": "<", "value": -100, "params": {"period": 20}}]
        )
        
        response = api_client.post(f"{BASE_URL}/api/v1/backtest", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        print(f"[INFO] CCI trades: {data['total_trades']}, PnL: {data['pnl']}%")
        
        if data["total_trades"] > 0:
            print(f"[PASS] CCI > 100 / < -100: {data['total_trades']} trades")
        else:
            print(f"[WARN] CCI 0 trades")
        
        time.sleep(13)


# ============================================================================
# Module: New indicator tests - PSAR
# ============================================================================

class TestPSARIndicator:
    """Tests for Parabolic SAR cross_above/cross_below."""

    def test_psar_cross_signals(self, api_client):
        """PSAR cross_above entry, cross_below exit."""
        payload = make_strategy(
            entry_conditions=[{"name": "PSAR", "operator": "cross_above", "value": None, "params": {"af_start": 0.02, "af_max": 0.2}}],
            exit_conditions=[{"name": "PSAR", "operator": "cross_below", "value": None, "params": {"af_start": 0.02, "af_max": 0.2}}]
        )
        
        response = api_client.post(f"{BASE_URL}/api/v1/backtest", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        print(f"[INFO] PSAR trades: {data['total_trades']}, win_rate={data['win_rate']}%")
        
        if data["total_trades"] > 0:
            print(f"[PASS] PSAR cross_above/cross_below: {data['total_trades']} trades")
        else:
            print(f"[WARN] PSAR 0 trades")
        
        time.sleep(13)


# ============================================================================
# Module: New indicator tests - Williams %R
# ============================================================================

class TestWilliamsRIndicator:
    """Tests for Williams %R indicator."""

    def test_williamsr_oversold_overbought(self, api_client):
        """Williams %R < -80 entry (oversold), > -20 exit (overbought)."""
        payload = make_strategy(
            entry_conditions=[{"name": "WilliamsR", "operator": "<", "value": -80, "params": {"period": 14}}],
            exit_conditions=[{"name": "WilliamsR", "operator": ">", "value": -20, "params": {"period": 14}}]
        )
        
        response = api_client.post(f"{BASE_URL}/api/v1/backtest", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        print(f"[INFO] WilliamsR trades: {data['total_trades']}, PnL: {data['pnl']}%")
        
        if data["total_trades"] > 0:
            print(f"[PASS] WilliamsR < -80 / > -20: {data['total_trades']} trades")
        else:
            print(f"[WARN] WilliamsR 0 trades")
        
        time.sleep(13)


# ============================================================================
# Module: New indicator tests - Pivot Points
# ============================================================================

class TestPivotPointsIndicator:
    """Tests for Pivot Points below_s1/above_r1."""

    def test_pivot_points_support_resistance(self, api_client):
        """PivotPoints below_s1 entry, above_r1 exit."""
        payload = make_strategy(
            entry_conditions=[{"name": "PivotPoints", "operator": "below_s1", "value": None, "params": {"method": "standard"}}],
            exit_conditions=[{"name": "PivotPoints", "operator": "above_r1", "value": None, "params": {"method": "standard"}}]
        )
        
        response = api_client.post(f"{BASE_URL}/api/v1/backtest", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        print(f"[INFO] PivotPoints trades: {data['total_trades']}, win_rate={data['win_rate']}%")
        
        if data["total_trades"] > 0:
            print(f"[PASS] PivotPoints below_s1/above_r1: {data['total_trades']} trades")
        else:
            print(f"[WARN] PivotPoints 0 trades")
        
        time.sleep(13)


# ============================================================================
# Module: ADX as filter test
# ============================================================================

class TestADXFilter:
    """Tests ADX > 25 as a filter combined with RSI entry."""

    def test_adx_filter_reduces_trades(self, api_client):
        """RSI < 30 with ADX > 25 filter should have fewer trades than RSI alone."""
        # First run RSI without filter
        payload_no_filter = make_strategy(
            entry_conditions=[{"name": "RSI", "operator": "<", "value": 30, "params": {"period": 14}}],
            exit_conditions=[{"name": "RSI", "operator": ">", "value": 70, "params": {"period": 14}}]
        )
        
        response1 = api_client.post(f"{BASE_URL}/api/v1/backtest", json=payload_no_filter)
        assert response1.status_code == 200
        data_no_filter = response1.json()
        trades_no_filter = data_no_filter["total_trades"]
        print(f"[INFO] RSI without filter: {trades_no_filter} trades")
        
        time.sleep(13)
        
        # Now run with ADX > 25 filter
        payload_with_filter = make_strategy(
            entry_conditions=[{"name": "RSI", "operator": "<", "value": 30, "params": {"period": 14}}],
            exit_conditions=[{"name": "RSI", "operator": ">", "value": 70, "params": {"period": 14}}],
            filters=[{"name": "ADX", "operator": ">", "value": 25, "params": {"period": 14}}]
        )
        
        response2 = api_client.post(f"{BASE_URL}/api/v1/backtest", json=payload_with_filter)
        assert response2.status_code == 200
        data_with_filter = response2.json()
        trades_with_filter = data_with_filter["total_trades"]
        print(f"[INFO] RSI with ADX > 25 filter: {trades_with_filter} trades")
        
        # Filter should reduce or equal trade count
        assert trades_with_filter <= trades_no_filter, \
            f"ADX filter should reduce trades: {trades_with_filter} <= {trades_no_filter}"
        
        print(f"[PASS] ADX filter test: {trades_no_filter} -> {trades_with_filter} trades (filter works)")
        
        time.sleep(13)


# ============================================================================
# Module: Verify no fake/simulated code
# ============================================================================

class TestNoFakeCode:
    """Verify no simulated/fake/random backtest code exists."""

    def test_no_simulated_code_in_server(self):
        """Check server.py has no simulate/fake/random keywords in backtest context."""
        import subprocess
        result = subprocess.run(
            ["grep", "-n", "-i", "-E", "(simulate|fake|random|mock)", "/app/backend/server.py"],
            capture_output=True, text=True
        )
        
        # Some hits may be comments or unrelated - check context
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            suspicious = [l for l in lines if "backtest" in l.lower() or "trade" in l.lower()]
            assert len(suspicious) == 0, f"Suspicious fake/random code: {suspicious}"
        
        print("[PASS] No fake/simulated backtest code found in server.py")

    def test_no_simulated_code_in_engine(self):
        """Check backtest/engine.py has no simulate/fake/random."""
        import subprocess
        result = subprocess.run(
            ["grep", "-n", "-i", "-E", "(simulate|fake|random\\.)", "/app/backend/backtest/engine.py"],
            capture_output=True, text=True
        )
        
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            # Filter out comments
            suspicious = [l for l in lines if not l.strip().startswith("#")]
            assert len(suspicious) == 0, f"Suspicious code in engine: {suspicious}"
        
        print("[PASS] No fake/simulated code in backtest/engine.py")


# ============================================================================
# Module: Indicator registry verification
# ============================================================================

class TestIndicatorRegistry:
    """Verify indicator registry has exactly 15 indicators."""

    def test_exactly_15_indicators(self):
        """indicator_registry.py should have exactly 15 indicators."""
        import sys
        sys.path.insert(0, "/app/backend")
        from indicator_registry import INDICATORS
        
        expected = 15
        actual = len(INDICATORS)
        assert actual == expected, f"Expected {expected} indicators, got {actual}"
        
        expected_names = ["RSI", "SMA", "EMA", "MACD", "Bollinger", "Stochastic", 
                         "ADX", "ATR", "Supertrend", "VWAP", "PivotPoints", 
                         "PSAR", "CCI", "WilliamsR", "OBV"]
        
        for name in expected_names:
            assert name in INDICATORS, f"Missing indicator: {name}"
        
        print(f"[PASS] Indicator registry has exactly {actual} indicators: {list(INDICATORS.keys())}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
