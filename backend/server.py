"""Text2trade API — slim app factory."""
from fastapi import FastAPI, APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from pathlib import Path

# CRITICAL: Load .env BEFORE any module that reads env vars
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import os
import logging
import time
import jwt
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime, timezone
from pymongo.errors import ServerSelectionTimeoutError

from logging_config import setup_logging, generate_request_id, set_request_id, set_endpoint, log_auth_attempt
from resilience import circuit_breakers
from auth import (
    UserRegister, UserLogin, UserResponse, TokenResponse,
    RefreshRequest, AccessTokenResponse,
    ForgotPasswordRequest, ResetPasswordRequest, PasswordResetResponse,
    ChangePasswordRequest,
    register_user, login_user, refresh_access_token, users_collection,
    blacklist_token, create_password_reset_otp, reset_password_with_otp,
    change_password, get_current_user,
)
from database import (
    db, mongo_client, strategies_collection, analytics_db,
    feedback_db, waitlist_db
)
from models import HealthResponse, RootResponse

# Routers
from routers.strategies import router as strategies_router
from routers.backtest_routes import router as backtest_router
from routers.paper_trading import router as paper_trading_router
from routers.templates import router as templates_router
from routers.screener_routes import router as screener_router
from routers.ai import router as ai_router
from routers.admin import router as admin_router
from routers.optimizer import router as optimizer_router
from routers.sharing import router as sharing_router
from routers.watchlist import router as watchlist_router
from routers.leaderboard import router as leaderboard_router
from routers.tracker import router as tracker_router
from routers.alerts import router as alerts_router
from routers.account import router as account_router
from routers.diagnostics import router as diagnostics_router
from routers.legal import router as legal_router
from routers.knowledge import router as knowledge_router

# Diagnostics
from diagnostics import (
    ErrorRecord, store_error, sanitize_dict, classify_severity,
    store_slow_request,
)
from logging_config import get_request_id, get_user_id, set_user_id as set_user_id_ctx

# Setup structured logging
setup_logging(os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


# =============================================================================
# RATE LIMITER
# =============================================================================

def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return get_remote_address(request)

limiter = Limiter(key_func=get_client_ip, default_limits=["60/minute"])

def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    retry_after = exc.detail.split("per")[0].strip() if exc.detail else "later"
    return JSONResponse(
        status_code=429,
        content={"detail": f"Rate limit exceeded. Try again in {retry_after}."}
    )


# =============================================================================
# APP SETUP
# =============================================================================

app = FastAPI(title="Text2trade API", version="1.3.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)


# =============================================================================
# GLOBAL EXCEPTION HANDLER (catches ALL unhandled exceptions)
# =============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all unhandled exceptions, store in error_logs, return friendly msg."""
    import traceback as tb

    # Skip HTTP exceptions — they already have proper responses
    if isinstance(exc, HTTPException):
        raise exc

    error_type = type(exc).__name__
    stack = tb.format_exception(type(exc), exc, exc.__traceback__)
    stack_trace = "".join(stack)

    # Try to get request body for debugging (sanitized)
    request_body = None
    try:
        body_bytes = await request.body()
        if body_bytes:
            import json
            raw = json.loads(body_bytes)
            request_body = sanitize_dict(raw) if isinstance(raw, dict) else None
    except Exception:
        pass

    record = ErrorRecord(
        user_id=get_user_id(),
        endpoint=str(request.url.path),
        method=request.method,
        request_body=request_body,
        error_type=error_type,
        error_message=str(exc)[:2000],
        stack_trace=stack_trace[:10000],
        request_id=get_request_id() or "",
        severity=classify_severity(error_type),
        source="backend",
    )

    try:
        store_error(record)
    except Exception as store_err:
        logger.error(f"Failed to store error record: {store_err}")

    logger.error(f"Unhandled exception: {error_type}: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Our team has been notified."},
    )

# Base routers
api_router = APIRouter(prefix="/api/v1")
auth_router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# =============================================================================
# MIDDLEWARE
# =============================================================================

PERF_THRESHOLD_MS = 3000  # log slow requests above this
MAX_BODY_SIZE = 1 * 1024 * 1024  # 1MB

class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Reject oversized request bodies
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_BODY_SIZE:
            return JSONResponse(status_code=413, content={"detail": "Request body too large. Maximum 1MB."})

        request_id = generate_request_id()
        set_request_id(request_id)
        set_endpoint(f"{request.method} {request.url.path}")
        start_time = time.time()

        # Update last_active for authenticated users
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                token = auth_header[7:]
                payload = jwt.decode(token, os.environ.get("JWT_SECRET"), algorithms=["HS256"], options={"verify_exp": False})
                uid = payload.get("sub")
                if uid:
                    set_user_id_ctx(uid)
                    users_collection.update_one(
                        {"user_id": uid},
                        {"$set": {"last_active": datetime.now(timezone.utc).isoformat()}},
                    )
            except Exception:
                pass

        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000
        response.headers["X-Request-ID"] = request_id
        logger.info("Request completed", extra={"duration_ms": round(duration_ms, 2), "status_code": response.status_code})

        # Performance monitoring — log slow requests
        if duration_ms > PERF_THRESHOLD_MS:
            try:
                store_slow_request(
                    endpoint=request.url.path,
                    method=request.method,
                    duration_ms=duration_ms,
                    user_id=get_user_id(),
                    request_id=request_id,
                )
            except Exception:
                pass

        return response


# =============================================================================
# GENERAL ROUTES
# =============================================================================

@api_router.get("/", response_model=RootResponse)
async def root():
    return {"message": "Welcome to Text2trade API", "app_name": "Text2trade"}


APP_VERSION = os.environ.get("APP_VERSION", "0.2.0")

@api_router.get("/app/version")
async def app_version():
    """Public endpoint — returns app version info."""
    return {
        "version": APP_VERSION,
        "build_date": "2026-03-28",
        "min_supported_version": "0.2.0",
    }


# ── Diagnostics test endpoints (admin-only, for verification) ────────────────

@api_router.get("/admin/diagnostics/test/error")
async def test_force_error(request: Request, admin: dict = Depends(get_current_user)):
    """Force an unhandled exception to verify error tracking."""
    raise RuntimeError("Diagnostics test: intentional error for verification")


@api_router.get("/admin/diagnostics/test/slow")
async def test_slow_request(request: Request, admin: dict = Depends(get_current_user)):
    """Simulate a 4-second slow request for performance monitoring."""
    import asyncio
    await asyncio.sleep(4)
    return {"message": "Slow request completed", "duration_sec": 4}

@api_router.get("/health")
async def health_check():
    mongodb_healthy = False
    status = "unhealthy"
    try:
        mongo_client.admin.command('ping')
        mongodb_healthy = True
        status = "healthy"
    except ServerSelectionTimeoutError:
        logger.error("MongoDB health check failed: timeout")
    except Exception as e:
        logger.error(f"MongoDB health check failed: {e}")

    cb_states = {name: cb.state for name, cb in circuit_breakers.items()}
    if mongodb_healthy and any(state != "closed" for state in cb_states.values()):
        status = "degraded"

    # Error rate summary
    from diagnostics import error_logs as diag_error_logs
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    h1_iso = (now - timedelta(hours=1)).isoformat()
    h24_iso = (now - timedelta(hours=24)).isoformat()
    errors_1h = diag_error_logs.count_documents({"timestamp": {"$gte": h1_iso}})
    errors_24h = diag_error_logs.count_documents({"timestamp": {"$gte": h24_iso}})

    return {
        "status": status, "mongodb": mongodb_healthy,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.3.0", "circuit_breakers": cb_states,
        "error_rate": {"last_1h": errors_1h, "last_24h": errors_24h},
    }


# =============================================================================
# AUTH ROUTES
# =============================================================================

@auth_router.post("/register", response_model=UserResponse, status_code=201)
@limiter.limit("5/minute")
async def register(request: Request, body: UserRegister):
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")
    result = register_user(body, ip_address=ip)
    log_auth_attempt(result.email, True)
    logger.info(f"New user registered: {result.email}")
    return result

@auth_router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(request: Request, body: UserLogin):
    try:
        result = login_user(body)
        log_auth_attempt(body.email, True)
        logger.info(f"User logged in: {body.email}")
        return result
    except HTTPException as e:
        log_auth_attempt(body.email, False, reason=e.detail)
        raise

@auth_router.post("/refresh", response_model=AccessTokenResponse)
@limiter.limit("20/minute")
async def refresh(request: Request, body: RefreshRequest):
    return refresh_access_token(body.refresh_token)


@auth_router.post("/logout")
async def logout(request: Request):
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        blacklist_token(token)
    return {"success": True, "message": "Logged out"}


@auth_router.post("/forgot-password", response_model=PasswordResetResponse)
@limiter.limit("3/minute")
async def forgot_password(request: Request, body: ForgotPasswordRequest):
    result = await create_password_reset_otp(body.email)
    response = {"success": True, "message": "If that email exists, a 6-digit OTP has been sent."}
    if result.get("sandbox_restricted"):
        response["email_sent"] = False
        response["warning"] = "Email could not be sent (sandbox mode). Check server logs for your OTP."
    elif result.get("otp") and result.get("email_sent"):
        response["email_sent"] = True
    return response


@auth_router.post("/reset-password", response_model=PasswordResetResponse)
@limiter.limit("5/minute")
async def reset_password(request: Request, body: ResetPasswordRequest):
    reset_password_with_otp(body.email, body.otp, body.new_password)
    return {"success": True, "message": "Password reset successfully. You can now login with your new password."}


# =============================================================================
# FEEDBACK, ANALYTICS, WAITLIST
# =============================================================================

class FeedbackRequest(BaseModel):
    message: str
    email: Optional[str] = None

@api_router.post("/feedback")
@limiter.limit("5/minute")
async def submit_feedback(request: Request, body: FeedbackRequest):
    feedback_db.append({"message": body.message, "email": body.email, "timestamp": datetime.now(timezone.utc).isoformat()})
    logger.info(f"Feedback received: {body.message[:50]}...")
    return {"success": True}

@api_router.get("/analytics")
@limiter.limit("30/minute")
async def get_analytics(request: Request):
    try:
        sorted_indicators = dict(sorted(analytics_db["indicator_usage"].items(), key=lambda x: x[1], reverse=True))
        return {
            "success": True,
            "stats": {
                "strategies_created": strategies_collection.count_documents({}),
                "backtests_run": analytics_db["backtests_run"],
                "backtest_types": analytics_db["backtest_types"],
                "indicator_usage": sorted_indicators,
                "total_users": users_collection.count_documents({}),
                "total_feedback": len(feedback_db),
                "waitlist_signups": len(waitlist_db),
            }
        }
    except Exception as e:
        logger.error(f"DB error fetching analytics: {e}")
        raise HTTPException(status_code=500, detail="Database error")

class WaitlistRequest(BaseModel):
    email: str

@api_router.post("/waitlist")
@limiter.limit("5/minute")
async def join_waitlist(request: Request, body: WaitlistRequest):
    email = body.email.lower().strip()
    if email not in waitlist_db:
        waitlist_db.append(email)
        logger.info(f"Waitlist signup: {email}")
    return {"success": True, "message": "Added to waitlist"}


# =============================================================================
# INCLUDE ROUTERS
# =============================================================================

# Include feature routers into the api_router
api_router.include_router(strategies_router)
api_router.include_router(backtest_router)
api_router.include_router(paper_trading_router)
api_router.include_router(templates_router)
api_router.include_router(screener_router)
api_router.include_router(ai_router)
api_router.include_router(optimizer_router)
api_router.include_router(sharing_router)
api_router.include_router(watchlist_router)
api_router.include_router(leaderboard_router)
api_router.include_router(tracker_router)
api_router.include_router(alerts_router)
api_router.include_router(account_router)

# Diagnostics router (has its own /api/v1 prefix)
app.include_router(diagnostics_router)

# Legal router (has its own /api/v1 prefix, some endpoints public)
app.include_router(legal_router)

# Knowledge base router (has its own /api/v1 prefix, public endpoints)
app.include_router(knowledge_router)


# =============================================================================
# STARTUP
# =============================================================================

@app.on_event("startup")
async def startup_validation():
    try:
        from data.service import market_data_collection
        count = market_data_collection.count_documents({})
        if count == 0:
            logger.warning(
                "No market data found. Backtesting will not work. "
                "Run: python scripts/setup_data_source.py && python scripts/ingest_data.py"
            )
        else:
            symbols = len(market_data_collection.distinct("symbol"))
            logger.info(f"Market data loaded: {count:,} candles across {symbols} symbols")
            from datetime import timedelta, timezone as tz
            cutoff = datetime.now(tz.utc) - timedelta(days=7)
            latest = market_data_collection.find_one(
                {"timeframe": "1d"}, {"_id": 0, "timestamp": 1}, sort=[("timestamp", -1)]
            )
            if latest and latest["timestamp"].replace(tzinfo=tz.utc) < cutoff:
                logger.warning("Market data is stale (>5 trading days old). Run: python scripts/refresh_data.py")
    except Exception as e:
        logger.warning(f"Startup data validation failed: {e}")


# =============================================================================
# FINALIZE
# =============================================================================

app.add_middleware(BaseHTTPMiddleware, dispatch=RequestIdMiddleware(app).dispatch)

app.include_router(api_router)
app.include_router(auth_router)
app.include_router(admin_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('ALLOWED_ORIGINS', os.environ.get('CORS_ORIGINS', '*')).split(','),
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

logger.info("Text2trade API initialized (modular routers)")
