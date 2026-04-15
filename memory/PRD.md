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

### Session 39 (2026-04-15) — Broker Login Links & Execute on Broker
- **Broker Links**: Login URLs for 6 brokers (Zerodha, Angel One, Upstox, Dhan, Groww, 5paisa)
- **BrokerModal Component**: Reusable modal with disclaimer step (first click) + broker selection. "Don't show again" checkbox saves preference.
- **Execute on Broker Button**: Added to Strategy Detail page header, Backtest results page, and Share View page
- **Broker Preference**: `preferred_broker` field in user profile, selectable from Profile page. Auto-highlighted in modal.
- **Disclaimer**: Required before first broker click. Can be dismissed permanently via profile setting.
- **Audit Trail**: Every broker link click logged as `broker_link_generated` action for SEBI compliance
- **Share Page Integration**: Logged-in users see "Open Broker Platform" button, logged-out users see login prompt
- **Testing**: 19/19 backend, all frontend verified (iteration_39)

### Session 38 (2026-04-15) — Strategy Sharing & Export (8 Tasks)
- Short URL shares (/s/{id}), copy-as-text, PDF export, broker instructions for 6 brokers, share analytics, share management UI
- Testing: 41/41 backend (iteration_38)

### Session 37 (2026-04-15) — Reproducible Backtests (7 Tasks)
- Immutable snapshots, strategy versioning, SHA-256 data hashing, verify export ZIP, comparison tool, permanent URLs, engine changelog
- Testing: 30/30 backend (iteration_37)

### Session 36 (2026-04-15) — Engine Benchmarks & Lookahead Bias Audit
- 12 anti-cheat tests, 10 benchmark strategies (10/10 PASS), public /benchmarks page

### Previous Sessions (10-26c)
- Full platform: AI strategy builder, backtesting, paper trading, screener, optimizer, tracker, alerts, watchlist, templates, sharing, leaderboard, demo mode, onboarding, legal compliance, diagnostics, session hardening, SEBI compliance, knowledge base

## Key API Endpoints (New in This Session)
| Endpoint | Auth | Description |
|----------|------|-------------|
| GET /api/v1/broker-links | No | Returns all 6 broker login URLs |
| POST /api/v1/broker-link/generate | User | Logs broker link click to audit trail |
| PUT /api/v1/account/profile | User | Now supports preferred_broker and broker_disclaimer_dismissed |

## Remaining Backlog
- **CI Documentation (P2)**: Update DEPLOYMENT.md
- **Broker Integrations (P1)**: Zerodha, Angel One, Upstox, Dhan — Phase 2 actual OAuth + deep links
- **Scheduled Auto-Evaluation (P2)**: Auto alert checks
- **Verified Domain Email**: Resend sandbox to full delivery

## Credentials
- Test user: `testai@example.com` / `Password123!`
- Admin: `admin@example.com` / `Password123!`
