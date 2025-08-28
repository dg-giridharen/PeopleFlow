"""
Database models and configuration for HR Assistant
SQLAlchemy models replacing JSON file storage
"""
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(db.Model):
    """User model for authentication and authorization"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default='employee')  # admin, hr, manager, employee
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    
    # Relationship to employee
    employee = relationship("Employee", back_populates="user", uselist=False)
    
    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def has_role(self, role):
        """Check if user has specific role"""
        return self.role == role
    
    def is_admin(self):
        """Check if user is admin"""
        return self.role == 'admin'
    
    def is_hr(self):
        """Check if user is HR"""
        return self.role in ['admin', 'hr']
    
    def __repr__(self):
        return f'<User {self.username}>'


class Employee(db.Model):
    """Employee model"""
    __tablename__ = 'employees'
    
    id = Column(Integer, primary_key=True)
    employee_id = Column(String(20), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    role = Column(String(100), nullable=False)
    department = Column(String(100), nullable=False)
    hire_date = Column(DateTime, nullable=False)
    manager_id = Column(String(20), nullable=True)
    status = Column(String(20), default='active')  # active, inactive, terminated
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign key to user
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    user = relationship("User", back_populates="employee")
    
    # Relationships
    leave_balances = relationship("LeaveBalance", back_populates="employee", cascade="all, delete-orphan")
    assets = relationship("Asset", back_populates="employee")
    leave_requests = relationship("LeaveRequest", back_populates="employee")
    
    def __repr__(self):
        return f'<Employee {self.employee_id}: {self.name}>'
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'department': self.department,
            'hire_date': self.hire_date.isoformat() if self.hire_date else None,
            'manager_id': self.manager_id,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class LeaveBalance(db.Model):
    """Leave balance model"""
    __tablename__ = 'leave_balances'
    
    id = Column(Integer, primary_key=True)
    employee_id = Column(String(20), ForeignKey('employees.employee_id'), nullable=False)
    year = Column(Integer, nullable=False)
    annual_leave = Column(Float, default=20.0)
    sick_leave = Column(Float, default=10.0)
    personal_leave = Column(Float, default=5.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    employee = relationship("Employee", back_populates="leave_balances")
    
    # Unique constraint
    __table_args__ = (db.UniqueConstraint('employee_id', 'year', name='unique_employee_year'),)
    
    def __repr__(self):
        return f'<LeaveBalance {self.employee_id} {self.year}>'
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'year': self.year,
            'annual_leave': self.annual_leave,
            'sick_leave': self.sick_leave,
            'personal_leave': self.personal_leave,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Asset(db.Model):
    """Asset model"""
    __tablename__ = 'assets'
    
    id = Column(Integer, primary_key=True)
    asset_id = Column(String(50), unique=True, nullable=False)
    asset_type = Column(String(50), nullable=False)  # laptop, monitor, phone, etc.
    brand = Column(String(50), nullable=True)
    model = Column(String(100), nullable=True)
    serial_number = Column(String(100), nullable=True)
    status = Column(String(20), default='available')  # available, assigned, maintenance, retired
    assigned_to = Column(String(20), ForeignKey('employees.employee_id'), nullable=True)
    assigned_date = Column(DateTime, nullable=True)
    purchase_date = Column(DateTime, nullable=True)
    warranty_expiry = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    employee = relationship("Employee", back_populates="assets")
    
    def __repr__(self):
        return f'<Asset {self.asset_id}: {self.asset_type}>'
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'asset_id': self.asset_id,
            'asset_type': self.asset_type,
            'brand': self.brand,
            'model': self.model,
            'serial_number': self.serial_number,
            'status': self.status,
            'assigned_to': self.assigned_to,
            'assigned_date': self.assigned_date.isoformat() if self.assigned_date else None,
            'purchase_date': self.purchase_date.isoformat() if self.purchase_date else None,
            'warranty_expiry': self.warranty_expiry.isoformat() if self.warranty_expiry else None,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class LeaveRequest(db.Model):
    """Leave request model for tracking leave applications"""
    __tablename__ = 'leave_requests'
    
    id = Column(Integer, primary_key=True)
    employee_id = Column(String(20), ForeignKey('employees.employee_id'), nullable=False)
    leave_type = Column(String(20), nullable=False)  # annual_leave, sick_leave, personal_leave
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    days_requested = Column(Float, nullable=False)
    reason = Column(Text, nullable=True)
    status = Column(String(20), default='pending')  # pending, approved, rejected, cancelled
    approved_by = Column(String(20), nullable=True)
    approved_date = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    employee = relationship("Employee", back_populates="leave_requests")
    
    def __repr__(self):
        return f'<LeaveRequest {self.employee_id}: {self.leave_type} {self.status}>'
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'leave_type': self.leave_type,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'days_requested': self.days_requested,
            'reason': self.reason,
            'status': self.status,
            'approved_by': self.approved_by,
            'approved_date': self.approved_date.isoformat() if self.approved_date else None,
            'rejection_reason': self.rejection_reason,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class AuditLog(db.Model):
    """Audit log for tracking changes"""
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    action = Column(String(100), nullable=False)  # create, update, delete, login, etc.
    table_name = Column(String(50), nullable=False)
    record_id = Column(String(50), nullable=True)
    old_values = Column(Text, nullable=True)  # JSON string of old values
    new_values = Column(Text, nullable=True)  # JSON string of new values
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<AuditLog {self.action} on {self.table_name}>'


# Configuration class for different environments
class DatabaseConfig:
    """Database configuration"""
    
    @staticmethod
    def get_database_uri(environment='development'):
        """Get database URI for different environments"""
        if environment == 'production':
            # Production database configuration
            return 'postgresql://username:password@localhost/hr_assistant_prod'
        elif environment == 'testing':
            # Testing database configuration
            return 'postgresql://username:password@localhost/hr_assistant_test'
        else:
            # Development database configuration
            return 'postgresql://username:password@localhost/hr_assistant_dev'
    
    @staticmethod
    def init_app(app, environment='development'):
        """Initialize database configuration for Flask app"""
        app.config['SQLALCHEMY_DATABASE_URI'] = DatabaseConfig.get_database_uri(environment)
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['SQLALCHEMY_ECHO'] = environment == 'development'  # Log SQL in development
        
        db.init_app(app)
        
        return db
