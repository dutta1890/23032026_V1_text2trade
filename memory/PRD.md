# Text2trade - Product Requirements Document

## Overview
Text2trade is a trading strategy builder platform with AI-powered features for parsing, explaining, and analyzing trading strategies. Uses NSE India market data for backtesting.

## Architecture
- **Frontend**: React + TailwindCSS + Shadcn UI + Recharts
- **Backend**: FastAPI (Python) — modular routers (v0.2.0)
- **Database**: MongoDB
- **Auth**: JWT with role-based routing (admin/user)
- **AI**: OpenAI GPT-5.2 via Emergent LLM Key
- **Market Data**: NSE India via `nse` package
- **Indicators**: `ta` library (15 indicators)
- **PDF**: ReportLab (server-side generation)

## What's Been Implemented

### Session 38 (2026-04-15) — Strategy Sharing & Export (8 Tasks)
- **Task 1: Share Model** — `strategy_shares` collection with short 8-char URL-friendly IDs, view/clone tracking, expiry support
- **Task 2: Share Endpoints** — `POST /strategies/{id}/share` (create), `GET /s/{id}` (public view), `POST /s/{id}/clone` (auth clone), `DELETE /strategies/{id}/share/{share_id}` (revoke)
- **Task 3: Public Share View** — `/s/{shareId}` page with read-only strategy view, backtest results, equity curve, broker instructions, limitations banner, clone/signup CTA
- **Task 4: Copy as Text** — Formatted plain text for WhatsApp/email with strategy conditions, risk, backtest stats
- **Task 5: PDF Export** — Server-side PDF (ReportLab) with strategy details, metrics table, disclaimers. Available for owned and shared strategies
- **Task 6: Broker Instructions** — Dynamic step-by-step for Zerodha, Angel One, Upstox, Dhan, Groww, 5paisa with broker help links
- **Task 7: Share Analytics** — View/clone tracking per share, admin endpoint with top shared strategies and conversion rate
- **Task 8: Share Management UI** — Strategy detail page: Share & Export section with Copy Text/PDF/Share Link buttons, stats, revoke. Broker execution section with 6 brokers.
- **Testing**: 41/41 backend, all frontend verified (iteration_38)

### Session 37 (2026-04-15) — Reproducible Backtests (7 Tasks)
- Immutable backtest snapshots, strategy versioning, SHA-256 data hashing, verify export ZIP, backtest comparison tool, permanent URLs, engine changelog
- Bug fix: BacktestPage.js infinite loop (memoized useApi)
- Testing: 30/30 backend (iteration_37)

### Session 36 (2026-04-15) — Engine Benchmarks & Lookahead Bias Audit
- 12 anti-cheat tests, 10 benchmark strategies (10/10 PASS), public /benchmarks page, admin integration

### Previous Sessions (10-26c)
- Full platform: AI strategy builder, backtesting, paper trading, screener, optimizer, tracker, alerts, watchlist, templates, sharing, leaderboard, demo mode, onboarding, legal compliance, diagnostics, session hardening, SEBI compliance, knowledge base

## Key Routes
| Route | Auth | Description |
|-------|------|-------------|
| /s/:shareId | No | Public strategy share view with broker instructions |
| /backtest/snapshot/:id | No | Public immutable backtest viewer |
| /backtest/compare | No | Side-by-side snapshot comparison |
| /benchmarks | No | Engine benchmark results |
| /compliance | No | SEBI compliance info |

## Key API Endpoints (New)
| Endpoint | Auth | Description |
|----------|------|-------------|
| POST /api/v1/strategies/{id}/share | User | Create short share link |
| GET /api/v1/s/{share_id} | No | Public share view |
| POST /api/v1/s/{share_id}/clone | User | Clone to account |
| DELETE /api/v1/strategies/{id}/share/{share_id} | User | Revoke share |
| GET /api/v1/strategies/{id}/copy-text | User | Formatted text for sharing |
| GET /api/v1/s/{share_id}/copy-text | No | Public copy text |
| GET /api/v1/strategies/{id}/pdf | User | PDF download |
| GET /api/v1/s/{share_id}/pdf | No | Public PDF download |
| GET /api/v1/strategies/{id}/broker-instructions/{broker} | User | Broker-specific steps |
| GET /api/v1/s/{share_id}/broker-instructions/{broker} | No | Public broker steps |
| GET /api/v1/strategies/{id}/share-stats | User | Share analytics |
| GET /api/v1/admin/analytics/shares | Admin | Platform share analytics |

## New MongoDB Collections
- `strategy_shares` — short-ID shares with view/clone counters
- `backtest_snapshots` — immutable backtest records
- `strategy_versions` — strategy change history

## Remaining Backlog
- **CI Documentation (P2)**: Update DEPLOYMENT.md
- **Broker Integrations (P1)**: Zerodha, Angel One, Upstox, Dhan — Phase 2 actual OAuth
- **Scheduled Auto-Evaluation (P2)**: Auto alert checks
- **Verified Domain Email**: Resend sandbox to full delivery

## Credentials
- Test user: `testai@example.com` / `Password123!`
- Admin: `admin@example.com` / `Password123!`
