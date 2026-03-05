# Text2trade - Product Requirements Document

## Overview
Text2trade is a trading strategy builder platform with AI-powered features for parsing, explaining, and analyzing trading strategies.

## Original Problem Statement
Build a full-stack web app called Text2trade with:
- Home page, Login page, Dashboard with sidebar navigation
- Strategy Builder UI with multi-step form
- AI features: Natural Language Parser, Strategy Explainer, Risk Analyzer
- Support for multiple indicators: RSI, SMA, EMA, MACD, Stochastic, ADX (filter)
- JWT authentication with MongoDB persistence
- API hardening: rate limiting, input sanitization, circuit breakers, structured logging

## Architecture
- **Frontend**: React (CRA with Craco) + TailwindCSS + Shadcn UI
- **Backend**: FastAPI (Python)
- **Database**: MongoDB (persistent)
- **AI**: OpenAI GPT-5.2 via Emergent LLM Key
- **Authentication**: JWT (Access + Refresh tokens) with bcrypt password hashing
- **Theme**: "Tactical Bloomberg" - Dark mode, Signal Green (#00E599) accent

## User Personas
1. **Traders**: Need fast, functional interfaces to create and manage strategies
2. **Developers**: Need clean scaffold to build upon

## Supported Indicators
| Indicator | Type | Parameters | Operators |
|-----------|------|------------|-----------|
| RSI | Entry/Exit | period, overbought, oversold | <, >, cross |
| SMA | Entry/Exit | short, long | cross_above, cross_below |
| EMA | Entry/Exit | short, long | cross_above, cross_below |
| MACD | Entry/Exit | fast, slow, signal | bullish_cross, bearish_cross |
| Stochastic | Entry/Exit | k_period, d_period | cross_above, cross_below |
| ADX | Filter only | period | >, < |
| ATR | Stop Loss | period | atr_multiple |

## API Endpoints (All prefixed with /api/v1/)
| Endpoint | Method | Auth | Rate Limit | Description |
|----------|--------|------|------------|-------------|
| /api/v1/health | GET | No | - | Health check with circuit breaker states |
| /api/v1/auth/register | POST | No | 5/min | Register new user |
| /api/v1/auth/login | POST | No | 10/min | Login, returns JWT tokens |
| /api/v1/auth/refresh | POST | No | 20/min | Refresh access token |
| /api/v1/strategy | POST | JWT | 30/min | Create strategy |
| /api/v1/strategies | GET | JWT | 30/min | List user's strategies |
| /api/v1/strategy/{id} | GET | JWT | 30/min | Get single strategy |
| /api/v1/strategy/{id} | PUT | JWT | 20/min | Update strategy |
| /api/v1/strategy/{id} | DELETE | JWT | 10/min | Delete strategy |
| /api/v1/backtest | POST | No | 5/min | Run backtest |
| /api/v1/parse-strategy | POST | No | 10/min | NL to JSON parser |
| /api/v1/explain | POST | No | 10/min | AI strategy explainer |
| /api/v1/analyze-risk | POST | No | 10/min | AI risk analyzer |
| /api/v1/analytics | GET | No | 30/min | Usage analytics |
| /api/v1/feedback | POST | No | 5/min | Submit feedback |
| /api/v1/waitlist | POST | No | 5/min | Join waitlist |

## What's Been Implemented

### Date: 2026-03-05 - API Hardening & Auth Fix (Current Session)
- Applied @limiter.limit() decorators to ALL endpoints with appropriate limits
- Applied sanitize_user_input() to all AI text inputs (parse, explain, risk)
- Wired CircuitBreaker + resilient_call for AI service calls with retry/timeout
- Added RequestIdMiddleware for request tracing
- Fixed structured JSON logging (removed duplicate logging.basicConfig)
- Set user_id in logging context for authenticated endpoints
- Fixed critical crash: analytics endpoint referenced non-existent users_db
- Fixed internal test utility to use MongoDB instead of removed in-memory stores
- Fixed ALL frontend API paths from /api/ to /api/v1/
- Fixed frontend auth: LoginPage now calls /api/v1/auth/register and /api/v1/auth/login
- Frontend now stores JWT tokens (accessToken, refreshToken) in localStorage
- DashboardPage uses Authorization: Bearer header for all API calls
- Added Stochastic indicator fields in exit conditions (was missing)
- Value field now shows for both RSI and Stochastic indicators
- Password validation on signup matches backend (8+ chars, 1 number, 1 special char)

### Earlier Features
- Full scaffold with 3 pages (Home, Login, Dashboard)
- JWT-based authentication (register, login, refresh tokens)
- Dashboard layout with sidebar navigation
- Multi-step Strategy Builder (7 steps)
- AI Strategy Explainer, NL Parser, Risk Analyzer
- Support for RSI, SMA, EMA, MACD, Stochastic, ADX, ATR indicators
- Strategy versioning and validation via indicator_registry
- Historical backtest with yfinance (SMA/EMA), simulated for others
- ATR-based stop loss
- ADX filter
- Usage analytics
- Landing page with waitlist
- MongoDB persistence for users and strategies
- User ownership enforcement on strategies

## File Structure
```
/app/
├── backend/
│   ├── .env
│   ├── auth.py             # JWT auth, user models, password hashing
│   ├── indicator_registry.py # Indicator definitions & validation
│   ├── logging_config.py   # Structured JSON logging config
│   ├── resilience.py       # CircuitBreaker, resilient_call, sanitize_user_input
│   ├── requirements.txt
│   ├── server.py           # FastAPI with all /api/v1/ routes
│   └── tests/
│       └── test_api_v1.py  # Comprehensive API tests
├── frontend/src/
│   ├── App.js
│   ├── pages/
│   │   ├── HomePage.js     # Landing page with waitlist
│   │   ├── LoginPage.js    # JWT auth (login/signup)
│   │   └── DashboardPage.js # Main dashboard with sidebar
│   ├── components/
│   │   ├── StrategyBuilder.js # 7-step strategy form (all indicators)
│   │   ├── NLStrategyInput.js # NL parser UI
│   │   └── StrategyChat.js    # AI explainer chat
│   └── utils/
│       ├── explainStrategy.js # Strategy text formatter
│       └── simulate.js
└── memory/
    └── PRD.md
```

## Prioritized Backlog

### P0 - Critical (All Done)
- [x] Basic scaffold with all pages
- [x] JWT authentication with MongoDB
- [x] Strategy Builder UI (7 steps, all indicators)
- [x] AI features (parser, explainer, risk analyzer)
- [x] MongoDB persistence
- [x] API hardening (rate limiting, sanitization, circuit breakers, logging)
- [x] Frontend JWT auth integration

### P1 - Important (Next)
- [ ] Frontend edit/delete buttons on strategy list
- [ ] Analytics dashboard UI

### P2 - Nice to Have
- [ ] Token blacklist for logout
- [ ] Password reset flow
- [ ] Caching layer for DB queries
- [ ] Expand backtest beyond SMA/EMA (currently MOCKED for other indicators)
- [ ] Strategy sharing between users
- [ ] Email integration for waitlist

## Known Limitations
- **Backtest**: Only SMA/EMA use real yfinance data; RSI/MACD/Stochastic use SIMULATED random data
- **No token blacklist**: Logout only clears localStorage, doesn't invalidate server-side tokens

## Test Reports
- `/app/test_reports/iteration_7.json` - Comprehensive e2e test (100% pass rate)
