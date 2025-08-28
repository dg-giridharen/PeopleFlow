#!/usr/bin/env python3
"""
Migration script to move data from JSON files to PostgreSQL database
"""
import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# Add the parent directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from backend.models.database import db, DatabaseConfig, Employee, LeaveBalance, Asset
from backend.utils.data_manager import DataManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataMigrator:
    """Handles migration from JSON files to PostgreSQL database"""
    
    def __init__(self, app, json_data_dir="data"):
        """
        Initialize the migrator
        
        Args:
            app: Flask application instance
            json_data_dir: Directory containing JSON data files
        """
        self.app = app
        self.json_data_dir = json_data_dir
        self.data_manager = DataManager(json_data_dir)
        
        # Initialize database
        with app.app_context():
            db.create_all()
    
    def migrate_all_data(self):
        """Migrate all data from JSON to database"""
        logger.info("Starting complete data migration from JSON to PostgreSQL")
        
        with self.app.app_context():
            try:
                # Clear existing data (for clean migration)
                self.clear_database()
                
                # Migrate in order (employees first, then dependent data)
                self.migrate_employees()
                self.migrate_leave_balances()
                self.migrate_assets()
                
                logger.info("Data migration completed successfully")
                return True
                
            except Exception as e:
                logger.error(f"Migration failed: {str(e)}")
                db.session.rollback()
                return False
    
    def clear_database(self):
        """Clear existing data from database tables"""
        logger.info("Clearing existing database data")
        
        # Delete in reverse order of dependencies
        db.session.query(Asset).delete()
        db.session.query(LeaveBalance).delete()
        db.session.query(Employee).delete()
        
        db.session.commit()
        logger.info("Database cleared")
    
    def migrate_employees(self):
        """Migrate employee data from JSON to database"""
        logger.info("Migrating employee data")
        
        try:
            employees_data = self.data_manager.get_all_employees()
            
            if not employees_data:
                logger.warning("No employee data found in JSON files")
                return
            
            migrated_count = 0
            for emp_data in employees_data:
                try:
                    # Convert hire_date string to datetime
                    hire_date_str = emp_data.get('hire_date', '')
                    if hire_date_str:
                        hire_date = datetime.strptime(hire_date_str, '%Y-%m-%d').date()
                    else:
                        hire_date = datetime.now().date()
                    
                    employee = Employee(
                        employee_id=emp_data['employee_id'],
                        name=emp_data['name'],
                        email=emp_data['email'],
                        role=emp_data['role'],
                        department=emp_data['department'],
                        hire_date=hire_date,
                        manager_id=emp_data.get('manager_id'),
                        status=emp_data.get('status', 'active')
                    )
                    
                    db.session.add(employee)
                    migrated_count += 1
                    
                except Exception as e:
                    logger.error(f"Error migrating employee {emp_data.get('employee_id', 'unknown')}: {str(e)}")
                    continue
            
            db.session.commit()
            logger.info(f"Migrated {migrated_count} employees")
            
        except Exception as e:
            logger.error(f"Error migrating employees: {str(e)}")
            db.session.rollback()
            raise
    
    def migrate_leave_balances(self):
        """Migrate leave balance data from JSON to database"""
        logger.info("Migrating leave balance data")
        
        try:
            balances_data = self.data_manager.get_all_leave_balances()
            
            if not balances_data:
                logger.warning("No leave balance data found in JSON files")
                return
            
            migrated_count = 0
            for balance_data in balances_data:
                try:
                    # Check if employee exists
                    employee = db.session.query(Employee).filter(
                        Employee.employee_id == balance_data['employee_id']
                    ).first()
                    
                    if not employee:
                        logger.warning(f"Employee {balance_data['employee_id']} not found, skipping leave balance")
                        continue
                    
                    leave_balance = LeaveBalance(
                        employee_id=balance_data['employee_id'],
                        year=balance_data.get('year', datetime.now().year),
                        annual_leave=balance_data.get('annual_leave', 20.0),
                        sick_leave=balance_data.get('sick_leave', 10.0),
                        personal_leave=balance_data.get('personal_leave', 5.0)
                    )
                    
                    db.session.add(leave_balance)
                    migrated_count += 1
                    
                except Exception as e:
                    logger.error(f"Error migrating leave balance for {balance_data.get('employee_id', 'unknown')}: {str(e)}")
                    continue
            
            db.session.commit()
            logger.info(f"Migrated {migrated_count} leave balances")
            
        except Exception as e:
            logger.error(f"Error migrating leave balances: {str(e)}")
            db.session.rollback()
            raise
    
    def migrate_assets(self):
        """Migrate asset data from JSON to database"""
        logger.info("Migrating asset data")
        
        try:
            assets_data = self.data_manager.get_all_assets()
            
            if not assets_data:
                logger.warning("No asset data found in JSON files")
                return
            
            migrated_count = 0
            for asset_data in assets_data:
                try:
                    # Check if assigned employee exists (if asset is assigned)
                    assigned_to = asset_data.get('assigned_to')
                    if assigned_to:
                        employee = db.session.query(Employee).filter(
                            Employee.employee_id == assigned_to
                        ).first()
                        if not employee:
                            logger.warning(f"Employee {assigned_to} not found, setting asset as available")
                            assigned_to = None
                            status = 'available'
                        else:
                            status = asset_data.get('status', 'assigned')
                    else:
                        status = asset_data.get('status', 'available')
                    
                    asset = Asset(
                        asset_id=asset_data['asset_id'],
                        asset_type=asset_data['asset_type'],
                        brand=asset_data.get('brand'),
                        model=asset_data.get('model'),
                        serial_number=asset_data.get('serial_number'),
                        status=status,
                        assigned_to=assigned_to,
                        assigned_date=datetime.utcnow() if assigned_to else None,
                        notes=asset_data.get('notes')
                    )
                    
                    db.session.add(asset)
                    migrated_count += 1
                    
                except Exception as e:
                    logger.error(f"Error migrating asset {asset_data.get('asset_id', 'unknown')}: {str(e)}")
                    continue
            
            db.session.commit()
            logger.info(f"Migrated {migrated_count} assets")
            
        except Exception as e:
            logger.error(f"Error migrating assets: {str(e)}")
            db.session.rollback()
            raise
    
    def verify_migration(self):
        """Verify that migration was successful"""
        logger.info("Verifying migration results")
        
        with self.app.app_context():
            try:
                # Count records in database
                employee_count = db.session.query(Employee).count()
                balance_count = db.session.query(LeaveBalance).count()
                asset_count = db.session.query(Asset).count()
                
                logger.info(f"Database contains:")
                logger.info(f"  - {employee_count} employees")
                logger.info(f"  - {balance_count} leave balances")
                logger.info(f"  - {asset_count} assets")
                
                # Compare with JSON data
                json_employees = len(self.data_manager.get_all_employees())
                json_balances = len(self.data_manager.get_all_leave_balances())
                json_assets = len(self.data_manager.get_all_assets())
                
                logger.info(f"JSON files contained:")
                logger.info(f"  - {json_employees} employees")
                logger.info(f"  - {json_balances} leave balances")
                logger.info(f"  - {json_assets} assets")
                
                # Check for discrepancies
                if employee_count != json_employees:
                    logger.warning(f"Employee count mismatch: DB={employee_count}, JSON={json_employees}")
                if balance_count != json_balances:
                    logger.warning(f"Leave balance count mismatch: DB={balance_count}, JSON={json_balances}")
                if asset_count != json_assets:
                    logger.warning(f"Asset count mismatch: DB={asset_count}, JSON={json_assets}")
                
                return True
                
            except Exception as e:
                logger.error(f"Error verifying migration: {str(e)}")
                return False
    
    def backup_json_data(self, backup_dir="data_backup"):
        """Create backup of JSON data before migration"""
        logger.info(f"Creating backup of JSON data in {backup_dir}")
        
        try:
            # Create backup directory
            Path(backup_dir).mkdir(exist_ok=True)
            
            # Copy JSON files
            json_files = ['employees.json', 'leave_balances.json', 'assets.json']
            
            for filename in json_files:
                source_path = os.path.join(self.json_data_dir, filename)
                backup_path = os.path.join(backup_dir, f"{filename}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
                
                if os.path.exists(source_path):
                    import shutil
                    shutil.copy2(source_path, backup_path)
                    logger.info(f"Backed up {filename} to {backup_path}")
                else:
                    logger.warning(f"JSON file {filename} not found")
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating backup: {str(e)}")
            return False


def main():
    """Main migration function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate HR Assistant data from JSON to PostgreSQL")
    parser.add_argument("--environment", choices=["development", "testing", "production"], 
                       default="development", help="Database environment")
    parser.add_argument("--data-dir", default="data", help="Directory containing JSON data files")
    parser.add_argument("--backup", action="store_true", help="Create backup of JSON data before migration")
    parser.add_argument("--verify-only", action="store_true", help="Only verify existing migration")
    
    args = parser.parse_args()
    
    # Create Flask app for database context
    app = Flask(__name__)
    DatabaseConfig.init_app(app, args.environment)
    
    # Initialize migrator
    migrator = DataMigrator(app, args.data_dir)
    
    try:
        if args.verify_only:
            # Only verify existing data
            success = migrator.verify_migration()
        else:
            # Create backup if requested
            if args.backup:
                migrator.backup_json_data()
            
            # Perform migration
            success = migrator.migrate_all_data()
            
            if success:
                # Verify migration
                migrator.verify_migration()
        
        if success:
            logger.info("Migration process completed successfully")
        else:
            logger.error("Migration process failed")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Migration process failed with error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
