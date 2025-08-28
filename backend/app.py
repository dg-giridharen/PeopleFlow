"""
Flask application for AI-Powered HR Assistant
Provides webhook endpoints for Dialogflow integration
"""
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import os
import sys
import logging
import re
from datetime import datetime, timedelta
from collections import defaultdict

# Add the parent directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.utils.data_manager import DataManager
from backend.workflows.leave_approval import LeaveApprovalWorkflow
from backend.workflows.asset_issuance import AssetIssuanceWorkflow
from backend.workflows.policy_query import PolicyQueryWorkflow
from backend.routes.auth_routes import auth_bp

# Initialize Flask app
app = Flask(__name__, static_folder='../frontend/static', template_folder='../frontend/templates')
CORS(app, origins=["http://localhost:5001", "http://127.0.0.1:5001", "http://localhost:5000", "http://127.0.0.1:5000"])
socketio = SocketIO(app, cors_allowed_origins="*")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize data manager and workflows
data_manager = DataManager()
leave_workflow = LeaveApprovalWorkflow(data_manager)
asset_workflow = AssetIssuanceWorkflow(data_manager)

# Initialize policy workflow with PDF RAG support
# Get credentials from environment variables
astra_db_token = os.getenv('ASTRA_DB_TOKEN')
astra_db_id = os.getenv('ASTRA_DB_ID')
astra_db_endpoint = os.getenv('ASTRA_DB_API_ENDPOINT')
openai_api_key = os.getenv('OPENAI_API_KEY')

policy_workflow = PolicyQueryWorkflow(
    astra_db_token=astra_db_token,
    astra_db_id=astra_db_id,
    astra_db_endpoint=astra_db_endpoint,
    openai_api_key=openai_api_key
)

# Register blueprints
app.register_blueprint(auth_bp)


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "AI-Powered HR Assistant",
        "timestamp": datetime.now().isoformat()
    })


@app.route('/webhook', methods=['POST'])
def dialogflow_webhook():
    """Main webhook endpoint for Dialogflow"""
    try:
        req = request.get_json()
        
        # Extract intent information
        intent_name = req.get('queryResult', {}).get('intent', {}).get('displayName', '')
        parameters = req.get('queryResult', {}).get('parameters', {})
        query_text = req.get('queryResult', {}).get('queryText', '')
        
        logger.info(f"Received intent: {intent_name}")
        logger.info(f"Parameters: {parameters}")
        
        # Route to appropriate workflow
        if intent_name == 'leave.request':
            response = handle_leave_request(parameters)
        elif intent_name == 'asset.provision':
            response = handle_asset_provision(parameters)
        elif intent_name == 'employee.info':
            response = handle_employee_info(parameters)
        elif intent_name == 'leave.balance':
            response = handle_leave_balance_inquiry(parameters)
        elif intent_name == 'policy.query':
            response = handle_policy_query(parameters, query_text)
        else:
            response = {
                "fulfillmentText": "I'm sorry, I didn't understand that request. I can help you with leave requests, asset provisioning, employee information, and company policy questions."
            }
        
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return jsonify({
            "fulfillmentText": "I'm sorry, there was an error processing your request. Please try again."
        }), 500


def handle_leave_request(parameters):
    """Handle leave request workflow"""
    try:
        employee_id = parameters.get('employee-id', '')
        start_date = parameters.get('start-date', '')
        end_date = parameters.get('end-date', '')
        leave_type = parameters.get('leave-type', 'annual_leave')
        
        # Validate required parameters
        if not all([employee_id, start_date, end_date]):
            return {
                "fulfillmentText": "I need your employee ID, start date, and end date to process your leave request. Please provide all the required information."
            }
        
        # Process leave request
        result = leave_workflow.process_leave_request(
            employee_id=employee_id,
            start_date=start_date,
            end_date=end_date,
            leave_type=leave_type
        )
        
        return {"fulfillmentText": result["message"]}
    
    except Exception as e:
        logger.error(f"Error in leave request: {str(e)}")
        return {
            "fulfillmentText": "There was an error processing your leave request. Please try again."
        }


def handle_asset_provision(parameters):
    """Handle asset provisioning workflow"""
    try:
        employee_id = parameters.get('employee-id', '')
        
        if not employee_id:
            return {
                "fulfillmentText": "I need the employee ID to provision assets. Please provide the employee ID."
            }
        
        # Process asset provisioning
        result = asset_workflow.provision_assets_for_new_hire(employee_id)
        
        return {"fulfillmentText": result["message"]}
    
    except Exception as e:
        logger.error(f"Error in asset provisioning: {str(e)}")
        return {
            "fulfillmentText": "There was an error provisioning assets. Please try again."
        }


def handle_employee_info(parameters):
    """Handle employee information inquiry"""
    try:
        employee_id = parameters.get('employee-id', '')
        
        if not employee_id:
            return {
                "fulfillmentText": "Please provide an employee ID to look up information."
            }
        
        employee = data_manager.get_employee(employee_id)
        if not employee:
            return {
                "fulfillmentText": f"Employee with ID {employee_id} not found."
            }
        
        message = f"Employee Information:\n"
        message += f"Name: {employee['name']}\n"
        message += f"Role: {employee['role']}\n"
        message += f"Department: {employee['department']}\n"
        message += f"Hire Date: {employee['hire_date']}\n"
        message += f"Status: {employee['status']}"
        
        return {"fulfillmentText": message}
    
    except Exception as e:
        logger.error(f"Error getting employee info: {str(e)}")
        return {
            "fulfillmentText": "There was an error retrieving employee information."
        }


def handle_leave_balance_inquiry(parameters):
    """Handle leave balance inquiry"""
    try:
        employee_id = parameters.get('employee-id', '')

        if not employee_id:
            return {
                "fulfillmentText": "Please provide your employee ID to check leave balance."
            }

        balance = data_manager.get_leave_balance(employee_id)
        if not balance:
            return {
                "fulfillmentText": f"Leave balance not found for employee {employee_id}."
            }

        message = f"Leave Balance for {employee_id}:\n"
        message += f"Annual Leave: {balance['annual_leave']} days\n"
        message += f"Sick Leave: {balance['sick_leave']} days\n"
        message += f"Personal Leave: {balance['personal_leave']} days"

        return {"fulfillmentText": message}

    except Exception as e:
        logger.error(f"Error getting leave balance: {str(e)}")
        return {
            "fulfillmentText": "There was an error retrieving leave balance information."
        }


def handle_policy_query(parameters, query_text):
    """Handle policy-related queries using RAG"""
    try:
        employee_id = parameters.get('employee-id', '')

        if not query_text:
            return {
                "fulfillmentText": "Please ask a specific question about company policies. I can help you with information about work from home, expenses, code of conduct, and other policies."
            }

        # Process the query using enhanced PDF RAG if available
        if hasattr(policy_workflow, 'pdf_rag_available') and policy_workflow.pdf_rag_available:
            result = policy_workflow.process_policy_query_with_pdf(query_text, employee_id)
        else:
            result = policy_workflow.process_policy_query(query_text, employee_id)

        if result["success"]:
            # Format response with sources if available
            message = result["message"]
            if result.get("sources"):
                message += "\n\nSources: "
                source_names = [source["filename"] for source in result["sources"]]
                message += ", ".join(source_names)

            return {"fulfillmentText": message}
        else:
            return {"fulfillmentText": result["message"]}

    except Exception as e:
        logger.error(f"Error processing policy query: {str(e)}")
        return {
            "fulfillmentText": "I'm sorry, there was an error processing your policy question. Please try again or contact HR directly."
        }


# Frontend routes
@app.route('/')
def index():
    """Serve the main dashboard"""
    return render_template('index.html')

@app.route('/employee')
def employee_portal():
    """Serve the employee portal"""
    return render_template('employee.html')

@app.route('/admin')
def admin_dashboard():
    """Serve the admin dashboard"""
    return render_template('admin.html')

# API endpoints for direct testing
@app.route('/api/employees', methods=['GET'])
def get_employees():
    """Get all employees"""
    employees = data_manager.get_all_employees()
    return jsonify({"employees": employees})

@app.route('/api/employees/<employee_id>', methods=['GET'])
def get_employee(employee_id):
    """Get specific employee"""
    employee = data_manager.get_employee(employee_id)
    if employee:
        return jsonify(employee)
    return jsonify({"error": "Employee not found"}), 404

@app.route('/api/employees', methods=['POST'])
def create_employee():
    """Create new employee"""
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['employee_id', 'name', 'email', 'role', 'department']
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # Validate employee ID format
        import re
        if not re.match(r'^EMP\d{3}$', data['employee_id']):
            return jsonify({"error": "Employee ID must be in format EMP001"}), 400

        # Validate email format
        email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        if not re.match(email_regex, data['email']):
            return jsonify({"error": "Invalid email format"}), 400

        # Set default values
        employee_data = {
            "employee_id": data['employee_id'],
            "name": data['name'],
            "email": data['email'],
            "role": data['role'],
            "department": data['department'],
            "hire_date": data.get('hire_date', datetime.now().strftime('%Y-%m-%d')),
            "manager_id": data.get('manager_id'),
            "status": data.get('status', 'active')
        }

        # Add employee
        success = data_manager.add_employee(employee_data)
        if success:
            # Create initial leave balance
            leave_balance = {
                "employee_id": data['employee_id'],
                "annual_leave": 20,
                "sick_leave": 10,
                "personal_leave": 5,
                "year": datetime.now().year
            }

            # Add to leave balances
            leave_data = data_manager._load_json(data_manager.leave_balances_file)
            if "leave_balances" not in leave_data:
                leave_data["leave_balances"] = []
            leave_data["leave_balances"].append(leave_balance)
            data_manager._save_json(data_manager.leave_balances_file, leave_data)

            # Emit real-time update
            socketio.emit('employee_created', {
                'employee_id': data['employee_id'],
                'name': data['name']
            })

            return jsonify({"success": True, "message": "Employee created successfully", "employee": employee_data}), 201
        else:
            return jsonify({"error": "Employee ID already exists"}), 409

    except Exception as e:
        logger.error(f"Error creating employee: {str(e)}")
        return jsonify({"error": "Failed to create employee"}), 500

@app.route('/api/employees/<employee_id>', methods=['PUT'])
def update_employee(employee_id):
    """Update existing employee"""
    try:
        data = request.get_json()

        # Get existing employee
        employee = data_manager.get_employee(employee_id)
        if not employee:
            return jsonify({"error": "Employee not found"}), 404

        # Update fields
        updatable_fields = ['name', 'email', 'role', 'department', 'manager_id', 'status']
        for field in updatable_fields:
            if field in data:
                if field == 'email':
                    # Validate email format
                    email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
                    if not re.match(email_regex, data[field]):
                        return jsonify({"error": "Invalid email format"}), 400
                employee[field] = data[field]

        # Save updated employee data
        employees_data = data_manager._load_json(data_manager.employees_file)
        for i, emp in enumerate(employees_data.get("employees", [])):
            if emp["employee_id"] == employee_id:
                employees_data["employees"][i] = employee
                break

        data_manager._save_json(data_manager.employees_file, employees_data)

        # Emit real-time update
        socketio.emit('employee_updated', {
            'employee_id': employee_id,
            'name': employee['name']
        })

        return jsonify({"success": True, "message": "Employee updated successfully", "employee": employee})

    except Exception as e:
        logger.error(f"Error updating employee: {str(e)}")
        return jsonify({"error": "Failed to update employee"}), 500

@app.route('/api/employees/<employee_id>', methods=['DELETE'])
def delete_employee(employee_id):
    """Delete employee (soft delete by setting status to inactive)"""
    try:
        # Get existing employee
        employee = data_manager.get_employee(employee_id)
        if not employee:
            return jsonify({"error": "Employee not found"}), 404

        # Soft delete by setting status to inactive
        employee['status'] = 'inactive'

        # Save updated employee data
        employees_data = data_manager._load_json(data_manager.employees_file)
        for i, emp in enumerate(employees_data.get("employees", [])):
            if emp["employee_id"] == employee_id:
                employees_data["employees"][i] = employee
                break

        data_manager._save_json(data_manager.employees_file, employees_data)

        # Emit real-time update
        socketio.emit('employee_deleted', {
            'employee_id': employee_id,
            'name': employee['name']
        })

        return jsonify({"success": True, "message": "Employee deactivated successfully"})

    except Exception as e:
        logger.error(f"Error deleting employee: {str(e)}")
        return jsonify({"error": "Failed to delete employee"}), 500

@app.route('/api/employees/<employee_id>/leave-balance', methods=['GET'])
def get_employee_leave_balance(employee_id):
    """Get leave balance for specific employee"""
    balance = data_manager.get_leave_balance(employee_id)
    if balance:
        return jsonify(balance)
    return jsonify({"error": "Leave balance not found"}), 404

@app.route('/api/employees/<employee_id>/assets', methods=['GET'])
def get_employee_assets(employee_id):
    """Get assets assigned to specific employee"""
    assets = data_manager.get_employee_assets(employee_id)
    return jsonify({"assets": assets})

@app.route('/api/leave-balances', methods=['GET'])
def get_leave_balances():
    """Get all leave balances"""
    balances = data_manager.get_all_leave_balances()
    return jsonify({"leave_balances": balances})

@app.route('/api/assets', methods=['GET'])
def get_assets():
    """Get all assets"""
    assets = data_manager.get_all_assets()
    return jsonify({"assets": assets})

# Dashboard analytics endpoints
@app.route('/api/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    """Get dashboard statistics"""
    try:
        employees = data_manager.get_all_employees()
        leave_balances = data_manager.get_all_leave_balances()
        assets = data_manager.get_all_assets()

        # Calculate statistics
        total_employees = len(employees)
        active_employees = len([e for e in employees if e.get('status') == 'active'])

        # Leave statistics
        total_annual_leave = sum(b.get('annual_leave', 0) for b in leave_balances)
        total_sick_leave = sum(b.get('sick_leave', 0) for b in leave_balances)

        # Asset statistics
        total_assets = len(assets)
        available_assets = len([a for a in assets if a.get('status') == 'available'])
        assigned_assets = len([a for a in assets if a.get('status') == 'assigned'])

        # Department breakdown
        dept_breakdown = defaultdict(int)
        for emp in employees:
            dept_breakdown[emp.get('department', 'Unknown')] += 1

        # Asset type breakdown
        asset_type_breakdown = defaultdict(int)
        for asset in assets:
            asset_type_breakdown[asset.get('asset_type', 'Unknown')] += 1

        return jsonify({
            "employees": {
                "total": total_employees,
                "active": active_employees,
                "by_department": dict(dept_breakdown)
            },
            "leave": {
                "total_annual_days": total_annual_leave,
                "total_sick_days": total_sick_leave,
                "average_annual_per_employee": round(total_annual_leave / max(total_employees, 1), 1)
            },
            "assets": {
                "total": total_assets,
                "available": available_assets,
                "assigned": assigned_assets,
                "utilization_rate": round((assigned_assets / max(total_assets, 1)) * 100, 1),
                "by_type": dict(asset_type_breakdown)
            }
        })
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {str(e)}")
        return jsonify({"error": "Failed to get dashboard statistics"}), 500

@app.route('/api/leave-requests', methods=['POST'])
def submit_leave_request():
    """Submit a leave request via API"""
    try:
        data = request.get_json()
        employee_id = data.get('employee_id')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        leave_type = data.get('leave_type', 'annual')

        result = leave_workflow.process_leave_request(
            employee_id=employee_id,
            start_date=start_date,
            end_date=end_date,
            leave_type=leave_type
        )

        # Emit real-time update
        socketio.emit('leave_request_update', {
            'employee_id': employee_id,
            'status': 'approved' if result['success'] else 'rejected',
            'message': result['message']
        })

        return jsonify(result)
    except Exception as e:
        logger.error(f"Error submitting leave request: {str(e)}")
        return jsonify({"success": False, "message": "Failed to submit leave request"}), 500

@app.route('/api/assets/provision', methods=['POST'])
def provision_assets():
    """Provision assets for employee via API"""
    try:
        data = request.get_json()
        employee_id = data.get('employee_id')

        result = asset_workflow.provision_assets_for_new_hire(employee_id)

        # Emit real-time update
        socketio.emit('asset_provision_update', {
            'employee_id': employee_id,
            'status': 'success' if result['success'] else 'failed',
            'message': result['message']
        })

        return jsonify(result)
    except Exception as e:
        logger.error(f"Error provisioning assets: {str(e)}")
        return jsonify({"success": False, "message": "Failed to provision assets"}), 500

# WebSocket events
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info('Client connected')
    emit('status', {'msg': 'Connected to HR Assistant'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info('Client disconnected')

@socketio.on('chat_message')
def handle_chat_message(data):
    """Handle chat messages from frontend"""
    try:
        message = data.get('message', '')
        employee_id = data.get('employee_id', '')

        # Process message through webhook logic
        # This simulates Dialogflow processing
        webhook_payload = {
            "queryResult": {
                "queryText": message,
                "parameters": {"employee-id": employee_id}
            }
        }

        # Simple intent detection for demo
        if 'leave' in message.lower() and 'balance' in message.lower():
            webhook_payload["queryResult"]["intent"] = {"displayName": "leave.balance"}
        elif 'leave' in message.lower() and ('request' in message.lower() or 'apply' in message.lower()):
            webhook_payload["queryResult"]["intent"] = {"displayName": "leave.request"}
        elif 'asset' in message.lower() or 'equipment' in message.lower():
            webhook_payload["queryResult"]["intent"] = {"displayName": "asset.provision"}
        elif any(keyword in message.lower() for keyword in ['policy', 'work from home', 'remote work', 'expense', 'reimbursement', 'conduct', 'code of conduct']):
            webhook_payload["queryResult"]["intent"] = {"displayName": "policy.query"}

        # Process through existing webhook logic
        response = process_webhook_message(webhook_payload)

        # Emit response back to client
        emit('chat_response', {
            'message': response.get('fulfillmentText', 'I did not understand that request.'),
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Error handling chat message: {str(e)}")
        emit('chat_response', {
            'message': 'Sorry, there was an error processing your message.',
            'timestamp': datetime.now().isoformat()
        })

def process_webhook_message(req):
    """Process webhook message (extracted from existing webhook logic)"""
    intent_name = req.get('queryResult', {}).get('intent', {}).get('displayName', '')
    parameters = req.get('queryResult', {}).get('parameters', {})
    query_text = req.get('queryResult', {}).get('queryText', '')

    if intent_name == 'leave.balance':
        return handle_leave_balance_inquiry(parameters)
    elif intent_name == 'leave.request':
        return handle_leave_request(parameters)
    elif intent_name == 'asset.provision':
        return handle_asset_provision(parameters)
    elif intent_name == 'policy.query':
        return handle_policy_query(parameters, query_text)
    else:
        return {"fulfillmentText": "I can help you with leave requests, leave balance inquiries, asset provisioning, and company policy questions."}


# PDF RAG API Endpoints
@app.route('/api/policy/upload-pdf', methods=['POST'])
def upload_policy_pdf():
    """Upload a PDF policy document to the RAG system"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400

        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'success': False, 'message': 'Only PDF files are supported'}), 400

        # Save uploaded file temporarily
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            file.save(temp_file.name)

            # Get document name from form or use filename
            document_name = request.form.get('document_name', file.filename)

            # Upload to RAG system
            result = policy_workflow.upload_pdf_document(temp_file.name, document_name)

            # Clean up temp file
            os.unlink(temp_file.name)

            if result['success']:
                return jsonify(result), 200
            else:
                return jsonify(result), 500

    except Exception as e:
        logger.error(f"Error uploading PDF: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error uploading PDF: {str(e)}'
        }), 500

@app.route('/api/policy/query-enhanced', methods=['POST'])
def enhanced_policy_query():
    """Enhanced policy query using PDF RAG system"""
    try:
        data = request.get_json()
        query = data.get('query', '')
        employee_id = data.get('employee_id')

        if not query:
            return jsonify({'success': False, 'message': 'Query is required'}), 400

        # Use enhanced PDF RAG if available
        if hasattr(policy_workflow, 'pdf_rag_available') and policy_workflow.pdf_rag_available:
            result = policy_workflow.process_policy_query_with_pdf(query, employee_id)
        else:
            result = policy_workflow.process_policy_query(query, employee_id)

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Error in enhanced policy query: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error processing query: {str(e)}'
        }), 500

@app.route('/api/policy/rag-status', methods=['GET'])
def rag_system_status():
    """Get the status of the RAG system"""
    try:
        status = {
            'pdf_rag_available': hasattr(policy_workflow, 'pdf_rag_available') and policy_workflow.pdf_rag_available,
            'astra_db_connected': False,
            'documents_indexed': 0,
            'last_update': None
        }

        if status['pdf_rag_available']:
            status['astra_db_connected'] = policy_workflow.astra_vector_store is not None
            # You could add more detailed status checks here

        return jsonify(status), 200

    except Exception as e:
        logger.error(f"Error getting RAG status: {str(e)}")
        return jsonify({
            'pdf_rag_available': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    # Ensure data directory exists
    os.makedirs('data', exist_ok=True)

    # Run the Flask app with SocketIO
    socketio.run(app, debug=True, host='0.0.0.0', port=5001)
