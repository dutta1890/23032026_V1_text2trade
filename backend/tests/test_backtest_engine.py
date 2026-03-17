"""
Backtest Engine Tests - Tests the real indicator backtest engine.

Covers:
- RSI strategy with real trades
- SMA golden cross (short=50, long=200) 
- MACD bullish_cross
- Bollinger Bands lower_touch/upper_touch
- Impossible conditions returning 0 trades
- Non-existent symbols returning error with available symbols
- Missing entry_conditions error
- Trade schema validation
"""

import os
import pytest
import requests
import time

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")


def make_backtest_request(strategy_json, max_retries=3):
    """Make a backtest request with retry logic for rate limiting"""
    for attempt in range(max_retries):
        response = requests.post(
            f"{BASE_URL}/api/v1/backtest",
            json={"strategy": strategy_json},
            headers={"Content-Type": "application/json"},
        )
        if response.status_code == 429:
            # Rate limited - wait and retry
            wait_time = 15 * (attempt + 1)  # 15, 30, 45 seconds
            print(f"Rate limited, waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
            time.sleep(wait_time)
            continue
        return response
    return response  # Return last response even if rate limited


class TestBacktestEngineRSI:
    """RSI strategy backtest tests"""

    def test_rsi_strategy_returns_real_trades(self):
        """POST /api/v1/backtest with RSI strategy should return real trades with real dates"""
        strategy = {
            "instrument": {"symbol": "RELIANCE"},
            "timeframe": {"interval": "1d"},
            "entry_conditions": [
                {"name": "RSI", "params": {"period": 14}, "operator": "<", "value": 30}
            ],
            "exit_conditions": [
                {"name": "RSI", "params": {"period": 14}, "operator": ">", "value": 70}
            ],
            "risk_management": {},
        }
        response = make_backtest_request(strategy)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        # Verify success
        assert data["success"] is True
        assert data["label"] == "Historical Backtest (Real Indicators)"
        assert "mongodb" in data["data_source"]

        # Verify we have real trades with proper structure
        assert data["total_trades"] > 0
        assert len(data["trades"]) == data["total_trades"]

        # Verify trade schema
        trade = data["trades"][0]
        assert "entry_time" in trade
        assert "entry_price" in trade
        assert "exit_time" in trade
        assert "exit_price" in trade
        assert "pnl_points" in trade
        assert "pnl_percent" in trade
        assert "holding_candles" in trade

        # Verify dates are real (YYYY-MM-DD format)
        assert len(trade["entry_time"]) == 10
        assert "-" in trade["entry_time"]
        print(f"PASS: RSI strategy returned {data['total_trades']} real trades")

    def test_impossible_rsi_condition_returns_zero_trades(self):
        """POST /api/v1/backtest with impossible RSI < 1 should return 0 trades with message (NOT random)"""
        strategy = {
            "instrument": {"symbol": "RELIANCE"},
            "timeframe": {"interval": "1d"},
            "entry_conditions": [
                {"name": "RSI", "params": {"period": 14}, "operator": "<", "value": 1}
            ],
            "exit_conditions": [],
            "risk_management": {},
        }
        response = make_backtest_request(strategy)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        # Verify success=true but 0 trades
        assert data["success"] is True
        assert data["total_trades"] == 0
        assert len(data["trades"]) == 0

        # Verify message explains no signals (not random data)
        assert "no signal" in data["message"].lower() or "never met" in data["message"].lower()
        print(f"PASS: Impossible RSI < 1 returned 0 trades with message: {data['message']}")


class TestBacktestEngineSMA:
    """SMA strategy backtest tests"""

    def test_sma_golden_cross_returns_specific_trades(self):
        """POST /api/v1/backtest with SMA golden cross (short=50, long=200) should return 2 trades at specific dates"""
        strategy = {
            "instrument": {"symbol": "RELIANCE"},
            "timeframe": {"interval": "1d"},
            "entry_conditions": [
                {"name": "SMA", "params": {"short": 50, "long": 200}, "operator": "crosses_above"}
            ],
            "exit_conditions": [
                {"name": "SMA", "params": {"short": 50, "long": 200}, "operator": "crosses_below"}
            ],
            "risk_management": {},
        }
        response = make_backtest_request(strategy)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        assert data["success"] is True
        assert data["total_trades"] == 2

        # Verify specific trade dates (2024-01-11 and 2025-07-18)
        entry_dates = [t["entry_time"] for t in data["trades"]]
        assert "2024-01-11" in entry_dates, f"Expected 2024-01-11 in {entry_dates}"
        assert "2025-07-18" in entry_dates, f"Expected 2025-07-18 in {entry_dates}"
        print(f"PASS: SMA golden cross returned 2 trades at expected dates: {entry_dates}")


class TestBacktestEngineMACD:
    """MACD strategy backtest tests"""

    def test_macd_bullish_cross_returns_multiple_trades(self):
        """POST /api/v1/backtest with MACD bullish_cross should return ~27 trades with real dates"""
        strategy = {
            "instrument": {"symbol": "RELIANCE"},
            "timeframe": {"interval": "1d"},
            "entry_conditions": [
                {"name": "MACD", "params": {"fast": 12, "slow": 26, "signal": 9}, "operator": "bullish_cross"}
            ],
            "exit_conditions": [
                {"name": "MACD", "params": {"fast": 12, "slow": 26, "signal": 9}, "operator": "bearish_cross"}
            ],
            "risk_management": {},
        }
        response = make_backtest_request(strategy)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        assert data["success"] is True
        # Should have approximately 27 trades (allow some variance)
        assert data["total_trades"] >= 20, f"Expected ~27 trades, got {data['total_trades']}"
        assert data["total_trades"] <= 35, f"Expected ~27 trades, got {data['total_trades']}"
        print(f"PASS: MACD bullish_cross returned {data['total_trades']} trades")


class TestBacktestEngineBollinger:
    """Bollinger Bands strategy backtest tests"""

    def test_bollinger_bands_touch_strategy(self):
        """POST /api/v1/backtest with Bollinger lower_touch/upper_touch should return trades"""
        strategy = {
            "instrument": {"symbol": "RELIANCE"},
            "timeframe": {"interval": "1d"},
            "entry_conditions": [
                {"name": "Bollinger", "params": {"period": 20, "std_dev": 2}, "operator": "lower_touch"}
            ],
            "exit_conditions": [
                {"name": "Bollinger", "params": {"period": 20, "std_dev": 2}, "operator": "upper_touch"}
            ],
            "risk_management": {},
        }
        response = make_backtest_request(strategy)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        assert data["success"] is True
        # Should have some trades (varies but should have some)
        assert data["total_trades"] > 0, f"Expected trades, got {data['total_trades']}"
        print(f"PASS: Bollinger Bands returned {data['total_trades']} trades")


class TestBacktestEngineErrors:
    """Error handling tests for backtest engine"""

    def test_nonexistent_symbol_returns_error_with_available_symbols(self):
        """POST /api/v1/backtest with non-existent symbol should return success=false with available symbols"""
        strategy = {
            "instrument": {"symbol": "NONEXISTENT"},
            "timeframe": {"interval": "1d"},
            "entry_conditions": [
                {"name": "RSI", "params": {"period": 14}, "operator": "<", "value": 30}
            ],
            "exit_conditions": [],
            "risk_management": {},
        }
        response = make_backtest_request(strategy)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        # Verify error response
        assert data["success"] is False
        assert data["total_trades"] == 0

        # Verify error message lists available symbols
        assert "RELIANCE" in data["message"] or "RELIANCE" in data["disclaimer"]
        assert "No data for NONEXISTENT" in data["message"] or "No data for NONEXISTENT" in data["disclaimer"]
        print(f"PASS: Non-existent symbol returned error with available symbols: {data['message']}")

    def test_missing_entry_conditions_returns_error(self):
        """POST /api/v1/backtest with no entry_conditions should return error"""
        strategy = {
            "instrument": {"symbol": "RELIANCE"},
            "timeframe": {"interval": "1d"},
            "entry_conditions": [],
            "exit_conditions": [],
            "risk_management": {},
        }
        response = make_backtest_request(strategy)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        # Verify error response
        assert data["success"] is False
        assert data["total_trades"] == 0

        # Verify error message about missing conditions
        assert "entry" in data["message"].lower() or "condition" in data["message"].lower()
        print(f"PASS: Missing entry_conditions returned error: {data['message']}")


class TestBacktestTradeSchema:
    """Trade schema validation tests"""

    def test_trade_has_all_required_fields(self):
        """Verify trades have correct schema: entry_time, entry_price, exit_time, exit_price, pnl_points, pnl_percent, holding_candles"""
        strategy = {
            "instrument": {"symbol": "RELIANCE"},
            "timeframe": {"interval": "1d"},
            "entry_conditions": [
                {"name": "RSI", "params": {"period": 14}, "operator": "<", "value": 30}
            ],
            "exit_conditions": [
                {"name": "RSI", "params": {"period": 14}, "operator": ">", "value": 70}
            ],
            "risk_management": {},
        }
        response = make_backtest_request(strategy)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        assert data["success"] is True
        assert len(data["trades"]) > 0

        # Verify all required fields in each trade
        required_fields = [
            "entry_time",
            "entry_price",
            "exit_time",
            "exit_price",
            "pnl_points",
            "pnl_percent",
            "holding_candles",
        ]

        for i, trade in enumerate(data["trades"]):
            for field in required_fields:
                assert field in trade, f"Trade {i} missing field: {field}"

            # Verify data types
            assert isinstance(trade["entry_time"], str)
            assert isinstance(trade["entry_price"], (int, float))
            assert isinstance(trade["exit_time"], str)
            assert isinstance(trade["exit_price"], (int, float))
            assert isinstance(trade["pnl_points"], (int, float))
            assert isinstance(trade["pnl_percent"], (int, float))
            assert isinstance(trade["holding_candles"], int)

        print(f"PASS: All {len(data['trades'])} trades have correct schema")


class TestBacktestNoSimulatedCode:
    """Verify no simulated/fake code exists"""

    def test_trades_have_real_dates(self):
        """Verify trades have real dates within data range (2023-2026), not random or fake"""
        strategy = {
            "instrument": {"symbol": "RELIANCE"},
            "timeframe": {"interval": "1d"},
            "entry_conditions": [
                {"name": "RSI", "params": {"period": 14}, "operator": "<", "value": 35}
            ],
            "exit_conditions": [
                {"name": "RSI", "params": {"period": 14}, "operator": ">", "value": 65}
            ],
            "risk_management": {},
        }
        response = make_backtest_request(strategy)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        assert data["success"] is True
        assert len(data["trades"]) > 0

        for trade in data["trades"]:
            # Entry dates should be in valid range (2023-2026)
            entry_year = int(trade["entry_time"].split("-")[0])
            exit_year = int(trade["exit_time"].split("-")[0])

            assert 2023 <= entry_year <= 2026, f"Entry date {trade['entry_time']} out of range"
            assert 2023 <= exit_year <= 2026, f"Exit date {trade['exit_time']} out of range"

        print(f"PASS: All trades have real dates within 2023-2026 range")

    def test_consistent_results_multiple_runs(self):
        """Verify same strategy returns same results (not random)"""
        strategy = {
            "instrument": {"symbol": "RELIANCE"},
            "timeframe": {"interval": "1d"},
            "entry_conditions": [
                {"name": "SMA", "params": {"short": 50, "long": 200}, "operator": "crosses_above"}
            ],
            "exit_conditions": [
                {"name": "SMA", "params": {"short": 50, "long": 200}, "operator": "crosses_below"}
            ],
            "risk_management": {},
        }

        response1 = make_backtest_request(strategy)
        response2 = make_backtest_request(strategy)

        assert response1.status_code == 200, f"First request failed: {response1.text}"
        assert response2.status_code == 200, f"Second request failed: {response2.text}"

        data1 = response1.json()
        data2 = response2.json()

        # Results should be identical (not random)
        assert data1["total_trades"] == data2["total_trades"], "Trade counts differ between runs"
        assert data1["win_rate"] == data2["win_rate"], "Win rates differ between runs"
        assert data1["pnl"] == data2["pnl"], "PnL differs between runs"

        # Trade dates should match
        for i in range(len(data1["trades"])):
            assert data1["trades"][i]["entry_time"] == data2["trades"][i]["entry_time"], f"Trade {i} entry dates differ"
            assert data1["trades"][i]["exit_time"] == data2["trades"][i]["exit_time"], f"Trade {i} exit dates differ"

        print(f"PASS: Results are consistent across multiple runs (deterministic, not random)")
