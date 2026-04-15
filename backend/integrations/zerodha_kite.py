"""Zerodha Kite integration — Phase 2 placeholder.

Implements BrokerIntegration for Zerodha's Kite Connect API.
OAuth flow: https://kite.trade/docs/connect/v3/
"""

from integrations import BrokerIntegration


class ZerodhaIntegration(BrokerIntegration):
    """Zerodha Kite Connect integration. NOT IMPLEMENTED — Phase 2."""

    BROKER_NAME = "zerodha"
    API_BASE = "https://api.kite.trade"
    LOGIN_URL = "https://kite.zerodha.com/connect/login"

    def authenticate(self, user_id, oauth_code):
        raise NotImplementedError("Zerodha integration is planned for Phase 2")

    def place_order(self, session, order):
        raise NotImplementedError("Zerodha integration is planned for Phase 2")

    def get_positions(self, session):
        raise NotImplementedError("Zerodha integration is planned for Phase 2")

    def cancel_order(self, session, order_id):
        raise NotImplementedError("Zerodha integration is planned for Phase 2")

    def disconnect(self, session):
        raise NotImplementedError("Zerodha integration is planned for Phase 2")

    def get_static_ip(self):
        raise NotImplementedError("Static IP not configured — Phase 2")
