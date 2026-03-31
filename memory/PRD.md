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

### Session 19 (2026-03-21) — Full System Test & QA Sprint
- **Bug Fix**: Admin strategy_count query was using email instead of user_id — FIXED
- **Role-Based Access Tests**: 5 users registered, strategy isolation verified, admin 403 for users, admin 200 for all admin endpoints
- **AI Conversation Tests**: Happy path (2-3 turns), vague input (template suggestions), unsupported indicator (error mode), F&O (redirect message), session timeout (clean 404)
- **Backtest Accuracy**: SMA 50/200 on RELIANCE (1 trade, 742 candles), RSI<30 on HDFCBANK (11 trades), Supertrend on INFY (14 trades) — all producing valid results
- **Paper Trading**: Deploy → trades created, Pause → status paused, Stop → status stopped, positions closed
- **Frontend QA**: 29/29 tests passed — every page verified (login, register, forgot-password, dashboard, build, screener, optimizer, tracker, alerts, watchlist, templates, paper-trades, strategy detail, admin dashboard, admin users, shared strategy, 404)
- **Mobile Responsive**: Verified at 375x812 (iPhone)
- **Console Errors**: Minor table hydration warning (non-functional), no unhandled exceptions
- **KNOWN_ISSUES.md**: Created at `/app/KNOWN_ISSUES.md`
- **Testing**: iteration_24.json (Frontend 29/29)

### Session 20 (2026-03-23) — Demo Account Mode + Onboarding Tour
- **User Schema Extension**: Added `account_mode`, `demo_capital`, `demo_created_at`, `has_completed_onboarding` to users collection
- **Registration Flow**: `POST /api/v1/auth/register` now accepts `start_demo: bool`. Demo = seeds 3 strategies + 1 paper trade + 1 backtest + ₹10,000 virtual capital
- **Account Management Endpoints**:
  - `POST /api/v1/account/activate-demo` — Activate demo mode (idempotent)
  - `POST /api/v1/account/switch-mode` — Toggle between "demo" and "real" views
  - `GET /api/v1/account/profile` — Returns mode, capital, onboarding status
  - `POST /api/v1/account/complete-onboarding` / `restart-tour`
- **Demo Data Seeding**: 3 pre-built strategies (Golden Cross, RSI Mean Reversion, Supertrend), 1 backtest result, 1 paper trade with 5 simulated trades, demo capital tracker
- **Data Filtering**: All strategy/paper-trade/tracker queries filter by `is_demo` matching current mode. Legacy data (without field) shows in real mode via `$ne: True`
- **Demo Protection**: Demo-seeded strategies (with `demo_tag`) cannot be deleted (403)
- **Frontend**: Register page with dual CTAs ("Start Free Demo" / "Create Account"), demo banner, demo capital badge in sidebar, DEMO badges on strategy cards, mode toggle, "Restart Tour" button
- **Onboarding Tour**: react-joyride integration with 8 steps loaded from `/config/tour_config.json`. Auto-triggers on first demo login. Completes/skips via API
- **New Collections**: `demo_capital` (user_id, starting_capital, current_capital, trades_made)
- **Testing**: Backend 17/17, Frontend 10/10 — iteration_25.json

### Session 25 (2026-03-28) — Session Hardening, Data Export, Input Validation, Versioning
- **Task 1: Session Timeout Handling**:
  - `useApi.js` rewritten with 401 interceptor — silently refreshes token via `/auth/refresh`, retries original request transparently
  - Refresh token stored in `localStorage` (`t2t_refresh`), passed during refresh
  - `auth.py` enforces 7-day max age on refresh tokens (`iat` claim check)
  - `SessionExpiredModal.js` shown when refresh fails — "Session Expired" with login redirect
- **Task 2: Multiple Tab Handling**:
  - `AuthContext.js` listens to `storage` events — detects logout in other tabs
  - Detects user_id mismatch across tabs → forces `window.location.reload()`
- **Task 3: Data Export**:
  - `POST /api/v1/account/export-data` returns JSON: {exported_at, user_email, profile, strategies, backtests, paper_trades, performance_records}
  - Excludes demo data (`is_demo: true`), excludes `password_hash` and `_id`
  - Profile sanitized to only include safe fields (email, display_name, timezone, etc.)
- **Task 4: Input Hardening**:
  - 1MB request body limit in `RequestIdMiddleware` (413 on exceed)
  - Strategy validation: max 10 entry + 10 exit conditions (422 if exceeded)
  - Strategy names: max 200 chars, HTML tags stripped
  - `sanitize_user_input()` in `resilience.py` now strips `<tags>` (XSS prevention)
- **Task 5: App Version + Cache Busting**:
  - `GET /api/v1/app/version` (public) returns `{version, build_date, min_supported_version}`
  - `VersionBanner.js` compares frontend vs backend versions, shows refresh banner if outdated
  - `LegalFooter.js` displays `v0.2.0` in footer
  - `APP_VERSION=0.2.0` in backend `.env`, `REACT_APP_VERSION=0.2.0` in frontend `.env`
- **Task 6: Middleware Enhancement**:
  - `last_active` timestamp updated on every authenticated request in `RequestIdMiddleware`
- **Testing**: 19/19 backend + all frontend passed (iteration_30.json)

### Session 24 (2026-03-28) — Legal Compliance System (6 Tasks)
- **Task 1: Legal Documents**: Created 4 markdown files in `/backend/legal/` — Terms of Service, Privacy Policy, Risk Disclaimer, Cookie Policy. All include app-specific clauses (AI-generated strategies, backtesting limitations, SEBI notice, governing law India).
- **Task 2: Legal Document API**:
  - Public endpoints: `GET /api/v1/legal/{terms|privacy|disclaimer|cookies}` — returns markdown + version + effective_date (no auth)
  - `GET /api/v1/legal/versions` — returns latest versions of all docs
  - Admin: `PUT /api/v1/admin/legal/{type}` — creates new version (immutable, audit trail)
  - MongoDB `legal_documents` collection with unique index on (type, version)
  - Auto-seeds from markdown files on startup
- **Task 3: Consent Tracking**:
  - MongoDB `user_consents` collection — permanent records: `{user_id, document_type, document_version, accepted_at, ip_address}`
  - Registration requires `accepted_terms=true, accepted_privacy=true, accepted_disclaimer=true` — returns 400 otherwise
  - `GET /api/v1/legal/consent-status` — checks pending vs latest versions
  - `POST /api/v1/legal/accept` — accepts specific doc+version with IP logging
- **Task 4: Registration Consent Checkboxes**: 3 checkboxes with clickable links to legal doc modals. Buttons disabled until all checked.
- **Task 5: Re-consent Modal**: Full-screen blocking modal on login if docs updated. Tab-based UI for multiple pending docs. "Log out instead" option. Cannot dismiss.
- **Task 6: Legal Pages + Footer**: `/legal/terms`, `/legal/privacy`, `/legal/disclaimer` public pages. Footer links on register, login, and user dashboard.
- **Testing**: 17/17 backend + all frontend passed (iteration_29). Bug fixed: `get_latest_doc()` sort by `created_at` instead of version string.

### Session 23 (2026-03-28) — Diagnostics System (5 Tasks)
- **Task 1: Backend Error Tracking**:
  - `diagnostics/__init__.py`: ErrorRecord model, store_error(), sanitize_dict(), classify_severity()
  - MongoDB `error_logs` collection with 90-day TTL index
  - Global exception handler catches ALL unhandled exceptions, stores record, returns friendly "An internal error occurred" message (never raw stack traces)
  - Severity auto-classification: TimeoutError→medium, ValidationError→low, DB errors→high, unhandled→critical
  - Request body sanitization strips passwords, tokens, secrets
- **Task 2: Frontend Crash Boundary**:
  - Enhanced `ErrorBoundary.js`: catches React render errors, shows friendly UI with "Go to Dashboard" and "Report Details" buttons
  - Auto-sends crash reports to `POST /api/v1/diagnostics/frontend-crash` with error_message, component_stack, page_url, browser_info, user_id
- **Task 3: Health Monitoring Endpoints**:
  - `GET /api/v1/health` includes `error_rate.last_1h` and `error_rate.last_24h`
  - `GET /api/v1/admin/diagnostics/summary` — dashboard data (24h/7d counts by severity, top errors, affected users, hourly error rate)
  - `GET /api/v1/admin/diagnostics/errors` — paginated, filterable by severity/source/resolved/date/user
  - `GET /api/v1/admin/diagnostics/errors/{id}` — full detail with stack trace
  - `PUT /api/v1/admin/diagnostics/errors/{id}/resolve` — mark resolved with admin note
- **Task 4: Performance Monitoring**:
  - Middleware logs slow requests (>3s) to `performance_logs` collection (30-day TTL)
  - `GET /api/v1/admin/diagnostics/performance` — avg/max/P95 response times per endpoint, slowest requests
  - Test endpoints: `/test/error` (force RuntimeError), `/test/slow` (4s sleep)
- **Task 5: Admin Diagnostics Dashboard** (`/admin/diagnostics`):
  - Summary cards: Errors (24h), Critical count, Affected Users, Avg Response Time
  - Error rate bar chart (Recharts, hourly last 24h)
  - Errors table with severity badges, source, type, endpoint, status, pagination
  - Filter dropdowns: severity, source (backend/frontend), resolved status
  - Error detail modal: full stack trace, sanitized request body, resolve button with notes
  - Performance tab: slowest endpoints table, P95 times, recent slow requests
- **Testing**: 20/20 passed (iteration_28.json). Testing agent fixed infinite loop bug in AdminDiagnostics.js (unstable useCallback deps)

### Session 22 (2026-03-26) — P0 Bug Fixes: Resend Sandbox + Auth Persistence + Validation Error Crash
- **Resend Sandbox Graceful Handling (P0)**:
  - `email_service.py` `send_email()` now returns structured dict `{sent, sandbox_restricted, error}` instead of bare bool
  - `auth.py` `create_password_reset_otp()` refactored to `async` — awaits email result and passes sandbox info upstream
  - `PasswordResetResponse` model extended with optional `email_sent` and `warning` fields
  - `forgot-password` endpoint returns `{email_sent: false, warning: "Email could not be sent (sandbox mode)..."}` when Resend sandbox blocks delivery
  - Frontend `ForgotPasswordPage.js` displays amber inline warning banner + `sonner` toast notification
  - OTP is always logged to backend console as fallback
  - No more 500 errors for arbitrary email addresses
- **Auth State Persistence (P0, Recurring)**:
  - `AuthContext.js` refactored to use `localStorage` (`t2t_token`, `t2t_user`) for session persistence
  - Token expiry validated on mount via `parseJwt()` — expired tokens auto-cleared
  - `restoring` state prevents flash-redirect on page load
  - `ProtectedRoute.js` and `AdminRoute.js` check `restoring` before redirecting
  - `switchMode()` updates localStorage immediately
  - `logout()` clears all localStorage keys
  - Page refresh now stays on authenticated routes
- **Pydantic Validation Error Crash Fix (P0)**:
  - React error #31: Pydantic validation errors returned `detail` as array of objects, rendered directly in JSX causing crash
  - Created `/utils/apiError.js` with `extractApiError()` utility — safely extracts human-readable messages from both string and array error formats
  - Applied to all 18+ error handling locations across RegisterPage, LoginPage, ForgotPasswordPage, ResetPasswordPage, ProfilePage, TrackerPage, BacktestPage
- **Testing**: Backend 9/9, Frontend 8/8 — iteration_27.json + manual verification of registration flow

### Session 21 (2026-03-24) — User Profile & Account Management
- **Profile Schema**: Extended users with display_name, phone, avatar_initial, timezone, default_capital, preferred_instruments, notification_preferences
- **Profile Endpoints**:
  - `GET /api/v1/account/profile` — Full profile with all fields
  - `PUT /api/v1/account/profile` — Update with validation (phone format, timezone list, capital > 0)
  - `PUT /api/v1/profile/change-password` — Requires current password verification
- **Forgot/Reset Password (OTP)**: Updated from token-based to 6-digit OTP with 15-min TTL. OTP logged to console when EMAIL_ENABLED=false
- **Account Management**:
  - `GET /api/v1/account/summary` — Stats: mode, strategy counts, backtests, paper trades, member_since
  - `POST /api/v1/account/export-data` — JSON export of all user data (GDPR readiness)
  - `DELETE /api/v1/account` — Soft delete (is_active=false), requires password confirmation
- **Frontend Profile Page** (`/profile`): 7 sections — Personal Info, Password, Preferences, Notifications, Account (mode + stats + export + delete), Integrations (Coming Soon placeholders for Zerodha/Angel One/Upstox), App (tour restart, version, bug report)
- **Frontend Updates**: Sidebar profile avatar link, updated Forgot/Reset Password pages for OTP flow
- **Testing**: Backend 19/20 (1 skipped), Frontend 100% — iteration_26.json

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

### Session 26 (2026-03-28) — Knowledge Base & Info Tooltips System
- **Task 1: Knowledge Base Backend**:
  - `GET /api/v1/knowledge` — returns all 30 seeded trading terms sorted by term_id
  - `GET /api/v1/knowledge/{term_id}` — returns single term details
  - `GET /api/v1/knowledge/category/{category}` — filter by category (indicator/risk_management/general)
  - Admin CRUD: POST/PUT/DELETE at `/api/v1/admin/knowledge`
  - MongoDB `knowledge_base` collection with unique index on `term_id`
  - 30 terms seeded: 15 indicators, 8 risk management, 7 general concepts
  - Fixed seed script to load `.env` (was seeding wrong DB)
- **Task 2: InfoTooltip Component**:
  - Reusable `<InfoTooltip termId="..." />` fetches KB data once, caches globally
  - Hover reveals term name, description, and real-world example via Shadcn Tooltip
- **Task 3: Tooltips Injected Across UI**:
  - Strategy Builder: Entry/Exit indicator labels, ADX filter, Stop Loss, ATR Multiple
  - BuilderPage RiskEditor: Stop Loss, Target Profit, Trailing Stop Loss, Time-based Exit
  - BacktestPage MetricCards: Win Rate, Max Drawdown, Sharpe Ratio, Profit Factor
- **Task 4: Trading Glossary Page** (`/glossary`):
  - Searchable, filterable dictionary of all 30 terms
  - Category filters: All, General Concepts, Indicators, Risk Management
  - Cards with descriptions and example blocks
  - Added to sidebar navigation with GraduationCap icon
- **Testing**: 31/31 backend + all frontend passed (iteration_31.json)

### Session 26b (2026-03-28) — UI Polish: Password Toggle, Badge Removal, Dropdown Descriptions
- **Password Eye Toggle**: Added Eye/EyeOff toggle to all password fields: LoginPage, RegisterPage (password + confirm), ResetPasswordPage (new + confirm)
- **Emergent Badge Removed**: Hidden "Made with Emergent" badge via index.html inline style + CSS override
- **Strategy Builder Dropdowns**: Added short descriptions below each indicator name in Entry/Exit/SL type dropdowns (e.g., "Momentum (0-100). <30 oversold, >70 overbought" for RSI)
- **Testing**: All features verified (iteration_32.json)

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
| /glossary | User | GlossaryPage | Trading terms dictionary with search |
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
│   ├── sharing.py, watchlist.py, leaderboard.py, tracker.py, alerts.py, knowledge.py (NEW)
├── optimizer/engine.py
├── screener/engine.py, backtest/engine.py
└── data/service.py, scripts/

/app/frontend/src/
├── App.js (19 routes)
├── context/AuthContext.js (login → API call + JWT decode, logout → blacklist)
├── components/ (ErrorBoundary, LoadingSkeleton, MultiStockCompare, StrategyCompare, InfoTooltip(NEW))
├── pages/
│   ├── ForgotPasswordPage.js (NEW), ResetPasswordPage.js (NEW)
│   ├── SharedStrategyPage.js (NEW), NotFoundPage.js
│   ├── user/ (Dashboard, Builder, Backtest, PaperTrades, Templates,
│   │         Screener, StrategyDetail, Optimizer, Watchlist, Tracker, Alerts)
│   ├── GlossaryPage.js (NEW)
│   └── admin/ (AdminDashboard, AdminUsers, AdminDiagnostics)
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
- `knowledge_base` (NEW): 30 trading terms with term_id, term, category, short_description, example

## Remaining Backlog
- **Broker Integrations (P1)**: Zerodha, Angel One, Upstox — UI placeholders exist on profile page
- **Scheduled Auto-Evaluation (P2)**: Automatically run alert checks post-backtest
- **Verified Domain Email**: Once user adds domain on Resend, switch from sandbox fallback to full delivery

## Credentials
- Test user: `testai@example.com` / `Password123!`
- Admin: `admin@example.com` / `Password123!`
- Market data: 7 symbols (RELIANCE, TCS, INFY, HDFCBANK, ICICIBANK, ITC, HINDUNILVR)
