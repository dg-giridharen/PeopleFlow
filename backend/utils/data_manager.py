"""
Data Manager utility for handling JSON file operations
"""
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime


class DataManager:
    """Handles CRUD operations for JSON data files"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.employees_file = os.path.join(data_dir, "employees.json")
        self.leave_balances_file = os.path.join(data_dir, "leave_balances.json")
        self.assets_file = os.path.join(data_dir, "assets.json")
    
    def _load_json(self, file_path: str) -> Dict[str, Any]:
        """Load JSON data from file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {file_path}: {e}")
    
    def _save_json(self, file_path: str, data: Dict[str, Any]) -> None:
        """Save JSON data to file"""
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
    
    # Employee operations
    def get_employee(self, employee_id: str) -> Optional[Dict[str, Any]]:
        """Get employee by ID"""
        data = self._load_json(self.employees_file)
        employees = data.get("employees", [])
        return next((emp for emp in employees if emp["employee_id"] == employee_id), None)
    
    def get_all_employees(self) -> List[Dict[str, Any]]:
        """Get all employees"""
        data = self._load_json(self.employees_file)
        return data.get("employees", [])
    
    def add_employee(self, employee_data: Dict[str, Any]) -> bool:
        """Add new employee"""
        data = self._load_json(self.employees_file)
        if "employees" not in data:
            data["employees"] = []
        
        # Check if employee already exists
        if any(emp["employee_id"] == employee_data["employee_id"] for emp in data["employees"]):
            return False
        
        data["employees"].append(employee_data)
        self._save_json(self.employees_file, data)
        return True
    
    # Leave balance operations
    def get_leave_balance(self, employee_id: str, year: int = None) -> Optional[Dict[str, Any]]:
        """Get leave balance for employee"""
        if year is None:
            year = datetime.now().year
        
        data = self._load_json(self.leave_balances_file)
        balances = data.get("leave_balances", [])
        return next((bal for bal in balances 
                    if bal["employee_id"] == employee_id and bal["year"] == year), None)
    
    def update_leave_balance(self, employee_id: str, leave_type: str, 
                           days_to_deduct: int, year: int = None) -> bool:
        """Update leave balance by deducting days"""
        if year is None:
            year = datetime.now().year
        
        data = self._load_json(self.leave_balances_file)
        balances = data.get("leave_balances", [])
        
        for balance in balances:
            if balance["employee_id"] == employee_id and balance["year"] == year:
                if leave_type in balance and balance[leave_type] >= days_to_deduct:
                    balance[leave_type] -= days_to_deduct
                    self._save_json(self.leave_balances_file, data)
                    return True
                else:
                    return False
        return False
    
    def get_all_leave_balances(self) -> List[Dict[str, Any]]:
        """Get all leave balances"""
        data = self._load_json(self.leave_balances_file)
        return data.get("leave_balances", [])
    
    # Asset operations
    def get_asset(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """Get asset by ID"""
        data = self._load_json(self.assets_file)
        assets = data.get("assets", [])
        return next((asset for asset in assets if asset["asset_id"] == asset_id), None)
    
    def get_available_assets_by_type(self, asset_type: str) -> List[Dict[str, Any]]:
        """Get available assets of specific type"""
        data = self._load_json(self.assets_file)
        assets = data.get("assets", [])
        return [asset for asset in assets 
                if asset["asset_type"] == asset_type and asset["status"] == "available"]
    
    def assign_asset(self, asset_id: str, employee_id: str) -> bool:
        """Assign asset to employee"""
        data = self._load_json(self.assets_file)
        assets = data.get("assets", [])
        
        for asset in assets:
            if asset["asset_id"] == asset_id and asset["status"] == "available":
                asset["status"] = "assigned"
                asset["assigned_to"] = employee_id
                self._save_json(self.assets_file, data)
                return True
        return False
    
    def get_role_asset_rules(self) -> Dict[str, List[str]]:
        """Get asset assignment rules by role"""
        data = self._load_json(self.assets_file)
        return data.get("role_asset_rules", {})
    
    def get_all_assets(self) -> List[Dict[str, Any]]:
        """Get all assets"""
        data = self._load_json(self.assets_file)
        return data.get("assets", [])
    
    def get_employee_assets(self, employee_id: str) -> List[Dict[str, Any]]:
        """Get all assets assigned to an employee"""
        data = self._load_json(self.assets_file)
        assets = data.get("assets", [])
        return [asset for asset in assets if asset["assigned_to"] == employee_id]
