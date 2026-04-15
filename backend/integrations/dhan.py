"""Dhan API integration — Phase 2 placeholder."""

from integrations import BrokerIntegration


class DhanIntegration(BrokerIntegration):
    """Dhan HQ API integration. NOT IMPLEMENTED — Phase 2."""

    BROKER_NAME = "dhan"
    API_BASE = "https://api.dhan.co"

    def authenticate(self, user_id, oauth_code):
        raise NotImplementedError("Dhan integration is planned for Phase 2")

    def place_order(self, session, order):
        raise NotImplementedError("Dhan integration is planned for Phase 2")

    def get_positions(self, session):
        raise NotImplementedError("Dhan integration is planned for Phase 2")

    def cancel_order(self, session, order_id):
        raise NotImplementedError("Dhan integration is planned for Phase 2")

    def disconnect(self, session):
        raise NotImplementedError("Dhan integration is planned for Phase 2")

    def get_static_ip(self):
        raise NotImplementedError("Static IP not configured — Phase 2")
