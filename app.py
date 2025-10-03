import os
import csv
import logging
import secrets
from datetime import datetime, timedelta
from io import StringIO, BytesIO
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('incident_reports.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-this')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///incidents.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Email configuration
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', '')
app.config['MAIL_RECIPIENTS'] = os.getenv('MAIL_RECIPIENTS', '')

db = SQLAlchemy(app)
mail = Mail(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'

# Permission Decorators
def master_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('admin_login'))
        if not current_user.can_manage_users():
            flash('Access denied. Master admin privileges required.', 'error')
            return redirect(url_for('admin_dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def incident_manager_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('admin_login'))
        if not current_user.can_manage_incidents():
            flash('Access denied. Incident manager privileges required.', 'error')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def email_config_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('admin_login'))
        if not current_user.can_manage_email_config():
            flash('Access denied. Master admin privileges required for email configuration.', 'error')
            return redirect(url_for('admin_dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    must_change_password = db.Column(db.Boolean, default=False)
    role = db.Column(db.String(20), default='incident_manager')  # 'master_admin' or 'incident_manager'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_master_admin(self):
        return self.role == 'master_admin'

    def is_incident_manager(self):
        return self.role == 'incident_manager'

    def can_manage_users(self):
        return self.is_master_admin()

    def can_manage_email_config(self):
        return self.is_master_admin()

    def can_view_dashboard(self):
        return self.is_master_admin() or self.is_incident_manager()

    def can_manage_incidents(self):
        return self.is_master_admin() or self.is_incident_manager()

    def __repr__(self):
        return f'<User {self.username}>'

class PasswordResetToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def is_valid(self):
        return not self.used and datetime.utcnow() < self.expires_at

    def __repr__(self):
        return f'<PasswordResetToken {self.token}>'

class Incident(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Reporter information (all optional)
    reporter_name = db.Column(db.String(100), default='Anonymous')
    reporter_job_title = db.Column(db.String(100), nullable=True)
    reporter_email = db.Column(db.String(120), nullable=True)
    reporter_phone = db.Column(db.String(20), nullable=True)
    # Incident details
    incident_datetime = db.Column(db.DateTime, nullable=False)
    incident_type = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    # Legacy field for compatibility (will be removed in future)
    description = db.Column(db.Text, nullable=False)
    # Detailed incident information
    incident_description = db.Column(db.Text, nullable=False)  # What happened and how it started
    persons_involved = db.Column(db.Text, nullable=False)  # Names, job titles, identifiers of those involved
    threats_weapons = db.Column(db.Text, nullable=True)  # Nature of threats, physical acts, or weapons used
    medical_treatment = db.Column(db.Text, nullable=True)  # Whether medical treatment was needed
    law_enforcement = db.Column(db.Text, nullable=True)  # Whether law enforcement was contacted (legacy combined field)
    law_enforcement_contacted = db.Column(db.String(10), nullable=True)  # Yes/No for law enforcement contact
    police_report_id = db.Column(db.String(50), nullable=True)  # Police Report ID if applicable
    security_intervention = db.Column(db.Text, nullable=True)  # Whether security or other intervention was required
    incident_response = db.Column(db.Text, nullable=True)  # How incident was responded to (de-escalation, first aid, etc.)
    contributing_factors = db.Column(db.Text, nullable=True)  # Contributing factors (environmental, organizational, procedural)
    corrective_actions = db.Column(db.Text, nullable=True)  # Corrective actions taken or recommended
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'reporter_name': self.reporter_name,
            'reporter_job_title': self.reporter_job_title,
            'reporter_email': self.reporter_email,
            'reporter_phone': self.reporter_phone,
            'incident_datetime': self.incident_datetime.strftime('%Y-%m-%d %H:%M'),
            'incident_type': self.incident_type,
            'location': self.location,
            'incident_description': self.incident_description,
            'persons_involved': self.persons_involved,
            'threats_weapons': self.threats_weapons,
            'medical_treatment': self.medical_treatment,
            'law_enforcement': self.law_enforcement,
            'security_intervention': self.security_intervention,
            'incident_response': self.incident_response,
            'contributing_factors': self.contributing_factors,
            'corrective_actions': self.corrective_actions,
            'submitted_at': self.submitted_at.strftime('%Y-%m-%d %H:%M')
        }

class EmailConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mail_server = db.Column(db.String(100), nullable=False, default='smtp.gmail.com')
    mail_port = db.Column(db.Integer, nullable=False, default=587)
    mail_use_tls = db.Column(db.Boolean, nullable=False, default=True)
    mail_username = db.Column(db.String(120), nullable=False)
    mail_password = db.Column(db.String(120), nullable=False)
    mail_default_sender = db.Column(db.String(120), nullable=False)
    mail_recipients = db.Column(db.Text, nullable=False)  # Comma-separated list
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_recipients_list(self):
        """Convert comma-separated recipients string to list"""
        if not self.mail_recipients:
            return []
        return [email.strip() for email in self.mail_recipients.split(',') if email.strip()]

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Helper Functions
def send_corrective_actions_notification(incident, action_type="updated"):
    """Send email notification when corrective actions are modified"""
    try:
        email_config = EmailConfig.query.first()
        
        if not email_config or not email_config.is_active:
            logger.warning("Email configuration not active, skipping corrective actions notification")
            return False
        
        # Create a new Mail instance with current config
        notification_mail = Mail(app)
        
        # Update Flask-Mail configuration with database values
        app.config['MAIL_SERVER'] = email_config.mail_server
        app.config['MAIL_PORT'] = email_config.mail_port
        app.config['MAIL_USE_TLS'] = email_config.mail_use_tls
        app.config['MAIL_USERNAME'] = email_config.mail_username
        app.config['MAIL_PASSWORD'] = email_config.mail_password
        
        # Create new Mail instance with updated config
        notification_mail = Mail(app)
        
        # Prepare email content
        subject = f"Corrective Actions {action_type.title()} - Incident #{incident.id}"
        
        body = f"""A new Work Place Incident corrective actions have been {action_type}.

Incident Details:
- Incident ID: #{incident.id}
- Incident Type: {incident.incident_type}
- Submitted: {incident.submitted_at.strftime('%Y-%m-%d %H:%M:%S')}
- Reporter: {incident.reporter_name or 'Anonymous'}

Corrective Actions:
{incident.corrective_actions or 'No corrective actions specified'}

Please follow the link below to see the full report.
Note: if you are outside the office you will need to be connected via VPN to see the report.

Link: {request.url_root}admin/login
"""
        
        msg = Message(
            subject=subject,
            recipients=[email_config.admin_email],
            body=body,
            sender=email_config.mail_username
        )
        
        notification_mail.send(msg)
        logger.info(f"Corrective actions notification email sent to {email_config.admin_email} for incident #{incident.id}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending corrective actions notification email: {str(e)}")
        return False

def send_reporter_corrective_actions_notification(incident):
    """Send email notification to reporter when corrective actions are updated"""
    try:
        email_config = EmailConfig.query.first()
        
        if not email_config or not email_config.is_active:
            logger.warning("Email configuration not active, skipping reporter notification")
            return False
        
        if not incident.reporter_email:
            logger.warning("No reporter email available for notification")
            return False
        
        # Create a new Mail instance with current config
        reporter_mail = Mail(app)
        
        # Update Flask-Mail configuration with database values
        app.config['MAIL_SERVER'] = email_config.mail_server
        app.config['MAIL_PORT'] = email_config.mail_port
        app.config['MAIL_USE_TLS'] = email_config.mail_use_tls
        app.config['MAIL_USERNAME'] = email_config.mail_username
        app.config['MAIL_PASSWORD'] = email_config.mail_password
        
        # Create new Mail instance with updated config
        reporter_mail = Mail(app)
        
        # Prepare email content
        subject = f"Corrective Actions Update - Incident #{incident.id}"
        
        body = f"""Dear {incident.reporter_name or 'Reporter'},

We wanted to inform you that corrective actions have been updated for the incident you reported.

Incident Details:
- Incident ID: #{incident.id}
- Incident Type: {incident.incident_type}
- Submitted: {incident.submitted_at.strftime('%Y-%m-%d %H:%M:%S')}

Corrective Actions:
{incident.corrective_actions or 'No corrective actions specified'}

Thank you for reporting this incident. Your report helps us maintain a safe workplace environment.

If you have any questions or additional information about this incident, please contact your supervisor or the appropriate department.

Best regards,
Work Place Violence Reporting Team
Architectural Nexus
"""
        
        msg = Message(
            subject=subject,
            recipients=[incident.reporter_email],
            body=body,
            sender=email_config.mail_username
        )
        
        reporter_mail.send(msg)
        logger.info(f"Reporter notification email sent to {incident.reporter_email} for incident #{incident.id}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending reporter notification email: {str(e)}")
        return False

def send_incident_notification(incident, reporter_email=None):
    """Send email notification when an incident is reported"""
    try:
        email_config = EmailConfig.query.first()
        
        if not email_config or not email_config.is_active:
            logger.info("Email notifications disabled or not configured")
            return False
        
        # Update Flask-Mail config with database values
        app.config['MAIL_SERVER'] = email_config.mail_server
        app.config['MAIL_PORT'] = email_config.mail_port
        app.config['MAIL_USE_TLS'] = email_config.mail_use_tls
        app.config['MAIL_USERNAME'] = email_config.mail_username
        app.config['MAIL_PASSWORD'] = email_config.mail_password
        app.config['MAIL_DEFAULT_SENDER'] = email_config.mail_default_sender
        
        # Create new Mail instance with updated config
        notification_mail = Mail(app)
        
        # Format incident datetime
        incident_datetime_str = incident.incident_datetime.strftime('%B %d, %Y at %I:%M %p')
        
        # Create email message for administrators
        msg = Message(
            subject='Notice: A Work Place Incident Has Been Reported',
            sender=email_config.mail_default_sender,
            recipients=email_config.get_recipients_list()
        )
        
        # Email body
        msg.body = f"""A new Work Place Incident has been reported. Please follow the link below to see the report. Note: if you are outside the office you will need to be connected via VPN to see the report.

Incident ID: #{incident.id}
Reported By: {incident.reporter_name}
Date/Time: {incident_datetime_str}
Type: {incident.incident_type}
Location: {incident.location}

To view the full incident report, please log in to the admin dashboard:
http://localhost:5002/admin/login

Submitted: {incident.submitted_at.strftime('%B %d, %Y at %I:%M %p')}

---
This is an automated notification from the Work Place Violence Reporting Server.
        """
        
        # Send notification email to administrators
        notification_mail.send(msg)
        logger.info(f"Incident notification email sent for incident #{incident.id}")
        
        # If reporter email is provided, send confirmation email to reporter
        if reporter_email:
            confirmation_msg = Message(
                subject='Incident Report Confirmation',
                sender=email_config.mail_default_sender,
                recipients=[reporter_email]
            )
            
            # Determine if this was submitted anonymously
            is_anonymous = incident.reporter_email is None
            
            if is_anonymous:
                confirmation_msg.body = f"""Your incident report has been submitted successfully.

Incident ID: #{incident.id}
Date/Time: {incident_datetime_str}
Type: {incident.incident_type}
Location: {incident.location}

• Your contact information was not recorded because you chose to submit the form anonymously.
• Because you chose to submit the form anonymously, Management at Architectural Nexus will not have any way to get in touch with you.

Submitted: {incident.submitted_at.strftime('%B %d, %Y at %I:%M %p')}

---
This is an automated confirmation from the Work Place Violence Reporting Server.
                """
            else:
                confirmation_msg.body = f"""Thank you for reporting the workplace incident. Your report has been received and will be reviewed by the appropriate personnel.

Incident ID: #{incident.id}
Date/Time: {incident_datetime_str}
Type: {incident.incident_type}
Location: {incident.location}

Your contact information has been recorded with the incident report for follow-up purposes.

Submitted: {incident.submitted_at.strftime('%B %d, %Y at %I:%M %p')}

---
This is an automated confirmation from the Work Place Violence Reporting Server.
                """
            
            notification_mail.send(confirmation_msg)
            logger.info(f"Confirmation email sent to reporter: {reporter_email}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error sending email notification for incident #{incident.id}: {str(e)}")
        return False

def generate_password_reset_token(user):
    """Generate a secure password reset token for a user"""
    # Generate a secure random token
    token = secrets.token_urlsafe(32)
    
    # Set expiration time (1 hour from now)
    expires_at = datetime.utcnow() + timedelta(hours=1)
    
    # Create the token record
    reset_token = PasswordResetToken(
        user_id=user.id,
        token=token,
        expires_at=expires_at
    )
    
    # Invalidate any existing tokens for this user
    PasswordResetToken.query.filter_by(user_id=user.id, used=False).update({'used': True})
    
    # Save the new token
    db.session.add(reset_token)
    db.session.commit()
    
    return token

def send_password_reset_email(user, token):
    """Send password reset email to user"""
    try:
        email_config = EmailConfig.query.first()
        
        if not email_config or not email_config.is_active:
            logger.info("Email notifications disabled or not configured")
            return False
        
        # Update Flask-Mail config with database values
        app.config['MAIL_SERVER'] = email_config.mail_server
        app.config['MAIL_PORT'] = email_config.mail_port
        app.config['MAIL_USE_TLS'] = email_config.mail_use_tls
        app.config['MAIL_USERNAME'] = email_config.mail_username
        app.config['MAIL_PASSWORD'] = email_config.mail_password
        app.config['MAIL_DEFAULT_SENDER'] = email_config.mail_default_sender
        
        # Create new Mail instance with updated config
        reset_mail = Mail(app)
        
        # Create reset URL
        reset_url = f"http://localhost:5002/admin/reset-password/{token}"
        
        # Create email message
        msg = Message(
            subject='Password Reset Request - Incident Reporting System',
            sender=email_config.mail_default_sender,
            recipients=[user.email]
        )
        
        msg.body = f"""Hello {user.username},

You have requested a password reset for your Incident Reporting System admin account.

To reset your password, please click the link below:
{reset_url}

This link will expire in 1 hour for security reasons.

If you did not request this password reset, please ignore this email and your password will remain unchanged.

---
This is an automated message from the Work Place Violence Reporting Server.
        """
        
        reset_mail.send(msg)
        logger.info(f"Password reset email sent to {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending password reset email to {user.email}: {str(e)}")
        return False

def generate_temporary_password():
    """Generate a secure temporary password"""
    # Generate a password with letters, numbers, and special characters
    import string
    import random
    
    # Use a mix of characters for security
    chars = string.ascii_letters + string.digits + "!@#$%"
    password = ''.join(random.choice(chars) for _ in range(12))
    
    # Ensure it has at least one of each type
    if not any(c.islower() for c in password):
        password = password[:-1] + random.choice(string.ascii_lowercase)
    if not any(c.isupper() for c in password):
        password = password[:-1] + random.choice(string.ascii_uppercase)
    if not any(c.isdigit() for c in password):
        password = password[:-1] + random.choice(string.digits)
    
    return password

def send_welcome_email(user, temporary_password):
    """Send welcome email to new user with credentials"""
    try:
        email_config = EmailConfig.query.first()
        
        if not email_config or not email_config.is_active:
            logger.info("Email notifications disabled or not configured")
            return False
        
        # Update Flask-Mail config with database values
        app.config['MAIL_SERVER'] = email_config.mail_server
        app.config['MAIL_PORT'] = email_config.mail_port
        app.config['MAIL_USE_TLS'] = email_config.mail_use_tls
        app.config['MAIL_USERNAME'] = email_config.mail_username
        app.config['MAIL_PASSWORD'] = email_config.mail_password
        app.config['MAIL_DEFAULT_SENDER'] = email_config.mail_default_sender
        
        # Create new Mail instance with updated config
        welcome_mail = Mail(app)
        
        # Create login URL
        login_url = "http://localhost:5002/admin/login"
        
        # Create email message
        msg = Message(
            subject='Welcome to Incident Reporting System - Your Account Has Been Created',
            sender=email_config.mail_default_sender,
            recipients=[user.email]
        )
        
        msg.body = f"""Hello {user.username},

Welcome to the Incident Reporting System! Your admin account has been created.

Your login credentials:
Username: {user.username}
Temporary Password: {temporary_password}

To access the system:
1. Go to: {login_url}
2. Log in with your username and temporary password
3. You will be required to change your password on first login

Important Security Notes:
• This is a temporary password that must be changed on first login
• Keep your login credentials secure
• Do not share your password with others
• Contact your administrator if you have any issues

The Incident Reporting System allows you to:
• View and manage incident reports
• Export reports to PDF and CSV
• Manage other admin users
• Configure email settings

If you did not expect this account creation, please contact your administrator immediately.

---
This is an automated message from the Work Place Violence Reporting Server.
        """
        
        welcome_mail.send(msg)
        logger.info(f"Welcome email sent to {user.email} for user: {user.username}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending welcome email to {user.email}: {str(e)}")
        return False

# Routes
@app.route('/')
def index():
    """Main incident reporting form page"""
    return render_template('index.html')

@app.route('/submit_incident', methods=['POST'])
def submit_incident():
    """Handle incident form submission"""
    try:
        # Get reporter information (all optional)
        reporter_name = request.form.get('reporter_name', '').strip()
        if not reporter_name:
            reporter_name = 'Anonymous'
        reporter_job_title = request.form.get('reporter_job_title', '').strip() or None
        reporter_email = request.form.get('reporter_email', '').strip() or None
        reporter_phone = request.form.get('reporter_phone', '').strip() or None
        remain_anonymous = request.form.get('remain_anonymous') == 'on'
        
        # If user wants to remain anonymous, don't store their email in the database
        # but keep it for sending confirmation email
        confirmation_email = reporter_email  # Always keep email for confirmation if provided
        if remain_anonymous:
            reporter_email = None  # Don't store in database
        
        # Get incident details
        incident_datetime_str = request.form.get('incident_datetime')
        incident_type = request.form.get('incident_type', '').strip()
        location = request.form.get('location', '').strip()
        incident_description = request.form.get('incident_description', '').strip()
        persons_involved = request.form.get('persons_involved', '').strip()
        threats_weapons = request.form.get('threats_weapons', '').strip() or None
        medical_treatment = request.form.get('medical_treatment', '').strip() or None
        law_enforcement_contacted = request.form.get('law_enforcement_contacted', '').strip() or None
        police_report_id = request.form.get('police_report_id', '').strip() or None
        
        # Combine law enforcement data
        law_enforcement = None
        if law_enforcement_contacted:
            if law_enforcement_contacted == 'Yes' and police_report_id:
                law_enforcement = f"Yes - Police Report ID: {police_report_id}"
            elif law_enforcement_contacted == 'Yes':
                law_enforcement = "Yes - No Police Report ID provided"
            else:
                law_enforcement = "No"
        security_intervention = request.form.get('security_intervention', '').strip() or None
        incident_response = request.form.get('incident_response', '').strip() or None
        contributing_factors = request.form.get('contributing_factors', '').strip() or None

        # Validate required fields
        if not incident_datetime_str or not incident_type or not location or not incident_description or not persons_involved:
            return jsonify({'success': False, 'message': 'All required fields must be filled out'}), 400

        # Validate incident type
        valid_types = ['Type 1 – Criminal Intent', 'Type 2 – Customer / Client / Patient', 'Type 3 – Worker-on-Worker', 'Type 4 – Personal Relationship']
        if incident_type not in valid_types:
            return jsonify({'success': False, 'message': 'Invalid incident type selected'}), 400

        # Parse datetime
        try:
            incident_datetime = datetime.fromisoformat(incident_datetime_str.replace('T', ' '))
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid date/time format'}), 400

        # Create and save incident
        incident = Incident(
            reporter_name=reporter_name,
            reporter_job_title=reporter_job_title,
            reporter_email=reporter_email,
            reporter_phone=reporter_phone,
            incident_datetime=incident_datetime,
            incident_type=incident_type,
            location=location,
            description=incident_description,  # Populate old field for compatibility
            incident_description=incident_description,
            persons_involved=persons_involved,
            threats_weapons=threats_weapons,
            medical_treatment=medical_treatment,
            law_enforcement=law_enforcement,  # Combined field for compatibility
            law_enforcement_contacted=law_enforcement_contacted,  # Individual field
            police_report_id=police_report_id,  # Individual field
            security_intervention=security_intervention,
            incident_response=incident_response,
            contributing_factors=contributing_factors
        )
        
        # Save incident to database first
        db.session.add(incident)
        db.session.commit()

        logger.info(f"New incident reported: ID={incident.id}, Location={location}, Reporter={reporter_name}")
        
        # Send email notification after successful database save
        email_sent = send_incident_notification(incident, confirmation_email)
        if email_sent:
            logger.info(f"Email notification sent for incident #{incident.id}")
        else:
            logger.warning(f"Failed to send email notification for incident #{incident.id}")
        
        return jsonify({'success': True, 'message': 'Incident report submitted successfully and email notification sent'})

    except Exception as e:
        logger.error(f"Error submitting incident: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'An error occurred while submitting the report'}), 500

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username, is_active=True).first()
        
        if user and user.check_password(password):
            login_user(user)
            logger.info(f"Admin login successful: {username}")
            
            # Check if user must change password
            if user.must_change_password:
                return redirect(url_for('change_password_required'))
            
            return redirect(url_for('admin_dashboard'))
        else:
            logger.warning(f"Failed login attempt for username: {username}")
            flash('Invalid username or password')
    
    return render_template('admin_login.html')

@app.route('/admin/change-password-required', methods=['GET', 'POST'])
@login_required
def change_password_required():
    """Force password change for new users"""
    if request.method == 'POST':
        new_password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not new_password or len(new_password) < 6:
            flash('Password must be at least 6 characters long')
            return render_template('change_password_required.html')
        
        if new_password != confirm_password:
            flash('Passwords do not match')
            return render_template('change_password_required.html')
        
        # Update user password and clear must_change_password flag
        current_user.set_password(new_password)
        current_user.must_change_password = False
        db.session.commit()
        
        logger.info(f"User {current_user.username} changed password successfully")
        flash('Password changed successfully! You can now access the system.')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('change_password_required.html')

@app.route('/admin/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Handle password reset requests"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        
        if not username:
            flash('Please enter your username')
            return render_template('forgot_password.html')
        
        user = User.query.filter_by(username=username, is_active=True).first()
        
        if user and user.email:
            # Generate reset token
            token = generate_password_reset_token(user)
            
            # Send reset email
            if send_password_reset_email(user, token):
                flash('Password reset instructions have been sent to your email address.')
                logger.info(f"Password reset requested for user: {username}")
            else:
                flash('Failed to send password reset email. Please contact your administrator.')
                logger.error(f"Failed to send password reset email for user: {username}")
        else:
            # Don't reveal whether user exists or has email
            flash('If an account with that username exists and has an email address, password reset instructions have been sent.')
            logger.info(f"Password reset requested for non-existent user or user without email: {username}")
        
        return redirect(url_for('admin_login'))
    
    return render_template('forgot_password.html')

@app.route('/admin/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Handle password reset with token"""
    reset_token = PasswordResetToken.query.filter_by(token=token).first()
    
    if not reset_token or not reset_token.is_valid():
        flash('Invalid or expired password reset link.')
        return redirect(url_for('admin_login'))
    
    user = User.query.get(reset_token.user_id)
    
    if request.method == 'POST':
        new_password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        if not new_password:
            flash('Please enter a new password')
            return render_template('reset_password.html', token=token)
        
        if new_password != confirm_password:
            flash('Passwords do not match')
            return render_template('reset_password.html', token=token)
        
        if len(new_password) < 6:
            flash('Password must be at least 6 characters long')
            return render_template('reset_password.html', token=token)
        
        # Update password
        user.set_password(new_password)
        
        # Mark token as used
        reset_token.used = True
        
        db.session.commit()
        
        flash('Your password has been reset successfully. Please log in with your new password.')
        logger.info(f"Password reset completed for user: {user.username}")
        
        return redirect(url_for('admin_login'))
    
    return render_template('reset_password.html', token=token)

@app.route('/admin/logout')
@login_required
def admin_logout():
    """Admin logout"""
    logger.info(f"Admin logout: {current_user.username}")
    logout_user()
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
@incident_manager_required
def admin_dashboard():
    """Admin dashboard to view incidents"""
    return render_template('admin_dashboard.html')

@app.route('/admin/incidents')
@incident_manager_required
def get_incidents():
    """API endpoint to get incidents with filtering and sorting"""
    try:
        # Get query parameters
        search = request.args.get('search', '').strip()
        start_date = request.args.get('start_date', '').strip()
        end_date = request.args.get('end_date', '').strip()
        sort_by = request.args.get('sort_by', 'submitted_at')
        sort_order = request.args.get('sort_order', 'desc')
        
        # Build query
        query = Incident.query
        
        # Apply search filter
        if search:
            query = query.filter(
                db.or_(
                    Incident.reporter_name.ilike(f'%{search}%'),
                    Incident.reporter_job_title.ilike(f'%{search}%'),
                    Incident.reporter_email.ilike(f'%{search}%'),
                    Incident.incident_type.ilike(f'%{search}%'),
                    Incident.location.ilike(f'%{search}%'),
                    Incident.incident_description.ilike(f'%{search}%'),
                    Incident.persons_involved.ilike(f'%{search}%'),
                    Incident.threats_weapons.ilike(f'%{search}%'),
                    Incident.medical_treatment.ilike(f'%{search}%'),
                    Incident.law_enforcement.ilike(f'%{search}%'),
                    Incident.security_intervention.ilike(f'%{search}%'),
                    Incident.incident_response.ilike(f'%{search}%'),
                    Incident.contributing_factors.ilike(f'%{search}%'),
                    Incident.corrective_actions.ilike(f'%{search}%')
                )
            )
        
        # Apply date filters
        if start_date:
            try:
                start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(Incident.incident_datetime >= start_datetime)
            except ValueError:
                logger.warning(f"Invalid start_date format: {start_date}")
        
        if end_date:
            try:
                end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
                # Add one day to include the entire end date
                end_datetime = end_datetime.replace(hour=23, minute=59, second=59)
                query = query.filter(Incident.incident_datetime <= end_datetime)
            except ValueError:
                logger.warning(f"Invalid end_date format: {end_date}")
        
        # Apply sorting
        if hasattr(Incident, sort_by):
            sort_column = getattr(Incident, sort_by)
            if sort_order == 'desc':
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())
        
        incidents = query.all()
        
        logger.info(f"Admin {current_user.username} retrieved {len(incidents)} incidents")
        
        return jsonify({
            'success': True,
            'incidents': [incident.to_dict() for incident in incidents]
        })
        
    except Exception as e:
        logger.error(f"Error retrieving incidents: {str(e)}")
        return jsonify({'success': False, 'message': 'Error retrieving incidents'}), 500

@app.route('/admin/export')
@incident_manager_required
def export_incidents():
    """Export incidents to CSV"""
    try:
        logger.info(f"Starting CSV export for admin {current_user.username}")
        
        # Get all incidents
        incidents = Incident.query.order_by(Incident.submitted_at.desc()).all()
        logger.info(f"Found {len(incidents)} incidents to export")
        
        # Create CSV data
        output = StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)
        
        # Write header
        writer.writerow([
            'ID', 'Reporter Name', 'Job Title', 'Email', 'Phone', 
            'Incident Date/Time', 'Incident Type', 'Location', 
            'Incident Description', 'Persons Involved', 'Threats/Weapons', 
            'Medical Treatment', 'Law Enforcement', 'Security Intervention',
            'Incident Response', 'Contributing Factors', 'Corrective Actions', 'Submitted At'
        ])
        
        # Write data
        for incident in incidents:
            try:
                writer.writerow([
                    incident.id,
                    incident.reporter_name or 'Anonymous',
                    incident.reporter_job_title or '',
                    incident.reporter_email or '',
                    incident.reporter_phone or '',
                    incident.incident_datetime.strftime('%Y-%m-%d %H:%M') if incident.incident_datetime else '',
                    incident.incident_type or '',
                    incident.location or '',
                    incident.incident_description or '',
                    incident.persons_involved or '',
                    incident.threats_weapons or '',
                    incident.medical_treatment or '',
                    incident.law_enforcement or '',
                    incident.security_intervention or '',
                    incident.incident_response or '',
                    incident.contributing_factors or '',
                    incident.corrective_actions or '',
                    incident.submitted_at.strftime('%Y-%m-%d %H:%M') if incident.submitted_at else ''
                ])
            except Exception as row_error:
                logger.error(f"Error writing incident {incident.id}: {str(row_error)}")
                # Write a placeholder row for failed incidents
                writer.writerow([
                    incident.id,
                    'ERROR',
                    'ERROR',
                    'ERROR',
                    'ERROR',
                    'ERROR',
                    'ERROR',
                    'ERROR',
                    'ERROR',
                    'ERROR',
                    'ERROR',
                    'ERROR',
                    'ERROR',
                    'ERROR',
                    'ERROR',
                    'ERROR',
                    'ERROR',
                    'ERROR'
                ])
        
        output.seek(0)
        csv_content = output.getvalue()
        logger.info(f"CSV content generated, size: {len(csv_content)} characters")
        
        logger.info(f"Admin {current_user.username} exported {len(incidents)} incidents to CSV")
        
        # Create a BytesIO object for the response (send_file requires binary data)
        response_io = BytesIO(csv_content.encode('utf-8'))
        response_io.seek(0)
        
        # Add headers to ensure proper download
        response = send_file(
            response_io,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'incident_reports_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
        response.headers['Content-Disposition'] = f'attachment; filename=incident_reports_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        return response
        
    except Exception as e:
        logger.error(f"Error exporting incidents: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        flash('Error exporting incidents')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/users')
@master_admin_required
def admin_users():
    """Admin users management page"""
    users = User.query.all()
    return render_template('admin_users.html', users=users)

@app.route('/admin/users/add', methods=['POST'])
@master_admin_required
def add_user():
    """Add new admin user"""
    try:
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip() or None
        role = request.form.get('role', 'incident_manager').strip()

        if not username:
            flash('Username is required')
            return redirect(url_for('admin_users'))

        if not email:
            flash('Email address is required for new users')
            return redirect(url_for('admin_users'))

        if role not in ['master_admin', 'incident_manager']:
            flash('Invalid role selected')
            return redirect(url_for('admin_users'))

        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('admin_users'))

        if User.query.filter_by(email=email).first():
            flash('Email address already exists')
            return redirect(url_for('admin_users'))

        # Generate temporary password
        temporary_password = generate_temporary_password()
        
        # Create user with temporary password and must_change_password flag
        user = User(username=username, email=email, role=role, must_change_password=True)
        user.set_password(temporary_password)
        db.session.add(user)
        db.session.commit()

        # Send welcome email
        email_sent = send_welcome_email(user, temporary_password)
        
        if email_sent:
            logger.info(f"Admin {current_user.username} added new user: {username} with welcome email sent")
            flash(f'User {username} added successfully. Welcome email sent to {email}')
        else:
            logger.warning(f"Admin {current_user.username} added new user: {username} but welcome email failed to send")
            flash(f'User {username} added successfully, but welcome email could not be sent. Please contact the user directly.')

    except Exception as e:
        logger.error(f"Error adding user: {str(e)}")
        db.session.rollback()
        flash('An error occurred while adding the user')
    
    return redirect(url_for('admin_users'))

@app.route('/admin/users/<int:user_id>/toggle', methods=['POST'])
@master_admin_required
def toggle_user(user_id):
    """Toggle user active status"""
    try:
        user = User.query.get_or_404(user_id)
        
        # Prevent deactivating self
        if user.id == current_user.id:
            flash('Cannot deactivate your own account')
            return redirect(url_for('admin_users'))
        
        user.is_active = not user.is_active
        db.session.commit()
        
        status = 'activated' if user.is_active else 'deactivated'
        logger.info(f"Admin {current_user.username} {status} user: {user.username}")
        flash(f'User {status} successfully')
        
    except Exception as e:
        logger.error(f"Error toggling user: {str(e)}")
        db.session.rollback()
        flash('Error updating user')
    
    return redirect(url_for('admin_users'))

@app.route('/admin/users/<int:user_id>/change-password', methods=['POST'])
@master_admin_required
def change_user_password(user_id):
    """Change user password"""
    try:
        user = User.query.get_or_404(user_id)
        
        # Prevent changing own password through this route
        if user.id == current_user.id:
            return jsonify({'success': False, 'message': 'Cannot change your own password through this interface'}), 400
        
        data = request.get_json()
        new_password = data.get('new_password', '').strip()
        
        if not new_password:
            return jsonify({'success': False, 'message': 'New password is required'}), 400
        
        if len(new_password) < 6:
            return jsonify({'success': False, 'message': 'Password must be at least 6 characters long'}), 400
        
        user.set_password(new_password)
        db.session.commit()
        
        logger.info(f"Admin {current_user.username} changed password for user: {user.username}")
        return jsonify({'success': True, 'message': 'Password changed successfully'})
        
    except Exception as e:
        logger.error(f"Error changing user password: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Error changing password'}), 500

@app.route('/admin/users/<int:user_id>/change-role', methods=['POST'])
@master_admin_required
def change_user_role(user_id):
    """Change user role"""
    try:
        user = User.query.get_or_404(user_id)
        
        # Prevent changing own role
        if user.id == current_user.id:
            return jsonify({'success': False, 'message': 'Cannot change your own role'}), 400
        
        data = request.get_json()
        new_role = data.get('new_role', '').strip()
        
        if not new_role:
            return jsonify({'success': False, 'message': 'New role is required'}), 400
        
        if new_role not in ['master_admin', 'incident_manager']:
            return jsonify({'success': False, 'message': 'Invalid role selected'}), 400
        
        if new_role == user.role:
            return jsonify({'success': False, 'message': 'User already has this role'}), 400
        
        old_role = user.role
        user.role = new_role
        db.session.commit()
        
        logger.info(f"Admin {current_user.username} changed role for user {user.username} from {old_role} to {new_role}")
        return jsonify({'success': True, 'message': 'Role changed successfully'})
        
    except Exception as e:
        logger.error(f"Error changing user role: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Error changing role'}), 500

@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@master_admin_required
def delete_user(user_id):
    """Delete admin user"""
    try:
        user = User.query.get_or_404(user_id)
        
        # Prevent deleting self
        if user.id == current_user.id:
            flash('Cannot delete your own account')
            return redirect(url_for('admin_users'))
        
        db.session.delete(user)
        db.session.commit()
        
        logger.info(f"Admin {current_user.username} deleted user: {user.username}")
        flash('User deleted successfully')
        
    except Exception as e:
        logger.error(f"Error deleting user: {str(e)}")
        db.session.rollback()
        flash('Error deleting user')
    
    return redirect(url_for('admin_users'))

@app.route('/admin/email-config')
@email_config_required
def admin_email_config():
    """Email configuration page"""
    email_config = EmailConfig.query.first()
    return render_template('admin_email_config.html', email_config=email_config)

@app.route('/admin/email-config/save', methods=['POST'])
@email_config_required
def save_email_config():
    """Save email configuration"""
    try:
        email_config = EmailConfig.query.first()
        
        if not email_config:
            email_config = EmailConfig()
        
        email_config.mail_server = request.form.get('mail_server', '').strip()
        email_config.mail_port = int(request.form.get('mail_port', 587))
        email_config.mail_use_tls = request.form.get('mail_use_tls') == 'on'
        email_config.mail_username = request.form.get('mail_username', '').strip()
        email_config.mail_password = request.form.get('mail_password', '').strip()
        email_config.mail_default_sender = request.form.get('mail_default_sender', '').strip()
        email_config.mail_recipients = request.form.get('mail_recipients', '').strip()
        email_config.is_active = request.form.get('is_active') == 'on'
        
        # Validate required fields
        if not email_config.mail_server or not email_config.mail_username or not email_config.mail_password:
            flash('Mail server, username, and password are required', 'error')
            return redirect(url_for('admin_email_config'))
        
        if email_config.is_active and not email_config.mail_recipients:
            flash('Recipients are required when email notifications are active', 'error')
            return redirect(url_for('admin_email_config'))
        
        if email_config.id is None:
            db.session.add(email_config)
        
        db.session.commit()
        
        logger.info(f"Admin {current_user.username} updated email configuration")
        flash('Email configuration saved successfully', 'success')
        
    except Exception as e:
        logger.error(f"Error saving email configuration: {str(e)}")
        db.session.rollback()
        flash('Error saving email configuration', 'error')
    
    return redirect(url_for('admin_email_config'))

@app.route('/admin/email-config/test', methods=['POST'])
@email_config_required
def test_email_config():
    """Test email configuration by sending a test email"""
    try:
        email_config = EmailConfig.query.first()
        
        if not email_config or not email_config.is_active:
            return jsonify({'success': False, 'message': 'Email configuration not found or not active'}), 400
        
        # Temporarily update Flask-Mail config with database values
        app.config['MAIL_SERVER'] = email_config.mail_server
        app.config['MAIL_PORT'] = email_config.mail_port
        app.config['MAIL_USE_TLS'] = email_config.mail_use_tls
        app.config['MAIL_USERNAME'] = email_config.mail_username
        app.config['MAIL_PASSWORD'] = email_config.mail_password
        app.config['MAIL_DEFAULT_SENDER'] = email_config.mail_default_sender
        
        # Create new Mail instance with updated config
        test_mail = Mail(app)
        
        # Send test email
        msg = Message(
            subject='Test Email - Incident Reporting System',
            sender=email_config.mail_default_sender,
            recipients=email_config.get_recipients_list()
        )
        msg.body = f"""
This is a test email from the Work Place Violence Reporting Server.

Configuration Details:
- Server: {email_config.mail_server}:{email_config.mail_port}
- TLS: {'Enabled' if email_config.mail_use_tls else 'Disabled'}
- Sender: {email_config.mail_default_sender}
- Recipients: {email_config.mail_recipients}

If you receive this email, your email configuration is working correctly.

Sent by: {current_user.username}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        test_mail.send(msg)
        
        logger.info(f"Test email sent successfully by admin {current_user.username}")
        return jsonify({'success': True, 'message': 'Test email sent successfully'})
        
    except Exception as e:
        logger.error(f"Error sending test email: {str(e)}")
        return jsonify({'success': False, 'message': f'Error sending test email: {str(e)}'}), 500

@app.route('/admin/incidents/<int:incident_id>/corrective-actions', methods=['POST'])
@incident_manager_required
def update_corrective_actions(incident_id):
    """Update corrective actions for a specific incident"""
    try:
        incident = Incident.query.get_or_404(incident_id)
        data = request.get_json()
        
        corrective_actions = data.get('corrective_actions', '').strip()
        notify_reporter = data.get('notify_reporter', False)
        
        incident.corrective_actions = corrective_actions if corrective_actions else None
        db.session.commit()
        
        logger.info(f"Admin {current_user.username} updated corrective actions for incident #{incident_id}")
        
        # Send email notification to admin
        send_corrective_actions_notification(incident, "updated")
        
        # Send email notification to reporter if requested and email exists
        if notify_reporter and incident.reporter_email:
            send_reporter_corrective_actions_notification(incident)
        
        return jsonify({
            'success': True, 
            'message': 'Corrective actions updated successfully',
            'corrective_actions': incident.corrective_actions or ''
        })
        
    except Exception as e:
        logger.error(f"Error updating corrective actions for incident #{incident_id}: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Error updating corrective actions'}), 500

@app.route('/export_incident_pdf', methods=['POST'])
def export_incident_pdf():
    """Export incident form data as PDF"""
    try:
        data = request.get_json()
        
        # Create PDF in memory
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story = []
        
        # Get styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=1,  # Center alignment
            textColor=colors.darkblue
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=12,
            spaceAfter=12,
            spaceBefore=12,
            textColor=colors.darkblue
        )
        
        normal_style = styles['Normal']
        normal_style.fontSize = 10
        normal_style.spaceAfter = 6
        
        # Title
        story.append(Paragraph("INCIDENT REPORT", title_style))
        story.append(Spacer(1, 20))
        
        # Reporter Information Section
        story.append(Paragraph("Reporter Information", heading_style))
        
        reporter_data = [
            ['Reporter Name:', data.get('reporter_name', 'Anonymous')],
            ['Job Title:', data.get('reporter_job_title', 'Not provided')],
            ['Email:', data.get('reporter_email', 'Not provided')],
            ['Phone:', data.get('reporter_phone', 'Not provided')]
        ]
        
        reporter_table = Table(reporter_data, colWidths=[2*inch, 4*inch])
        reporter_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        story.append(reporter_table)
        story.append(Spacer(1, 20))
        
        # Incident Details Section
        story.append(Paragraph("Incident Details", heading_style))
        
        # Parse datetime
        incident_datetime = data.get('incident_datetime', '')
        if incident_datetime:
            try:
                dt = datetime.fromisoformat(incident_datetime.replace('T', ' '))
                formatted_datetime = dt.strftime('%B %d, %Y at %I:%M %p')
            except:
                formatted_datetime = incident_datetime
        else:
            formatted_datetime = 'Not provided'
        
        incident_data = [
            ['Date/Time:', formatted_datetime],
            ['Type:', data.get('incident_type', 'Not provided')],
            ['Location:', data.get('location', 'Not provided')]
        ]
        
        incident_table = Table(incident_data, colWidths=[2*inch, 4*inch])
        incident_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        story.append(incident_table)
        story.append(Spacer(1, 20))
        
        # Required Information
        story.append(Paragraph("Description of What Happened", heading_style))
        story.append(Paragraph(data.get('incident_description', 'Not provided'), normal_style))
        story.append(Spacer(1, 12))
        
        story.append(Paragraph("Names and Identifiers of Those Involved", heading_style))
        story.append(Paragraph(data.get('persons_involved', 'Not provided'), normal_style))
        story.append(Spacer(1, 20))
        
        # Additional Details Section
        story.append(Paragraph("Additional Incident Details", heading_style))
        
        additional_fields = [
            ('Nature of Threats, Physical Acts, or Weapons Used:', 'threats_weapons'),
            ('Medical Treatment:', 'medical_treatment'),
            ('Was Law Enforcement Contacted:', 'law_enforcement'),
            ('Security or Other Intervention:', 'security_intervention'),
            ('How the Incident Was Responded To:', 'incident_response'),
            ('Contributing Factors:', 'contributing_factors')
        ]
        
        for field_name, field_key in additional_fields:
            value = data.get(field_key, '').strip()
            if value:  # Only include fields that have content
                story.append(Paragraph(field_name, ParagraphStyle(
                    'FieldLabel',
                    parent=normal_style,
                    fontName='Helvetica-Bold',
                    fontSize=10,
                    spaceAfter=3
                )))
                story.append(Paragraph(value, normal_style))
                story.append(Spacer(1, 8))
        
        # Footer
        story.append(Spacer(1, 30))
        story.append(Paragraph(f"Report generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", 
                             ParagraphStyle('Footer', parent=normal_style, fontSize=8, 
                                           textColor=colors.grey, alignment=1)))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        logger.info("PDF incident report generated successfully")
        
        # Return PDF as response
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'incident_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        )
        
    except Exception as e:
        logger.error(f"Error generating PDF: {str(e)}")
        return jsonify({'success': False, 'message': 'Error generating PDF'}), 500

@app.route('/export_modal_pdf', methods=['POST'])
def export_modal_pdf():
    """Export incident modal data as PDF - specifically for modal exports"""
    try:
        data = request.get_json()
        
        # Create PDF in memory
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story = []
        
        # Get styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=1,  # Center alignment
            textColor=colors.darkblue
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=12,
            spaceAfter=12,
            spaceBefore=12,
            textColor=colors.darkblue
        )
        
        normal_style = styles['Normal']
        normal_style.fontSize = 10
        normal_style.spaceAfter = 6
        
        # Title
        story.append(Paragraph("INCIDENT REPORT", title_style))
        story.append(Spacer(1, 10))
        
        # Incident ID
        incident_id = data.get('incident_id', 'N/A')
        story.append(Paragraph(f"Incident ID: #{incident_id}", ParagraphStyle(
            'IncidentID',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=20,
            alignment=1,  # Center alignment
            textColor=colors.darkblue
        )))
        story.append(Spacer(1, 10))
        
        # Reporter Information Section
        story.append(Paragraph("Reporter Information", heading_style))
        
        reporter_data = [
            ['Reporter Name:', data.get('reporter_name', 'Anonymous')],
            ['Job Title:', data.get('reporter_job_title', 'Not provided')],
            ['Email:', data.get('reporter_email', 'Not provided')],
            ['Phone:', data.get('reporter_phone', 'Not provided')]
        ]
        
        reporter_table = Table(reporter_data, colWidths=[2*inch, 4*inch])
        reporter_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(reporter_table)
        story.append(Spacer(1, 20))
        
        # Incident Details Section
        story.append(Paragraph("Incident Details", heading_style))
        
        incident_data = [
            ['Date/Time:', data.get('incident_datetime', 'Not provided')],
            ['Incident Type:', data.get('incident_type', 'Not provided')],
            ['Location:', data.get('location', 'Not provided')],
            ['Description:', data.get('incident_description', 'Not provided')]
        ]
        
        incident_table = Table(incident_data, colWidths=[2*inch, 4*inch])
        incident_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(incident_table)
        story.append(Spacer(1, 20))
        
        # Names and Identifiers Section
        story.append(Paragraph("Names and Identifiers of Those Involved", heading_style))
        story.append(Paragraph(data.get('persons_involved', 'Not provided'), normal_style))
        story.append(Spacer(1, 20))
        
        # Corrective Actions Section - PROMINENT POSITION
        corrective_actions_value = data.get('corrective_actions', '').strip()
        story.append(Paragraph("Corrective Actions", heading_style))
        story.append(Paragraph(corrective_actions_value if corrective_actions_value else 'No corrective actions specified', normal_style))
        story.append(Spacer(1, 20))
        
        # Additional Details Section
        story.append(Paragraph("Additional Incident Details", heading_style))
        
        additional_fields = [
            ('Nature of Threats, Physical Acts, or Weapons Used:', 'threats_weapons'),
            ('Medical Treatment:', 'medical_treatment'),
            ('Was Law Enforcement Contacted:', 'law_enforcement'),
            ('Security or Other Intervention:', 'security_intervention'),
            ('How the Incident Was Responded To:', 'incident_response'),
            ('Contributing Factors:', 'contributing_factors')
        ]
        
        for field_name, field_key in additional_fields:
            value = data.get(field_key, '').strip()
            if value:  # Only include fields that have content
                story.append(Paragraph(field_name, ParagraphStyle(
                    'FieldLabel',
                    parent=normal_style,
                    fontName='Helvetica-Bold',
                    fontSize=10,
                    spaceAfter=3
                )))
                story.append(Paragraph(value, normal_style))
                story.append(Spacer(1, 8))
        
        # Footer
        story.append(Spacer(1, 30))
        story.append(Paragraph(f"Report generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", 
                             ParagraphStyle('Footer', parent=normal_style, fontSize=8, 
                                           textColor=colors.grey, alignment=1)))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        logger.info("PDF modal incident report generated successfully")
        
        # Return PDF as response
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'incident_report_modal_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        )
        
    except Exception as e:
        logger.error(f"Error generating modal PDF: {str(e)}")
        return jsonify({'success': False, 'message': 'Error generating modal PDF'}), 500

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

# CLI commands
@app.cli.command('init-db')
def init_db():
    """Initialize the database"""
    db.create_all()
    
    # Create default admin user if it doesn't exist
    default_admin = User.query.filter_by(username='admin').first()
    if not default_admin:
        default_admin = User(username='admin', email='admin@archnexus.com')
        default_admin.set_password('admin123')
        db.session.add(default_admin)
        db.session.commit()
        logger.info("Default admin user created: admin/admin123")
        print('Database initialized!')
        print('Default admin user created:')
        print('  Username: admin')
        print('  Email: admin@archnexus.com')
        print('  Password: admin123')
        print('  ⚠️  Please change this password after first login!')
    else:
        print('Database initialized!')
        print('Default admin user already exists: admin')

@app.cli.command('create-admin')
def create_admin():
    """Create additional admin user"""
    username = input('Enter admin username: ')
    password = input('Enter admin password: ')
    
    if User.query.filter_by(username=username).first():
        print('User already exists!')
        return
    
    user = User(username=username)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    
    logger.info(f"Additional admin user created: {username}")
    print(f'Admin user {username} created successfully!')

@app.cli.command('reset-default-admin')
def reset_default_admin():
    """Reset the default admin password"""
    default_admin = User.query.filter_by(username='admin').first()
    if default_admin:
        default_admin.set_password('admin123')
        db.session.commit()
        logger.info("Default admin password reset to: admin123")
        print('Default admin password reset to: admin123')
        print('⚠️  Please change this password after login!')
    else:
        print('Default admin user not found. Run init-db first.')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Migrate existing users to have roles
        existing_users = User.query.filter(User.role.is_(None)).all()
        for user in existing_users:
            if user.username == 'admin':
                user.role = 'master_admin'
            else:
                user.role = 'incident_manager'
        if existing_users:
            db.session.commit()
            logger.info(f"Migrated {len(existing_users)} users to have roles")
        
        # Ensure default admin user exists
        default_admin = User.query.filter_by(username='admin').first()
        if not default_admin:
            default_admin = User(username='admin', email='admin@archnexus.com', role='master_admin')
            default_admin.set_password('admin123')
            db.session.add(default_admin)
            db.session.commit()
            logger.info("Default admin user created on startup: admin/admin123")
            print('Default admin user created: admin/admin123')
    
    app.run(debug=True, host='0.0.0.0', port=5002) 