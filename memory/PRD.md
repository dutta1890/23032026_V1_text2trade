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
- **Indicators**: `ta` library for 15 indicators (RSI, SMA, EMA, MACD, Bollinger, Stochastic, ADX, ATR, Supertrend, VWAP, PivotPoints, PSAR, CCI, WilliamsR, OBV)

## What's Been Implemented

### Session 11 (2026-03-19) — Strategy Templates + E2E Pipeline
- **12 Equity Templates** seeded in `strategy_templates` collection:
  - Trend: Golden Cross, Supertrend Follower, EMA Ribbon
  - Mean Reversion: RSI Mean Reversion, Bollinger Bounce, Stochastic Reversal
  - Momentum: MACD Momentum, CCI Breakout
  - Intraday: VWAP Intraday
  - Breakout: Pivot Breakout
  - Volatility: ATR Volatility
  - Combined: Supertrend + RSI
- **Template Endpoints**:
  - `GET /api/v1/templates` — public list (no auth)
  - `GET /api/v1/template/{id}` — public detail
  - `POST /api/v1/template/{id}/clone` — user clones to their strategies (auth)
  - `POST /api/v1/admin/templates` — admin creates (403 for non-admin)
  - `PUT /api/v1/admin/templates/{id}` — admin updates
  - `DELETE /api/v1/admin/templates/{id}` — admin deletes
- **Templates UI**: Template browser with category filter tabs, condition display, symbol picker, clone button
- **AI Template Awareness**: AI prompt now suggests templates for vague user queries
- **E2E Tested**: Clone→Backtest (16 trades), AI conversation→finalize, Gibberish→clarifying question
- **Testing**: Backend 13/13, Frontend 8/8 — iteration_15.json

### Session 10 (2026-03-19) — Frontend Dashboard + Paper Trading UI + AI Playground
- BacktestResultsPanel: equity curve chart, 18 metrics, cost breakdown, trade log
- AI Strategy Playground: chat + real-time JSON preview
- Paper Trading UI: deploy form, status tracking, pause/stop
- Testing: Backend 10/10, Frontend 12/12 — iteration_14.json

### Earlier Sessions
- Session 9: Paper Trading Engine + Expanded Risk Management
- Session 8: Multi-turn NL Parser (12/12 — iteration_13.json)
- Session 7: Performance Analytics, Costs & Equity Curve (9/9 — iteration_12.json)
- Session 6: 15 Indicators Complete (12/12 — iteration_11.json)
- Session 5: Real Backtest Engine (9/10 — iteration_10.json)
- Session 4: AI Session System & Token Limits (13/13 — iteration_9.json)
- Session 3: Market Data Pipeline + Admin Roles
- Session 2: API Hardening & Auth Fix
- Session 1: MVP

## API Endpoints
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| /api/v1/health | GET | No | Health check |
| /api/v1/auth/register | POST | No | Register |
| /api/v1/auth/login | POST | No | Login |
| /api/v1/templates | GET | No | List all 12 templates (public) |
| /api/v1/template/{id} | GET | No | Template detail (public) |
| /api/v1/template/{id}/clone | POST | JWT | Clone template to user's strategies |
| /api/v1/strategy | POST | JWT | Create strategy |
| /api/v1/strategies | GET | JWT | List strategies |
| /api/v1/strategy/{id} | GET/PUT/DELETE | JWT | CRUD strategy |
| /api/v1/backtest | POST | No | Real backtest with indicators |
| /api/v1/session/start | POST | JWT | Start AI session |
| /api/v1/session/{id}/message | POST | JWT | Send message |
| /api/v1/session/{id}/finalize | POST | JWT | Finalize strategy |
| /api/v1/paper-trade/deploy | POST | JWT | Deploy paper trade |
| /api/v1/paper-trades | GET | JWT | List paper trades |
| /api/v1/paper-trade/{id} | GET | JWT | Get paper trade |
| /api/v1/paper-trade/{id}/pause | POST | JWT | Pause paper trade |
| /api/v1/paper-trade/{id}/stop | POST | JWT | Stop paper trade |
| /api/v1/admin/templates | POST | Admin | Create template |
| /api/v1/admin/templates/{id} | PUT | Admin | Update template |
| /api/v1/admin/templates/{id} | DELETE | Admin | Delete template |
| /api/v1/admin/data/* | Various | Admin | Data management |
| /api/v1/admin/users | GET | Admin | List users |
| /api/v1/admin/analytics | GET | Admin | Analytics |

## DB Collections
- `users` — JWT auth with admin/user roles
- `strategies` — User strategies (created or cloned)
- `strategy_templates` — 12 pre-built templates (admin-managed, user-clonable)
- `market_data` — OHLCV candles from NSE
- `conversation_sessions` — AI multi-turn sessions
- `paper_trades` — Paper trading simulations

## Prioritized Backlog

### P1 - Next
- [ ] Refactor server.py into routers (strategies, sessions, paper_trading, templates)
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
- `/app/test_reports/iteration_15.json` — Templates + E2E (Backend 13/13, Frontend 8/8)
- `/app/test_reports/iteration_14.json` — Dashboard + Paper Trading UI (Backend 10/10, Frontend 12/12)
- Earlier: iteration_9 through iteration_13

## Credentials
- Test user: `testai@example.com` / `Password123!`
- Admin: `admin@example.com` / `Password123!`
- Market data: RELIANCE daily (741 candles)
