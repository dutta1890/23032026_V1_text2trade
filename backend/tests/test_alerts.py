"""
Test suite for Strategy Alerts feature.
Tests: POST /alerts, GET /alerts, PUT /alerts/{id}, DELETE /alerts/{id},
       POST /alerts/evaluate, GET /alerts/notifications, 
       PUT /alerts/notifications/{id}/read, PUT /alerts/notifications/read-all
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestAlertsAuth:
    """Test authentication requirements for all alert endpoints"""
    
    def test_create_alert_without_auth(self):
        """POST /alerts without auth returns 401"""
        payload = {"strategy_name": "Test", "metric": "sharpe", "operator": "lt", "threshold": 1.0}
        response = requests.post(f"{BASE_URL}/api/v1/alerts", json=payload)
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    
    def test_list_alerts_without_auth(self):
        """GET /alerts without auth returns 401"""
        response = requests.get(f"{BASE_URL}/api/v1/alerts")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    
    def test_update_alert_without_auth(self):
        """PUT /alerts/{id} without auth returns 401"""
        response = requests.put(f"{BASE_URL}/api/v1/alerts/test123", json={"enabled": False})
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    
    def test_delete_alert_without_auth(self):
        """DELETE /alerts/{id} without auth returns 401"""
        response = requests.delete(f"{BASE_URL}/api/v1/alerts/test123")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    
    def test_evaluate_alerts_without_auth(self):
        """POST /alerts/evaluate without auth returns 401"""
        response = requests.post(f"{BASE_URL}/api/v1/alerts/evaluate")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    
    def test_get_notifications_without_auth(self):
        """GET /alerts/notifications without auth returns 401"""
        response = requests.get(f"{BASE_URL}/api/v1/alerts/notifications")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    
    def test_mark_notification_read_without_auth(self):
        """PUT /alerts/notifications/{id}/read without auth returns 401"""
        response = requests.put(f"{BASE_URL}/api/v1/alerts/notifications/test123/read")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    
    def test_mark_all_read_without_auth(self):
        """PUT /alerts/notifications/read-all without auth returns 401"""
        response = requests.put(f"{BASE_URL}/api/v1/alerts/notifications/read-all")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"


class TestAlertsCRUD:
    """Test CRUD operations for alert rules"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for test user"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": "testai@example.com",
            "password": "Password123!"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Headers with auth token"""
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    
    # =========================================================================
    # POST /alerts - Create alert rule
    # =========================================================================
    
    def test_create_alert_success(self, auth_headers):
        """Test creating an alert rule with valid data"""
        payload = {
            "strategy_name": "TEST_Alert_Strategy",
            "metric": "sharpe",
            "operator": "lt",
            "threshold": 1.0
        }
        response = requests.post(f"{BASE_URL}/api/v1/alerts", json=payload, headers=auth_headers)
        assert response.status_code == 200, f"Create alert failed: {response.text}"
        data = response.json()
        assert data.get("success") is True
        assert "alert" in data
        alert = data["alert"]
        assert alert["strategy_name"] == "TEST_Alert_Strategy"
        assert alert["metric"] == "sharpe"
        assert alert["operator"] == "lt"
        assert alert["threshold"] == 1.0
        assert alert["enabled"] is True
        assert "alert_id" in alert
        assert "created_at" in alert
    
    def test_create_alert_pnl_pct_metric(self, auth_headers):
        """Test creating alert with pnl_pct metric"""
        payload = {
            "strategy_name": "TEST_PnL_Alert",
            "metric": "pnl_pct",
            "operator": "gt",
            "threshold": 10.0
        }
        response = requests.post(f"{BASE_URL}/api/v1/alerts", json=payload, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["alert"]["metric"] == "pnl_pct"
        assert data["alert"]["operator"] == "gt"
    
    def test_create_alert_win_rate_metric(self, auth_headers):
        """Test creating alert with win_rate metric"""
        payload = {
            "strategy_name": "TEST_WinRate_Alert",
            "metric": "win_rate",
            "operator": "lte",
            "threshold": 50.0
        }
        response = requests.post(f"{BASE_URL}/api/v1/alerts", json=payload, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["alert"]["metric"] == "win_rate"
        assert data["alert"]["operator"] == "lte"
    
    def test_create_alert_max_drawdown_metric(self, auth_headers):
        """Test creating alert with max_drawdown metric"""
        payload = {
            "strategy_name": "TEST_Drawdown_Alert",
            "metric": "max_drawdown",
            "operator": "gte",
            "threshold": -15.0
        }
        response = requests.post(f"{BASE_URL}/api/v1/alerts", json=payload, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["alert"]["metric"] == "max_drawdown"
        assert data["alert"]["operator"] == "gte"
    
    def test_create_alert_invalid_metric(self, auth_headers):
        """Test creating alert with invalid metric returns 422"""
        payload = {
            "strategy_name": "TEST_Invalid",
            "metric": "invalid_metric",
            "operator": "lt",
            "threshold": 1.0
        }
        response = requests.post(f"{BASE_URL}/api/v1/alerts", json=payload, headers=auth_headers)
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
    
    def test_create_alert_invalid_operator(self, auth_headers):
        """Test creating alert with invalid operator returns 422"""
        payload = {
            "strategy_name": "TEST_Invalid",
            "metric": "sharpe",
            "operator": "invalid_op",
            "threshold": 1.0
        }
        response = requests.post(f"{BASE_URL}/api/v1/alerts", json=payload, headers=auth_headers)
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
    
    # =========================================================================
    # GET /alerts - List alert rules
    # =========================================================================
    
    def test_list_alerts_success(self, auth_headers):
        """Test listing alert rules"""
        response = requests.get(f"{BASE_URL}/api/v1/alerts", headers=auth_headers)
        assert response.status_code == 200, f"List alerts failed: {response.text}"
        data = response.json()
        assert "alerts" in data
        assert "count" in data
        assert isinstance(data["alerts"], list)
        assert isinstance(data["count"], int)
        assert data["count"] == len(data["alerts"])
    
    def test_list_alerts_structure(self, auth_headers):
        """Test alert rule structure in list response"""
        response = requests.get(f"{BASE_URL}/api/v1/alerts", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        if data["alerts"]:
            alert = data["alerts"][0]
            assert "alert_id" in alert
            assert "user_id" in alert
            assert "strategy_name" in alert
            assert "metric" in alert
            assert "operator" in alert
            assert "threshold" in alert
            assert "enabled" in alert
            assert "created_at" in alert
            # Verify _id is excluded
            assert "_id" not in alert
    
    # =========================================================================
    # PUT /alerts/{alert_id} - Toggle alert enabled/disabled
    # =========================================================================
    
    def test_toggle_alert_disable(self, auth_headers):
        """Test disabling an alert"""
        # First create an alert
        create_payload = {
            "strategy_name": "TEST_Toggle_Alert",
            "metric": "sharpe",
            "operator": "lt",
            "threshold": 0.5
        }
        create_response = requests.post(f"{BASE_URL}/api/v1/alerts", json=create_payload, headers=auth_headers)
        assert create_response.status_code == 200
        alert_id = create_response.json()["alert"]["alert_id"]
        
        # Disable the alert
        update_response = requests.put(f"{BASE_URL}/api/v1/alerts/{alert_id}", json={"enabled": False}, headers=auth_headers)
        assert update_response.status_code == 200, f"Toggle failed: {update_response.text}"
        assert update_response.json().get("success") is True
        
        # Verify it's disabled in list
        list_response = requests.get(f"{BASE_URL}/api/v1/alerts", headers=auth_headers)
        alerts = list_response.json()["alerts"]
        found_alert = next((a for a in alerts if a["alert_id"] == alert_id), None)
        assert found_alert is not None
        assert found_alert["enabled"] is False
    
    def test_toggle_alert_enable(self, auth_headers):
        """Test enabling a disabled alert"""
        # First create and disable an alert
        create_payload = {
            "strategy_name": "TEST_Enable_Alert",
            "metric": "pnl_pct",
            "operator": "gt",
            "threshold": 5.0
        }
        create_response = requests.post(f"{BASE_URL}/api/v1/alerts", json=create_payload, headers=auth_headers)
        alert_id = create_response.json()["alert"]["alert_id"]
        
        # Disable first
        requests.put(f"{BASE_URL}/api/v1/alerts/{alert_id}", json={"enabled": False}, headers=auth_headers)
        
        # Enable again
        update_response = requests.put(f"{BASE_URL}/api/v1/alerts/{alert_id}", json={"enabled": True}, headers=auth_headers)
        assert update_response.status_code == 200
        
        # Verify it's enabled
        list_response = requests.get(f"{BASE_URL}/api/v1/alerts", headers=auth_headers)
        alerts = list_response.json()["alerts"]
        found_alert = next((a for a in alerts if a["alert_id"] == alert_id), None)
        assert found_alert["enabled"] is True
    
    def test_toggle_nonexistent_alert(self, auth_headers):
        """Test toggling non-existent alert returns 404"""
        response = requests.put(f"{BASE_URL}/api/v1/alerts/nonexistent123", json={"enabled": False}, headers=auth_headers)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    
    # =========================================================================
    # DELETE /alerts/{alert_id} - Delete alert rule
    # =========================================================================
    
    def test_delete_alert_success(self, auth_headers):
        """Test deleting an alert rule"""
        # First create an alert
        create_payload = {
            "strategy_name": "TEST_Delete_Alert",
            "metric": "win_rate",
            "operator": "lt",
            "threshold": 40.0
        }
        create_response = requests.post(f"{BASE_URL}/api/v1/alerts", json=create_payload, headers=auth_headers)
        alert_id = create_response.json()["alert"]["alert_id"]
        
        # Delete the alert
        delete_response = requests.delete(f"{BASE_URL}/api/v1/alerts/{alert_id}", headers=auth_headers)
        assert delete_response.status_code == 200, f"Delete failed: {delete_response.text}"
        assert delete_response.json().get("success") is True
        
        # Verify it's gone from list
        list_response = requests.get(f"{BASE_URL}/api/v1/alerts", headers=auth_headers)
        alerts = list_response.json()["alerts"]
        found_alert = next((a for a in alerts if a["alert_id"] == alert_id), None)
        assert found_alert is None, "Deleted alert should not appear in list"
    
    def test_delete_nonexistent_alert(self, auth_headers):
        """Test deleting non-existent alert returns 404"""
        response = requests.delete(f"{BASE_URL}/api/v1/alerts/nonexistent456", headers=auth_headers)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"


class TestAlertsEvaluate:
    """Test alert evaluation against tracker data"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for test user"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": "testai@example.com",
            "password": "Password123!"
        })
        assert response.status_code == 200
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    
    def test_evaluate_alerts_success(self, auth_headers):
        """Test evaluating alerts returns triggered count and notifications"""
        response = requests.post(f"{BASE_URL}/api/v1/alerts/evaluate", headers=auth_headers)
        assert response.status_code == 200, f"Evaluate failed: {response.text}"
        data = response.json()
        assert "triggered" in data
        assert "notifications" in data
        assert isinstance(data["triggered"], int)
        assert isinstance(data["notifications"], list)
    
    def test_evaluate_alerts_notification_structure(self, auth_headers):
        """Test triggered notification has correct structure"""
        response = requests.post(f"{BASE_URL}/api/v1/alerts/evaluate", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        if data["notifications"]:
            notif = data["notifications"][0]
            assert "notification_id" in notif
            assert "user_id" in notif
            assert "alert_id" in notif
            assert "strategy_name" in notif
            assert "metric" in notif
            assert "metric_label" in notif
            assert "operator" in notif
            assert "operator_label" in notif
            assert "threshold" in notif
            assert "actual_value" in notif
            assert "severity" in notif
            assert "message" in notif
            assert "read" in notif
            assert "triggered_at" in notif
            # Verify _id is excluded
            assert "_id" not in notif


class TestAlertsNotifications:
    """Test notification retrieval and marking as read"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for test user"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": "testai@example.com",
            "password": "Password123!"
        })
        assert response.status_code == 200
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    
    def test_get_notifications_success(self, auth_headers):
        """Test getting notifications"""
        response = requests.get(f"{BASE_URL}/api/v1/alerts/notifications", headers=auth_headers)
        assert response.status_code == 200, f"Get notifications failed: {response.text}"
        data = response.json()
        assert "notifications" in data
        assert "count" in data
        assert "unread" in data
        assert isinstance(data["notifications"], list)
        assert isinstance(data["count"], int)
        assert isinstance(data["unread"], int)
    
    def test_get_notifications_structure(self, auth_headers):
        """Test notification structure in list response"""
        response = requests.get(f"{BASE_URL}/api/v1/alerts/notifications", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        if data["notifications"]:
            notif = data["notifications"][0]
            assert "notification_id" in notif
            assert "strategy_name" in notif
            assert "metric" in notif
            assert "message" in notif
            assert "severity" in notif
            assert "read" in notif
            assert "triggered_at" in notif
            # Verify _id is excluded
            assert "_id" not in notif
    
    def test_mark_notification_read(self, auth_headers):
        """Test marking a notification as read"""
        # First get notifications
        get_response = requests.get(f"{BASE_URL}/api/v1/alerts/notifications", headers=auth_headers)
        notifications = get_response.json()["notifications"]
        
        # Find an unread notification
        unread_notif = next((n for n in notifications if not n.get("read")), None)
        
        if unread_notif:
            notif_id = unread_notif["notification_id"]
            
            # Mark as read
            mark_response = requests.put(f"{BASE_URL}/api/v1/alerts/notifications/{notif_id}/read", headers=auth_headers)
            assert mark_response.status_code == 200, f"Mark read failed: {mark_response.text}"
            assert mark_response.json().get("success") is True
            
            # Verify it's marked as read
            verify_response = requests.get(f"{BASE_URL}/api/v1/alerts/notifications", headers=auth_headers)
            updated_notifs = verify_response.json()["notifications"]
            updated_notif = next((n for n in updated_notifs if n["notification_id"] == notif_id), None)
            assert updated_notif is not None
            assert updated_notif["read"] is True
        else:
            pytest.skip("No unread notifications to test")
    
    def test_mark_nonexistent_notification_read(self, auth_headers):
        """Test marking non-existent notification returns 404"""
        response = requests.put(f"{BASE_URL}/api/v1/alerts/notifications/nonexistent789/read", headers=auth_headers)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    
    def test_mark_all_read(self, auth_headers):
        """Test marking all notifications as read"""
        # First trigger some alerts to create notifications
        requests.post(f"{BASE_URL}/api/v1/alerts/evaluate", headers=auth_headers)
        
        # Mark all as read
        mark_response = requests.put(f"{BASE_URL}/api/v1/alerts/notifications/read-all", headers=auth_headers)
        assert mark_response.status_code == 200, f"Mark all read failed: {mark_response.text}"
        assert mark_response.json().get("success") is True
        
        # Verify unread count is 0
        verify_response = requests.get(f"{BASE_URL}/api/v1/alerts/notifications", headers=auth_headers)
        assert verify_response.json()["unread"] == 0, "Unread count should be 0 after mark all read"


class TestAlertsMaxLimit:
    """Test 20 rule maximum limit"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for test user"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": "testai@example.com",
            "password": "Password123!"
        })
        assert response.status_code == 200
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    
    def test_max_20_rules_enforced(self, auth_headers):
        """Test that creating more than 20 rules returns 400"""
        # Get current count
        list_response = requests.get(f"{BASE_URL}/api/v1/alerts", headers=auth_headers)
        current_count = list_response.json()["count"]
        
        # If already at or above 20, test should pass by trying to create one more
        if current_count >= 20:
            payload = {
                "strategy_name": "TEST_Over_Limit",
                "metric": "sharpe",
                "operator": "lt",
                "threshold": 0.1
            }
            response = requests.post(f"{BASE_URL}/api/v1/alerts", json=payload, headers=auth_headers)
            assert response.status_code == 400, f"Expected 400 for exceeding limit, got {response.status_code}"
            assert "Maximum 20" in response.json().get("detail", "")
        else:
            # Not at limit, just verify the endpoint works
            pytest.skip(f"Only {current_count} alerts exist, not at 20 limit to test")
