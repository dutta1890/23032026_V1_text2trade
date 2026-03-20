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

### Session 15 (2026-03-19) — Backend Refactoring + UI Polish
- **Backend Refactoring**: Split `server.py` (~2046 lines) into modular architecture:
  - `database.py`: Shared MongoDB connections, collections, in-memory state
  - `models.py`: Centralized Pydantic models
  - `routers/strategies.py`: Strategy CRUD
  - `routers/ai.py`: AI parser, risk analyzer, explainer, session management
  - `routers/backtest_routes.py`: Backtest + multi-stock + comparison
  - `routers/paper_trading.py`: Paper trading endpoints
  - `routers/templates.py`: Template endpoints
  - `routers/screener_routes.py`: Screener scan + presets
  - `routers/admin.py`: Admin-only endpoints
  - Slim `server.py` (~230 lines): App factory, middleware, auth, general routes
- **Loading Skeletons**: Wired `PageSkeleton` component into Dashboard, Templates, Paper Trades, Strategy Detail pages (replacing plain Loader2 spinners)
- **Testing**: Backend 20/20, Frontend 14/14 — iteration_19.json

### Session 14 (2026-03-19) — Frontend Feature Push
- **Stock Screener UI** (`/screener`): 5 preset cards, custom scan builder, results table with Build Strategy button
- **Strategy Detail Page** (`/strategy/:id`): Human-readable conditions/risk, action buttons (Run Backtest, Edit, Delete)
- **Multi-Stock Comparison**: Compare strategy across 10 stocks on backtest page
- **Strategy Comparison**: Select 2-5 strategies on dashboard via checkboxes for side-by-side comparison
- **General UI Polish**: Error boundary, 404 page, SVG favicon, page titles, loading skeletons
- **Admin Polish**: Green/red data health banner, refresh button with loading+toast
- **Testing**: Frontend 20/20 — iteration_18.json

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
| /admin/dashboard | Admin | AdminDashboard | System health with data banner |
| /admin/users | Admin | AdminUsers | User management |
| * | No | NotFoundPage | 404 page |

## File Structure
```
/app/backend/
├── server.py (~230 lines - app factory)
├── database.py (shared DB, collections, state)
├── models.py (Pydantic models)
├── auth.py, ai_sessions.py, resilience.py
├── routers/
│   ├── strategies.py, ai.py, backtest_routes.py
│   ├── paper_trading.py, templates.py
│   ├── screener_routes.py, admin.py
├── screener/engine.py
├── backtest/engine.py, evaluator.py, costs.py, metrics.py
├── indicators/calculator.py
├── paper_trading/engine.py
├── data/service.py
└── scripts/seed_templates.py, etc.

/app/frontend/src/
├── App.js (ErrorBoundary, all routes)
├── context/AuthContext.js
├── hooks/useApi.js
├── components/
│   ├── ErrorBoundary.js, LoadingSkeleton.js
│   ├── MultiStockCompare.js, StrategyCompare.js
│   ├── layout/UserLayout.js, AdminLayout.js
│   └── ui/ (Shadcn)
├── pages/
│   ├── NotFoundPage.js
│   ├── user/ScreenerPage.js, StrategyDetailPage.js, etc.
│   └── admin/AdminDashboard.js, AdminUsers.js
```

## Prioritized Backlog
### P1 - Next
- [ ] Strategy Optimizer (parameter sweeps)

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
