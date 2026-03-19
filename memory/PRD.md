# Text2trade - Product Requirements Document

## Overview
Text2trade is a trading strategy builder platform with AI-powered features for parsing, explaining, and analyzing trading strategies. Uses NSE India market data for backtesting.

## Architecture
- **Frontend**: React + TailwindCSS + Shadcn UI + Recharts
- **Backend**: FastAPI (Python)
- **Database**: MongoDB
- **Market Data**: NSE India via `nse` package (no API key, no signup)
- **AI**: OpenAI GPT-5.2 via Emergent LLM Key
- **Auth**: JWT (Access + Refresh tokens) with admin/user roles
- **Indicators**: `ta` library for 15 indicators

## What's Been Implemented

### Session 12 (2026-03-19) — Screener + Multi-Backtest + Comparison Engine
- **Screener** (`POST /api/v1/screener/scan`): Scans all symbols against indicator conditions on latest candle. Auth required. Returns matches with indicator values and timing.
- **5 Screener Presets** (`GET /api/v1/screener/presets`): Oversold, Trending Up, VWAP Breakout, Bollinger Squeeze, Momentum Surge. Public endpoint.
- **Multi-Stock Backtest** (`POST /api/v1/backtest/multi`): Same strategy on up to 10 stocks independently. Results sorted by P&L.
- **Strategy Comparison** (`POST /api/v1/backtest/compare`): Up to 5 strategies on one stock, ranked by Sharpe ratio.
- **Admin Screener Analytics** (`GET /api/v1/admin/screener/stats`): Most run presets, most scanned symbols. In-memory tracking.
- **Evaluator Enhancement**: SMA/EMA `>` operator now compares short vs long directly when no threshold provided.
- **Testing**: Backend 20/20 — iteration_16.json

### Session 11 — Strategy Templates + E2E Pipeline
- 12 equity templates seeded (7 categories)
- Template endpoints: public list/detail, user clone, admin CRUD
- Templates UI: category filters, clone button
- Testing: Backend 13/13, Frontend 8/8 — iteration_15.json

### Session 10 — Frontend Dashboard + Paper Trading UI + AI Playground
- BacktestResultsPanel: equity curve chart, metrics, costs, trade log
- AI Strategy Playground: chat + JSON preview
- Paper Trading UI: deploy, status, pause/stop
- Testing: Backend 10/10, Frontend 12/12 — iteration_14.json

### Earlier Sessions
- Sessions 4-9: Real backtest engine, 15 indicators, performance analytics, multi-turn AI, paper trading engine, risk management
- Sessions 1-3: MVP, auth, market data pipeline

## API Endpoints
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| /api/v1/screener/presets | GET | No | List 5 screener presets |
| /api/v1/screener/scan | POST | JWT | Scan symbols against conditions |
| /api/v1/backtest/multi | POST | JWT | Same strategy on up to 10 stocks |
| /api/v1/backtest/compare | POST | JWT | Up to 5 strategies on one stock (ranked by Sharpe) |
| /api/v1/templates | GET | No | List 12 templates |
| /api/v1/template/{id} | GET | No | Template detail |
| /api/v1/template/{id}/clone | POST | JWT | Clone template |
| /api/v1/strategies | GET | JWT | List user strategies |
| /api/v1/backtest | POST | No | Single backtest |
| /api/v1/session/* | Various | JWT | AI conversation |
| /api/v1/paper-trade/* | Various | JWT | Paper trading |
| /api/v1/admin/templates | POST/PUT/DELETE | Admin | Template CRUD |
| /api/v1/admin/screener/stats | GET | Admin | Screener analytics |
| /api/v1/admin/* | Various | Admin | Data, users, analytics |

## File Structure
```
/app/backend/
├── server.py
├── auth.py, ai_sessions.py, indicator_registry.py
├── screener/
│   └── engine.py              # NEW: Screener logic + 5 presets
├── backtest/
│   ├── engine.py, evaluator.py (updated), costs.py, metrics.py
├── indicators/
│   └── calculator.py          # 15 indicators
├── paper_trading/
│   └── engine.py
├── data/
│   └── service.py
└── scripts/
    ├── seed_templates.py, migrate_risk_schema.py, create_admin.py, etc.
```

## Prioritized Backlog
### P1 - Next
- [ ] Refactor server.py into separate FastAPI routers
- [ ] Frontend edit/delete buttons on strategy list
- [ ] Strategy Optimizer (multiple parameter combinations)
- [ ] Frontend for screener, multi-backtest, and comparison

### P2 - Nice to Have
- [ ] Strategy performance comparison view
- [ ] Token blacklist for logout / password reset
- [ ] Strategy sharing between users
- [ ] Email integration for waitlist

## Credentials
- Test user: `testai@example.com` / `Password123!`
- Admin: `admin@example.com` / `Password123!`
- Market data: 7 symbols (RELIANCE, TCS, INFY, HDFCBANK, ICICIBANK, ITC, HINDUNILVR)
