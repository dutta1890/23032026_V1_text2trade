"""Angel One SmartAPI integration — Phase 2 placeholder."""

from integrations import BrokerIntegration


class AngelOneIntegration(BrokerIntegration):
    """Angel One SmartAPI integration. NOT IMPLEMENTED — Phase 2."""

    BROKER_NAME = "angel_one"
    API_BASE = "https://apiconnect.angelbroking.com"

    def authenticate(self, user_id, oauth_code):
        raise NotImplementedError("Angel One integration is planned for Phase 2")

    def place_order(self, session, order):
        raise NotImplementedError("Angel One integration is planned for Phase 2")

    def get_positions(self, session):
        raise NotImplementedError("Angel One integration is planned for Phase 2")

    def cancel_order(self, session, order_id):
        raise NotImplementedError("Angel One integration is planned for Phase 2")

    def disconnect(self, session):
        raise NotImplementedError("Angel One integration is planned for Phase 2")

    def get_static_ip(self):
        raise NotImplementedError("Static IP not configured — Phase 2")
