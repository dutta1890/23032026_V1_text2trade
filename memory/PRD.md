# Text2trade - Product Requirements Document

## Overview
Text2trade is a trading strategy builder platform with AI-powered features for parsing, explaining, and analyzing trading strategies. Uses NSE India market data for backtesting.

## Architecture
- **Frontend**: React + TailwindCSS + Shadcn UI + Recharts
- **Backend**: FastAPI (Python) — modular routers (v1.2.0)
- **Database**: MongoDB (with TTL indexes for token blacklist & password resets)
- **Auth**: JWT with role-based routing (admin/user), token blacklist on logout, password reset flow
- **AI**: OpenAI GPT-5.2 via Emergent LLM Key
- **Market Data**: NSE India via `nse` package
- **Indicators**: `ta` library (15 indicators)

## What's Been Implemented (All Backlog Complete)

### Session 18 (2026-03-21) — Strategy Performance Tracker + Auth Fix
- **Strategy Performance Tracker** (P0):
  - `POST /api/v1/tracker/record` — Record a performance entry (strategy name, symbol, metrics)
  - `GET /api/v1/tracker/dashboard` — Aggregated stats: cumulative P&L, strategy rankings, best/worst performers, improvement trends, recent activity
  - `GET /api/v1/tracker/history` — Last 50 records sorted by date
  - Auto-recording: Successful backtests automatically feed the tracker via `_auto_record()` in `backtest_routes.py`
  - New collection: `performance_records` with indexes on `user_id` and `(user_id, recorded_at)`
  - Frontend: Dedicated `/tracker` page with KPI stat cards, cumulative P&L area chart, best/worst performers, improvement trend, strategy rankings, and recent activity
  - Sidebar: "Tracker" nav item with BarChart3 icon
- **Auth Fix**:
  - Fixed critical bug: `AuthContext.login()` was a state setter but LoginPage passed (email, password). Now login() makes the API call and decodes JWT for user data (user_id, email, role)
  - Added `get_optional_user` dependency in `auth.py` for non-mandatory auth (used by backtest auto-record)
- **Strategy Alerts** (P1):
  - `POST /api/v1/alerts` — Create alert rule (strategy_name, metric, operator, threshold, max 20 rules)
  - `GET /api/v1/alerts` — List user's alert rules
  - `PUT /api/v1/alerts/{id}` — Toggle enable/disable
  - `DELETE /api/v1/alerts/{id}` — Delete rule
  - `POST /api/v1/alerts/evaluate` — Evaluate enabled alerts against latest tracker data, generate notifications
  - `GET /api/v1/alerts/notifications` — Get triggered notifications with unread count
  - `PUT /api/v1/alerts/notifications/{id}/read` — Mark as read
  - `PUT /api/v1/alerts/notifications/read-all` — Mark all as read
  - New collections: `alert_rules`, `alert_notifications`
  - Frontend: Dedicated `/alerts` page with create form, alert rules list (toggle/delete), triggered notifications with severity badges, "Run Check" button
  - Sidebar: "Alerts" nav item with Bell icon and unread count badge
- **Testing**: Backend 46/46, Frontend all verified — iteration_22.json, iteration_23.json

### Session 17 (2026-03-21) — P2 Backlog: Auth, Sharing, Watchlist, Leaderboard
- **Token Blacklist + Password Reset**:
  - `POST /auth/logout` blacklists JWT in MongoDB (TTL index auto-cleans expired tokens)
  - `POST /auth/forgot-password` generates reset token (1-hour TTL)
  - `POST /auth/reset-password` validates token + updates password
  - AuthContext.logout() calls API to invalidate token server-side
  - Forgot Password page + Reset Password page
  - "Forgot Password?" link on login page
- **Strategy Sharing**:
  - `POST /strategy/{id}/share` generates unique share token + stores strategy snapshot
  - `GET /shared/{token}` public view (no auth) with view/clone counters
  - `POST /shared/{token}/clone` copies strategy to authenticated user's account
  - "Share" button on Strategy Detail page with copy-to-clipboard
  - Public SharedStrategyPage at `/shared/:shareToken`
- **Watchlist**:
  - Full CRUD: add/list/update/delete with 20-item limit, duplicate prevention
  - "Watch" button on screener results (saves symbol + indicator snapshot)
  - Dedicated WatchlistPage at `/watchlist` with remove + "Build Strategy" actions
  - Watchlist in sidebar navigation
- **Template Leaderboard**:
  - `GET /templates/leaderboard` returns top 10 templates by clone count
  - "Most Popular" horizontal scroll section on Templates page
- **Testing**: Backend 15/15, Frontend all pages verified — iteration_21.json

### Session 16 (2026-03-19) — Strategy Optimizer
- Parameter sweep engine (auto-detect tunables, grid search, impact analysis, overfitting warnings)
- Optimizer UI at `/optimizer`, "Optimize" button on Strategy Detail page
- Testing: Backend 9/9, Frontend 10/10 — iteration_20.json

### Session 15 (2026-03-19) — Backend Refactoring + UI Polish
- Split server.py into modular routers, wired loading skeletons
- Testing: Backend 20/20, Frontend 14/14 — iteration_19.json

### Session 14 (2026-03-19) — Frontend Feature Push
- Screener UI, Strategy Detail page, Multi-stock comparison, Strategy comparison, UI polish
- Testing: Frontend 20/20 — iteration_18.json

### Session 13 — Complete Frontend Rebuild
- Auth system, role-based routing, all user/admin pages
- Testing: Frontend 27/27 — iteration_17.json

### Sessions 10-12 — Backend Features
- Screener, multi-backtest, comparison engine, strategy templates, backtest engine

## Routes
| Route | Auth | Component | Description |
|-------|------|-----------|-------------|
| / | No | HomePage | Landing page |
| /login | No | LoginPage | Sign in + forgot password link |
| /register | No | RegisterPage | Create account |
| /forgot-password | No | ForgotPasswordPage | Request password reset |
| /reset-password | No | ResetPasswordPage | Set new password with token |
| /shared/:token | No | SharedStrategyPage | Public shared strategy view |
| /dashboard | User | UserDashboard | Main hub with strategy comparison |
| /build | User | BuilderPage | AI builder + templates |
| /backtest/:id | User | BacktestPage | Backtest results + multi-stock compare |
| /paper-trades | User | PaperTradesPage | Paper trading |
| /templates | User | TemplatesPage | Template gallery + leaderboard |
| /screener | User | ScreenerPage | Stock screener with presets + watchlist |
| /strategy/:id | User | StrategyDetailPage | Strategy detail + share + optimize |
| /optimizer | User | OptimizerPage | Parameter sweep optimizer |
| /tracker | User | TrackerPage | Performance tracker dashboard |
| /alerts | User | AlertsPage | Strategy alerts & notifications |
| /watchlist | User | WatchlistPage | Saved screener matches |
| /admin/dashboard | Admin | AdminDashboard | System health with data banner |
| /admin/users | Admin | AdminUsers | User management |
| * | No | NotFoundPage | 404 page |

## File Structure
```
/app/backend/
├── server.py (~260 lines - app factory)
├── database.py, models.py, auth.py
├── routers/
│   ├── strategies.py, ai.py, backtest_routes.py
│   ├── paper_trading.py, templates.py
│   ├── screener_routes.py, admin.py, optimizer.py
│   ├── sharing.py, watchlist.py, leaderboard.py, tracker.py, alerts.py (NEW)
├── optimizer/engine.py
├── screener/engine.py, backtest/engine.py
└── data/service.py, scripts/

/app/frontend/src/
├── App.js (19 routes)
├── context/AuthContext.js (login → API call + JWT decode, logout → blacklist)
├── components/ (ErrorBoundary, LoadingSkeleton, MultiStockCompare, StrategyCompare)
├── pages/
│   ├── ForgotPasswordPage.js (NEW), ResetPasswordPage.js (NEW)
│   ├── SharedStrategyPage.js (NEW), NotFoundPage.js
│   ├── user/ (Dashboard, Builder, Backtest, PaperTrades, Templates,
│   │         Screener, StrategyDetail, Optimizer, Watchlist, Tracker, Alerts(NEW))
│   └── admin/ (AdminDashboard, AdminUsers)
```

## MongoDB Collections
- `users`: user accounts with hashed passwords
- `strategies`: user strategies (CRUD + versioning)
- `market_data`: OHLCV candles per symbol/timeframe
- `paper_trades`: simulated trading records
- `strategy_templates`: 12 pre-built templates with clone counts
- `blacklisted_tokens` (NEW): revoked JWTs with TTL auto-cleanup
- `password_resets` (NEW): reset tokens with 1-hour TTL
- `shared_strategies` (NEW): strategy snapshots with share tokens, view/clone counts
- `watchlist`: user watchlist items (symbol + indicator snapshot)
- `performance_records`: backtest/paper-trade metrics per strategy per user
- `alert_rules` (NEW): user alert rules (strategy_name, metric, operator, threshold, enabled)
- `alert_notifications` (NEW): triggered alert notifications (severity, read status)

## ALL BACKLOG ITEMS COMPLETE
No remaining P1/P2 items. All features requested by user have been implemented and tested.

## Credentials
- Test user: `testai@example.com` / `Password123!`
- Admin: `admin@example.com` / `Password123!`
- Market data: 7 symbols (RELIANCE, TCS, INFY, HDFCBANK, ICICIBANK, ITC, HINDUNILVR)
