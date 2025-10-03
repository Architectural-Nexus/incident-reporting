#!/bin/bash

# Incident Reporting System - Update Script
# This script updates the application while preserving data

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

APP_DIR="/opt/incident-reporting"
BACKUP_DIR="/opt/incident-reporting/backups"

echo -e "${GREEN}🔄 Updating Incident Reporting System${NC}"
echo "=================================================="

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}❌ This script must be run as root (use sudo)${NC}"
   exit 1
fi

# Stop the service
echo -e "${YELLOW}⏹️ Stopping service...${NC}"
systemctl stop incident-reporting

# Create backup
echo -e "${YELLOW}💾 Creating backup...${NC}"
mkdir -p $BACKUP_DIR
cp $APP_DIR/instance/incidents.db $BACKUP_DIR/incidents-$(date +%Y%m%d-%H%M%S).db

# Update application files
echo -e "${YELLOW}📦 Updating application files...${NC}"
cd $APP_DIR

# If using git, pull updates
if [ -d ".git" ]; then
    sudo -u www-data git pull
else
    echo -e "${YELLOW}📋 Please copy new files to $APP_DIR${NC}"
    echo -e "${YELLOW}Press Enter when ready to continue...${NC}"
    read
fi

# Update Python dependencies
echo -e "${YELLOW}🐍 Updating Python dependencies...${NC}"
sudo -u www-data venv/bin/pip install --upgrade pip
sudo -u www-data venv/bin/pip install -r requirements.txt

# Set proper permissions
echo -e "${YELLOW}🔐 Setting permissions...${NC}"
chown -R www-data:www-data $APP_DIR
chmod 600 $APP_DIR/.env

# Start the service
echo -e "${YELLOW}🚀 Starting service...${NC}"
systemctl start incident-reporting

# Check service status
sleep 5
if systemctl is-active --quiet incident-reporting; then
    echo -e "${GREEN}✅ Update completed successfully!${NC}"
    echo -e "${GREEN}✅ Service is running${NC}"
else
    echo -e "${RED}❌ Service failed to start. Check logs with: journalctl -u incident-reporting${NC}"
    exit 1
fi

echo -e "${GREEN}🎉 Update completed!${NC}"
