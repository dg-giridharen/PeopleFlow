"""
Employee Offboarding Workflow Implementation
Handles automated offboarding process for departing employees
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from enum import Enum

from backend.utils.database_manager import DatabaseManager
from backend.models.database import Employee, Asset, db

logger = logging.getLogger(__name__)


class OffboardingTaskStatus(Enum):
    """Offboarding task status enumeration"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


class OffboardingReason(Enum):
    """Reasons for employee departure"""
    RESIGNATION = "resignation"
    TERMINATION = "termination"
    RETIREMENT = "retirement"
    CONTRACT_END = "contract_end"
    LAYOFF = "layoff"
    OTHER = "other"


class OffboardingTask:
    """Individual offboarding task"""
    
    def __init__(self, task_id: str, title: str, description: str, 
                 assignee: str, due_days: int = 0, dependencies: List[str] = None):
        self.task_id = task_id
        self.title = title
        self.description = description
        self.assignee = assignee  # hr, it, manager, finance
        self.due_days = due_days  # Days from termination date (negative = before, positive = after)
        self.dependencies = dependencies or []
        self.status = OffboardingTaskStatus.PENDING
        self.assigned_date = None
        self.completed_date = None
        self.notes = ""


class OffboardingWorkflow:
    """Handles the complete employee offboarding process"""
    
    def __init__(self, db_manager: DatabaseManager = None):
        self.db_manager = db_manager or DatabaseManager()
        self.default_tasks = self._get_default_offboarding_tasks()
    
    def _get_default_offboarding_tasks(self) -> List[OffboardingTask]:
        """Get default offboarding tasks"""
        return [
            # Pre-departure tasks (negative days = before last day)
            OffboardingTask(
                "hr_exit_interview_schedule",
                "Schedule Exit Interview",
                "Schedule exit interview to gather feedback and discuss transition",
                "hr",
                due_days=-5
            ),
            OffboardingTask(
                "hr_benefits_discussion",
                "Benefits Continuation Discussion",
                "Discuss COBRA, 401k rollover, and other benefit continuation options",
                "hr",
                due_days=-3
            ),
            OffboardingTask(
                "manager_knowledge_transfer",
                "Knowledge Transfer Session",
                "Conduct knowledge transfer sessions and document key processes",
                "manager",
                due_days=-7
            ),
            OffboardingTask(
                "manager_project_handover",
                "Project Handover",
                "Transfer ongoing projects and responsibilities to other team members",
                "manager",
                due_days=-5
            ),
            
            # Last day tasks
            OffboardingTask(
                "hr_exit_interview",
                "Conduct Exit Interview",
                "Conduct final exit interview and collect feedback",
                "hr",
                due_days=0
            ),
            OffboardingTask(
                "hr_final_paperwork",
                "Complete Final Paperwork",
                "Process final paperwork, return company property checklist",
                "hr",
                due_days=0
            ),
            OffboardingTask(
                "it_disable_accounts",
                "Disable IT Accounts",
                "Disable email, system access, and revoke all IT permissions",
                "it",
                due_days=0
            ),
            OffboardingTask(
                "it_collect_equipment",
                "Collect IT Equipment",
                "Collect laptop, phone, access cards, and other company equipment",
                "it",
                due_days=0
            ),
            OffboardingTask(
                "security_revoke_access",
                "Revoke Physical Access",
                "Deactivate key cards, building access, and parking permits",
                "security",
                due_days=0
            ),
            
            # Post-departure tasks (positive days = after last day)
            OffboardingTask(
                "finance_final_payroll",
                "Process Final Payroll",
                "Calculate and process final paycheck including unused PTO",
                "finance",
                due_days=1
            ),
            OffboardingTask(
                "hr_update_records",
                "Update Employee Records",
                "Update employee status in all systems and archive records",
                "hr",
                due_days=1
            ),
            OffboardingTask(
                "it_data_backup",
                "Backup Employee Data",
                "Backup important files and transfer to appropriate team members",
                "it",
                due_days=1,
                dependencies=["it_disable_accounts"]
            ),
            OffboardingTask(
                "hr_reference_setup",
                "Setup Reference Process",
                "Document reference contact information and approval process",
                "hr",
                due_days=3
            )
        ]
    
    def initiate_offboarding(self, employee_id: str, termination_date: datetime, 
                           reason: OffboardingReason, initiated_by: str = None) -> Dict[str, Any]:
        """
        Initiate offboarding process for an employee
        
        Args:
            employee_id: Employee ID
            termination_date: Last working day
            reason: Reason for departure
            initiated_by: Who initiated the offboarding
            
        Returns:
            Dict containing offboarding process details
        """
        try:
            # Verify employee exists and is active
            employee = self.db_manager.get_employee(employee_id)
            if not employee:
                return {
                    "success": False,
                    "message": f"Employee {employee_id} not found"
                }
            
            if employee.status != 'active':
                return {
                    "success": False,
                    "message": f"Employee {employee_id} is not active"
                }
            
            logger.info(f"Initiating offboarding process for employee {employee_id}")
            
            # Create offboarding tasks
            tasks = self._create_offboarding_tasks(employee, termination_date, reason)
            
            # Get employee assets for return tracking
            assets_to_return = self._get_employee_assets_for_return(employee)
            
            # Send offboarding notifications
            notification_result = self._send_offboarding_notifications(employee, tasks, termination_date, reason)
            
            # Update employee status to indicate offboarding in progress
            # (Don't set to inactive yet - that happens on termination date)
            
            return {
                "success": True,
                "message": f"Offboarding process initiated for {employee.name}",
                "employee_id": employee_id,
                "termination_date": termination_date.isoformat(),
                "reason": reason.value,
                "tasks_created": len(tasks),
                "assets_to_return": len(assets_to_return),
                "tasks": [self._task_to_dict(task) for task in tasks],
                "assets": [self._asset_to_dict(asset) for asset in assets_to_return]
            }
            
        except Exception as e:
            logger.error(f"Error initiating offboarding for {employee_id}: {str(e)}")
            return {
                "success": False,
                "message": f"Error initiating offboarding process: {str(e)}"
            }
    
    def _create_offboarding_tasks(self, employee: Employee, termination_date: datetime, 
                                reason: OffboardingReason) -> List[OffboardingTask]:
        """Create offboarding tasks for employee"""
        tasks = []
        
        for template_task in self.default_tasks:
            task = OffboardingTask(
                task_id=f"{employee.employee_id}_{template_task.task_id}",
                title=template_task.title,
                description=template_task.description,
                assignee=template_task.assignee,
                due_days=template_task.due_days,
                dependencies=template_task.dependencies
            )
            
            # Calculate due date based on termination date
            task.assigned_date = datetime.now()
            task.due_date = termination_date + timedelta(days=template_task.due_days)
            
            # Customize task based on departure reason
            task = self._customize_task_for_reason(task, reason)
            
            tasks.append(task)
        
        # Add reason-specific tasks
        if reason == OffboardingReason.TERMINATION:
            tasks.append(OffboardingTask(
                f"{employee.employee_id}_security_escort",
                "Security Escort",
                "Arrange security escort for final day if required",
                "security",
                due_days=0
            ))
        
        logger.info(f"Created {len(tasks)} offboarding tasks for {employee.employee_id}")
        return tasks
    
    def _customize_task_for_reason(self, task: OffboardingTask, reason: OffboardingReason) -> OffboardingTask:
        """Customize task based on departure reason"""
        if reason == OffboardingReason.TERMINATION:
            if task.task_id.endswith("exit_interview"):
                task.description = "Conduct exit interview focusing on immediate concerns and feedback"
            elif task.task_id.endswith("knowledge_transfer"):
                task.due_days = -1  # Shorter timeline for terminations
        
        elif reason == OffboardingReason.RETIREMENT:
            if task.task_id.endswith("benefits_discussion"):
                task.description = "Discuss retirement benefits, pension, and healthcare continuation"
        
        return task
    
    def _get_employee_assets_for_return(self, employee: Employee) -> List[Asset]:
        """Get list of assets assigned to employee that need to be returned"""
        try:
            return self.db_manager.get_employee_assets(employee.employee_id)
        except Exception as e:
            logger.error(f"Error getting assets for {employee.employee_id}: {str(e)}")
            return []
    
    def _send_offboarding_notifications(self, employee: Employee, tasks: List[OffboardingTask], 
                                      termination_date: datetime, reason: OffboardingReason) -> Dict[str, Any]:
        """Send offboarding notifications to relevant parties"""
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
                    "subject": f"Offboarding Tasks for Departing Employee: {employee.name}",
                    "message": f"You have {len(assignee_tasks)} offboarding tasks for departing employee {employee.name} ({employee.employee_id})",
                    "termination_date": termination_date.isoformat(),
                    "reason": reason.value,
                    "tasks": [task.title for task in assignee_tasks],
                    "employee": {
                        "name": employee.name,
                        "employee_id": employee.employee_id,
                        "role": employee.role,
                        "department": employee.department
                    }
                }
                notifications_sent.append(notification)
            
            # Special notification to manager
            manager_notification = {
                "recipient": "manager",
                "subject": f"Employee Departure: {employee.name}",
                "message": f"Employee {employee.name} will be leaving on {termination_date.strftime('%Y-%m-%d')}. Please ensure knowledge transfer and project handover are completed.",
                "priority": "high"
            }
            notifications_sent.append(manager_notification)
            
            logger.info(f"Created {len(notifications_sent)} offboarding notifications for {employee.employee_id}")
            
            return {
                "success": True,
                "notifications_sent": len(notifications_sent),
                "notifications": notifications_sent
            }
            
        except Exception as e:
            logger.error(f"Error sending offboarding notifications for {employee.employee_id}: {str(e)}")
            return {
                "success": False,
                "message": f"Error sending notifications: {str(e)}"
            }
    
    def process_asset_return(self, employee_id: str, asset_id: str, condition: str = "good", 
                           notes: str = "") -> Dict[str, Any]:
        """Process return of company asset"""
        try:
            asset = self.db_manager.get_asset(asset_id)
            if not asset:
                return {
                    "success": False,
                    "message": f"Asset {asset_id} not found"
                }
            
            if asset.assigned_to != employee_id:
                return {
                    "success": False,
                    "message": f"Asset {asset_id} is not assigned to employee {employee_id}"
                }
            
            # Update asset status
            asset.status = 'available' if condition == 'good' else 'maintenance'
            asset.assigned_to = None
            asset.assigned_date = None
            asset.notes = f"Returned on {datetime.now().strftime('%Y-%m-%d')}. Condition: {condition}. Notes: {notes}"
            
            self.db_manager.commit()
            
            logger.info(f"Asset {asset_id} returned by employee {employee_id}")
            
            return {
                "success": True,
                "message": f"Asset {asset_id} returned successfully",
                "asset_id": asset_id,
                "condition": condition,
                "new_status": asset.status
            }
            
        except Exception as e:
            logger.error(f"Error processing asset return: {str(e)}")
            return {
                "success": False,
                "message": f"Error processing asset return: {str(e)}"
            }
    
    def complete_offboarding(self, employee_id: str) -> Dict[str, Any]:
        """Complete offboarding process and deactivate employee"""
        try:
            employee = self.db_manager.get_employee(employee_id)
            if not employee:
                return {
                    "success": False,
                    "message": f"Employee {employee_id} not found"
                }
            
            # Check if all critical tasks are completed
            # In a real implementation, this would check actual task status
            
            # Deactivate employee
            success = self.db_manager.deactivate_employee(employee_id)
            
            if success:
                logger.info(f"Completed offboarding for employee {employee_id}")
                
                return {
                    "success": True,
                    "message": f"Offboarding completed for {employee.name}",
                    "employee_id": employee_id,
                    "completion_date": datetime.now().isoformat()
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to deactivate employee"
                }
            
        except Exception as e:
            logger.error(f"Error completing offboarding for {employee_id}: {str(e)}")
            return {
                "success": False,
                "message": f"Error completing offboarding: {str(e)}"
            }
    
    def get_offboarding_progress(self, employee_id: str) -> Dict[str, Any]:
        """Get offboarding progress for employee"""
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
                "total_tasks": len(self.default_tasks),
                "completed_tasks": 7,   # Mock data
                "pending_tasks": 6,     # Mock data
                "overdue_tasks": 0,     # Mock data
                "completion_percentage": 53.8,  # Mock data
                "assets_returned": 2,   # Mock data
                "assets_pending": 1,    # Mock data
                "next_due_task": {
                    "title": "Process Final Payroll",
                    "due_date": (datetime.now() + timedelta(days=1)).isoformat(),
                    "assignee": "finance"
                }
            }
            
            return {
                "success": True,
                "progress": mock_progress
            }
            
        except Exception as e:
            logger.error(f"Error getting offboarding progress for {employee_id}: {str(e)}")
            return {
                "success": False,
                "message": f"Error retrieving progress: {str(e)}"
            }
    
    def _task_to_dict(self, task: OffboardingTask) -> Dict[str, Any]:
        """Convert OffboardingTask to dictionary"""
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
    
    def _asset_to_dict(self, asset: Asset) -> Dict[str, Any]:
        """Convert Asset to dictionary for return tracking"""
        return {
            "asset_id": asset.asset_id,
            "asset_type": asset.asset_type,
            "brand": asset.brand,
            "model": asset.model,
            "serial_number": asset.serial_number,
            "assigned_date": asset.assigned_date.isoformat() if asset.assigned_date else None
        }
