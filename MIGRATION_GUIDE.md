# Migration Guide: Local to incidents.archnexus.com

## Step 1: Check Current Server Configuration

First, SSH into the server and run the configuration check script:

```bash
# Copy the check script to the server
scp check_server_config.sh root@incidents.archnexus.com:/tmp/

# SSH into the server
ssh root@incidents.archnexus.com

# Run the check script
bash /tmp/check_server_config.sh > server_config_report.txt
cat server_config_report.txt
```

Or manually check these key items:

```bash
# Check if application exists
ls -la /opt/incident-reporting/

# Check systemd service
systemctl status incident-reporting 2>/dev/null || systemctl status incident-reports 2>/dev/null

# Check web server
ls -la /etc/nginx/sites-available/incident* 2>/dev/null
ls -la /etc/httpd/conf.d/incident* 2>/dev/null

# Check database
ls -la /opt/incident-reporting/instance/incidents.db 2>/dev/null
ls -la /var/lib/incident-reports/incidents.db 2>/dev/null
```

## Step 2: Determine Migration Type

### Scenario A: Fresh Installation (No existing app)
If `/opt/incident-reporting` doesn't exist, proceed with a fresh installation.

### Scenario B: Update Existing Installation
If the application already exists, you'll need to:
1. Backup existing database
2. Backup existing configuration
3. Update application files
4. Migrate database schema if needed

## Step 3: Prepare Deployment Package

On your local machine:

```bash
cd /Users/khansen/Documents/GitHub/incident-reporting

# Create deployment package (exclude unnecessary files)
tar -czf incident-reporting-deploy.tar.gz \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    --exclude='instance' \
    --exclude='*.log' \
    --exclude='.env' \
    --exclude='*.db' \
    --exclude='*.tar.gz' \
    .
```

## Step 4: Upload to Server

```bash
# Upload the package
scp incident-reporting-deploy.tar.gz root@incidents.archnexus.com:/tmp/
```

## Step 5: Deployment Steps

### For Fresh Installation (Ubuntu/Debian):

```bash
# SSH into server
ssh root@incidents.archnexus.com

# Extract package
cd /tmp
tar -xzf incident-reporting-deploy.tar.gz
cd incident-reporting

# Run automated installation
sudo ./deploy/install.sh
```

### For Fresh Installation (AlmaLinux/RHEL):

The project has AlmaLinux deployment scripts. Check if the server is AlmaLinux:

```bash
cat /etc/os-release | grep -i "almalinux\|rhel\|centos"
```

If AlmaLinux, use the deployment script from the README:

```bash
# Extract and deploy
cd /tmp
tar -xzf incident-reporting-deploy.tar.gz
cd incident-reporting
sudo chmod +x deploy.sh
sudo ./deploy.sh
```

### For Update Existing Installation:

```bash
# SSH into server
ssh root@incidents.archnexus.com

# Backup existing installation
BACKUP_DIR="/opt/incident-reporting-backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p $BACKUP_DIR
cp -r /opt/incident-reporting/* $BACKUP_DIR/

# Backup database
cp /opt/incident-reporting/instance/incidents.db $BACKUP_DIR/incidents.db.backup

# Stop service
systemctl stop incident-reporting 2>/dev/null || systemctl stop incident-reports 2>/dev/null

# Extract new files
cd /tmp
tar -xzf incident-reporting-deploy.tar.gz
cd incident-reporting

# Copy files (preserve .env and database)
cp -r * /opt/incident-reporting/
# Don't overwrite .env
cp /opt/incident-reporting/.env /opt/incident-reporting/.env.backup
# Restore .env
mv /opt/incident-reporting/.env.backup /opt/incident-reporting/.env

# Update Python dependencies
cd /opt/incident-reporting
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Set permissions
chown -R www-data:www-data /opt/incident-reporting
chmod 600 /opt/incident-reporting/.env

# Run database migrations (if any)
# The app.py will auto-migrate on startup, but you can also:
source venv/bin/activate
python -c "from app import app, db; app.app_context().push(); db.create_all()"

# Start service
systemctl start incident-reporting 2>/dev/null || systemctl start incident-reports 2>/dev/null
systemctl status incident-reporting 2>/dev/null || systemctl status incident-reports 2>/dev/null
```

## Step 6: Configuration Updates

### Update Nginx/Apache Configuration

**For Nginx (Ubuntu):**
```bash
# Edit nginx config
nano /etc/nginx/sites-available/incident-reporting

# Update server_name to incidents.archnexus.com
# Test and reload
nginx -t
systemctl reload nginx
```

**For Apache (AlmaLinux):**
```bash
# Edit Apache config
nano /etc/httpd/conf.d/incident-reports.conf

# Update ServerName to incidents.archnexus.com
# Test and restart
httpd -t
systemctl restart httpd
```

### Update Environment Variables

```bash
# Edit .env file
nano /opt/incident-reporting/.env
```

Key variables to check/update:
- `SECRET_KEY` - Should be a strong random key
- `FLASK_ENV=production`
- `DATABASE_URL` - Usually `sqlite:///instance/incidents.db`
- Email configuration (if using email notifications)

### Update Systemd Service (if needed)

```bash
# Check service file
cat /etc/systemd/system/incident-reporting.service

# If using different paths, update:
nano /etc/systemd/system/incident-reporting.service

# Reload systemd
systemctl daemon-reload
systemctl restart incident-reporting
```

## Step 7: SSL/HTTPS Configuration

If SSL is not already configured:

```bash
# For Let's Encrypt (Ubuntu/Nginx)
certbot --nginx -d incidents.archnexus.com

# For Let's Encrypt (AlmaLinux/Apache)
certbot --apache -d incidents.archnexus.com

# Or use the provided SSL setup script
cd /opt/incident-reporting
sudo ./setup_ssl.sh
```

## Step 8: Verify Installation

```bash
# Check service status
systemctl status incident-reporting

# Check logs
journalctl -u incident-reporting -f

# Test web server
curl -I http://incidents.archnexus.com
curl -I https://incidents.archnexus.com

# Check application
curl http://incidents.archnexus.com/admin/login
```

## Step 9: Security Checklist

- [ ] Change default admin password (`admin` / `admin123`)
- [ ] Verify SSL certificate is working
- [ ] Check firewall rules (allow SSH, HTTP, HTTPS)
- [ ] Verify file permissions:
  ```bash
  chown -R www-data:www-data /opt/incident-reporting
  chmod 600 /opt/incident-reporting/.env
  chmod 644 /opt/incident-reporting/instance/incidents.db
  ```
- [ ] Review fail2ban status: `systemctl status fail2ban`
- [ ] Test admin login at https://incidents.archnexus.com/admin/login

## Step 10: Database Migration (if updating)

If you're updating an existing installation and the database schema has changed:

```bash
cd /opt/incident-reporting
source venv/bin/activate

# The app will auto-create missing tables on startup
# But you can also manually run:
python -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('Database schema updated')
"
```

## Troubleshooting

### Service Won't Start
```bash
# Check logs
journalctl -u incident-reporting -n 50

# Check permissions
ls -la /opt/incident-reporting/
ls -la /opt/incident-reporting/instance/

# Test manually
cd /opt/incident-reporting
source venv/bin/activate
python app.py
```

### Web Server Issues
```bash
# Nginx
nginx -t
systemctl status nginx
tail -f /var/log/nginx/error.log

# Apache
httpd -t
systemctl status httpd
tail -f /var/log/httpd/error_log
```

### Database Issues
```bash
# Check database file
ls -la /opt/incident-reporting/instance/incidents.db

# Fix permissions
chown www-data:www-data /opt/incident-reporting/instance/incidents.db
chmod 644 /opt/incident-reporting/instance/incidents.db

# Backup before any operations
cp /opt/incident-reporting/instance/incidents.db /opt/incident-reporting/instance/incidents.db.backup
```

## Key Differences: Local vs Production

| Aspect | Local (Development) | Production (Server) |
|--------|-------------------|-------------------|
| Port | 5002 | 80/443 (via nginx/apache) |
| Database | `instance/incidents.db` | `/opt/incident-reporting/instance/incidents.db` |
| User | Your user | `www-data` |
| Server | Flask dev server | Gunicorn + nginx/apache |
| Debug | Enabled | Disabled |
| Logs | `incident_reports.log` | `journalctl` or `/var/log/` |

## Post-Migration Tasks

1. **Test all functionality:**
   - Submit a test incident report
   - Login to admin dashboard
   - Export CSV
   - Export PDF
   - Test email notifications (if configured)

2. **Monitor logs:**
   ```bash
   journalctl -u incident-reporting -f
   ```

3. **Set up backups:**
   ```bash
   # Add to crontab
   crontab -e
   # Add: 0 2 * * * cp /opt/incident-reporting/instance/incidents.db /opt/backups/incidents-$(date +\%Y\%m\%d).db
   ```

4. **Document configuration:**
   - Save a copy of `.env` (securely)
   - Document any custom configurations
   - Note any manual changes made

## Rollback Plan

If something goes wrong:

```bash
# Stop service
systemctl stop incident-reporting

# Restore from backup
BACKUP_DIR="/opt/incident-reporting-backup-YYYYMMDD-HHMMSS"
cp -r $BACKUP_DIR/* /opt/incident-reporting/

# Restore database
cp $BACKUP_DIR/incidents.db.backup /opt/incident-reporting/instance/incidents.db

# Restart service
systemctl start incident-reporting
```
