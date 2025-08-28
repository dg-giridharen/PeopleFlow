#!/usr/bin/env python3
"""
Production System Setup Script
Initializes the complete HR Assistant with all production features
"""
import os
import sys
import logging
from datetime import datetime
from pathlib import Path

# Add the parent directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from backend.models.database import db, DatabaseConfig
from backend.utils.auth import auth_manager, create_default_admin_user
from backend.utils.email_service import email_service
from backend.utils.document_processor import DocumentProcessor
from backend.utils.vector_store import VectorStore
from backend.workflows.policy_query import PolicyQueryWorkflow

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ProductionSystemSetup:
    """Handles complete production system setup"""
    
    def __init__(self, environment='development'):
        self.environment = environment
        self.app = None
        self.setup_steps = [
            ('Initialize Flask Application', self.setup_flask_app),
            ('Setup Database', self.setup_database),
            ('Setup Authentication', self.setup_authentication),
            ('Setup Email Service', self.setup_email_service),
            ('Setup RAG System', self.setup_rag_system),
            ('Create Sample Data', self.create_sample_data),
            ('Verify System', self.verify_system)
        ]
    
    def run_complete_setup(self):
        """Run complete production system setup"""
        logger.info(f"Starting production system setup for {self.environment} environment")
        
        success_count = 0
        total_steps = len(self.setup_steps)
        
        for step_name, step_function in self.setup_steps:
            try:
                logger.info(f"Running step: {step_name}")
                result = step_function()
                
                if result:
                    logger.info(f"✓ {step_name} completed successfully")
                    success_count += 1
                else:
                    logger.error(f"✗ {step_name} failed")
                    
            except Exception as e:
                logger.error(f"✗ {step_name} failed with error: {str(e)}")
        
        logger.info(f"Setup completed: {success_count}/{total_steps} steps successful")
        
        if success_count == total_steps:
            logger.info("🎉 Production system setup completed successfully!")
            self.print_next_steps()
            return True
        else:
            logger.error("❌ Production system setup completed with errors")
            return False
    
    def setup_flask_app(self):
        """Initialize Flask application with production configuration"""
        try:
            self.app = Flask(__name__)
            
            # Production configuration
            self.app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'production-secret-key-change-me')
            self.app.config['WTF_CSRF_ENABLED'] = True
            self.app.config['SESSION_COOKIE_SECURE'] = self.environment == 'production'
            self.app.config['SESSION_COOKIE_HTTPONLY'] = True
            
            # Initialize database configuration
            DatabaseConfig.init_app(self.app, self.environment)
            
            logger.info("Flask application initialized with production configuration")
            return True
            
        except Exception as e:
            logger.error(f"Error setting up Flask app: {str(e)}")
            return False
    
    def setup_database(self):
        """Setup database with all tables and initial data"""
        try:
            with self.app.app_context():
                # Create all database tables
                db.create_all()
                logger.info("Database tables created successfully")
                
                # Verify database connection
                db.session.execute('SELECT 1')
                logger.info("Database connection verified")
                
                return True
                
        except Exception as e:
            logger.error(f"Error setting up database: {str(e)}")
            return False
    
    def setup_authentication(self):
        """Setup authentication system"""
        try:
            with self.app.app_context():
                # Initialize authentication manager
                auth_manager.init_app(self.app)
                
                # Create default admin user
                create_default_admin_user()
                
                logger.info("Authentication system initialized")
                return True
                
        except Exception as e:
            logger.error(f"Error setting up authentication: {str(e)}")
            return False
    
    def setup_email_service(self):
        """Setup email notification service"""
        try:
            # Initialize email service
            email_service.init_app(self.app)
            
            # Test email configuration (if credentials are provided)
            if self.app.config.get('MAIL_USERNAME'):
                logger.info("Email service configured with SMTP credentials")
            else:
                logger.warning("Email service configured but no SMTP credentials provided")
            
            return True
            
        except Exception as e:
            logger.error(f"Error setting up email service: {str(e)}")
            return False
    
    def setup_rag_system(self):
        """Setup RAG system for policy queries"""
        try:
            # Check if knowledge base directory exists
            knowledge_base_dir = "knowledge_base"
            if not os.path.exists(knowledge_base_dir):
                logger.warning(f"Knowledge base directory {knowledge_base_dir} not found")
                return True  # Not a critical failure
            
            # Initialize document processor
            doc_processor = DocumentProcessor(knowledge_base_dir)
            
            # Process documents
            documents = doc_processor.process_documents_for_rag()
            
            if documents:
                # Initialize vector store
                vector_store = VectorStore()
                
                # Build index
                vector_store.build_index(documents)
                
                # Test the system
                test_query = "What is the company policy?"
                results = vector_store.search(test_query, k=1)
                
                if results:
                    logger.info(f"RAG system initialized with {len(documents)} document chunks")
                else:
                    logger.warning("RAG system initialized but search test failed")
            else:
                logger.warning("No documents found in knowledge base")
            
            return True
            
        except Exception as e:
            logger.error(f"Error setting up RAG system: {str(e)}")
            return False
    
    def create_sample_data(self):
        """Create sample data for testing"""
        try:
            with self.app.app_context():
                from backend.utils.database_manager import DatabaseManager
                from backend.models.database import Employee, Asset
                
                db_manager = DatabaseManager()
                
                # Check if sample data already exists
                existing_employees = db_manager.get_all_employees()
                if existing_employees:
                    logger.info("Sample data already exists, skipping creation")
                    return True
                
                # Create sample employees
                sample_employees = [
                    {
                        'employee_id': 'EMP001',
                        'name': 'John Doe',
                        'email': 'john.doe@company.com',
                        'role': 'Software Engineer',
                        'department': 'Engineering',
                        'hire_date': '2024-01-15',
                        'status': 'active'
                    },
                    {
                        'employee_id': 'EMP002',
                        'name': 'Jane Smith',
                        'email': 'jane.smith@company.com',
                        'role': 'Product Manager',
                        'department': 'Product',
                        'hire_date': '2024-02-01',
                        'status': 'active'
                    },
                    {
                        'employee_id': 'EMP003',
                        'name': 'Mike Johnson',
                        'email': 'mike.johnson@company.com',
                        'role': 'HR Manager',
                        'department': 'Human Resources',
                        'hire_date': '2023-12-01',
                        'status': 'active'
                    }
                ]
                
                for emp_data in sample_employees:
                    success = db_manager.add_employee(emp_data)
                    if success:
                        logger.info(f"Created sample employee: {emp_data['name']}")
                
                # Create sample assets
                sample_assets = [
                    {
                        'asset_id': 'LAP001',
                        'asset_type': 'laptop',
                        'brand': 'Dell',
                        'model': 'XPS 13',
                        'status': 'available'
                    },
                    {
                        'asset_id': 'LAP002',
                        'asset_type': 'laptop',
                        'brand': 'MacBook',
                        'model': 'Pro 14"',
                        'status': 'available'
                    },
                    {
                        'asset_id': 'MON001',
                        'asset_type': 'monitor',
                        'brand': 'Samsung',
                        'model': '27" 4K',
                        'status': 'available'
                    }
                ]
                
                for asset_data in sample_assets:
                    asset = Asset(**asset_data)
                    db.session.add(asset)
                
                db.session.commit()
                logger.info("Sample data created successfully")
                
                return True
                
        except Exception as e:
            logger.error(f"Error creating sample data: {str(e)}")
            return False
    
    def verify_system(self):
        """Verify all system components are working"""
        try:
            with self.app.app_context():
                # Test database connection
                from backend.utils.database_manager import DatabaseManager
                db_manager = DatabaseManager()
                employees = db_manager.get_all_employees()
                logger.info(f"Database verification: Found {len(employees)} employees")
                
                # Test authentication system
                from backend.models.database import User
                admin_users = db.session.query(User).filter(User.role == 'admin').count()
                logger.info(f"Authentication verification: Found {admin_users} admin users")
                
                # Test RAG system
                try:
                    from backend.workflows.policy_query import PolicyQueryWorkflow
                    policy_workflow = PolicyQueryWorkflow()
                    test_result = policy_workflow.process_policy_query("test query")
                    logger.info("RAG system verification: Policy query system operational")
                except Exception as e:
                    logger.warning(f"RAG system verification failed: {str(e)}")
                
                return True
                
        except Exception as e:
            logger.error(f"Error verifying system: {str(e)}")
            return False
    
    def print_next_steps(self):
        """Print next steps for the user"""
        print("\n" + "="*60)
        print("🎉 HR ASSISTANT PRODUCTION SETUP COMPLETE!")
        print("="*60)
        print("\nNext Steps:")
        print("1. Update environment variables:")
        print("   - DATABASE_URL (PostgreSQL connection string)")
        print("   - SECRET_KEY (strong secret key for production)")
        print("   - MAIL_SERVER, MAIL_USERNAME, MAIL_PASSWORD (email settings)")
        print("\n2. Run the application:")
        print("   python backend/app.py")
        print("\n3. Access the system:")
        print("   - Web Interface: http://localhost:5000")
        print("   - Admin Dashboard: http://localhost:5000/admin")
        print("   - Employee Portal: http://localhost:5000/employee")
        print("\n4. Default Admin Credentials:")
        print("   - Username: admin")
        print("   - Password: admin123")
        print("   ⚠️  CHANGE THESE CREDENTIALS IMMEDIATELY!")
        print("\n5. Build RAG Knowledge Base:")
        print("   python scripts/build_vector_store.py")
        print("\n6. Test the system:")
        print("   python -m pytest tests/")
        print("\n" + "="*60)


def main():
    """Main setup function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Setup HR Assistant Production System")
    parser.add_argument("--environment", choices=["development", "testing", "production"], 
                       default="development", help="Environment to setup")
    
    args = parser.parse_args()
    
    # Create setup instance and run
    setup = ProductionSystemSetup(args.environment)
    success = setup.run_complete_setup()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
