"""AI endpoints: NL parser, risk analyzer, strategy explainer, session management."""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
import os
import json
import time
import uuid
import logging

from emergentintegrations.llm.chat import LlmChat, UserMessage
from auth import get_current_user
from resilience import (
    sanitize_user_input, resilient_call,
    ServiceTimeoutError, ServiceUnavailableError
)
from logging_config import log_ai_call
from ai_sessions import (
    get_ai_config, check_and_increment_usage, get_usage_stats,
    create_session, get_session, append_message, update_strategy_draft,
    delete_session, get_context_messages
)
from database import strategies_collection, analytics_db

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# PROMPTS
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

EXPLAIN_PROMPT = """You are a trading strategy explainer.

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
- Never give financial advice. Never predict profits.

TEMPLATES (suggest when user is vague or exploring):
If the user's request is vague (e.g., "I want a simple strategy", "something for beginners", "trend following"), suggest relevant templates from this list:
1. Golden Cross (Trend) - SMA 50/200 crossover, 3% SL
2. RSI Mean Reversion - Buy RSI<30, sell RSI>70, 2% SL
3. Supertrend Follower (Trend) - Supertrend buy/sell signals, 1.5% TSL
4. MACD Momentum - MACD cross + ADX>25 filter, 2.5% SL
5. Bollinger Bounce (Mean Reversion) - Lower band touch + RSI<35, 2% SL
6. VWAP Intraday - VWAP crossover, 15:10 time exit, 1% SL
7. Pivot Breakout - Above R1 entry, 1.5% SL
8. Stochastic Reversal - K crosses D in oversold zone, 2% SL
9. ATR Volatility - EMA crossover + ATR filter, ATR-based SL
10. CCI Breakout (Momentum) - CCI crosses +100, 3% SL
11. Supertrend + RSI (Combined) - Supertrend + RSI>50 filter, 2% TSL
12. EMA Ribbon (Trend) - EMA 9/21/55 ribbon, 2.5% SL
When suggesting templates, respond: { "mode": "question", "message": "Based on your interest, here are some templates you might like: ...", "fields_needed": ["template_choice"] }
If the user picks a template, still ask about instrument and any customizations before returning a strategy JSON."""


# =============================================================================
# HELPERS
# =============================================================================

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
    invalid = []
    for cond_list_key in ("entry_conditions", "exit_conditions", "filters"):
        for cond in strategy_data.get(cond_list_key, []):
            name = cond.get("name") or cond.get("indicator") or ""
            if name and name not in SUPPORTED_INDICATORS:
                invalid.append(name)
    return invalid


def _parse_ai_json(text: str) -> dict:
    import re
    cleaned = text.strip()
    match = re.search(r'```(?:json)?\s*([\s\S]*?)```', cleaned)
    if match:
        cleaned = match.group(1).strip()
    start = cleaned.find('{')
    if start == -1:
        return None
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
    name = cond.get("name") or cond.get("indicator") or ""
    raw_params = cond.get("params", {})
    params = {}
    for k, v in raw_params.items():
        if k == "length":
            params["period"] = v
        else:
            params[k] = v
    operator = cond.get("operator", "")
    value = cond.get("value")
    result = {"name": name, "params": params, "operator": operator}
    if value is not None:
        result["value"] = value
    return result


def _normalize_ai_strategy(draft: dict) -> dict:
    normalized = {}
    inst = draft.get("instrument", {})
    if isinstance(inst, str):
        normalized["instrument"] = {"symbol": inst}
    else:
        normalized["instrument"] = {"symbol": inst.get("symbol", ""), "base": None, "quote": None}

    tf = draft.get("timeframe", "1d")
    if isinstance(tf, dict):
        normalized["timeframe"] = tf
    else:
        normalized["timeframe"] = {"interval": tf, "candle_count": None}

    normalized["entry_conditions"] = []
    for c in draft.get("entry_conditions", []):
        ind_name = c.get("name") or c.get("indicator") or ""
        if ind_name in SUPPORTED_INDICATORS:
            normalized["entry_conditions"].append(_normalize_ai_condition(c))

    normalized["exit_conditions"] = []
    for c in draft.get("exit_conditions", []):
        ctype = c.get("type", "")
        if ctype in ("take_profit", "stop_loss"):
            continue
        ind_name = c.get("name") or c.get("indicator") or ""
        if ind_name in SUPPORTED_INDICATORS:
            normalized["exit_conditions"].append(_normalize_ai_condition(c))

    normalized["filters"] = []
    for c in draft.get("filters", []):
        ind_name = c.get("name") or c.get("indicator") or ""
        if ind_name in SUPPORTED_INDICATORS:
            normalized["filters"].append(_normalize_ai_condition(c))

    rm = draft.get("risk_management", {})
    sl = rm.get("stop_loss")
    tp = rm.get("take_profit")
    trailing = rm.get("trailing_stop") or rm.get("trailing_stop_loss")
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


# =============================================================================
# MODELS
# =============================================================================

class ParseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(max_length=2000)

class ParseResponse(BaseModel):
    success: bool
    parsed: Optional[dict] = None
    error: Optional[str] = None

class RiskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    strategy: dict

class RiskResponse(BaseModel):
    success: bool
    warnings: list

class ExplainRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    strategy: dict
    question: str = Field(max_length=500)

class ExplainResponse(BaseModel):
    success: bool
    answer: str

class SessionMessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(max_length=1000)

class SessionMessageResponse(BaseModel):
    mode: str
    content: dict
    session_id: str
    strategy_draft: Optional[dict] = None

class DraftUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    strategy_draft: dict


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/parse-strategy", response_model=ParseResponse)
async def parse_strategy(request: Request, body: ParseRequest, current_user: dict = Depends(get_current_user)):
    user_email = current_user.get("email", "anonymous")
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
        api_key=api_key, session_id=str(uuid.uuid4()), system_message=PARSER_PROMPT
    ).with_model("openai", "gpt-5.2").with_params(max_tokens=ai_config["max_tokens"], temperature=ai_config["temperature"])

    start_time = time.time()
    try:
        response = await resilient_call(
            chat.send_message, UserMessage(text=sanitized_text),
            circuit_name="ai", max_retries=2, timeout=30.0, fallback=None
        )
        if response is None:
            raise HTTPException(status_code=503, detail="AI service temporarily unavailable")
        log_ai_call("parser", len(sanitized_text), (time.time() - start_time) * 1000, True)
    except (ServiceTimeoutError, ServiceUnavailableError) as e:
        log_ai_call("parser", len(sanitized_text), (time.time() - start_time) * 1000, False)
        raise HTTPException(status_code=503, detail=str(e))

    try:
        parsed = json.loads(response)
        return {"success": True, "parsed": parsed}
    except json.JSONDecodeError:
        import re
        match = re.search(r'\{[\s\S]*\}', response)
        if match:
            try:
                parsed = json.loads(match.group())
                return {"success": True, "parsed": parsed}
            except json.JSONDecodeError:
                pass
        return {"success": False, "error": "Invalid JSON response", "parsed": None}


@router.post("/analyze-risk", response_model=RiskResponse)
async def analyze_risk(request: Request, body: RiskRequest, current_user: dict = Depends(get_current_user)):
    user_email = current_user.get("email", "anonymous")
    if not check_and_increment_usage(user_email, "risk_analyzer"):
        raise HTTPException(status_code=429, detail="Daily limit for risk analysis reached (10/day). Try again tomorrow.")

    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="LLM key not configured")

    ai_config = get_ai_config("risk_analyzer")
    chat = LlmChat(
        api_key=api_key, session_id=str(uuid.uuid4()), system_message=RISK_PROMPT
    ).with_model("openai", "gpt-5.2").with_params(max_tokens=ai_config["max_tokens"], temperature=ai_config["temperature"])

    strategy_text = json.dumps(body.strategy, indent=2)
    sanitized_text = sanitize_user_input(strategy_text, max_length=5000)

    start_time = time.time()
    try:
        response = await resilient_call(
            chat.send_message, UserMessage(text=sanitized_text),
            circuit_name="ai", max_retries=2, timeout=30.0, fallback=None
        )
        if response is None:
            raise HTTPException(status_code=503, detail="AI service temporarily unavailable")
        log_ai_call("risk_analyzer", len(sanitized_text), (time.time() - start_time) * 1000, True)
    except (ServiceTimeoutError, ServiceUnavailableError) as e:
        log_ai_call("risk_analyzer", len(sanitized_text), (time.time() - start_time) * 1000, False)
        raise HTTPException(status_code=503, detail=str(e))

    lines = [l.strip().lstrip("•-*").strip() for l in response.split("\n") if l.strip() and l.strip()[0] in "•-*"]
    warnings = lines[:3] if lines else [response.strip()]
    return {"success": True, "warnings": warnings}


@router.post("/explain", response_model=ExplainResponse)
async def explain_strategy(request: Request, body: ExplainRequest, current_user: dict = Depends(get_current_user)):
    user_email = current_user.get("email", "anonymous")
    if not check_and_increment_usage(user_email, "explainer"):
        raise HTTPException(status_code=429, detail="Daily limit for strategy explanations reached (10/day). Try again tomorrow.")

    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="LLM key not configured")

    ai_config = get_ai_config("explainer")
    chat = LlmChat(
        api_key=api_key, session_id=str(uuid.uuid4()), system_message=EXPLAIN_PROMPT
    ).with_model("openai", "gpt-5.2").with_params(max_tokens=ai_config["max_tokens"], temperature=ai_config["temperature"])

    sanitized_question = sanitize_user_input(body.question, max_length=500)
    strategy_text = sanitize_user_input(json.dumps(body.strategy, indent=2), max_length=5000)
    prompt = f"Strategy JSON:\n{strategy_text}\n\nUser question: {sanitized_question}"

    start_time = time.time()
    try:
        response = await resilient_call(
            chat.send_message, UserMessage(text=prompt),
            circuit_name="ai", max_retries=2, timeout=30.0, fallback=None
        )
        if response is None:
            raise HTTPException(status_code=503, detail="AI service temporarily unavailable")
        log_ai_call("explainer", len(prompt), (time.time() - start_time) * 1000, True)
    except (ServiceTimeoutError, ServiceUnavailableError) as e:
        log_ai_call("explainer", len(prompt), (time.time() - start_time) * 1000, False)
        raise HTTPException(status_code=503, detail=str(e))

    return {"success": True, "answer": response}


# =============================================================================
# SESSION MANAGEMENT
# =============================================================================

@router.post("/session/start")
async def start_session_endpoint(request: Request, current_user: dict = Depends(get_current_user)):
    return create_session(current_user.get("email"))


@router.post("/session/{session_id}/message")
async def send_session_message(request: Request, session_id: str, body: SessionMessageRequest, current_user: dict = Depends(get_current_user)):
    user_email = current_user.get("email")
    session = get_session(session_id, user_email)
    if session == "forbidden":
        raise HTTPException(status_code=403, detail="Access denied to this session")
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if not check_and_increment_usage(user_email, "session_chat"):
        raise HTTPException(status_code=429, detail="Daily session chat limit reached (30/day). Try again tomorrow.")

    sanitized = sanitize_user_input(body.message, max_length=1000)
    if not sanitized:
        raise HTTPException(status_code=400, detail="Message is empty or invalid")

    append_message(session_id, user_email, "user", sanitized)
    context_msgs = get_context_messages(session_id, user_email, max_messages=6, token_budget=500)

    context_parts = []
    for msg in context_msgs[:-1]:
        prefix = "User" if msg["role"] == "user" else "Assistant"
        context_parts.append(f"{prefix}: {msg['content']}")
    context_str = "\n".join(context_parts) if context_parts else ""
    full_prompt = f"{context_str}\nUser: {sanitized}" if context_str else sanitized

    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="LLM key not configured")

    ai_config = get_ai_config("session_chat")
    ai_text = await _call_session_ai(api_key, session_id, full_prompt, ai_config)

    parsed = _parse_ai_json(ai_text)
    if parsed is None:
        parsed = {"mode": "question", "message": ai_text, "fields_needed": []}

    mode = parsed.get("mode", "question")

    if mode == "strategy":
        strategy_data = parsed.get("strategy", {})
        errors = _validate_strategy_draft(strategy_data)
        if errors:
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
                parsed = {"mode": "error", "message": f"Strategy validation failed: {'; '.join(errors)}"}
                mode = "error"
            else:
                mode = "strategy"

        if mode == "strategy":
            update_strategy_draft(session_id, user_email, strategy_data)

    append_message(session_id, user_email, "assistant", json.dumps(parsed) if isinstance(parsed, dict) else ai_text)

    return SessionMessageResponse(
        mode=mode, content=parsed, session_id=session_id,
        strategy_draft=parsed.get("strategy") if mode == "strategy" else None,
    )


async def _call_session_ai(api_key: str, session_id: str, prompt: str, ai_config: dict) -> str:
    chat = LlmChat(
        api_key=api_key, session_id=session_id, system_message=NL_BUILDER_SYSTEM_PROMPT,
    ).with_model("openai", "gpt-5.2").with_params(max_tokens=ai_config["max_tokens"], temperature=ai_config["temperature"])

    start_time = time.time()
    try:
        response = await resilient_call(
            chat.send_message, UserMessage(text=prompt),
            circuit_name="ai", max_retries=2, timeout=30.0, fallback=None,
        )
        if response is None:
            raise HTTPException(status_code=503, detail="AI service temporarily unavailable")
        log_ai_call("session_chat", len(prompt), (time.time() - start_time) * 1000, True)
    except (ServiceTimeoutError, ServiceUnavailableError) as e:
        log_ai_call("session_chat", len(prompt), (time.time() - start_time) * 1000, False)
        raise HTTPException(status_code=503, detail=str(e))

    return response if isinstance(response, str) else str(response)


@router.post("/session/{session_id}/finalize")
async def finalize_session_strategy(request: Request, session_id: str, current_user: dict = Depends(get_current_user)):
    user_email = current_user.get("email")
    session = get_session(session_id, user_email)
    if session == "forbidden":
        raise HTTPException(status_code=403, detail="Access denied to this session")
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    draft = session.get("strategy_draft")
    if not draft:
        raise HTTPException(status_code=400, detail="No strategy draft in this session. Continue the conversation to build one.")

    normalized = _normalize_ai_strategy(draft)
    errors = _validate_strategy_draft(normalized)
    if errors:
        raise HTTPException(status_code=422, detail=f"Draft has errors: {'; '.join(errors)}")

    from datetime import datetime, timezone
    strategy_id = str(uuid.uuid4())
    user_id = current_user.get("user_id", user_email)
    symbol = normalized["instrument"].get("symbol", "UNKNOWN")
    timeframe_val = normalized["timeframe"]
    if isinstance(timeframe_val, dict):
        timeframe_val = timeframe_val.get("interval", "1d")

    strategy_doc = {
        "id": strategy_id, "user_id": user_id, "version": "1.0",
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
    return {"success": True, "strategy_id": strategy_id, "message": f"Strategy saved for {symbol}."}


@router.put("/session/{session_id}/draft")
async def update_session_draft_endpoint(request: Request, session_id: str, body: DraftUpdateRequest, current_user: dict = Depends(get_current_user)):
    user_email = current_user.get("email")
    session = get_session(session_id, user_email)
    if session == "forbidden":
        raise HTTPException(status_code=403, detail="Access denied to this session")
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    errors = _validate_strategy_draft(body.strategy_draft)
    if errors:
        raise HTTPException(status_code=422, detail=f"Draft has errors: {'; '.join(errors)}")

    update_strategy_draft(session_id, user_email, body.strategy_draft)
    return {"success": True, "message": "Draft updated.", "strategy_draft": body.strategy_draft}


@router.get("/session/{session_id}")
async def get_session_endpoint(request: Request, session_id: str, current_user: dict = Depends(get_current_user)):
    user_email = current_user.get("email")
    session = get_session(session_id, user_email)
    if session == "forbidden":
        raise HTTPException(status_code=403, detail="Access denied to this session")
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.delete("/session/{session_id}")
async def delete_session_endpoint(request: Request, session_id: str, current_user: dict = Depends(get_current_user)):
    user_email = current_user.get("email")
    session = get_session(session_id, user_email)
    if session == "forbidden":
        raise HTTPException(status_code=403, detail="Access denied to this session")
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    delete_session(session_id, user_email)
    return {"success": True, "message": "Session deleted"}


@router.get("/ai/usage")
async def get_ai_usage(request: Request, current_user: dict = Depends(get_current_user)):
    return get_usage_stats(current_user.get("email"))
