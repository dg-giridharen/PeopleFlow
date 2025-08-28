"""
Employee Onboarding Workflow Implementation
Handles automated onboarding process for new employees
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from enum import Enum

from backend.utils.database_manager import DatabaseManager
from backend.models.database import Employee, Asset, LeaveBalance, db

logger = logging.getLogger(__name__)


class OnboardingTaskStatus(Enum):
    """Onboarding task status enumeration"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


class OnboardingTask:
    """Individual onboarding task"""
    
    def __init__(self, task_id: str, title: str, description: str, 
                 assignee: str, due_days: int = 1, dependencies: List[str] = None):
        self.task_id = task_id
        self.title = title
        self.description = description
        self.assignee = assignee  # hr, it, manager, employee
        self.due_days = due_days  # Days from start date
        self.dependencies = dependencies or []
        self.status = OnboardingTaskStatus.PENDING
        self.assigned_date = None
        self.completed_date = None
        self.notes = ""


class OnboardingWorkflow:
    """Handles the complete employee onboarding process"""
    
    def __init__(self, db_manager: DatabaseManager = None):
        self.db_manager = db_manager or DatabaseManager()
        self.default_tasks = self._get_default_onboarding_tasks()
    
    def _get_default_onboarding_tasks(self) -> List[OnboardingTask]:
        """Get default onboarding tasks"""
        return [
            # HR Tasks
            OnboardingTask(
                "hr_welcome_email",
                "Send Welcome Email",
                "Send welcome email with first day information and company handbook",
                "hr",
                due_days=0
            ),
            OnboardingTask(
                "hr_create_employee_record",
                "Create Employee Record",
                "Create employee record in HR system with all personal information",
                "hr",
                due_days=0
            ),
            OnboardingTask(
                "hr_benefits_enrollment",
                "Benefits Enrollment",
                "Schedule benefits enrollment meeting and provide enrollment forms",
                "hr",
                due_days=3,
                dependencies=["hr_create_employee_record"]
            ),
            OnboardingTask(
                "hr_policy_review",
                "Policy Review Session",
                "Schedule session to review company policies and code of conduct",
                "hr",
                due_days=5
            ),
            
            # IT Tasks
            OnboardingTask(
                "it_create_accounts",
                "Create IT Accounts",
                "Create email account, system logins, and access credentials",
                "it",
                due_days=1,
                dependencies=["hr_create_employee_record"]
            ),
            OnboardingTask(
                "it_provision_equipment",
                "Provision Equipment",
                "Assign and configure laptop, monitor, and other required equipment",
                "it",
                due_days=1,
                dependencies=["hr_create_employee_record"]
            ),
            OnboardingTask(
                "it_security_training",
                "Security Training",
                "Complete mandatory IT security training and sign security agreement",
                "it",
                due_days=7,
                dependencies=["it_create_accounts"]
            ),
            
            # Manager Tasks
            OnboardingTask(
                "manager_workspace_setup",
                "Workspace Setup",
                "Prepare workspace, desk assignment, and office tour",
                "manager",
                due_days=1
            ),
            OnboardingTask(
                "manager_team_introduction",
                "Team Introduction",
                "Introduce new employee to team members and key stakeholders",
                "manager",
                due_days=1
            ),
            OnboardingTask(
                "manager_role_overview",
                "Role Overview Meeting",
                "Discuss role expectations, goals, and initial projects",
                "manager",
                due_days=2
            ),
            OnboardingTask(
                "manager_30day_checkin",
                "30-Day Check-in",
                "Schedule 30-day check-in meeting to review progress and address concerns",
                "manager",
                due_days=30
            ),
            
            # Employee Tasks
            OnboardingTask(
                "employee_handbook_review",
                "Review Employee Handbook",
                "Read and acknowledge receipt of employee handbook",
                "employee",
                due_days=7
            ),
            OnboardingTask(
                "employee_emergency_contacts",
                "Provide Emergency Contacts",
                "Submit emergency contact information and update personal details",
                "employee",
                due_days=3
            ),
            OnboardingTask(
                "employee_direct_deposit",
                "Setup Direct Deposit",
                "Provide banking information for payroll direct deposit",
                "employee",
                due_days=5
            )
        ]
    
    def start_onboarding(self, employee_id: str, start_date: datetime = None) -> Dict[str, Any]:
        """
        Start onboarding process for a new employee
        
        Args:
            employee_id: Employee ID
            start_date: Onboarding start date (defaults to today)
            
        Returns:
            Dict containing onboarding process details
        """
        try:
            if start_date is None:
                start_date = datetime.now()
            
            # Verify employee exists
            employee = self.db_manager.get_employee(employee_id)
            if not employee:
                return {
                    "success": False,
                    "message": f"Employee {employee_id} not found"
                }
            
            logger.info(f"Starting onboarding process for employee {employee_id}")
            
            # Create onboarding tasks
            tasks = self._create_onboarding_tasks(employee, start_date)
            
            # Provision initial assets
            asset_result = self._provision_initial_assets(employee)
            
            # Send welcome notifications
            notification_result = self._send_onboarding_notifications(employee, tasks)
            
            # Create initial leave balance if not exists
            self.db_manager.create_initial_leave_balance(employee_id)
            
            return {
                "success": True,
                "message": f"Onboarding process started for {employee.name}",
                "employee_id": employee_id,
                "start_date": start_date.isoformat(),
                "tasks_created": len(tasks),
                "assets_provisioned": asset_result.get("assets_assigned", 0),
                "tasks": [self._task_to_dict(task) for task in tasks]
            }
            
        except Exception as e:
            logger.error(f"Error starting onboarding for {employee_id}: {str(e)}")
            return {
                "success": False,
                "message": f"Error starting onboarding process: {str(e)}"
            }
    
    def _create_onboarding_tasks(self, employee: Employee, start_date: datetime) -> List[OnboardingTask]:
        """Create onboarding tasks for employee"""
        tasks = []
        
        for template_task in self.default_tasks:
            task = OnboardingTask(
                task_id=f"{employee.employee_id}_{template_task.task_id}",
                title=template_task.title,
                description=template_task.description,
                assignee=template_task.assignee,
                due_days=template_task.due_days,
                dependencies=template_task.dependencies
            )
            
            # Calculate due date
            task.assigned_date = start_date
            task.due_date = start_date + timedelta(days=template_task.due_days)
            
            # Customize task based on employee role
            task = self._customize_task_for_role(task, employee.role)
            
            tasks.append(task)
        
        logger.info(f"Created {len(tasks)} onboarding tasks for {employee.employee_id}")
        return tasks
    
    def _customize_task_for_role(self, task: OnboardingTask, role: str) -> OnboardingTask:
        """Customize task based on employee role"""
        role_customizations = {
            "Software Engineer": {
                "it_provision_equipment": "Provision development laptop with IDE, development tools, and access to code repositories"
            },
            "Data Scientist": {
                "it_provision_equipment": "Provision high-performance laptop with data analysis tools and database access"
            },
            "Sales Representative": {
                "it_provision_equipment": "Provision laptop and mobile phone with CRM access and sales tools"
            }
        }
        
        if role in role_customizations and task.task_id.endswith(task.task_id.split('_', 1)[1]):
            base_task_id = task.task_id.split('_', 1)[1]
            if base_task_id in role_customizations[role]:
                task.description = role_customizations[role][base_task_id]
        
        return task
    
    def _provision_initial_assets(self, employee: Employee) -> Dict[str, Any]:
        """Provision initial assets for new employee"""
        try:
            # Get role-based asset rules
            asset_rules = self.db_manager.get_role_asset_rules()
            required_assets = asset_rules.get(employee.role, [])
            
            if not required_assets:
                logger.info(f"No asset rules defined for role: {employee.role}")
                return {"success": True, "assets_assigned": 0, "message": "No assets required for this role"}
            
            assigned_assets = []
            failed_assignments = []
            
            for asset_type in required_assets:
                # Find available asset of this type
                available_assets = self.db_manager.get_available_assets_by_type(asset_type)
                
                if available_assets:
                    # Assign the first available asset
                    asset = available_assets[0]
                    success = self.db_manager.assign_asset(asset.asset_id, employee.employee_id)
                    
                    if success:
                        assigned_assets.append({
                            "asset_id": asset.asset_id,
                            "asset_type": asset_type,
                            "model": asset.model
                        })
                        logger.info(f"Assigned {asset_type} {asset.asset_id} to {employee.employee_id}")
                    else:
                        failed_assignments.append(asset_type)
                else:
                    failed_assignments.append(asset_type)
                    logger.warning(f"No available {asset_type} assets for {employee.employee_id}")
            
            return {
                "success": True,
                "assets_assigned": len(assigned_assets),
                "assigned_assets": assigned_assets,
                "failed_assignments": failed_assignments,
                "message": f"Assigned {len(assigned_assets)} assets, {len(failed_assignments)} failed"
            }
            
        except Exception as e:
            logger.error(f"Error provisioning assets for {employee.employee_id}: {str(e)}")
            return {
                "success": False,
                "message": f"Error provisioning assets: {str(e)}"
            }
    
    def _send_onboarding_notifications(self, employee: Employee, tasks: List[OnboardingTask]) -> Dict[str, Any]:
        """Send onboarding notifications to relevant parties"""
        try:
            notifications_sent = []
            
            # Group tasks by assignee
            tasks_by_assignee = {}
            for task in tasks:
                if task.assignee not in tasks_by_assignee:
                    tasks_by_assignee[task.assignee] = []
                tasks_by_assignee[task.assignee].append(task)
            
            # Create notification messages
            for assignee, assignee_tasks in tasks_by_assignee.items():
                notification = {
                    "recipient": assignee,
                    "subject": f"Onboarding Tasks for New Employee: {employee.name}",
                    "message": f"You have {len(assignee_tasks)} onboarding tasks assigned for new employee {employee.name} ({employee.employee_id})",
                    "tasks": [task.title for task in assignee_tasks],
                    "employee": {
                        "name": employee.name,
                        "employee_id": employee.employee_id,
                        "role": employee.role,
                        "department": employee.department,
                        "start_date": employee.hire_date.isoformat() if employee.hire_date else None
                    }
                }
                notifications_sent.append(notification)
            
            # In a real implementation, these would be sent via email
            logger.info(f"Created {len(notifications_sent)} onboarding notifications for {employee.employee_id}")
            
            return {
                "success": True,
                "notifications_sent": len(notifications_sent),
                "notifications": notifications_sent
            }
            
        except Exception as e:
            logger.error(f"Error sending onboarding notifications for {employee.employee_id}: {str(e)}")
            return {
                "success": False,
                "message": f"Error sending notifications: {str(e)}"
            }
    
    def update_task_status(self, task_id: str, status: OnboardingTaskStatus, notes: str = "") -> Dict[str, Any]:
        """Update onboarding task status"""
        try:
            # In a real implementation, this would update the task in the database
            # For now, we'll just log the update
            logger.info(f"Updated task {task_id} status to {status.value}")
            
            if status == OnboardingTaskStatus.COMPLETED:
                completed_date = datetime.now()
                logger.info(f"Task {task_id} completed on {completed_date}")
            
            return {
                "success": True,
                "message": f"Task status updated to {status.value}",
                "task_id": task_id,
                "status": status.value,
                "updated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error updating task status for {task_id}: {str(e)}")
            return {
                "success": False,
                "message": f"Error updating task status: {str(e)}"
            }
    
    def get_onboarding_progress(self, employee_id: str) -> Dict[str, Any]:
        """Get onboarding progress for employee"""
        try:
            employee = self.db_manager.get_employee(employee_id)
            if not employee:
                return {
                    "success": False,
                    "message": f"Employee {employee_id} not found"
                }
            
            # In a real implementation, this would fetch actual task data from database
            # For now, we'll return a mock progress report
            mock_progress = {
                "employee_id": employee_id,
                "employee_name": employee.name,
                "start_date": employee.hire_date.isoformat() if employee.hire_date else None,
                "total_tasks": len(self.default_tasks),
                "completed_tasks": 5,  # Mock data
                "pending_tasks": 8,    # Mock data
                "overdue_tasks": 2,    # Mock data
                "completion_percentage": 38.5,  # Mock data
                "next_due_task": {
                    "title": "Benefits Enrollment",
                    "due_date": (datetime.now() + timedelta(days=2)).isoformat(),
                    "assignee": "hr"
                }
            }
            
            return {
                "success": True,
                "progress": mock_progress
            }
            
        except Exception as e:
            logger.error(f"Error getting onboarding progress for {employee_id}: {str(e)}")
            return {
                "success": False,
                "message": f"Error retrieving progress: {str(e)}"
            }
    
    def _task_to_dict(self, task: OnboardingTask) -> Dict[str, Any]:
        """Convert OnboardingTask to dictionary"""
        return {
            "task_id": task.task_id,
            "title": task.title,
            "description": task.description,
            "assignee": task.assignee,
            "status": task.status.value,
            "due_days": task.due_days,
            "dependencies": task.dependencies,
            "assigned_date": task.assigned_date.isoformat() if task.assigned_date else None,
            "completed_date": task.completed_date.isoformat() if task.completed_date else None,
            "notes": task.notes
        }
