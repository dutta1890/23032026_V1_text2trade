# Lookahead Bias Audit Report

**Engine Version**: v0.2.0
**Audit Date**: 2026-02-01
**Auditor**: Automated Code Review + Manual Analysis
**Files Audited**:
- `backtest/engine.py` (403 lines)
- `backtest/evaluator.py` (303 lines)
- `indicators/calculator.py` (279 lines)
- `backtest/metrics.py` (130 lines)
- `backtest/costs.py` (135 lines)

---

## Executive Summary

**Verdict: NO LOOKAHEAD BIAS DETECTED**

The backtest engine is clean. All condition evaluations at candle index `N` use only data from indices `<= N`. No future data (index `N+1` or beyond) is accessed during decision-making.

---

## Detailed Analysis

### 1. Main Loop (`engine.py`, Line 318)

```python
for i in range(start_idx, len(df)):
    close = df["close"].iloc[i]      # Current candle ONLY
```

The forward-only loop iterates from `start_idx` (after indicator warm-up) to the last candle. At each step `i`:
- **Entry check** (L339): `evaluate_condition(c, indicators, i, df)` — passes current `i`
- **Exit check** (L342): `_check_exit(position, close, i, ...)` — passes current `i`
- **Filter check** (L336): `evaluate_condition(f, indicators, i, df)` — passes current `i`

**PASS** — No index `i+1` or `len(df)-1` is ever used for decision-making.

### 2. Condition Evaluator (`evaluator.py`)

#### `_safe_value(series, idx)` (Line 19-26)
Returns `series.iloc[idx]` — exact index lookup. Bounds-checked. Never accesses beyond `idx`.

**PASS**

#### `_crosses(series_a, series_b_or_val, idx, direction)` (Line 29-49)
Uses two indices: `idx` (current) and `idx - 1` (previous). This is correct for crossover detection — you need the previous candle to confirm a cross happened.

```python
curr_a = _safe_value(series_a, idx)       # Current
prev_a = _safe_value(series_a, idx - 1)   # Previous (NOT future)
```

**PASS** — Only backward-looking (idx and idx-1).

#### `_compare(val, operator, threshold, series, idx)` (Line 52-68)
Numeric comparisons (`>`, `<`, `>=`, `<=`, `==`). Cross operators delegate to `_crosses()`.

**PASS**

#### Per-Indicator Evaluators (Lines 88-302)
All 13 evaluator functions follow the same pattern:
1. Look up precomputed indicator value at `candle_index`
2. Compare against threshold or another indicator at `candle_index`
3. For crosses, use `candle_index` and `candle_index - 1`

Specifically verified:
- `_eval_moving_average`: Uses `_crosses(short_s, long_s, idx, ...)` — PASS
- `_eval_single_series` (RSI, ATR, CCI, WilliamsR): `_safe_value(ind_data, idx)` — PASS
- `_eval_macd`: `_crosses(macd_line, signal_line, idx, ...)` — PASS
- `_eval_bollinger`: `_safe_value(upper/lower, idx)`, `_safe_value(df["close"], idx)` — PASS
- `_eval_supertrend`: `_safe_value(direction, idx)` and `idx - 1` for signal change — PASS
- `_eval_close_vs_series` (VWAP, PSAR): `_safe_value` at `idx` — PASS
- `_eval_pivot_points`: `_safe_value` at `idx` — PASS
- `_eval_stochastic`: `_safe_value` and `_crosses` at `idx` — PASS
- `_eval_obv`: `_safe_value(ind_data, idx)` — PASS
- `_eval_adx`: `_safe_value(adx_series, idx)` — PASS

### 3. Indicator Precomputation (`engine.py`, Line 48-64)

```python
indicators = _precompute_indicators(df, all_conditions)
```

Indicators are computed on the **full DataFrame** upfront. This is a common pattern and is NOT lookahead bias because:

1. **Rolling-window indicators** (SMA, EMA, RSI, MACD, Bollinger, ATR, CCI, WilliamsR, Stochastic, ADX, OBV): The `ta` library computes these using backward-looking windows only. SMA(20) at candle N uses candles N-19 through N. It cannot "see" candle N+1.

2. **Pivot Points** (`calculator.py`, Line 185-187): Uses `shift(1)` which means pivot at candle N uses HLC from candle N-1 (the previous candle). This is the standard Pivot Point definition.

3. **VWAP** (`calculator.py`, Line 154-178): Uses `cumsum()` from the start of the day/dataset. At candle N, it accumulates data from candle 0 through N.

4. **Supertrend** (`calculator.py`, Line 89-151): The manual loop iterates forward `for i in range(start + 1, len(df))` and only uses `iloc[i]` and `iloc[i-1]`. No future data accessed.

5. **PSAR** (`calculator.py`, Line 213-225): Uses `ta.trend.PSARIndicator` which is a forward-iterating algorithm.

**PASS** — All indicator computations are backward-looking.

### 4. Risk Management Checks (`engine.py`, `_check_exit`)

- **Stop Loss** (L229-232): Compares current `close` against `raw_entry`. No future data.
- **Target Profit** (L235-238): Same pattern. No future data.
- **Trailing SL** (L216-226): Tracks `highest_since_entry` updated with current `close`. Only uses current and historical data.
- **Time Exit** (L210-213): Reads `df["timestamp"].iloc[idx]` — current candle only.
- **Daily Limits** (L333): Counts trades/losses for current day. No lookahead.

**PASS**

### 5. Trade Construction (`engine.py`, `_close_trade`, Line 388-402)

Reads `df["timestamp"].iloc[entry_idx]` and `df["timestamp"].iloc[exit_idx]` for recording. These are just metadata — the DECISION to close was already made at the current candle. No future data involved.

**PASS**

### 6. Edge Cases Verified

| Scenario | Status |
|----------|--------|
| Last candle force-close | CLEAN — marked as `end_of_data` exit reason |
| Indicator warm-up period skipped | CLEAN — `_first_valid_index()` ensures start after NaN values |
| Cross detection at first candle | CLEAN — `_crosses` returns False if `idx < 1` |
| NaN handling in indicators | CLEAN — `_safe_value` returns NaN, conditions return False |

---

## Anti-Cheat Test Coverage

The following automated tests in `tests/test_lookahead_bias.py` validate these findings:

1. **Truncation Consistency**: Trades before cutoff are identical regardless of future data length
2. **Future Data Modification**: Changing future prices doesn't affect historical trades
3. **Perfect Foresight Rejection**: An "oracle" strategy cannot achieve impossible results
4. **Indicator Window Independence**: RSI/SMA values don't change when future data changes
5. **Entry-Before-Exit Ordering**: All trades have chronologically valid entry < exit
6. **Deterministic Results**: Same input always produces same output

---

## Conclusion

The Text2trade backtest engine is **free of lookahead bias**. The architecture enforces temporal correctness through:
1. Forward-only candle iteration
2. Index-bounded condition evaluation (`idx` and `idx-1` only)
3. Backward-looking indicator computation (rolling windows, cumulative sums)
4. No access to future indices in risk management checks

This audit is supported by automated anti-cheat tests that deliberately attempt to exploit future data access and verify it is impossible.
