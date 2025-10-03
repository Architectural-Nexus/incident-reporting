# Incident Reporting System - Ubuntu Deployment Guide

## Overview
This guide will help you deploy the Incident Reporting System on Ubuntu as a production service with nginx, systemd, and security hardening.

## Prerequisites
- Ubuntu 20.04 LTS or newer
- Root/sudo access
- Domain name or IP address for the server
- Basic knowledge of Linux administration

## Quick Deployment

### 1. Upload Files to Server
```bash
# On your local machine, create a deployment package
tar -czf incident-reporting-deploy.tar.gz \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    --exclude='instance' \
    --exclude='deploy' \
    .

# Upload to server
scp incident-reporting-deploy.tar.gz user@your-server:/tmp/
```

### 2. Run Installation Script
```bash
# SSH to your server
ssh user@your-server

# Extract and run installation
cd /tmp
tar -xzf incident-reporting-deploy.tar.gz
cd incident-reporting
sudo ./deploy/install.sh
```

## Manual Deployment Steps

### 1. System Preparation
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3 python3-pip python3-venv python3-dev nginx supervisor git curl ufw fail2ban certbot python3-certbot-nginx
```

### 2. Application Setup
```bash
# Create application directory
sudo mkdir -p /opt/incident-reporting
sudo chown www-data:www-data /opt/incident-reporting

# Copy application files
sudo cp -r . /opt/incident-reporting/
cd /opt/incident-reporting

# Create virtual environment
sudo -u www-data python3 -m venv venv
sudo -u www-data venv/bin/pip install --upgrade pip
sudo -u www-data venv/bin/pip install -r requirements.txt
```

### 3. Configuration
```bash
# Set up environment
sudo cp env.example .env
sudo chmod 600 .env
sudo chown www-data:www-data .env

# Initialize database
sudo -u www-data bash -c "cd /opt/incident-reporting && source venv/bin/activate && python -c 'from app import init_db; init_db()'"
```

### 4. Systemd Service
```bash
# Copy service file
sudo cp deploy/incident-reporting.service /etc/systemd/system/

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable incident-reporting
sudo systemctl start incident-reporting
```

### 5. Nginx Configuration
```bash
# Copy nginx config
sudo cp deploy/nginx.conf /etc/nginx/sites-available/incident-reporting

# Update domain in config
sudo sed -i 's/your-domain.com/your-actual-domain.com/g' /etc/nginx/sites-available/incident-reporting

# Enable site
sudo ln -sf /etc/nginx/sites-available/incident-reporting /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test and restart nginx
sudo nginx -t
sudo systemctl restart nginx
```

### 6. Security Configuration
```bash
# Configure firewall
sudo ufw --force enable
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'

# Configure fail2ban
sudo systemctl enable fail2ban
sudo systemctl restart fail2ban
```

### 7. SSL Certificate (Optional but Recommended)
```bash
# Install SSL certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

## Configuration Files

### Environment Variables (.env)
```bash
# Database
DATABASE_URL=sqlite:///instance/incidents.db

# Security
SECRET_KEY=your-secret-key-here
FLASK_ENV=production

# Email Configuration
MAIL_SERVER=smtp.your-domain.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@your-domain.com
MAIL_PASSWORD=your-email-password
MAIL_DEFAULT_SENDER=your-email@your-domain.com
```

### Systemd Service Configuration
The service file is located at `/etc/systemd/system/incident-reporting.service` and includes:
- Automatic restart on failure
- Proper user/group permissions
- Logging configuration
- Resource limits

### Nginx Configuration
The nginx configuration includes:
- Security headers
- Static file serving
- Gzip compression
- Proxy configuration
- SSL termination

## Service Management

### Start/Stop/Restart Service
```bash
sudo systemctl start incident-reporting
sudo systemctl stop incident-reporting
sudo systemctl restart incident-reporting
sudo systemctl reload incident-reporting
```

### Check Service Status
```bash
sudo systemctl status incident-reporting
sudo journalctl -u incident-reporting -f
```

### Update Application
```bash
# Stop service
sudo systemctl stop incident-reporting

# Backup database
sudo cp /opt/incident-reporting/instance/incidents.db /opt/incident-reporting/instance/incidents.db.backup

# Update code
cd /opt/incident-reporting
sudo -u www-data git pull  # if using git
# OR copy new files manually

# Update dependencies
sudo -u www-data venv/bin/pip install -r requirements.txt

# Start service
sudo systemctl start incident-reporting
```

## Monitoring and Logs

### Application Logs
```bash
# View real-time logs
sudo journalctl -u incident-reporting -f

# View recent logs
sudo journalctl -u incident-reporting --since "1 hour ago"
```

### Nginx Logs
```bash
# Access logs
sudo tail -f /var/log/nginx/access.log

# Error logs
sudo tail -f /var/log/nginx/error.log
```

### System Monitoring
```bash
# Check service status
sudo systemctl status incident-reporting nginx

# Check disk usage
df -h

# Check memory usage
free -h

# Check running processes
ps aux | grep incident-reporting
```

## Security Considerations

### Default Credentials
- **IMPORTANT**: Change the default admin password immediately after deployment
- Default login: `admin` / `admin123`

### File Permissions
```bash
# Ensure proper permissions
sudo chown -R www-data:www-data /opt/incident-reporting
sudo chmod 600 /opt/incident-reporting/.env
sudo chmod 755 /opt/incident-reporting
```

### Database Security
- Database file is located at `/opt/incident-reporting/instance/incidents.db`
- Ensure proper file permissions (600)
- Regular backups recommended

### Network Security
- Firewall configured to only allow SSH and HTTP/HTTPS
- Fail2ban configured for intrusion prevention
- Consider VPN access for admin functions

## Troubleshooting

### Service Won't Start
```bash
# Check service status
sudo systemctl status incident-reporting

# Check logs
sudo journalctl -u incident-reporting -n 50

# Check configuration
sudo -u www-data /opt/incident-reporting/venv/bin/python /opt/incident-reporting/app.py
```

### Nginx Issues
```bash
# Test configuration
sudo nginx -t

# Check nginx status
sudo systemctl status nginx

# Check nginx logs
sudo tail -f /var/log/nginx/error.log
```

### Database Issues
```bash
# Check database file permissions
ls -la /opt/incident-reporting/instance/

# Recreate database if needed
sudo -u www-data bash -c "cd /opt/incident-reporting && source venv/bin/activate && python -c 'from app import init_db; init_db()'"
```

## Backup and Recovery

### Database Backup
```bash
# Create backup
sudo cp /opt/incident-reporting/instance/incidents.db /opt/incident-reporting/backups/incidents-$(date +%Y%m%d-%H%M%S).db

# Restore from backup
sudo cp /opt/incident-reporting/backups/incidents-YYYYMMDD-HHMMSS.db /opt/incident-reporting/instance/incidents.db
sudo chown www-data:www-data /opt/incident-reporting/instance/incidents.db
sudo systemctl restart incident-reporting
```

### Full Application Backup
```bash
# Create full backup
sudo tar -czf /opt/incident-reporting-backup-$(date +%Y%m%d).tar.gz /opt/incident-reporting
```

## Performance Optimization

### Gunicorn Workers
Adjust the number of workers in the systemd service file based on your server's CPU cores:
```bash
# For 2 CPU cores: --workers 3
# For 4 CPU cores: --workers 5
# For 8 CPU cores: --workers 9
```

### Database Optimization
- Consider migrating to PostgreSQL for better performance with multiple users
- Regular database maintenance and cleanup

### Caching
- Static files are cached by nginx
- Consider implementing Redis for session caching if needed

## Support and Maintenance

### Regular Maintenance Tasks
1. **Weekly**: Check service status and logs
2. **Monthly**: Update system packages
3. **Quarterly**: Review security logs and update dependencies
4. **Annually**: Review and update SSL certificates

### Getting Help
- Check application logs: `sudo journalctl -u incident-reporting -f`
- Check nginx logs: `sudo tail -f /var/log/nginx/error.log`
- Verify configuration: `sudo nginx -t`
- Test application manually: `sudo -u www-data /opt/incident-reporting/venv/bin/python /opt/incident-reporting/app.py`
