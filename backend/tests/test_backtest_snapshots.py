"""
Test suite for backtest snapshot features:
- Immutable backtest snapshots
- Strategy versioning
- Data snapshot hashing
- Verify export ZIP
- Backtest comparison tool
- Permanent backtest URLs
"""

import pytest
import requests
import os
import zipfile
import io
import json

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    BASE_URL = "https://info-tooltips.preview.emergentagent.com"

API_URL = f"{BASE_URL}/api/v1"

# Test snapshot IDs from context
SNAPSHOT_A = "10f11267-d15d-4a4c-a992-a3442ccb9c5f"
SNAPSHOT_B = "a719b3eb-8b90-4eed-910f-59bb33ef62b9"

# Test credentials
TEST_USER_EMAIL = "testai@example.com"
TEST_USER_PASSWORD = "Password123!"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def auth_token(api_client):
    """Get authentication token for test user"""
    response = api_client.post(f"{API_URL}/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Authentication failed - skipping authenticated tests")


@pytest.fixture(scope="module")
def authenticated_client(api_client, auth_token):
    """Session with auth header"""
    api_client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api_client


class TestPublicSnapshotEndpoint:
    """Tests for GET /api/v1/backtest/snapshot/{snapshot_id} - public endpoint"""

    def test_get_snapshot_returns_200(self, api_client):
        """Public snapshot endpoint returns 200 for valid snapshot"""
        response = api_client.get(f"{API_URL}/backtest/snapshot/{SNAPSHOT_A}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"✓ GET /backtest/snapshot/{SNAPSHOT_A[:8]}... returns 200")

    def test_snapshot_has_required_fields(self, api_client):
        """Snapshot response contains all required fields"""
        response = api_client.get(f"{API_URL}/backtest/snapshot/{SNAPSHOT_A}")
        data = response.json()
        
        required_fields = [
            "snapshot_id", "strategy_version", "strategy_json_snapshot",
            "symbol", "timeframe", "start_date", "end_date",
            "engine_version", "data_snapshot_hash", "results",
            "trades", "equity_curve", "created_at", "is_immutable"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        print(f"✓ Snapshot contains all {len(required_fields)} required fields")

    def test_snapshot_excludes_user_id(self, api_client):
        """Public snapshot should NOT include user_id for privacy"""
        response = api_client.get(f"{API_URL}/backtest/snapshot/{SNAPSHOT_A}")
        data = response.json()
        assert "user_id" not in data, "user_id should be excluded from public snapshot"
        print("✓ Snapshot correctly excludes user_id")

    def test_snapshot_is_immutable(self, api_client):
        """Snapshot should have is_immutable=True"""
        response = api_client.get(f"{API_URL}/backtest/snapshot/{SNAPSHOT_A}")
        data = response.json()
        assert data.get("is_immutable") == True, "Snapshot should be marked as immutable"
        print("✓ Snapshot is marked as immutable")

    def test_snapshot_has_engine_version(self, api_client):
        """Snapshot should include engine version"""
        response = api_client.get(f"{API_URL}/backtest/snapshot/{SNAPSHOT_A}")
        data = response.json()
        assert data.get("engine_version"), "engine_version should be present"
        assert data["engine_version"] == "0.2.0", f"Expected engine v0.2.0, got {data['engine_version']}"
        print(f"✓ Snapshot has engine_version: {data['engine_version']}")

    def test_snapshot_has_data_hash(self, api_client):
        """Snapshot should include data snapshot hash for reproducibility"""
        response = api_client.get(f"{API_URL}/backtest/snapshot/{SNAPSHOT_A}")
        data = response.json()
        assert data.get("data_snapshot_hash"), "data_snapshot_hash should be present"
        assert len(data["data_snapshot_hash"]) == 64, "Hash should be SHA-256 (64 chars)"
        print(f"✓ Snapshot has data_snapshot_hash: {data['data_snapshot_hash'][:16]}...")

    def test_snapshot_not_found_returns_404(self, api_client):
        """Non-existent snapshot returns 404"""
        response = api_client.get(f"{API_URL}/backtest/snapshot/nonexistent-id-12345")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent snapshot returns 404")


class TestVerifyExportEndpoint:
    """Tests for GET /api/v1/backtest/snapshot/{snapshot_id}/verify - ZIP download"""

    def test_verify_returns_zip(self, api_client):
        """Verify endpoint returns application/zip content type"""
        response = api_client.get(f"{API_URL}/backtest/snapshot/{SNAPSHOT_A}/verify")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert "application/zip" in response.headers.get("Content-Type", ""), \
            f"Expected application/zip, got {response.headers.get('Content-Type')}"
        print("✓ Verify endpoint returns application/zip")

    def test_verify_zip_has_5_files(self, api_client):
        """ZIP should contain exactly 5 files"""
        response = api_client.get(f"{API_URL}/backtest/snapshot/{SNAPSHOT_A}/verify")
        zip_buffer = io.BytesIO(response.content)
        
        with zipfile.ZipFile(zip_buffer, 'r') as zf:
            files = zf.namelist()
            expected_files = ["strategy.json", "backtest_params.json", "data_used.csv", 
                           "expected_results.json", "README.txt"]
            
            for expected in expected_files:
                assert expected in files, f"Missing file in ZIP: {expected}"
            
            print(f"✓ ZIP contains all 5 required files: {files}")

    def test_verify_zip_strategy_json_valid(self, api_client):
        """strategy.json in ZIP should be valid JSON"""
        response = api_client.get(f"{API_URL}/backtest/snapshot/{SNAPSHOT_A}/verify")
        zip_buffer = io.BytesIO(response.content)
        
        with zipfile.ZipFile(zip_buffer, 'r') as zf:
            strategy_content = zf.read("strategy.json").decode("utf-8")
            strategy = json.loads(strategy_content)
            assert "entry_conditions" in strategy or "instrument" in strategy, \
                "strategy.json should contain strategy configuration"
            print("✓ strategy.json is valid JSON with strategy config")

    def test_verify_zip_backtest_params_valid(self, api_client):
        """backtest_params.json should contain snapshot metadata"""
        response = api_client.get(f"{API_URL}/backtest/snapshot/{SNAPSHOT_A}/verify")
        zip_buffer = io.BytesIO(response.content)
        
        with zipfile.ZipFile(zip_buffer, 'r') as zf:
            params_content = zf.read("backtest_params.json").decode("utf-8")
            params = json.loads(params_content)
            
            required_params = ["snapshot_id", "symbol", "timeframe", "engine_version", 
                             "data_snapshot_hash"]
            for param in required_params:
                assert param in params, f"Missing param in backtest_params.json: {param}"
            
            print(f"✓ backtest_params.json contains: {list(params.keys())}")

    def test_verify_zip_expected_results_valid(self, api_client):
        """expected_results.json should contain metrics and trades"""
        response = api_client.get(f"{API_URL}/backtest/snapshot/{SNAPSHOT_A}/verify")
        zip_buffer = io.BytesIO(response.content)
        
        with zipfile.ZipFile(zip_buffer, 'r') as zf:
            results_content = zf.read("expected_results.json").decode("utf-8")
            results = json.loads(results_content)
            
            assert "metrics" in results, "expected_results.json should have metrics"
            assert "trades" in results, "expected_results.json should have trades"
            print(f"✓ expected_results.json has metrics and {len(results.get('trades', []))} trades")

    def test_verify_zip_readme_exists(self, api_client):
        """README.txt should exist and contain verification instructions"""
        response = api_client.get(f"{API_URL}/backtest/snapshot/{SNAPSHOT_A}/verify")
        zip_buffer = io.BytesIO(response.content)
        
        with zipfile.ZipFile(zip_buffer, 'r') as zf:
            readme = zf.read("README.txt").decode("utf-8")
            assert "BACKTEST VERIFICATION" in readme, "README should have verification header"
            assert "HOW TO VERIFY" in readme, "README should have verification instructions"
            print("✓ README.txt contains verification instructions")

    def test_verify_not_found_returns_404(self, api_client):
        """Non-existent snapshot verify returns 404"""
        response = api_client.get(f"{API_URL}/backtest/snapshot/nonexistent-id/verify")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent snapshot verify returns 404")


class TestCompareSnapshotsEndpoint:
    """Tests for GET /api/v1/backtest/compare-snapshots?a=X&b=Y"""

    def test_compare_returns_200(self, api_client):
        """Compare endpoint returns 200 for valid snapshots"""
        response = api_client.get(
            f"{API_URL}/backtest/compare-snapshots?a={SNAPSHOT_A}&b={SNAPSHOT_B}"
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ Compare endpoint returns 200")

    def test_compare_has_snapshot_info(self, api_client):
        """Compare response includes both snapshot info"""
        response = api_client.get(
            f"{API_URL}/backtest/compare-snapshots?a={SNAPSHOT_A}&b={SNAPSHOT_B}"
        )
        data = response.json()
        
        assert "snapshot_a" in data, "Missing snapshot_a info"
        assert "snapshot_b" in data, "Missing snapshot_b info"
        assert data["snapshot_a"]["snapshot_id"] == SNAPSHOT_A
        assert data["snapshot_b"]["snapshot_id"] == SNAPSHOT_B
        print("✓ Compare response includes both snapshot info")

    def test_compare_has_same_data_flag(self, api_client):
        """Compare response includes same_data flag"""
        response = api_client.get(
            f"{API_URL}/backtest/compare-snapshots?a={SNAPSHOT_A}&b={SNAPSHOT_B}"
        )
        data = response.json()
        
        assert "same_data" in data, "Missing same_data flag"
        assert isinstance(data["same_data"], bool), "same_data should be boolean"
        print(f"✓ same_data flag: {data['same_data']}")

    def test_compare_has_same_engine_flag(self, api_client):
        """Compare response includes same_engine flag"""
        response = api_client.get(
            f"{API_URL}/backtest/compare-snapshots?a={SNAPSHOT_A}&b={SNAPSHOT_B}"
        )
        data = response.json()
        
        assert "same_engine" in data, "Missing same_engine flag"
        assert isinstance(data["same_engine"], bool), "same_engine should be boolean"
        print(f"✓ same_engine flag: {data['same_engine']}")

    def test_compare_has_metrics_diff(self, api_client):
        """Compare response includes metrics_diff with deltas"""
        response = api_client.get(
            f"{API_URL}/backtest/compare-snapshots?a={SNAPSHOT_A}&b={SNAPSHOT_B}"
        )
        data = response.json()
        
        assert "metrics_diff" in data, "Missing metrics_diff"
        md = data["metrics_diff"]
        
        expected_metrics = ["total_trades", "win_rate", "total_pnl_pct", 
                          "max_drawdown_pct", "sharpe_ratio", "profit_factor"]
        
        for metric in expected_metrics:
            assert metric in md, f"Missing metric in diff: {metric}"
            assert "a" in md[metric], f"Missing 'a' value for {metric}"
            assert "b" in md[metric], f"Missing 'b' value for {metric}"
            assert "delta" in md[metric], f"Missing 'delta' for {metric}"
        
        print(f"✓ metrics_diff contains {len(expected_metrics)} metrics with a/b/delta")

    def test_compare_missing_snapshot_returns_404(self, api_client):
        """Compare with non-existent snapshot returns 404"""
        response = api_client.get(
            f"{API_URL}/backtest/compare-snapshots?a={SNAPSHOT_A}&b=nonexistent-id"
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Compare with non-existent snapshot returns 404")

    def test_compare_missing_params_returns_422(self, api_client):
        """Compare without required params returns 422"""
        response = api_client.get(f"{API_URL}/backtest/compare-snapshots")
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("✓ Compare without params returns 422")


class TestUserSnapshotsEndpoint:
    """Tests for GET /api/v1/backtest/snapshots - authenticated user's snapshots"""

    def test_snapshots_requires_auth(self, api_client):
        """User snapshots endpoint requires authentication"""
        # Remove auth header temporarily
        auth_header = api_client.headers.pop("Authorization", None)
        response = api_client.get(f"{API_URL}/backtest/snapshots")
        if auth_header:
            api_client.headers["Authorization"] = auth_header
        
        assert response.status_code in [401, 403], \
            f"Expected 401/403 without auth, got {response.status_code}"
        print("✓ User snapshots endpoint requires authentication")

    def test_snapshots_returns_list(self, authenticated_client):
        """Authenticated user can list their snapshots"""
        response = authenticated_client.get(f"{API_URL}/backtest/snapshots")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "snapshots" in data, "Response should have 'snapshots' array"
        assert "count" in data, "Response should have 'count'"
        assert isinstance(data["snapshots"], list), "snapshots should be a list"
        print(f"✓ User has {data['count']} snapshots")


class TestBacktestCreatesSnapshot:
    """Tests for POST /api/v1/backtest - should create snapshot on success"""

    def test_backtest_returns_snapshot_id(self, authenticated_client):
        """Successful backtest returns snapshot_id in response"""
        strategy = {
            "instrument": {"symbol": "RELIANCE"},
            "timeframe": {"interval": "1d"},
            "entry_conditions": [
                {"name": "RSI", "params": {"period": 14}, "operator": "<", "value": 30}
            ],
            "exit_conditions": [
                {"name": "RSI", "params": {"period": 14}, "operator": ">", "value": 70}
            ],
            "risk_management": {}
        }
        
        response = authenticated_client.post(f"{API_URL}/backtest", json={
            "strategy": strategy,
            "slippage_pct": 0.05,
            "initial_capital": 100000
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert data.get("success") == True, "Backtest should succeed"
        assert "snapshot_id" in data, "Response should include snapshot_id"
        assert data["snapshot_id"], "snapshot_id should not be empty"
        print(f"✓ Backtest created snapshot: {data['snapshot_id'][:8]}...")

    def test_backtest_returns_engine_version(self, authenticated_client):
        """Backtest response includes engine_version"""
        strategy = {
            "instrument": {"symbol": "RELIANCE"},
            "timeframe": {"interval": "1d"},
            "entry_conditions": [
                {"name": "SMA", "params": {"short": 9, "long": 21}, "operator": "crosses_above"}
            ],
            "exit_conditions": [],
            "risk_management": {"stop_loss": {"type": "percentage", "value": 2}}
        }
        
        response = authenticated_client.post(f"{API_URL}/backtest", json={
            "strategy": strategy
        })
        
        data = response.json()
        assert "engine_version" in data, "Response should include engine_version"
        print(f"✓ Backtest response includes engine_version: {data.get('engine_version')}")

    def test_backtest_returns_data_hash(self, authenticated_client):
        """Backtest response includes data_snapshot_hash"""
        strategy = {
            "instrument": {"symbol": "RELIANCE"},
            "timeframe": {"interval": "1d"},
            "entry_conditions": [
                {"name": "EMA", "params": {"short": 12, "long": 26}, "operator": "crosses_above"}
            ],
            "exit_conditions": [],
            "risk_management": {}
        }
        
        response = authenticated_client.post(f"{API_URL}/backtest", json={
            "strategy": strategy
        })
        
        data = response.json()
        assert "data_snapshot_hash" in data, "Response should include data_snapshot_hash"
        assert len(data.get("data_snapshot_hash", "")) == 64, "Hash should be SHA-256"
        print(f"✓ Backtest response includes data_snapshot_hash: {data.get('data_snapshot_hash', '')[:16]}...")

    def test_backtest_returns_data_dates(self, authenticated_client):
        """Backtest response includes data_start and data_end"""
        strategy = {
            "instrument": {"symbol": "RELIANCE"},
            "timeframe": {"interval": "1d"},
            "entry_conditions": [
                {"name": "RSI", "params": {"period": 14}, "operator": "<", "value": 35}
            ],
            "exit_conditions": [],
            "risk_management": {}
        }
        
        response = authenticated_client.post(f"{API_URL}/backtest", json={
            "strategy": strategy
        })
        
        data = response.json()
        assert "data_start" in data, "Response should include data_start"
        assert "data_end" in data, "Response should include data_end"
        print(f"✓ Backtest data range: {data.get('data_start')} to {data.get('data_end')}")


class TestStrategyVersionsEndpoint:
    """Tests for GET /api/v1/strategy/{id}/versions - strategy version history"""

    def test_versions_requires_auth(self, api_client):
        """Strategy versions endpoint requires authentication"""
        # Remove auth header temporarily
        auth_header = api_client.headers.pop("Authorization", None)
        response = api_client.get(f"{API_URL}/strategy/some-id/versions")
        if auth_header:
            api_client.headers["Authorization"] = auth_header
        
        assert response.status_code in [401, 403], \
            f"Expected 401/403 without auth, got {response.status_code}"
        print("✓ Strategy versions endpoint requires authentication")

    def test_versions_not_found_for_invalid_strategy(self, authenticated_client):
        """Non-existent strategy returns 404"""
        response = authenticated_client.get(f"{API_URL}/strategy/nonexistent-id/versions")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent strategy versions returns 404")

    def test_create_and_update_strategy_creates_version(self, authenticated_client):
        """Creating and updating a strategy should create version history"""
        import uuid
        
        # 1. Create a new strategy
        strategy_name = f"TEST_Version_Strategy_{uuid.uuid4().hex[:8]}"
        create_response = authenticated_client.post(f"{API_URL}/strategy", json={
            "metadata": {"name": strategy_name, "description": "Test strategy for versioning"},
            "market": {"type": "equity", "exchange": "NSE"},
            "instrument": {"symbol": "RELIANCE"},
            "timeframe": {"interval": "1d"},
            "entry_conditions": [
                {"name": "RSI", "params": {"period": 14}, "operator": "<", "value": 30}
            ],
            "exit_conditions": [],
            "filters": [],
            "risk_management": {"stop_loss": {"type": "percentage", "value": 2}}
        })
        
        assert create_response.status_code == 200, f"Create failed: {create_response.text}"
        strategy_id = create_response.json().get("strategy", {}).get("id")
        assert strategy_id, "Strategy ID should be returned"
        print(f"✓ Created strategy: {strategy_id[:8]}...")
        
        # 2. Update the strategy
        update_response = authenticated_client.put(f"{API_URL}/strategy/{strategy_id}", json={
            "metadata": {"name": strategy_name, "description": "Updated description"},
            "market": {"type": "equity", "exchange": "NSE"},
            "instrument": {"symbol": "RELIANCE"},
            "timeframe": {"interval": "1d"},
            "entry_conditions": [
                {"name": "RSI", "params": {"period": 14}, "operator": "<", "value": 25}  # Changed value
            ],
            "exit_conditions": [],
            "filters": [],
            "risk_management": {"stop_loss": {"type": "percentage", "value": 3}}  # Changed SL
        })
        
        assert update_response.status_code == 200, f"Update failed: {update_response.text}"
        updated = update_response.json().get("strategy", {})
        assert updated.get("strategy_version", 1) > 1, "Version should increment after update"
        print(f"✓ Updated strategy to version {updated.get('strategy_version')}")
        
        # 3. Check version history
        versions_response = authenticated_client.get(f"{API_URL}/strategy/{strategy_id}/versions")
        assert versions_response.status_code == 200, f"Versions failed: {versions_response.text}"
        
        versions_data = versions_response.json()
        assert "versions" in versions_data, "Response should have 'versions'"
        assert len(versions_data["versions"]) >= 1, "Should have at least 1 version in history"
        
        # Check version structure
        if versions_data["versions"]:
            v = versions_data["versions"][0]
            assert "version" in v, "Version entry should have 'version'"
            assert "created_at" in v, "Version entry should have 'created_at'"
            assert "json_snapshot" in v, "Version entry should have 'json_snapshot'"
        
        print(f"✓ Strategy has {len(versions_data['versions'])} version(s) in history")
        
        # 4. Cleanup - delete the test strategy
        authenticated_client.delete(f"{API_URL}/strategy/{strategy_id}")
        print("✓ Cleaned up test strategy")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
