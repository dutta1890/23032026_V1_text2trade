from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path
from pydantic import BaseModel, EmailStr
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
import uuid
import json
from emergentintegrations.llm.chat import LlmChat, UserMessage


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

app = FastAPI(title="Text2trade API", version="0.6.0")
api_router = APIRouter(prefix="/api")

users_db: Dict[str, str] = {}
strategies_db: List[dict] = []
feedback_db: List[dict] = []


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

class IndicatorCondition(BaseModel):
    name: str  # RSI, SMA, EMA, MACD, BB, VOLUME, PRICE, etc.
    params: Dict[str, Any] = {}  # {"period": 14, "source": "close"}
    operator: str  # >, <, ==, >=, <=, crosses_above, crosses_below
    value: Optional[Union[float, str]] = None  # 70, "SMA_50", etc.

class Metadata(BaseModel):
    name: str
    description: Optional[str] = None
    tags: List[str] = []
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class Market(BaseModel):
    type: str  # crypto, forex, stocks, futures
    exchange: Optional[str] = None

class Instrument(BaseModel):
    symbol: str
    base: Optional[str] = None
    quote: Optional[str] = None

class Timeframe(BaseModel):
    interval: str  # 1m, 5m, 15m, 1h, 4h, 1d
    candle_count: Optional[int] = None

class RiskManagement(BaseModel):
    position_size: Optional[float] = None
    position_size_type: Optional[str] = None  # fixed, percent, risk_based
    max_daily_loss: Optional[float] = None
    max_drawdown: Optional[float] = None
    risk_per_trade: Optional[float] = None
    take_profit: Optional[float] = None
    stop_loss: Optional[float] = None
    trailing_stop: Optional[float] = None

class Strategy(BaseModel):
    id: Optional[str] = None
    version: str = "1.0"
    metadata: Metadata
    market: Market
    instrument: Instrument
    timeframe: Timeframe
    entry_conditions: List[IndicatorCondition] = []
    exit_conditions: List[IndicatorCondition] = []
    filters: List[IndicatorCondition] = []
    risk_management: RiskManagement

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
        "version": "0.4.0"
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

def validate_strategy(strategy: Strategy):
    errors = []
    
    # At least one entry condition required
    if not strategy.entry_conditions:
        errors.append("At least one entry condition is required")
    
    # Timeframe required
    if not strategy.timeframe or not strategy.timeframe.interval:
        errors.append("Timeframe is required")
    
    # stop_loss > 0
    sl = strategy.risk_management.stop_loss if strategy.risk_management else None
    tp = strategy.risk_management.take_profit if strategy.risk_management else None
    
    if sl is not None and sl <= 0:
        errors.append("stop_loss must be greater than 0")
    
    # target > stop_loss if both defined
    if sl is not None and tp is not None and tp <= sl:
        errors.append("take_profit must be greater than stop_loss")
    
    return errors

def get_next_version(name: str) -> str:
    existing = [s for s in strategies_db if s.get("metadata", {}).get("name") == name]
    if not existing:
        return "1.0"
    versions = [float(s.get("version", "1.0")) for s in existing]
    return str(max(versions) + 1.0)

@api_router.post("/strategy", response_model=StrategyResponse)
async def create_strategy(strategy: Strategy):
    errors = validate_strategy(strategy)
    if errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))
    
    strategy.id = str(uuid.uuid4())
    strategy.version = get_next_version(strategy.metadata.name)
    strategy.metadata.created_at = datetime.now(timezone.utc).isoformat()
    strategy.metadata.updated_at = strategy.metadata.created_at
    strategies_db.append(strategy.model_dump())
    logger.info(f"Strategy created: {strategy.id} - {strategy.metadata.name} v{strategy.version}")
    return {"success": True, "strategy": strategy}

@api_router.get("/strategies", response_model=StrategiesListResponse)
async def get_strategies():
    return {
        "success": True,
        "strategies": strategies_db,
        "count": len(strategies_db)
    }


# =============================================================================
# NL PARSER ROUTE
# =============================================================================

PARSER_PROMPT = """You extract structured trading strategy data.

Supported indicators:
RSI, SMA, EMA, MACD, Bollinger, Stochastic, ADX, ATR, SAR, OBV, Ichimoku.

Return ONLY valid JSON in this format:

{
  "entry_conditions": [],
  "exit_conditions": [],
  "filters": [],
  "risk_management": {
    "stop_loss": null,
    "take_profit": null
  }
}

Rules:
- Extract only explicitly mentioned values.
- Do not guess missing numbers.
- If a value is not specified, set it to null.
- Do not explain.
- Do not include text outside JSON.
- Do not optimize or improve the strategy.
- Do not calculate formulas."""

class ParseRequest(BaseModel):
    text: str

class ParseResponse(BaseModel):
    success: bool
    parsed: Optional[dict] = None
    error: Optional[str] = None

@api_router.post("/parse-strategy", response_model=ParseResponse)
async def parse_strategy(request: ParseRequest):
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="LLM key not configured")
    
    chat = LlmChat(
        api_key=api_key,
        session_id=str(uuid.uuid4()),
        system_message=PARSER_PROMPT
    ).with_model("openai", "gpt-5.2")
    
    user_message = UserMessage(text=request.text)
    response = await chat.send_message(user_message)
    
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

Output:
- Maximum 3 concise risk observations.
- Bullet points only.
- Under 120 words total.

Rules:
- Do not give advice.
- Do not predict profitability.
- Do not suggest alternative indicators.
- Only comment on structural risk (e.g., no stop loss, high trade frequency).
- If insufficient data, say: "Risk cannot be assessed fully."

Be neutral and concise."""

class RiskRequest(BaseModel):
    strategy: dict

class RiskResponse(BaseModel):
    success: bool
    warnings: list

@api_router.post("/analyze-risk", response_model=RiskResponse)
async def analyze_risk(request: RiskRequest):
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="LLM key not configured")
    
    chat = LlmChat(
        api_key=api_key,
        session_id=str(uuid.uuid4()),
        system_message=RISK_PROMPT
    ).with_model("openai", "gpt-5.2")
    
    user_message = UserMessage(text=json.dumps(request.strategy, indent=2))
    response = await chat.send_message(user_message)
    
    # Parse bullet points
    lines = [l.strip().lstrip("•-*").strip() for l in response.split("\n") if l.strip() and l.strip()[0] in "•-*"]
    warnings = lines[:3] if lines else [response.strip()]
    
    return {"success": True, "warnings": warnings}


# =============================================================================
# AI EXPLAINER ROUTE
# =============================================================================

SYSTEM_PROMPT = """You are a trading strategy explainer.

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
- Do NOT suggest improvements or optimizations.
- Do NOT add indicators not present in the JSON.
- Do NOT modify the strategy.
- Do NOT use marketing language.
- If a field is missing, say: "That parameter is not defined in this strategy."

Constraints:
- Maximum 120 words.
- Clear, neutral tone.
- No disclaimers.
- No extra commentary."""

class ExplainRequest(BaseModel):
    strategy: dict
    question: str

class ExplainResponse(BaseModel):
    success: bool
    answer: str

@api_router.post("/explain", response_model=ExplainResponse)
async def explain_strategy(request: ExplainRequest):
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="LLM key not configured")
    
    chat = LlmChat(
        api_key=api_key,
        session_id=str(uuid.uuid4()),
        system_message=SYSTEM_PROMPT
    ).with_model("openai", "gpt-5.2")
    
    prompt = f"Strategy JSON:\n{json.dumps(request.strategy, indent=2)}\n\nUser question: {request.question}"
    
    user_message = UserMessage(text=prompt)
    response = await chat.send_message(user_message)
    
    return {"success": True, "answer": response}


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
