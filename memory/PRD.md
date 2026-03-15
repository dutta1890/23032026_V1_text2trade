# Text2trade - Product Requirements Document

## Overview
Text2trade is a trading strategy builder platform with AI-powered features for parsing, explaining, and analyzing trading strategies. Uses NSE India market data for backtesting.

## Architecture
- **Frontend**: React + TailwindCSS + Shadcn UI
- **Backend**: FastAPI (Python)
- **Database**: MongoDB
- **Market Data**: NSE India via `nse` package (no API key, no signup)
- **AI**: OpenAI GPT-5.2 via Emergent LLM Key (temperature=1 only, GPT-5.2 constraint)
- **Auth**: JWT (Access + Refresh tokens) with admin/user roles

## What's Been Implemented

### Session 4 (2026-03-15) — AI Session System & Token Limits
- **AI Token Budgets**: Role-specific max_tokens (nl_parser=800, explainer=400, risk_analyzer=400, session_chat=600). Temperature=1 (GPT-5.2 only supports 1).
- **Daily Usage Limits**: nl_parser=20/day, explainer=10/day, risk_analyzer=10/day, session_chat=30/day. Stored in MongoDB `ai_usage` collection with compound index on (user_id, role, date).
- **Conversation Sessions**: MongoDB `conversation_sessions` collection with TTL 24h index. CRUD endpoints: start, message, get, delete.
- **Context Window Management**: Last 6 messages with 500-token budget, trim oldest first.
- **Session Ownership**: Users can only access their own sessions (403 for cross-user access).
- **Stochastic Frontend Fix**: `explainStrategy.js` now handles both "Stochastic" and "stoch" indicator names.
- **Testing**: 13/13 tests passed (iteration_9.json)

### Session 3 (2026-03-15) — Market Data Pipeline + Admin Roles
- **Admin/User Roles**: `role` field in users, `get_admin_user` dependency (403 if not admin), role in JWT payload
- **create_admin.py**: CLI script to seed admin accounts
- **Market Data Pipeline**: NSE India-native data sources (no yfinance):
  - NseIndiaApiSource (PRIMARY) — `nse` package, daily OHLCV
  - NSEPythonSource (BACKUP) — `nsepython` package (currently broken, NSE blocked endpoint)
  - NSEBhavcopySource (FALLBACK) — official NSE CSV archives
- **Data Ingestion**: `scripts/ingest_data.py` — 22 symbols x 4 timeframes, 1.5s rate limiting
- **Data Service**: `data/service.py` — `get_ohlcv()`, `get_available_symbols()`, `get_data_range()` — reads MongoDB ONLY
- **Admin Endpoints**: `/api/v1/admin/data/status`, `/api/v1/admin/data/refresh`, `/api/v1/admin/users`, `/api/v1/admin/analytics`
- **Startup Validation**: Checks market_data on startup, warns if empty/stale
- **yfinance completely removed**: Zero references in codebase

### Session 2 (2026-03-05) — API Hardening & Auth Fix
- Rate limiting (slowapi), input sanitization, circuit breakers, structured logging
- Fixed frontend JWT auth flow (was using old /api/ paths and X-User-Id)
- Stochastic indicator exit condition UI
- Fixed analytics crash, internal test utility

### Session 1 — MVP
- Full scaffold (Home, Login, Dashboard)
- JWT auth, strategy CRUD, AI features (parser, explainer, risk analyzer)
- Indicators: RSI, SMA, EMA, MACD, Stochastic, ADX, ATR
- Historical backtest, usage analytics, landing page with waitlist

## File Structure
```
/app/backend/
├── auth.py                    # JWT auth with admin/user roles
├── server.py                  # FastAPI with all /api/v1/ routes + admin + session endpoints
├── ai_sessions.py             # AI config, usage tracking, session CRUD, context window
├── data/
│   ├── service.py             # Data access layer (MongoDB ONLY)
│   └── sources/
│       ├── base.py            # MarketDataSource ABC
│       ├── nseindia_api_source.py  # PRIMARY (nse package)
│       ├── nsepython_source.py     # BACKUP (broken)
│       └── nse_bhavcopy_source.py  # FALLBACK
├── scripts/
│   ├── create_admin.py        # Seed admin accounts
│   ├── setup_data_source.py   # Interactive setup wizard
│   ├── ingest_data.py         # Download data from NSE India
│   └── refresh_data.py        # Incremental daily refresh
├── resilience.py, logging_config.py, indicator_registry.py
└── tests/test_ai_sessions.py  # Pytest for AI session system
```

## API Endpoints
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| /api/v1/health | GET | No | Health check |
| /api/v1/auth/register | POST | No | Register (role=user) |
| /api/v1/auth/login | POST | No | Login -> JWT with role |
| /api/v1/strategy | POST | JWT | Create strategy |
| /api/v1/strategies | GET | JWT | List user strategies |
| /api/v1/backtest | POST | No | Run backtest |
| /api/v1/parse-strategy | POST | JWT | AI: parse natural language to strategy JSON |
| /api/v1/explain | POST | JWT | AI: explain a strategy |
| /api/v1/analyze-risk | POST | JWT | AI: analyze strategy risks |
| /api/v1/session/start | POST | JWT | Create conversation session |
| /api/v1/session/{id}/message | POST | JWT | Send message in session |
| /api/v1/session/{id} | GET | JWT | Get full session |
| /api/v1/session/{id} | DELETE | JWT | Delete session |
| /api/v1/ai/usage | GET | JWT | Get user's AI usage stats |
| /api/v1/admin/data/status | GET | Admin | Data health report |
| /api/v1/admin/data/refresh | POST | Admin | Trigger refresh |
| /api/v1/admin/users | GET | Admin | List all users |
| /api/v1/admin/analytics | GET | Admin | Platform stats |

## DB Collections
- `users`: {user_id, email, password_hash, role, created_at, is_active}
- `strategies`: {id, user_id, version, metadata, market, instrument, timeframe, entry_conditions, exit_conditions, filters, risk_management}
- `market_data`: {symbol, timeframe, timestamp, open, high, low, close, volume} (unique index)
- `conversation_sessions`: {session_id, user_id, messages[], strategy_draft, created_at, updated_at} (TTL 24h)
- `ai_usage`: {user_id, role, date, count} (unique compound index)

## Prioritized Backlog

### P1 - Next
- [ ] Frontend edit/delete buttons on strategy list
- [ ] Analytics dashboard UI
- [ ] Refactor server.py into routers (session, AI, strategy CRUD)

### P2 - Nice to Have
- [ ] Expand backtest beyond SMA (RSI/MACD/Stochastic with real data)
- [ ] Token blacklist for logout
- [ ] Password reset flow
- [ ] Strategy sharing between users
- [ ] Caching layer for DB queries
- [ ] Email integration for waitlist

## Test Reports
- `/app/test_reports/iteration_9.json` — AI sessions + token limits (13/13 pass, 100%)
- `/app/test_reports/iteration_8.json` — Admin roles + market data pipeline (100% pass)

## Credentials
- Test user: `testai@example.com` / `Password123!`
- Test user 2: `testai2@example.com` / `Password123!`
- Market data: RELIANCE daily (743 candles) ingested
