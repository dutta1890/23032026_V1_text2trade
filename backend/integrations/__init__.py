"""Abstract broker integration interface — SEBI-compliant architecture for Phase 2.

SEBI Requirements this must satisfy:
- OAuth-based authentication (no open APIs)
- Static IP whitelisting
- 2FA verification
- Algo-ID tagging on every order
- Daily session auto-logout
- 5-year audit trail for all orders

This module defines the base class only. No actual broker connections are implemented.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class BrokerSession(BaseModel):
    session_id: str
    user_id: str
    broker: str
    access_token_encrypted: str
    static_ip: Optional[str] = None
    two_factor_verified: bool = False
    connected_at: str
    expires_at: Optional[str] = None


class Order(BaseModel):
    symbol: str
    exchange: str
    order_type: str          # MARKET, LIMIT, SL, SL-M
    transaction_type: str    # BUY, SELL
    quantity: int
    price: Optional[float] = None
    trigger_price: Optional[float] = None
    algo_id: str             # MANDATORY: exchange-assigned ID (SEBI requirement)
    strategy_id: str
    tag: Optional[str] = None


class OrderResult(BaseModel):
    order_id: str
    status: str              # PLACED, REJECTED, CANCELLED
    message: Optional[str] = None
    exchange_timestamp: Optional[str] = None
    filled_quantity: int = 0
    average_price: float = 0.0


class Position(BaseModel):
    symbol: str
    exchange: str
    quantity: int
    average_price: float
    pnl: float
    last_price: float


class BrokerIntegration(ABC):
    """Base class for all broker integrations. Phase 2 implementation."""

    @abstractmethod
    def authenticate(self, user_id: str, oauth_code: str) -> BrokerSession:
        """OAuth callback handler. User authenticates on broker site, we receive code."""

    @abstractmethod
    def place_order(self, session: BrokerSession, order: Order) -> OrderResult:
        """Place order with mandatory algo_id tag."""

    @abstractmethod
    def get_positions(self, session: BrokerSession) -> List[Position]:
        """Fetch current positions."""

    @abstractmethod
    def cancel_order(self, session: BrokerSession, order_id: str) -> bool:
        """Cancel pending order."""

    @abstractmethod
    def disconnect(self, session: BrokerSession) -> bool:
        """Logout and revoke session."""

    @abstractmethod
    def get_static_ip(self) -> str:
        """Return the static IP this connection routes through."""
