# Text2trade - Product Requirements Document

## Overview
Text2trade is a trading strategy builder platform with AI-powered features for parsing, explaining, and analyzing trading strategies. Uses NSE India market data for backtesting.

## Architecture
- **Frontend**: React + TailwindCSS + Shadcn UI
- **Backend**: FastAPI (Python)
- **Database**: MongoDB
- **Market Data**: NSE India via `nse` package (no API key, no signup)
- **AI**: OpenAI GPT-5.2 via Emergent LLM Key (temperature=1 only, GPT-5.2 constraint)
- **Auth**: JWT (Access + Refresh tokens) with admin/user roles
- **Indicators**: `ta` library for RSI, SMA, EMA, MACD, Bollinger Bands

## What's Been Implemented

### Session 8 (2026-03-15) — Multi-turn NL Parser Rewrite
- **New system prompt**: 3 response modes (question/strategy/error). AI asks follow-up questions for missing info. Never guesses values. F&O redirect. 15 supported indicators + 22 instruments.
- **Conversation flow handler**: Parses AI JSON response, validates strategy mode against registry + Pydantic, silent retry on validation failure (1 extra credit).
- **Hallucination detection**: Extracts indicator names from every strategy response, rejects + retries if unsupported indicator found.
- **Normalization**: `_normalize_ai_strategy()` transforms free-form AI JSON to strict schema (handles `indicator`→`name`, nested risk_management objects, etc.)
- **Strategy finalization**: `POST /session/{id}/finalize` validates draft, normalizes, saves to strategies collection. `PUT /session/{id}/draft` for manual editing before finalize.
- **Testing**: 12/12 passed, iteration_13.json

### Session 7 (2026-03-15) — Performance Analytics, Costs & Equity Curve
- **Metrics** (`backtest/metrics.py`): 18 fields — total_trades, win_rate, total_pnl_pct/abs, max_drawdown_pct/duration, sharpe_ratio (annualized, 6% risk-free), profit_factor, avg_pnl, avg_win/loss, max_consecutive_wins/losses, avg_holding, best/worst trade
- **Costs** (`backtest/costs.py`): Zerodha-like model — Rs 20/order brokerage, 0.1% STT sell-side delivery, 0.00345% exchange charges, GST, stamp duty, SEBI charges
- **Slippage**: Configurable per-request (default 0.05%). Entry goes up, exit goes down.
- **Equity Curve**: [{timestamp, equity, drawdown_pct}] starting at initial_capital
- **Updated API**: BacktestRequest accepts slippage_pct, initial_capital, brokerage_per_order. Response now includes metrics, costs, equity_curve, warnings
- **Testing**: 9/9 passed, iteration_12.json

### Session 6 (2026-03-15) — 15 Indicators Complete
- **Completed existing 3**: Stochastic (k, d), ADX (adx, +DI, -DI), ATR
- **Added 7 new**: Supertrend (buy_signal/sell_signal), VWAP (daily-reset for intraday), Pivot Points (standard/fibonacci/woodie), PSAR, CCI, Williams %R, OBV
- **Updated registry**: 15 indicators with params and operators
- **Updated evaluator**: New operators buy_signal, sell_signal, above_r1, below_s1, above_r2, below_s2
- **Updated AI prompts**: All 15 indicators listed in parser, explainer, risk analyzer, session prompts
- **Testing**: 12/12 passed, iteration_11.json

### Session 5 (2026-03-15) — Real Backtest Engine
- **Killed fake backtest**: Removed ALL simulated/random backtest code from server.py
- **Indicator Calculator** (`indicators/calculator.py`): 5 core indicators using `ta` library:
  - `calculate_rsi(df, period=14)` -> Series
  - `calculate_sma(df, period=20)` -> Series
  - `calculate_ema(df, period=20)` -> Series
  - `calculate_macd(df, fast=12, slow=26, signal=9)` -> {macd, signal, histogram}
  - `calculate_bollinger(df, period=20, std_dev=2)` -> {upper, middle, lower}
- **Condition Evaluator** (`backtest/evaluator.py`): Supports >, <, >=, <=, cross_above, cross_below, bullish_cross, bearish_cross, upper_touch, lower_touch
- **Backtest Engine** (`backtest/engine.py`): Fetches OHLCV from MongoDB, computes indicators, iterates candles, evaluates entry/exit conditions, collects trades
- **Trade schema**: entry_time, entry_price, exit_time, exit_price, pnl_points, pnl_percent, holding_candles
- **Testing**: 9/10 tests passed (1 rate-limit flake), iteration_10.json

### Session 4 (2026-03-15) — AI Session System & Token Limits
- AI Token Budgets: nl_parser=800, explainer=400, risk_analyzer=400, session_chat=600 max_tokens
- Daily Usage Limits: nl_parser=20/day, explainer=10/day, risk_analyzer=10/day, session_chat=30/day
- Conversation Sessions: MongoDB with TTL 24h, CRUD endpoints, context window (6 msgs, 500 token budget)
- Testing: 13/13 passed, iteration_9.json

### Session 3 (2026-03-15) — Market Data Pipeline + Admin Roles
- Admin/User Roles, CLI scripts, NSE India data pipeline, admin endpoints
- Testing: 100% pass, iteration_8.json

### Session 2 (2026-03-05) — API Hardening & Auth Fix
- Rate limiting, input sanitization, circuit breakers, structured logging

### Session 1 — MVP
- Full scaffold, JWT auth, strategy CRUD, AI features, indicators, landing page

## File Structure
```
/app/backend/
├── auth.py
├── server.py
├── ai_sessions.py
├── indicator_registry.py
├── resilience.py, logging_config.py
├── indicators/
│   ├── __init__.py
│   └── calculator.py          # 5 indicators via ta library
├── backtest/
│   ├── __init__.py
│   ├── engine.py              # Real backtest engine
│   └── evaluator.py           # Condition evaluator
├── data/
│   ├── service.py
│   └── sources/
├── scripts/
│   ├── create_admin.py, ingest_data.py, refresh_data.py, setup_data_source.py
└── tests/
    ├── test_ai_sessions.py
    └── test_backtest_engine.py
```

## API Endpoints
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| /api/v1/health | GET | No | Health check |
| /api/v1/auth/register | POST | No | Register |
| /api/v1/auth/login | POST | No | Login |
| /api/v1/strategy | POST | JWT | Create strategy |
| /api/v1/strategies | GET | JWT | List strategies |
| /api/v1/backtest | POST | No | **Real** backtest with indicator math |
| /api/v1/parse-strategy | POST | JWT | AI: parse NL to strategy |
| /api/v1/explain | POST | JWT | AI: explain strategy |
| /api/v1/analyze-risk | POST | JWT | AI: risk analysis |
| /api/v1/session/start | POST | JWT | Create session |
| /api/v1/session/{id}/message | POST | JWT | Session message |
| /api/v1/session/{id}/finalize | POST | JWT | Validate + save strategy draft |
| /api/v1/session/{id}/draft | PUT | JWT | Manually edit strategy draft |
| /api/v1/session/{id} | GET/DELETE | JWT | Get/delete session |
| /api/v1/ai/usage | GET | JWT | Usage stats |
| /api/v1/admin/* | Various | Admin | Admin endpoints |

## Prioritized Backlog

### P1 - Next
- [ ] Frontend edit/delete buttons on strategy list
- [ ] Analytics dashboard UI
- [ ] Refactor server.py into routers

### P2 - Nice to Have
- [ ] Token blacklist for logout
- [ ] Password reset flow
- [ ] Strategy sharing between users
- [ ] Caching layer for DB queries
- [ ] Email integration for waitlist

## Test Reports
- `/app/test_reports/iteration_13.json` — Multi-turn NL parser (12/12 pass)
- `/app/test_reports/iteration_12.json` — Analytics layer (9/9 pass)
- `/app/test_reports/iteration_11.json` — 15 indicators (12/12 pass)
- `/app/test_reports/iteration_10.json` — Real backtest engine (9/10 pass)
- `/app/test_reports/iteration_9.json` — AI sessions (13/13 pass)
- `/app/test_reports/iteration_8.json` — Data pipeline (100% pass)

## Credentials
- Test user: `testai@example.com` / `Password123!`
- Test user 2: `testai2@example.com` / `Password123!`
- Market data: RELIANCE daily (741 candles)
