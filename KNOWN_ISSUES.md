# Known Issues — Text2trade

Last Updated: 2026-03-21

## Resolved Issues (This Sprint)

### Bug #1: Admin strategy_count always 0
- **Root Cause**: Admin `/users` endpoint queried `strategies_collection` by `email`, but strategies store `user_id` as UUID
- **Fix**: Changed query to use `user_id` from user document
- **File**: `/app/backend/routers/admin.py`
- **Status**: FIXED & VERIFIED

## Minor / Non-blocking

### HTML hydration warning (Admin Users table)
- **Severity**: Low — cosmetic console warning only
- **Impact**: None — table renders correctly
- **Details**: React dev-mode warning about table structure hydration. Only appears in dev mode, not in production builds.

## No Open Critical or High-Priority Issues
All system tests pass. See `/app/test_reports/` for detailed results.
