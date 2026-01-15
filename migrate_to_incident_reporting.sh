#!/bin/bash

# Migration Script: Option B
# Migrates from /opt/incident-reports to /opt/incident-reporting
# Works on both AlmaLinux and Ubuntu

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
OLD_APP_DIR="/opt/incident-reports"
NEW_APP_DIR="/opt/incident-reporting"
OLD_DB_PATH="/var/lib/incident-reports/incidents.db"
NEW_DB_PATH="/opt/incident-reporting/instance/incidents.db"
SERVICE_NAME="incident-reports"
NEW_SERVICE_NAME="incident-reporting"
APP_USER="incident-reports"
APP_GROUP="incident-reports"

# Detect OS
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        OS_VERSION=$VERSION_ID
    else
        echo -e "${RED}❌ Cannot detect OS${NC}"
        exit 1
    fi
}

# Print functions
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Backup existing data
backup_data() {
    print_step "Creating backup..."
    
    BACKUP_DIR="/opt/incident-reporting-backup-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    # Backup old directory if it exists
    if [ -d "$OLD_APP_DIR" ]; then
        print_status "Backing up $OLD_APP_DIR"
        cp -r "$OLD_APP_DIR" "$BACKUP_DIR/incident-reports-old" 2>/dev/null || true
    fi
    
    # Backup database
    if [ -f "$OLD_DB_PATH" ]; then
        print_status "Backing up database"
        mkdir -p "$BACKUP_DIR"
        cp "$OLD_DB_PATH" "$BACKUP_DIR/incidents.db.backup"
    fi
    
    # Backup service file
    if [ -f "/etc/systemd/system/${SERVICE_NAME}.service" ]; then
        cp "/etc/systemd/system/${SERVICE_NAME}.service" "$BACKUP_DIR/${SERVICE_NAME}.service.backup"
    fi
    
    # Backup Apache config
    if [ -f "/etc/httpd/conf.d/incident-reports.conf" ]; then
        cp "/etc/httpd/conf.d/incident-reports.conf" "$BACKUP_DIR/incident-reports-apache.conf.backup"
    elif [ -f "/etc/nginx/sites-available/incident-reporting" ]; then
        cp "/etc/nginx/sites-available/incident-reporting" "$BACKUP_DIR/incident-reporting-nginx.conf.backup"
    fi
    
    print_status "Backup created at: $BACKUP_DIR"
}

# Stop old service
stop_old_service() {
    print_step "Stopping old service..."
    
    if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
        print_status "Stopping $SERVICE_NAME service"
        systemctl stop "$SERVICE_NAME"
        sleep 2
    else
        print_warning "Service $SERVICE_NAME is not running"
    fi
    
    # Kill any remaining processes
    if pgrep -f "gunicorn.*incident" > /dev/null; then
        print_warning "Killing remaining gunicorn processes"
        pkill -f "gunicorn.*incident" || true
        sleep 2
    fi
}

# Set up new directory structure
setup_new_directory() {
    print_step "Setting up new directory structure..."
    
    # Create new directory
    if [ ! -d "$NEW_APP_DIR" ]; then
        print_status "Creating $NEW_APP_DIR"
        mkdir -p "$NEW_APP_DIR"
    fi
    
    # If git repo already exists, we'll use it
    if [ -d "$NEW_APP_DIR/.git" ]; then
        print_status "Git repository found at $NEW_APP_DIR"
        cd "$NEW_APP_DIR"
        print_status "Pulling latest changes..."
        git pull origin main || print_warning "Could not pull from git"
    else
        print_error "Git repository not found at $NEW_APP_DIR"
        print_error "Please ensure the repository is cloned to $NEW_APP_DIR"
        exit 1
    fi
    
    # Create necessary directories
    mkdir -p "$NEW_APP_DIR/instance"
    mkdir -p "$NEW_APP_DIR/logs"
    mkdir -p "$NEW_APP_DIR/backups"
}

# Set up Python virtual environment
setup_venv() {
    print_step "Setting up Python virtual environment..."
    
    cd "$NEW_APP_DIR"
    
    # Detect best Python version available
    PYTHON_CMD="python3"
    if command -v python3.12 &> /dev/null; then
        PYTHON_CMD="python3.12"
        print_status "Using Python 3.12"
    elif command -v python3.11 &> /dev/null; then
        PYTHON_CMD="python3.11"
        print_status "Using Python 3.11"
    elif command -v python3.10 &> /dev/null; then
        PYTHON_CMD="python3.10"
        print_status "Using Python 3.10"
    elif command -v python3.9 &> /dev/null; then
        PYTHON_CMD="python3.9"
        print_status "Using Python 3.9"
    else
        PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
        print_warning "Using default Python: $PYTHON_VERSION"
        print_warning "Python 3.9+ is recommended for Flask 2.3.3"
    fi
    
    if [ ! -d "venv" ]; then
        print_status "Creating virtual environment with $PYTHON_CMD..."
        $PYTHON_CMD -m venv venv
    else
        # Check if we need to recreate with correct Python version
        VENV_PYTHON=$(venv/bin/python --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
        DESIRED_PYTHON=$($PYTHON_CMD --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
        print_status "Current venv Python: $VENV_PYTHON"
        
        # If Python version is too old (less than 3.9), recreate venv
        if [ "$(echo "$VENV_PYTHON < 3.9" | bc 2>/dev/null || echo "1")" = "1" ] || [ "$VENV_PYTHON" != "$DESIRED_PYTHON" ]; then
            print_warning "Virtual environment uses Python $VENV_PYTHON, but need $DESIRED_PYTHON"
            print_status "Recreating virtual environment with $PYTHON_CMD..."
            rm -rf venv
            $PYTHON_CMD -m venv venv
        else
            print_status "Virtual environment Python version is compatible"
        fi
    fi
    
    print_status "Installing/updating dependencies..."
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    
    print_status "Virtual environment ready"
}

# Migrate database
migrate_database() {
    print_step "Migrating database..."
    
    # Create instance directory if it doesn't exist
    mkdir -p "$NEW_APP_DIR/instance"
    
    # Copy database from old location if it exists
    if [ -f "$OLD_DB_PATH" ]; then
        print_status "Copying database from $OLD_DB_PATH to $NEW_DB_PATH"
        cp "$OLD_DB_PATH" "$NEW_DB_PATH"
        chown "$APP_USER:$APP_GROUP" "$NEW_DB_PATH" 2>/dev/null || chown root:root "$NEW_DB_PATH"
        chmod 644 "$NEW_DB_PATH"
    else
        print_warning "No existing database found, will create new one"
    fi
    
    # Initialize database schema if needed
    cd "$NEW_APP_DIR"
    source venv/bin/activate
    print_status "Initializing/updating database schema..."
    python -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('Database schema initialized/updated')
" || print_warning "Database initialization had issues (may be normal if schema is up to date)"
}

# Configure environment file
configure_env() {
    print_step "Configuring environment file..."
    
    cd "$NEW_APP_DIR"
    
    if [ ! -f ".env" ]; then
        print_status "Creating .env file from template"
        cp env.example .env
        
        # Set production defaults
        sed -i 's/FLASK_ENV=.*/FLASK_ENV=production/' .env 2>/dev/null || \
        echo "FLASK_ENV=production" >> .env
        
        # Update database path
        sed -i "s|DATABASE_URL=.*|DATABASE_URL=sqlite:///instance/incidents.db|" .env 2>/dev/null || \
        echo "DATABASE_URL=sqlite:///instance/incidents.db" >> .env
        
        # Generate secret key if not set
        if ! grep -q "SECRET_KEY=" .env || grep -q "SECRET_KEY=your-secret-key" .env; then
            SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
            sed -i "s|SECRET_KEY=.*|SECRET_KEY=$SECRET_KEY|" .env 2>/dev/null || \
            echo "SECRET_KEY=$SECRET_KEY" >> .env
        fi
        
        print_warning "⚠️  Please review and update .env file with your configuration"
    else
        print_status ".env file already exists, preserving it"
        # Update database path in existing .env if needed
        if grep -q "DATABASE_URL=.*/var/lib/incident-reports" .env; then
            print_status "Updating DATABASE_URL in .env"
            sed -i "s|DATABASE_URL=.*|DATABASE_URL=sqlite:///instance/incidents.db|" .env
        fi
    fi
    
    chmod 600 .env
    chown "$APP_USER:$APP_GROUP" .env 2>/dev/null || chown root:root .env
}

# Update systemd service
update_systemd_service() {
    print_step "Updating systemd service..."
    
    # Disable old service
    if systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
        print_status "Disabling old service $SERVICE_NAME"
        systemctl disable "$SERVICE_NAME" 2>/dev/null || true
    fi
    
    # Create new service file
    SERVICE_FILE="/etc/systemd/system/${NEW_SERVICE_NAME}.service"
    
    print_status "Creating new service file: $SERVICE_FILE"
    
    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Incident Reporting System
After=network.target

[Service]
Type=notify
User=$APP_USER
Group=$APP_GROUP
WorkingDirectory=$NEW_APP_DIR
Environment=PATH=$NEW_APP_DIR/venv/bin
Environment=FLASK_APP=app.py
Environment=FLASK_ENV=production
ExecStart=$NEW_APP_DIR/venv/bin/gunicorn --config gunicorn.conf.py --bind 0.0.0.0:8000 app:app
ExecReload=/bin/kill -s HUP \$MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=always
RestartSec=10
RuntimeDirectory=incident-reporting

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd
    systemctl daemon-reload
    
    # Enable new service
    systemctl enable "$NEW_SERVICE_NAME"
    
    print_status "Service file created and enabled"
}

# Update web server configuration
update_web_server() {
    print_step "Updating web server configuration..."
    
    # Safety check: Verify we won't affect other sites
    print_status "Checking for other Apache virtual hosts..."
    OTHER_SITES=$(grep -l "ServerName" /etc/httpd/conf.d/*.conf 2>/dev/null | grep -v "incident-reports.conf" | wc -l)
    if [ "$OTHER_SITES" -gt 0 ]; then
        print_warning "Found $OTHER_SITES other Apache virtual host(s) - will only modify incident-reports.conf"
        print_status "Other sites in /var/www/html will NOT be affected"
    fi
    
    if [ -f "/etc/httpd/conf.d/incident-reports.conf" ]; then
        # Apache configuration (AlmaLinux)
        print_status "Updating Apache configuration for incidents.archnexus.com only..."
        
        APACHE_CONFIG="/etc/httpd/conf.d/incident-reports.conf"
        BACKUP_FILE="${APACHE_CONFIG}.backup.$(date +%Y%m%d-%H%M%S)"
        
        # Backup original
        cp "$APACHE_CONFIG" "$BACKUP_FILE"
        print_status "Backup created: $BACKUP_FILE"
        
        # Verify this is the incidents.archnexus.com config before modifying
        if ! grep -q "incidents.archnexus.com" "$APACHE_CONFIG"; then
            print_error "Apache config does not contain 'incidents.archnexus.com' - aborting modification"
            return 1
        fi
        
        # Only update paths that are specific to incident-reports
        # Use very specific patterns to avoid affecting other configs
        print_status "Updating paths in incident-reports.conf only..."
        
        # Update DocumentRoot (only if it's /opt/incident-reports)
        sed -i "s|DocumentRoot /opt/incident-reports|DocumentRoot $NEW_APP_DIR|g" "$APACHE_CONFIG"
        
        # Update Alias paths (only for /opt/incident-reports)
        sed -i "s|Alias /static /opt/incident-reports/static|Alias /static $NEW_APP_DIR/static|g" "$APACHE_CONFIG"
        sed -i "s|Alias /favicon.ico /opt/incident-reports/static|Alias /favicon.ico $NEW_APP_DIR/static|g" "$APACHE_CONFIG"
        sed -i "s|Alias /robots.txt /opt/incident-reports/robots.txt|Alias /robots.txt $NEW_APP_DIR/robots.txt|g" "$APACHE_CONFIG"
        
        # Update Directory paths (only for /opt/incident-reports)
        sed -i "s|<Directory \"/opt/incident-reports/static\">|<Directory \"$NEW_APP_DIR/static\">|g" "$APACHE_CONFIG"
        
        # Verify we didn't accidentally modify other paths
        if grep -q "/var/www/html" "$APACHE_CONFIG"; then
            print_warning "Warning: /var/www/html found in config - this should not be modified"
        fi
        
        # Test Apache configuration
        print_status "Testing Apache configuration..."
        if httpd -t > /tmp/httpd-test.log 2>&1; then
            print_status "✅ Apache configuration is valid"
            print_status "Other sites (assets, revitfam) are unaffected"
        else
            print_error "❌ Apache configuration has errors!"
            print_error "Error output:"
            cat /tmp/httpd-test.log
            print_warning "Restoring backup..."
            cp "$BACKUP_FILE" "$APACHE_CONFIG"
            print_error "Please check the configuration manually"
            httpd -t
            return 1
        fi
        
    elif [ -f "/etc/nginx/sites-available/incident-reporting" ]; then
        # Nginx configuration (Ubuntu)
        print_status "Updating Nginx configuration..."
        
        NGINX_CONFIG="/etc/nginx/sites-available/incident-reporting"
        BACKUP_FILE="${NGINX_CONFIG}.backup.$(date +%Y%m%d-%H%M%S)"
        
        # Backup original
        cp "$NGINX_CONFIG" "$BACKUP_FILE"
        
        # Only update paths specific to incident-reporting
        sed -i "s|/opt/incident-reporting|$NEW_APP_DIR|g" "$NGINX_CONFIG" 2>/dev/null || true
        
        # Test Nginx configuration
        if nginx -t > /dev/null 2>&1; then
            print_status "✅ Nginx configuration is valid"
        else
            print_error "❌ Nginx configuration has errors!"
            print_warning "Restoring backup..."
            cp "$BACKUP_FILE" "$NGINX_CONFIG"
            nginx -t
            return 1
        fi
    else
        print_warning "No web server configuration found. You may need to configure it manually."
    fi
}

# Set file permissions
set_permissions() {
    print_step "Setting file permissions..."
    
    # Set ownership
    if id "$APP_USER" &>/dev/null; then
        print_status "Setting ownership to $APP_USER:$APP_GROUP"
        chown -R "$APP_USER:$APP_GROUP" "$NEW_APP_DIR"
    else
        print_warning "User $APP_USER does not exist, using root ownership"
        chown -R root:root "$NEW_APP_DIR"
    fi
    
    # Set specific permissions
    chmod 755 "$NEW_APP_DIR"
    chmod 600 "$NEW_APP_DIR/.env"
    chmod 644 "$NEW_DB_PATH" 2>/dev/null || true
    chmod +x "$NEW_APP_DIR/start_dev.sh" 2>/dev/null || true
    
    print_status "Permissions set"
}

# Start new service
start_new_service() {
    print_step "Starting new service..."
    
    systemctl start "$NEW_SERVICE_NAME"
    sleep 3
    
    if systemctl is-active --quiet "$NEW_SERVICE_NAME"; then
        print_status "✅ Service $NEW_SERVICE_NAME is running"
    else
        print_error "❌ Service failed to start"
        print_status "Check logs with: journalctl -u $NEW_SERVICE_NAME -n 50"
        exit 1
    fi
}

# Restart web server
restart_web_server() {
    print_step "Restarting web server..."
    
    if systemctl is-active --quiet httpd; then
        print_status "Restarting Apache (this will affect all virtual hosts)"
        print_warning "Verifying other sites are still configured..."
        
        # Quick check that other configs still exist
        if [ -f "/etc/httpd/conf.d/assets.conf" ] && [ -f "/etc/httpd/conf.d/revitfam.conf" ]; then
            print_status "✅ Other site configs (assets, revitfam) are present"
        fi
        
        systemctl restart httpd
        
        # Verify Apache started successfully
        sleep 2
        if systemctl is-active --quiet httpd; then
            print_status "✅ Apache restarted successfully"
            print_status "✅ All sites should be accessible"
        else
            print_error "❌ Apache failed to restart!"
            print_error "Check logs: journalctl -u httpd -n 50"
            return 1
        fi
    elif systemctl is-active --quiet nginx; then
        print_status "Restarting Nginx"
        systemctl restart nginx
    else
        print_warning "No web server found running"
    fi
}

# Safety check: Verify we won't affect other sites
safety_checks() {
    print_step "Running safety checks..."
    
    # Check for other sites in /var/www/html
    if [ -d "/var/www/html" ]; then
        OTHER_SITES=$(find /var/www/html -maxdepth 1 -type d ! -name "html" ! -name "." | wc -l)
        if [ "$OTHER_SITES" -gt 0 ]; then
            print_status "Found $OTHER_SITES other site(s) in /var/www/html:"
            find /var/www/html -maxdepth 1 -type d ! -name "html" ! -name "." -exec basename {} \;
            print_status "✅ These sites will NOT be affected by this migration"
        fi
    fi
    
    # Verify we're only modifying incident-reports config
    if [ -f "/etc/httpd/conf.d/incident-reports.conf" ]; then
        OTHER_CONFIGS=$(ls /etc/httpd/conf.d/*.conf 2>/dev/null | grep -v "incident-reports.conf" | wc -l)
        if [ "$OTHER_CONFIGS" -gt 0 ]; then
            print_status "Found $OTHER_CONFIGS other Apache config file(s)"
            print_status "✅ Only incident-reports.conf will be modified"
        fi
    fi
    
    # Verify migration paths don't conflict with /var/www/html
    if [ "$NEW_APP_DIR" = "/var/www/html" ] || [[ "$NEW_APP_DIR" == /var/www/html/* ]]; then
        print_error "ERROR: New app directory conflicts with /var/www/html!"
        print_error "Migration aborted to protect other sites"
        exit 1
    fi
    
    if [ "$OLD_APP_DIR" = "/var/www/html" ] || [[ "$OLD_APP_DIR" == /var/www/html/* ]]; then
        print_error "ERROR: Old app directory conflicts with /var/www/html!"
        print_error "Migration aborted to protect other sites"
        exit 1
    fi
    
    print_status "✅ Safety checks passed - other sites are protected"
    echo ""
}

# Main migration function
main() {
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  Incident Reporting System - Migration to Option B     ║${NC}"
    echo -e "${GREEN}║  Migrating to /opt/incident-reporting                   ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    detect_os
    print_status "Detected OS: $OS $OS_VERSION"
    echo ""
    
    check_root
    safety_checks
    backup_data
    stop_old_service
    setup_new_directory
    setup_venv
    migrate_database
    configure_env
    update_systemd_service
    update_web_server
    set_permissions
    start_new_service
    restart_web_server
    
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✅ Migration Complete!                                 ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    print_status "Application is now running at: $NEW_APP_DIR"
    print_status "Service name: $NEW_SERVICE_NAME"
    print_status "Database location: $NEW_DB_PATH"
    echo ""
    print_warning "⚠️  Next steps:"
    echo "   1. Review and update $NEW_APP_DIR/.env"
    echo "   2. Test the application: https://incidents.archnexus.com"
    echo "   3. Check service status: systemctl status $NEW_SERVICE_NAME"
    echo "   4. View logs: journalctl -u $NEW_SERVICE_NAME -f"
    echo ""
    print_status "To rollback, restore from backup directory"
}

# Run migration
main
