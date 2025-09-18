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
- Nginx (for production)
- Gunicorn (for production)
- SystemD (for service management)

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

### Manual Production Setup

#### Ubuntu Server Setup

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

For production deployments, SSL/HTTPS is strongly recommended. The nginx configuration is pre-configured for SSL with modern security settings.

#### Option 1: Let's Encrypt (Recommended)

Use the provided SSL setup script for automatic Let's Encrypt certificate installation:

```bash
# Make the SSL setup script executable
sudo chmod +x setup_ssl.sh

# Run the SSL setup script
sudo ./setup_ssl.sh
```

The script will:
- Install Certbot
- Obtain Let's Encrypt certificates
- Update nginx configuration with certificate paths
- Setup automatic certificate renewal
- Configure HTTPS redirects

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
- Installing root CA certificates for system trust
- Validating certificate and key compatibility
- Automatic nginx configuration

**Manual Setup:**
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

# Update nginx configuration
sudo nano /etc/nginx/sites-available/incident-reports
# Change: ssl_certificate /etc/ssl/certs/incident-reports-fullchain.crt;

# Test and reload
sudo nginx -t
sudo systemctl reload nginx
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
- `incident_reports.log`: Application logs
- `/var/log/gunicorn/`: Gunicorn logs (production)
- `/var/log/nginx/`: Nginx logs (production)

## Troubleshooting

### Common Issues

1. **Database Errors**: Ensure the database file is writable
2. **Permission Errors**: Check file permissions and ownership
3. **Port Conflicts**: Ensure port 5000 (development) or 80 (production) is available
4. **Import Errors**: Verify all dependencies are installed

### Logs

Check logs for detailed error information:

```bash
# Application logs
tail -f incident_reports.log

# Gunicorn logs (production)
sudo journalctl -u incident-reports -f

# Nginx logs (production)
sudo tail -f /var/log/nginx/incident_reports_error.log
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