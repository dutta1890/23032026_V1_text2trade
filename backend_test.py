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
    def __init__(self, base_url: str = "https://email-service-7.preview.emergentagent.com"):
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

    def test_signup_new_user(self) -> bool:
        """Test signup with new user credentials."""
        url = f"{self.base_url}/api/signup"
        
        # Use timestamp to ensure unique email
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        test_email = f"test_user_{timestamp}@example.com"
        test_password = "testpass123"
        
        try:
            start_time = datetime.now()
            response = requests.post(url, json={
                "email": test_email,
                "password": test_password
            }, timeout=10)
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds()
            
            success = response.status_code == 200
            
            details = {
                "status_code": response.status_code,
                "response_time": response_time,
                "url": url,
                "test_email": test_email
            }
            
            if success:
                try:
                    data = response.json()
                    details.update({
                        "response_data": data,
                        "has_success": "success" in data,
                        "has_message": "message" in data,
                        "has_email": "email" in data,
                        "success_value": data.get("success"),
                        "message_value": data.get("message"),
                        "email_value": data.get("email")
                    })
                    
                    # Validate response structure
                    if not data.get("success"):
                        success = False
                        details["error"] = f"Expected success=true, got {data.get('success')}"
                    elif data.get("email") != test_email:
                        success = False
                        details["error"] = f"Expected email '{test_email}', got '{data.get('email')}'"
                    
                except json.JSONDecodeError as e:
                    success = False
                    details["error"] = f"Invalid JSON response: {str(e)}"
                    details["response_text"] = response.text[:200]
            else:
                details["error"] = f"HTTP {response.status_code}"
                try:
                    error_data = response.json()
                    details["error_detail"] = error_data.get("detail", "No detail provided")
                except:
                    details["response_text"] = response.text[:200]
                
        except requests.exceptions.RequestException as e:
            success = False
            details = {
                "error": f"Request failed: {str(e)}",
                "url": url
            }
        
        self.log_test("Signup New User", success, details)
        return success

    def test_signup_duplicate_email(self) -> bool:
        """Test signup with duplicate email (should fail)."""
        url = f"{self.base_url}/api/signup"
        
        # First, create a user
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        test_email = f"duplicate_test_{timestamp}@example.com"
        test_password = "testpass123"
        
        try:
            # First signup - should succeed
            first_response = requests.post(url, json={
                "email": test_email,
                "password": test_password
            }, timeout=10)
            
            if first_response.status_code != 200:
                success = False
                details = {
                    "error": "Failed to create initial user for duplicate test",
                    "first_signup_status": first_response.status_code,
                    "url": url
                }
            else:
                # Second signup with same email - should fail
                start_time = datetime.now()
                response = requests.post(url, json={
                    "email": test_email,
                    "password": test_password
                }, timeout=10)
                end_time = datetime.now()
                response_time = (end_time - start_time).total_seconds()
                
                success = response.status_code == 400
                
                details = {
                    "status_code": response.status_code,
                    "response_time": response_time,
                    "url": url,
                    "test_email": test_email,
                    "expected_status": 400
                }
                
                if success:
                    try:
                        data = response.json()
                        details.update({
                            "error_detail": data.get("detail"),
                            "response_data": data
                        })
                        
                        # Check if error message is appropriate
                        if "already registered" not in data.get("detail", "").lower():
                            print(f"   Warning: Error message might not be clear: {data.get('detail')}")
                        
                    except json.JSONDecodeError:
                        details["response_text"] = response.text[:200]
                else:
                    details["error"] = f"Expected 400 for duplicate email, got {response.status_code}"
                    try:
                        error_data = response.json()
                        details["unexpected_response"] = error_data
                    except:
                        details["response_text"] = response.text[:200]
                
        except requests.exceptions.RequestException as e:
            success = False
            details = {
                "error": f"Request failed: {str(e)}",
                "url": url
            }
        
        self.log_test("Signup Duplicate Email", success, details)
        return success

    def test_login_valid_credentials(self) -> bool:
        """Test login with valid credentials."""
        url_signup = f"{self.base_url}/api/signup"
        url_login = f"{self.base_url}/api/login"
        
        # Create a test user first
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        test_email = f"login_test_{timestamp}@example.com"
        test_password = "loginpass123"
        
        try:
            # First, create the user
            signup_response = requests.post(url_signup, json={
                "email": test_email,
                "password": test_password
            }, timeout=10)
            
            if signup_response.status_code != 200:
                success = False
                details = {
                    "error": "Failed to create user for login test",
                    "signup_status": signup_response.status_code,
                    "url": url_login
                }
            else:
                # Now test login
                start_time = datetime.now()
                response = requests.post(url_login, json={
                    "email": test_email,
                    "password": test_password
                }, timeout=10)
                end_time = datetime.now()
                response_time = (end_time - start_time).total_seconds()
                
                success = response.status_code == 200
                
                details = {
                    "status_code": response.status_code,
                    "response_time": response_time,
                    "url": url_login,
                    "test_email": test_email
                }
                
                if success:
                    try:
                        data = response.json()
                        details.update({
                            "response_data": data,
                            "has_success": "success" in data,
                            "has_message": "message" in data,
                            "has_email": "email" in data,
                            "success_value": data.get("success"),
                            "message_value": data.get("message"),
                            "email_value": data.get("email")
                        })
                        
                        # Validate response structure
                        if not data.get("success"):
                            success = False
                            details["error"] = f"Expected success=true, got {data.get('success')}"
                        elif data.get("email") != test_email:
                            success = False
                            details["error"] = f"Expected email '{test_email}', got '{data.get('email')}'"
                        
                    except json.JSONDecodeError as e:
                        success = False
                        details["error"] = f"Invalid JSON response: {str(e)}"
                        details["response_text"] = response.text[:200]
                else:
                    details["error"] = f"HTTP {response.status_code}"
                    try:
                        error_data = response.json()
                        details["error_detail"] = error_data.get("detail", "No detail provided")
                    except:
                        details["response_text"] = response.text[:200]
                
        except requests.exceptions.RequestException as e:
            success = False
            details = {
                "error": f"Request failed: {str(e)}",
                "url": url_login
            }
        
        self.log_test("Login Valid Credentials", success, details)
        return success

    def test_login_invalid_credentials(self) -> bool:
        """Test login with invalid credentials (should fail)."""
        url = f"{self.base_url}/api/login"
        
        # Use non-existent credentials
        test_email = "nonexistent@example.com"
        test_password = "wrongpassword"
        
        try:
            start_time = datetime.now()
            response = requests.post(url, json={
                "email": test_email,
                "password": test_password
            }, timeout=10)
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds()
            
            success = response.status_code == 401
            
            details = {
                "status_code": response.status_code,
                "response_time": response_time,
                "url": url,
                "test_email": test_email,
                "expected_status": 401
            }
            
            if success:
                try:
                    data = response.json()
                    details.update({
                        "error_detail": data.get("detail"),
                        "response_data": data
                    })
                    
                    # Check if error message is appropriate
                    if "invalid" not in data.get("detail", "").lower():
                        print(f"   Warning: Error message might not be clear: {data.get('detail')}")
                    
                except json.JSONDecodeError:
                    details["response_text"] = response.text[:200]
            else:
                details["error"] = f"Expected 401 for invalid credentials, got {response.status_code}"
                try:
                    error_data = response.json()
                    details["unexpected_response"] = error_data
                except:
                    details["response_text"] = response.text[:200]
                
        except requests.exceptions.RequestException as e:
            success = False
            details = {
                "error": f"Request failed: {str(e)}",
                "url": url
            }
        
        self.log_test("Login Invalid Credentials", success, details)
        return success

    def test_existing_test_user(self) -> bool:
        """Test login with the existing test user mentioned in context."""
        url = f"{self.base_url}/api/login"
        
        # Test with the existing user: test@example.com / pass123
        test_email = "test@example.com"
        test_password = "pass123"
        
        try:
            start_time = datetime.now()
            response = requests.post(url, json={
                "email": test_email,
                "password": test_password
            }, timeout=10)
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds()
            
            success = response.status_code == 200
            
            details = {
                "status_code": response.status_code,
                "response_time": response_time,
                "url": url,
                "test_email": test_email
            }
            
            if success:
                try:
                    data = response.json()
                    details.update({
                        "response_data": data,
                        "has_success": "success" in data,
                        "has_message": "message" in data,
                        "has_email": "email" in data,
                        "success_value": data.get("success"),
                        "message_value": data.get("message"),
                        "email_value": data.get("email")
                    })
                    
                    # Validate response structure
                    if not data.get("success"):
                        success = False
                        details["error"] = f"Expected success=true, got {data.get('success')}"
                    elif data.get("email") != test_email:
                        success = False
                        details["error"] = f"Expected email '{test_email}', got '{data.get('email')}'"
                    
                except json.JSONDecodeError as e:
                    success = False
                    details["error"] = f"Invalid JSON response: {str(e)}"
                    details["response_text"] = response.text[:200]
            else:
                details["error"] = f"HTTP {response.status_code}"
                try:
                    error_data = response.json()
                    details["error_detail"] = error_data.get("detail", "No detail provided")
                    # If user doesn't exist, that's also valuable info
                    if response.status_code == 401:
                        details["note"] = "Test user test@example.com may not exist in memory"
                except:
                    details["response_text"] = response.text[:200]
                
        except requests.exceptions.RequestException as e:
            success = False
            details = {
                "error": f"Request failed: {str(e)}",
                "url": url
            }
        
        self.log_test("Existing Test User Login", success, details)
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
            self.test_invalid_endpoint,
            self.test_signup_new_user,
            self.test_signup_duplicate_email,
            self.test_login_valid_credentials,
            self.test_login_invalid_credentials,
            self.test_existing_test_user
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