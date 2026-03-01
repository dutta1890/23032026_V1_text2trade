# Text2trade - Product Requirements Document

## Overview
Text2trade is a trading strategy builder platform with AI-powered features for parsing, explaining, and analyzing trading strategies.

## Original Problem Statement
Build a full-stack web app called Text2trade with:
- Home page, Login page, Dashboard with sidebar navigation
- Strategy Builder UI with multi-step form
- AI features: Natural Language Parser, Strategy Explainer, Risk Analyzer
- Support for multiple indicators: RSI, SMA, EMA, MACD, Stochastic, ADX (filter)

## Architecture
- **Frontend**: React (CRA with Craco) + TailwindCSS + Shadcn UI
- **Backend**: FastAPI (Python)
- **Database**: In-memory (volatile - resets on restart)
- **AI**: OpenAI GPT-5.2 via Emergent LLM Key
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
| Stochastic | Entry/Exit | k_period, d_period, overbought, oversold | cross_above, cross_below |
| ADX | Filter only | period | >, < |

## What's Been Implemented

**Date: 2026-03-01 - ADX Filter Feature**
- Added ADX indicator as filter-only in `indicator_registry.py`
- Added Filters step (step 6 of 7) in StrategyBuilder
- ADX filter UI: Period, Operator (>/< only), Value inputs
- Backend validation: Uses `validate_condition` from indicator_registry.py
- `explainStrategy.js` formats ADX filters correctly

**Earlier Features**
- Full scaffold with 3 pages (Home, Login, Dashboard)
- In-memory authentication (signup/login)
- Dashboard layout with sidebar navigation
- Multi-step Strategy Builder (7 steps)
- AI Strategy Explainer (`/api/explain`)
- AI Natural Language Parser (`/api/parse-strategy`)
- AI Risk Analyzer (`/api/analyze-risk`)
- Support for RSI, SMA, EMA, MACD, Stochastic indicators
- Strategy versioning and validation

## File Structure
```
/app/
├── backend/
│   ├── server.py             # FastAPI with all endpoints
│   ├── indicator_registry.py # Indicator definitions & validation
│   └── ai_utils.py           # AI helper functions
├── frontend/src/
│   ├── App.js                # Main routing
│   ├── pages/
│   │   ├── HomePage.js
│   │   ├── LoginPage.js
│   │   └── DashboardPage.js  # Main dashboard with sidebar
│   ├── components/
│   │   ├── StrategyBuilder.js # 7-step strategy form
│   │   ├── NLStrategyInput.js # NL parser UI
│   │   └── StrategyChat.js    # AI explainer chat
│   └── utils/
│       ├── explainStrategy.js # Strategy text formatter
│       └── simulate.js        # MOCKED: Fake backtest
└── memory/
    └── PRD.md
```

## API Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/health | GET | Health check |
| /api/signup | POST | Create user (in-memory) |
| /api/login | POST | Authenticate user |
| /api/strategy | POST | Create strategy |
| /api/strategies | GET | List all strategies |
| /api/parse-strategy | POST | NL to JSON parser |
| /api/explain | POST | AI strategy explainer |
| /api/analyze-risk | POST | AI risk analyzer |
| /api/feedback | POST | Submit feedback |

## Prioritized Backlog

### P0 - Critical (Done)
- [x] Basic scaffold with all pages
- [x] In-memory authentication
- [x] Strategy Builder UI (7 steps)
- [x] All indicators: RSI, SMA, EMA, MACD, Stochastic
- [x] ADX filter support
- [x] AI features (parser, explainer, risk analyzer)

### P1 - Important (Next)
- [ ] Persist data to MongoDB
- [ ] Single-strategy endpoints (GET/PUT/DELETE by ID)
- [ ] User ownership for strategies

### P2 - Nice to Have
- [ ] Real backtesting engine (currently mocked)
- [ ] Session management (remember me, timeouts)
- [ ] WebSocket for real-time data
- [ ] More indicators as needed

## Known Limitations
- **In-memory storage**: All data resets on server restart
- **Mocked simulation**: `simulate.js` generates random data
- **No user ownership**: All users see all strategies

## Test Reports
- `/app/test_reports/iteration_4.json` - ADX feature tests (100% pass)
