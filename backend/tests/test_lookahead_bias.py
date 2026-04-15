"""Anti-cheat / Lookahead Bias Tests for the Backtest Engine.

These tests deliberately attempt to exploit future data access
and verify the engine rejects all such attempts.

Run: cd /app/backend && python -m pytest tests/test_lookahead_bias.py -v
"""

import math
import copy
import numpy as np
import pandas as pd
import pytest
from unittest.mock import patch
from datetime import datetime, timezone, timedelta

# Engine imports
from backtest.engine import run_backtest, _precompute_indicators, _first_valid_index
from backtest.evaluator import evaluate_condition, _safe_value, _crosses
from indicators.calculator import compute_indicator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_synthetic_ohlcv(n=500, base_price=1000.0, seed=42):
    """Create synthetic OHLCV data with a random-walk price series."""
    rng = np.random.RandomState(seed)
    dates = pd.date_range("2023-01-02", periods=n, freq="B")  # business days
    returns = rng.normal(0.0003, 0.015, n)
    close = base_price * np.cumprod(1 + returns)
    daily_range = close * rng.uniform(0.005, 0.02, n)
    high = close + daily_range / 2
    low = close - daily_range / 2
    open_ = close + rng.uniform(-0.3, 0.3, n) * daily_range
    volume = rng.randint(500_000, 5_000_000, n).astype(float)

    return pd.DataFrame({
        "timestamp": dates,
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    })


def _run_with_mock_data(strategy_json, df, symbol="SYNTH"):
    """Run backtest with mocked OHLCV data."""
    with patch("backtest.engine.get_ohlcv", return_value=df.copy()):
        return run_backtest(
            strategy_json, symbol, "1d",
            start_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2025, 12, 31, tzinfo=timezone.utc),
            slippage_pct=0.0,
        )


# Simple RSI strategy for reuse
RSI_STRATEGY = {
    "entry_conditions": [
        {"name": "RSI", "params": {"period": 14}, "operator": "<", "value": 35}
    ],
    "exit_conditions": [
        {"name": "RSI", "params": {"period": 14}, "operator": ">", "value": 65}
    ],
    "risk_management": {},
}

SMA_STRATEGY = {
    "entry_conditions": [
        {"name": "SMA", "params": {"short": 20, "long": 50}, "operator": "crosses_above"}
    ],
    "exit_conditions": [
        {"name": "SMA", "params": {"short": 20, "long": 50}, "operator": "crosses_below"}
    ],
    "risk_management": {},
}


# ===========================================================================
# TEST 1: Truncation Consistency
# ===========================================================================

class TestTruncationConsistency:
    """Trades before a cutoff point must be identical regardless of future data length.

    If the engine peeks ahead, extending the dataset would change historical trades.
    """

    def test_trades_before_cutoff_match_across_dataset_lengths(self):
        df_full = _make_synthetic_ohlcv(500, seed=100)
        df_short = df_full.iloc[:300].copy().reset_index(drop=True)

        result_short = _run_with_mock_data(RSI_STRATEGY, df_short)
        result_full = _run_with_mock_data(RSI_STRATEGY, df_full)

        assert result_short["success"] and result_full["success"]

        # Get trades from short run that completed naturally (not force-closed)
        short_trades = [t for t in result_short["trades"] if t["exit_reason"] != "end_of_data"]

        if not short_trades:
            pytest.skip("No completed trades in short dataset — try different seed")

        # These same trades must appear identically in the full run
        full_trades = result_full["trades"]
        for i, st in enumerate(short_trades):
            assert i < len(full_trades), f"Full run has fewer trades than short run at index {i}"
            ft = full_trades[i]
            assert st["entry_time"] == ft["entry_time"], (
                f"Trade {i} entry differs: short={st['entry_time']} full={ft['entry_time']}"
            )
            assert st["exit_time"] == ft["exit_time"], (
                f"Trade {i} exit differs: short={st['exit_time']} full={ft['exit_time']}"
            )
            assert abs(st["entry_price"] - ft["entry_price"]) < 0.01
            assert abs(st["exit_price"] - ft["exit_price"]) < 0.01

    def test_sma_truncation_consistency(self):
        """Same test with SMA crossover strategy."""
        df_full = _make_synthetic_ohlcv(600, seed=200)
        df_short = df_full.iloc[:400].copy().reset_index(drop=True)

        result_short = _run_with_mock_data(SMA_STRATEGY, df_short)
        result_full = _run_with_mock_data(SMA_STRATEGY, df_full)

        assert result_short["success"] and result_full["success"]

        short_trades = [t for t in result_short["trades"] if t["exit_reason"] != "end_of_data"]
        if not short_trades:
            pytest.skip("No completed SMA trades in short dataset")

        full_trades = result_full["trades"]
        for i, st in enumerate(short_trades):
            assert i < len(full_trades)
            ft = full_trades[i]
            assert st["entry_time"] == ft["entry_time"]
            assert st["exit_time"] == ft["exit_time"]


# ===========================================================================
# TEST 2: Future Data Modification
# ===========================================================================

class TestFutureDataModification:
    """Modifying prices AFTER a certain point must not change earlier trades.

    If the engine accesses future candles during evaluation, corrupting future
    data would alter historical trade signals.
    """

    def test_corrupting_future_prices_does_not_change_history(self):
        df_original = _make_synthetic_ohlcv(500, seed=300)
        cutoff = 250

        # Corrupt future: set all prices after cutoff to extreme values
        df_corrupted = df_original.copy()
        df_corrupted.loc[cutoff:, "close"] = 1.0  # crash to Rs 1
        df_corrupted.loc[cutoff:, "high"] = 1.5
        df_corrupted.loc[cutoff:, "low"] = 0.5
        df_corrupted.loc[cutoff:, "open"] = 1.0

        result_orig = _run_with_mock_data(RSI_STRATEGY, df_original)
        result_corrupt = _run_with_mock_data(RSI_STRATEGY, df_corrupted)

        assert result_orig["success"] and result_corrupt["success"]

        # Find trades that complete before the cutoff date
        cutoff_date = str(df_original["timestamp"].iloc[cutoff])[:10]

        orig_early = [t for t in result_orig["trades"]
                      if t["exit_time"] < cutoff_date and t["exit_reason"] != "end_of_data"]
        corrupt_early = [t for t in result_corrupt["trades"]
                         if t["exit_time"] < cutoff_date and t["exit_reason"] != "end_of_data"]

        assert len(orig_early) == len(corrupt_early), (
            f"Different number of pre-cutoff trades: orig={len(orig_early)} corrupt={len(corrupt_early)}"
        )

        for i, (o, c) in enumerate(zip(orig_early, corrupt_early)):
            assert o["entry_time"] == c["entry_time"], f"Trade {i} entry time differs"
            assert o["exit_time"] == c["exit_time"], f"Trade {i} exit time differs"
            assert abs(o["pnl_percent"] - c["pnl_percent"]) < 0.01, (
                f"Trade {i} PnL differs: {o['pnl_percent']} vs {c['pnl_percent']}"
            )


# ===========================================================================
# TEST 3: Perfect Foresight Rejection
# ===========================================================================

class TestPerfectForesightRejection:
    """A strategy that SHOULD be impossible without future knowledge
    must not achieve a 100% win rate.

    We create data with an alternating up/down pattern and use RSI
    thresholds that would only predict perfectly if future data was visible.
    """

    def test_no_strategy_achieves_perfect_foresight(self):
        """Use wider RSI thresholds — engine should still produce losing trades."""
        # Wider thresholds to guarantee trades on synthetic data
        wide_rsi = {
            "entry_conditions": [
                {"name": "RSI", "params": {"period": 14}, "operator": "<", "value": 45}
            ],
            "exit_conditions": [
                {"name": "RSI", "params": {"period": 14}, "operator": ">", "value": 55}
            ],
            "risk_management": {},
        }
        df = _make_synthetic_ohlcv(500, seed=400)
        result = _run_with_mock_data(wide_rsi, df)

        assert result["success"]
        trades = result["trades"]
        if len(trades) < 5:
            pytest.skip("Too few trades to validate")

        # A real strategy on random data should NOT have 100% win rate
        # (statistically near-impossible on random walk with 5+ trades)
        wins = sum(1 for t in trades if t["pnl_percent"] > 0)
        win_rate = wins / len(trades) * 100

        assert win_rate < 100.0, (
            f"Suspicious 100% win rate with {len(trades)} trades — possible lookahead"
        )
        # Also verify it's not 0% (engine is functional)
        assert win_rate > 0.0, "0% win rate on random data — engine may be broken"

    def test_oracle_entry_exit_not_possible(self):
        """Create data with random walk. Even with wide RSI thresholds,
        the engine should not achieve near-perfect results because
        indicators are lagging and cannot predict future movements.
        """
        # Use wider thresholds that produce many trades
        wide_rsi = {
            "entry_conditions": [
                {"name": "RSI", "params": {"period": 7}, "operator": "<", "value": 45}
            ],
            "exit_conditions": [
                {"name": "RSI", "params": {"period": 7}, "operator": ">", "value": 55}
            ],
            "risk_management": {},
        }
        df = _make_synthetic_ohlcv(500, seed=555)
        result = _run_with_mock_data(wide_rsi, df)
        assert result["success"]

        trades = result["trades"]
        if len(trades) < 3:
            pytest.skip("Too few trades on synthetic data")

        wins = sum(1 for t in trades if t["pnl_percent"] > 0)
        win_rate = wins / len(trades) * 100

        # With alternating data and RSI, perfect prediction is impossible
        # Allow up to 95% since patterns could occasionally align
        assert win_rate < 95.0, (
            f"Suspiciously high {win_rate}% win rate on alternating data"
        )


# ===========================================================================
# TEST 4: Indicator Window Independence
# ===========================================================================

class TestIndicatorWindowIndependence:
    """Indicator values at candle N must not change when data beyond N is modified.

    This directly tests that the `ta` library indicators are backward-looking.
    """

    def test_rsi_values_unchanged_by_future_data(self):
        df_base = _make_synthetic_ohlcv(300, seed=500)
        cutoff = 150

        df_modified = df_base.copy()
        df_modified.loc[cutoff:, "close"] = 50.0  # extreme change after cutoff

        rsi_base = compute_indicator(df_base, "RSI", {"period": 14})
        rsi_modified = compute_indicator(df_modified, "RSI", {"period": 14})

        # RSI values BEFORE cutoff should be identical
        for i in range(14, cutoff):
            v1 = rsi_base.iloc[i]
            v2 = rsi_modified.iloc[i]
            if math.isnan(v1) and math.isnan(v2):
                continue
            assert abs(v1 - v2) < 1e-10, (
                f"RSI at index {i} changed: {v1} vs {v2}"
            )

    def test_sma_values_unchanged_by_future_data(self):
        df_base = _make_synthetic_ohlcv(300, seed=600)
        cutoff = 150

        df_modified = df_base.copy()
        df_modified.loc[cutoff:, "close"] = 50.0

        sma_base = compute_indicator(df_base, "SMA", {"period": 20})
        sma_modified = compute_indicator(df_modified, "SMA", {"period": 20})

        for i in range(20, cutoff):
            v1 = sma_base.iloc[i]
            v2 = sma_modified.iloc[i]
            if math.isnan(v1) and math.isnan(v2):
                continue
            assert abs(v1 - v2) < 1e-10, (
                f"SMA at index {i} changed: {v1} vs {v2}"
            )

    def test_macd_values_unchanged_by_future_data(self):
        df_base = _make_synthetic_ohlcv(300, seed=700)
        cutoff = 150

        df_modified = df_base.copy()
        df_modified.loc[cutoff:, "close"] = 50.0

        macd_base = compute_indicator(df_base, "MACD", {"fast": 12, "slow": 26, "signal": 9})
        macd_modified = compute_indicator(df_modified, "MACD", {"fast": 12, "slow": 26, "signal": 9})

        for i in range(35, cutoff):
            for key in ("macd", "signal"):
                v1 = macd_base[key].iloc[i]
                v2 = macd_modified[key].iloc[i]
                if math.isnan(v1) and math.isnan(v2):
                    continue
                assert abs(v1 - v2) < 1e-10, (
                    f"MACD.{key} at index {i} changed: {v1} vs {v2}"
                )


# ===========================================================================
# TEST 5: Entry-Before-Exit Ordering
# ===========================================================================

class TestEntryExitOrdering:
    """All trades must have entry_time <= exit_time and positive holding candles.

    A time-traveling engine might produce trades where the exit precedes the entry.
    """

    def test_all_trades_have_valid_chronology(self):
        df = _make_synthetic_ohlcv(500, seed=800)
        result = _run_with_mock_data(RSI_STRATEGY, df)

        assert result["success"]
        for i, trade in enumerate(result["trades"]):
            assert trade["entry_time"] <= trade["exit_time"], (
                f"Trade {i}: entry {trade['entry_time']} > exit {trade['exit_time']}"
            )
            assert trade["holding_candles"] >= 0, (
                f"Trade {i}: negative holding candles {trade['holding_candles']}"
            )

    def test_sma_trades_have_valid_chronology(self):
        df = _make_synthetic_ohlcv(500, seed=900)
        result = _run_with_mock_data(SMA_STRATEGY, df)

        assert result["success"]
        for i, trade in enumerate(result["trades"]):
            assert trade["entry_time"] <= trade["exit_time"]
            assert trade["holding_candles"] >= 0


# ===========================================================================
# TEST 6: Deterministic Results
# ===========================================================================

class TestDeterministicResults:
    """Same input must always produce identical output.

    Non-determinism could indicate random data injection or race conditions.
    """

    def test_identical_runs_produce_identical_trades(self):
        df = _make_synthetic_ohlcv(400, seed=1000)

        result1 = _run_with_mock_data(RSI_STRATEGY, df)
        result2 = _run_with_mock_data(RSI_STRATEGY, df)

        assert result1["success"] and result2["success"]
        assert len(result1["trades"]) == len(result2["trades"]), (
            f"Trade count differs: {len(result1['trades'])} vs {len(result2['trades'])}"
        )

        for i, (t1, t2) in enumerate(zip(result1["trades"], result2["trades"])):
            assert t1["entry_time"] == t2["entry_time"], f"Trade {i} entry time differs"
            assert t1["exit_time"] == t2["exit_time"], f"Trade {i} exit time differs"
            assert t1["entry_price"] == t2["entry_price"], f"Trade {i} entry price differs"
            assert t1["exit_price"] == t2["exit_price"], f"Trade {i} exit price differs"
            assert t1["pnl_percent"] == t2["pnl_percent"], f"Trade {i} PnL differs"

    def test_metrics_are_deterministic(self):
        df = _make_synthetic_ohlcv(400, seed=1100)

        result1 = _run_with_mock_data(RSI_STRATEGY, df)
        result2 = _run_with_mock_data(RSI_STRATEGY, df)

        m1 = result1["metrics"]
        m2 = result2["metrics"]
        for key in ("total_trades", "win_rate", "total_pnl_pct", "max_drawdown_pct"):
            assert m1[key] == m2[key], f"Metric '{key}' differs: {m1[key]} vs {m2[key]}"
