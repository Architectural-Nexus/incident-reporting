#!/bin/bash

# Incident Reporting System - Backup Script
# This script creates backups of the application and database

set -e

# Configuration
APP_DIR="/opt/incident-reporting"
BACKUP_DIR="/opt/incident-reporting/backups"
DATE=$(date +%Y%m%d-%H%M%S)
BACKUP_FILE="incident-reporting-backup-$DATE.tar.gz"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}🔄 Creating backup of Incident Reporting System${NC}"
echo "=================================================="

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Create backup
echo -e "${YELLOW}📦 Creating backup archive...${NC}"
cd /opt
tar -czf $BACKUP_DIR/$BACKUP_FILE \
    --exclude='incident-reporting/venv' \
    --exclude='incident-reporting/__pycache__' \
    --exclude='incident-reporting/*.pyc' \
    --exclude='incident-reporting/.git' \
    incident-reporting/

# Set proper permissions
chown www-data:www-data $BACKUP_DIR/$BACKUP_FILE
chmod 600 $BACKUP_DIR/$BACKUP_FILE

echo -e "${GREEN}✅ Backup created: $BACKUP_DIR/$BACKUP_FILE${NC}"

# Clean up old backups (keep last 7 days)
echo -e "${YELLOW}🧹 Cleaning up old backups...${NC}"
find $BACKUP_DIR -name "incident-reporting-backup-*.tar.gz" -mtime +7 -delete

echo -e "${GREEN}🎉 Backup completed successfully!${NC}"
