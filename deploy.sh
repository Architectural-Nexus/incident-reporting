#!/bin/bash

# Incident Reports Application Deployment Script
# This script sets up the application to run as a system service

set -e

# Configuration
APP_NAME="incident-reports"
APP_USER="incident-reports"
APP_GROUP="incident-reports"
APP_DIR="/opt/incident-reports"
SERVICE_FILE="/etc/systemd/system/incident-reports.service"
LOG_DIR="/var/log/incident-reports"
DATA_DIR="/var/lib/incident-reports"
VENV_DIR="/opt/incident-reports/venv"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Function to check if systemd is available
check_systemd() {
    if ! command -v systemctl &> /dev/null; then
        print_error "systemd is not available on this system"
        exit 1
    fi
}

# Function to create user and group
create_user() {
    print_status "Creating user and group..."
    
    if ! getent group $APP_GROUP > /dev/null 2>&1; then
        groupadd $APP_GROUP
        print_status "Created group: $APP_GROUP"
    else
        print_warning "Group $APP_GROUP already exists"
    fi
    
    if ! getent passwd $APP_USER > /dev/null 2>&1; then
        useradd -r -g $APP_GROUP -s /bin/false -d $APP_DIR $APP_USER
        print_status "Created user: $APP_USER"
    else
        print_warning "User $APP_USER already exists"
    fi
}

# Function to create directories
create_directories() {
    print_status "Creating directories..."
    
    mkdir -p $APP_DIR
    mkdir -p $LOG_DIR
    mkdir -p $DATA_DIR
    mkdir -p /var/run/incident-reports
    
    # Set ownership
    chown -R $APP_USER:$APP_GROUP $APP_DIR
    chown -R $APP_USER:$APP_GROUP $LOG_DIR
    chown -R $APP_USER:$APP_GROUP $DATA_DIR
    chown -R $APP_USER:$APP_GROUP /var/run/incident-reports
    
    # Set permissions
    chmod 755 $APP_DIR
    chmod 755 $LOG_DIR
    chmod 755 $DATA_DIR
    chmod 755 /var/run/incident-reports
    
    print_status "Directories created and permissions set:"
    print_status "  - Application: $APP_DIR"
    print_status "  - Logs: $LOG_DIR"
    print_status "  - Data: $DATA_DIR"
    print_status "  - Runtime: /var/run/incident-reports"
}

# Function to copy application files
copy_application() {
    print_status "Copying application files..."
    
    # Get the directory where this script is located
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    # Copy application files
    cp -r $SCRIPT_DIR/* $APP_DIR/
    
    # Remove deployment files from app directory
    rm -f $APP_DIR/deploy.sh
    rm -f $APP_DIR/nginx.conf
    
    # Set ownership
    chown -R $APP_USER:$APP_GROUP $APP_DIR
}

# Function to setup Python virtual environment
setup_python_env() {
    print_status "Setting up Python virtual environment..."
    
    # Check if Python 3 is available
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed. Please install Python 3.8 or higher."
        exit 1
    fi
    
    # Check if pip3 is available
    if ! command -v pip3 &> /dev/null; then
        print_error "pip3 is not installed. Please install pip3."
        exit 1
    fi
    
    # Create virtual environment
    cd $APP_DIR
    python3 -m venv $VENV_DIR
    
    # Activate virtual environment and install dependencies
    source $VENV_DIR/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    
    # Set ownership
    chown -R $APP_USER:$APP_GROUP $VENV_DIR
}

# Function to create systemd service file
create_service_file() {
    print_status "Creating systemd service file..."
    
    cat > $SERVICE_FILE << EOF
[Unit]
Description=Incident Reports Application
After=network.target

[Service]
Type=notify
User=$APP_USER
Group=$APP_GROUP
WorkingDirectory=$APP_DIR
Environment=PATH=$VENV_DIR/bin
Environment=FLASK_APP=app.py
Environment=FLASK_ENV=production
Environment=SECRET_KEY=your-secret-key-change-this-in-production
Environment=DATABASE_URL=sqlite:///$DATA_DIR/incidents.db
ExecStartPre=/bin/mkdir -p /var/run/incident-reports
ExecStartPre=/bin/chown $APP_USER:$APP_GROUP /var/run/incident-reports
ExecStartPre=/bin/chmod 755 /var/run/incident-reports
ExecStart=$VENV_DIR/bin/gunicorn --config gunicorn.conf.py --bind 0.0.0.0:8000 app:app
ExecReload=/bin/kill -s HUP \$MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd
    systemctl daemon-reload
}

# Function to initialize database
initialize_database() {
    print_status "Initializing database..."
    
    # Ensure data directory exists and has proper permissions
    mkdir -p $DATA_DIR
    chown $APP_USER:$APP_GROUP $DATA_DIR
    chmod 755 $DATA_DIR
    
    cd $APP_DIR
    source $VENV_DIR/bin/activate
    
    # Set environment variable for database location
    export DATABASE_URL="sqlite:///$DATA_DIR/incidents.db"
    
    # Initialize database
    python -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('Database initialized successfully')
"
    
    # Create default admin user
    python -c "
from app import app, db, User
with app.app_context():
    # Check if admin user already exists
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(username='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print('Default admin user created: admin/admin123')
    else:
        print('Admin user already exists')
"
    
    # Set ownership of database file if it exists
    if [ -f "$DATA_DIR/incidents.db" ]; then
        chown $APP_USER:$APP_GROUP $DATA_DIR/incidents.db
        chmod 644 $DATA_DIR/incidents.db
        print_status "Database file ownership and permissions set"
    else
        print_warning "Database file not found, ownership will be set when file is created"
    fi
}

# Function to setup firewall (optional)
setup_firewall() {
    print_status "Setting up firewall rules..."
    
    # Check if ufw is available
    if command -v ufw &> /dev/null; then
        ufw allow 8000/tcp
        print_status "Firewall rule added for port 8000"
    elif command -v firewall-cmd &> /dev/null; then
        firewall-cmd --permanent --add-port=8000/tcp
        firewall-cmd --reload
        print_status "Firewall rule added for port 8000"
    else
        print_warning "No supported firewall found. Please manually configure firewall for port 8000"
    fi
}

# Function to verify database creation
verify_database() {
    print_status "Verifying database creation..."
    
    if [ -f "$DATA_DIR/incidents.db" ]; then
        print_status "Database file created successfully at $DATA_DIR/incidents.db"
        ls -la "$DATA_DIR/incidents.db"
    else
        print_error "Database file was not created. Check the initialization logs above."
        exit 1
    fi
}

# Function to start and enable service
start_service() {
    print_status "Starting and enabling service..."
    
    systemctl enable incident-reports.service
    systemctl start incident-reports.service
    
    # Wait a moment for service to start
    sleep 3
    
    # Check service status
    if systemctl is-active --quiet incident-reports.service; then
        print_status "Service started successfully"
    else
        print_error "Service failed to start. Checking for common issues..."
        
        # Check if runtime directory exists and has proper permissions
        if [ ! -d "/var/run/incident-reports" ]; then
            print_status "Creating missing runtime directory..."
            mkdir -p /var/run/incident-reports
            chown $APP_USER:$APP_GROUP /var/run/incident-reports
            chmod 755 /var/run/incident-reports
        fi
        
        # Check service logs
        print_status "Recent service logs:"
        journalctl -u incident-reports.service --no-pager -n 20
        
        print_error "Service failed to start. Please check the logs above and try again."
        exit 1
    fi
}

# Function to display final information
display_info() {
    echo ""
    echo "=========================================="
    echo "🎉 Deployment completed successfully!"
    echo "=========================================="
    echo ""
    echo "Application Information:"
    echo "  - Service Name: incident-reports"
    echo "  - Application URL: http://localhost:8000"
    echo "  - Admin URL: http://localhost:8000/admin/login"
    echo "  - Default Admin: admin / admin123"
    echo ""
    echo "Service Management:"
    echo "  - Start:   sudo systemctl start incident-reports"
    echo "  - Stop:    sudo systemctl stop incident-reports"
    echo "  - Restart: sudo systemctl restart incident-reports"
    echo "  - Status:  sudo systemctl status incident-reports"
    echo "  - Logs:    sudo journalctl -u incident-reports -f"
    echo ""
    echo "Files and Directories:"
    echo "  - Application: $APP_DIR"
    echo "  - Logs: $LOG_DIR"
    echo "  - Data: $DATA_DIR"
    echo "  - Virtual Environment: $VENV_DIR"
    echo ""
    echo "⚠️  IMPORTANT: Change the default admin password!"
    echo "⚠️  IMPORTANT: Update SECRET_KEY in the service file!"
    echo ""
}

# Main execution
main() {
    print_status "Starting deployment of Incident Reports Application..."
    
    check_root
    check_systemd
    create_user
    create_directories
    copy_application
    setup_python_env
    create_service_file
    initialize_database
    verify_database
    setup_firewall
    start_service
    display_info
}

# Run main function
main "$@" 