"""Upstox API integration — Phase 2 placeholder."""

from integrations import BrokerIntegration


class UpstoxIntegration(BrokerIntegration):
    """Upstox API integration. NOT IMPLEMENTED — Phase 2."""

    BROKER_NAME = "upstox"
    API_BASE = "https://api.upstox.com/v2"

    def authenticate(self, user_id, oauth_code):
        raise NotImplementedError("Upstox integration is planned for Phase 2")

    def place_order(self, session, order):
        raise NotImplementedError("Upstox integration is planned for Phase 2")

    def get_positions(self, session):
        raise NotImplementedError("Upstox integration is planned for Phase 2")

    def cancel_order(self, session, order_id):
        raise NotImplementedError("Upstox integration is planned for Phase 2")

    def disconnect(self, session):
        raise NotImplementedError("Upstox integration is planned for Phase 2")

    def get_static_ip(self):
        raise NotImplementedError("Static IP not configured — Phase 2")
