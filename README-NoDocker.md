# Incident Reports Application - Production Deployment

This document explains how to deploy and run the Incident Reports Application as a system service for production use.

## Prerequisites

- Linux system with systemd (Ubuntu 18.04+, CentOS 7+, etc.)
- Python 3.8 or higher
- pip3
- Root access (for system service deployment)

## Quick Start

### Option 1: Automated Deployment (Recommended)

1. **Clone or download the application files**
   ```bash
   # Make sure you have all the application files in a directory
   cd /path/to/incident-reports
   ```

2. **Run the deployment script**
   ```bash
   sudo chmod +x deploy.sh
   sudo ./deploy.sh
   ```

3. **Access the application**
   - Main application: http://localhost:8000
   - Admin panel: http://localhost:8000/admin/login
   - Default admin: `admin` / `admin123`

### Option 2: Manual Setup

1. **Run the initialization script**
   ```bash
   chmod +x init.sh
   ./init.sh
   ```

2. **Run the application**
   ```bash
   # Development mode
   ./run.sh
   
   # Production mode
   ./run_prod.sh
   ```

## Deployment Details

### What the deployment script does:

1. **Creates system user and group**: `incident-reports`
2. **Sets up directories**:
   - Application: `/opt/incident-reports`
   - Logs: `/var/log/incident-reports`
   - Data: `/var/lib/incident-reports`
3. **Creates Python virtual environment**
4. **Installs dependencies**
5. **Creates systemd service**
6. **Initializes database**
7. **Creates default admin user**
8. **Starts and enables the service**

### Service Management

Once deployed, you can manage the service using systemctl:

```bash
# Check service status
sudo systemctl status incident-reports

# Start the service
sudo systemctl start incident-reports

# Stop the service
sudo systemctl stop incident-reports

# Restart the service
sudo systemctl restart incident-reports

# Enable auto-start on boot
sudo systemctl enable incident-reports

# Disable auto-start on boot
sudo systemctl disable incident-reports

# View logs
sudo journalctl -u incident-reports -f
```

### Configuration

#### Environment Variables

The service uses the following environment variables (set in the service file):

- `FLASK_APP=app.py`
- `FLASK_ENV=production`
- `SECRET_KEY=your-secret-key-change-this-in-production`
- `DATABASE_URL=sqlite:////var/lib/incident-reports/incidents.db`

#### Updating Configuration

To update the configuration:

1. **Edit the service file**:
   ```bash
   sudo nano /etc/systemd/system/incident-reports.service
   ```

2. **Reload systemd and restart the service**:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl restart incident-reports
   ```

#### Security Considerations

⚠️ **IMPORTANT**: Before using in production:

1. **Change the default admin password**:
   - Log in to the admin panel
   - Go to Users management
   - Change the admin password

2. **Update the SECRET_KEY**:
   - Generate a secure random key
   - Update it in the service file
   - Restart the service

3. **Configure firewall**:
   - The deployment script attempts to configure firewall rules
   - Verify port 8000 is properly secured

4. **Use HTTPS in production**:
   - Set up a reverse proxy (nginx/apache) with SSL
   - Configure the application behind the proxy

## File Structure

After deployment, the application files are organized as follows:

```
/opt/incident-reports/          # Application files
├── app.py                      # Main application
├── requirements.txt            # Python dependencies
├── gunicorn.conf.py           # Gunicorn configuration
├── venv/                      # Python virtual environment
├── templates/                 # HTML templates
├── static/                    # Static files
└── ...

/var/log/incident-reports/      # Application logs
├── access.log                 # Access logs
└── error.log                  # Error logs

/var/lib/incident-reports/      # Application data
└── incidents.db               # SQLite database

/etc/systemd/system/           # System service
└── incident-reports.service   # Service definition
```

## Troubleshooting

### Service won't start

1. **Check service status**:
   ```bash
   sudo systemctl status incident-reports
   ```

2. **Check logs**:
   ```bash
   sudo journalctl -u incident-reports -n 50
   ```

3. **Check file permissions**:
   ```bash
   sudo ls -la /opt/incident-reports/
   sudo ls -la /var/log/incident-reports/
   sudo ls -la /var/lib/incident-reports/
   ```

### Common Issues

1. **Permission denied errors**:
   - Ensure the `incident-reports` user owns all application files
   - Check that log and data directories are writable

2. **Port already in use**:
   - Check if another service is using port 8000
   - Change the port in `gunicorn.conf.py` and the service file

3. **Database errors**:
   - Ensure the data directory is writable
   - Check database file permissions

### Uninstalling

To completely remove the application:

```bash
sudo chmod +x uninstall.sh
sudo ./uninstall.sh
```

⚠️ **Warning**: This will permanently delete all application data!

## Development vs Production

### Development Mode

- Uses Flask development server
- Debug mode enabled
- Auto-reload on code changes
- Less secure, not suitable for production

### Production Mode

- Uses Gunicorn WSGI server
- Multiple worker processes
- Proper logging
- More secure and performant

## Backup and Recovery

### Database Backup

```bash
# Backup the database
sudo cp /var/lib/incident-reports/incidents.db /backup/incidents_$(date +%Y%m%d_%H%M%S).db

# Restore from backup
sudo cp /backup/incidents_backup.db /var/lib/incident-reports/incidents.db
sudo chown incident-reports:incident-reports /var/lib/incident-reports/incidents.db
sudo systemctl restart incident-reports
```

### Full Application Backup

```bash
# Backup application files
sudo tar -czf /backup/incident-reports_$(date +%Y%m%d_%H%M%S).tar.gz \
    /opt/incident-reports \
    /var/lib/incident-reports \
    /var/log/incident-reports \
    /etc/systemd/system/incident-reports.service
```

## Support

For issues and questions:

1. Check the troubleshooting section above
2. Review the application logs
3. Check system service status
4. Verify file permissions and ownership

## Data Migration

If you're migrating from a previous installation:

1. **Backup existing data**:
   ```bash
   # Backup your existing database
   sudo cp /path/to/old/incidents.db /backup/location/
   ```

2. **Deploy using the deployment script**:
   ```bash
   sudo ./deploy.sh
   ```

3. **Restore data** (if needed):
   ```bash
   # Copy database to new location
   sudo cp /backup/location/incidents.db /var/lib/incident-reports/
   sudo chown -R incident-reports:incident-reports /var/lib/incident-reports/
   
   # Run database migration if needed
   cd /opt/incident-reports
   sudo -u incident-reports python migrate_database.py /var/lib/incident-reports/incidents.db
   
   # Restart the service
   sudo systemctl restart incident-reports
   ``` 