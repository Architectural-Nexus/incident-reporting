# Incident Reporting System

A Flask-based web application for reporting and managing incidents within an organization. This system provides a simple form for anonymous incident reporting and an admin interface for reviewing and exporting reports.

## Features

- **Public Incident Reporting**: Anonymous form for submitting incident reports
- **Admin Dashboard**: Secure login for reviewing all submitted reports
- **Search and Sort**: Advanced filtering and sorting capabilities
- **CSV Export**: Export all reports to CSV format
- **User Management**: Add, remove, and manage admin users
- **Responsive Design**: Works on desktop and mobile devices
- **Comprehensive Logging**: Detailed audit logs for all operations

## Requirements

- Python 3.8+
- Flask 2.3.3+
- SQLite (default) or PostgreSQL/MySQL
- Apache2/httpd (for production)
- Gunicorn (for production)
- SystemD (for service management)
- AlmaLinux 8+ (recommended for production)

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd incident-reporting
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables

```bash
cp env.example .env
# Edit .env with your configuration
```

### 5. Initialize Database

```bash
flask init-db
```

### 6. Create Default Admin User

```bash
flask init-db
```

This will create a default admin user with:
- **Username**: `admin`
- **Password**: `admin123`

⚠️ **Important**: Change this password after first login!

## Local Development

### Running the Application

```bash
python app.py
```

The application will be available at `http://localhost:5000`

### Development Features

- Auto-reload on code changes
- Debug mode enabled
- SQLite database for simplicity

## Production Deployment

### Quick Deployment

For a simple production deployment, use the provided deployment scripts:

1. **Automated Deployment**
   ```bash
   sudo chmod +x deploy.sh
   sudo ./deploy.sh
   ```

2. **Manual Setup**
   ```bash
   chmod +x init.sh
   ./init.sh
   ```

3. **Access the Application**
   - Main application: http://localhost:8000
   - Admin panel: http://localhost:8000/admin/login
   - Default admin: `admin` / `admin123`

For detailed instructions, see [README-NoDocker.md](README-NoDocker.md)

### AlmaLinux Production Setup (Recommended)

#### Automated Deployment

The easiest way to deploy on AlmaLinux is using the provided deployment script:

```bash
# Clone the repository
git clone <repository-url>
cd incident-reporting

# Make the deployment script executable
sudo chmod +x deploy.sh

# Run the automated deployment
sudo ./deploy.sh
```

The deployment script will:
- Create dedicated user and group (`incident-reports`)
- Install and configure the application in `/opt/incident-reports`
- Set up Apache2 virtual host configuration
- Configure systemd service for automatic startup
- Set up proper file permissions and SELinux contexts
- Create log directories with proper permissions
- Initialize the database with default admin user

After deployment:
- **Application URL**: `https://incidents.your-domain.com`
- **Admin Panel**: `https://incidents.your-domain.com/admin/login`
- **Default Admin**: `admin` / `admin123`

#### Manual AlmaLinux Setup

If you prefer manual installation or need to customize the setup:

1. **Install System Dependencies**

```bash
# Update system packages
sudo dnf update -y

# Install required packages
sudo dnf install -y python3 python3-pip python3-venv httpd mod_ssl
sudo dnf install -y gcc python3-devel  # For building Python packages

# Enable and start Apache
sudo systemctl enable httpd
sudo systemctl start httpd
```

2. **Configure Firewall**

```bash
# Open HTTP and HTTPS ports
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload

# Verify firewall status
sudo firewall-cmd --list-all
```

3. **Create Application User and Directories**

```bash
# Create dedicated user
sudo groupadd incident-reports
sudo useradd -r -g incident-reports -s /bin/false -d /opt/incident-reports incident-reports

# Create directories
sudo mkdir -p /opt/incident-reports
sudo mkdir -p /var/log/incident-reports
sudo mkdir -p /var/lib/incident-reports
sudo mkdir -p /var/run/incident-reports

# Set ownership
sudo chown -R incident-reports:incident-reports /opt/incident-reports
sudo chown -R incident-reports:incident-reports /var/log/incident-reports
sudo chown -R incident-reports:incident-reports /var/lib/incident-reports
sudo chown -R incident-reports:incident-reports /var/run/incident-reports
```

4. **Deploy Application**

```bash
# Copy application files
sudo cp -r * /opt/incident-reports/
sudo chown -R incident-reports:incident-reports /opt/incident-reports
```

5. **Set Up Python Environment**

```bash
cd /opt/incident-reports
sudo -u incident-reports python3 -m venv venv
sudo -u incident-reports venv/bin/pip install --upgrade pip
sudo -u incident-reports venv/bin/pip install -r requirements.txt
```

6. **Configure Environment**

```bash
sudo -u incident-reports cp env.example .env
# Edit .env with production settings
sudo nano .env
```

7. **Initialize Database**

```bash
cd /opt/incident-reports
sudo -u incident-reports venv/bin/python -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('Database initialized')
"

# Create default admin user
sudo -u incident-reports venv/bin/python -c "
from app import app, db, User
with app.app_context():
    admin = User(username='admin')
    admin.set_password('admin123')
    db.session.add(admin)
    db.session.commit()
    print('Admin user created: admin/admin123')
"
```

8. **Configure SystemD Service**

```bash
# Copy and edit systemd service file
sudo cp incident-reports.service /etc/systemd/system/
sudo nano /etc/systemd/system/incident-reports.service
# Verify paths are correct

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable incident-reports
sudo systemctl start incident-reports

# Check service status
sudo systemctl status incident-reports
```

9. **Configure Apache2**

```bash
# Copy Apache configuration
sudo cp incident-reports-apache.conf /etc/httpd/conf.d/incident-reports.conf

# Edit configuration file
sudo nano /etc/httpd/conf.d/incident-reports.conf
# Update ServerName with your domain name
# Update SSL certificate paths if using SSL

# Test Apache configuration
sudo httpd -t

# Restart Apache to load new configuration
sudo systemctl restart httpd
```

10. **Configure SELinux**

```bash
# Allow Apache to connect to network (for proxy to Gunicorn)
sudo setsebool -P httpd_can_network_connect 1

# Set proper SELinux contexts
sudo semanage fcontext -a -t httpd_exec_t "/opt/incident-reports(/.*)?"
sudo restorecon -R /opt/incident-reports

sudo semanage fcontext -a -t httpd_log_t "/var/log/incident-reports(/.*)?"
sudo restorecon -R /var/log/incident-reports

sudo semanage fcontext -a -t httpd_var_lib_t "/var/lib/incident-reports(/.*)?"
sudo restorecon -R /var/lib/incident-reports
```

### Ubuntu Server Setup (Alternative)

For Ubuntu/Debian systems, you can still use nginx:

1. **Install System Dependencies**

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv nginx
```

2. **Set Up Application Directory**

```bash
sudo mkdir -p /var/www/incident_reports
sudo chown $USER:$USER /var/www/incident_reports
```

3. **Deploy Application**

```bash
# Copy your application files to /var/www/incident_reports
cp -r * /var/www/incident_reports/
cd /var/www/incident_reports
```

4. **Set Up Virtual Environment**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

5. **Configure Environment**

```bash
cp env.example .env
# Edit .env with production settings
nano .env
```

6. **Initialize Database and Create Admin**

```bash
flask init-db
flask create-admin
```

7. **Set Up Gunicorn**

```bash
# Create log directories
sudo mkdir -p /var/log/gunicorn
sudo chown www-data:www-data /var/log/gunicorn

# Copy systemd service file
sudo cp systemd.service /etc/systemd/system/incident-reports.service
sudo nano /etc/systemd/system/incident-reports.service
# Update paths in the service file

# Enable and start service
sudo systemctl enable incident-reports
sudo systemctl start incident-reports
```

8. **Configure Nginx**

```bash
# Copy nginx configuration
sudo cp nginx.conf /etc/nginx/sites-available/incident-reports
sudo ln -s /etc/nginx/sites-available/incident-reports /etc/nginx/sites-enabled/
sudo nano /etc/nginx/sites-available/incident-reports
# Update server_name and paths

# Test and reload nginx
sudo nginx -t
sudo systemctl reload nginx
```

9. **Set Up Firewall**

```bash
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

### SSL/HTTPS Setup

For production deployments, SSL/HTTPS is strongly recommended. The Apache2 configuration is pre-configured for SSL with modern security settings.

#### Option 1: Let's Encrypt (Recommended)

Use the provided SSL setup script for automatic Let's Encrypt certificate installation:

```bash
# Make the SSL setup script executable
sudo chmod +x setup_ssl.sh

# Run the SSL setup script
sudo ./setup_ssl.sh
```

The script will:
- Install Certbot with Apache2 plugin for AlmaLinux
- Obtain Let's Encrypt certificates
- Update Apache2 configuration with certificate paths
- Setup automatic certificate renewal
- Configure HTTPS redirects
- Set proper SELinux contexts for certificates

#### Option 2: Enterprise/Internal CA Certificates

For organizations using internal Certificate Authorities:

**Automated Setup (Recommended):**
```bash
sudo ./setup_ssl.sh
# Select option 2 for enterprise/internal CA certificate
```

The script will guide you through:
- Installing your server certificate and private key
- Setting up certificate chains (intermediate certificates)
- Installing root CA certificates for system trust (AlmaLinux-compatible)
- Validating certificate and key compatibility
- Automatic Apache2 configuration
- SELinux context configuration

**Manual Setup for AlmaLinux:**
```bash
# Copy certificates
sudo cp your-certificate.crt /etc/ssl/certs/incident-reports.crt
sudo cp your-private-key.key /etc/ssl/private/incident-reports.key
sudo cp certificate-chain.crt /etc/ssl/certs/incident-reports-chain.crt

# Create full chain (server cert + intermediate certs)
sudo cat /etc/ssl/certs/incident-reports.crt /etc/ssl/certs/incident-reports-chain.crt > /etc/ssl/certs/incident-reports-fullchain.crt

# Set proper permissions
sudo chmod 644 /etc/ssl/certs/incident-reports*.crt
sudo chmod 600 /etc/ssl/private/incident-reports.key

# Update Apache configuration
sudo nano /etc/httpd/conf.d/incident-reports.conf
# Change: SSLCertificateFile /etc/ssl/certs/incident-reports-fullchain.crt

# Configure SELinux contexts
sudo restorecon -R /etc/ssl/certs/
sudo restorecon -R /etc/ssl/private/

# Test and reload Apache
sudo httpd -t
sudo systemctl reload httpd
```

#### Option 3: Certificate Signing Request (CSR)

To generate a CSR for your Certificate Authority:

```bash
sudo ./setup_ssl.sh
# Select option 3 to create a CSR
```

This will:
- Generate a private key
- Create a Certificate Signing Request
- Display the CSR content for submission to your CA
- Provide next steps for certificate installation

#### Option 4: Self-Signed Certificates (Development Only)

For development or testing environments:

```bash
sudo ./setup_ssl.sh
# Select option 4 for self-signed certificates
```

**Note**: Self-signed certificates will show security warnings in browsers.

#### SSL Certificate Management

**Check Certificate Status:**
```bash
# View current certificate information
sudo ./setup_ssl.sh
# Select option 7 to view certificate details

# Check certificate expiration
openssl x509 -in /etc/ssl/certs/incident-reports.crt -noout -dates

# Test SSL configuration
openssl s_client -connect your-domain.com:443 -servername your-domain.com
```

**Renew Let's Encrypt Certificates:**
```bash
# Test renewal (dry run)
sudo certbot renew --dry-run

# Renew certificates
sudo certbot renew

# Auto-renewal is configured via systemd timer
sudo systemctl status certbot.timer
```

## Usage

### Public Incident Reporting

1. Navigate to the main page (`/`)
2. Fill out the incident report form:
   - **Your Name**: Optional (defaults to "Anonymous")
   - **Time and Date of Incident**: Required
   - **Location of Incident**: Required
   - **Names of Persons Involved**: Required
   - **Description of Incident**: Required
3. Submit the form

### Admin Dashboard

1. Navigate to `/admin/login`
2. Log in with default credentials:
   - **Username**: `admin`
   - **Password**: `admin123`
3. Use the dashboard to:
   - View all incident reports
   - Search and filter reports
   - Sort by various criteria
   - Export reports to CSV
   - Manage admin users

### User Management

1. Access the Users page from the admin dashboard
2. Add new admin users with username and password
3. Activate/deactivate existing users
4. Delete users (cannot delete your own account)

### Additional Commands

```bash
# Create additional admin user
flask create-admin

# Reset default admin password to admin123
flask reset-default-admin
```

## Database Schema

### Users Table
- `id`: Primary key
- `username`: Unique username
- `password_hash`: Hashed password
- `created_at`: Account creation timestamp
- `is_active`: Account status

### Incidents Table
- `id`: Primary key
- `reporter_name`: Name of person reporting (defaults to "Anonymous")
- `incident_datetime`: When the incident occurred
- `location`: Where the incident occurred
- `persons_involved`: People involved in the incident
- `description`: Detailed description of the incident
- `submitted_at`: When the report was submitted

## Security Features

- Password hashing using Werkzeug
- Session management with Flask-Login
- CSRF protection
- Input validation and sanitization
- Comprehensive audit logging
- SQL injection prevention through SQLAlchemy ORM

## Logging

The application logs to:
- `incident_reports.log`: Application logs (development)
- `/var/log/incident-reports/`: Application logs (production)
- `/var/log/httpd/`: Apache2 logs (AlmaLinux production)
- `/var/log/nginx/`: Nginx logs (Ubuntu production)

## Troubleshooting

### Common Issues

#### AlmaLinux/Apache2 Specific

1. **SELinux Issues**: If you get permission denied errors:
   ```bash
   # Check SELinux status
   sudo getenforce
   
   # View SELinux denials
   sudo ausearch -m AVC -ts recent
   
   # Allow Apache network connections
   sudo setsebool -P httpd_can_network_connect 1
   
   # Reset SELinux contexts
   sudo restorecon -R /opt/incident-reports
   ```

2. **Firewall Issues**: Ensure ports are open:
   ```bash
   # Check firewall status
   sudo firewall-cmd --list-all
   
   # Open required ports
   sudo firewall-cmd --permanent --add-service=http
   sudo firewall-cmd --permanent --add-service=https
   sudo firewall-cmd --reload
   ```

3. **Apache Module Issues**: Ensure required modules are loaded:
   ```bash
   # Check loaded modules
   sudo httpd -M | grep -E "(ssl|proxy|headers)"
   
   # If modules are missing, they may need to be installed
   sudo dnf install mod_ssl mod_proxy_html
   ```

4. **Database Permission Issues**: Fix database file permissions:
   ```bash
   sudo chown incident-reports:incident-reports /var/lib/incident-reports/incidents.db
   sudo chmod 644 /var/lib/incident-reports/incidents.db
   sudo restorecon /var/lib/incident-reports/incidents.db
   ```

#### General Issues

1. **Database Errors**: Ensure the database file is writable
2. **Permission Errors**: Check file permissions and ownership
3. **Port Conflicts**: Ensure port 8000 (application) is available
4. **Import Errors**: Verify all dependencies are installed

### Logs

Check logs for detailed error information:

#### AlmaLinux/Apache2 Production
```bash
# Application logs
sudo tail -f /var/log/incident-reports/error.log

# Gunicorn logs (systemd service)
sudo journalctl -u incident-reports -f

# Apache logs
sudo tail -f /var/log/httpd/incident_reports_error.log
sudo tail -f /var/log/httpd/incident_reports_access.log

# System logs
sudo journalctl -xe
```

#### Ubuntu/Nginx Production
```bash
# Application logs
tail -f incident_reports.log

# Gunicorn logs (production)
sudo journalctl -u incident-reports -f

# Nginx logs (production)
sudo tail -f /var/log/nginx/incident_reports_error.log
```

#### Development
```bash
# Application logs
tail -f incident_reports.log

# Flask development server output
python app.py
```

### Service Management

#### AlmaLinux Commands
```bash
# Check service status
sudo systemctl status incident-reports
sudo systemctl status httpd

# Restart services
sudo systemctl restart incident-reports
sudo systemctl restart httpd

# View service logs
sudo journalctl -u incident-reports --no-pager
sudo journalctl -u httpd --no-pager

# Test Apache configuration
sudo httpd -t
```

### Performance Tuning

#### For High Traffic Environments

1. **Increase Gunicorn Workers**:
   ```bash
   sudo nano /etc/systemd/system/incident-reports.service
   # Modify ExecStart to include more workers:
   # --workers 4 --worker-class gevent
   ```

2. **Apache Tuning**:
   ```bash
   sudo nano /etc/httpd/conf.d/incident-reports.conf
   # Add performance directives:
   # KeepAlive On
   # MaxKeepAliveRequests 100
   # KeepAliveTimeout 5
   ```

3. **Database Optimization**:
   ```bash
   # For SQLite, consider moving to PostgreSQL for high traffic
   # Update DATABASE_URL in service file
   ```

## Quick Reference

### AlmaLinux Production Deployment

```bash
# 1. Clone and deploy
git clone <repository-url>
cd incident-reporting
sudo chmod +x deploy.sh
sudo ./deploy.sh

# 2. Configure domain and SSL
sudo nano /etc/httpd/conf.d/incident-reports.conf
# Update ServerName to your domain

sudo chmod +x setup_ssl.sh
sudo ./setup_ssl.sh
# Follow prompts for SSL setup

# 3. Access application
# https://your-domain.com
# https://your-domain.com/admin/login
# admin/admin123 (change this!)
```

### Service Management Commands

```bash
# Application service
sudo systemctl {start|stop|restart|status} incident-reports

# Apache service
sudo systemctl {start|stop|restart|status} httpd

# View logs
sudo journalctl -u incident-reports -f
sudo tail -f /var/log/httpd/incident_reports_error.log

# Test configurations
sudo httpd -t
```

### File Locations

```
/opt/incident-reports/                 # Application files
/etc/httpd/conf.d/incident-reports.conf  # Apache config
/etc/systemd/system/incident-reports.service  # Service config
/var/log/incident-reports/            # Application logs
/var/log/httpd/incident_reports_*.log  # Apache logs
/var/lib/incident-reports/incidents.db # Database
/etc/ssl/certs/incident-reports.crt   # SSL certificate
/etc/ssl/private/incident-reports.key # SSL private key
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please contact your system administrator or create an issue in the project repository. 