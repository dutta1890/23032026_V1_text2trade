"""Structured logging configuration with JSON format and request context."""

import logging
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Optional
from pythonjsonlogger import jsonlogger


# Context variables for request tracking
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)
endpoint_var: ContextVar[Optional[str]] = ContextVar("endpoint", default=None)


def get_request_id() -> Optional[str]:
    return request_id_var.get()

def set_request_id(request_id: str):
    request_id_var.set(request_id)

def get_user_id() -> Optional[str]:
    return user_id_var.get()

def set_user_id(user_id: str):
    user_id_var.set(user_id)

def get_endpoint() -> Optional[str]:
    return endpoint_var.get()

def set_endpoint(endpoint: str):
    endpoint_var.set(endpoint)

def generate_request_id() -> str:
    return str(uuid.uuid4())[:8]


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter that includes request context."""
    
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp
        log_record['timestamp'] = datetime.now(timezone.utc).isoformat()
        
        # Add log level
        log_record['level'] = record.levelname
        
        # Add request context
        log_record['request_id'] = get_request_id()
        log_record['user_id'] = get_user_id()
        log_record['endpoint'] = get_endpoint()
        
        # Clean up default fields
        if 'message' not in log_record:
            log_record['message'] = record.getMessage()


def setup_logging(level: str = "INFO"):
    """Configure structured JSON logging."""
    
    # Create formatter
    formatter = CustomJsonFormatter(
        fmt='%(timestamp)s %(level)s %(request_id)s %(user_id)s %(endpoint)s %(message)s'
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add stream handler with JSON formatter
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)
    
    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    return root_logger


def log_auth_attempt(email: str, success: bool, reason: Optional[str] = None):
    """Log authentication attempt."""
    logger = logging.getLogger(__name__)
    if success:
        logger.info(f"Auth success", extra={"auth_email": email, "auth_result": "success"})
    else:
        logger.warning(f"Auth failed", extra={"auth_email": email, "auth_result": "failure", "auth_reason": reason})


def log_ai_call(role: str, token_count: int, latency_ms: float, success: bool):
    """Log AI API call."""
    logger = logging.getLogger(__name__)
    logger.info(
        f"AI call completed",
        extra={
            "ai_role": role,
            "ai_tokens": token_count,
            "ai_latency_ms": latency_ms,
            "ai_success": success
        }
    )


def log_circuit_breaker_change(name: str, old_state: str, new_state: str):
    """Log circuit breaker state change."""
    logger = logging.getLogger(__name__)
    logger.warning(
        f"Circuit breaker state change",
        extra={
            "cb_name": name,
            "cb_old_state": old_state,
            "cb_new_state": new_state
        }
    )
