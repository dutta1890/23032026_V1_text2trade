"""
SEBI Compliance Layer Tests - Iteration 34
Tests for:
1. Public compliance status endpoint
2. Audit logging on auth (register, login, logout)
3. Admin compliance endpoints (audit-stats, audit-trail, audit-export, ops, strategy-classification)
4. Algo-ID live execution gate (403 without algo_id)
5. Strategy model SEBI fields (algo_id, algo_registered, classification)
"""

import pytest
import requests
import os
import time
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_USER_EMAIL = "testai@example.com"
TEST_USER_PASSWORD = "Password123!"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "Password123!"


class TestPublicComplianceStatus:
    """Test public compliance status endpoint (no auth required)"""
    
    def test_compliance_status_returns_200(self):
        """GET /api/v1/compliance/status should return 200 without auth"""
        response = requests.get(f"{BASE_URL}/api/v1/compliance/status")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ Compliance status endpoint returns 200")
    
    def test_compliance_status_has_required_fields(self):
        """Compliance status should have SEBI framework fields"""
        response = requests.get(f"{BASE_URL}/api/v1/compliance/status")
        data = response.json()
        
        required_fields = [
            "framework", "circular", "compliance_status", "live_trading",
            "audit_trail", "data_retention", "hosting_region", "algo_registration",
            "static_ip", "strategy_type", "note"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        # Verify specific values
        assert data["audit_trail"] == "active", f"Expected audit_trail='active', got {data['audit_trail']}"
        assert data["data_retention"] == "5_years", f"Expected data_retention='5_years', got {data['data_retention']}"
        assert data["strategy_type"] == "white_box_only", f"Expected strategy_type='white_box_only', got {data['strategy_type']}"
        print("✓ Compliance status has all required SEBI fields")


class TestAuthAuditLogging:
    """Test audit logging for auth events"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin token for audit trail verification"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Admin login failed")
    
    def test_login_creates_audit_entry(self, admin_token):
        """POST /api/v1/auth/login should create user_login audit entry"""
        # Login as test user
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        
        # Wait for audit entry to be written
        time.sleep(0.5)
        
        # Check audit trail for login entry
        headers = {"Authorization": f"Bearer {admin_token}"}
        audit_response = requests.get(
            f"{BASE_URL}/api/v1/admin/compliance/audit-trail?action=user_login&user_id={TEST_USER_EMAIL}&limit=5",
            headers=headers
        )
        assert audit_response.status_code == 200, f"Audit trail query failed: {audit_response.text}"
        
        data = audit_response.json()
        assert data["total"] > 0, "No user_login audit entries found"
        
        # Verify entry structure
        entry = data["entries"][0]
        assert entry["action"] == "user_login"
        assert entry["user_id"] == TEST_USER_EMAIL
        print(f"✓ Login created audit entry: {entry['audit_id']}")
    
    def test_register_creates_audit_entry(self, admin_token):
        """POST /api/v1/auth/register should create user_registered audit entry"""
        # Use unique email for registration
        timestamp = int(time.time())
        test_email = f"audit-test-{timestamp}@example.com"
        
        response = requests.post(f"{BASE_URL}/api/v1/auth/register", json={
            "email": test_email,
            "password": "TestPassword123!",
            "name": "Audit Test User"
        })
        
        # Accept 201 (success) or 400 (email exists from previous test)
        if response.status_code == 201:
            time.sleep(0.5)
            
            # Check audit trail for register entry
            headers = {"Authorization": f"Bearer {admin_token}"}
            audit_response = requests.get(
                f"{BASE_URL}/api/v1/admin/compliance/audit-trail?action=user_registered&user_id={test_email}&limit=5",
                headers=headers
            )
            assert audit_response.status_code == 200
            
            data = audit_response.json()
            assert data["total"] > 0, "No user_registered audit entry found"
            
            entry = data["entries"][0]
            assert entry["action"] == "user_registered"
            print(f"✓ Register created audit entry: {entry['audit_id']}")
        else:
            print(f"⚠ Registration returned {response.status_code} - may be rate limited or email exists")
    
    def test_logout_creates_audit_entry(self, admin_token):
        """POST /api/v1/auth/logout should create user_logout audit entry"""
        # First login to get a token
        login_response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        assert login_response.status_code == 200
        user_token = login_response.json().get("access_token")
        
        # Logout
        logout_response = requests.post(
            f"{BASE_URL}/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert logout_response.status_code == 200, f"Logout failed: {logout_response.text}"
        
        time.sleep(0.5)
        
        # Check audit trail for logout entry
        headers = {"Authorization": f"Bearer {admin_token}"}
        audit_response = requests.get(
            f"{BASE_URL}/api/v1/admin/compliance/audit-trail?action=user_logout&limit=5",
            headers=headers
        )
        assert audit_response.status_code == 200
        
        data = audit_response.json()
        assert data["total"] > 0, "No user_logout audit entries found"
        print(f"✓ Logout created audit entry")


class TestAdminComplianceEndpoints:
    """Test admin compliance dashboard endpoints"""
    
    @pytest.fixture(scope="class")
    def admin_headers(self):
        """Get admin auth headers"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Admin login failed")
    
    def test_audit_stats_returns_required_fields(self, admin_headers):
        """GET /api/v1/admin/compliance/audit-stats should return stats"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/compliance/audit-stats",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        required_fields = ["total_entries", "entries_today", "retention_years"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        assert data["retention_years"] == 5, f"Expected retention_years=5, got {data['retention_years']}"
        assert isinstance(data["total_entries"], int), "total_entries should be int"
        assert isinstance(data["entries_today"], int), "entries_today should be int"
        print(f"✓ Audit stats: total={data['total_entries']}, today={data['entries_today']}, retention={data['retention_years']}yr")
    
    def test_audit_trail_returns_paginated_entries(self, admin_headers):
        """GET /api/v1/admin/compliance/audit-trail should return paginated entries"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/compliance/audit-trail?page=1&limit=10",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "entries" in data, "Missing 'entries' field"
        assert "total" in data, "Missing 'total' field"
        assert "page" in data, "Missing 'page' field"
        assert "pages" in data, "Missing 'pages' field"
        
        # Verify entry structure if entries exist
        if data["entries"]:
            entry = data["entries"][0]
            entry_fields = ["audit_id", "timestamp", "user_id", "action"]
            for field in entry_fields:
                assert field in entry, f"Entry missing field: {field}"
        
        print(f"✓ Audit trail: {data['total']} total entries, page {data['page']}/{data['pages']}")
    
    def test_audit_trail_filters_by_action(self, admin_headers):
        """Audit trail should filter by action type"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/compliance/audit-trail?action=user_login&limit=5",
            headers=admin_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        for entry in data["entries"]:
            assert entry["action"] == "user_login", f"Filter failed: got action={entry['action']}"
        
        print(f"✓ Audit trail filter by action works ({len(data['entries'])} user_login entries)")
    
    def test_audit_trail_filters_by_user_id(self, admin_headers):
        """Audit trail should filter by user_id"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/compliance/audit-trail?user_id={TEST_USER_EMAIL}&limit=5",
            headers=admin_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        for entry in data["entries"]:
            assert entry["user_id"] == TEST_USER_EMAIL, f"Filter failed: got user_id={entry['user_id']}"
        
        print(f"✓ Audit trail filter by user_id works ({len(data['entries'])} entries)")
    
    def test_audit_export_returns_csv(self, admin_headers):
        """GET /api/v1/admin/compliance/audit-export should return CSV file"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/compliance/audit-export",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Check content type
        content_type = response.headers.get("content-type", "")
        assert "text/csv" in content_type, f"Expected text/csv, got {content_type}"
        
        # Check content disposition
        content_disp = response.headers.get("content-disposition", "")
        assert "attachment" in content_disp, f"Expected attachment, got {content_disp}"
        assert ".csv" in content_disp, f"Expected .csv filename, got {content_disp}"
        
        # Verify CSV has header row
        csv_content = response.text
        assert "audit_id" in csv_content, "CSV missing audit_id column"
        assert "timestamp" in csv_content, "CSV missing timestamp column"
        assert "action" in csv_content, "CSV missing action column"
        
        print(f"✓ Audit export returns CSV ({len(csv_content)} bytes)")
    
    def test_ops_monitoring_returns_threshold_and_users(self, admin_headers):
        """GET /api/v1/admin/compliance/ops should return threshold and users array"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/compliance/ops",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "threshold" in data, "Missing 'threshold' field"
        assert "users" in data, "Missing 'users' field"
        assert isinstance(data["users"], list), "users should be a list"
        assert data["threshold"] == 10, f"Expected threshold=10, got {data['threshold']}"
        
        print(f"✓ OPS monitoring: threshold={data['threshold']}, active_users={len(data['users'])}")
    
    def test_strategy_classification_returns_counts(self, admin_headers):
        """GET /api/v1/admin/compliance/strategy-classification should return white_box and black_box counts"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/compliance/strategy-classification",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "white_box" in data, "Missing 'white_box' field"
        assert "black_box" in data, "Missing 'black_box' field"
        assert "total" in data, "Missing 'total' field"
        
        assert isinstance(data["white_box"], int), "white_box should be int"
        assert isinstance(data["black_box"], int), "black_box should be int"
        
        print(f"✓ Strategy classification: total={data['total']}, white_box={data['white_box']}, black_box={data['black_box']}")


class TestAlgoIdLiveExecutionGate:
    """Test that live execution is blocked without algo_id"""
    
    @pytest.fixture(scope="class")
    def user_headers_and_strategy(self):
        """Get user auth headers and a strategy ID"""
        # Login as test user
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("User login failed")
        
        token = response.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get user's strategies
        strategies_response = requests.get(f"{BASE_URL}/api/v1/strategies", headers=headers)
        if strategies_response.status_code != 200:
            pytest.skip("Failed to get strategies")
        
        strategies = strategies_response.json().get("strategies", [])
        if not strategies:
            pytest.skip("No strategies found for test user")
        
        strategy_id = strategies[0]["id"]
        return headers, strategy_id
    
    def test_execute_live_returns_403_without_algo_id(self, user_headers_and_strategy):
        """POST /api/v1/strategy/{id}/execute-live should return 403 without algo_id"""
        headers, strategy_id = user_headers_and_strategy
        
        response = requests.post(
            f"{BASE_URL}/api/v1/strategy/{strategy_id}/execute-live",
            headers=headers
        )
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "detail" in data, "Missing error detail"
        assert "algo" in data["detail"].lower() or "registered" in data["detail"].lower(), \
            f"Error should mention algo registration: {data['detail']}"
        
        print(f"✓ Execute-live returns 403 with algo-id registration message")


class TestStrategyModelSEBIFields:
    """Test that Strategy model has SEBI compliance fields"""
    
    @pytest.fixture(scope="class")
    def user_headers(self):
        """Get user auth headers"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("User login failed")
        
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}
    
    def test_strategy_has_sebi_fields(self, user_headers):
        """Strategy should have algo_id, algo_registered, classification fields"""
        # Get strategies
        response = requests.get(f"{BASE_URL}/api/v1/strategies", headers=user_headers)
        assert response.status_code == 200
        
        strategies = response.json().get("strategies", [])
        if not strategies:
            pytest.skip("No strategies to verify")
        
        strategy = strategies[0]
        
        # Check SEBI fields exist (may be null/default)
        sebi_fields = ["algo_id", "algo_registered", "classification"]
        for field in sebi_fields:
            assert field in strategy, f"Strategy missing SEBI field: {field}"
        
        # Verify default values
        assert strategy["algo_registered"] == False, f"Expected algo_registered=False, got {strategy['algo_registered']}"
        assert strategy["classification"] in ["white_box", "black_box"], \
            f"Invalid classification: {strategy['classification']}"
        
        print(f"✓ Strategy has SEBI fields: algo_id={strategy.get('algo_id')}, algo_registered={strategy['algo_registered']}, classification={strategy['classification']}")


class TestAdminEndpointsRequireAuth:
    """Test that admin endpoints require authentication"""
    
    def test_audit_stats_requires_auth(self):
        """Admin audit-stats should return 401/403 without auth"""
        response = requests.get(f"{BASE_URL}/api/v1/admin/compliance/audit-stats")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ audit-stats requires auth")
    
    def test_audit_trail_requires_auth(self):
        """Admin audit-trail should return 401/403 without auth"""
        response = requests.get(f"{BASE_URL}/api/v1/admin/compliance/audit-trail")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ audit-trail requires auth")
    
    def test_audit_export_requires_auth(self):
        """Admin audit-export should return 401/403 without auth"""
        response = requests.get(f"{BASE_URL}/api/v1/admin/compliance/audit-export")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ audit-export requires auth")
    
    def test_ops_requires_auth(self):
        """Admin ops should return 401/403 without auth"""
        response = requests.get(f"{BASE_URL}/api/v1/admin/compliance/ops")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ ops requires auth")
    
    def test_strategy_classification_requires_auth(self):
        """Admin strategy-classification should return 401/403 without auth"""
        response = requests.get(f"{BASE_URL}/api/v1/admin/compliance/strategy-classification")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ strategy-classification requires auth")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
