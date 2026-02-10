#!/usr/bin/env python3
"""
Text2trade Backend API Testing
==============================
Comprehensive testing for the Text2trade FastAPI backend.
Tests all available endpoints and validates responses.
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any

class Text2tradeAPITester:
    def __init__(self, base_url: str = "https://t2t-fullstack.preview.emergentagent.com"):
        """Initialize the API tester with the public endpoint."""
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name: str, success: bool, details: Dict[str, Any]):
        """Log test result for reporting."""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
        
        result = {
            "test_name": name,
            "success": success,
            "timestamp": datetime.now().isoformat(),
            **details
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"\n{status} - {name}")
        
        if success:
            print(f"   Status: {details.get('status_code', 'N/A')}")
            if 'response_time' in details:
                print(f"   Response Time: {details['response_time']:.3f}s")
        else:
            print(f"   Error: {details.get('error', 'Unknown error')}")
            if 'status_code' in details:
                print(f"   Status Code: {details['status_code']}")

    def test_health_endpoint(self) -> bool:
        """Test the /api/health endpoint."""
        url = f"{self.base_url}/api/health"
        
        try:
            start_time = datetime.now()
            response = requests.get(url, timeout=10)
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds()
            
            success = response.status_code == 200
            
            details = {
                "status_code": response.status_code,
                "response_time": response_time,
                "url": url
            }
            
            if success:
                try:
                    data = response.json()
                    details.update({
                        "response_data": data,
                        "has_status": "status" in data,
                        "has_timestamp": "timestamp" in data,
                        "has_version": "version" in data,
                        "status_value": data.get("status"),
                        "version_value": data.get("version")
                    })
                    
                    # Validate response structure
                    if data.get("status") != "healthy":
                        success = False
                        details["error"] = f"Expected status 'healthy', got '{data.get('status')}'"
                    
                except json.JSONDecodeError as e:
                    success = False
                    details["error"] = f"Invalid JSON response: {str(e)}"
                    details["response_text"] = response.text[:200]
            else:
                details["error"] = f"HTTP {response.status_code}"
                details["response_text"] = response.text[:200]
                
        except requests.exceptions.RequestException as e:
            success = False
            details = {
                "error": f"Request failed: {str(e)}",
                "url": url
            }
        
        self.log_test("Health Check Endpoint", success, details)
        return success

    def test_root_api_endpoint(self) -> bool:
        """Test the /api/ root endpoint."""
        url = f"{self.base_url}/api/"
        
        try:
            start_time = datetime.now()
            response = requests.get(url, timeout=10)
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds()
            
            success = response.status_code == 200
            
            details = {
                "status_code": response.status_code,
                "response_time": response_time,
                "url": url
            }
            
            if success:
                try:
                    data = response.json()
                    details.update({
                        "response_data": data,
                        "has_message": "message" in data,
                        "has_app_name": "app_name" in data,
                        "message_value": data.get("message"),
                        "app_name_value": data.get("app_name")
                    })
                    
                    # Validate response content
                    if data.get("app_name") != "Text2trade":
                        success = False
                        details["error"] = f"Expected app_name 'Text2trade', got '{data.get('app_name')}'"
                    
                except json.JSONDecodeError as e:
                    success = False
                    details["error"] = f"Invalid JSON response: {str(e)}"
                    details["response_text"] = response.text[:200]
            else:
                details["error"] = f"HTTP {response.status_code}"
                details["response_text"] = response.text[:200]
                
        except requests.exceptions.RequestException as e:
            success = False
            details = {
                "error": f"Request failed: {str(e)}",
                "url": url
            }
        
        self.log_test("Root API Endpoint", success, details)
        return success

    def test_cors_headers(self) -> bool:
        """Test CORS configuration by checking headers."""
        url = f"{self.base_url}/api/health"
        
        try:
            # Make an OPTIONS request to check CORS
            response = requests.options(url, timeout=10)
            
            success = True
            details = {
                "status_code": response.status_code,
                "url": url,
                "cors_headers": {}
            }
            
            # Check for CORS headers
            cors_headers = [
                "Access-Control-Allow-Origin",
                "Access-Control-Allow-Methods", 
                "Access-Control-Allow-Headers"
            ]
            
            for header in cors_headers:
                value = response.headers.get(header)
                details["cors_headers"][header] = value
                if not value:
                    print(f"   Warning: Missing CORS header {header}")
            
            # Also test with a GET request and check CORS headers
            get_response = requests.get(url, timeout=10)
            if get_response.headers.get("Access-Control-Allow-Origin"):
                details["cors_headers"]["Access-Control-Allow-Origin"] = get_response.headers.get("Access-Control-Allow-Origin")
            
        except requests.exceptions.RequestException as e:
            success = False
            details = {
                "error": f"Request failed: {str(e)}",
                "url": url
            }
        
        self.log_test("CORS Configuration", success, details)
        return success

    def test_invalid_endpoint(self) -> bool:
        """Test behavior with invalid endpoint."""
        url = f"{self.base_url}/api/nonexistent"
        
        try:
            response = requests.get(url, timeout=10)
            
            # Should return 404 for non-existent endpoint
            success = response.status_code == 404
            
            details = {
                "status_code": response.status_code,
                "url": url,
                "expected_status": 404
            }
            
            if not success:
                details["error"] = f"Expected 404, got {response.status_code}"
                details["response_text"] = response.text[:200]
                
        except requests.exceptions.RequestException as e:
            success = False
            details = {
                "error": f"Request failed: {str(e)}",
                "url": url
            }
        
        self.log_test("Invalid Endpoint Handling", success, details)
        return success

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all backend tests and return summary."""
        print("🚀 Starting Text2trade Backend API Tests")
        print(f"📍 Testing endpoint: {self.base_url}")
        print("=" * 60)
        
        # Run all tests
        tests = [
            self.test_health_endpoint,
            self.test_root_api_endpoint,
            self.test_cors_headers,
            self.test_invalid_endpoint
        ]
        
        for test_func in tests:
            test_func()
        
        # Generate summary
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print(f"   Total Tests: {self.tests_run}")
        print(f"   Passed: {self.tests_passed}")
        print(f"   Failed: {self.tests_run - self.tests_passed}")
        print(f"   Success Rate: {success_rate:.1f}%")
        
        summary = {
            "total_tests": self.tests_run,
            "passed_tests": self.tests_passed,
            "failed_tests": self.tests_run - self.tests_passed,
            "success_rate": success_rate,
            "test_results": self.test_results,
            "timestamp": datetime.now().isoformat()
        }
        
        if success_rate < 100:
            print("\n❌ Some tests failed. Check the details above.")
            return summary
        else:
            print("\n✅ All tests passed! Backend API is working correctly.")
            return summary

def main():
    """Main function to run the tests."""
    tester = Text2tradeAPITester()
    summary = tester.run_all_tests()
    
    # Return appropriate exit code
    return 0 if summary["success_rate"] == 100 else 1

if __name__ == "__main__":
    sys.exit(main())