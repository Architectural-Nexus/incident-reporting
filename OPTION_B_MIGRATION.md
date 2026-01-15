# Option B Migration Guide: /opt/incident-reporting

## Overview

This guide migrates the Incident Reporting System from `/opt/incident-reports` to `/opt/incident-reporting` to standardize the path across AlmaLinux and Ubuntu deployments.

## Pre-Migration Checklist

Before running the migration:

- [ ] SSH access to `incidents.archnexus.com` as root
- [ ] Git repository cloned to `/opt/incident-reporting` (or will be cloned)
- [ ] Backup of current database (script will do this automatically)
- [ ] Access to review logs if issues occur
- [ ] **Verified other sites (assets.archnexus.com, revitfam.archnexus.com) are backed up** (optional but recommended)

## Safety Guarantees

✅ **Other sites are protected:**
- The migration script **ONLY** modifies `/etc/httpd/conf.d/incident-reports.conf`
- Sites in `/var/www/html` (assets, revitfam) are **NOT touched**
- The script includes safety checks to prevent accidental modifications
- Apache configuration is tested before applying changes
- If Apache config test fails, changes are automatically rolled back

✅ **What the script does:**
- Only updates paths in `incident-reports.conf` (incidents.archnexus.com)
- Creates backups before any modifications
- Tests Apache configuration before restarting
- Verifies other site configs are still present after restart

✅ **What the script does NOT do:**
- Does NOT modify `/var/www/html` or any files within it
- Does NOT touch `assets.conf` or `revitfam.conf`
- Does NOT change any other Apache virtual host configurations
- Does NOT modify SSL certificates or other site settings

## Current State

- **Old Path**: `/opt/incident-reports` (deleted, but process still running)
- **New Path**: `/opt/incident-reporting` (git repository)
- **Database**: `/var/lib/incident-reports/incidents.db` (will be migrated)
- **Service**: `incident-reports.service` (will become `incident-reporting.service`)
- **OS**: AlmaLinux 8.10

## Migration Steps

### Step 1: Ensure Git Repository is Ready

The repository should already be at `/opt/incident-reporting`. Verify:

```bash
ssh root@incidents.archnexus.com
cd /opt/incident-reporting
git status
git pull origin main  # Ensure latest code
```

### Step 2: Upload Migration Script

From your local machine:

```bash
cd /Users/khansen/Documents/GitHub/incident-reporting
scp migrate_to_incident_reporting.sh root@incidents.archnexus.com:/tmp/
```

### Step 3: Run Migration Script

On the server:

```bash
ssh root@incidents.archnexus.com
chmod +x /tmp/migrate_to_incident_reporting.sh
/tmp/migrate_to_incident_reporting.sh
```

The script will:
1. ✅ Create backups
2. ✅ Stop old service
3. ✅ Set up new directory structure
4. ✅ Install Python dependencies
5. ✅ Migrate database
6. ✅ Configure environment
7. ✅ Update systemd service
8. ✅ Update Apache configuration
9. ✅ Set file permissions
10. ✅ Start new service
11. ✅ Restart web server

### Step 4: Verify Migration

```bash
# Check service status
systemctl status incident-reporting

# Check logs
journalctl -u incident-reporting -n 50

# Test web server
curl -I https://incidents.archnexus.com

# Verify database
ls -lh /opt/incident-reporting/instance/incidents.db

# Verify other sites are still working
curl -I http://assets.archnexus.com
curl -I http://revitfam.archnexus.com

# Check Apache configs are intact
ls -la /etc/httpd/conf.d/assets.conf
ls -la /etc/httpd/conf.d/revitfam.conf
```

### Step 5: Update Configuration

Review and update the `.env` file:

```bash
nano /opt/incident-reporting/.env
```

Key settings to verify:
- `SECRET_KEY` - Should be a strong random key
- `FLASK_ENV=production`
- `DATABASE_URL=sqlite:///instance/incidents.db`
- Email configuration (if using)

### Step 6: Test Application

1. Visit: https://incidents.archnexus.com
2. Test incident submission
3. Login to admin: https://incidents.archnexus.com/admin/login
4. Verify database operations

## What Changes

### Directory Structure
- **Old**: `/opt/incident-reports/`
- **New**: `/opt/incident-reporting/`

### Database Location
- **Old**: `/var/lib/incident-reports/incidents.db`
- **New**: `/opt/incident-reporting/instance/incidents.db`

### Service Name
- **Old**: `incident-reports.service`
- **New**: `incident-reporting.service`

### Service File Location
- **Old**: `/etc/systemd/system/incident-reports.service`
- **New**: `/etc/systemd/system/incident-reporting.service`

## Rollback Procedure

If something goes wrong:

```bash
# Stop new service
systemctl stop incident-reporting

# Find backup directory
ls -la /opt/incident-reporting-backup-*

# Restore database
BACKUP_DIR="/opt/incident-reporting-backup-YYYYMMDD-HHMMSS"
cp $BACKUP_DIR/incidents.db.backup /var/lib/incident-reports/incidents.db

# Restore service file
cp $BACKUP_DIR/incident-reports.service.backup /etc/systemd/system/incident-reports.service

# Restore Apache config
cp $BACKUP_DIR/incident-reports-apache.conf.backup /etc/httpd/conf.d/incident-reports.conf

# Restart old service
systemctl daemon-reload
systemctl start incident-reports
systemctl restart httpd
```

## Post-Migration Tasks

1. **Update deploy.sh script** (optional, for future deployments)
   - Change `APP_DIR="/opt/incident-reports"` to `APP_DIR="/opt/incident-reporting"`
   - This ensures future deployments use the standard path

2. **Document the standard path**
   - Update any internal documentation
   - Note that both AlmaLinux and Ubuntu now use `/opt/incident-reporting`

3. **Monitor logs**
   ```bash
   journalctl -u incident-reporting -f
   ```

4. **Set up automated backups**
   ```bash
   # Add to crontab
   crontab -e
   # Add: 0 2 * * * cp /opt/incident-reporting/instance/incidents.db /opt/incident-reporting/backups/incidents-$(date +\%Y\%m\%d).db
   ```

## Troubleshooting

### Service Won't Start

```bash
# Check logs
journalctl -u incident-reporting -n 50

# Check permissions
ls -la /opt/incident-reporting/
ls -la /opt/incident-reporting/.env
ls -la /opt/incident-reporting/instance/

# Test manually
cd /opt/incident-reporting
source venv/bin/activate
python app.py
```

### Database Issues

```bash
# Check database file
ls -lh /opt/incident-reporting/instance/incidents.db

# Fix permissions
chown incident-reports:incident-reports /opt/incident-reporting/instance/incidents.db
chmod 644 /opt/incident-reporting/instance/incidents.db

# Verify database integrity
cd /opt/incident-reporting
source venv/bin/activate
python -c "from app import app, db; app.app_context().push(); print('Database OK')"
```

### Apache Issues

```bash
# Test configuration
httpd -t

# Check error logs
tail -f /var/log/httpd/incident_reports_error.log

# Restart Apache
systemctl restart httpd
```

### Permission Issues

```bash
# Fix ownership
chown -R incident-reports:incident-reports /opt/incident-reporting

# Fix specific permissions
chmod 755 /opt/incident-reporting
chmod 600 /opt/incident-reporting/.env
chmod 644 /opt/incident-reporting/instance/incidents.db
```

## Benefits of Option B

✅ **Consistent Path**: Same path on AlmaLinux and Ubuntu  
✅ **Matches Git Repo**: Directory name matches repository name  
✅ **Standardized**: Aligns with deployment scripts  
✅ **Easier Migration**: Future server migrations are simpler  
✅ **Better Documentation**: One path to document and maintain  

## Next Steps After Migration

1. Test all functionality thoroughly
2. Monitor logs for 24-48 hours
3. Update any internal documentation
4. Consider updating `deploy.sh` to use the new path
5. Set up monitoring and alerts
