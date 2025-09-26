# Local Development Setup

This guide will help you set up a local development environment for the Incident Reporting System.

## Prerequisites

- Python 3.8 or higher
- Git (if cloning from repository)

## Quick Start

### 1. Activate Virtual Environment
```bash
source venv/bin/activate
```

### 2. Start Development Server
```bash
./start_dev.sh
```

Or manually:
```bash
python app.py
```

### 3. Access the Application
- **Main Application**: http://localhost:5000
- **Admin Dashboard**: http://localhost:5000/admin/login
- **Default Admin Credentials**: 
  - Username: `admin`
  - Password: `admin123`

⚠️ **Important**: Change the default admin password after first login!

## Development Features

- **Auto-reload**: The Flask development server automatically reloads when you make changes to the code
- **Debug Mode**: Enabled for detailed error messages
- **SQLite Database**: Uses a local SQLite database (`incidents.db`)
- **PDF Export**: Test the new PDF export feature on the incident form

## Project Structure

```
incident-reporting/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (local development)
├── venv/                  # Python virtual environment
├── templates/             # HTML templates
│   ├── base.html         # Base template with CSS
│   ├── index.html        # Incident reporting form
│   ├── admin_login.html  # Admin login page
│   ├── admin_dashboard.html # Admin dashboard
│   └── admin_users.html  # User management
├── static/               # Static files (CSS, JS, images)
├── incidents.db          # SQLite database (created after init)
└── start_dev.sh          # Development server startup script
```

## Available Routes

- `GET /` - Incident reporting form
- `POST /submit_incident` - Submit incident report
- `POST /export_incident_pdf` - Export form data as PDF
- `GET /admin/login` - Admin login page
- `POST /admin/login` - Admin authentication
- `GET /admin/dashboard` - Admin dashboard
- `GET /admin/incidents` - Get incidents (API)
- `GET /admin/export` - Export incidents to CSV
- `GET /admin/users` - User management
- Various admin user management endpoints

## Database Commands

```bash
# Initialize database (creates tables and default admin user)
flask init-db

# Create additional admin user
flask create-admin

# Reset default admin password
flask reset-default-admin
```

## Environment Variables

The `.env` file contains:
- `SECRET_KEY`: Flask secret key for sessions
- `FLASK_ENV`: Set to `development` for local development
- `DATABASE_URL`: SQLite database path
- `LOG_LEVEL`: Logging level

## Testing the PDF Export Feature

1. Go to http://localhost:5000
2. Fill out the incident form with some test data
3. Click "Export as PDF" button
4. The PDF should download automatically

## Troubleshooting

### Virtual Environment Issues
```bash
# Recreate virtual environment
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Database Issues
```bash
# Reset database
rm incidents.db
flask init-db
```

### Port Already in Use
If port 5000 is already in use, modify `app.py` to use a different port:
```python
app.run(debug=True, host='0.0.0.0', port=5001)  # Change port number
```

## Development Tips

1. **Hot Reload**: The development server automatically reloads when you save changes
2. **Debug Mode**: Detailed error messages are shown in the browser
3. **Database**: SQLite database file is created in the project root
4. **Logs**: Application logs are written to `incident_reports.log`
5. **PDF Testing**: Test the PDF export feature with various form data

## Next Steps

- Modify templates in the `templates/` directory
- Update CSS styles in `templates/base.html`
- Add new routes in `app.py`
- Test the PDF export functionality
- Add new features as needed

Happy coding! 🚀
