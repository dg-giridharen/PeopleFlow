"""
Database Manager for HR Assistant
SQLAlchemy-based replacement for JSON file operations
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, date
import logging
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_

from backend.models.database import db, Employee, LeaveBalance, Asset, LeaveRequest, User, AuditLog

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Handles CRUD operations using SQLAlchemy models"""
    
    def __init__(self, db_session=None):
        """
        Initialize database manager
        
        Args:
            db_session: Optional database session, uses db.session if not provided
        """
        self.db = db_session or db.session
    
    # Employee operations
    def get_employee(self, employee_id: str) -> Optional[Employee]:
        """Get employee by ID"""
        try:
            return self.db.query(Employee).filter(Employee.employee_id == employee_id).first()
        except Exception as e:
            logger.error(f"Error getting employee {employee_id}: {str(e)}")
            return None
    
    def get_all_employees(self, include_inactive: bool = False) -> List[Employee]:
        """Get all employees"""
        try:
            query = self.db.query(Employee)
            if not include_inactive:
                query = query.filter(Employee.status == 'active')
            return query.all()
        except Exception as e:
            logger.error(f"Error getting all employees: {str(e)}")
            return []
    
    def add_employee(self, employee_data: Dict[str, Any]) -> bool:
        """Add new employee"""
        try:
            # Convert hire_date string to datetime if needed
            hire_date = employee_data.get('hire_date')
            if isinstance(hire_date, str):
                hire_date = datetime.strptime(hire_date, '%Y-%m-%d').date()
            elif isinstance(hire_date, date):
                hire_date = hire_date
            else:
                hire_date = datetime.now().date()
            
            employee = Employee(
                employee_id=employee_data['employee_id'],
                name=employee_data['name'],
                email=employee_data['email'],
                role=employee_data['role'],
                department=employee_data['department'],
                hire_date=hire_date,
                manager_id=employee_data.get('manager_id'),
                status=employee_data.get('status', 'active')
            )
            
            self.db.add(employee)
            self.db.commit()
            
            # Create initial leave balance
            self.create_initial_leave_balance(employee_data['employee_id'])
            
            logger.info(f"Added employee: {employee_data['employee_id']}")
            return True
            
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Employee {employee_data['employee_id']} already exists: {str(e)}")
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error adding employee: {str(e)}")
            return False
    
    def update_employee(self, employee_id: str, update_data: Dict[str, Any]) -> bool:
        """Update existing employee"""
        try:
            employee = self.get_employee(employee_id)
            if not employee:
                return False
            
            # Update allowed fields
            updatable_fields = ['name', 'email', 'role', 'department', 'manager_id', 'status']
            for field in updatable_fields:
                if field in update_data:
                    setattr(employee, field, update_data[field])
            
            employee.updated_at = datetime.utcnow()
            self.db.commit()
            
            logger.info(f"Updated employee: {employee_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating employee {employee_id}: {str(e)}")
            return False
    
    def deactivate_employee(self, employee_id: str) -> bool:
        """Deactivate employee (soft delete)"""
        return self.update_employee(employee_id, {'status': 'inactive'})
    
    # Leave balance operations
    def get_leave_balance(self, employee_id: str, year: int = None) -> Optional[LeaveBalance]:
        """Get leave balance for employee"""
        try:
            if year is None:
                year = datetime.now().year
            
            return self.db.query(LeaveBalance).filter(
                and_(LeaveBalance.employee_id == employee_id, LeaveBalance.year == year)
            ).first()
        except Exception as e:
            logger.error(f"Error getting leave balance for {employee_id}: {str(e)}")
            return None
    
    def create_initial_leave_balance(self, employee_id: str, year: int = None) -> bool:
        """Create initial leave balance for new employee"""
        try:
            if year is None:
                year = datetime.now().year
            
            # Check if balance already exists
            existing = self.get_leave_balance(employee_id, year)
            if existing:
                return True
            
            leave_balance = LeaveBalance(
                employee_id=employee_id,
                year=year,
                annual_leave=20.0,
                sick_leave=10.0,
                personal_leave=5.0
            )
            
            self.db.add(leave_balance)
            self.db.commit()
            
            logger.info(f"Created initial leave balance for {employee_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating leave balance for {employee_id}: {str(e)}")
            return False
    
    def update_leave_balance(self, employee_id: str, leave_type: str, 
                           days_to_deduct: float, year: int = None) -> bool:
        """Update leave balance by deducting days"""
        try:
            if year is None:
                year = datetime.now().year
            
            balance = self.get_leave_balance(employee_id, year)
            if not balance:
                return False
            
            # Check if sufficient balance exists
            current_balance = getattr(balance, leave_type, 0)
            if current_balance < days_to_deduct:
                logger.warning(f"Insufficient {leave_type} balance for {employee_id}")
                return False
            
            # Deduct days
            setattr(balance, leave_type, current_balance - days_to_deduct)
            balance.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(f"Updated {leave_type} balance for {employee_id}: -{days_to_deduct} days")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating leave balance for {employee_id}: {str(e)}")
            return False
    
    def get_all_leave_balances(self, year: int = None) -> List[LeaveBalance]:
        """Get all leave balances"""
        try:
            query = self.db.query(LeaveBalance)
            if year:
                query = query.filter(LeaveBalance.year == year)
            return query.all()
        except Exception as e:
            logger.error(f"Error getting all leave balances: {str(e)}")
            return []
    
    # Asset operations
    def get_asset(self, asset_id: str) -> Optional[Asset]:
        """Get asset by ID"""
        try:
            return self.db.query(Asset).filter(Asset.asset_id == asset_id).first()
        except Exception as e:
            logger.error(f"Error getting asset {asset_id}: {str(e)}")
            return None
    
    def get_available_assets_by_type(self, asset_type: str) -> List[Asset]:
        """Get available assets of specific type"""
        try:
            return self.db.query(Asset).filter(
                and_(Asset.asset_type == asset_type, Asset.status == 'available')
            ).all()
        except Exception as e:
            logger.error(f"Error getting available assets of type {asset_type}: {str(e)}")
            return []
    
    def assign_asset(self, asset_id: str, employee_id: str) -> bool:
        """Assign asset to employee"""
        try:
            asset = self.get_asset(asset_id)
            if not asset or asset.status != 'available':
                return False
            
            # Check if employee exists
            employee = self.get_employee(employee_id)
            if not employee:
                return False
            
            asset.status = 'assigned'
            asset.assigned_to = employee_id
            asset.assigned_date = datetime.utcnow()
            asset.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(f"Assigned asset {asset_id} to employee {employee_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error assigning asset {asset_id} to {employee_id}: {str(e)}")
            return False
    
    def get_all_assets(self) -> List[Asset]:
        """Get all assets"""
        try:
            return self.db.query(Asset).all()
        except Exception as e:
            logger.error(f"Error getting all assets: {str(e)}")
            return []
    
    def get_employee_assets(self, employee_id: str) -> List[Asset]:
        """Get all assets assigned to an employee"""
        try:
            return self.db.query(Asset).filter(Asset.assigned_to == employee_id).all()
        except Exception as e:
            logger.error(f"Error getting assets for employee {employee_id}: {str(e)}")
            return []
    
    # Leave request operations
    def create_leave_request(self, request_data: Dict[str, Any]) -> Optional[LeaveRequest]:
        """Create a new leave request"""
        try:
            # Convert date strings to datetime objects
            start_date = request_data['start_date']
            end_date = request_data['end_date']
            
            if isinstance(start_date, str):
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            if isinstance(end_date, str):
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            # Calculate days requested
            days_requested = (end_date - start_date).days + 1
            
            leave_request = LeaveRequest(
                employee_id=request_data['employee_id'],
                leave_type=request_data['leave_type'],
                start_date=start_date,
                end_date=end_date,
                days_requested=days_requested,
                reason=request_data.get('reason', ''),
                status='pending'
            )
            
            self.db.add(leave_request)
            self.db.commit()
            
            logger.info(f"Created leave request for {request_data['employee_id']}")
            return leave_request
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating leave request: {str(e)}")
            return None
    
    def approve_leave_request(self, request_id: int, approved_by: str) -> bool:
        """Approve a leave request"""
        try:
            leave_request = self.db.query(LeaveRequest).filter(LeaveRequest.id == request_id).first()
            if not leave_request:
                return False
            
            leave_request.status = 'approved'
            leave_request.approved_by = approved_by
            leave_request.approved_date = datetime.utcnow()
            leave_request.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(f"Approved leave request {request_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error approving leave request {request_id}: {str(e)}")
            return False
    
    # User operations (for authentication)
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        try:
            return self.db.query(User).filter(User.username == username).first()
        except Exception as e:
            logger.error(f"Error getting user {username}: {str(e)}")
            return None
    
    def create_user(self, user_data: Dict[str, Any]) -> Optional[User]:
        """Create a new user"""
        try:
            user = User(
                username=user_data['username'],
                email=user_data['email'],
                role=user_data.get('role', 'employee')
            )
            user.set_password(user_data['password'])
            
            self.db.add(user)
            self.db.commit()
            
            logger.info(f"Created user: {user_data['username']}")
            return user
            
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"User {user_data['username']} already exists: {str(e)}")
            return None
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating user: {str(e)}")
            return None
    
    # Utility methods
    def get_role_asset_rules(self) -> Dict[str, List[str]]:
        """Get asset assignment rules by role (hardcoded for now)"""
        return {
            "Software Engineer": ["laptop", "monitor", "keyboard", "mouse"],
            "Data Scientist": ["laptop", "monitor", "keyboard", "mouse"],
            "Product Manager": ["laptop", "monitor"],
            "HR Manager": ["laptop", "monitor"],
            "Sales Representative": ["laptop", "phone"]
        }
    
    def commit(self):
        """Commit current transaction"""
        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error committing transaction: {str(e)}")
            raise
    
    def rollback(self):
        """Rollback current transaction"""
        self.db.rollback()
