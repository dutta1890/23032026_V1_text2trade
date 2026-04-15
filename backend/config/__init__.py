"""SEBI compliance configuration — runtime flags for regulatory requirements."""

import os

HOSTING_REGION = os.environ.get("HOSTING_REGION", "unknown")

SEBI_COMPLIANCE = {
    "static_ip_required": True,
    "ops_threshold": 10,
    "audit_retention_years": 5,
    "daily_session_logout": True,
    "hosting_region": HOSTING_REGION,
    "oauth_required": True,
    "two_factor_required": True,
    "algo_id_required_for_live": True,
}

COMPLIANCE_STATUS = {
    "framework": "SEBI Retail Algo Trading Framework 2025-26",
    "circular": "SEBI/HO/MIRSD/MIRSD-PoD/P/2025/0000013",
    "compliance_status": "partial",
    "live_trading": "not_available",
    "audit_trail": "active",
    "data_retention": "5_years",
    "hosting_region": HOSTING_REGION,
    "hosting_migration_required": HOSTING_REGION != "india",
    "algo_registration": "not_applicable_until_live",
    "static_ip": "not_applicable_until_live",
    "strategy_type": "white_box_only",
    "note": (
        "Strategy creation, backtesting, and paper trading are fully operational. "
        "Live execution with broker integration and full SEBI compliance is planned for Phase 2."
    ),
}
