# Text2trade - Product Requirements Document

## Overview
Text2trade is a trading strategy builder platform with AI-powered features for parsing, explaining, and analyzing trading strategies. Uses NSE India market data for backtesting.

## Architecture
- **Frontend**: React + TailwindCSS + Shadcn UI + Recharts
- **Backend**: FastAPI (Python) — modular routers (v1.2.0)
- **Database**: MongoDB
- **Auth**: JWT with role-based routing (admin/user). Tokens in React state/context only.
- **AI**: OpenAI GPT-5.2 via Emergent LLM Key
- **Market Data**: NSE India via `nse` package
- **Indicators**: `ta` library (15 indicators)

## What's Been Implemented

### Session 16 (2026-03-19) — Strategy Optimizer
- **Optimizer Backend** (`optimizer/engine.py`):
  - Auto-detect tunable parameters from any strategy (indicator params, SL/TP values)
  - Grid-based parameter sweep (capped at 500 combinations)
  - Results ranked by Sharpe ratio with baseline comparison
  - Parameter impact analysis (which param moves the needle most)
  - Overfitting warnings (few trades, high Sharpe, over-filtering)
- **Optimizer API** (`routers/optimizer.py`):
  - `POST /optimizer/detect-params`: Auto-detect tunable params
  - `POST /optimizer/run`: Run sweep with ranked results
- **Optimizer UI** (`/optimizer`):
  - Strategy selector dropdown
  - Auto-detected parameter range cards with enable/disable toggle
  - Min/Max/Steps configuration per parameter
  - Combination count validation (max 500)
  - Results: summary cards, Top 10 Sharpe bar chart, parameter impact chart, ranked results table with baseline row, "Apply & Edit" CTA when improvement found
- **Integration**: "Optimize" button on Strategy Detail page, "Optimizer" in sidebar nav
- **Testing**: Backend 9/9, Frontend 10/10 — iteration_20.json

### Session 15 (2026-03-19) — Backend Refactoring + UI Polish
- Split `server.py` (~2046 lines) into modular routers (7 files + database.py + models.py)
- Wired loading skeletons into pages
- Testing: Backend 20/20, Frontend 14/14 — iteration_19.json

### Session 14 (2026-03-19) — Frontend Feature Push
- Stock Screener UI, Strategy Detail page, Multi-stock comparison, Strategy comparison
- General UI polish (error boundary, 404, favicon, page titles), Admin polish
- Testing: Frontend 20/20 — iteration_18.json

### Session 13 — Complete Frontend Rebuild
- Auth system (JWT in memory), role-based routing, all user/admin pages
- Testing: Frontend 27/27 — iteration_17.json

### Sessions 10-12 — Backend Features
- Screener + multi-backtest + comparison engine, strategy templates, backtest engine

## Routes
| Route | Auth | Component | Description |
|-------|------|-----------|-------------|
| / | No | HomePage | Landing page |
| /login | No | LoginPage | Sign in |
| /register | No | RegisterPage | Create account |
| /dashboard | User | UserDashboard | Main hub with strategy comparison |
| /build | User | BuilderPage | AI builder + templates |
| /backtest/:id | User | BacktestPage | Backtest results + multi-stock compare |
| /paper-trades | User | PaperTradesPage | Paper trading |
| /templates | User | TemplatesPage | Template gallery |
| /screener | User | ScreenerPage | Stock screener with presets |
| /strategy/:id | User | StrategyDetailPage | Strategy detail with actions |
| /optimizer | User | OptimizerPage | Parameter sweep optimizer |
| /admin/dashboard | Admin | AdminDashboard | System health with data banner |
| /admin/users | Admin | AdminUsers | User management |
| * | No | NotFoundPage | 404 page |

## File Structure
```
/app/backend/
├── server.py (~230 lines - app factory)
├── database.py, models.py
├── auth.py, ai_sessions.py, resilience.py
├── routers/
│   ├── strategies.py, ai.py, backtest_routes.py
│   ├── paper_trading.py, templates.py
│   ├── screener_routes.py, admin.py, optimizer.py
├── optimizer/engine.py (NEW)
├── screener/engine.py, backtest/engine.py
├── indicators/calculator.py, paper_trading/engine.py
└── data/service.py, scripts/

/app/frontend/src/
├── App.js
├── components/ (ErrorBoundary, LoadingSkeleton, MultiStockCompare, StrategyCompare)
├── pages/user/ (UserDashboard, BuilderPage, BacktestPage, PaperTradesPage,
│                TemplatesPage, ScreenerPage, StrategyDetailPage, OptimizerPage)
├── pages/admin/ (AdminDashboard, AdminUsers)
└── pages/ (HomePage, LoginPage, RegisterPage, NotFoundPage)
```

## Prioritized Backlog
### P2 - Nice to Have
- [ ] Token blacklist for logout / password reset
- [ ] Strategy sharing between users
- [ ] Email notifications
- [ ] Watchlist for screener results
- [ ] Strategy Leaderboard / Most Cloned section

## Credentials
- Test user: `testai@example.com` / `Password123!`
- Admin: `admin@example.com` / `Password123!`
- Market data: 7 symbols (RELIANCE, TCS, INFY, HDFCBANK, ICICIBANK, ITC, HINDUNILVR)
