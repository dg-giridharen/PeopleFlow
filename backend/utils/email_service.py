"""
Email Service for HR Assistant
Flask-Mail integration for automated email notifications
"""
import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from flask import current_app, render_template_string
from flask_mail import Mail, Message
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

logger = logging.getLogger(__name__)

# Initialize Flask-Mail
mail = Mail()


class EmailService:
    """Handles email notifications for HR processes"""
    
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize email service with Flask app"""
        # Configure Flask-Mail settings
        app.config.setdefault('MAIL_SERVER', os.environ.get('MAIL_SERVER', 'smtp.gmail.com'))
        app.config.setdefault('MAIL_PORT', int(os.environ.get('MAIL_PORT', 587)))
        app.config.setdefault('MAIL_USE_TLS', os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true')
        app.config.setdefault('MAIL_USE_SSL', os.environ.get('MAIL_USE_SSL', 'false').lower() == 'true')
        app.config.setdefault('MAIL_USERNAME', os.environ.get('MAIL_USERNAME'))
        app.config.setdefault('MAIL_PASSWORD', os.environ.get('MAIL_PASSWORD'))
        app.config.setdefault('MAIL_DEFAULT_SENDER', os.environ.get('MAIL_DEFAULT_SENDER', 'hr@company.com'))
        
        # Company information
        app.config.setdefault('COMPANY_NAME', os.environ.get('COMPANY_NAME', 'Your Company'))
        app.config.setdefault('COMPANY_ADDRESS', os.environ.get('COMPANY_ADDRESS', '123 Business St, City, State 12345'))
        app.config.setdefault('HR_CONTACT_EMAIL', os.environ.get('HR_CONTACT_EMAIL', 'hr@company.com'))
        app.config.setdefault('HR_CONTACT_PHONE', os.environ.get('HR_CONTACT_PHONE', '(555) 123-4567'))
        
        mail.init_app(app)
    
    def send_welcome_email(self, employee_data: Dict[str, Any], start_date: str = None) -> Dict[str, Any]:
        """Send welcome email to new employee"""
        try:
            subject = f"Welcome to {current_app.config['COMPANY_NAME']}!"
            
            # Email template
            template = """
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2c3e50;">Welcome to {{ company_name }}!</h2>
                    
                    <p>Dear {{ employee_name }},</p>
                    
                    <p>We are excited to welcome you to the {{ company_name }} team! We're thrilled to have you join us as a {{ role }} in our {{ department }} department.</p>
                    
                    {% if start_date %}
                    <p><strong>Your first day is scheduled for {{ start_date }}.</strong></p>
                    {% endif %}
                    
                    <h3 style="color: #34495e;">What to Expect on Your First Day:</h3>
                    <ul>
                        <li>Check in at the front desk at 9:00 AM</li>
                        <li>Meet with HR for orientation and paperwork</li>
                        <li>Receive your equipment and workspace assignment</li>
                        <li>Meet your team and manager</li>
                        <li>Complete initial training modules</li>
                    </ul>
                    
                    <h3 style="color: #34495e;">What to Bring:</h3>
                    <ul>
                        <li>Government-issued photo ID</li>
                        <li>Social Security card or passport</li>
                        <li>Bank account information for direct deposit</li>
                        <li>Emergency contact information</li>
                    </ul>
                    
                    <h3 style="color: #34495e;">Important Information:</h3>
                    <p><strong>Office Address:</strong><br>{{ company_address }}</p>
                    <p><strong>HR Contact:</strong><br>{{ hr_email }} | {{ hr_phone }}</p>
                    
                    <p>If you have any questions before your start date, please don't hesitate to reach out to our HR team.</p>
                    
                    <p>We look forward to working with you!</p>
                    
                    <p>Best regards,<br>
                    The {{ company_name }} HR Team</p>
                    
                    <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                    <p style="font-size: 12px; color: #666;">
                        This is an automated message from the {{ company_name }} HR system.
                    </p>
                </div>
            </body>
            </html>
            """
            
            html_content = render_template_string(template,
                company_name=current_app.config['COMPANY_NAME'],
                employee_name=employee_data['name'],
                role=employee_data['role'],
                department=employee_data['department'],
                start_date=start_date,
                company_address=current_app.config['COMPANY_ADDRESS'],
                hr_email=current_app.config['HR_CONTACT_EMAIL'],
                hr_phone=current_app.config['HR_CONTACT_PHONE']
            )
            
            return self._send_email(
                to=employee_data['email'],
                subject=subject,
                html_body=html_content
            )
            
        except Exception as e:
            logger.error(f"Error sending welcome email: {str(e)}")
            return {"success": False, "message": f"Error sending welcome email: {str(e)}"}
    
    def send_leave_approval_notification(self, employee_data: Dict[str, Any], 
                                       leave_details: Dict[str, Any]) -> Dict[str, Any]:
        """Send leave approval notification"""
        try:
            subject = f"Leave Request {'Approved' if leave_details['approved'] else 'Rejected'}"
            
            template = """
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: {% if approved %}#27ae60{% else %}#e74c3c{% endif %};">
                        Leave Request {{ status }}
                    </h2>
                    
                    <p>Dear {{ employee_name }},</p>
                    
                    <p>Your leave request has been <strong>{{ status.lower() }}</strong>.</p>
                    
                    <h3 style="color: #34495e;">Request Details:</h3>
                    <ul>
                        <li><strong>Leave Type:</strong> {{ leave_type }}</li>
                        <li><strong>Start Date:</strong> {{ start_date }}</li>
                        <li><strong>End Date:</strong> {{ end_date }}</li>
                        <li><strong>Duration:</strong> {{ duration }} days</li>
                    </ul>
                    
                    {% if approved %}
                    <p style="color: #27ae60;">Your leave has been approved. Please ensure all necessary arrangements are made before your leave begins.</p>
                    {% else %}
                    <p style="color: #e74c3c;">Unfortunately, your leave request could not be approved at this time.</p>
                    {% if reason %}
                    <p><strong>Reason:</strong> {{ reason }}</p>
                    {% endif %}
                    {% endif %}
                    
                    <p>If you have any questions, please contact your manager or HR.</p>
                    
                    <p>Best regards,<br>
                    The {{ company_name }} HR Team</p>
                </div>
            </body>
            </html>
            """
            
            html_content = render_template_string(template,
                approved=leave_details['approved'],
                status='Approved' if leave_details['approved'] else 'Rejected',
                employee_name=employee_data['name'],
                leave_type=leave_details['leave_type'],
                start_date=leave_details['start_date'],
                end_date=leave_details['end_date'],
                duration=leave_details.get('duration', 'N/A'),
                reason=leave_details.get('reason', ''),
                company_name=current_app.config['COMPANY_NAME']
            )
            
            return self._send_email(
                to=employee_data['email'],
                subject=subject,
                html_body=html_content
            )
            
        except Exception as e:
            logger.error(f"Error sending leave notification: {str(e)}")
            return {"success": False, "message": f"Error sending leave notification: {str(e)}"}
    
    def send_asset_assignment_notification(self, employee_data: Dict[str, Any], 
                                         assets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Send asset assignment notification"""
        try:
            subject = "Equipment Assignment Notification"
            
            template = """
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #3498db;">Equipment Assignment</h2>
                    
                    <p>Dear {{ employee_name }},</p>
                    
                    <p>The following equipment has been assigned to you:</p>
                    
                    <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                        <thead>
                            <tr style="background-color: #f8f9fa;">
                                <th style="border: 1px solid #dee2e6; padding: 12px; text-align: left;">Asset ID</th>
                                <th style="border: 1px solid #dee2e6; padding: 12px; text-align: left;">Type</th>
                                <th style="border: 1px solid #dee2e6; padding: 12px; text-align: left;">Model</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for asset in assets %}
                            <tr>
                                <td style="border: 1px solid #dee2e6; padding: 12px;">{{ asset.asset_id }}</td>
                                <td style="border: 1px solid #dee2e6; padding: 12px;">{{ asset.asset_type }}</td>
                                <td style="border: 1px solid #dee2e6; padding: 12px;">{{ asset.model or 'N/A' }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                    
                    <h3 style="color: #34495e;">Important Reminders:</h3>
                    <ul>
                        <li>You are responsible for the care and security of assigned equipment</li>
                        <li>Report any damage or issues immediately to IT support</li>
                        <li>Equipment must be returned upon termination of employment</li>
                        <li>Personal use of company equipment should follow company policy</li>
                    </ul>
                    
                    <p>If you have any questions about your assigned equipment, please contact IT support.</p>
                    
                    <p>Best regards,<br>
                    The {{ company_name }} IT Team</p>
                </div>
            </body>
            </html>
            """
            
            html_content = render_template_string(template,
                employee_name=employee_data['name'],
                assets=assets,
                company_name=current_app.config['COMPANY_NAME']
            )
            
            return self._send_email(
                to=employee_data['email'],
                subject=subject,
                html_body=html_content
            )
            
        except Exception as e:
            logger.error(f"Error sending asset notification: {str(e)}")
            return {"success": False, "message": f"Error sending asset notification: {str(e)}"}
    
    def send_onboarding_task_notification(self, assignee_email: str, employee_data: Dict[str, Any], 
                                        tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Send onboarding task notification to task assignees"""
        try:
            subject = f"Onboarding Tasks - New Employee: {employee_data['name']}"
            
            template = """
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2c3e50;">Onboarding Tasks Assigned</h2>
                    
                    <p>You have been assigned onboarding tasks for new employee <strong>{{ employee_name }}</strong>.</p>
                    
                    <h3 style="color: #34495e;">Employee Information:</h3>
                    <ul>
                        <li><strong>Name:</strong> {{ employee_name }}</li>
                        <li><strong>Employee ID:</strong> {{ employee_id }}</li>
                        <li><strong>Role:</strong> {{ role }}</li>
                        <li><strong>Department:</strong> {{ department }}</li>
                        <li><strong>Start Date:</strong> {{ start_date }}</li>
                    </ul>
                    
                    <h3 style="color: #34495e;">Your Assigned Tasks:</h3>
                    <ul>
                        {% for task in tasks %}
                        <li><strong>{{ task.title }}</strong> - Due: {{ task.due_date }}</li>
                        {% endfor %}
                    </ul>
                    
                    <p>Please complete these tasks by their due dates to ensure a smooth onboarding experience.</p>
                    
                    <p>Best regards,<br>
                    The {{ company_name }} HR Team</p>
                </div>
            </body>
            </html>
            """
            
            html_content = render_template_string(template,
                employee_name=employee_data['name'],
                employee_id=employee_data['employee_id'],
                role=employee_data['role'],
                department=employee_data['department'],
                start_date=employee_data.get('start_date', 'TBD'),
                tasks=tasks,
                company_name=current_app.config['COMPANY_NAME']
            )
            
            return self._send_email(
                to=assignee_email,
                subject=subject,
                html_body=html_content
            )
            
        except Exception as e:
            logger.error(f"Error sending onboarding task notification: {str(e)}")
            return {"success": False, "message": f"Error sending onboarding task notification: {str(e)}"}
    
    def send_offboarding_notification(self, manager_email: str, employee_data: Dict[str, Any], 
                                    termination_date: str, reason: str) -> Dict[str, Any]:
        """Send offboarding notification to manager"""
        try:
            subject = f"Employee Departure Notification - {employee_data['name']}"
            
            template = """
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #e74c3c;">Employee Departure Notification</h2>
                    
                    <p>This is to inform you that <strong>{{ employee_name }}</strong> will be leaving the company.</p>
                    
                    <h3 style="color: #34495e;">Departure Details:</h3>
                    <ul>
                        <li><strong>Employee:</strong> {{ employee_name }} ({{ employee_id }})</li>
                        <li><strong>Role:</strong> {{ role }}</li>
                        <li><strong>Department:</strong> {{ department }}</li>
                        <li><strong>Last Working Day:</strong> {{ termination_date }}</li>
                        <li><strong>Reason:</strong> {{ reason }}</li>
                    </ul>
                    
                    <h3 style="color: #34495e;">Action Required:</h3>
                    <ul>
                        <li>Plan knowledge transfer sessions</li>
                        <li>Reassign ongoing projects and responsibilities</li>
                        <li>Update team on transition plans</li>
                        <li>Coordinate with HR for exit interview</li>
                    </ul>
                    
                    <p>Please contact HR if you have any questions about the offboarding process.</p>
                    
                    <p>Best regards,<br>
                    The {{ company_name }} HR Team</p>
                </div>
            </body>
            </html>
            """
            
            html_content = render_template_string(template,
                employee_name=employee_data['name'],
                employee_id=employee_data['employee_id'],
                role=employee_data['role'],
                department=employee_data['department'],
                termination_date=termination_date,
                reason=reason,
                company_name=current_app.config['COMPANY_NAME']
            )
            
            return self._send_email(
                to=manager_email,
                subject=subject,
                html_body=html_content
            )
            
        except Exception as e:
            logger.error(f"Error sending offboarding notification: {str(e)}")
            return {"success": False, "message": f"Error sending offboarding notification: {str(e)}"}
    
    def _send_email(self, to: str, subject: str, html_body: str, 
                   text_body: str = None, attachments: List[str] = None) -> Dict[str, Any]:
        """Send email using Flask-Mail"""
        try:
            msg = Message(
                subject=subject,
                recipients=[to] if isinstance(to, str) else to,
                html=html_body,
                body=text_body
            )
            
            # Add attachments if provided
            if attachments:
                for attachment_path in attachments:
                    if os.path.exists(attachment_path):
                        with current_app.open_resource(attachment_path) as fp:
                            msg.attach(
                                filename=os.path.basename(attachment_path),
                                content_type="application/octet-stream",
                                data=fp.read()
                            )
            
            mail.send(msg)
            
            logger.info(f"Email sent successfully to {to}: {subject}")
            
            return {
                "success": True,
                "message": "Email sent successfully",
                "recipient": to,
                "subject": subject,
                "sent_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error sending email to {to}: {str(e)}")
            return {
                "success": False,
                "message": f"Error sending email: {str(e)}",
                "recipient": to,
                "subject": subject
            }


# Initialize email service
email_service = EmailService()
