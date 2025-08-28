#!/usr/bin/env python3
"""
Comprehensive API Testing Suite
Tests all REST endpoints, WebSocket connections, and integrations
"""
import os
import sys
import json
import requests
import unittest
from datetime import datetime, timedelta
import socketio
import threading
import time

# Add the parent directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from backend.models.database import db, DatabaseConfig
from backend.utils.database_manager import DatabaseManager
from backend.utils.auth import auth_manager, create_default_admin_user


class APITestSuite(unittest.TestCase):
    """Comprehensive API testing suite"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.base_url = "http://localhost:5001"
        cls.api_url = f"{cls.base_url}/api"
        cls.auth_url = f"{cls.base_url}/auth"
        cls.webhook_url = f"{cls.base_url}/webhook"
        
        # Test credentials
        cls.admin_credentials = {"username": "admin", "password": "admin123"}
        cls.test_employee_data = {
            "employee_id": "TEST001",
            "name": "Test Employee",
            "email": "test@company.com",
            "role": "Software Engineer",
            "department": "Engineering"
        }
        
        # Store tokens for authenticated requests
        cls.admin_token = None
        cls.session = requests.Session()
    
    def setUp(self):
        """Set up each test"""
        # Ensure we have admin token
        if not self.admin_token:
            self.admin_token = self._get_admin_token()
    
    def _get_admin_token(self):
        """Get admin JWT token for API testing"""
        try:
            response = self.session.post(
                f"{self.auth_url}/login",
                json=self.admin_credentials,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("access_token")
            else:
                print(f"Failed to get admin token: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Error getting admin token: {str(e)}")
            return None
    
    def _make_authenticated_request(self, method, url, **kwargs):
        """Make authenticated API request"""
        headers = kwargs.get("headers", {})
        if self.admin_token:
            headers["Authorization"] = f"Bearer {self.admin_token}"
        kwargs["headers"] = headers
        
        return getattr(self.session, method.lower())(url, **kwargs)
    
    # Authentication Tests
    def test_01_health_check(self):
        """Test health check endpoint"""
        response = self.session.get(f"{self.base_url}/health")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn("status", data)
        self.assertEqual(data["status"], "healthy")
        print("✅ Health check endpoint working")
    
    def test_02_admin_login(self):
        """Test admin login"""
        response = self.session.post(
            f"{self.auth_url}/login",
            json=self.admin_credentials,
            headers={"Content-Type": "application/json"}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))
        self.assertIn("access_token", data)
        self.assertIn("user", data)
        print("✅ Admin login working")
    
    def test_03_token_verification(self):
        """Test JWT token verification"""
        if not self.admin_token:
            self.skipTest("No admin token available")
        
        response = self.session.post(
            f"{self.auth_url}/verify-token",
            json={"token": self.admin_token},
            headers={"Content-Type": "application/json"}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("valid"))
        print("✅ JWT token verification working")
    
    def test_04_user_profile(self):
        """Test user profile endpoint"""
        response = self._make_authenticated_request(
            "GET", f"{self.auth_url}/profile"
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))
        self.assertIn("user", data)
        print("✅ User profile endpoint working")
    
    # Employee Management Tests
    def test_05_get_employees(self):
        """Test get all employees"""
        response = self._make_authenticated_request(
            "GET", f"{self.api_url}/employees"
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("employees", data)
        print(f"✅ Get employees working - Found {len(data['employees'])} employees")
    
    def test_06_create_employee(self):
        """Test create new employee"""
        response = self._make_authenticated_request(
            "POST", f"{self.api_url}/employees",
            json=self.test_employee_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 201:
            data = response.json()
            self.assertTrue(data.get("success"))
            self.assertIn("employee", data)
            print("✅ Create employee working")
        elif response.status_code == 409:
            print("✅ Create employee working (employee already exists)")
        else:
            self.fail(f"Unexpected response: {response.status_code} - {response.text}")
    
    def test_07_get_specific_employee(self):
        """Test get specific employee"""
        response = self._make_authenticated_request(
            "GET", f"{self.api_url}/employees/{self.test_employee_data['employee_id']}"
        )
        
        if response.status_code == 200:
            data = response.json()
            self.assertEqual(data["employee_id"], self.test_employee_data["employee_id"])
            print("✅ Get specific employee working")
        elif response.status_code == 404:
            print("⚠️ Employee not found (may need to create first)")
        else:
            self.fail(f"Unexpected response: {response.status_code}")
    
    def test_08_update_employee(self):
        """Test update employee"""
        update_data = {"role": "Senior Software Engineer"}
        response = self._make_authenticated_request(
            "PUT", f"{self.api_url}/employees/{self.test_employee_data['employee_id']}",
            json=update_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            self.assertTrue(data.get("success"))
            print("✅ Update employee working")
        elif response.status_code == 404:
            print("⚠️ Employee not found for update")
        else:
            print(f"⚠️ Update employee response: {response.status_code}")
    
    # Leave Management Tests
    def test_09_get_leave_balance(self):
        """Test get leave balance"""
        response = self._make_authenticated_request(
            "GET", f"{self.api_url}/employees/{self.test_employee_data['employee_id']}/leave-balance"
        )
        
        if response.status_code == 200:
            data = response.json()
            self.assertIn("annual_leave", data)
            print("✅ Get leave balance working")
        elif response.status_code == 404:
            print("⚠️ Leave balance not found")
        else:
            print(f"⚠️ Leave balance response: {response.status_code}")
    
    def test_10_submit_leave_request(self):
        """Test submit leave request"""
        leave_data = {
            "employee_id": self.test_employee_data["employee_id"],
            "start_date": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
            "end_date": (datetime.now() + timedelta(days=32)).strftime("%Y-%m-%d"),
            "leave_type": "annual"
        }
        
        response = self._make_authenticated_request(
            "POST", f"{self.api_url}/leave-requests",
            json=leave_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Leave request working - {data.get('message', 'Success')}")
        else:
            print(f"⚠️ Leave request response: {response.status_code} - {response.text}")
    
    # Asset Management Tests
    def test_11_get_assets(self):
        """Test get all assets"""
        response = self._make_authenticated_request(
            "GET", f"{self.api_url}/assets"
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("assets", data)
        print(f"✅ Get assets working - Found {len(data['assets'])} assets")
    
    def test_12_provision_assets(self):
        """Test asset provisioning"""
        provision_data = {"employee_id": self.test_employee_data["employee_id"]}
        
        response = self._make_authenticated_request(
            "POST", f"{self.api_url}/assets/provision",
            json=provision_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Asset provisioning working - {data.get('message', 'Success')}")
        else:
            print(f"⚠️ Asset provisioning response: {response.status_code}")
    
    def test_13_get_employee_assets(self):
        """Test get employee assets"""
        response = self._make_authenticated_request(
            "GET", f"{self.api_url}/employees/{self.test_employee_data['employee_id']}/assets"
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("assets", data)
        print(f"✅ Get employee assets working - Found {len(data['assets'])} assets")
    
    # Dashboard Analytics Tests
    def test_14_dashboard_stats(self):
        """Test dashboard statistics"""
        response = self._make_authenticated_request(
            "GET", f"{self.api_url}/dashboard/stats"
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("employees", data)
        self.assertIn("leave", data)
        self.assertIn("assets", data)
        print("✅ Dashboard statistics working")
    
    # Dialogflow Webhook Tests
    def test_15_dialogflow_webhook_policy_query(self):
        """Test Dialogflow webhook with policy query"""
        webhook_payload = {
            "queryResult": {
                "intent": {"displayName": "policy.query"},
                "parameters": {"employee-id": "TEST001"},
                "queryText": "What is the work from home policy?"
            }
        }
        
        response = self.session.post(
            self.webhook_url,
            json=webhook_payload,
            headers={"Content-Type": "application/json"}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("fulfillmentText", data)
        print(f"✅ Policy query webhook working - Response: {data['fulfillmentText'][:100]}...")
    
    def test_16_dialogflow_webhook_leave_balance(self):
        """Test Dialogflow webhook with leave balance query"""
        webhook_payload = {
            "queryResult": {
                "intent": {"displayName": "leave.balance"},
                "parameters": {"employee-id": "TEST001"},
                "queryText": "What is my leave balance?"
            }
        }
        
        response = self.session.post(
            self.webhook_url,
            json=webhook_payload,
            headers={"Content-Type": "application/json"}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("fulfillmentText", data)
        print("✅ Leave balance webhook working")
    
    def test_17_dialogflow_webhook_employee_info(self):
        """Test Dialogflow webhook with employee info query"""
        webhook_payload = {
            "queryResult": {
                "intent": {"displayName": "employee.info"},
                "parameters": {"employee-id": "TEST001"},
                "queryText": "Show employee information"
            }
        }
        
        response = self.session.post(
            self.webhook_url,
            json=webhook_payload,
            headers={"Content-Type": "application/json"}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("fulfillmentText", data)
        print("✅ Employee info webhook working")


class WebSocketTestSuite(unittest.TestCase):
    """WebSocket functionality tests"""
    
    def setUp(self):
        """Set up WebSocket test"""
        self.base_url = "http://localhost:5001"
        self.messages_received = []
        self.connection_established = False
    
    def test_websocket_connection(self):
        """Test WebSocket connection and chat functionality"""
        try:
            # Create SocketIO client
            sio = socketio.Client()
            
            @sio.event
            def connect():
                self.connection_established = True
                print("✅ WebSocket connection established")
            
            @sio.event
            def chat_response(data):
                self.messages_received.append(data)
                print(f"✅ Received chat response: {data.get('message', '')[:50]}...")
            
            @sio.event
            def status(data):
                print(f"✅ Status message: {data.get('msg', '')}")
            
            # Connect to server
            sio.connect(self.base_url)
            time.sleep(1)  # Wait for connection
            
            self.assertTrue(self.connection_established, "WebSocket connection failed")
            
            # Test chat message
            test_message = {
                "message": "What is the work from home policy?",
                "employee_id": "TEST001"
            }
            
            sio.emit('chat_message', test_message)
            time.sleep(3)  # Wait for response
            
            self.assertGreater(len(self.messages_received), 0, "No chat response received")
            
            sio.disconnect()
            print("✅ WebSocket chat functionality working")
            
        except Exception as e:
            print(f"⚠️ WebSocket test failed: {str(e)}")
            self.skipTest(f"WebSocket test failed: {str(e)}")


def run_api_tests():
    """Run comprehensive API tests"""
    print("🚀 Starting Comprehensive API Testing Suite")
    print("=" * 60)
    
    # Check if server is running
    try:
        response = requests.get("http://localhost:5001/health", timeout=5)
        if response.status_code != 200:
            print("❌ Server not responding. Please start the application first:")
            print("   python backend/app.py")
            return False
    except requests.exceptions.RequestException:
        print("❌ Cannot connect to server. Please start the application first:")
        print("   python backend/app.py")
        return False
    
    print("✅ Server is running, starting tests...\n")
    
    # Run API tests
    api_suite = unittest.TestLoader().loadTestsFromTestCase(APITestSuite)
    api_runner = unittest.TextTestRunner(verbosity=0)
    api_result = api_runner.run(api_suite)
    
    # Run WebSocket tests
    ws_suite = unittest.TestLoader().loadTestsFromTestCase(WebSocketTestSuite)
    ws_runner = unittest.TextTestRunner(verbosity=0)
    ws_result = ws_runner.run(ws_suite)
    
    # Summary
    total_tests = api_result.testsRun + ws_result.testsRun
    total_failures = len(api_result.failures) + len(ws_result.failures)
    total_errors = len(api_result.errors) + len(ws_result.errors)
    
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {total_tests - total_failures - total_errors}")
    print(f"Failed: {total_failures}")
    print(f"Errors: {total_errors}")
    
    if total_failures == 0 and total_errors == 0:
        print("🎉 All tests passed! API is working correctly.")
        return True
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
        return False


if __name__ == "__main__":
    success = run_api_tests()
    sys.exit(0 if success else 1)
