# Text2trade - Product Requirements Document

## Overview
Text2trade is a trading strategy builder platform with AI-powered features for parsing, explaining, and analyzing trading strategies. Uses NSE India market data for backtesting.

## Architecture
- **Frontend**: React + TailwindCSS + Shadcn UI + Recharts
- **Backend**: FastAPI (Python) — modular routers (v0.2.0)
- **Database**: MongoDB (with TTL indexes for token blacklist & password resets)
- **Auth**: JWT with role-based routing (admin/user), token blacklist on logout, password reset flow
- **AI**: OpenAI GPT-5.2 via Emergent LLM Key
- **Market Data**: NSE India via `nse` package
- **Indicators**: `ta` library (15 indicators)

## What's Been Implemented

### Session 36 (2026-04-15) — Engine Benchmarks & Lookahead Bias Audit
- **Lookahead Bias Audit**: Full code audit of `engine.py`, `evaluator.py`, `calculator.py`. Verdict: NO LOOKAHEAD BIAS DETECTED. Document at `tests/lookahead_audit.md`
- **Anti-Cheat Test Suite**: 12 pytest tests in `tests/test_lookahead_bias.py`:
  - Truncation Consistency (2) — historical trades unchanged by extending dataset
  - Future Data Modification (1) — corrupting future prices has zero effect on past trades
  - Perfect Foresight Rejection (2) — no strategy achieves impossible win rates
  - Indicator Independence (3) — RSI/SMA/MACD unaffected by future candles
  - Entry-Exit Ordering (2) — chronologically valid timestamps
  - Deterministic Results (2) — same input always produces identical output
- **10 Benchmark Strategies**: JSON configs in `tests/benchmarks/strategies.json`:
  1. SMA Golden Cross (50/200) on RELIANCE
  2. RSI Mean Reversion (30/70) on HDFCBANK
  3. MACD Crossover on TCS
  4. Bollinger Bands Mean Reversion on INFY
  5. EMA Crossover (9/21) on ITC
  6. Supertrend Buy/Sell on ICICIBANK
  7. Stochastic Oscillator (20/80) on HINDUNILVR
  8. RSI + SMA Combo on RELIANCE
  9. MACD + ADX Trend Filter on TCS
  10. RSI Mean Reversion + 3% Stop Loss on RELIANCE
- **Benchmark Runner**: `tests/benchmarks/run_benchmarks.py` validates results against expected ranges, checks determinism and chronology
- **Backend API**:
  - `GET /api/v1/benchmarks` (public) — returns latest run results, strategy list, audit status
  - `POST /api/v1/admin/benchmarks/run` (admin) — triggers fresh benchmark run
  - `GET /api/v1/admin/benchmarks/history` (admin) — last 10 runs
- **Public /benchmarks Page**: Shows 10/10 pass status, audit verdict, anti-cheat suite breakdown, 10 strategy cards with expandable check details
- **Admin Dashboard Integration**: ENGINE BENCHMARKS section with stat cards (Benchmark Status, Anti-Cheat Tests, Lookahead Audit) and Run Benchmarks button
- **Cross-links**: Compliance page links to Benchmarks; Benchmarks page links to Compliance
- **Testing**: 12/12 anti-cheat tests, 10/10 benchmarks, frontend verified (iteration_36)

### Previous Sessions (Summary)
- Sessions 10-26c: Full platform built — AI strategy builder, backtesting, paper trading, screener, optimizer, tracker, alerts, watchlist, templates, sharing, leaderboard, demo mode, onboarding, legal compliance, diagnostics, session hardening, data export, SEBI compliance, knowledge base, code quality refactor

## Routes
| Route | Auth | Component | Description |
|-------|------|-----------|-------------|
| / | No | HomePage | Landing page |
| /login | No | LoginPage | Sign in |
| /register | No | RegisterPage | Create account |
| /forgot-password | No | ForgotPasswordPage | Request password reset |
| /reset-password | No | ResetPasswordPage | Set new password |
| /shared/:token | No | SharedStrategyPage | Public shared strategy view |
| /legal/:docType | No | LegalPage | Legal documents |
| /compliance | No | CompliancePage | SEBI compliance info |
| /benchmarks | No | BenchmarksPage | Engine benchmark results |
| /dashboard | User | UserDashboard | Main hub |
| /build | User | BuilderPage | AI builder + templates |
| /backtest/:id | User | BacktestPage | Backtest results |
| /paper-trades | User | PaperTradesPage | Paper trading |
| /templates | User | TemplatesPage | Template gallery |
| /screener | User | ScreenerPage | Stock screener |
| /strategy/:id | User | StrategyDetailPage | Strategy detail |
| /optimizer | User | OptimizerPage | Parameter sweep |
| /watchlist | User | WatchlistPage | Saved screener matches |
| /tracker | User | TrackerPage | Performance tracker |
| /alerts | User | AlertsPage | Strategy alerts |
| /profile | User | ProfilePage | User profile |
| /glossary | User | GlossaryPage | Trading terms |
| /admin/dashboard | Admin | AdminDashboard | System health + benchmarks |
| /admin/users | Admin | AdminUsers | User management |
| /admin/diagnostics | Admin | AdminDiagnostics | Error tracking |
| /admin/compliance | Admin | AdminCompliance | SEBI compliance admin |
| * | No | NotFoundPage | 404 page |

## MongoDB Collections
- `users`, `strategies`, `market_data`, `paper_trades`, `strategy_templates`
- `blacklisted_tokens`, `password_resets`, `shared_strategies`, `watchlist`
- `performance_records`, `alert_rules`, `alert_notifications`
- `knowledge_base`, `legal_documents`, `user_consents`
- `audit_trail`, `broker_connections`, `error_logs`, `performance_logs`
- `benchmark_results` (NEW) — stores benchmark run results

## Remaining Backlog
- **CI Trigger Documentation (P2)**: Update `DEPLOYMENT.md` with release-check instructions
- **Broker Integrations (P1)**: Zerodha, Angel One, Upstox, Dhan — UI placeholders exist
- **Scheduled Auto-Evaluation (P2)**: Auto alert checks post-backtest
- **Verified Domain Email**: Switch from Resend sandbox to full delivery

## Credentials
- Test user: `testai@example.com` / `Password123!`
- Admin: `admin@example.com` / `Password123!`
- Market data: 7 symbols (RELIANCE, TCS, INFY, HDFCBANK, ICICIBANK, ITC, HINDUNILVR)
