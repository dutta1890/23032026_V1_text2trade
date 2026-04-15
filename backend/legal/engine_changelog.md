# Engine Changelog

All changes to the Text2trade backtest engine are logged here. Users can check this changelog to determine if an engine update might affect their historical backtests.

---

## v0.2.0 (2026-04-15)

### Changes
- Added data snapshot hashing (SHA-256) to every backtest result
- Added immutable backtest snapshot storage
- Added engine version tracking in results
- Refactored `engine.py` to extract `_open_position()` and `_check_exit()` helpers
- Refactored `evaluator.py` from monolithic if/elif to dispatch pattern
- Completed lookahead bias audit (all 12 anti-cheat tests pass)

### Benchmarks Affected
None. All 10 benchmark strategies produce identical results before and after changes.

### Impact on Old Backtests
None. This is a refactoring and feature addition. No changes to indicator computation, entry/exit logic, slippage, or cost calculations.

---

## v0.1.0 (2026-03-19)

### Changes
- Initial backtest engine with 15 technical indicators
- Support for: SMA, EMA, RSI, MACD, Bollinger, Stochastic, ADX, ATR, Supertrend, VWAP, Pivot Points, PSAR, CCI, WilliamsR, OBV
- Risk management: stop loss, target profit, trailing stop loss, time-based exit, daily limits
- Transaction costs: Zerodha-like flat brokerage + STT + exchange charges + GST + stamp duty
- Slippage modeling (configurable percentage)
- Equity curve generation
- Comprehensive performance metrics (Sharpe, profit factor, drawdown, etc.)

### Benchmarks Affected
N/A (initial release)

### Impact on Old Backtests
N/A (initial release)
