from fastapi import FastAPI, APIRouter, HTTPException, Header, Depends, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from pathlib import Path

# CRITICAL: Load .env BEFORE any module that reads env vars
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import os
import logging
from pydantic import BaseModel, EmailStr
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
import uuid
import json
import time
from emergentintegrations.llm.chat import LlmChat, UserMessage
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

from indicator_registry import validate_condition
from auth import (
    UserRegister, UserLogin, UserResponse, TokenResponse, 
    RefreshRequest, AccessTokenResponse,
    register_user, login_user, refresh_access_token,
    get_current_user, get_admin_user, users_collection
)
from resilience import (
    sanitize_user_input, resilient_call, resilient_call_sync,
    circuit_breakers, ServiceTimeoutError, ServiceUnavailableError
)
from logging_config import (
    setup_logging, generate_request_id, set_request_id, set_user_id, set_endpoint,
    get_request_id, log_auth_attempt, log_ai_call
)
from ai_sessions import (
    get_ai_config, check_and_increment_usage, get_usage_stats,
    create_session, get_session, append_message, update_strategy_draft,
    delete_session, get_context_messages
)


# Setup structured logging
setup_logging(os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Rate limiter with global default - use X-Forwarded-For for proxied environments
def get_client_ip(request: Request) -> str:
    """Get real client IP from X-Forwarded-For header or fall back to remote address."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return get_remote_address(request)

limiter = Limiter(key_func=get_client_ip, default_limits=["60/minute"])

# Custom 429 handler
def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    retry_after = exc.detail.split("per")[0].strip() if exc.detail else "later"
    return JSONResponse(
        status_code=429,
        content={"detail": f"Rate limit exceeded. Try again in {retry_after}."}
    )

# MongoDB connection
mongo_client = MongoClient(os.environ.get("MONGO_URL"), serverSelectionTimeoutMS=5000)
db = mongo_client[os.environ.get("DB_NAME", "text2trade")]
strategies_collection = db["strategies"]

# Create indexes
try:
    strategies_collection.create_index("user_id")
    strategies_collection.create_index("metadata.created_at")
except Exception as e:
    logger.warning(f"Could not create indexes: {e}")

app = FastAPI(title="Text2trade API", version="1.1.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)

# Routers
api_router = APIRouter(prefix="/api/v1")
auth_router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

feedback_db: List[dict] = []
waitlist_db: List[str] = []


# =============================================================================
# REQUEST ID MIDDLEWARE
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

# Analytics tracking
analytics_db = {
    "strategies_created": 0,
    "backtests_run": 0,
    "indicator_usage": {},
    "backtest_types": {"historical": 0}
}

def track_indicator(indicator_name: str):
    """Track indicator usage."""
    if indicator_name not in analytics_db["indicator_usage"]:
        analytics_db["indicator_usage"][indicator_name] = 0
    analytics_db["indicator_usage"][indicator_name] += 1


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str

class RootResponse(BaseModel):
    message: str
    app_name: str


# =============================================================================
# STRATEGY MODELS (with strict validation)
# =============================================================================

from pydantic import Field, field_validator, ConfigDict
from typing import Literal

# Valid operators from indicator registry
VALID_OPERATORS = Literal[
    "<", ">", ">=", "<=", "==",
    "cross_above", "cross_below", "crosses_above", "crosses_below",
    "bullish_cross", "bearish_cross",
    "atr_multiple",
    "buy_signal", "sell_signal",
    "upper_touch", "lower_touch",
    "above_r1", "below_s1", "above_r2", "below_s2"
]

class IndicatorCondition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    name: str = Field(max_length=50)
    params: Dict[str, Any] = Field(default_factory=dict)
    operator: VALID_OPERATORS
    value: Optional[Union[float, str]] = Field(default=None)
    
    @field_validator("name", "operator", mode="before")
    @classmethod
    def strip_strings(cls, v):
        return v.strip() if isinstance(v, str) else v
    
    @field_validator("value")
    @classmethod
    def validate_value(cls, v):
        if isinstance(v, (int, float)) and (v < -10000 or v > 10000):
            raise ValueError("Value must be between -10000 and 10000")
        return v

class Metadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    tags: List[str] = Field(default_factory=list, max_length=10)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    @field_validator("name", "description", mode="before")
    @classmethod
    def strip_strings(cls, v):
        return v.strip() if isinstance(v, str) else v

class Market(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    type: str = Field(max_length=50)
    exchange: Optional[str] = Field(default=None, max_length=50)
    
    @field_validator("type", "exchange", mode="before")
    @classmethod
    def strip_strings(cls, v):
        return v.strip() if isinstance(v, str) else v

class Instrument(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    symbol: str = Field(min_length=1, max_length=20)
    base: Optional[str] = Field(default=None, max_length=10)
    quote: Optional[str] = Field(default=None, max_length=10)
    
    @field_validator("symbol", "base", "quote", mode="before")
    @classmethod
    def strip_and_upper(cls, v):
        return v.strip().upper() if isinstance(v, str) else v

class Timeframe(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    interval: str = Field(max_length=10)
    candle_count: Optional[int] = Field(default=None, ge=1, le=1000)
    
    @field_validator("interval", mode="before")
    @classmethod
    def strip_strings(cls, v):
        return v.strip() if isinstance(v, str) else v

class StopLoss(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["percentage", "points", "atr_multiple"] = "percentage"
    value: float = Field(ge=0.1, le=50)

class TrailingStopLoss(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = False
    type: Literal["percentage", "points"] = "percentage"
    value: float = Field(ge=0.1, le=20, default=1.0)
    activation_profit: float = Field(ge=0, le=50, default=0)

class TargetProfit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["percentage", "points"] = "percentage"
    value: float = Field(ge=0.1, le=100)

class TimeBasedExit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = False
    exit_time: str = Field(default="15:10", pattern=r"^\d{2}:\d{2}$")

class DailyLimits(BaseModel):
    model_config = ConfigDict(extra="forbid")
    max_loss_per_day: float = Field(ge=0, le=100, default=5.0)
    max_trades_per_day: int = Field(ge=1, le=50, default=10)

class PositionSizing(BaseModel):
    model_config = ConfigDict(extra="forbid")
    method: Literal["fixed_quantity", "percent_capital", "risk_per_trade"] = "fixed_quantity"
    value: float = Field(ge=0.1, le=100, default=1)

class RiskManagement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    stop_loss: Optional[StopLoss] = None
    trailing_stop_loss: TrailingStopLoss = Field(default_factory=TrailingStopLoss)
    target_profit: Optional[TargetProfit] = None
    time_based_exit: TimeBasedExit = Field(default_factory=TimeBasedExit)
    daily_limits: DailyLimits = Field(default_factory=DailyLimits)
    position_sizing: PositionSizing = Field(default_factory=lambda: PositionSizing(method="fixed_quantity", value=1))

class Strategy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    id: Optional[str] = Field(default=None, max_length=50)
    version: str = Field(default="1.0", max_length=10)
    user_id: Optional[str] = Field(default=None, max_length=50)
    metadata: Metadata
    market: Market
    instrument: Instrument
    timeframe: Timeframe
    entry_conditions: List[IndicatorCondition] = Field(default_factory=list, max_length=10)
    exit_conditions: List[IndicatorCondition] = Field(default_factory=list, max_length=10)
    filters: List[IndicatorCondition] = Field(default_factory=list, max_length=5)
    risk_management: RiskManagement

class StrategyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    success: bool
    strategy: Strategy

class StrategiesListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    success: bool
    strategies: List[Strategy]
    count: int


# =============================================================================
# GENERAL ROUTES
# =============================================================================

@api_router.get("/", response_model=RootResponse)
async def root():
    return {"message": "Welcome to Text2trade API", "app_name": "Text2trade"}

@api_router.get("/health")
async def health_check():
    """Health check endpoint with MongoDB status."""
    mongodb_healthy = False
    status = "unhealthy"
    
    try:
        # Ping MongoDB
        mongo_client.admin.command('ping')
        mongodb_healthy = True
        status = "healthy"
    except ServerSelectionTimeoutError:
        logger.error("MongoDB health check failed: timeout")
    except Exception as e:
        logger.error(f"MongoDB health check failed: {e}")
    
    # Check circuit breakers for degraded state
    cb_states = {name: cb.state for name, cb in circuit_breakers.items()}
    if mongodb_healthy and any(state != "closed" for state in cb_states.values()):
        status = "degraded"
    
    return {
        "status": status,
        "mongodb": mongodb_healthy,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.1.0",
        "circuit_breakers": cb_states
    }


# =============================================================================
# AUTH ROUTES (JWT-based)
# =============================================================================

@auth_router.post("/register", response_model=UserResponse, status_code=201)
@limiter.limit("5/minute")
async def register(request: Request, body: UserRegister):
    """Register a new user."""
    result = register_user(body)
    log_auth_attempt(result.email, True)
    logger.info(f"New user registered: {result.email}")
    return result

@auth_router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(request: Request, body: UserLogin):
    """Login and get access + refresh tokens."""
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
    """Refresh access token using refresh token."""
    return refresh_access_token(body.refresh_token)


# =============================================================================
# STRATEGY ROUTES
# =============================================================================

def validate_strategy(strategy: Strategy):
    errors = []
    
    # At least one entry condition required
    if not strategy.entry_conditions:
        errors.append("At least one entry condition is required")
    
    # Timeframe required
    if not strategy.timeframe or not strategy.timeframe.interval:
        errors.append("Timeframe is required")
    
    rm = strategy.risk_management
    if rm:
        # Trailing SL requires base SL
        if rm.trailing_stop_loss and rm.trailing_stop_loss.enabled and rm.stop_loss is None:
            errors.append("Trailing stop loss requires a base stop loss")
        
        # risk_per_trade requires SL
        if rm.position_sizing and rm.position_sizing.method == "risk_per_trade" and rm.stop_loss is None:
            errors.append("risk_per_trade position sizing requires a stop loss")
        
        # Time exit warns if not intraday
        if rm.time_based_exit and rm.time_based_exit.enabled:
            tf = strategy.timeframe.interval if strategy.timeframe else ""
            if tf in ("1d", "1wk", "1mo"):
                errors.append("Time-based exit is only meaningful for intraday timeframes")
    
    # Validate conditions against indicator registry
    for cond in strategy.entry_conditions:
        if not validate_condition(cond.model_dump()):
            errors.append(f"Invalid entry condition: {cond.name}")
    for cond in strategy.exit_conditions:
        if not validate_condition(cond.model_dump()):
            errors.append(f"Invalid exit condition: {cond.name}")
    for cond in strategy.filters:
        if not validate_condition(cond.model_dump()):
            errors.append(f"Invalid filter: {cond.name}")
    
    return errors

def get_next_version(name: str, user_id: str) -> str:
    existing = list(strategies_collection.find(
        {"metadata.name": name, "user_id": user_id},
        {"version": 1, "_id": 0}
    ))
    if not existing:
        return "1.0"
    versions = [float(s.get("version", "1.0")) for s in existing]
    return str(max(versions) + 1.0)

@api_router.post("/strategy", response_model=StrategyResponse)
@limiter.limit("30/minute")
async def create_strategy(request: Request, strategy: Strategy, current_user: dict = Depends(get_current_user)):
    set_user_id(current_user.get("email", ""))
    errors = validate_strategy(strategy)
    if errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))
    
    try:
        user_id = current_user["user_id"]
        strategy.id = str(uuid.uuid4())
        strategy.user_id = user_id
        strategy.version = get_next_version(strategy.metadata.name, user_id)
        strategy.metadata.created_at = datetime.now(timezone.utc).isoformat()
        strategy.metadata.updated_at = strategy.metadata.created_at
        
        doc = strategy.model_dump()
        strategies_collection.insert_one(doc)
        
        # Track analytics
        analytics_db["strategies_created"] += 1
        for cond in strategy.entry_conditions:
            track_indicator(cond.name)
        for cond in strategy.exit_conditions:
            track_indicator(cond.name)
        for f in strategy.filters:
            track_indicator(f.name)
        
        logger.info(f"Strategy created: {strategy.id} - {strategy.metadata.name} v{strategy.version} (user: {user_id})")
        return {"success": True, "strategy": strategy}
    except Exception as e:
        logger.error(f"DB error creating strategy: {e}")
        raise HTTPException(status_code=500, detail="Database error")

@api_router.get("/strategies", response_model=StrategiesListResponse)
@limiter.limit("30/minute")
async def get_strategies(request: Request, current_user: dict = Depends(get_current_user)):
    set_user_id(current_user.get("email", ""))
    try:
        user_id = current_user["user_id"]
        user_strategies = list(strategies_collection.find(
            {"user_id": user_id},
            {"_id": 0}
        ))
        return {
            "success": True,
            "strategies": user_strategies,
            "count": len(user_strategies)
        }
    except Exception as e:
        logger.error(f"DB error fetching strategies: {e}")
        raise HTTPException(status_code=500, detail="Database error")

@api_router.get("/strategy/{strategy_id}")
@limiter.limit("30/minute")
async def get_strategy(request: Request, strategy_id: str, current_user: dict = Depends(get_current_user)):
    set_user_id(current_user.get("email", ""))
    try:
        user_id = current_user["user_id"]
        strategy = strategies_collection.find_one({"id": strategy_id}, {"_id": 0})
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        if strategy.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        return {"success": True, "strategy": strategy}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"DB error fetching strategy: {e}")
        raise HTTPException(status_code=500, detail="Database error")

@api_router.put("/strategy/{strategy_id}")
@limiter.limit("20/minute")
async def update_strategy(request: Request, strategy_id: str, strategy: Strategy, current_user: dict = Depends(get_current_user)):
    set_user_id(current_user.get("email", ""))
    try:
        user_id = current_user["user_id"]
        existing = strategies_collection.find_one({"id": strategy_id}, {"_id": 0})
        if not existing:
            raise HTTPException(status_code=404, detail="Strategy not found")
        if existing.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        errors = validate_strategy(strategy)
        if errors:
            raise HTTPException(status_code=400, detail="; ".join(errors))
        
        # Increment version
        old_version = existing.get("version", "1.0")
        try:
            major, minor = old_version.split(".")
            new_version = f"{major}.{int(minor) + 1}"
        except:
            new_version = "1.1"
        
        strategy.id = strategy_id
        strategy.user_id = user_id
        strategy.version = new_version
        strategy.metadata.updated_at = datetime.now(timezone.utc).isoformat()
        strategy.metadata.created_at = existing.get("metadata", {}).get("created_at")
        
        doc = strategy.model_dump()
        strategies_collection.replace_one({"id": strategy_id}, doc)
        logger.info(f"Strategy updated: {strategy_id} v{new_version} (user: {user_id})")
        return {"success": True, "strategy": strategy}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"DB error updating strategy: {e}")
        raise HTTPException(status_code=500, detail="Database error")

@api_router.delete("/strategy/{strategy_id}")
@limiter.limit("10/minute")
async def delete_strategy(request: Request, strategy_id: str, current_user: dict = Depends(get_current_user)):
    set_user_id(current_user.get("email", ""))
    try:
        user_id = current_user["user_id"]
        existing = strategies_collection.find_one({"id": strategy_id}, {"_id": 0})
        if not existing:
            raise HTTPException(status_code=404, detail="Strategy not found")
        if existing.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        strategies_collection.delete_one({"id": strategy_id})
        logger.info(f"Strategy deleted: {strategy_id} (user: {user_id})")
        return {"success": True, "message": "Strategy deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"DB error deleting strategy: {e}")
        raise HTTPException(status_code=500, detail="Database error")


# =============================================================================
# FEEDBACK ROUTE
# =============================================================================

class FeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(max_length=500)
    email: Optional[str] = Field(default=None, max_length=100)

class FeedbackResponse(BaseModel):
    success: bool

@api_router.post("/feedback", response_model=FeedbackResponse)
@limiter.limit("5/minute")
async def submit_feedback(request: Request, body: FeedbackRequest):
    feedback_db.append({
        "message": body.message,
        "email": body.email,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    logger.info(f"Feedback received: {body.message[:50]}...")
    return {"success": True}


# =============================================================================
# ANALYTICS ROUTE
# =============================================================================

@api_router.get("/analytics")
@limiter.limit("30/minute")
async def get_analytics(request: Request):
    """Get product usage analytics."""
    try:
        sorted_indicators = dict(sorted(
            analytics_db["indicator_usage"].items(),
            key=lambda x: x[1],
            reverse=True
        ))
        
        return {
            "success": True,
            "stats": {
                "strategies_created": strategies_collection.count_documents({}),
                "backtests_run": analytics_db["backtests_run"],
                "backtest_types": analytics_db["backtest_types"],
                "indicator_usage": sorted_indicators,
                "total_users": users_collection.count_documents({}),
                "total_feedback": len(feedback_db),
                "waitlist_signups": len(waitlist_db)
            }
        }
    except Exception as e:
        logger.error(f"DB error fetching analytics: {e}")
        raise HTTPException(status_code=500, detail="Database error")


# =============================================================================
# WAITLIST ROUTE
# =============================================================================

class WaitlistRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(max_length=100)

@api_router.post("/waitlist")
@limiter.limit("5/minute")
async def join_waitlist(request: Request, body: WaitlistRequest):
    """Add email to waitlist."""
    email = body.email.lower().strip()
    if email not in waitlist_db:
        waitlist_db.append(email)
        logger.info(f"Waitlist signup: {email}")
    return {"success": True, "message": "Added to waitlist"}


# =============================================================================
# NL PARSER ROUTE
# =============================================================================

PARSER_PROMPT = """You extract structured trading strategy data.

Supported indicators (15 total):
- RSI: params { "period": int }, value 0-100, operators: <, >, cross_above, cross_below
- SMA: params { "short": int, "long": int }, operators: crosses_above, crosses_below
- EMA: params { "short": int, "long": int }, operators: crosses_above, crosses_below
- MACD: params { "fast": int, "slow": int, "signal": int }, operators: bullish_cross, bearish_cross
- Stochastic: params { "k_period": int, "d_period": int }, operators: cross_above, cross_below
- Bollinger: params { "period": int, "std_dev": int }, operators: upper_touch, lower_touch
- ADX: params { "period": int }, operators: >, <
- ATR: params { "period": int }, operators: >, <
- Supertrend: params { "period": int, "multiplier": float }, operators: buy_signal, sell_signal
- VWAP: no params, operators: >, <, cross_above, cross_below (price vs VWAP)
- PivotPoints: params { "method": "standard"|"fibonacci"|"woodie" }, operators: above_r1, below_s1, above_r2, below_s2
- PSAR: params { "af_start": float, "af_max": float }, operators: >, <, cross_above, cross_below
- CCI: params { "period": int }, value threshold, operators: >, <, cross_above, cross_below
- WilliamsR: params { "period": int }, value -100 to 0, operators: >, <, cross_above, cross_below
- OBV: no params, operators: >, <

Common patterns:
- "Golden cross" = SMA with operator crosses_above
- "Death cross" = SMA with operator crosses_below
- "MACD bullish" = MACD with operator bullish_cross
- "Stochastic oversold" = Stochastic cross_above with value 20
- "Supertrend buy" = Supertrend with operator buy_signal
- "Price above VWAP" = VWAP with operator >
- "Bollinger squeeze" = Bollinger lower_touch (entry) + upper_touch (exit)

Return ONLY valid JSON:

{
  "entry_conditions": [],
  "exit_conditions": [],
  "filters": [],
  "risk_management": { "stop_loss": null, "take_profit": null }
}

Rules:
- Only use the 15 indicators listed above. Ignore unsupported indicators.
- Extract only explicitly mentioned values.
- Do not guess missing numbers.
- Do not explain or add text outside JSON."""

class ParseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(max_length=2000)

class ParseResponse(BaseModel):
    success: bool
    parsed: Optional[dict] = None
    error: Optional[str] = None

@api_router.post("/parse-strategy", response_model=ParseResponse)
@limiter.limit("10/minute")
async def parse_strategy(request: Request, body: ParseRequest, current_user: dict = Depends(get_current_user)):
    user_email = current_user.get("email", "anonymous")
    
    # Check daily usage limit
    if not check_and_increment_usage(user_email, "nl_parser"):
        raise HTTPException(status_code=429, detail="Daily limit for strategy parsing reached (20/day). Try again tomorrow.")
    
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="LLM key not configured")
    
    sanitized_text = sanitize_user_input(body.text, max_length=2000)
    if not sanitized_text:
        raise HTTPException(status_code=400, detail="Input text is empty or invalid")
    
    ai_config = get_ai_config("nl_parser")
    chat = LlmChat(
        api_key=api_key,
        session_id=str(uuid.uuid4()),
        system_message=PARSER_PROMPT
    ).with_model("openai", "gpt-5.2").with_params(
        max_tokens=ai_config["max_tokens"],
        temperature=ai_config["temperature"]
    )
    
    user_message = UserMessage(text=sanitized_text)
    
    start_time = time.time()
    try:
        response = await resilient_call(
            chat.send_message, user_message,
            circuit_name="ai", max_retries=2, timeout=30.0,
            fallback=None
        )
        if response is None:
            raise HTTPException(status_code=503, detail="AI service temporarily unavailable")
        latency_ms = (time.time() - start_time) * 1000
        log_ai_call("parser", len(sanitized_text), latency_ms, True)
    except (ServiceTimeoutError, ServiceUnavailableError) as e:
        log_ai_call("parser", len(sanitized_text), (time.time() - start_time) * 1000, False)
        raise HTTPException(status_code=503, detail=str(e))
    
    # Extract JSON from response
    try:
        # Try to parse directly
        parsed = json.loads(response)
        return {"success": True, "parsed": parsed}
    except json.JSONDecodeError:
        # Try to find JSON in response
        import re
        match = re.search(r'\{[\s\S]*\}', response)
        if match:
            try:
                parsed = json.loads(match.group())
                return {"success": True, "parsed": parsed}
            except json.JSONDecodeError:
                pass
        return {"success": False, "error": "Invalid JSON response", "parsed": None}


# =============================================================================
# RISK ANALYZER ROUTE
# =============================================================================

RISK_PROMPT = """You analyze a structured trading strategy.

Supported indicators: RSI, SMA, EMA, MACD, Stochastic, Bollinger, ADX, ATR, Supertrend, VWAP, PivotPoints, PSAR, CCI, WilliamsR, OBV.

Output:
- Maximum 3 concise risk observations.
- Bullet points only.
- Under 100 words total.

Rules:
- Do not give advice.
- Do not predict profitability.
- Do not suggest alternative indicators.
- Only comment on structural risk (e.g., no stop loss, missing exit).
- If insufficient data, say: "Risk cannot be assessed fully."

Be neutral and concise."""

class RiskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    strategy: dict

class RiskResponse(BaseModel):
    success: bool
    warnings: list

@api_router.post("/analyze-risk", response_model=RiskResponse)
@limiter.limit("10/minute")
async def analyze_risk(request: Request, body: RiskRequest, current_user: dict = Depends(get_current_user)):
    user_email = current_user.get("email", "anonymous")
    
    if not check_and_increment_usage(user_email, "risk_analyzer"):
        raise HTTPException(status_code=429, detail="Daily limit for risk analysis reached (10/day). Try again tomorrow.")
    
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="LLM key not configured")
    
    ai_config = get_ai_config("risk_analyzer")
    chat = LlmChat(
        api_key=api_key,
        session_id=str(uuid.uuid4()),
        system_message=RISK_PROMPT
    ).with_model("openai", "gpt-5.2").with_params(
        max_tokens=ai_config["max_tokens"],
        temperature=ai_config["temperature"]
    )
    
    strategy_text = json.dumps(body.strategy, indent=2)
    sanitized_text = sanitize_user_input(strategy_text, max_length=5000)
    user_message = UserMessage(text=sanitized_text)
    
    start_time = time.time()
    try:
        response = await resilient_call(
            chat.send_message, user_message,
            circuit_name="ai", max_retries=2, timeout=30.0,
            fallback=None
        )
        if response is None:
            raise HTTPException(status_code=503, detail="AI service temporarily unavailable")
        latency_ms = (time.time() - start_time) * 1000
        log_ai_call("risk_analyzer", len(sanitized_text), latency_ms, True)
    except (ServiceTimeoutError, ServiceUnavailableError) as e:
        log_ai_call("risk_analyzer", len(sanitized_text), (time.time() - start_time) * 1000, False)
        raise HTTPException(status_code=503, detail=str(e))
    
    # Parse bullet points
    lines = [l.strip().lstrip("•-*").strip() for l in response.split("\n") if l.strip() and l.strip()[0] in "•-*"]
    warnings = lines[:3] if lines else [response.strip()]
    
    return {"success": True, "warnings": warnings}


# =============================================================================
# AI EXPLAINER ROUTE
# =============================================================================

SYSTEM_PROMPT = """You are a trading strategy explainer.

Supported indicators: RSI, SMA, EMA, MACD, Stochastic, Bollinger, ADX, ATR, Supertrend, VWAP, PivotPoints, PSAR, CCI, WilliamsR, OBV.

You will receive:
1. A structured strategy JSON.
2. A user question.

Your task:
- Explain the strategy logic clearly and concisely.
- Describe how entry and exit conditions work.
- Describe risk structure if defined.

Strict rules:
- Do NOT give financial advice.
- Do NOT predict profits or performance.
- Do NOT suggest improvements.
- Do NOT hallucinate or add information not present.
- If a field is missing, say: "Not defined in this strategy."

Constraints:
- Maximum 120 words.
- Neutral tone.
- No disclaimers."""

class ExplainRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    strategy: dict
    question: str = Field(max_length=500)

class ExplainResponse(BaseModel):
    success: bool
    answer: str

@api_router.post("/explain", response_model=ExplainResponse)
@limiter.limit("10/minute")
async def explain_strategy(request: Request, body: ExplainRequest, current_user: dict = Depends(get_current_user)):
    user_email = current_user.get("email", "anonymous")
    
    if not check_and_increment_usage(user_email, "explainer"):
        raise HTTPException(status_code=429, detail="Daily limit for strategy explanations reached (10/day). Try again tomorrow.")
    
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="LLM key not configured")
    
    ai_config = get_ai_config("explainer")
    chat = LlmChat(
        api_key=api_key,
        session_id=str(uuid.uuid4()),
        system_message=SYSTEM_PROMPT
    ).with_model("openai", "gpt-5.2").with_params(
        max_tokens=ai_config["max_tokens"],
        temperature=ai_config["temperature"]
    )
    
    # Sanitize user question
    sanitized_question = sanitize_user_input(body.question, max_length=500)
    strategy_text = sanitize_user_input(json.dumps(body.strategy, indent=2), max_length=5000)
    prompt = f"Strategy JSON:\n{strategy_text}\n\nUser question: {sanitized_question}"
    
    user_message = UserMessage(text=prompt)
    
    start_time = time.time()
    try:
        response = await resilient_call(
            chat.send_message, user_message,
            circuit_name="ai", max_retries=2, timeout=30.0,
            fallback=None
        )
        if response is None:
            raise HTTPException(status_code=503, detail="AI service temporarily unavailable")
        latency_ms = (time.time() - start_time) * 1000
        log_ai_call("explainer", len(prompt), latency_ms, True)
    except (ServiceTimeoutError, ServiceUnavailableError) as e:
        log_ai_call("explainer", len(prompt), (time.time() - start_time) * 1000, False)
        raise HTTPException(status_code=503, detail=str(e))
    
    return {"success": True, "answer": response}


# =============================================================================
# BACKTEST ROUTE
# =============================================================================

from data.service import get_available_symbols, get_data_status
from backtest.engine import run_backtest as engine_run_backtest

class BacktestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    strategy: dict
    slippage_pct: float = 0.05
    initial_capital: float = 100000
    brokerage_per_order: float = 20

class BacktestResponse(BaseModel):
    success: bool
    label: str
    disclaimer: str
    trades: list
    metrics: dict
    costs: dict
    equity_curve: list
    warnings: list
    data_source: str
    candles_processed: int = 0

@api_router.post("/backtest", response_model=BacktestResponse)
@limiter.limit("5/minute")
async def run_backtest_endpoint(request: Request, body: BacktestRequest):
    try:
        strategy = body.strategy
        symbol = strategy.get("instrument", {}).get("symbol", "RELIANCE")
        timeframe = strategy.get("timeframe", {}).get("interval", "1d")

        result = engine_run_backtest(
            strategy, symbol, timeframe,
            slippage_pct=body.slippage_pct,
            initial_capital=body.initial_capital,
            brokerage_per_order=body.brokerage_per_order,
        )

        analytics_db["backtests_run"] += 1
        if result["success"] and result["trades"]:
            analytics_db["backtest_types"]["historical"] += 1

        return result
    except Exception as e:
        logger.error(f"Backtest endpoint error: {e}")
        from backtest.metrics import calculate_metrics
        return {
            "success": False, "label": "Backtest Error",
            "disclaimer": str(e), "trades": [],
            "metrics": calculate_metrics([]), "costs": {},
            "equity_curve": [], "warnings": [str(e)],
            "data_source": "error", "candles_processed": 0,
        }


# =============================================================================
# PAPER TRADING ENDPOINTS
# =============================================================================

from paper_trading.engine import deploy_paper_trade, stop_paper_trade, pause_paper_trade


class PaperTradeDeployRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    strategy_id: str
    symbol: str = "RELIANCE"
    timeframe: str = "1d"
    initial_capital: float = Field(default=100000, ge=1000, le=10000000)
    lookback_days: int = Field(default=60, ge=7, le=365)
    slippage_pct: float = Field(default=0.05, ge=0, le=1)


@api_router.post("/paper-trade/deploy")
@limiter.limit("5/minute")
async def deploy_paper_trade_endpoint(request: Request, body: PaperTradeDeployRequest, current_user: dict = Depends(get_current_user)):
    """Deploy a strategy for paper trading on cached data."""
    user_id = current_user.get("user_id", current_user.get("email"))

    # Load strategy
    strategy_doc = strategies_collection.find_one(
        {"id": body.strategy_id, "user_id": user_id}, {"_id": 0}
    )
    if not strategy_doc:
        raise HTTPException(status_code=404, detail="Strategy not found")

    result = deploy_paper_trade(
        strategy=strategy_doc,
        symbol=body.symbol,
        timeframe=body.timeframe,
        initial_capital=body.initial_capital,
        user_id=user_id,
        db=db,
        lookback_days=body.lookback_days,
        slippage_pct=body.slippage_pct,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@api_router.get("/paper-trades")
@limiter.limit("20/minute")
async def list_paper_trades(request: Request, current_user: dict = Depends(get_current_user)):
    """List all paper trades for the authenticated user."""
    user_id = current_user.get("user_id", current_user.get("email"))
    docs = list(db.paper_trades.find(
        {"user_id": user_id}, {"_id": 0}
    ).sort("created_at", -1))
    return {"paper_trades": docs, "count": len(docs)}


@api_router.get("/paper-trade/{paper_trade_id}")
@limiter.limit("30/minute")
async def get_paper_trade(request: Request, paper_trade_id: str, current_user: dict = Depends(get_current_user)):
    """Get a specific paper trade with full details."""
    user_id = current_user.get("user_id", current_user.get("email"))
    doc = db.paper_trades.find_one(
        {"paper_trade_id": paper_trade_id, "user_id": user_id}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Paper trade not found")
    return doc


@api_router.post("/paper-trade/{paper_trade_id}/pause")
@limiter.limit("10/minute")
async def pause_paper_trade_endpoint(request: Request, paper_trade_id: str, current_user: dict = Depends(get_current_user)):
    """Pause a paper trade."""
    user_id = current_user.get("user_id", current_user.get("email"))
    result = pause_paper_trade(paper_trade_id, user_id, db)
    if not result:
        raise HTTPException(status_code=404, detail="Paper trade not found")
    return {"success": True, "status": result.get("status"), "paper_trade_id": paper_trade_id}


@api_router.post("/paper-trade/{paper_trade_id}/stop")
@limiter.limit("10/minute")
async def stop_paper_trade_endpoint(request: Request, paper_trade_id: str, current_user: dict = Depends(get_current_user)):
    """Stop a paper trade and close any open positions."""
    user_id = current_user.get("user_id", current_user.get("email"))
    result = stop_paper_trade(paper_trade_id, user_id, db)
    if not result:
        raise HTTPException(status_code=404, detail="Paper trade not found")
    return result


# =============================================================================
# SESSION MANAGEMENT ENDPOINTS
# =============================================================================

NL_BUILDER_SYSTEM_PROMPT = """You are a trading strategy builder assistant for the Indian stock market.

Your job: Convert the user's trading idea into a structured equity strategy JSON through conversation. Ask clarifying questions when information is missing. Never guess values.

SCOPE: Equity / stock trading only. If the user asks about options, futures, F&O, or derivatives, respond:
{ "mode": "question", "message": "F&O support is coming in the next release. For now, let's build your equity strategy. Which stock are you interested in?" }

SUPPORTED INDICATORS (only use these):
RSI, SMA, EMA, MACD, Bollinger, Stochastic, ADX, ATR, Supertrend, VWAP, PivotPoints, PSAR, CCI, WilliamsR, OBV

SUPPORTED INSTRUMENTS (equity only):
RELIANCE, TCS, HDFCBANK, INFY, ICICIBANK, HINDUNILVR, ITC, SBIN, BHARTIARTL, KOTAKBANK, LT, AXISBANK, ASIANPAINT, MARUTI, BAJFINANCE, TITAN, SUNPHARMA, HCLTECH, WIPRO, TATAMOTORS, NIFTY 50, BANKNIFTY

RESPONSE MODES:

MODE 1 — QUESTION: { "mode": "question", "message": "...", "fields_needed": [...] }
MODE 2 — STRATEGY: { "mode": "strategy", "strategy": { "instrument": { "symbol": "", "type": "equity" }, "timeframe": "", "entry_conditions": [...], "exit_conditions": [...], "risk_management": { ... } }, "explanation": "..." }
MODE 3 — ERROR: { "mode": "error", "message": "..." }

RULES:
- Instrument type is ALWAYS "equity".
- If stop loss missing: ASK.
- If exit condition missing: ASK.
- If instrument missing: ASK.
- If timeframe missing: ASK.
- Unsupported indicator: return error mode.
- One question at a time. Max 2 fields per question.
- Never give financial advice. Never predict profits."""

SUPPORTED_INDICATORS = {
    "RSI", "SMA", "EMA", "MACD", "Bollinger", "Stochastic", "ADX", "ATR",
    "Supertrend", "VWAP", "PivotPoints", "PSAR", "CCI", "WilliamsR", "OBV",
}

SUPPORTED_INSTRUMENTS = {
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR", "ITC",
    "SBIN", "BHARTIARTL", "KOTAKBANK", "LT", "AXISBANK", "ASIANPAINT", "MARUTI",
    "BAJFINANCE", "TITAN", "SUNPHARMA", "HCLTECH", "WIPRO", "TATAMOTORS",
    "NIFTY 50", "BANKNIFTY",
}


def _detect_hallucinated_indicators(strategy_data: dict) -> list:
    """Extract indicator names from a strategy dict and check against registry.
    Returns list of invalid indicator names. Handles both 'name' and 'indicator' fields.
    """
    invalid = []
    for cond_list_key in ("entry_conditions", "exit_conditions", "filters"):
        for cond in strategy_data.get(cond_list_key, []):
            name = cond.get("name") or cond.get("indicator") or ""
            if name and name not in SUPPORTED_INDICATORS:
                invalid.append(name)
    return invalid


def _parse_ai_json(text: str) -> dict:
    """Extract JSON from AI response text. Handles markdown code blocks."""
    import re
    cleaned = text.strip()
    # Strip markdown code fences
    match = re.search(r'```(?:json)?\s*([\s\S]*?)```', cleaned)
    if match:
        cleaned = match.group(1).strip()
    # Try to find JSON object
    start = cleaned.find('{')
    if start == -1:
        return None
    # Find matching closing brace
    depth = 0
    for i in range(start, len(cleaned)):
        if cleaned[i] == '{':
            depth += 1
        elif cleaned[i] == '}':
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(cleaned[start:i+1])
                except json.JSONDecodeError:
                    return None
    return None


def _validate_strategy_draft(strategy_data: dict) -> list:
    """Validate a strategy draft from AI. Returns list of error strings."""
    errors = []
    if not strategy_data.get("entry_conditions"):
        errors.append("No entry conditions defined.")
    if not strategy_data.get("instrument") or not strategy_data["instrument"].get("symbol"):
        errors.append("No instrument/symbol specified.")
    if not strategy_data.get("timeframe"):
        errors.append("No timeframe specified.")

    hallucinated = _detect_hallucinated_indicators(strategy_data)
    if hallucinated:
        errors.append(f"Unsupported indicators: {', '.join(hallucinated)}")

    return errors


def _normalize_ai_condition(cond: dict) -> dict:
    """Normalize an AI-generated condition to match our strict IndicatorCondition schema.
    Handles: 'indicator' -> 'name', 'length' -> 'period', strips extra fields.
    """
    name = cond.get("name") or cond.get("indicator") or ""

    # Normalize params
    raw_params = cond.get("params", {})
    params = {}
    for k, v in raw_params.items():
        if k == "length":
            params["period"] = v
        else:
            params[k] = v

    operator = cond.get("operator", "")
    value = cond.get("value")

    # Only return fields our schema expects
    result = {"name": name, "params": params, "operator": operator}
    if value is not None:
        result["value"] = value
    return result


def _normalize_ai_strategy(draft: dict) -> dict:
    """Normalize AI-generated strategy JSON to match the strict schema used by CRUD endpoints."""
    normalized = {}

    # Instrument
    inst = draft.get("instrument", {})
    if isinstance(inst, str):
        normalized["instrument"] = {"symbol": inst}
    else:
        normalized["instrument"] = {"symbol": inst.get("symbol", ""), "base": None, "quote": None}

    # Timeframe
    tf = draft.get("timeframe", "1d")
    if isinstance(tf, dict):
        normalized["timeframe"] = tf
    else:
        normalized["timeframe"] = {"interval": tf, "candle_count": None}

    # Entry conditions — normalize each, skip non-indicator entries
    normalized["entry_conditions"] = []
    for c in draft.get("entry_conditions", []):
        ind_name = c.get("name") or c.get("indicator") or ""
        if ind_name in SUPPORTED_INDICATORS:
            normalized["entry_conditions"].append(_normalize_ai_condition(c))

    # Exit conditions — normalize each, skip TP/SL entries (they go to risk_management)
    normalized["exit_conditions"] = []
    for c in draft.get("exit_conditions", []):
        ctype = c.get("type", "")
        if ctype in ("take_profit", "stop_loss"):
            continue  # These belong in risk_management
        ind_name = c.get("name") or c.get("indicator") or ""
        if ind_name in SUPPORTED_INDICATORS:
            normalized["exit_conditions"].append(_normalize_ai_condition(c))

    # Filters
    normalized["filters"] = []
    for c in draft.get("filters", []):
        ind_name = c.get("name") or c.get("indicator") or ""
        if ind_name in SUPPORTED_INDICATORS:
            normalized["filters"].append(_normalize_ai_condition(c))

    # Risk management — normalize from various AI formats to new schema
    rm = draft.get("risk_management", {})
    sl = rm.get("stop_loss")
    tp = rm.get("take_profit")
    trailing = rm.get("trailing_stop") or rm.get("trailing_stop_loss")
    # Handle nested objects like {"stop_loss": {"value": 4, "type": "fixed_percent"}}
    if isinstance(sl, dict):
        sl = sl.get("value")
    if isinstance(tp, dict):
        tp = tp.get("value")
    if isinstance(trailing, dict):
        trailing = trailing.get("value")

    risk = {}
    if sl is not None:
        risk["stop_loss"] = {"type": "percentage", "value": float(sl)}
    else:
        risk["stop_loss"] = None
    if tp is not None:
        risk["target_profit"] = {"type": "percentage", "value": float(tp)}
    else:
        risk["target_profit"] = None
    risk["trailing_stop_loss"] = {"enabled": trailing is not None, "type": "percentage", "value": float(trailing) if trailing else 1.0, "activation_profit": 0}
    risk["time_based_exit"] = {"enabled": False, "exit_time": "15:10"}
    risk["daily_limits"] = {"max_loss_per_day": 5.0, "max_trades_per_day": 10}
    risk["position_sizing"] = {"method": "fixed_quantity", "value": 1}
    normalized["risk_management"] = risk

    return normalized


class SessionMessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(max_length=1000)


class SessionMessageResponse(BaseModel):
    mode: str  # "question", "strategy", "error"
    content: dict  # The parsed JSON response
    session_id: str
    strategy_draft: Optional[dict] = None


class DraftUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    strategy_draft: dict


@api_router.post("/session/start")
@limiter.limit("10/minute")
async def start_session(request: Request, current_user: dict = Depends(get_current_user)):
    """Create a new conversation session."""
    user_email = current_user.get("email")
    result = create_session(user_email)
    return result


@api_router.post("/session/{session_id}/message")
@limiter.limit("20/minute")
async def send_session_message(request: Request, session_id: str, body: SessionMessageRequest, current_user: dict = Depends(get_current_user)):
    """Send a message in a session. AI responds in 3 modes: question, strategy, error."""
    user_email = current_user.get("email")

    # Verify session ownership
    session = get_session(session_id, user_email)
    if session == "forbidden":
        raise HTTPException(status_code=403, detail="Access denied to this session")
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Check daily usage
    if not check_and_increment_usage(user_email, "session_chat"):
        raise HTTPException(status_code=429, detail="Daily session chat limit reached (30/day). Try again tomorrow.")

    # Sanitize user message
    sanitized = sanitize_user_input(body.message, max_length=1000)
    if not sanitized:
        raise HTTPException(status_code=400, detail="Message is empty or invalid")

    # Store user message
    append_message(session_id, user_email, "user", sanitized)

    # Build context: last 6 messages, token-budgeted to 500 tokens
    context_msgs = get_context_messages(session_id, user_email, max_messages=6, token_budget=500)

    # Build prompt with conversation history
    context_parts = []
    for msg in context_msgs[:-1]:
        prefix = "User" if msg["role"] == "user" else "Assistant"
        context_parts.append(f"{prefix}: {msg['content']}")

    context_str = "\n".join(context_parts) if context_parts else ""
    full_prompt = f"{context_str}\nUser: {sanitized}" if context_str else sanitized

    # Call AI
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="LLM key not configured")

    ai_config = get_ai_config("session_chat")
    ai_text = await _call_session_ai(api_key, session_id, full_prompt, ai_config)

    # Parse response JSON
    parsed = _parse_ai_json(ai_text)
    if parsed is None:
        # AI didn't return valid JSON — wrap as question mode
        parsed = {"mode": "question", "message": ai_text, "fields_needed": []}

    mode = parsed.get("mode", "question")

    # --- Handle strategy mode with validation + hallucination check ---
    if mode == "strategy":
        strategy_data = parsed.get("strategy", {})
        errors = _validate_strategy_draft(strategy_data)

        if errors:
            # Silent retry with correction context (costs 1 extra credit)
            if check_and_increment_usage(user_email, "session_chat"):
                correction_prompt = (
                    f"Your previous response had validation errors: {'; '.join(errors)}. "
                    f"Please fix and return a valid strategy JSON. Only use supported indicators: "
                    f"{', '.join(sorted(SUPPORTED_INDICATORS))}. "
                    f"Original user request context:\n{full_prompt}"
                )
                retry_text = await _call_session_ai(api_key, session_id, correction_prompt, ai_config)
                retry_parsed = _parse_ai_json(retry_text)
                if retry_parsed and retry_parsed.get("mode") == "strategy":
                    retry_errors = _validate_strategy_draft(retry_parsed.get("strategy", {}))
                    if not retry_errors:
                        parsed = retry_parsed
                        strategy_data = parsed.get("strategy", {})
                        errors = []
                        ai_text = retry_text

            if errors:
                # Retry also failed — return as error
                parsed = {"mode": "error", "message": f"Strategy validation failed: {'; '.join(errors)}"}
                mode = "error"
            else:
                mode = "strategy"

        if mode == "strategy":
            # Store validated strategy draft in session
            update_strategy_draft(session_id, user_email, strategy_data)

    # Store assistant response
    append_message(session_id, user_email, "assistant", json.dumps(parsed) if isinstance(parsed, dict) else ai_text)

    return SessionMessageResponse(
        mode=mode,
        content=parsed,
        session_id=session_id,
        strategy_draft=parsed.get("strategy") if mode == "strategy" else None,
    )


async def _call_session_ai(api_key: str, session_id: str, prompt: str, ai_config: dict) -> str:
    """Make an AI call for the session. Returns raw text."""
    chat = LlmChat(
        api_key=api_key,
        session_id=session_id,
        system_message=NL_BUILDER_SYSTEM_PROMPT,
    ).with_model("openai", "gpt-5.2").with_params(
        max_tokens=ai_config["max_tokens"],
        temperature=ai_config["temperature"],
    )

    start_time = time.time()
    try:
        response = await resilient_call(
            chat.send_message, UserMessage(text=prompt),
            circuit_name="ai", max_retries=2, timeout=30.0, fallback=None,
        )
        if response is None:
            raise HTTPException(status_code=503, detail="AI service temporarily unavailable")
        latency_ms = (time.time() - start_time) * 1000
        log_ai_call("session_chat", len(prompt), latency_ms, True)
    except (ServiceTimeoutError, ServiceUnavailableError) as e:
        log_ai_call("session_chat", len(prompt), (time.time() - start_time) * 1000, False)
        raise HTTPException(status_code=503, detail=str(e))

    return response if isinstance(response, str) else str(response)


@api_router.post("/session/{session_id}/finalize")
@limiter.limit("10/minute")
async def finalize_session_strategy(request: Request, session_id: str, current_user: dict = Depends(get_current_user)):
    """Validate the session's strategy draft and save to strategies collection."""
    user_email = current_user.get("email")

    session = get_session(session_id, user_email)
    if session == "forbidden":
        raise HTTPException(status_code=403, detail="Access denied to this session")
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    draft = session.get("strategy_draft")
    if not draft:
        raise HTTPException(status_code=400, detail="No strategy draft in this session. Continue the conversation to build one.")

    # Normalize AI output to match our strict schema
    normalized = _normalize_ai_strategy(draft)

    # Validate normalized draft
    errors = _validate_strategy_draft(normalized)
    if errors:
        raise HTTPException(status_code=422, detail=f"Draft has errors: {'; '.join(errors)}")

    # Build a full Strategy-compatible doc
    strategy_id = str(uuid.uuid4())
    user_id = current_user.get("user_id", user_email)
    symbol = normalized["instrument"].get("symbol", "UNKNOWN")
    timeframe_val = normalized["timeframe"]
    if isinstance(timeframe_val, dict):
        timeframe_val = timeframe_val.get("interval", "1d")

    strategy_doc = {
        "id": strategy_id,
        "user_id": user_id,
        "version": "1.0",
        "metadata": {
            "name": f"AI Strategy - {symbol}",
            "description": draft.get("explanation") or f"AI-built strategy for {symbol}",
            "tags": ["ai-generated"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        "market": {"type": "equity", "exchange": "NSE"},
        "instrument": normalized["instrument"],
        "timeframe": normalized["timeframe"],
        "entry_conditions": normalized["entry_conditions"],
        "exit_conditions": normalized["exit_conditions"],
        "filters": normalized.get("filters", []),
        "risk_management": normalized["risk_management"],
    }

    strategies_collection.insert_one(strategy_doc)
    analytics_db["strategies_created"] += 1

    return {
        "success": True,
        "strategy_id": strategy_id,
        "message": f"Strategy saved for {symbol}.",
    }


@api_router.put("/session/{session_id}/draft")
@limiter.limit("20/minute")
async def update_session_draft(request: Request, session_id: str, body: DraftUpdateRequest, current_user: dict = Depends(get_current_user)):
    """Manually edit the strategy draft before finalizing."""
    user_email = current_user.get("email")

    session = get_session(session_id, user_email)
    if session == "forbidden":
        raise HTTPException(status_code=403, detail="Access denied to this session")
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Validate the new draft
    errors = _validate_strategy_draft(body.strategy_draft)
    if errors:
        raise HTTPException(status_code=422, detail=f"Draft has errors: {'; '.join(errors)}")

    update_strategy_draft(session_id, user_email, body.strategy_draft)

    return {"success": True, "message": "Draft updated.", "strategy_draft": body.strategy_draft}


@api_router.get("/session/{session_id}")
@limiter.limit("30/minute")
async def get_session_endpoint(request: Request, session_id: str, current_user: dict = Depends(get_current_user)):
    """Get full session with all messages."""
    user_email = current_user.get("email")
    session = get_session(session_id, user_email)
    if session == "forbidden":
        raise HTTPException(status_code=403, detail="Access denied to this session")
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@api_router.delete("/session/{session_id}")
@limiter.limit("10/minute")
async def delete_session_endpoint(request: Request, session_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a session."""
    user_email = current_user.get("email")
    session = get_session(session_id, user_email)
    if session == "forbidden":
        raise HTTPException(status_code=403, detail="Access denied to this session")
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    delete_session(session_id, user_email)
    return {"success": True, "message": "Session deleted"}


@api_router.get("/ai/usage")
@limiter.limit("30/minute")
async def get_ai_usage(request: Request, current_user: dict = Depends(get_current_user)):
    """Get current user's AI usage stats for today."""
    return get_usage_stats(current_user.get("email"))


# =============================================================================
# ADMIN ENDPOINTS
# =============================================================================

admin_router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

@admin_router.get("/data/status")
@limiter.limit("10/minute")
async def admin_data_status(request: Request, admin: dict = Depends(get_admin_user)):
    """Full data health report — admin only."""
    try:
        status = get_data_status()
        return status
    except Exception as e:
        logger.error(f"Data status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@admin_router.post("/data/refresh")
@limiter.limit("2/minute")
async def admin_data_refresh(request: Request, admin: dict = Depends(get_admin_user)):
    """Trigger incremental data refresh — admin only."""
    import subprocess, sys
    try:
        script_path = os.path.join(os.path.dirname(__file__), "scripts", "refresh_data.py")
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True, text=True, timeout=600,
            cwd=os.path.dirname(__file__),
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout[-2000:] if result.stdout else "",
            "stderr": result.stderr[-500:] if result.stderr else "",
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Refresh timed out (10 min limit)"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@admin_router.get("/users")
@limiter.limit("10/minute")
async def admin_list_users(request: Request, admin: dict = Depends(get_admin_user)):
    """List all users with activity stats — admin only."""
    users = list(users_collection.find({}, {"_id": 0, "password_hash": 0}))
    for u in users:
        email = u.get("email", "")
        u["strategy_count"] = strategies_collection.count_documents({"user_id": email})
    return {"users": users, "total": len(users)}

@admin_router.get("/analytics")
@limiter.limit("10/minute")
async def admin_analytics(request: Request, admin: dict = Depends(get_admin_user)):
    """Platform-wide analytics — admin only."""
    from data.service import market_data_collection
    return {
        "users": {
            "total": users_collection.count_documents({}),
            "admins": users_collection.count_documents({"role": "admin"}),
        },
        "strategies": {
            "total": strategies_collection.count_documents({}),
        },
        "market_data": {
            "total_candles": market_data_collection.count_documents({}),
            "symbols": len(market_data_collection.distinct("symbol")),
            "timeframes": market_data_collection.distinct("timeframe"),
        },
        "usage": analytics_db,
    }


# =============================================================================
# STARTUP VALIDATION
# =============================================================================

@app.on_event("startup")
async def startup_validation():
    """Check market_data on startup."""
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
            
            # Check for stale data
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
# APP SETUP
# =============================================================================

# Add Request ID middleware (defined above as RequestIdMiddleware)
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

logger.info("Text2trade API initialized")

# Run tests on startup if TEST_MODE env is set
if os.environ.get("TEST_MODE") == "1":
    run_internal_tests()
