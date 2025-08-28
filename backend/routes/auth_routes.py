"""
Authentication routes for HR Assistant
Login, logout, and user management endpoints
"""
from flask import Blueprint, request, jsonify, session, redirect, url_for, render_template
from flask_login import login_user, logout_user, current_user, login_required
import logging
from datetime import datetime

from backend.utils.auth import auth_manager, AuthenticatedUser, validate_password_strength
from backend.utils.database_manager import DatabaseManager
from backend.models.database import User, Employee, db

logger = logging.getLogger(__name__)

# Create authentication blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login endpoint"""
    if request.method == 'GET':
        # Return login page for web interface
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        return render_template('login.html')
    
    try:
        data = request.get_json() if request.is_json else request.form
        username = data.get('username', '').strip()
        password = data.get('password', '')
        remember_me = data.get('remember_me', False)
        
        if not username or not password:
            return jsonify({
                'success': False,
                'message': 'Username and password are required'
            }), 400
        
        # Authenticate user
        user = auth_manager.authenticate_user(username, password)
        
        if user:
            # Log in user with Flask-Login
            login_user(user, remember=remember_me)
            
            # Create JWT token for API access
            access_token = auth_manager.create_access_token(user)
            
            # Log successful login
            logger.info(f"User {username} logged in successfully")
            
            response_data = {
                'success': True,
                'message': 'Login successful',
                'user': user.to_dict(),
                'access_token': access_token
            }
            
            # Handle redirect for web interface
            if not request.is_json:
                next_page = request.args.get('next')
                if user.is_admin():
                    return redirect(next_page or url_for('admin_dashboard'))
                elif user.is_hr():
                    return redirect(next_page or url_for('admin_dashboard'))
                else:
                    return redirect(next_page or url_for('employee_portal'))
            
            return jsonify(response_data)
        
        else:
            logger.warning(f"Failed login attempt for username: {username}")
            return jsonify({
                'success': False,
                'message': 'Invalid username or password'
            }), 401
    
    except Exception as e:
        logger.error(f"Error during login: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred during login'
        }), 500


@auth_bp.route('/logout', methods=['POST', 'GET'])
@login_required
def logout():
    """User logout endpoint"""
    try:
        username = current_user.username
        logout_user()
        
        logger.info(f"User {username} logged out")
        
        if request.is_json:
            return jsonify({
                'success': True,
                'message': 'Logout successful'
            })
        else:
            return redirect(url_for('auth.login'))
    
    except Exception as e:
        logger.error(f"Error during logout: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred during logout'
        }), 500


@auth_bp.route('/register', methods=['POST'])
def register():
    """User registration endpoint (admin only)"""
    try:
        # Check if user is admin (for API calls with JWT)
        auth_header = request.headers.get('Authorization')
        if auth_header:
            token = auth_header.split(' ')[1] if ' ' in auth_header else None
            if token:
                payload = auth_manager.verify_access_token(token)
                if not payload or payload.get('role') != 'admin':
                    return jsonify({'error': 'Admin access required'}), 403
        elif not (current_user.is_authenticated and current_user.is_admin()):
            return jsonify({'error': 'Admin access required'}), 403
        
        data = request.get_json()
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        role = data.get('role', 'employee')
        employee_id = data.get('employee_id', '').strip()
        
        # Validate required fields
        if not all([username, email, password]):
            return jsonify({
                'success': False,
                'message': 'Username, email, and password are required'
            }), 400
        
        # Validate password strength
        is_valid, password_message = validate_password_strength(password)
        if not is_valid:
            return jsonify({
                'success': False,
                'message': password_message
            }), 400
        
        # Validate role
        valid_roles = ['admin', 'hr', 'manager', 'employee']
        if role not in valid_roles:
            return jsonify({
                'success': False,
                'message': f'Role must be one of: {", ".join(valid_roles)}'
            }), 400
        
        # Check if username or email already exists
        existing_user = db.session.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing_user:
            return jsonify({
                'success': False,
                'message': 'Username or email already exists'
            }), 409
        
        # Create new user
        db_manager = DatabaseManager()
        user_data = {
            'username': username,
            'email': email,
            'password': password,
            'role': role
        }
        
        new_user = db_manager.create_user(user_data)
        
        if new_user:
            # Link to employee if employee_id provided
            if employee_id:
                employee = db_manager.get_employee(employee_id)
                if employee:
                    employee.user_id = new_user.id
                    db.session.commit()
            
            logger.info(f"Created new user: {username} with role: {role}")
            
            return jsonify({
                'success': True,
                'message': 'User created successfully',
                'user': {
                    'id': new_user.id,
                    'username': new_user.username,
                    'email': new_user.email,
                    'role': new_user.role
                }
            }), 201
        
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to create user'
            }), 500
    
    except Exception as e:
        logger.error(f"Error during user registration: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred during registration'
        }), 500


@auth_bp.route('/profile', methods=['GET'])
@login_required
def get_profile():
    """Get current user profile"""
    try:
        user_data = current_user.to_dict()
        
        # Add employee information if linked
        if current_user.user_model.employee:
            user_data['employee'] = current_user.user_model.employee.to_dict()
        
        return jsonify({
            'success': True,
            'user': user_data
        })
    
    except Exception as e:
        logger.error(f"Error getting user profile: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error retrieving profile'
        }), 500


@auth_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """Change user password"""
    try:
        data = request.get_json()
        current_password = data.get('current_password', '')
        new_password = data.get('new_password', '')
        
        if not current_password or not new_password:
            return jsonify({
                'success': False,
                'message': 'Current password and new password are required'
            }), 400
        
        # Verify current password
        if not current_user.user_model.check_password(current_password):
            return jsonify({
                'success': False,
                'message': 'Current password is incorrect'
            }), 400
        
        # Validate new password strength
        is_valid, password_message = validate_password_strength(new_password)
        if not is_valid:
            return jsonify({
                'success': False,
                'message': password_message
            }), 400
        
        # Update password
        current_user.user_model.set_password(new_password)
        db.session.commit()
        
        logger.info(f"User {current_user.username} changed password")
        
        return jsonify({
            'success': True,
            'message': 'Password changed successfully'
        })
    
    except Exception as e:
        logger.error(f"Error changing password: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error changing password'
        }), 500


@auth_bp.route('/users', methods=['GET'])
@login_required
def list_users():
    """List all users (admin/HR only)"""
    try:
        if not current_user.is_hr():
            return jsonify({'error': 'HR access required'}), 403
        
        users = db.session.query(User).all()
        users_data = []
        
        for user in users:
            user_dict = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'is_active': user.is_active,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'last_login': user.last_login.isoformat() if user.last_login else None
            }
            
            # Add employee info if linked
            if user.employee:
                user_dict['employee'] = {
                    'employee_id': user.employee.employee_id,
                    'name': user.employee.name,
                    'department': user.employee.department
                }
            
            users_data.append(user_dict)
        
        return jsonify({
            'success': True,
            'users': users_data
        })
    
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error retrieving users'
        }), 500


@auth_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
def toggle_user_status(user_id):
    """Toggle user active status (admin only)"""
    try:
        if not current_user.is_admin():
            return jsonify({'error': 'Admin access required'}), 403
        
        user = db.session.query(User).get(user_id)
        if not user:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404
        
        # Don't allow deactivating the last admin
        if user.role == 'admin' and user.is_active:
            admin_count = db.session.query(User).filter(
                User.role == 'admin', User.is_active == True
            ).count()
            if admin_count <= 1:
                return jsonify({
                    'success': False,
                    'message': 'Cannot deactivate the last admin user'
                }), 400
        
        user.is_active = not user.is_active
        db.session.commit()
        
        status = 'activated' if user.is_active else 'deactivated'
        logger.info(f"User {user.username} {status} by {current_user.username}")
        
        return jsonify({
            'success': True,
            'message': f'User {status} successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'is_active': user.is_active
            }
        })
    
    except Exception as e:
        logger.error(f"Error toggling user status: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error updating user status'
        }), 500


@auth_bp.route('/verify-token', methods=['POST'])
def verify_token():
    """Verify JWT token validity"""
    try:
        data = request.get_json()
        token = data.get('token', '')
        
        if not token:
            return jsonify({
                'valid': False,
                'message': 'Token is required'
            }), 400
        
        payload = auth_manager.verify_access_token(token)
        
        if payload:
            return jsonify({
                'valid': True,
                'user': {
                    'user_id': payload['user_id'],
                    'username': payload['username'],
                    'role': payload['role']
                }
            })
        else:
            return jsonify({
                'valid': False,
                'message': 'Invalid or expired token'
            }), 401
    
    except Exception as e:
        logger.error(f"Error verifying token: {str(e)}")
        return jsonify({
            'valid': False,
            'message': 'Error verifying token'
        }), 500
