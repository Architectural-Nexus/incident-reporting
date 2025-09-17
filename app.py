import os
import csv
import logging
from datetime import datetime
from io import StringIO, BytesIO
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

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

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Incident(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reporter_name = db.Column(db.String(100), default='Anonymous')
    incident_datetime = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(200), nullable=False)
    persons_involved = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text, nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'reporter_name': self.reporter_name,
            'incident_datetime': self.incident_datetime.strftime('%Y-%m-%d %H:%M'),
            'location': self.location,
            'persons_involved': self.persons_involved,
            'description': self.description,
            'submitted_at': self.submitted_at.strftime('%Y-%m-%d %H:%M')
        }

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    """Main incident reporting form page"""
    return render_template('index.html')

@app.route('/submit_incident', methods=['POST'])
def submit_incident():
    """Handle incident form submission"""
    try:
        # Get form data
        reporter_name = request.form.get('reporter_name', 'Anonymous').strip()
        if not reporter_name:
            reporter_name = 'Anonymous'
        
        incident_datetime_str = request.form.get('incident_datetime')
        location = request.form.get('location', '').strip()
        persons_involved = request.form.get('persons_involved', '').strip()
        description = request.form.get('description', '').strip()

        # Validate required fields
        if not incident_datetime_str or not location or not persons_involved or not description:
            return jsonify({'success': False, 'message': 'All required fields must be filled out'}), 400

        # Parse datetime
        try:
            incident_datetime = datetime.fromisoformat(incident_datetime_str.replace('T', ' '))
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid date/time format'}), 400

        # Create and save incident
        incident = Incident(
            reporter_name=reporter_name,
            incident_datetime=incident_datetime,
            location=location,
            persons_involved=persons_involved,
            description=description
        )
        
        db.session.add(incident)
        db.session.commit()

        logger.info(f"New incident reported: ID={incident.id}, Location={location}, Reporter={reporter_name}")
        
        return jsonify({'success': True, 'message': 'Incident report submitted successfully'})

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
            return redirect(url_for('admin_dashboard'))
        else:
            logger.warning(f"Failed login attempt for username: {username}")
            flash('Invalid username or password')
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
@login_required
def admin_logout():
    """Admin logout"""
    logger.info(f"Admin logout: {current_user.username}")
    logout_user()
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    """Admin dashboard to view incidents"""
    return render_template('admin_dashboard.html')

@app.route('/admin/incidents')
@login_required
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
                    Incident.location.ilike(f'%{search}%'),
                    Incident.persons_involved.ilike(f'%{search}%'),
                    Incident.description.ilike(f'%{search}%')
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
@login_required
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
            'ID', 'Reporter Name', 'Incident Date/Time', 'Location', 
            'Persons Involved', 'Description', 'Submitted At'
        ])
        
        # Write data
        for incident in incidents:
            try:
                writer.writerow([
                    incident.id,
                    incident.reporter_name or 'Anonymous',
                    incident.incident_datetime.strftime('%Y-%m-%d %H:%M') if incident.incident_datetime else '',
                    incident.location or '',
                    incident.persons_involved or '',
                    incident.description or '',
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
@login_required
def admin_users():
    """Admin users management page"""
    users = User.query.all()
    return render_template('admin_users.html', users=users)

@app.route('/admin/users/add', methods=['POST'])
@login_required
def add_user():
    """Add new admin user"""
    try:
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            flash('Username and password are required')
            return redirect(url_for('admin_users'))
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('admin_users'))
        
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        logger.info(f"Admin {current_user.username} added new user: {username}")
        flash('User added successfully')
        
    except Exception as e:
        logger.error(f"Error adding user: {str(e)}")
        db.session.rollback()
        flash('Error adding user')
    
    return redirect(url_for('admin_users'))

@app.route('/admin/users/<int:user_id>/toggle', methods=['POST'])
@login_required
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
@login_required
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

@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required
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
        default_admin = User(username='admin')
        default_admin.set_password('admin123')
        db.session.add(default_admin)
        db.session.commit()
        logger.info("Default admin user created: admin/admin123")
        print('Database initialized!')
        print('Default admin user created:')
        print('  Username: admin')
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
        
        # Ensure default admin user exists
        default_admin = User.query.filter_by(username='admin').first()
        if not default_admin:
            default_admin = User(username='admin')
            default_admin.set_password('admin123')
            db.session.add(default_admin)
            db.session.commit()
            logger.info("Default admin user created on startup: admin/admin123")
            print('Default admin user created: admin/admin123')
    
    app.run(debug=True, host='0.0.0.0', port=5000) 