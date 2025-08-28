"""
Comprehensive test suite for HR Assistant workflows
Tests both leave approval and asset issuance workflows
"""
import pytest
import json
import os
import sys
import tempfile
import shutil
from datetime import datetime, timedelta

# Add the parent directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.utils.data_manager import DataManager
from backend.workflows.leave_approval import LeaveApprovalWorkflow
from backend.workflows.asset_issuance import AssetIssuanceWorkflow


class TestDataManager:
    """Test the DataManager utility functions"""
    
    def setup_method(self):
        """Set up test environment with temporary data directory"""
        self.test_dir = tempfile.mkdtemp()
        self.data_manager = DataManager(self.test_dir)
        
        # Create test data
        self.create_test_data()
    
    def teardown_method(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)
    
    def create_test_data(self):
        """Create test data files"""
        # Test employees
        employees_data = {
            "employees": [
                {
                    "employee_id": "TEST001",
                    "name": "Test Employee",
                    "email": "test@company.com",
                    "role": "Software Engineer",
                    "department": "Engineering",
                    "hire_date": "2023-01-15",
                    "manager_id": "TEST002",
                    "status": "active"
                },
                {
                    "employee_id": "TEST002",
                    "name": "Test Manager",
                    "email": "manager@company.com",
                    "role": "Engineering Manager",
                    "department": "Engineering",
                    "hire_date": "2022-01-15",
                    "manager_id": None,
                    "status": "active"
                }
            ]
        }
        
        # Test leave balances
        leave_balances_data = {
            "leave_balances": [
                {
                    "employee_id": "TEST001",
                    "annual_leave": 20,
                    "sick_leave": 10,
                    "personal_leave": 5,
                    "year": 2025
                },
                {
                    "employee_id": "TEST002",
                    "annual_leave": 25,
                    "sick_leave": 12,
                    "personal_leave": 7,
                    "year": 2025
                }
            ]
        }
        
        # Test assets
        assets_data = {
            "assets": [
                {
                    "asset_id": "TEST_LAP001",
                    "asset_type": "laptop",
                    "brand": "Dell",
                    "model": "XPS 15",
                    "specifications": "Intel i7, 16GB RAM, 512GB SSD",
                    "status": "available",
                    "assigned_to": None,
                    "purchase_date": "2023-01-15",
                    "warranty_expiry": "2026-01-15"
                },
                {
                    "asset_id": "TEST_MON001",
                    "asset_type": "monitor",
                    "brand": "Dell",
                    "model": "UltraSharp 27",
                    "specifications": "27-inch 4K USB-C",
                    "status": "available",
                    "assigned_to": None,
                    "purchase_date": "2023-01-20",
                    "warranty_expiry": "2026-01-20"
                }
            ],
            "role_asset_rules": {
                "Software Engineer": ["laptop", "monitor"],
                "Engineering Manager": ["laptop", "monitor"]
            }
        }
        
        # Save test data
        self.data_manager._save_json(self.data_manager.employees_file, employees_data)
        self.data_manager._save_json(self.data_manager.leave_balances_file, leave_balances_data)
        self.data_manager._save_json(self.data_manager.assets_file, assets_data)
    
    def test_get_employee(self):
        """Test getting employee data"""
        employee = self.data_manager.get_employee("TEST001")
        assert employee is not None
        assert employee["name"] == "Test Employee"
        assert employee["role"] == "Software Engineer"
        
        # Test non-existent employee
        employee = self.data_manager.get_employee("NONEXISTENT")
        assert employee is None
    
    def test_get_leave_balance(self):
        """Test getting leave balance"""
        balance = self.data_manager.get_leave_balance("TEST001")
        assert balance is not None
        assert balance["annual_leave"] == 20
        assert balance["sick_leave"] == 10
        
        # Test non-existent employee
        balance = self.data_manager.get_leave_balance("NONEXISTENT")
        assert balance is None
    
    def test_update_leave_balance(self):
        """Test updating leave balance"""
        # Test successful update
        success = self.data_manager.update_leave_balance("TEST001", "annual_leave", 5)
        assert success is True
        
        # Verify balance was updated
        balance = self.data_manager.get_leave_balance("TEST001")
        assert balance["annual_leave"] == 15
        
        # Test insufficient balance
        success = self.data_manager.update_leave_balance("TEST001", "annual_leave", 20)
        assert success is False
    
    def test_asset_operations(self):
        """Test asset-related operations"""
        # Test getting available assets
        laptops = self.data_manager.get_available_assets_by_type("laptop")
        assert len(laptops) == 1
        assert laptops[0]["asset_id"] == "TEST_LAP001"
        
        # Test assigning asset
        success = self.data_manager.assign_asset("TEST_LAP001", "TEST001")
        assert success is True
        
        # Verify asset was assigned
        asset = self.data_manager.get_asset("TEST_LAP001")
        assert asset["status"] == "assigned"
        assert asset["assigned_to"] == "TEST001"
        
        # Test assigning already assigned asset
        success = self.data_manager.assign_asset("TEST_LAP001", "TEST002")
        assert success is False


class TestLeaveApprovalWorkflow:
    """Test the Leave Approval Workflow"""
    
    def setup_method(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.data_manager = DataManager(self.test_dir)
        self.workflow = LeaveApprovalWorkflow(self.data_manager)
        
        # Create test data
        self.create_test_data()
    
    def teardown_method(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)
    
    def create_test_data(self):
        """Create test data for leave workflow"""
        employees_data = {
            "employees": [
                {
                    "employee_id": "TEST001",
                    "name": "John Test",
                    "email": "john@company.com",
                    "role": "Software Engineer",
                    "department": "Engineering",
                    "hire_date": "2023-01-15",
                    "manager_id": "TEST002",
                    "status": "active"
                }
            ]
        }
        
        leave_balances_data = {
            "leave_balances": [
                {
                    "employee_id": "TEST001",
                    "annual_leave": 20,
                    "sick_leave": 10,
                    "personal_leave": 5,
                    "year": 2025
                }
            ]
        }
        
        self.data_manager._save_json(self.data_manager.employees_file, employees_data)
        self.data_manager._save_json(self.data_manager.leave_balances_file, leave_balances_data)
    
    def test_successful_leave_request(self):
        """Test successful leave request processing"""
        # Calculate future dates
        start_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        end_date = (datetime.now() + timedelta(days=11)).strftime("%Y-%m-%d")
        
        result = self.workflow.process_leave_request(
            employee_id="TEST001",
            start_date=start_date,
            end_date=end_date,
            leave_type="annual"
        )
        
        assert result["success"] is True
        assert "approved" in result["message"].lower()
        assert "details" in result
        business_days = result["details"]["business_days"]
        assert business_days > 0  # Should have some business days

        # Verify balance was updated
        balance = self.data_manager.get_leave_balance("TEST001")
        assert balance["annual_leave"] == 20 - business_days  # Original balance minus used days
    
    def test_insufficient_balance(self):
        """Test leave request with insufficient balance"""
        start_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        end_date = (datetime.now() + timedelta(days=50)).strftime("%Y-%m-%d")  # Way too many days

        result = self.workflow.process_leave_request(
            employee_id="TEST001",
            start_date=start_date,
            end_date=end_date,
            leave_type="annual"
        )

        assert result["success"] is False
        # Could be insufficient balance or too long period
        assert ("insufficient" in result["message"].lower() or
                "exceed" in result["message"].lower())
    
    def test_invalid_employee(self):
        """Test leave request for non-existent employee"""
        start_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        end_date = (datetime.now() + timedelta(days=11)).strftime("%Y-%m-%d")
        
        result = self.workflow.process_leave_request(
            employee_id="NONEXISTENT",
            start_date=start_date,
            end_date=end_date,
            leave_type="annual"
        )
        
        assert result["success"] is False
        assert "not found" in result["message"].lower()
    
    def test_invalid_dates(self):
        """Test leave request with invalid dates"""
        # Past date
        past_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        future_date = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        
        result = self.workflow.process_leave_request(
            employee_id="TEST001",
            start_date=past_date,
            end_date=future_date,
            leave_type="annual"
        )
        
        assert result["success"] is False
        assert "past" in result["message"].lower()


class TestAssetIssuanceWorkflow:
    """Test the Asset Issuance Workflow"""
    
    def setup_method(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.data_manager = DataManager(self.test_dir)
        self.workflow = AssetIssuanceWorkflow(self.data_manager)
        
        # Create test data
        self.create_test_data()
    
    def teardown_method(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)
    
    def create_test_data(self):
        """Create test data for asset workflow"""
        employees_data = {
            "employees": [
                {
                    "employee_id": "TEST001",
                    "name": "New Hire",
                    "email": "newhire@company.com",
                    "role": "Software Engineer",
                    "department": "Engineering",
                    "hire_date": "2024-01-15",
                    "manager_id": "TEST002",
                    "status": "active"
                }
            ]
        }
        
        assets_data = {
            "assets": [
                {
                    "asset_id": "TEST_LAP001",
                    "asset_type": "laptop",
                    "brand": "Dell",
                    "model": "XPS 15",
                    "specifications": "Intel i7, 16GB RAM, 512GB SSD",
                    "status": "available",
                    "assigned_to": None,
                    "purchase_date": "2023-01-15",
                    "warranty_expiry": "2026-01-15"
                },
                {
                    "asset_id": "TEST_MON001",
                    "asset_type": "monitor",
                    "brand": "Dell",
                    "model": "UltraSharp 27",
                    "specifications": "27-inch 4K USB-C",
                    "status": "available",
                    "assigned_to": None,
                    "purchase_date": "2023-01-20",
                    "warranty_expiry": "2026-01-20"
                }
            ],
            "role_asset_rules": {
                "Software Engineer": ["laptop", "monitor"],
                "Engineering Manager": ["laptop", "monitor", "headset"]
            }
        }
        
        self.data_manager._save_json(self.data_manager.employees_file, employees_data)
        self.data_manager._save_json(self.data_manager.assets_file, assets_data)
    
    def test_successful_asset_provisioning(self):
        """Test successful asset provisioning for new hire"""
        result = self.workflow.provision_assets_for_new_hire("TEST001")
        
        assert result["success"] is True
        assert "assigned assets" in result["message"].lower()
        assert "assigned_assets" in result
        assert len(result["assigned_assets"]) == 2  # laptop and monitor
        
        # Verify assets were assigned
        laptop = self.data_manager.get_asset("TEST_LAP001")
        monitor = self.data_manager.get_asset("TEST_MON001")
        
        assert laptop["status"] == "assigned"
        assert laptop["assigned_to"] == "TEST001"
        assert monitor["status"] == "assigned"
        assert monitor["assigned_to"] == "TEST001"
    
    def test_invalid_employee_asset_provisioning(self):
        """Test asset provisioning for non-existent employee"""
        result = self.workflow.provision_assets_for_new_hire("NONEXISTENT")
        
        assert result["success"] is False
        assert "not found" in result["message"].lower()
    
    def test_already_assigned_employee(self):
        """Test asset provisioning for employee who already has assets"""
        # First, assign assets
        self.workflow.provision_assets_for_new_hire("TEST001")
        
        # Try to assign again
        result = self.workflow.provision_assets_for_new_hire("TEST001")
        
        assert result["success"] is False
        assert "already has assets" in result["message"].lower()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
