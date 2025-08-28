"""
API Endpoint Testing Script
Tests all Flask API endpoints and webhook functionality
"""
import requests
import json
import time
from datetime import datetime, timedelta


class APITester:
    """Test class for API endpoints"""
    
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def test_health_check(self):
        """Test the health check endpoint"""
        print("🔍 Testing Health Check Endpoint...")
        try:
            response = self.session.get(f"{self.base_url}/")
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Health check passed: {data['status']}")
                print(f"Service: {data['service']}")
                return True
            else:
                print(f"❌ Health check failed with status {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Health check error: {str(e)}")
            return False
    
    def test_get_employees(self):
        """Test getting all employees"""
        print("\n🔍 Testing Get All Employees...")
        try:
            response = self.session.get(f"{self.base_url}/api/employees")
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                employees = data.get("employees", [])
                print(f"✅ Found {len(employees)} employees")
                if employees:
                    print(f"Sample employee: {employees[0]['name']} ({employees[0]['employee_id']})")
                return True
            else:
                print(f"❌ Failed to get employees: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error getting employees: {str(e)}")
            return False
    
    def test_get_specific_employee(self, employee_id="EMP001"):
        """Test getting specific employee"""
        print(f"\n🔍 Testing Get Specific Employee ({employee_id})...")
        try:
            response = self.session.get(f"{self.base_url}/api/employees/{employee_id}")
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                employee = response.json()
                print(f"✅ Employee found: {employee['name']}")
                print(f"Role: {employee['role']}")
                print(f"Department: {employee['department']}")
                return True
            elif response.status_code == 404:
                print(f"❌ Employee {employee_id} not found")
                return False
            else:
                print(f"❌ Failed to get employee: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error getting employee: {str(e)}")
            return False
    
    def test_get_leave_balances(self):
        """Test getting all leave balances"""
        print("\n🔍 Testing Get All Leave Balances...")
        try:
            response = self.session.get(f"{self.base_url}/api/leave-balances")
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                balances = data.get("leave_balances", [])
                print(f"✅ Found {len(balances)} leave balance records")
                if balances:
                    sample = balances[0]
                    print(f"Sample: {sample['employee_id']} - Annual: {sample['annual_leave']} days")
                return True
            else:
                print(f"❌ Failed to get leave balances: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error getting leave balances: {str(e)}")
            return False
    
    def test_get_assets(self):
        """Test getting all assets"""
        print("\n🔍 Testing Get All Assets...")
        try:
            response = self.session.get(f"{self.base_url}/api/assets")
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                assets = data.get("assets", [])
                available_assets = [a for a in assets if a["status"] == "available"]
                assigned_assets = [a for a in assets if a["status"] == "assigned"]
                
                print(f"✅ Found {len(assets)} total assets")
                print(f"Available: {len(available_assets)}, Assigned: {len(assigned_assets)}")
                
                if assets:
                    sample = assets[0]
                    print(f"Sample: {sample['brand']} {sample['model']} ({sample['asset_id']})")
                return True
            else:
                print(f"❌ Failed to get assets: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error getting assets: {str(e)}")
            return False
    
    def test_leave_request_webhook(self, employee_id="EMP001"):
        """Test leave request via webhook"""
        print(f"\n🔍 Testing Leave Request Webhook for {employee_id}...")
        
        # Calculate future dates
        start_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        end_date = (datetime.now() + timedelta(days=11)).strftime("%Y-%m-%d")
        
        webhook_payload = {
            "queryResult": {
                "intent": {
                    "displayName": "leave.request"
                },
                "parameters": {
                    "employee-id": employee_id,
                    "start-date": start_date,
                    "end-date": end_date,
                    "leave-type": "annual"
                },
                "queryText": f"I want to request annual leave from {start_date} to {end_date}"
            }
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/webhook",
                json=webhook_payload,
                headers={"Content-Type": "application/json"}
            )
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                message = data.get("fulfillmentText", "")
                print(f"✅ Leave request processed")
                print(f"Response: {message[:100]}...")
                
                # Check if it was approved
                if "approved" in message.lower():
                    print("✅ Leave request was approved!")
                    return True
                else:
                    print("⚠️ Leave request was not approved")
                    return False
            else:
                print(f"❌ Webhook failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Error testing leave request webhook: {str(e)}")
            return False
    
    def test_asset_provision_webhook(self, employee_id="EMP010"):
        """Test asset provisioning via webhook"""
        print(f"\n🔍 Testing Asset Provisioning Webhook for {employee_id}...")
        
        webhook_payload = {
            "queryResult": {
                "intent": {
                    "displayName": "asset.provision"
                },
                "parameters": {
                    "employee-id": employee_id
                },
                "queryText": f"Provision assets for new hire {employee_id}"
            }
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/webhook",
                json=webhook_payload,
                headers={"Content-Type": "application/json"}
            )
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                message = data.get("fulfillmentText", "")
                print(f"✅ Asset provisioning processed")
                print(f"Response: {message[:100]}...")
                
                # Check if assets were assigned
                if "assigned" in message.lower():
                    print("✅ Assets were successfully assigned!")
                    return True
                else:
                    print("⚠️ Asset assignment may have failed")
                    return False
            else:
                print(f"❌ Webhook failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Error testing asset provisioning webhook: {str(e)}")
            return False
    
    def test_leave_balance_webhook(self, employee_id="EMP001"):
        """Test leave balance inquiry via webhook"""
        print(f"\n🔍 Testing Leave Balance Inquiry Webhook for {employee_id}...")
        
        webhook_payload = {
            "queryResult": {
                "intent": {
                    "displayName": "leave.balance"
                },
                "parameters": {
                    "employee-id": employee_id
                },
                "queryText": f"What is my leave balance for {employee_id}"
            }
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/webhook",
                json=webhook_payload,
                headers={"Content-Type": "application/json"}
            )
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                message = data.get("fulfillmentText", "")
                print(f"✅ Leave balance inquiry processed")
                print(f"Response: {message}")
                return True
            else:
                print(f"❌ Webhook failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error testing leave balance webhook: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all API tests"""
        print("🚀 Starting API Endpoint Tests")
        print("=" * 50)
        
        tests = [
            self.test_health_check,
            self.test_get_employees,
            lambda: self.test_get_specific_employee("EMP001"),
            self.test_get_leave_balances,
            self.test_get_assets,
            lambda: self.test_leave_balance_webhook("EMP001"),
            lambda: self.test_leave_request_webhook("EMP001"),
            lambda: self.test_asset_provision_webhook("EMP010")
        ]
        
        passed = 0
        total = len(tests)
        
        for test in tests:
            try:
                if test():
                    passed += 1
                time.sleep(1)  # Small delay between tests
            except Exception as e:
                print(f"❌ Test failed with exception: {str(e)}")
        
        print("\n" + "=" * 50)
        print(f"🏁 Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! The HR Assistant is working correctly.")
        else:
            print("⚠️ Some tests failed. Please check the server and data files.")
        
        return passed == total


def main():
    """Main function to run API tests"""
    print("AI-Powered HR Assistant - API Testing")
    print("Make sure the Flask server is running on http://localhost:5000")
    print()
    
    # Wait for user confirmation
    input("Press Enter when the server is ready...")
    
    tester = APITester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
