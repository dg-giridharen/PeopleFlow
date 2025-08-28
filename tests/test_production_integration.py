"""
Production Integration Tests
End-to-end tests for the complete HR Assistant system
"""
import os
import sys
import unittest
import tempfile
from datetime import datetime, timedelta

# Add the parent directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from backend.models.database import db, DatabaseConfig, Employee, User, Asset
from backend.utils.database_manager import DatabaseManager
from backend.utils.auth import auth_manager, AuthenticatedUser
from backend.workflows.onboarding import OnboardingWorkflow
from backend.workflows.offboarding import OffboardingWorkflow, OffboardingReason
from backend.workflows.leave_approval import LeaveApprovalWorkflow
from backend.workflows.asset_issuance import AssetIssuanceWorkflow


class ProductionIntegrationTest(unittest.TestCase):
    """Integration tests for the complete production system"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        # Create test Flask app
        cls.app = Flask(__name__)
        cls.app.config['TESTING'] = True
        cls.app.config['SECRET_KEY'] = 'test-secret-key'
        cls.app.config['WTF_CSRF_ENABLED'] = False
        
        # Use in-memory SQLite for testing
        cls.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        cls.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        # Initialize database
        db.init_app(cls.app)
        auth_manager.init_app(cls.app)
        
        with cls.app.app_context():
            db.create_all()
            cls._create_test_data()
    
    @classmethod
    def _create_test_data(cls):
        """Create test data"""
        cls.db_manager = DatabaseManager()
        
        # Create test users
        admin_user_data = {
            'username': 'test_admin',
            'email': 'admin@test.com',
            'password': 'admin123',
            'role': 'admin'
        }
        cls.admin_user = cls.db_manager.create_user(admin_user_data)
        
        hr_user_data = {
            'username': 'test_hr',
            'email': 'hr@test.com',
            'password': 'hr123',
            'role': 'hr'
        }
        cls.hr_user = cls.db_manager.create_user(hr_user_data)
        
        # Create test employees
        test_employees = [
            {
                'employee_id': 'TEST001',
                'name': 'John Test',
                'email': 'john.test@company.com',
                'role': 'Software Engineer',
                'department': 'Engineering',
                'hire_date': '2024-01-15',
                'status': 'active'
            },
            {
                'employee_id': 'TEST002',
                'name': 'Jane Test',
                'email': 'jane.test@company.com',
                'role': 'Product Manager',
                'department': 'Product',
                'hire_date': '2024-02-01',
                'status': 'active'
            }
        ]
        
        for emp_data in test_employees:
            cls.db_manager.add_employee(emp_data)
        
        # Create test assets
        test_assets = [
            Asset(asset_id='TEST_LAP001', asset_type='laptop', brand='Dell', model='XPS 13', status='available'),
            Asset(asset_id='TEST_MON001', asset_type='monitor', brand='Samsung', model='27" 4K', status='available'),
            Asset(asset_id='TEST_PHN001', asset_type='phone', brand='iPhone', model='13', status='available')
        ]
        
        for asset in test_assets:
            db.session.add(asset)
        
        db.session.commit()
    
    def setUp(self):
        """Set up each test"""
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Initialize workflows
        self.onboarding_workflow = OnboardingWorkflow(self.db_manager)
        self.offboarding_workflow = OffboardingWorkflow(self.db_manager)
        self.leave_workflow = LeaveApprovalWorkflow(self.db_manager)
        self.asset_workflow = AssetIssuanceWorkflow(self.db_manager)
    
    def tearDown(self):
        """Clean up after each test"""
        self.app_context.pop()
    
    def test_complete_employee_lifecycle(self):
        """Test complete employee lifecycle from onboarding to offboarding"""
        # 1. Create new employee
        new_employee_data = {
            'employee_id': 'TEST003',
            'name': 'New Employee',
            'email': 'new.employee@company.com',
            'role': 'Data Scientist',
            'department': 'Engineering',
            'hire_date': datetime.now().strftime('%Y-%m-%d'),
            'status': 'active'
        }
        
        success = self.db_manager.add_employee(new_employee_data)
        self.assertTrue(success, "Failed to create new employee")
        
        # 2. Start onboarding process
        onboarding_result = self.onboarding_workflow.start_onboarding(
            employee_id='TEST003',
            start_date=datetime.now()
        )
        
        self.assertTrue(onboarding_result['success'], "Onboarding process failed to start")
        self.assertGreater(onboarding_result['tasks_created'], 0, "No onboarding tasks created")
        self.assertGreater(onboarding_result['assets_provisioned'], 0, "No assets provisioned")
        
        # 3. Verify employee can request leave
        leave_result = self.leave_workflow.process_leave_request(
            employee_id='TEST003',
            start_date=(datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            end_date=(datetime.now() + timedelta(days=32)).strftime('%Y-%m-%d'),
            leave_type='annual_leave'
        )
        
        self.assertTrue(leave_result['success'], "Leave request processing failed")
        
        # 4. Verify leave balance was updated
        leave_balance = self.db_manager.get_leave_balance('TEST003')
        self.assertIsNotNone(leave_balance, "Leave balance not found")
        self.assertEqual(leave_balance.annual_leave, 17.0, "Leave balance not updated correctly")  # 20 - 3 days
        
        # 5. Start offboarding process
        termination_date = datetime.now() + timedelta(days=60)
        offboarding_result = self.offboarding_workflow.initiate_offboarding(
            employee_id='TEST003',
            termination_date=termination_date,
            reason=OffboardingReason.RESIGNATION
        )
        
        self.assertTrue(offboarding_result['success'], "Offboarding process failed to start")
        self.assertGreater(offboarding_result['tasks_created'], 0, "No offboarding tasks created")
        
        # 6. Complete offboarding
        completion_result = self.offboarding_workflow.complete_offboarding('TEST003')
        self.assertTrue(completion_result['success'], "Offboarding completion failed")
        
        # 7. Verify employee is deactivated
        employee = self.db_manager.get_employee('TEST003')
        self.assertEqual(employee.status, 'inactive', "Employee not properly deactivated")
    
    def test_authentication_system(self):
        """Test authentication and authorization system"""
        # Test user authentication
        authenticated_user = auth_manager.authenticate_user('test_admin', 'admin123')
        self.assertIsNotNone(authenticated_user, "Admin authentication failed")
        self.assertTrue(authenticated_user.is_admin(), "Admin role not recognized")
        
        # Test JWT token creation
        token = auth_manager.create_access_token(authenticated_user)
        self.assertIsNotNone(token, "JWT token creation failed")
        
        # Test token verification
        payload = auth_manager.verify_access_token(token)
        self.assertIsNotNone(payload, "JWT token verification failed")
        self.assertEqual(payload['username'], 'test_admin', "Token payload incorrect")
        
        # Test HR user
        hr_user = auth_manager.authenticate_user('test_hr', 'hr123')
        self.assertIsNotNone(hr_user, "HR authentication failed")
        self.assertTrue(hr_user.is_hr(), "HR role not recognized")
        self.assertFalse(hr_user.is_admin(), "HR user should not be admin")
    
    def test_asset_management_workflow(self):
        """Test complete asset management workflow"""
        # Test asset provisioning for new hire
        result = self.asset_workflow.provision_assets_for_new_hire('TEST001')
        
        self.assertTrue(result['success'], "Asset provisioning failed")
        self.assertGreater(result['assets_assigned'], 0, "No assets were assigned")
        
        # Verify assets are assigned
        employee_assets = self.db_manager.get_employee_assets('TEST001')
        self.assertGreater(len(employee_assets), 0, "No assets found for employee")
        
        # Test asset return (for offboarding)
        if employee_assets:
            asset_id = employee_assets[0].asset_id
            return_result = self.offboarding_workflow.process_asset_return(
                employee_id='TEST001',
                asset_id=asset_id,
                condition='good',
                notes='Returned in good condition'
            )
            
            self.assertTrue(return_result['success'], "Asset return failed")
            
            # Verify asset is available again
            asset = self.db_manager.get_asset(asset_id)
            self.assertEqual(asset.status, 'available', "Asset not marked as available")
            self.assertIsNone(asset.assigned_to, "Asset still assigned to employee")
    
    def test_database_operations(self):
        """Test database operations and data integrity"""
        # Test employee CRUD operations
        employees = self.db_manager.get_all_employees()
        initial_count = len(employees)
        
        # Create employee
        new_emp_data = {
            'employee_id': 'TEST_DB001',
            'name': 'Database Test',
            'email': 'db.test@company.com',
            'role': 'Test Role',
            'department': 'Testing',
            'hire_date': '2024-01-01',
            'status': 'active'
        }
        
        success = self.db_manager.add_employee(new_emp_data)
        self.assertTrue(success, "Employee creation failed")
        
        # Verify employee count increased
        employees = self.db_manager.get_all_employees()
        self.assertEqual(len(employees), initial_count + 1, "Employee count not updated")
        
        # Test employee retrieval
        employee = self.db_manager.get_employee('TEST_DB001')
        self.assertIsNotNone(employee, "Employee retrieval failed")
        self.assertEqual(employee.name, 'Database Test', "Employee data incorrect")
        
        # Test employee update
        update_success = self.db_manager.update_employee('TEST_DB001', {'role': 'Updated Role'})
        self.assertTrue(update_success, "Employee update failed")
        
        # Verify update
        updated_employee = self.db_manager.get_employee('TEST_DB001')
        self.assertEqual(updated_employee.role, 'Updated Role', "Employee update not persisted")
        
        # Test employee deactivation
        deactivate_success = self.db_manager.deactivate_employee('TEST_DB001')
        self.assertTrue(deactivate_success, "Employee deactivation failed")
        
        # Verify deactivation
        deactivated_employee = self.db_manager.get_employee('TEST_DB001')
        self.assertEqual(deactivated_employee.status, 'inactive', "Employee not deactivated")
    
    def test_leave_management_system(self):
        """Test complete leave management system"""
        # Test leave balance creation
        balance_created = self.db_manager.create_initial_leave_balance('TEST001', 2024)
        self.assertTrue(balance_created, "Leave balance creation failed")
        
        # Test leave balance retrieval
        balance = self.db_manager.get_leave_balance('TEST001', 2024)
        self.assertIsNotNone(balance, "Leave balance retrieval failed")
        self.assertEqual(balance.annual_leave, 20.0, "Initial annual leave incorrect")
        
        # Test leave request processing
        leave_result = self.leave_workflow.process_leave_request(
            employee_id='TEST001',
            start_date=(datetime.now() + timedelta(days=10)).strftime('%Y-%m-%d'),
            end_date=(datetime.now() + timedelta(days=12)).strftime('%Y-%m-%d'),
            leave_type='annual_leave'
        )
        
        self.assertTrue(leave_result['success'], "Leave request processing failed")
        
        # Verify balance was deducted
        updated_balance = self.db_manager.get_leave_balance('TEST001', 2024)
        self.assertEqual(updated_balance.annual_leave, 17.0, "Leave balance not updated")  # 20 - 3 days
    
    def test_system_integration(self):
        """Test overall system integration"""
        # Test that all major components work together
        
        # 1. Authentication works
        user = auth_manager.authenticate_user('test_admin', 'admin123')
        self.assertIsNotNone(user, "Authentication integration failed")
        
        # 2. Database operations work
        employees = self.db_manager.get_all_employees()
        self.assertGreater(len(employees), 0, "Database integration failed")
        
        # 3. Workflows can access database
        onboarding_progress = self.onboarding_workflow.get_onboarding_progress('TEST001')
        self.assertTrue(onboarding_progress['success'], "Workflow-database integration failed")
        
        # 4. Asset management works
        assets = self.db_manager.get_all_assets()
        self.assertGreater(len(assets), 0, "Asset management integration failed")
        
        # 5. Leave system works
        leave_balances = self.db_manager.get_all_leave_balances()
        self.assertGreater(len(leave_balances), 0, "Leave system integration failed")


if __name__ == '__main__':
    # Run the integration tests
    unittest.main(verbosity=2)
