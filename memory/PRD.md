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

### Session 37 (2026-04-15) — Reproducible Backtests (7 Tasks)
- **Task 1: Immutable Backtest Snapshots** — `backtest_snapshots` collection with `snapshot_id` (UUID), full strategy JSON, trades, equity curve, metrics, data hash. Write-only (no update/delete). Every successful backtest creates a snapshot. Public URL: `/backtest/snapshot/{id}`
- **Task 2: Strategy Versioning** — `strategy_versions` collection. Integer version auto-incremented on strategy update. Old version snapshot saved before each edit with `changed_fields`. Version history accessible via `GET /api/v1/strategy/{id}/versions`. UI shows version timeline on strategy detail page.
- **Task 3: Data Snapshot Hashing** — SHA-256 hash of OHLCV data computed before every backtest. Stored with snapshot. Same hash = guaranteed identical data. Hash visible in backtest results UI.
- **Task 4: "Verify This Backtest" Export** — ZIP download at `GET /api/v1/backtest/snapshot/{id}/verify`. Contains: `strategy.json`, `backtest_params.json`, `data_used.csv` (actual OHLCV candles), `expected_results.json`, `README.txt`. Download button on both BacktestPage and public snapshot page.
- **Task 5: Backtest Comparison Tool** — `/backtest/compare?a=X&b=Y` page. Side-by-side metrics diff with color-coded deltas (green/red). Shows Same Data / Different Data and Same Engine / Different Engine badges. API: `GET /api/v1/backtest/compare-snapshots?a=X&b=Y`
- **Task 6: Permanent Backtest URLs** — Public `/backtest/snapshot/{id}` page shows full backtest result (metrics, equity curve, trade log) without auth. "Permanent Link" copy button on backtest results page. "Immutable" badge on snapshot page.
- **Task 7: Engine Version Changelog** — `legal/engine_changelog.md` with v0.1.0 and v0.2.0 entries. Version tracked in every backtest result.
- **Bug Fix: Infinite loop in BacktestPage.js** — Memoized useApi return object to prevent useCallback re-creation loop.
- **Testing**: 30/30 backend tests, all frontend pages verified (iteration_37)

### Session 36 (2026-04-15) — Engine Benchmarks & Lookahead Bias Audit
- Lookahead Bias Audit: NO LOOKAHEAD BIAS DETECTED
- 12 Anti-Cheat Tests: all passing
- 10 Benchmark Strategies: all 10/10 PASS
- Public `/benchmarks` page, Admin dashboard ENGINE BENCHMARKS section

### Previous Sessions (Summary)
- Sessions 10-26c: Full platform — AI strategy builder, backtesting, paper trading, screener, optimizer, tracker, alerts, watchlist, templates, sharing, leaderboard, demo mode, onboarding, legal compliance, diagnostics, session hardening, data export, SEBI compliance, knowledge base, code quality refactor

## New Routes Added
| Route | Auth | Component | Description |
|-------|------|-----------|-------------|
| /backtest/snapshot/:snapshotId | No | BacktestSnapshotPage | Public immutable backtest viewer |
| /backtest/compare | No | BacktestComparePage | Side-by-side snapshot comparison |

## New API Endpoints
| Endpoint | Auth | Description |
|----------|------|-------------|
| GET /api/v1/backtest/snapshot/{id} | No | Public snapshot retrieval |
| GET /api/v1/backtest/snapshot/{id}/verify | No | ZIP download for verification |
| GET /api/v1/backtest/compare-snapshots?a=X&b=Y | No | Metrics comparison |
| GET /api/v1/backtest/snapshots | User | List user's snapshots |
| GET /api/v1/strategy/{id}/versions | User | Strategy version history |

## New MongoDB Collections
- `backtest_snapshots` — immutable backtest records (snapshot_id unique index)
- `strategy_versions` — strategy change history (strategy_id + version compound unique index)

## Remaining Backlog
- **CI Trigger Documentation (P2)**: Update `DEPLOYMENT.md` with release-check instructions
- **Broker Integrations (P1)**: Zerodha, Angel One, Upstox, Dhan — UI placeholders exist
- **Scheduled Auto-Evaluation (P2)**: Auto alert checks post-backtest
- **Verified Domain Email**: Switch from Resend sandbox to full delivery

## Credentials
- Test user: `testai@example.com` / `Password123!`
- Admin: `admin@example.com` / `Password123!`
- Market data: 7 symbols (RELIANCE, TCS, INFY, HDFCBANK, ICICIBANK, ITC, HINDUNILVR)
