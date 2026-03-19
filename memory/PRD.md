# Text2trade - Product Requirements Document

## Overview
Text2trade is a trading strategy builder platform with AI-powered features for parsing, explaining, and analyzing trading strategies. Uses NSE India market data for backtesting.

## Architecture
- **Frontend**: React + TailwindCSS + Shadcn UI + Recharts
- **Backend**: FastAPI (Python)
- **Database**: MongoDB
- **Market Data**: NSE India via `nse` package (no API key, no signup)
- **AI**: OpenAI GPT-5.2 via Emergent LLM Key (temperature=1 only, GPT-5.2 constraint)
- **Auth**: JWT (Access + Refresh tokens) with admin/user roles
- **Indicators**: `ta` library for 15 indicators (RSI, SMA, EMA, MACD, Bollinger, Stochastic, ADX, ATR, Supertrend, VWAP, PivotPoints, PSAR, CCI, WilliamsR, OBV)

## What's Been Implemented

### Session 10 (2026-03-19) — Frontend Dashboard + Paper Trading UI + AI Playground
- **BacktestResultsPanel**: Full backtest results dashboard with interactive equity curve (Recharts AreaChart), 18 performance metrics grid, cost breakdown, collapsible trade log table with exit reason badges
- **AI Strategy Playground**: Split-panel UI — conversational chat on left, real-time strategy JSON preview on right. Uses session endpoints for multi-turn AI conversation. Finalize button saves strategy.
- **Paper Trading UI**: Deploy form with strategy/symbol/lookback selectors, summary stats cards (Total/Running/Completed/Stopped), paper trade cards with P&L, status badges, expand for detailed results
- **Sidebar expanded**: Added AI Playground and Paper Trading to dashboard navigation (5 items total)
- **Bug fix**: Fixed `explainStrategy.js` to handle new nested risk_management schema (stop_loss as `{type, value}` object)
- **Bug fix**: Fixed timeframe case mismatch (1D → 1d) in 4 strategies + added case-insensitive timeframe matching in data service
- **Bug fix**: Fixed GET /api/v1/strategies endpoint (schema was already migrated, confirmed working)
- **Testing**: Backend 10/10, Frontend 12/12 — iteration_14.json

### Session 9 (2026-03-15) — Paper Trading Engine + Expanded Risk Management
- **Paper Trading Engine** (`paper_trading/engine.py`): Forward backtest on cached OHLCV data with simulated live execution
- **Paper Trading Endpoints**: deploy, list, get, pause, stop
- **Expanded RiskManagement Schema**: Trailing stops, time-based exits, daily limits, position sizing
- **Migration Script**: `scripts/migrate_risk_schema.py` for database schema update

### Session 8 (2026-03-15) — Multi-turn NL Parser Rewrite
- 3 response modes (question/strategy/error). AI asks follow-up questions for missing info.
- Conversation flow handler, hallucination detection, normalization, finalization.
- Testing: 12/12 passed, iteration_13.json

### Session 7 (2026-03-15) — Performance Analytics, Costs & Equity Curve
- 18 metrics, Zerodha-like cost model, slippage, equity curve
- Testing: 9/9 passed, iteration_12.json

### Session 6 (2026-03-15) — 15 Indicators Complete
- All 15 indicators with params and operators
- Testing: 12/12 passed, iteration_11.json

### Session 5 (2026-03-15) — Real Backtest Engine
- Replaced fake backtest with real indicator-based engine
- Testing: 9/10 passed, iteration_10.json

### Session 4 (2026-03-15) — AI Session System & Token Limits
- Token budgets, daily limits, conversation sessions
- Testing: 13/13 passed, iteration_9.json

### Session 3 (2026-03-15) — Market Data Pipeline + Admin Roles
### Session 2 (2026-03-05) — API Hardening & Auth Fix
### Session 1 — MVP

## File Structure
```
/app/backend/
├── auth.py
├── server.py
├── ai_sessions.py
├── indicator_registry.py
├── resilience.py, logging_config.py
├── indicators/
│   └── calculator.py          # 15 indicators via ta library
├── backtest/
│   ├── engine.py              # Real backtest engine
│   ├── evaluator.py           # Condition evaluator
│   ├── costs.py               # Brokerage/STT cost calculations
│   └── metrics.py             # Performance metrics
├── paper_trading/
│   └── engine.py              # Paper trading simulation
├── data/
│   └── service.py             # OHLCV data service (case-insensitive timeframe)
├── scripts/
│   ├── create_admin.py, ingest_data.py, refresh_data.py, setup_data_source.py
│   └── migrate_risk_schema.py
└── tests/
    └── test_iteration_14.py

/app/frontend/src/
├── App.js
├── pages/
│   ├── HomePage.js
│   ├── LoginPage.js
│   └── DashboardPage.js       # Main dashboard with 5-item sidebar
├── components/
│   ├── BacktestResultsPanel.js # NEW: Equity curve + metrics + costs + trades
│   ├── StrategyPlayground.js   # NEW: AI chat + JSON preview
│   ├── PaperTradingContent.js  # NEW: Paper trading management
│   ├── StrategyBuilder.js
│   ├── StrategyChat.js
│   ├── NLStrategyInput.js
│   └── ui/                     # Shadcn components
└── utils/
    ├── explainStrategy.js      # FIXED: handles nested risk_management
    └── simulate.js
```

## API Endpoints
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| /api/v1/health | GET | No | Health check |
| /api/v1/auth/register | POST | No | Register |
| /api/v1/auth/login | POST | No | Login |
| /api/v1/strategy | POST | JWT | Create strategy |
| /api/v1/strategies | GET | JWT | List strategies |
| /api/v1/strategy/{id} | GET/PUT/DELETE | JWT | CRUD strategy |
| /api/v1/backtest | POST | No | Real backtest with indicator math |
| /api/v1/parse-strategy | POST | JWT | AI: parse NL to strategy |
| /api/v1/explain | POST | JWT | AI: explain strategy |
| /api/v1/analyze-risk | POST | JWT | AI: risk analysis |
| /api/v1/session/start | POST | JWT | Create session |
| /api/v1/session/{id}/message | POST | JWT | Session message |
| /api/v1/session/{id}/finalize | POST | JWT | Validate + save strategy |
| /api/v1/session/{id}/draft | PUT | JWT | Edit strategy draft |
| /api/v1/session/{id} | GET/DELETE | JWT | Get/delete session |
| /api/v1/ai/usage | GET | JWT | Usage stats |
| /api/v1/paper-trade/deploy | POST | JWT | Deploy paper trade |
| /api/v1/paper-trades | GET | JWT | List paper trades |
| /api/v1/paper-trade/{id} | GET | JWT | Get paper trade |
| /api/v1/paper-trade/{id}/pause | POST | JWT | Pause paper trade |
| /api/v1/paper-trade/{id}/stop | POST | JWT | Stop paper trade |
| /api/v1/admin/* | Various | Admin | Admin endpoints |

## Prioritized Backlog

### P0 - Done
- [x] Frontend backtest results dashboard (equity curve, metrics, costs)
- [x] AI Strategy Playground UI
- [x] Paper Trading management UI

### P1 - Next
- [ ] Refactor server.py into routers (strategies, sessions, paper_trading)
- [ ] Frontend edit/delete buttons on strategy list
- [ ] Strategy Optimizer (multiple parameter combinations)

### P2 - Nice to Have
- [ ] Strategy performance comparison view
- [ ] Token blacklist for logout
- [ ] Password reset flow
- [ ] Strategy sharing between users
- [ ] Caching layer for DB queries
- [ ] Email integration for waitlist

## Test Reports
- `/app/test_reports/iteration_14.json` — Frontend dashboard + Paper Trading UI (Backend 10/10, Frontend 12/12)
- `/app/test_reports/iteration_13.json` — Multi-turn NL parser (12/12 pass)
- `/app/test_reports/iteration_12.json` — Analytics layer (9/9 pass)
- `/app/test_reports/iteration_11.json` — 15 indicators (12/12 pass)
- `/app/test_reports/iteration_10.json` — Real backtest engine (9/10 pass)
- `/app/test_reports/iteration_9.json` — AI sessions (13/13 pass)

## Credentials
- Test user: `testai@example.com` / `Password123!`
- Test user 2: `testai2@example.com` / `Password123!`
- Market data: RELIANCE daily (741 candles)
