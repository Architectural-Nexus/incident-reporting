#!/bin/bash

# Incident Reporting System - Ubuntu Deployment Script
# This script installs and configures the Incident Reporting System on Ubuntu

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="incident-reporting"
APP_DIR="/opt/$APP_NAME"
APP_USER="www-data"
APP_GROUP="www-data"
DOMAIN="your-domain.com"  # Change this to your domain or IP

echo -e "${GREEN}🚀 Starting Incident Reporting System Deployment${NC}"
echo "=================================================="

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}❌ This script must be run as root (use sudo)${NC}"
   exit 1
fi

# Update system packages
echo -e "${YELLOW}📦 Updating system packages...${NC}"
apt update && apt upgrade -y

# Install required system packages
echo -e "${YELLOW}📦 Installing system dependencies...${NC}"
apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    nginx \
    supervisor \
    git \
    curl \
    ufw \
    fail2ban \
    certbot \
    python3-certbot-nginx

# Create application directory
echo -e "${YELLOW}📁 Creating application directory...${NC}"
mkdir -p $APP_DIR
chown $APP_USER:$APP_GROUP $APP_DIR

# Copy application files
echo -e "${YELLOW}📋 Copying application files...${NC}"
cp -r . $APP_DIR/
cd $APP_DIR

# Create virtual environment
echo -e "${YELLOW}🐍 Creating Python virtual environment...${NC}"
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo -e "${YELLOW}📦 Installing Python dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

# Set up environment file
echo -e "${YELLOW}⚙️ Setting up environment configuration...${NC}"
if [ ! -f .env ]; then
    cp env.example .env
    echo -e "${YELLOW}📝 Please edit $APP_DIR/.env with your configuration${NC}"
fi

# Set proper permissions
echo -e "${YELLOW}🔐 Setting file permissions...${NC}"
chown -R $APP_USER:$APP_GROUP $APP_DIR
chmod +x wsgi.py
chmod 600 .env

# Create database
echo -e "${YELLOW}🗄️ Initializing database...${NC}"
sudo -u $APP_USER bash -c "cd $APP_DIR && source venv/bin/activate && python -c 'from app import init_db; init_db()'"

# Configure systemd service
echo -e "${YELLOW}⚙️ Configuring systemd service...${NC}"
cp deploy/incident-reporting.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable incident-reporting

# Configure nginx
echo -e "${YELLOW}🌐 Configuring nginx...${NC}"
cp deploy/nginx.conf /etc/nginx/sites-available/$APP_NAME
sed -i "s/your-domain.com/$DOMAIN/g" /etc/nginx/sites-available/$APP_NAME
ln -sf /etc/nginx/sites-available/$APP_NAME /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test nginx configuration
nginx -t

# Configure firewall
echo -e "${YELLOW}🔥 Configuring firewall...${NC}"
ufw --force enable
ufw allow ssh
ufw allow 'Nginx Full'

# Configure fail2ban
echo -e "${YELLOW}🛡️ Configuring fail2ban...${NC}"
cat > /etc/fail2ban/jail.local << EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[nginx-http-auth]
enabled = true

[nginx-limit-req]
enabled = true
EOF

systemctl enable fail2ban
systemctl restart fail2ban

# Start services
echo -e "${YELLOW}🚀 Starting services...${NC}"
systemctl restart nginx
systemctl start incident-reporting

# Check service status
echo -e "${YELLOW}📊 Checking service status...${NC}"
sleep 5
if systemctl is-active --quiet incident-reporting; then
    echo -e "${GREEN}✅ Incident Reporting System is running!${NC}"
else
    echo -e "${RED}❌ Service failed to start. Check logs with: journalctl -u incident-reporting${NC}"
fi

if systemctl is-active --quiet nginx; then
    echo -e "${GREEN}✅ Nginx is running!${NC}"
else
    echo -e "${RED}❌ Nginx failed to start. Check logs with: journalctl -u nginx${NC}"
fi

echo ""
echo -e "${GREEN}🎉 Deployment Complete!${NC}"
echo "=================================================="
echo -e "${YELLOW}📋 Next Steps:${NC}"
echo "1. Edit $APP_DIR/.env with your configuration"
echo "2. Update /etc/nginx/sites-available/$APP_NAME with your domain"
echo "3. Restart services: systemctl restart incident-reporting nginx"
echo "4. Set up SSL certificate: certbot --nginx -d $DOMAIN"
echo ""
echo -e "${YELLOW}🔧 Useful Commands:${NC}"
echo "• Check service status: systemctl status incident-reporting"
echo "• View logs: journalctl -u incident-reporting -f"
echo "• Restart service: systemctl restart incident-reporting"
echo "• Check nginx: nginx -t && systemctl reload nginx"
echo ""
echo -e "${YELLOW}🌐 Access your application at: http://$DOMAIN${NC}"
echo -e "${YELLOW}👤 Default admin login: admin / admin123${NC}"
echo -e "${RED}⚠️  IMPORTANT: Change the default admin password immediately!${NC}"
