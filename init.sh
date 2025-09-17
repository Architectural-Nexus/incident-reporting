#!/bin/bash

# Incident Reports Application Initialization Script
# This script initializes the application for manual setup

set -e

# Configuration
APP_DIR="$(pwd)"
VENV_DIR="$APP_DIR/venv"
DATA_DIR="$APP_DIR/instance"
LOG_DIR="$APP_DIR/logs"

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

# Function to check Python installation
check_python() {
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed. Please install Python 3.8 or higher."
        exit 1
    fi
    
    if ! command -v pip3 &> /dev/null; then
        print_error "pip3 is not installed. Please install pip3."
        exit 1
    fi
    
    print_status "Python 3 and pip3 are available"
}

# Function to create virtual environment
create_venv() {
    print_status "Creating virtual environment..."
    
    if [ -d "$VENV_DIR" ]; then
        print_warning "Virtual environment already exists at $VENV_DIR"
        read -p "Do you want to recreate it? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$VENV_DIR"
        else
            print_status "Using existing virtual environment"
            return
        fi
    fi
    
    python3 -m venv "$VENV_DIR"
    print_status "Virtual environment created at $VENV_DIR"
}

# Function to install dependencies
install_dependencies() {
    print_status "Installing Python dependencies..."
    
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip
    pip install -r requirements.txt
    
    print_status "Dependencies installed successfully"
}

# Function to create directories
create_directories() {
    print_status "Creating necessary directories..."
    
    mkdir -p "$DATA_DIR"
    mkdir -p "$LOG_DIR"
    
    print_status "Directories created:"
    print_status "  - Data: $DATA_DIR"
    print_status "  - Logs: $LOG_DIR"
}

# Function to initialize database
init_database() {
    print_status "Initializing database..."
    
    source "$VENV_DIR/bin/activate"
    
    # Initialize database
    python -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('Database initialized successfully')
"
    
    print_status "Database initialized at $DATA_DIR/incidents.db"
}

# Function to create admin user
create_admin() {
    print_status "Creating admin user..."
    
    source "$VENV_DIR/bin/activate"
    
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
    
    print_status "Admin user created (username: admin, password: admin123)"
}

# Function to create run script
create_run_script() {
    print_status "Creating run script..."
    
    cat > run.sh << 'EOF'
#!/bin/bash

# Run script for Incident Reports Application
set -e

# Configuration
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$APP_DIR/venv"

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Set environment variables
export FLASK_APP=app.py
export FLASK_ENV=development
export SECRET_KEY=your-secret-key-change-this-in-production
export DATABASE_URL=sqlite:///instance/incidents.db

# Run the application
echo "Starting Incident Reports Application..."
echo "Application will be available at: http://localhost:8000"
echo "Admin panel: http://localhost:8000/admin/login"
echo "Press Ctrl+C to stop"
echo ""

python -m flask run --host=0.0.0.0 --port=8000
EOF
    
    chmod +x run.sh
    print_status "Run script created: run.sh"
}

# Function to create production run script
create_prod_run_script() {
    print_status "Creating production run script..."
    
    cat > run_prod.sh << 'EOF'
#!/bin/bash

# Production run script for Incident Reports Application
set -e

# Configuration
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$APP_DIR/venv"

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Set environment variables
export FLASK_APP=app.py
export FLASK_ENV=production
export SECRET_KEY=your-secret-key-change-this-in-production
export DATABASE_URL=sqlite:///instance/incidents.db

# Create log directory if it doesn't exist
mkdir -p logs

# Run the application with gunicorn
echo "Starting Incident Reports Application in production mode..."
echo "Application will be available at: http://localhost:8000"
echo "Admin panel: http://localhost:8000/admin/login"
echo "Logs will be written to logs/ directory"
echo "Press Ctrl+C to stop"
echo ""

gunicorn --config gunicorn.conf.py --bind 0.0.0.0:8000 app:app
EOF
    
    chmod +x run_prod.sh
    print_status "Production run script created: run_prod.sh"
}

# Function to display final information
display_info() {
    echo ""
    echo "=========================================="
    echo "🎉 Initialization completed successfully!"
    echo "=========================================="
    echo ""
    echo "Application Information:"
    echo "  - Virtual Environment: $VENV_DIR"
    echo "  - Database: $DATA_DIR/incidents.db"
    echo "  - Logs: $LOG_DIR"
    echo ""
    echo "Running the Application:"
    echo "  - Development: ./run.sh"
    echo "  - Production:  ./run_prod.sh"
    echo ""
    echo "Access Information:"
    echo "  - Application URL: http://localhost:8000"
    echo "  - Admin URL: http://localhost:8000/admin/login"
    echo "  - Default Admin: admin / admin123"
    echo ""
    echo "⚠️  IMPORTANT: Change the default admin password!"
    echo "⚠️  IMPORTANT: Update SECRET_KEY for production!"
    echo ""
}

# Main execution
main() {
    print_status "Starting initialization of Incident Reports Application..."
    
    check_python
    create_venv
    install_dependencies
    create_directories
    init_database
    create_admin
    create_run_script
    create_prod_run_script
    display_info
}

# Run main function
main "$@" 