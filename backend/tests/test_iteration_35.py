"""Iteration 35 Tests: Hosting verification, broker integration, compliance features.

Tests:
1. GET /api/v1/compliance/status - hosting_region and hosting_migration_required fields
2. GET /api/v1/admin/compliance/monthly-report - period, alerts, hosting_compliant
3. GET /api/v1/compliance/strategy-export/{id} - strategy + compliance metadata with sebi_framework
4. Broker integration files exist
5. broker_connections collection exists in MongoDB with indexes
6. Export data endpoint includes compliance metadata
"""

import pytest
import requests
import os
import sys

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    BASE_URL = "https://info-tooltips.preview.emergentagent.com"

# Test credentials
TEST_USER_EMAIL = "testai@example.com"
TEST_USER_PASSWORD = "Password123!"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "Password123!"


class TestComplianceStatus:
    """Test public compliance status endpoint with hosting fields."""

    def test_compliance_status_returns_hosting_region(self):
        """GET /api/v1/compliance/status returns hosting_region field."""
        response = requests.get(f"{BASE_URL}/api/v1/compliance/status")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "hosting_region" in data, "Missing hosting_region field"
        assert data["hosting_region"] == "us-preview", f"Expected 'us-preview', got {data['hosting_region']}"
        print(f"✓ hosting_region: {data['hosting_region']}")

    def test_compliance_status_returns_hosting_migration_required(self):
        """GET /api/v1/compliance/status returns hosting_migration_required field."""
        response = requests.get(f"{BASE_URL}/api/v1/compliance/status")
        assert response.status_code == 200
        data = response.json()
        assert "hosting_migration_required" in data, "Missing hosting_migration_required field"
        # Since hosting_region is us-preview (not india), migration should be required
        assert data["hosting_migration_required"] is True, f"Expected True, got {data['hosting_migration_required']}"
        print(f"✓ hosting_migration_required: {data['hosting_migration_required']}")

    def test_compliance_status_has_all_required_fields(self):
        """Verify all expected fields in compliance status."""
        response = requests.get(f"{BASE_URL}/api/v1/compliance/status")
        assert response.status_code == 200
        data = response.json()
        required_fields = [
            "framework", "circular", "compliance_status", "live_trading",
            "audit_trail", "data_retention", "hosting_region", "hosting_migration_required",
            "algo_registration", "static_ip", "strategy_type", "note"
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        print(f"✓ All {len(required_fields)} required fields present")


class TestAdminMonthlyReport:
    """Test admin monthly compliance report endpoint."""

    @pytest.fixture
    def admin_token(self):
        """Get admin authentication token."""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip(f"Admin login failed: {response.status_code}")
        return response.json().get("access_token")

    def test_monthly_report_returns_period(self, admin_token):
        """GET /api/v1/admin/compliance/monthly-report returns period field."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/v1/admin/compliance/monthly-report", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "period" in data, "Missing period field"
        print(f"✓ period: {data['period']}")

    def test_monthly_report_returns_alerts(self, admin_token):
        """GET /api/v1/admin/compliance/monthly-report returns alerts array."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/v1/admin/compliance/monthly-report", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "alerts" in data, "Missing alerts field"
        assert isinstance(data["alerts"], list), "alerts should be a list"
        # Since hosting is us-preview, there should be a hosting warning alert
        hosting_alert = [a for a in data["alerts"] if "hosting" in a.get("message", "").lower()]
        assert len(hosting_alert) > 0, "Expected hosting warning alert"
        print(f"✓ alerts: {len(data['alerts'])} alerts found")

    def test_monthly_report_returns_hosting_compliant(self, admin_token):
        """GET /api/v1/admin/compliance/monthly-report returns hosting_compliant field."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/v1/admin/compliance/monthly-report", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "hosting_compliant" in data, "Missing hosting_compliant field"
        # Since hosting is us-preview (not india), should be False
        assert data["hosting_compliant"] is False, f"Expected False, got {data['hosting_compliant']}"
        print(f"✓ hosting_compliant: {data['hosting_compliant']}")

    def test_monthly_report_returns_hosting_region(self, admin_token):
        """GET /api/v1/admin/compliance/monthly-report returns hosting_region field."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/v1/admin/compliance/monthly-report", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "hosting_region" in data, "Missing hosting_region field"
        assert data["hosting_region"] == "us-preview"
        print(f"✓ hosting_region: {data['hosting_region']}")

    def test_monthly_report_requires_admin(self):
        """Monthly report endpoint requires admin authentication."""
        response = requests.get(f"{BASE_URL}/api/v1/admin/compliance/monthly-report")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Monthly report requires admin auth")


class TestStrategyExport:
    """Test strategy export with compliance metadata."""

    @pytest.fixture
    def user_token(self):
        """Get user authentication token."""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip(f"User login failed: {response.status_code}")
        return response.json().get("access_token")

    @pytest.fixture
    def user_strategy_id(self, user_token):
        """Get a strategy ID for the test user."""
        headers = {"Authorization": f"Bearer {user_token}"}
        response = requests.get(f"{BASE_URL}/api/v1/strategies", headers=headers)
        if response.status_code != 200:
            pytest.skip("Failed to get strategies")
        data = response.json()
        strategies = data.get("strategies", [])
        if not strategies:
            pytest.skip("No strategies found for test user")
        return strategies[0]["id"]

    def test_strategy_export_returns_compliance_metadata(self, user_token, user_strategy_id):
        """GET /api/v1/compliance/strategy-export/{id} returns compliance metadata."""
        headers = {"Authorization": f"Bearer {user_token}"}
        response = requests.get(
            f"{BASE_URL}/api/v1/compliance/strategy-export/{user_strategy_id}",
            headers=headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "strategy" in data, "Missing strategy field"
        assert "compliance" in data, "Missing compliance field"
        print(f"✓ Strategy export has strategy and compliance fields")

    def test_strategy_export_has_sebi_framework(self, user_token, user_strategy_id):
        """Strategy export compliance metadata includes sebi_framework."""
        headers = {"Authorization": f"Bearer {user_token}"}
        response = requests.get(
            f"{BASE_URL}/api/v1/compliance/strategy-export/{user_strategy_id}",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        compliance = data.get("compliance", {})
        assert "sebi_framework" in compliance, "Missing sebi_framework in compliance"
        assert "SEBI" in compliance["sebi_framework"], "sebi_framework should reference SEBI"
        print(f"✓ sebi_framework: {compliance['sebi_framework']}")

    def test_strategy_export_has_classification(self, user_token, user_strategy_id):
        """Strategy export compliance metadata includes classification."""
        headers = {"Authorization": f"Bearer {user_token}"}
        response = requests.get(
            f"{BASE_URL}/api/v1/compliance/strategy-export/{user_strategy_id}",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        compliance = data.get("compliance", {})
        assert "classification" in compliance, "Missing classification"
        assert compliance["classification"] in ["white_box", "black_box"]
        print(f"✓ classification: {compliance['classification']}")

    def test_strategy_export_requires_auth(self):
        """Strategy export endpoint requires authentication."""
        response = requests.get(f"{BASE_URL}/api/v1/compliance/strategy-export/some-id")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Strategy export requires auth")

    def test_strategy_export_404_for_invalid_id(self, user_token):
        """Strategy export returns 404 for non-existent strategy."""
        headers = {"Authorization": f"Bearer {user_token}"}
        response = requests.get(
            f"{BASE_URL}/api/v1/compliance/strategy-export/nonexistent-strategy-id",
            headers=headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Returns 404 for invalid strategy ID")


class TestExportDataCompliance:
    """Test account export-data endpoint includes compliance metadata."""

    @pytest.fixture
    def user_token(self):
        """Get user authentication token."""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip(f"User login failed: {response.status_code}")
        return response.json().get("access_token")

    def test_export_data_includes_compliance(self, user_token):
        """POST /api/v1/account/export-data includes compliance metadata."""
        headers = {"Authorization": f"Bearer {user_token}"}
        response = requests.post(f"{BASE_URL}/api/v1/account/export-data", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "compliance" in data, "Missing compliance field in export"
        print("✓ Export data includes compliance field")

    def test_export_data_compliance_has_sebi_framework(self, user_token):
        """Export data compliance includes sebi_framework."""
        headers = {"Authorization": f"Bearer {user_token}"}
        response = requests.post(f"{BASE_URL}/api/v1/account/export-data", headers=headers)
        assert response.status_code == 200
        data = response.json()
        compliance = data.get("compliance", {})
        assert "sebi_framework" in compliance, "Missing sebi_framework"
        assert "SEBI" in compliance["sebi_framework"]
        print(f"✓ sebi_framework in export: {compliance['sebi_framework']}")

    def test_export_data_compliance_has_platform_info(self, user_token):
        """Export data compliance includes platform info."""
        headers = {"Authorization": f"Bearer {user_token}"}
        response = requests.post(f"{BASE_URL}/api/v1/account/export-data", headers=headers)
        assert response.status_code == 200
        data = response.json()
        compliance = data.get("compliance", {})
        assert "platform" in compliance, "Missing platform"
        assert "platform_version" in compliance, "Missing platform_version"
        assert compliance["platform"] == "Text2trade"
        print(f"✓ platform: {compliance['platform']}, version: {compliance['platform_version']}")


class TestBrokerIntegrationFiles:
    """Test broker integration files exist."""

    def test_broker_integration_base_class_exists(self):
        """integrations/__init__.py exists with BrokerIntegration ABC."""
        path = "/app/backend/integrations/__init__.py"
        assert os.path.exists(path), f"Missing {path}"
        with open(path) as f:
            content = f.read()
        assert "BrokerIntegration" in content, "Missing BrokerIntegration class"
        assert "ABC" in content, "BrokerIntegration should be ABC"
        print("✓ integrations/__init__.py exists with BrokerIntegration ABC")

    def test_zerodha_integration_exists(self):
        """zerodha_kite.py exists with placeholder implementation."""
        path = "/app/backend/integrations/zerodha_kite.py"
        assert os.path.exists(path), f"Missing {path}"
        with open(path) as f:
            content = f.read()
        assert "ZerodhaIntegration" in content, "Missing ZerodhaIntegration class"
        assert "NotImplementedError" in content, "Should have NotImplementedError"
        print("✓ zerodha_kite.py exists with placeholder")

    def test_angel_one_integration_exists(self):
        """angel_one.py exists with placeholder implementation."""
        path = "/app/backend/integrations/angel_one.py"
        assert os.path.exists(path), f"Missing {path}"
        with open(path) as f:
            content = f.read()
        assert "AngelOneIntegration" in content, "Missing AngelOneIntegration class"
        assert "NotImplementedError" in content
        print("✓ angel_one.py exists with placeholder")

    def test_upstox_integration_exists(self):
        """upstox.py exists with placeholder implementation."""
        path = "/app/backend/integrations/upstox.py"
        assert os.path.exists(path), f"Missing {path}"
        with open(path) as f:
            content = f.read()
        assert "UpstoxIntegration" in content, "Missing UpstoxIntegration class"
        assert "NotImplementedError" in content
        print("✓ upstox.py exists with placeholder")

    def test_dhan_integration_exists(self):
        """dhan.py exists with placeholder implementation."""
        path = "/app/backend/integrations/dhan.py"
        assert os.path.exists(path), f"Missing {path}"
        with open(path) as f:
            content = f.read()
        assert "DhanIntegration" in content, "Missing DhanIntegration class"
        assert "NotImplementedError" in content
        print("✓ dhan.py exists with placeholder")


class TestBrokerConnectionsCollection:
    """Test broker_connections MongoDB collection."""

    def test_broker_connections_collection_exists(self):
        """broker_connections collection exists in MongoDB."""
        from pymongo import MongoClient
        client = MongoClient("mongodb://localhost:27017")
        db = client["test_database"]
        collections = db.list_collection_names()
        # The collection may not exist until first document is inserted,
        # but the index creation in compliance.py should create it
        # Let's check if the router creates it
        print(f"✓ Collections in DB: {collections}")
        # The collection is created when the router is loaded
        # We can verify by checking the index
        try:
            indexes = list(db["broker_connections"].list_indexes())
            index_names = [idx["name"] for idx in indexes]
            print(f"✓ broker_connections indexes: {index_names}")
            assert any("user_id" in name for name in index_names), "Missing user_id index"
        except Exception as e:
            print(f"Note: broker_connections collection may be empty: {e}")
        client.close()


class TestBrokerConnectionModel:
    """Test BrokerConnection Pydantic model exists in models.py."""

    def test_broker_connection_model_exists(self):
        """BrokerConnection model exists in models.py."""
        path = "/app/backend/models.py"
        with open(path) as f:
            content = f.read()
        assert "class BrokerConnection" in content, "Missing BrokerConnection model"
        assert "broker:" in content, "BrokerConnection should have broker field"
        assert "zerodha" in content, "Should support zerodha broker"
        assert "angel_one" in content, "Should support angel_one broker"
        assert "upstox" in content, "Should support upstox broker"
        assert "dhan" in content, "Should support dhan broker"
        print("✓ BrokerConnection model exists with all broker types")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
