#!/bin/bash

# Incident Reporting System - Package Creation Script
# This script creates a deployment package for Ubuntu

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PACKAGE_NAME="incident-reporting-ubuntu-deploy"
PACKAGE_FILE="$PACKAGE_NAME.tar.gz"

echo -e "${GREEN}📦 Creating Ubuntu deployment package${NC}"
echo "=================================================="

# Create package directory
echo -e "${YELLOW}📁 Creating package directory...${NC}"
mkdir -p $PACKAGE_NAME

# Copy application files
echo -e "${YELLOW}📋 Copying application files...${NC}"
cp -r app.py wsgi.py requirements.txt env.example templates static deploy $PACKAGE_NAME/

# Copy additional files
cp README.md $PACKAGE_NAME/ 2>/dev/null || echo "README.md not found, skipping"
cp additional_info.md $PACKAGE_NAME/ 2>/dev/null || echo "additional_info.md not found, skipping"

# Create deployment instructions
cat > $PACKAGE_NAME/DEPLOY_INSTRUCTIONS.txt << EOF
Incident Reporting System - Ubuntu Deployment Package
=====================================================

This package contains everything needed to deploy the Incident Reporting System on Ubuntu.

QUICK START:
1. Upload this package to your Ubuntu server
2. Extract: tar -xzf $PACKAGE_FILE
3. Run: sudo ./deploy/install.sh
4. Edit /opt/incident-reporting/.env with your configuration
5. Restart: sudo systemctl restart incident-reporting

FILES INCLUDED:
- app.py: Main Flask application
- wsgi.py: WSGI entry point
- requirements.txt: Python dependencies
- env.example: Environment configuration template
- templates/: HTML templates
- static/: Static assets (CSS, JS, images)
- deploy/: Deployment scripts and configurations

DEPLOYMENT SCRIPTS:
- install.sh: Automated installation script
- update.sh: Application update script
- backup.sh: Backup creation script
- incident-reporting.service: Systemd service file
- nginx.conf: Nginx configuration
- DEPLOYMENT.md: Detailed deployment guide

SECURITY NOTES:
- Change default admin password immediately after deployment
- Configure SSL certificate for production use
- Review firewall and security settings
- Regular backups recommended

For detailed instructions, see deploy/DEPLOYMENT.md

Default admin login: admin / admin123
⚠️  CHANGE THIS PASSWORD IMMEDIATELY!
EOF

# Create package
echo -e "${YELLOW}📦 Creating package archive...${NC}"
tar -czf $PACKAGE_FILE $PACKAGE_NAME/

# Clean up
rm -rf $PACKAGE_NAME

echo -e "${GREEN}✅ Package created: $PACKAGE_FILE${NC}"
echo -e "${GREEN}📋 Package size: $(du -h $PACKAGE_FILE | cut -f1)${NC}"
echo ""
echo -e "${YELLOW}🚀 Ready for deployment!${NC}"
echo -e "${YELLOW}Upload $PACKAGE_FILE to your Ubuntu server and follow DEPLOY_INSTRUCTIONS.txt${NC}"
