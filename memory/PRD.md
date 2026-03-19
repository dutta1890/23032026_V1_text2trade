# Text2trade - Product Requirements Document

## Overview
Text2trade is a trading strategy builder platform with AI-powered features for parsing, explaining, and analyzing trading strategies. Uses NSE India market data for backtesting.

## Architecture
- **Frontend**: React + TailwindCSS + Shadcn UI + Recharts
- **Backend**: FastAPI (Python)
- **Database**: MongoDB
- **Auth**: JWT with role-based routing (admin/user). Tokens in React state/context only.
- **AI**: OpenAI GPT-5.2 via Emergent LLM Key
- **Market Data**: NSE India via `nse` package
- **Indicators**: `ta` library (15 indicators)

## What's Been Implemented

### Session 14 (2026-03-19) — Frontend Feature Push (Screener, Strategy Detail, Comparison, Polish)
- **Stock Screener UI** (`/screener`): 5 preset cards (Oversold, Trending Up, VWAP Breakout, Bollinger Squeeze, Momentum Surge), custom scan builder with indicator/operator/value fields, results table with Build Strategy button
- **Strategy Detail Page** (`/strategy/:id`): Human-readable entry/exit conditions, risk management display (SL, TP, TSL, time exit), action buttons (Run Backtest, Edit, Delete, Paper Trade), raw JSON preview
- **Multi-Stock Comparison**: On backtest page, compare strategy across up to 10 stocks with bar chart and metrics table
- **Strategy Comparison**: On dashboard, select 2-5 strategies via checkboxes, compare side-by-side on any symbol (ranked by Sharpe ratio)
- **General UI Polish**: Error boundary wrapper, 404 page with navigation, SVG favicon, page titles on all pages, loading skeletons component
- **Admin Polish**: Green/red data health banner with animated indicator dot, Refresh Data button with loading state and toast notifications
- **Bug Fix**: Added missing recharts imports to PaperTradesPage
- **Cleanup**: Removed unused DashboardPage.js
- **Testing**: Frontend 20/20 — iteration_18.json

### Session 13 (2026-03-19) — Complete Frontend Rebuild
- **Auth System**: AuthContext with useAuth(), ProtectedRoute, AdminRoute guards
  - JWT decode in memory, NO localStorage
  - Role-based routing: admin→/admin/dashboard, user→/dashboard
  - /register page with email/password/confirm
- **User Dashboard** (/dashboard): Quick Start (Build, Templates, Scan), Stats cards, Strategy list with checkboxes, Paper Trades summary
- **Strategy Builder** (/build): AI chat + template selector tabs, risk controls editor, Finalize→Backtest→Deploy buttons
- **Backtest Results** (/backtest/{id}): Metrics cards, equity curve, cost breakdown, sortable trade table, Paper Trade button, Multi-stock compare
- **Paper Trades** (/paper-trades): Deploy form, status badges, expand for equity curve + trade log
- **Template Gallery** (/templates): 12 cards with category badges+filters, symbol picker, clone→open flow
- **Admin Dashboard** (/admin/dashboard): Data pipeline health banner, Platform stats, Screener analytics, Refresh Data button with toast
- **Admin Users** (/admin/users): User table with search, strategy count, AI calls
- **Layouts**: UserLayout + AdminLayout with responsive sidebars, mobile menu (375px+)
- **Testing**: Frontend 27/27 — iteration_17.json, Frontend 20/20 — iteration_18.json

### Session 12 — Screener + Multi-Backtest + Comparison Engine
- Screener with 5 presets, Multi-stock backtest (up to 10), Strategy comparison (ranked by Sharpe)
- Testing: Backend 20/20 — iteration_16.json

### Session 11 — Strategy Templates + E2E Pipeline
- 12 equity templates, Template CRUD endpoints, clone flow
- Testing: Backend 13/13, Frontend 8/8 — iteration_15.json

### Session 10 — Frontend Dashboard (first version)
- BacktestResultsPanel, AI Playground, Paper Trading UI
- Testing: Backend 10/10, Frontend 12/12 — iteration_14.json

### Earlier Sessions (4-9)
- Real backtest engine, 15 indicators, performance analytics, multi-turn AI, paper trading engine, risk management

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
/app/frontend/src/
├── App.js (ErrorBoundary, all routes including /screener, /strategy/:id, 404)
├── context/AuthContext.js
├── hooks/useApi.js
├── components/
│   ├── ProtectedRoute.js, AdminRoute.js
│   ├── ErrorBoundary.js (NEW: React error boundary)
│   ├── LoadingSkeleton.js (NEW: PageSkeleton, TableSkeleton, CardSkeleton)
│   ├── MultiStockCompare.js (NEW: Compare strategy across stocks)
│   ├── StrategyCompare.js (NEW: Compare multiple strategies side-by-side)
│   ├── layout/UserLayout.js (Screener nav added), AdminLayout.js
│   ├── BacktestResultsPanel.js, StrategyPlayground.js
│   ├── PaperTradingContent.js, TemplatesContent.js
│   └── ui/ (Shadcn)
├── pages/
│   ├── HomePage.js, LoginPage.js, RegisterPage.js
│   ├── NotFoundPage.js (NEW: 404)
│   ├── user/UserDashboard.js, BuilderPage.js, BacktestPage.js
│   ├── user/PaperTradesPage.js, TemplatesPage.js
│   ├── user/ScreenerPage.js (NEW: Stock screener)
│   ├── user/StrategyDetailPage.js (NEW: Strategy detail view)
│   └── admin/AdminDashboard.js, AdminUsers.js
└── utils/explainStrategy.js, simulate.js

/app/backend/
├── server.py, auth.py, ai_sessions.py
├── screener/engine.py
├── backtest/engine.py, evaluator.py, costs.py, metrics.py
├── indicators/calculator.py
├── paper_trading/engine.py
├── data/service.py
└── scripts/seed_templates.py, migrate_risk_schema.py, etc.
```

## Prioritized Backlog
### P1 - Next
- [ ] Refactor server.py into separate FastAPI routers
- [ ] Strategy Optimizer (parameter sweeps)

### P2 - Nice to Have
- [ ] Token blacklist for logout / password reset
- [ ] Strategy sharing between users
- [ ] Email integration for notifications
- [ ] Watchlist feature for screener results
- [ ] Strategy Leaderboard / Most Cloned section

## Credentials
- Test user: `testai@example.com` / `Password123!`
- Admin: `admin@example.com` / `Password123!`
- Market data: 7 symbols (RELIANCE, TCS, INFY, HDFCBANK, ICICIBANK, ITC, HINDUNILVR)
