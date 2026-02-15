import os
import logging
import asyncio
from emergentintegrations.llm.chat import LlmChat, UserMessage

logger = logging.getLogger(__name__)

MAX_INPUT_LENGTH = 4000
MAX_TOKENS = 500
TIMEOUT_SECONDS = 30

ROLES = {
    "parser": "strategy_parser",
    "explainer": "strategy_explainer", 
    "risk": "risk_analyzer"
}

async def call_ai(role, payload, system_prompt):
    # strips long inputs
    if isinstance(payload, str) and len(payload) > MAX_INPUT_LENGTH:
        payload = payload[:MAX_INPUT_LENGTH] + "...[truncated]"
    
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        logger.error("EMERGENT_LLM_KEY not configured")
        return None
    
    # try/except
    try:
        # sets temperature=0.2, max_tokens
        chat = LlmChat(
            api_key=api_key,
            session_id=ROLES.get(role, role),
            system_message=system_prompt
        ).with_model("openai", "gpt-5.2").with_params(
            temperature=0.2,
            max_tokens=MAX_TOKENS
        )
        
        user_message = UserMessage(text=payload)
        
        # timeout handling
        response = await asyncio.wait_for(
            chat.send_message(user_message),
            timeout=TIMEOUT_SECONDS
        )
        
        # logs usage
        logger.info(f"AI call [{role}]: input={len(payload)} chars, output={len(response)} chars")
        
        return response
        
    except asyncio.TimeoutError:
        logger.error(f"AI call [{role}]: timeout after {TIMEOUT_SECONDS}s")
        return None
    except Exception as e:
        logger.error(f"AI call [{role}]: error - {str(e)}")
        return None
