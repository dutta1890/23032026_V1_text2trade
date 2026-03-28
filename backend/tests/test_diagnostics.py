"""
Diagnostics System Tests - Iteration 28
Tests for:
1. POST /api/v1/diagnostics/frontend-crash - stores crash report (no auth required)
2. GET /api/v1/admin/diagnostics/summary - returns error summary (admin only)
3. GET /api/v1/admin/diagnostics/errors - paginated error list with filters (admin only)
4. GET /api/v1/admin/diagnostics/errors/{error_id} - error detail (admin only)
5. PUT /api/v1/admin/diagnostics/errors/{error_id}/resolve - resolve error (admin only)
6. GET /api/v1/admin/diagnostics/performance - performance metrics (admin only)
7. GET /api/v1/admin/diagnostics/test/error - triggers unhandled RuntimeError (auth required)
8. GET /api/v1/admin/diagnostics/test/slow - triggers 4s slow request (auth required)
9. GET /api/v1/health - includes error_rate.last_1h and error_rate.last_24h
10. Global exception handler returns friendly message, not raw stack trace
11. Error records have sanitized request bodies (no passwords/tokens)
12. Admin endpoints require admin role (403 for regular users)
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "Password123!"
USER_EMAIL = "testai@example.com"
USER_PASSWORD = "Password123!"


class TestDiagnosticsAuth:
    """Test authentication requirements for diagnostics endpoints"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def user_token(self):
        """Get regular user auth token"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": USER_EMAIL,
            "password": USER_PASSWORD
        })
        assert response.status_code == 200, f"User login failed: {response.text}"
        return response.json()["access_token"]
    
    def test_frontend_crash_no_auth_required(self):
        """POST /api/v1/diagnostics/frontend-crash should work without auth"""
        response = requests.post(f"{BASE_URL}/api/v1/diagnostics/frontend-crash", json={
            "error_message": "Test crash from pytest - no auth",
            "component_stack": "at TestComponent\nat App",
            "page_url": "http://localhost:3000/test",
            "browser_info": "pytest-test-agent",
            "user_id": None,
            "timestamp": "2026-01-15T10:00:00Z"
        })
        assert response.status_code == 200, f"Frontend crash endpoint failed: {response.text}"
        data = response.json()
        assert data["success"] is True
        assert "error_id" in data
        print(f"✓ Frontend crash stored with error_id: {data['error_id']}")
    
    def test_admin_summary_requires_admin(self, user_token):
        """GET /api/v1/admin/diagnostics/summary should return 403 for regular user"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/diagnostics/summary",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 403, f"Expected 403 for regular user, got {response.status_code}"
        print("✓ Admin summary correctly returns 403 for regular user")
    
    def test_admin_errors_requires_admin(self, user_token):
        """GET /api/v1/admin/diagnostics/errors should return 403 for regular user"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/diagnostics/errors",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 403, f"Expected 403 for regular user, got {response.status_code}"
        print("✓ Admin errors list correctly returns 403 for regular user")
    
    def test_admin_performance_requires_admin(self, user_token):
        """GET /api/v1/admin/diagnostics/performance should return 403 for regular user"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/diagnostics/performance",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 403, f"Expected 403 for regular user, got {response.status_code}"
        print("✓ Admin performance correctly returns 403 for regular user")


class TestFrontendCrashEndpoint:
    """Test POST /api/v1/diagnostics/frontend-crash"""
    
    def test_store_frontend_crash_with_all_fields(self):
        """Frontend crash with all fields should be stored correctly"""
        crash_data = {
            "error_message": "TypeError: Cannot read property 'map' of undefined",
            "component_stack": "at UserList (UserList.js:42)\nat Dashboard (Dashboard.js:15)\nat App (App.js:8)",
            "page_url": "http://localhost:3000/dashboard",
            "browser_info": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
            "user_id": "test-user-123",
            "timestamp": "2026-01-15T12:30:00Z"
        }
        response = requests.post(f"{BASE_URL}/api/v1/diagnostics/frontend-crash", json=crash_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "error_id" in data
        assert len(data["error_id"]) > 0
        print(f"✓ Frontend crash stored: {data['error_id']}")
        return data["error_id"]
    
    def test_store_frontend_crash_minimal_fields(self):
        """Frontend crash with only required field should work"""
        response = requests.post(f"{BASE_URL}/api/v1/diagnostics/frontend-crash", json={
            "error_message": "Minimal crash test"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        print("✓ Minimal frontend crash stored successfully")


class TestAdminDiagnosticsSummary:
    """Test GET /api/v1/admin/diagnostics/summary"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_summary_returns_expected_fields(self, admin_token):
        """Summary should return last_24h, last_7d, top_errors, affected_users_24h, error_rate_per_hour"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/diagnostics/summary",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Summary failed: {response.text}"
        data = response.json()
        
        # Check required fields
        assert "last_24h" in data, "Missing last_24h"
        assert "last_7d" in data, "Missing last_7d"
        assert "top_errors" in data, "Missing top_errors"
        assert "affected_users_24h" in data, "Missing affected_users_24h"
        assert "error_rate_per_hour" in data, "Missing error_rate_per_hour"
        
        # Check last_24h structure
        assert "total" in data["last_24h"]
        assert "critical" in data["last_24h"]
        assert "high" in data["last_24h"]
        assert "medium" in data["last_24h"]
        assert "low" in data["last_24h"]
        
        # Check last_7d structure
        assert "total" in data["last_7d"]
        
        print(f"✓ Summary returned: {data['last_24h']['total']} errors in 24h, {data['last_7d']['total']} in 7d")
        print(f"  Top errors: {len(data['top_errors'])}, Affected users: {data['affected_users_24h']}")


class TestAdminErrorsList:
    """Test GET /api/v1/admin/diagnostics/errors"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_errors_list_returns_paginated_results(self, admin_token):
        """Errors list should return paginated results"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/diagnostics/errors",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "errors" in data
        assert "total" in data
        assert "page" in data
        assert "limit" in data
        assert isinstance(data["errors"], list)
        
        print(f"✓ Errors list: {data['total']} total, page {data['page']}, limit {data['limit']}")
        
        # Check error structure if any exist
        if len(data["errors"]) > 0:
            error = data["errors"][0]
            assert "error_id" in error
            assert "timestamp" in error
            assert "severity" in error
            assert "source" in error
            assert "error_type" in error
            print(f"  First error: {error['error_type']} ({error['severity']}) from {error['source']}")
    
    def test_errors_filter_by_severity(self, admin_token):
        """Errors list should filter by severity"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/diagnostics/errors?severity=high",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # All returned errors should have severity=high
        for error in data["errors"]:
            assert error["severity"] == "high", f"Expected severity=high, got {error['severity']}"
        
        print(f"✓ Severity filter works: {len(data['errors'])} high severity errors")
    
    def test_errors_filter_by_source(self, admin_token):
        """Errors list should filter by source"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/diagnostics/errors?source=frontend",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        for error in data["errors"]:
            assert error["source"] == "frontend", f"Expected source=frontend, got {error['source']}"
        
        print(f"✓ Source filter works: {len(data['errors'])} frontend errors")
    
    def test_errors_filter_by_resolved(self, admin_token):
        """Errors list should filter by resolved status"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/diagnostics/errors?resolved=false",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        for error in data["errors"]:
            assert error["resolved"] is False, f"Expected resolved=false, got {error['resolved']}"
        
        print(f"✓ Resolved filter works: {len(data['errors'])} open errors")


class TestAdminErrorDetail:
    """Test GET /api/v1/admin/diagnostics/errors/{error_id}"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def test_error_id(self, admin_token):
        """Create a test error and return its ID"""
        # Create a frontend crash to get an error_id
        response = requests.post(f"{BASE_URL}/api/v1/diagnostics/frontend-crash", json={
            "error_message": "Test error for detail view",
            "component_stack": "at TestComponent\nat App",
            "page_url": "http://localhost:3000/test-detail"
        })
        return response.json()["error_id"]
    
    def test_error_detail_returns_full_info(self, admin_token, test_error_id):
        """Error detail should return full error info including stack trace"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/diagnostics/errors/{test_error_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Error detail failed: {response.text}"
        data = response.json()
        
        assert data["error_id"] == test_error_id
        assert "timestamp" in data
        assert "error_type" in data
        assert "error_message" in data
        assert "stack_trace" in data
        assert "severity" in data
        assert "source" in data
        assert "resolved" in data
        
        print(f"✓ Error detail returned for {test_error_id}")
        print(f"  Type: {data['error_type']}, Severity: {data['severity']}")
    
    def test_error_detail_not_found(self, admin_token):
        """Non-existent error should return 404"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/diagnostics/errors/non-existent-id-12345",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404
        print("✓ Non-existent error returns 404")


class TestAdminResolveError:
    """Test PUT /api/v1/admin/diagnostics/errors/{error_id}/resolve"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_resolve_error_with_note(self, admin_token):
        """Resolve error should mark it as resolved with note and resolved_by"""
        # First create an error
        crash_response = requests.post(f"{BASE_URL}/api/v1/diagnostics/frontend-crash", json={
            "error_message": "Test error to be resolved",
            "page_url": "http://localhost:3000/resolve-test"
        })
        error_id = crash_response.json()["error_id"]
        
        # Resolve it
        resolve_response = requests.put(
            f"{BASE_URL}/api/v1/admin/diagnostics/errors/{error_id}/resolve",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"note": "Fixed by updating component state handling"}
        )
        assert resolve_response.status_code == 200
        data = resolve_response.json()
        assert data["success"] is True
        
        # Verify it's resolved
        detail_response = requests.get(
            f"{BASE_URL}/api/v1/admin/diagnostics/errors/{error_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        detail = detail_response.json()
        assert detail["resolved"] is True
        assert detail["resolve_note"] == "Fixed by updating component state handling"
        assert detail["resolved_by"] == ADMIN_EMAIL
        assert "resolved_at" in detail
        
        print(f"✓ Error {error_id} resolved successfully")
        print(f"  Resolved by: {detail['resolved_by']}, Note: {detail['resolve_note']}")
    
    def test_resolve_nonexistent_error(self, admin_token):
        """Resolving non-existent error should return 404"""
        response = requests.put(
            f"{BASE_URL}/api/v1/admin/diagnostics/errors/nonexistent-error-id/resolve",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"note": "Test"}
        )
        assert response.status_code == 404
        print("✓ Resolving non-existent error returns 404")


class TestAdminPerformance:
    """Test GET /api/v1/admin/diagnostics/performance"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_performance_returns_expected_fields(self, admin_token):
        """Performance should return avg_by_endpoint, slowest_requests, p95_by_endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/diagnostics/performance",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Performance failed: {response.text}"
        data = response.json()
        
        assert "avg_by_endpoint" in data
        assert "slowest_requests" in data
        assert "p95_by_endpoint" in data
        
        assert isinstance(data["avg_by_endpoint"], list)
        assert isinstance(data["slowest_requests"], list)
        assert isinstance(data["p95_by_endpoint"], list)
        
        print(f"✓ Performance metrics returned")
        print(f"  Endpoints tracked: {len(data['avg_by_endpoint'])}")
        print(f"  Slowest requests: {len(data['slowest_requests'])}")
        print(f"  P95 data points: {len(data['p95_by_endpoint'])}")


class TestDiagnosticsTestEndpoints:
    """Test the test endpoints for error and slow request simulation"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_force_error_endpoint(self, admin_token):
        """GET /api/v1/admin/diagnostics/test/error should trigger RuntimeError and return friendly message"""
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/diagnostics/test/error",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # Should return 500 with friendly message
        assert response.status_code == 500
        data = response.json()
        
        # Should NOT contain raw stack trace
        assert "detail" in data
        assert "An internal error occurred" in data["detail"]
        assert "RuntimeError" not in data["detail"]
        assert "Traceback" not in data["detail"]
        
        print("✓ Test error endpoint returns friendly message, not stack trace")
        
        # Verify error was stored
        time.sleep(0.5)  # Give time for async storage
        errors_response = requests.get(
            f"{BASE_URL}/api/v1/admin/diagnostics/errors?source=backend",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        errors = errors_response.json()["errors"]
        runtime_errors = [e for e in errors if e["error_type"] == "RuntimeError"]
        assert len(runtime_errors) > 0, "RuntimeError should be stored in error_logs"
        print(f"✓ RuntimeError stored in error_logs (found {len(runtime_errors)} RuntimeError(s))")
    
    def test_slow_request_endpoint(self, admin_token):
        """GET /api/v1/admin/diagnostics/test/slow should take ~4s and be logged"""
        start = time.time()
        response = requests.get(
            f"{BASE_URL}/api/v1/admin/diagnostics/test/slow",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10
        )
        duration = time.time() - start
        
        assert response.status_code == 200
        data = response.json()
        assert data["duration_sec"] == 4
        assert duration >= 3.5, f"Request should take ~4s, took {duration:.1f}s"
        
        print(f"✓ Slow request endpoint took {duration:.1f}s")
        
        # Verify it was logged in performance_logs
        time.sleep(0.5)
        perf_response = requests.get(
            f"{BASE_URL}/api/v1/admin/diagnostics/performance",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        perf = perf_response.json()
        slow_reqs = perf["slowest_requests"]
        test_slow = [r for r in slow_reqs if "/admin/diagnostics/test/slow" in r.get("endpoint", "")]
        assert len(test_slow) > 0, "Slow request should be logged in performance_logs"
        print(f"✓ Slow request logged in performance_logs")


class TestHealthEndpoint:
    """Test GET /api/v1/health includes error_rate"""
    
    def test_health_includes_error_rate(self):
        """Health endpoint should include error_rate.last_1h and error_rate.last_24h"""
        response = requests.get(f"{BASE_URL}/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        
        assert "error_rate" in data, "Health should include error_rate"
        assert "last_1h" in data["error_rate"], "error_rate should have last_1h"
        assert "last_24h" in data["error_rate"], "error_rate should have last_24h"
        
        print(f"✓ Health endpoint includes error_rate")
        print(f"  Errors last 1h: {data['error_rate']['last_1h']}")
        print(f"  Errors last 24h: {data['error_rate']['last_24h']}")


class TestSanitization:
    """Test that sensitive data is sanitized in error records"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_password_not_in_error_logs(self, admin_token):
        """Passwords should be redacted in error logs"""
        # Trigger an error with password in request body
        # Try to register with invalid data to trigger validation error
        response = requests.post(f"{BASE_URL}/api/v1/auth/register", json={
            "email": "invalid-email-format",  # Invalid to trigger error
            "password": "SuperSecretPassword123!",
            "name": "Test User"
        })
        # This should fail validation
        
        # Check error logs for any password leakage
        time.sleep(0.5)
        errors_response = requests.get(
            f"{BASE_URL}/api/v1/admin/diagnostics/errors?source=backend",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        errors = errors_response.json()["errors"]
        
        for error in errors:
            if error.get("request_body"):
                body_str = str(error["request_body"])
                assert "SuperSecretPassword123!" not in body_str, "Password should be redacted"
                if "password" in body_str.lower():
                    assert "REDACTED" in body_str or "***" in body_str, "Password field should be redacted"
        
        print("✓ Passwords are properly sanitized in error logs")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
