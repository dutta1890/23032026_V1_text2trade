from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path
from pydantic import BaseModel, EmailStr
from datetime import datetime, timezone
from typing import Dict, List, Optional
import uuid


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

app = FastAPI(title="Text2trade API", version="0.3.0")
api_router = APIRouter(prefix="/api")

# In-memory storage
users_db: Dict[str, str] = {}
strategies_db: List[dict] = []


# =============================================================================
# AUTH MODELS
# =============================================================================

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str

class RootResponse(BaseModel):
    message: str
    app_name: str

class AuthRequest(BaseModel):
    email: EmailStr
    password: str

class AuthResponse(BaseModel):
    success: bool
    message: str
    email: str


# =============================================================================
# STRATEGY MODELS
# =============================================================================

class Metadata(BaseModel):
    name: str
    description: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class Market(BaseModel):
    type: str  # crypto, forex, stocks
    exchange: Optional[str] = None

class Instrument(BaseModel):
    symbol: str
    base: Optional[str] = None
    quote: Optional[str] = None

class Timeframe(BaseModel):
    interval: str  # 1m, 5m, 1h, 1d
    candle_count: Optional[int] = None

class EntryRule(BaseModel):
    condition: str
    indicator: Optional[str] = None
    value: Optional[float] = None
    operator: Optional[str] = None  # >, <, ==, >=, <=

class RiskManagement(BaseModel):
    max_position_size: Optional[float] = None
    max_daily_loss: Optional[float] = None
    risk_per_trade: Optional[float] = None

class ExitRules(BaseModel):
    take_profit: Optional[float] = None
    stop_loss: Optional[float] = None
    trailing_stop: Optional[float] = None
    time_exit: Optional[str] = None

class Strategy(BaseModel):
    id: Optional[str] = None
    metadata: Metadata
    market: Market
    instrument: Instrument
    timeframe: Timeframe
    entry_rules: List[EntryRule]
    risk_management: RiskManagement
    exit_rules: ExitRules

class StrategyResponse(BaseModel):
    success: bool
    strategy: Strategy

class StrategiesListResponse(BaseModel):
    success: bool
    strategies: List[Strategy]
    count: int


# =============================================================================
# GENERAL ROUTES
# =============================================================================

@api_router.get("/", response_model=RootResponse)
async def root():
    return {"message": "Welcome to Text2trade API", "app_name": "Text2trade"}

@api_router.get("/health", response_model=HealthResponse)
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "0.3.0"
    }


# =============================================================================
# AUTH ROUTES
# =============================================================================

@api_router.post("/signup", response_model=AuthResponse)
async def signup(request: AuthRequest):
    email = request.email.lower()
    if email in users_db:
        raise HTTPException(status_code=400, detail="Email already registered")
    if not request.password:
        raise HTTPException(status_code=400, detail="Password cannot be empty")
    users_db[email] = request.password
    logger.info(f"New user signed up: {email}")
    return {"success": True, "message": "Account created successfully", "email": email}

@api_router.post("/login", response_model=AuthResponse)
async def login(request: AuthRequest):
    email = request.email.lower()
    if email not in users_db:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if users_db[email] != request.password:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    logger.info(f"User logged in: {email}")
    return {"success": True, "message": "Login successful", "email": email}


# =============================================================================
# STRATEGY ROUTES
# =============================================================================

@api_router.post("/strategy", response_model=StrategyResponse)
async def create_strategy(strategy: Strategy):
    strategy.id = str(uuid.uuid4())
    strategy.metadata.created_at = datetime.now(timezone.utc).isoformat()
    strategy.metadata.updated_at = strategy.metadata.created_at
    strategies_db.append(strategy.model_dump())
    logger.info(f"Strategy created: {strategy.id}")
    return {"success": True, "strategy": strategy}

@api_router.get("/strategies", response_model=StrategiesListResponse)
async def get_strategies():
    return {
        "success": True,
        "strategies": strategies_db,
        "count": len(strategies_db)
    }


# =============================================================================
# APP SETUP
# =============================================================================

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.info("Text2trade API initialized")
