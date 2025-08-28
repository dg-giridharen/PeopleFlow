"""
Leave Approval Workflow Implementation
Handles employee leave requests with validation and balance management
"""
from datetime import datetime, timedelta
from dateutil.parser import parse
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class LeaveApprovalWorkflow:
    """Handles the complete leave approval process"""
    
    def __init__(self, data_manager):
        self.data_manager = data_manager
        self.leave_type_mapping = {
            'annual': 'annual_leave',
            'vacation': 'annual_leave',
            'sick': 'sick_leave',
            'personal': 'personal_leave',
            'annual_leave': 'annual_leave',
            'sick_leave': 'sick_leave',
            'personal_leave': 'personal_leave'
        }
    
    def process_leave_request(self, employee_id: str, start_date: str, 
                            end_date: str, leave_type: str = 'annual_leave') -> Dict[str, Any]:
        """
        Process a complete leave request workflow
        
        Args:
            employee_id: Employee's ID
            start_date: Leave start date (YYYY-MM-DD format)
            end_date: Leave end date (YYYY-MM-DD format)
            leave_type: Type of leave (annual, sick, personal)
        
        Returns:
            Dict containing success status and message
        """
        try:
            # Step 1: Validate employee exists
            employee = self.data_manager.get_employee(employee_id)
            if not employee:
                return {
                    "success": False,
                    "message": f"Employee with ID {employee_id} not found. Please check your employee ID."
                }
            
            # Step 2: Normalize leave type
            normalized_leave_type = self._normalize_leave_type(leave_type)
            if not normalized_leave_type:
                return {
                    "success": False,
                    "message": f"Invalid leave type '{leave_type}'. Valid types are: annual, sick, personal."
                }
            
            # Step 3: Parse and validate dates
            try:
                start_dt = parse(start_date).date()
                end_dt = parse(end_date).date()
            except Exception as e:
                return {
                    "success": False,
                    "message": "Invalid date format. Please use YYYY-MM-DD format (e.g., 2024-03-15)."
                }
            
            # Step 4: Validate date logic
            validation_result = self._validate_dates(start_dt, end_dt)
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "message": validation_result["message"]
                }
            
            # Step 5: Calculate business days
            business_days = self._calculate_business_days(start_dt, end_dt)
            
            # Step 6: Check leave balance
            balance = self.data_manager.get_leave_balance(employee_id)
            if not balance:
                return {
                    "success": False,
                    "message": f"Leave balance not found for employee {employee_id}. Please contact HR."
                }
            
            current_balance = balance.get(normalized_leave_type, 0)
            if current_balance < business_days:
                return {
                    "success": False,
                    "message": f"Insufficient {normalized_leave_type.replace('_', ' ')} balance. "
                              f"Requested: {business_days} days, Available: {current_balance} days."
                }
            
            # Step 7: Approve and deduct leave
            success = self.data_manager.update_leave_balance(
                employee_id, normalized_leave_type, business_days
            )
            
            if not success:
                return {
                    "success": False,
                    "message": "Failed to update leave balance. Please try again or contact HR."
                }
            
            # Step 8: Get updated balance for confirmation
            updated_balance = self.data_manager.get_leave_balance(employee_id)
            new_balance = updated_balance.get(normalized_leave_type, 0)
            
            # Step 9: Generate confirmation message
            confirmation_message = self._generate_confirmation_message(
                employee["name"], normalized_leave_type, start_dt, end_dt, 
                business_days, new_balance
            )
            
            logger.info(f"Leave approved for {employee_id}: {business_days} days from {start_date} to {end_date}")
            
            return {
                "success": True,
                "message": confirmation_message,
                "details": {
                    "employee_id": employee_id,
                    "employee_name": employee["name"],
                    "leave_type": normalized_leave_type,
                    "start_date": start_date,
                    "end_date": end_date,
                    "business_days": business_days,
                    "remaining_balance": new_balance
                }
            }
        
        except Exception as e:
            logger.error(f"Error processing leave request: {str(e)}")
            return {
                "success": False,
                "message": "An unexpected error occurred while processing your leave request. Please try again."
            }
    
    def _normalize_leave_type(self, leave_type: str) -> str:
        """Normalize leave type to standard format"""
        return self.leave_type_mapping.get(leave_type.lower(), None)
    
    def _validate_dates(self, start_date, end_date) -> Dict[str, Any]:
        """Validate date logic"""
        today = datetime.now().date()
        
        # Check if start date is in the past
        if start_date < today:
            return {
                "valid": False,
                "message": "Leave start date cannot be in the past. Please select a future date."
            }
        
        # Check if end date is before start date
        if end_date < start_date:
            return {
                "valid": False,
                "message": "Leave end date cannot be before the start date. Please check your dates."
            }
        
        # Check if leave period is too long (more than 30 days)
        if (end_date - start_date).days > 30:
            return {
                "valid": False,
                "message": "Leave period cannot exceed 30 days. For longer periods, please contact HR directly."
            }
        
        return {"valid": True, "message": "Dates are valid"}
    
    def _calculate_business_days(self, start_date, end_date) -> int:
        """Calculate business days between two dates (excluding weekends)"""
        business_days = 0
        current_date = start_date
        
        while current_date <= end_date:
            # Monday = 0, Sunday = 6
            if current_date.weekday() < 5:  # Monday to Friday
                business_days += 1
            current_date += timedelta(days=1)
        
        return business_days
    
    def _generate_confirmation_message(self, employee_name: str, leave_type: str, 
                                     start_date, end_date, business_days: int, 
                                     remaining_balance: int) -> str:
        """Generate a confirmation message for approved leave"""
        leave_type_display = leave_type.replace('_', ' ').title()
        
        message = f"✅ Leave Request Approved!\n\n"
        message += f"Hello {employee_name},\n\n"
        message += f"Your {leave_type_display} request has been approved:\n"
        message += f"• Leave Type: {leave_type_display}\n"
        message += f"• Start Date: {start_date.strftime('%B %d, %Y')}\n"
        message += f"• End Date: {end_date.strftime('%B %d, %Y')}\n"
        message += f"• Business Days: {business_days} days\n"
        message += f"• Remaining {leave_type_display} Balance: {remaining_balance} days\n\n"
        message += f"Please ensure you complete any handover tasks before your leave begins. "
        message += f"Have a great time off!"
        
        return message
    
    def get_leave_balance(self, employee_id: str) -> Dict[str, Any]:
        """Get current leave balance for an employee"""
        try:
            employee = self.data_manager.get_employee(employee_id)
            if not employee:
                return {
                    "success": False,
                    "message": f"Employee with ID {employee_id} not found."
                }
            
            balance = self.data_manager.get_leave_balance(employee_id)
            if not balance:
                return {
                    "success": False,
                    "message": f"Leave balance not found for employee {employee_id}."
                }
            
            return {
                "success": True,
                "employee_name": employee["name"],
                "balances": {
                    "annual_leave": balance.get("annual_leave", 0),
                    "sick_leave": balance.get("sick_leave", 0),
                    "personal_leave": balance.get("personal_leave", 0)
                }
            }
        
        except Exception as e:
            logger.error(f"Error getting leave balance: {str(e)}")
            return {
                "success": False,
                "message": "Error retrieving leave balance information."
            }
