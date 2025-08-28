"""
Employee CRUD Operations Test
Tests the complete Create, Read, Update, Delete functionality for employees
"""
import requests
import json
from datetime import datetime


class EmployeeCRUDTester:
    """Test class for employee CRUD operations"""
    
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_employee_id = "EMP999"
    
    def test_create_employee(self):
        """Test creating a new employee"""
        print("🔍 Testing Employee Creation...")
        
        employee_data = {
            "employee_id": self.test_employee_id,
            "name": "Test Employee",
            "email": "test.employee@company.com",
            "role": "Software Engineer",
            "department": "Engineering",
            "hire_date": datetime.now().strftime('%Y-%m-%d'),
            "status": "active"
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/employees",
                json=employee_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 201:
                result = response.json()
                if result.get('success'):
                    print("✅ Employee created successfully")
                    print(f"   Employee: {result['employee']['name']}")
                    print(f"   ID: {result['employee']['employee_id']}")
                    return True
                else:
                    print(f"❌ Creation failed: {result.get('message', 'Unknown error')}")
                    return False
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data.get('error', 'Unknown error')}")
                except:
                    print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Exception during creation: {str(e)}")
            return False
    
    def test_read_employee(self):
        """Test reading employee data"""
        print("\n🔍 Testing Employee Read...")
        
        try:
            response = self.session.get(f"{self.base_url}/api/employees/{self.test_employee_id}")
            
            if response.status_code == 200:
                employee = response.json()
                print("✅ Employee retrieved successfully")
                print(f"   Name: {employee['name']}")
                print(f"   Email: {employee['email']}")
                print(f"   Role: {employee['role']}")
                print(f"   Department: {employee['department']}")
                return True
            elif response.status_code == 404:
                print("❌ Employee not found")
                return False
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Exception during read: {str(e)}")
            return False
    
    def test_update_employee(self):
        """Test updating employee data"""
        print("\n🔍 Testing Employee Update...")
        
        update_data = {
            "name": "Test Employee Updated",
            "email": "test.updated@company.com",
            "role": "Senior Software Engineer",
            "department": "Engineering"
        }
        
        try:
            response = self.session.put(
                f"{self.base_url}/api/employees/{self.test_employee_id}",
                json=update_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    print("✅ Employee updated successfully")
                    print(f"   New name: {result['employee']['name']}")
                    print(f"   New role: {result['employee']['role']}")
                    return True
                else:
                    print(f"❌ Update failed: {result.get('message', 'Unknown error')}")
                    return False
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data.get('error', 'Unknown error')}")
                except:
                    print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Exception during update: {str(e)}")
            return False
    
    def test_delete_employee(self):
        """Test deleting (deactivating) employee"""
        print("\n🔍 Testing Employee Deletion (Deactivation)...")
        
        try:
            response = self.session.delete(f"{self.base_url}/api/employees/{self.test_employee_id}")
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    print("✅ Employee deactivated successfully")
                    
                    # Verify the employee is now inactive
                    verify_response = self.session.get(f"{self.base_url}/api/employees/{self.test_employee_id}")
                    if verify_response.status_code == 200:
                        employee = verify_response.json()
                        if employee['status'] == 'inactive':
                            print("✅ Employee status confirmed as inactive")
                            return True
                        else:
                            print(f"⚠️ Employee status is {employee['status']}, expected 'inactive'")
                            return False
                    else:
                        print("❌ Failed to verify employee status")
                        return False
                else:
                    print(f"❌ Deletion failed: {result.get('message', 'Unknown error')}")
                    return False
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Exception during deletion: {str(e)}")
            return False
    
    def test_validation_errors(self):
        """Test validation error handling"""
        print("\n🔍 Testing Validation Errors...")
        
        test_cases = [
            {
                "name": "Missing required fields",
                "data": {"name": "Test"},
                "expected_error": "Missing required field"
            },
            {
                "name": "Invalid employee ID format",
                "data": {
                    "employee_id": "INVALID",
                    "name": "Test",
                    "email": "test@test.com",
                    "role": "Engineer",
                    "department": "Engineering"
                },
                "expected_error": "Employee ID must be in format EMP001"
            },
            {
                "name": "Invalid email format",
                "data": {
                    "employee_id": "EMP998",
                    "name": "Test",
                    "email": "invalid-email",
                    "role": "Engineer",
                    "department": "Engineering"
                },
                "expected_error": "Invalid email format"
            }
        ]
        
        passed = 0
        total = len(test_cases)
        
        for test_case in test_cases:
            try:
                response = self.session.post(
                    f"{self.base_url}/api/employees",
                    json=test_case["data"],
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 400:
                    error_data = response.json()
                    if test_case["expected_error"] in error_data.get("error", ""):
                        print(f"✅ {test_case['name']}: Validation working correctly")
                        passed += 1
                    else:
                        print(f"⚠️ {test_case['name']}: Unexpected error message")
                        print(f"   Expected: {test_case['expected_error']}")
                        print(f"   Got: {error_data.get('error', 'No error message')}")
                else:
                    print(f"❌ {test_case['name']}: Expected 400, got {response.status_code}")
                    
            except Exception as e:
                print(f"❌ {test_case['name']}: Exception - {str(e)}")
        
        print(f"\nValidation Tests: {passed}/{total} passed")
        return passed == total
    
    def test_duplicate_employee_id(self):
        """Test handling of duplicate employee IDs"""
        print("\n🔍 Testing Duplicate Employee ID Handling...")
        
        # Try to create an employee with an existing ID
        duplicate_data = {
            "employee_id": "EMP001",  # This should already exist
            "name": "Duplicate Test",
            "email": "duplicate@company.com",
            "role": "Software Engineer",
            "department": "Engineering"
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/employees",
                json=duplicate_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 409:
                error_data = response.json()
                print("✅ Duplicate ID properly rejected")
                print(f"   Error: {error_data.get('error', 'Unknown error')}")
                return True
            else:
                print(f"❌ Expected 409 Conflict, got {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Exception during duplicate test: {str(e)}")
            return False
    
    def cleanup_test_data(self):
        """Clean up test data"""
        print("\n🧹 Cleaning up test data...")
        
        try:
            # Try to delete the test employee if it exists
            response = self.session.delete(f"{self.base_url}/api/employees/{self.test_employee_id}")
            if response.status_code == 200:
                print("✅ Test employee cleaned up")
            else:
                print("ℹ️ Test employee not found (already cleaned up)")
        except:
            print("ℹ️ Cleanup completed")
    
    def run_all_tests(self):
        """Run all CRUD tests"""
        print("🚀 Starting Employee CRUD Tests")
        print("=" * 60)
        
        tests = [
            ('Employee Creation', self.test_create_employee),
            ('Employee Read', self.test_read_employee),
            ('Employee Update', self.test_update_employee),
            ('Employee Deletion', self.test_delete_employee),
            ('Validation Errors', self.test_validation_errors),
            ('Duplicate ID Handling', self.test_duplicate_employee_id)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            try:
                if test_func():
                    passed += 1
            except Exception as e:
                print(f"❌ {test_name} failed with exception: {str(e)}")
        
        # Cleanup
        self.cleanup_test_data()
        
        print("\n" + "=" * 60)
        print(f"🏁 Employee CRUD Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All Employee CRUD tests passed! The system is working correctly.")
        else:
            print("⚠️ Some tests failed. Please check the implementation.")
        
        return passed == total


def main():
    """Main function to run CRUD tests"""
    print("AI-Powered HR Assistant - Employee CRUD Testing")
    print("Make sure the Flask server is running on http://localhost:5000")
    print()
    
    # Wait for user confirmation
    input("Press Enter when the server is ready...")
    
    tester = EmployeeCRUDTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
