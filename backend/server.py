"""Text2trade API — slim app factory."""
from fastapi import FastAPI, APIRouter, HTTPException, Request
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
    register_user, login_user, refresh_access_token, users_collection,
    blacklist_token, create_password_reset_token, reset_password_with_token
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

app = FastAPI(title="Text2trade API", version="1.2.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)

# Base routers
api_router = APIRouter(prefix="/api/v1")
auth_router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# =============================================================================
# MIDDLEWARE
# =============================================================================

class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = generate_request_id()
        set_request_id(request_id)
        set_endpoint(f"{request.method} {request.url.path}")
        start_time = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000
        response.headers["X-Request-ID"] = request_id
        logger.info("Request completed", extra={"duration_ms": round(duration_ms, 2), "status_code": response.status_code})
        return response


# =============================================================================
# GENERAL ROUTES
# =============================================================================

@api_router.get("/", response_model=RootResponse)
async def root():
    return {"message": "Welcome to Text2trade API", "app_name": "Text2trade"}

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

    return {
        "status": status, "mongodb": mongodb_healthy,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.2.0", "circuit_breakers": cb_states
    }


# =============================================================================
# AUTH ROUTES
# =============================================================================

@auth_router.post("/register", response_model=UserResponse, status_code=201)
@limiter.limit("5/minute")
async def register(request: Request, body: UserRegister):
    result = register_user(body)
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
    token = create_password_reset_token(body.email)
    # Always return success (don't reveal if email exists)
    # In production, send the token via email. For now, return it directly.
    return {"success": True, "message": "If that email exists, a reset link has been generated.", "reset_token": token}


@auth_router.post("/reset-password", response_model=PasswordResetResponse)
@limiter.limit("5/minute")
async def reset_password(request: Request, body: ResetPasswordRequest):
    reset_password_with_token(body.token, body.new_password)
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
