"""
Authentication utilities for HR Assistant
Flask-Login integration with role-based access control
"""
from functools import wraps
from flask import request, jsonify, session, current_app
from flask_login import LoginManager, UserMixin, current_user
import jwt
from datetime import datetime, timedelta
import logging

from backend.models.database import User, db

logger = logging.getLogger(__name__)

# Initialize Flask-Login
login_manager = LoginManager()


class AuthenticatedUser(UserMixin):
    """User class for Flask-Login integration"""
    
    def __init__(self, user_model):
        self.user_model = user_model
        self.id = str(user_model.id)
        self.username = user_model.username
        self.email = user_model.email
        self.role = user_model.role
        self.is_active_user = user_model.is_active
    
    def get_id(self):
        """Return user ID for Flask-Login"""
        return self.id
    
    def is_active(self):
        """Check if user account is active"""
        return self.is_active_user
    
    def has_role(self, role):
        """Check if user has specific role"""
        return self.role == role
    
    def is_admin(self):
        """Check if user is admin"""
        return self.role == 'admin'
    
    def is_hr(self):
        """Check if user is HR or admin"""
        return self.role in ['admin', 'hr']
    
    def is_manager(self):
        """Check if user is manager, HR, or admin"""
        return self.role in ['admin', 'hr', 'manager']
    
    def can_access_employee_data(self, employee_id=None):
        """Check if user can access employee data"""
        if self.is_hr():
            return True
        
        # Employees can only access their own data
        if self.user_model.employee and employee_id:
            return self.user_model.employee.employee_id == employee_id
        
        return False
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'is_active': self.is_active_user
        }


@login_manager.user_loader
def load_user(user_id):
    """Load user for Flask-Login"""
    try:
        user_model = db.session.query(User).get(int(user_id))
        if user_model:
            return AuthenticatedUser(user_model)
        return None
    except Exception as e:
        logger.error(f"Error loading user {user_id}: {str(e)}")
        return None


class AuthManager:
    """Handles authentication operations"""
    
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize authentication with Flask app"""
        login_manager.init_app(app)
        login_manager.login_view = 'auth.login'
        login_manager.login_message = 'Please log in to access this page.'
        login_manager.login_message_category = 'info'
        
        # Set secret key for JWT tokens
        app.config.setdefault('JWT_SECRET_KEY', app.config.get('SECRET_KEY', 'dev-secret-key'))
        app.config.setdefault('JWT_ACCESS_TOKEN_EXPIRES', timedelta(hours=1))
    
    def authenticate_user(self, username, password):
        """
        Authenticate user with username and password
        
        Args:
            username: Username
            password: Password
            
        Returns:
            AuthenticatedUser instance if successful, None otherwise
        """
        try:
            user_model = db.session.query(User).filter(User.username == username).first()
            
            if user_model and user_model.check_password(password) and user_model.is_active:
                # Update last login
                user_model.last_login = datetime.utcnow()
                db.session.commit()
                
                logger.info(f"User {username} authenticated successfully")
                return AuthenticatedUser(user_model)
            
            logger.warning(f"Authentication failed for user {username}")
            return None
            
        except Exception as e:
            logger.error(f"Error authenticating user {username}: {str(e)}")
            return None
    
    def create_access_token(self, user):
        """
        Create JWT access token for user
        
        Args:
            user: AuthenticatedUser instance
            
        Returns:
            JWT token string
        """
        try:
            payload = {
                'user_id': user.id,
                'username': user.username,
                'role': user.role,
                'exp': datetime.utcnow() + current_app.config['JWT_ACCESS_TOKEN_EXPIRES'],
                'iat': datetime.utcnow()
            }
            
            token = jwt.encode(
                payload,
                current_app.config['JWT_SECRET_KEY'],
                algorithm='HS256'
            )
            
            return token
            
        except Exception as e:
            logger.error(f"Error creating access token for user {user.username}: {str(e)}")
            return None
    
    def verify_access_token(self, token):
        """
        Verify JWT access token
        
        Args:
            token: JWT token string
            
        Returns:
            User data dict if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                current_app.config['JWT_SECRET_KEY'],
                algorithms=['HS256']
            )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Access token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid access token: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error verifying access token: {str(e)}")
            return None


# Initialize auth manager
auth_manager = AuthManager()


# Decorators for role-based access control
def login_required(f):
    """Decorator to require user login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


def role_required(*roles):
    """Decorator to require specific roles"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({'error': 'Authentication required'}), 401
            
            if current_user.role not in roles:
                return jsonify({'error': 'Insufficient permissions'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
        
        if not current_user.is_admin():
            return jsonify({'error': 'Admin access required'}), 403
        
        return f(*args, **kwargs)
    return decorated_function


def hr_required(f):
    """Decorator to require HR or admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
        
        if not current_user.is_hr():
            return jsonify({'error': 'HR access required'}), 403
        
        return f(*args, **kwargs)
    return decorated_function


def manager_required(f):
    """Decorator to require manager, HR, or admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
        
        if not current_user.is_manager():
            return jsonify({'error': 'Manager access required'}), 403
        
        return f(*args, **kwargs)
    return decorated_function


def employee_data_access_required(f):
    """Decorator to check employee data access permissions"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Get employee_id from URL parameters or request data
        employee_id = kwargs.get('employee_id') or request.json.get('employee_id') if request.json else None
        
        if not current_user.can_access_employee_data(employee_id):
            return jsonify({'error': 'Access denied to employee data'}), 403
        
        return f(*args, **kwargs)
    return decorated_function


def jwt_token_required(f):
    """Decorator to require valid JWT token (for API endpoints)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        
        # Check for token in Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header:
            try:
                token = auth_header.split(' ')[1]  # Bearer <token>
            except IndexError:
                return jsonify({'error': 'Invalid authorization header format'}), 401
        
        if not token:
            return jsonify({'error': 'Access token required'}), 401
        
        # Verify token
        payload = auth_manager.verify_access_token(token)
        if not payload:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        # Add user info to request context
        request.current_user_data = payload
        
        return f(*args, **kwargs)
    return decorated_function


def create_default_admin_user():
    """Create default admin user if none exists"""
    try:
        admin_exists = db.session.query(User).filter(User.role == 'admin').first()
        
        if not admin_exists:
            admin_user = User(
                username='admin',
                email='admin@company.com',
                role='admin'
            )
            admin_user.set_password('admin123')  # Change this in production!
            
            db.session.add(admin_user)
            db.session.commit()
            
            logger.info("Created default admin user (username: admin, password: admin123)")
            logger.warning("Please change the default admin password in production!")
            
    except Exception as e:
        logger.error(f"Error creating default admin user: {str(e)}")
        db.session.rollback()


# Password validation utilities
def validate_password_strength(password):
    """
    Validate password strength
    
    Args:
        password: Password string
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"
    
    return True, "Password is valid"
