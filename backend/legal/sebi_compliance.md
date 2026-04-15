# SEBI Compliance Documentation

## Applicable Regulation
- **SEBI Circular**: SEBI/HO/MIRSD/MIRSD-PoD/P/2025/0000013
- **Title**: "Safer participation of retail investors in Algorithmic trading"
- **Effective**: April 1, 2026

## Platform Classification
- **Platform Type**: Algo Strategy Builder (creation + backtesting + paper trading)
- **Live Execution**: Not currently available (Phase 2)
- **Strategy Type**: White-box only (all logic visible to users)
- **Algo Provider Status**: Pre-empanelment (will empanel before live execution launch)

## Current Compliance Status

### Fully Compliant
- **Audit trail**: All user actions logged with 5-year retention (MongoDB `audit_trail` collection, no TTL index)
- **Strategy transparency**: All strategies are white-box with full logic disclosure; users create strategies via AI-guided chat and can inspect every entry/exit condition, indicator parameter, and risk control
- **Investor education**: Built-in knowledge base with 30+ trading terms, inline InfoTooltip explanations, and a searchable `/glossary` page
- **Data security**: Encrypted password storage (bcrypt), JWT authentication, input sanitization (XSS stripping), rate limiting (slowapi), request body size limits
- **Error tracking**: Global exception handler, structured logging, admin diagnostics dashboard
- **Legal documentation**: Terms of Service, Privacy Policy, Risk Disclaimer, Cookie Policy — all with versioned consent tracking and re-consent gates

### Planned for Phase 2 (before live execution)
- Exchange-assigned Algo-IDs for every strategy (`algo_id` field in strategy schema already prepared)
- Static IP infrastructure for API trading
- Broker OAuth integration with 2FA (Zerodha, Angel One, Upstox)
- OPS threshold enforcement (10 orders/second limit) — monitoring framework already active
- Daily session auto-logout before pre-open (script ready at `scripts/daily_session_cleanup.py`)
- Formal empanelment with stock exchanges as algo provider
- Broker partnership with due diligence completion
- SEBI RA registration (only if marketplace with hidden logic is added — black-box strategies)

### Not Applicable
- **HFT regulations**: Platform is not designed for high-frequency trading
- **Co-location services**: Retail-focused platform
- **Direct market access**: All orders will route through registered broker APIs

## Architecture for Compliance

### Audit Trail
- **Collection**: `audit_trail` in MongoDB
- **Retention**: No TTL index; data retained for 5+ years minimum
- **Immutability**: Write-only; no update or delete endpoints exist
- **Coverage**: 18+ action types covering registration, login, logout, strategy CRUD, backtest execution, paper trading, AI interactions, profile changes, and template cloning
- **Traceability**: Every entry includes user_id, IP address, user-agent, request_id, and UTC timestamp with millisecond precision

### Algo-ID Architecture
- Every strategy has `algo_id` (null until Phase 2), `algo_registered` (bool), `algo_registration_date`, and `algo_version` fields
- Live trade execution is **blocked** if `algo_id` is null — enforced at API level
- On significant strategy logic changes, `algo_version` increments, requiring re-registration with the exchange

### OPS Monitoring
- Orders per second tracked per user per exchange
- SEBI threshold: 10 OPS
- Warnings logged when paper trading exceeds threshold
- Admin dashboard shows users approaching limits

### Strategy Classification
- Default: `white_box` with `logic_disclosed=True`
- If marketplace with hidden logic is added in future → `black_box` → requires RA registration
- Classification enforced at strategy creation time

## Hosting
- Application designed for Indian server deployment
- Data stored in Indian data center (production deployment)
- No cross-border data transfer of user trading data

## Grievance Handling (Phase 2)
- Dedicated grievance officer to be appointed before live execution launch
- Escalation matrix to be published on website
- SEBI SCORES integration for complaint tracking

---

*This document serves as the compliance reference for broker partnerships, investor discussions, and regulatory inquiries.*

*Last updated: March 2026*
