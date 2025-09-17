#!/bin/bash

# Incident Reports Application Uninstall Script
# This script removes the application from the system

set -e

# Configuration
APP_NAME="incident-reports"
APP_USER="incident-reports"
APP_GROUP="incident-reports"
APP_DIR="/opt/incident-reports"
SERVICE_FILE="/etc/systemd/system/incident-reports.service"
LOG_DIR="/var/log/incident-reports"
DATA_DIR="/var/lib/incident-reports"

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

# Function to stop and disable service
stop_service() {
    print_status "Stopping and disabling service..."
    
    if systemctl is-active --quiet incident-reports.service; then
        systemctl stop incident-reports.service
        print_status "Service stopped"
    else
        print_warning "Service was not running"
    fi
    
    if systemctl is-enabled --quiet incident-reports.service; then
        systemctl disable incident-reports.service
        print_status "Service disabled"
    else
        print_warning "Service was not enabled"
    fi
}

# Function to remove service file
remove_service_file() {
    print_status "Removing service file..."
    
    if [ -f "$SERVICE_FILE" ]; then
        rm -f "$SERVICE_FILE"
        systemctl daemon-reload
        print_status "Service file removed"
    else
        print_warning "Service file not found"
    fi
}

# Function to remove application files
remove_app_files() {
    print_status "Removing application files..."
    
    if [ -d "$APP_DIR" ]; then
        rm -rf "$APP_DIR"
        print_status "Application directory removed: $APP_DIR"
    else
        print_warning "Application directory not found: $APP_DIR"
    fi
}

# Function to remove log files
remove_logs() {
    print_status "Removing log files..."
    
    if [ -d "$LOG_DIR" ]; then
        rm -rf "$LOG_DIR"
        print_status "Log directory removed: $LOG_DIR"
    else
        print_warning "Log directory not found: $LOG_DIR"
    fi
}

# Function to remove data files
remove_data() {
    print_status "Removing data files..."
    
    if [ -d "$DATA_DIR" ]; then
        rm -rf "$DATA_DIR"
        print_status "Data directory removed: $DATA_DIR"
    else
        print_warning "Data directory not found: $DATA_DIR"
    fi
}

# Function to remove user and group
remove_user() {
    print_status "Removing user and group..."
    
    if getent passwd $APP_USER > /dev/null 2>&1; then
        userdel $APP_USER
        print_status "User removed: $APP_USER"
    else
        print_warning "User not found: $APP_USER"
    fi
    
    if getent group $APP_GROUP > /dev/null 2>&1; then
        groupdel $APP_GROUP
        print_status "Group removed: $APP_GROUP"
    else
        print_warning "Group not found: $APP_GROUP"
    fi
}

# Function to remove run directory
remove_run_dir() {
    print_status "Removing run directory..."
    
    if [ -d "/var/run/incident-reports" ]; then
        rm -rf "/var/run/incident-reports"
        print_status "Run directory removed: /var/run/incident-reports"
    else
        print_warning "Run directory not found: /var/run/incident-reports"
    fi
}

# Function to confirm uninstall
confirm_uninstall() {
    echo ""
    echo "This will completely remove the Incident Reports Application from your system."
    echo ""
    echo "The following will be removed:"
    echo "  - System service: incident-reports"
    echo "  - Application files: $APP_DIR"
    echo "  - Log files: $LOG_DIR"
    echo "  - Data files: $DATA_DIR"
    echo "  - User and group: $APP_USER/$APP_GROUP"
    echo "  - Run directory: /var/run/incident-reports"
    echo ""
    echo "⚠️  WARNING: This will permanently delete all application data!"
    echo ""
    read -p "Are you sure you want to continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Uninstall cancelled"
        exit 0
    fi
}

# Function to display completion message
display_completion() {
    echo ""
    echo "=========================================="
    echo "🗑️  Uninstall completed successfully!"
    echo "=========================================="
    echo ""
    echo "The Incident Reports Application has been completely removed from your system."
    echo ""
    echo "If you want to reinstall, you can run the deploy.sh script again."
    echo ""
}

# Main execution
main() {
    print_status "Starting uninstall of Incident Reports Application..."
    
    check_root
    confirm_uninstall
    stop_service
    remove_service_file
    remove_app_files
    remove_logs
    remove_data
    remove_user
    remove_run_dir
    display_completion
}

# Run main function
main "$@" 