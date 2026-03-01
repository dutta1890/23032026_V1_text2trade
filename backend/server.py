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


from indicator_registry import validate_condition


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
    stop_loss_type: Optional[str] = "fixed"  # fixed, atr_multiple
    stop_loss_atr_period: Optional[int] = 14
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
# FEEDBACK ROUTE
# =============================================================================

class FeedbackRequest(BaseModel):
    message: str
    email: Optional[str] = None

class FeedbackResponse(BaseModel):
    success: bool

@api_router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest):
    feedback_db.append({
        "message": request.message,
        "email": request.email,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    logger.info(f"Feedback received: {request.message[:50]}...")
    return {"success": True}


# =============================================================================
# NL PARSER ROUTE
# =============================================================================

PARSER_PROMPT = """You extract structured trading strategy data.

Supported indicators ONLY:
- RSI: params { "period": int }, value is number (0-100)
- SMA: params { "short": int, "long": int }
- EMA: params { "short": int, "long": int }
- MACD: params { "fast": int, "slow": int, "signal": int }, operators: bullish_cross, bearish_cross

Common patterns:
- "Golden cross" = SMA with operator crosses_above
- "Death cross" = SMA with operator crosses_below
- "MACD bullish" = MACD with operator bullish_cross
- "MACD bearish" = MACD with operator bearish_cross

Return ONLY valid JSON:

{
  "entry_conditions": [],
  "exit_conditions": [],
  "filters": [],
  "risk_management": { "stop_loss": null, "take_profit": null }
}

Rules:
- Only use RSI, SMA, EMA, MACD. Ignore other indicators.
- Extract only explicitly mentioned values.
- Do not guess missing numbers.
- Do not explain or add text outside JSON."""

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

Supported indicators ONLY: RSI, SMA, EMA, MACD.

Output:
- Maximum 3 concise risk observations.
- Bullet points only.
- Under 100 words total.

Rules:
- Do not give advice.
- Do not predict profitability.
- Do not suggest alternative indicators.
- Do not mention indicators not supported (only RSI, SMA, EMA, MACD).
- Only comment on structural risk (e.g., no stop loss, missing exit).
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

Supported indicators ONLY: RSI, SMA, EMA, MACD.

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
- Do NOT mention indicators not in the JSON (only RSI, SMA, EMA, MACD supported).
- Do NOT hallucinate or add information not present.
- If a field is missing, say: "Not defined in this strategy."

Constraints:
- Maximum 120 words.
- Neutral tone.
- No disclaimers."""

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
# BACKTEST ROUTE
# =============================================================================

import yfinance as yf
import pandas as pd
import signal
from contextlib import contextmanager

# Safety limits
MAX_LOOKBACK = 200
MAX_EXECUTION_SECONDS = 30

class BacktestTimeoutError(Exception):
    pass

@contextmanager
def timeout_handler(seconds):
    """Context manager for execution timeout."""
    def handler(signum, frame):
        raise BacktestTimeoutError(f"Backtest exceeded {seconds}s limit")
    
    old_handler = signal.signal(signal.SIGALRM, handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)

class BacktestRequest(BaseModel):
    strategy: dict

class BacktestResponse(BaseModel):
    success: bool
    label: str
    disclaimer: str
    trades: list
    win_rate: float
    pnl: float
    total_trades: int
    wins: int
    losses: int
    data_source: str

def run_sma_backtest(symbol: str, short_period: int, long_period: int, max_candles: int = MAX_LOOKBACK):
    """Run simple SMA crossover backtest using yfinance data."""
    try:
        # Enforce max lookback limit
        max_candles = min(max_candles, MAX_LOOKBACK)
        
        # Map common crypto symbols to Yahoo Finance format
        yf_symbol = symbol
        if symbol in ["BTCUSDT", "BTC"]:
            yf_symbol = "BTC-USD"
        elif symbol in ["ETHUSDT", "ETH"]:
            yf_symbol = "ETH-USD"
        elif not "-" in symbol and not "." in symbol:
            # Try as stock symbol
            yf_symbol = symbol
        
        # Fetch data with timeout protection
        with timeout_handler(MAX_EXECUTION_SECONDS):
            ticker = yf.Ticker(yf_symbol)
            df = ticker.history(period="1y", interval="1d")
        
        if df.empty or len(df) < long_period + 10:
            return None
        
        # Limit to max candles
        df = df.tail(max_candles)
        
        # Calculate SMAs
        df['SMA_short'] = df['Close'].rolling(window=short_period).mean()
        df['SMA_long'] = df['Close'].rolling(window=long_period).mean()
        
        # Drop NaN rows
        df = df.dropna()
        
        if len(df) < 20:
            return None
        
        # Generate signals
        df['signal'] = 0
        df.loc[df['SMA_short'] > df['SMA_long'], 'signal'] = 1
        df.loc[df['SMA_short'] < df['SMA_long'], 'signal'] = -1
        
        # Find crossovers (signal changes)
        df['crossover'] = df['signal'].diff()
        
        trades = []
        position = None
        entry_price = 0
        entry_date = None
        
        for idx, row in df.iterrows():
            if row['crossover'] == 2:  # Buy signal (cross above)
                if position is None:
                    position = 'long'
                    entry_price = row['Close']
                    entry_date = idx.strftime('%Y-%m-%d')
            elif row['crossover'] == -2:  # Sell signal (cross below)
                if position == 'long':
                    exit_price = row['Close']
                    pnl_pct = ((exit_price - entry_price) / entry_price) * 100
                    trades.append({
                        'id': len(trades) + 1,
                        'symbol': symbol,
                        'entry': round(entry_price, 2),
                        'exit': round(exit_price, 2),
                        'pnl': round(pnl_pct, 2),
                        'result': 'WIN' if pnl_pct > 0 else 'LOSS',
                        'date': entry_date
                    })
                    position = None
        
        if not trades:
            return None
        
        wins = sum(1 for t in trades if t['result'] == 'WIN')
        total_pnl = sum(t['pnl'] for t in trades)
        
        return {
            'label': 'Basic Historical Backtest (Limited Accuracy)',
            'disclaimer': 'Simplified SMA crossover only. Does not account for fees, slippage, or market conditions.',
            'trades': trades,
            'win_rate': round((wins / len(trades)) * 100, 1),
            'pnl': round(total_pnl, 2),
            'total_trades': len(trades),
            'wins': wins,
            'losses': len(trades) - wins,
            'data_source': f'yfinance ({yf_symbol})'
        }
    except BacktestTimeoutError as e:
        logger.error(f"Backtest timeout: {e}")
        return None
    except Exception as e:
        logger.error(f"Backtest error: {e}")
        return None

def run_simulated_backtest(symbol: str, sl: float, tp: float):
    """Fallback simulated backtest."""
    try:
        import random
        num_trades = 10 + random.randint(0, 20)
        trades = []
        wins = 0
        total_pnl = 0
        
        for i in range(num_trades):
            is_win = random.random() > 0.45
            pnl = random.random() * tp if is_win else -(random.random() * sl)
            entry = 100 + random.random() * 50
            exit_price = entry * (1 + pnl / 100)
            
            if is_win:
                wins += 1
            total_pnl += pnl
            
            trades.append({
                'id': i + 1,
                'symbol': symbol,
                'entry': round(entry, 2),
                'exit': round(exit_price, 2),
                'pnl': round(pnl, 2),
                'result': 'WIN' if is_win else 'LOSS',
                'date': f'2025-{random.randint(1,12):02d}-{random.randint(1,28):02d}'
            })
        
        return {
            'label': 'Simulated Backtest (Not Real Data)',
            'disclaimer': 'Random simulation only. Not based on historical data.',
            'trades': trades,
            'win_rate': round((wins / num_trades) * 100, 1),
            'pnl': round(total_pnl, 2),
            'total_trades': num_trades,
            'wins': wins,
            'losses': num_trades - wins,
            'data_source': 'simulated'
        }
    except Exception as e:
        logger.error(f"Simulated backtest error: {e}")
        return {
            'label': 'Backtest Error',
            'disclaimer': 'An error occurred during backtest.',
            'trades': [],
            'win_rate': 0,
            'pnl': 0,
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'data_source': 'error'
        }

@api_router.post("/backtest", response_model=BacktestResponse)
async def run_backtest(request: BacktestRequest):
    try:
        strategy = request.strategy
        symbol = strategy.get('instrument', {}).get('symbol', 'BTCUSDT')
        entry_conditions = strategy.get('entry_conditions', [])
        sl = strategy.get('risk_management', {}).get('stop_loss') or 2
        tp = strategy.get('risk_management', {}).get('take_profit') or 5
        
        # Check if strategy uses SMA or EMA
        uses_ma = False
        short_period = 9
        long_period = 21
        
        for cond in entry_conditions:
            if cond.get('name') in ['SMA', 'EMA']:
                uses_ma = True
                params = cond.get('params', {})
                short_period = params.get('short', 9)
                long_period = params.get('long', 21)
                break
        
        result = None
        if uses_ma:
            result = run_sma_backtest(symbol, short_period, long_period, max_candles=MAX_LOOKBACK)
        
        # Fallback to simulated if historical fails or not MA strategy
        if result is None:
            result = run_simulated_backtest(symbol, sl, tp)
        
        return {"success": True, **result}
    except Exception as e:
        logger.error(f"Backtest endpoint error: {e}")
        return {
            "success": False,
            "label": "Backtest Error",
            "disclaimer": "An unexpected error occurred.",
            "trades": [],
            "win_rate": 0,
            "pnl": 0,
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "data_source": "error"
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


# =============================================================================
# INTERNAL TEST UTILITY
# =============================================================================

SAMPLE_STRATEGIES = [
    {
        "metadata": {"name": "AAPL SMA Crossover", "description": "Test strategy 1"},
        "market": {"type": "stocks", "exchange": "nasdaq"},
        "instrument": {"symbol": "AAPL"},
        "timeframe": {"interval": "1d"},
        "entry_conditions": [{"name": "SMA", "params": {"short": 10, "long": 30}, "operator": "cross_above"}],
        "exit_conditions": [],
        "filters": [],
        "risk_management": {"stop_loss": 2, "take_profit": 5}
    },
    {
        "metadata": {"name": "BTC RSI Strategy", "description": "Test strategy 2"},
        "market": {"type": "crypto", "exchange": "binance"},
        "instrument": {"symbol": "BTCUSDT"},
        "timeframe": {"interval": "1h"},
        "entry_conditions": [{"name": "RSI", "params": {"period": 14}, "operator": "<", "value": 30}],
        "exit_conditions": [],
        "filters": [],
        "risk_management": {"stop_loss": 3, "take_profit": 6}
    },
    {
        "metadata": {"name": "ETH EMA Crossover", "description": "Test strategy 3"},
        "market": {"type": "crypto", "exchange": "binance"},
        "instrument": {"symbol": "ETHUSDT"},
        "timeframe": {"interval": "4h"},
        "entry_conditions": [{"name": "EMA", "params": {"short": 12, "long": 26}, "operator": "cross_above"}],
        "exit_conditions": [],
        "filters": [{"name": "ADX", "params": {"period": 14}, "operator": ">", "value": 25}],
        "risk_management": {"stop_loss": 2, "take_profit": 4}
    }
]

def create_test_user():
    """Create a test user and return credentials."""
    test_email = "test@internal.dev"
    test_password = "test123"
    
    # Check if exists
    existing = next((u for u in users_db if u["email"] == test_email), None)
    if not existing:
        users_db.append({"email": test_email, "password": test_password})
        logger.info(f"[TEST] Created test user: {test_email}")
    else:
        logger.info(f"[TEST] Test user exists: {test_email}")
    
    return {"email": test_email, "password": test_password}

def run_internal_tests():
    """Run internal tests: create user, generate strategies, run backtests."""
    logger.info("=" * 60)
    logger.info("[TEST] Starting internal test suite")
    logger.info("=" * 60)
    
    # 1. Create test user
    user = create_test_user()
    logger.info(f"[TEST] User: {user['email']}")
    
    # 2. Create sample strategies
    created_strategies = []
    for strat_data in SAMPLE_STRATEGIES:
        strat_id = str(uuid.uuid4())[:8]
        strategy = {
            "id": strat_id,
            "version": "1.0",
            **strat_data
        }
        strategies_db.append(strategy)
        created_strategies.append(strategy)
        logger.info(f"[TEST] Created strategy: {strat_data['metadata']['name']} (id: {strat_id})")
    
    # 3. Run backtest on each
    logger.info("-" * 60)
    logger.info("[TEST] Running backtests...")
    
    for strategy in created_strategies:
        name = strategy["metadata"]["name"]
        symbol = strategy["instrument"]["symbol"]
        entry = strategy["entry_conditions"][0] if strategy["entry_conditions"] else {}
        indicator = entry.get("name", "N/A")
        
        # Determine backtest type
        if indicator in ["SMA", "EMA"]:
            params = entry.get("params", {})
            result = run_sma_backtest(symbol, params.get("short", 9), params.get("long", 21))
        else:
            sl = strategy["risk_management"].get("stop_loss", 2)
            tp = strategy["risk_management"].get("take_profit", 5)
            result = run_simulated_backtest(symbol, sl, tp)
        
        if result:
            logger.info(f"[TEST] {name} | {result['label']} | Trades: {result['total_trades']} | Win: {result['win_rate']}% | PnL: {result['pnl']}%")
        else:
            logger.info(f"[TEST] {name} | FAILED")
    
    logger.info("=" * 60)
    logger.info(f"[TEST] Complete. {len(created_strategies)} strategies created and tested.")
    logger.info("=" * 60)
    
    return {"user": user, "strategies": len(created_strategies)}

# Run tests on startup if TEST_MODE env is set
if os.environ.get("TEST_MODE") == "1":
    run_internal_tests()

