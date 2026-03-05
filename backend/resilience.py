"""Resilience, sanitization, and infrastructure utilities."""

import re
import asyncio
import time
import logging
from typing import Callable, Any, Optional, Dict
from functools import wraps
from datetime import datetime, timezone


# =============================================================================
# CUSTOM EXCEPTIONS
# =============================================================================

class ServiceTimeoutError(Exception):
    """Raised when a service call times out."""
    pass

class ServiceUnavailableError(Exception):
    """Raised when a service is unavailable after retries."""
    pass


# =============================================================================
# INPUT SANITIZATION
# =============================================================================

# Patterns that indicate prompt injection attempts
INJECTION_PATTERNS = [
    r"ignore\s+previous",
    r"ignore\s+all\s+prior",
    r"disregard\s+previous",
    r"forget\s+your\s+instructions",
    r"you\s+are\s+now",
    r"system\s*:",
    r"<\s*system\s*>",
    r"```\s*system",
    r"\[\s*system\s*\]",
    r"new\s+instructions\s*:",
    r"override\s+instructions",
]

def sanitize_user_input(text: str, max_length: int = 1000) -> str:
    """
    Sanitize user input before passing to AI prompts.
    - Strips injection patterns
    - Truncates to max_length
    - Removes markdown code fences containing 'system'
    """
    if not text:
        return ""
    
    # Truncate first
    text = text[:max_length]
    
    # Remove markdown code fences containing system
    text = re.sub(r'```[^`]*system[^`]*```', '[REMOVED]', text, flags=re.IGNORECASE | re.DOTALL)
    
    # Remove injection patterns
    for pattern in INJECTION_PATTERNS:
        text = re.sub(pattern, '[FILTERED]', text, flags=re.IGNORECASE)
    
    return text.strip()


# =============================================================================
# CIRCUIT BREAKER
# =============================================================================

class CircuitBreaker:
    """
    Circuit breaker pattern implementation.
    States: CLOSED (normal), OPEN (failing), HALF_OPEN (testing)
    """
    
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"
    
    def __init__(self, name: str, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = self.CLOSED
        self.logger = logging.getLogger(__name__)
    
    def record_success(self):
        """Record a successful call."""
        if self.state == self.HALF_OPEN:
            self.logger.info(f"Circuit breaker '{self.name}' closing after successful test call")
        self.failure_count = 0
        self.state = self.CLOSED
    
    def record_failure(self):
        """Record a failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            if self.state != self.OPEN:
                self.logger.warning(f"Circuit breaker '{self.name}' opening after {self.failure_count} failures")
            self.state = self.OPEN
    
    def can_execute(self) -> bool:
        """Check if a call can be made."""
        if self.state == self.CLOSED:
            return True
        
        if self.state == self.OPEN:
            # Check if recovery timeout has passed
            if self.last_failure_time and (time.time() - self.last_failure_time) >= self.recovery_timeout:
                self.logger.info(f"Circuit breaker '{self.name}' entering half-open state")
                self.state = self.HALF_OPEN
                return True
            return False
        
        # HALF_OPEN: allow one test call
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status."""
        return {
            "name": self.name,
            "state": self.state,
            "failure_count": self.failure_count,
            "last_failure": datetime.fromtimestamp(self.last_failure_time, tz=timezone.utc).isoformat() if self.last_failure_time else None
        }


# Global circuit breakers
circuit_breakers: Dict[str, CircuitBreaker] = {
    "ai": CircuitBreaker("ai", failure_threshold=5, recovery_timeout=60),
    "mongodb": CircuitBreaker("mongodb", failure_threshold=5, recovery_timeout=30),
    "datasource": CircuitBreaker("datasource", failure_threshold=5, recovery_timeout=60),
}


# =============================================================================
# RESILIENT CALL WRAPPER
# =============================================================================

async def resilient_call(
    func: Callable,
    *args,
    circuit_name: str = "default",
    max_retries: int = 3,
    base_delay: float = 1.0,
    timeout: float = 10.0,
    fallback: Any = None,
    **kwargs
) -> Any:
    """
    Execute a function with retry logic and circuit breaker.
    
    Args:
        func: The async function to call
        circuit_name: Name of the circuit breaker to use
        max_retries: Maximum number of retry attempts
        base_delay: Base delay for exponential backoff
        timeout: Timeout in seconds for each attempt
        fallback: Value to return if circuit is open
    """
    logger = logging.getLogger(__name__)
    
    # Get or create circuit breaker
    cb = circuit_breakers.get(circuit_name)
    if not cb:
        cb = CircuitBreaker(circuit_name)
        circuit_breakers[circuit_name] = cb
    
    # Check circuit breaker state
    if not cb.can_execute():
        logger.warning(f"Circuit breaker '{circuit_name}' is open, returning fallback")
        if fallback is not None:
            return fallback
        raise ServiceUnavailableError(f"Service '{circuit_name}' is currently unavailable")
    
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            # Execute with timeout
            if asyncio.iscoroutinefunction(func):
                result = await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
            else:
                # Wrap sync function in executor
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: func(*args, **kwargs)),
                    timeout=timeout
                )
            
            cb.record_success()
            return result
            
        except asyncio.TimeoutError:
            last_exception = ServiceTimeoutError(f"Call to '{circuit_name}' timed out after {timeout}s")
            cb.record_failure()
            logger.warning(f"Timeout on attempt {attempt + 1}/{max_retries} for '{circuit_name}'")
            
        except Exception as e:
            last_exception = e
            cb.record_failure()
            logger.warning(f"Error on attempt {attempt + 1}/{max_retries} for '{circuit_name}': {e}")
        
        # Exponential backoff
        if attempt < max_retries - 1:
            delay = base_delay * (2 ** attempt)
            await asyncio.sleep(delay)
    
    # All retries exhausted
    if isinstance(last_exception, ServiceTimeoutError):
        raise last_exception
    raise ServiceUnavailableError(f"Service '{circuit_name}' unavailable after {max_retries} retries: {last_exception}")


# =============================================================================
# SYNC WRAPPER FOR RESILIENT CALL
# =============================================================================

def resilient_call_sync(
    func: Callable,
    *args,
    circuit_name: str = "default",
    max_retries: int = 3,
    base_delay: float = 1.0,
    timeout: float = 10.0,
    fallback: Any = None,
    **kwargs
) -> Any:
    """Synchronous version of resilient_call for blocking operations."""
    logger = logging.getLogger(__name__)
    
    cb = circuit_breakers.get(circuit_name)
    if not cb:
        cb = CircuitBreaker(circuit_name)
        circuit_breakers[circuit_name] = cb
    
    if not cb.can_execute():
        logger.warning(f"Circuit breaker '{circuit_name}' is open, returning fallback")
        if fallback is not None:
            return fallback
        raise ServiceUnavailableError(f"Service '{circuit_name}' is currently unavailable")
    
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            result = func(*args, **kwargs)
            cb.record_success()
            return result
        except Exception as e:
            last_exception = e
            cb.record_failure()
            logger.warning(f"Error on attempt {attempt + 1}/{max_retries} for '{circuit_name}': {e}")
        
        if attempt < max_retries - 1:
            delay = base_delay * (2 ** attempt)
            time.sleep(delay)
    
    raise ServiceUnavailableError(f"Service '{circuit_name}' unavailable after {max_retries} retries: {last_exception}")
