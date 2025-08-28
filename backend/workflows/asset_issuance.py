"""
Asset Issuance Workflow Implementation
Handles new hire asset provisioning based on role requirements
"""
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class AssetIssuanceWorkflow:
    """Handles the complete asset issuance process for new hires"""
    
    def __init__(self, data_manager):
        self.data_manager = data_manager
        
        # Asset priority preferences for better allocation
        self.asset_preferences = {
            "laptop": ["MacBook Pro 16", "Dell XPS 15", "ThinkPad X1 Carbon", "Dell XPS 13"],
            "monitor": ["UltraWide 34", "UltraSharp 27", "Odyssey G7"],
            "keyboard": ["MX Keys", "Magic Keyboard"],
            "mouse": ["MX Master 3", "Magic Mouse"],
            "headset": ["WH-1000XM4"]
        }
    
    def provision_assets_for_new_hire(self, employee_id: str) -> Dict[str, Any]:
        """
        Provision standard equipment for a new hire based on their role
        
        Args:
            employee_id: New hire's employee ID
        
        Returns:
            Dict containing success status, message, and assigned assets
        """
        try:
            # Step 1: Validate employee exists
            employee = self.data_manager.get_employee(employee_id)
            if not employee:
                return {
                    "success": False,
                    "message": f"Employee with ID {employee_id} not found. Please verify the employee ID."
                }
            
            # Step 2: Check if employee already has assets assigned
            existing_assets = self.data_manager.get_employee_assets(employee_id)
            if existing_assets:
                return {
                    "success": False,
                    "message": f"Employee {employee['name']} already has assets assigned. "
                              f"Currently assigned: {len(existing_assets)} items."
                }
            
            # Step 3: Get role-based asset requirements
            role = employee.get("role", "")
            asset_rules = self.data_manager.get_role_asset_rules()
            required_asset_types = asset_rules.get(role, [])
            
            if not required_asset_types:
                return {
                    "success": False,
                    "message": f"No asset provisioning rules found for role '{role}'. "
                              f"Please contact IT to set up asset requirements for this role."
                }
            
            # Step 4: Find and assign assets
            assigned_assets = []
            assignment_failures = []
            
            for asset_type in required_asset_types:
                asset_result = self._assign_best_available_asset(asset_type, employee_id)
                
                if asset_result["success"]:
                    assigned_assets.append(asset_result["asset"])
                else:
                    assignment_failures.append({
                        "asset_type": asset_type,
                        "reason": asset_result["message"]
                    })
            
            # Step 5: Generate response based on results
            if not assigned_assets and assignment_failures:
                # No assets could be assigned
                failure_details = "\n".join([
                    f"• {failure['asset_type']}: {failure['reason']}" 
                    for failure in assignment_failures
                ])
                return {
                    "success": False,
                    "message": f"Unable to provision any assets for {employee['name']} ({role}).\n\n"
                              f"Issues encountered:\n{failure_details}\n\n"
                              f"Please contact IT to resolve inventory issues."
                }
            
            elif assigned_assets and assignment_failures:
                # Partial success
                success_message = self._generate_success_message(
                    employee, assigned_assets, partial=True
                )
                failure_details = "\n".join([
                    f"• {failure['asset_type']}: {failure['reason']}" 
                    for failure in assignment_failures
                ])
                
                return {
                    "success": True,
                    "message": f"{success_message}\n\n⚠️ Some assets could not be assigned:\n{failure_details}\n\n"
                              f"Please contact IT to complete the remaining assignments.",
                    "assigned_assets": assigned_assets,
                    "failed_assignments": assignment_failures
                }
            
            else:
                # Complete success
                success_message = self._generate_success_message(employee, assigned_assets)
                
                logger.info(f"Successfully provisioned {len(assigned_assets)} assets for {employee_id}")
                
                return {
                    "success": True,
                    "message": success_message,
                    "assigned_assets": assigned_assets
                }
        
        except Exception as e:
            logger.error(f"Error in asset provisioning: {str(e)}")
            return {
                "success": False,
                "message": "An unexpected error occurred during asset provisioning. Please try again."
            }
    
    def _assign_best_available_asset(self, asset_type: str, employee_id: str) -> Dict[str, Any]:
        """
        Find and assign the best available asset of the specified type
        
        Args:
            asset_type: Type of asset to assign
            employee_id: Employee to assign the asset to
        
        Returns:
            Dict with success status and asset details
        """
        try:
            # Get all available assets of this type
            available_assets = self.data_manager.get_available_assets_by_type(asset_type)
            
            if not available_assets:
                return {
                    "success": False,
                    "message": f"No available {asset_type} in inventory"
                }
            
            # Find the best asset based on preferences
            best_asset = self._select_best_asset(available_assets, asset_type)
            
            # Assign the asset
            success = self.data_manager.assign_asset(best_asset["asset_id"], employee_id)
            
            if success:
                return {
                    "success": True,
                    "asset": best_asset,
                    "message": f"Successfully assigned {asset_type}"
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to assign {asset_type} (system error)"
                }
        
        except Exception as e:
            logger.error(f"Error assigning {asset_type}: {str(e)}")
            return {
                "success": False,
                "message": f"Error occurred while assigning {asset_type}"
            }
    
    def _select_best_asset(self, available_assets: List[Dict], asset_type: str) -> Dict[str, Any]:
        """
        Select the best asset from available options based on preferences
        
        Args:
            available_assets: List of available assets
            asset_type: Type of asset
        
        Returns:
            Best asset from the list
        """
        preferences = self.asset_preferences.get(asset_type, [])
        
        # Try to find assets in order of preference
        for preferred_model in preferences:
            for asset in available_assets:
                if preferred_model.lower() in asset.get("model", "").lower():
                    return asset
        
        # If no preferred asset found, return the first available
        return available_assets[0]
    
    def _generate_success_message(self, employee: Dict, assigned_assets: List[Dict], 
                                partial: bool = False) -> str:
        """Generate success message for asset assignment"""
        status_emoji = "✅" if not partial else "⚠️"
        status_text = "Complete Asset Provisioning" if not partial else "Partial Asset Provisioning"
        
        message = f"{status_emoji} {status_text}\n\n"
        message += f"Assets have been provisioned for:\n"
        message += f"• Employee: {employee['name']} ({employee['employee_id']})\n"
        message += f"• Role: {employee['role']}\n"
        message += f"• Department: {employee['department']}\n\n"
        
        message += f"📦 Assigned Assets ({len(assigned_assets)} items):\n"
        
        for i, asset in enumerate(assigned_assets, 1):
            message += f"{i}. {asset['asset_type'].title()}: {asset['brand']} {asset['model']}\n"
            message += f"   • Asset ID: {asset['asset_id']}\n"
            message += f"   • Specifications: {asset['specifications']}\n"
            if i < len(assigned_assets):
                message += "\n"
        
        if not partial:
            message += f"\n🎉 All required assets have been successfully assigned! "
            message += f"The employee can collect these items from the IT department."
        
        return message
    
    def get_employee_assets(self, employee_id: str) -> Dict[str, Any]:
        """Get all assets currently assigned to an employee"""
        try:
            employee = self.data_manager.get_employee(employee_id)
            if not employee:
                return {
                    "success": False,
                    "message": f"Employee with ID {employee_id} not found."
                }
            
            assets = self.data_manager.get_employee_assets(employee_id)
            
            return {
                "success": True,
                "employee_name": employee["name"],
                "employee_role": employee["role"],
                "assigned_assets": assets,
                "total_assets": len(assets)
            }
        
        except Exception as e:
            logger.error(f"Error getting employee assets: {str(e)}")
            return {
                "success": False,
                "message": "Error retrieving asset information."
            }
    
    def get_available_assets_summary(self) -> Dict[str, Any]:
        """Get summary of available assets by type"""
        try:
            all_assets = self.data_manager.get_all_assets()
            available_assets = [asset for asset in all_assets if asset["status"] == "available"]
            
            # Group by asset type
            summary = {}
            for asset in available_assets:
                asset_type = asset["asset_type"]
                if asset_type not in summary:
                    summary[asset_type] = []
                summary[asset_type].append({
                    "asset_id": asset["asset_id"],
                    "brand": asset["brand"],
                    "model": asset["model"]
                })
            
            return {
                "success": True,
                "available_assets": summary,
                "total_available": len(available_assets)
            }
        
        except Exception as e:
            logger.error(f"Error getting asset summary: {str(e)}")
            return {
                "success": False,
                "message": "Error retrieving asset summary."
            }
