@echo off
REM Incident Reports Application Initialization Script for Windows
REM This script initializes the application for manual setup on Windows

echo Starting initialization of Incident Reports Application...

REM Configuration
set APP_DIR=%~dp0
set VENV_DIR=%APP_DIR%venv
set DATA_DIR=%APP_DIR%instance
set LOG_DIR=%APP_DIR%logs

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    exit /b 1
)

echo [INFO] Python is available

REM Create virtual environment
if exist "%VENV_DIR%" (
    echo [WARNING] Virtual environment already exists at %VENV_DIR%
    set /p RECREATE="Do you want to recreate it? (y/N): "
    if /i "%RECREATE%"=="y" (
        rmdir /s /q "%VENV_DIR%"
    ) else (
        echo [INFO] Using existing virtual environment
        goto :install_deps
    )
)

echo [INFO] Creating virtual environment...
python -m venv "%VENV_DIR%"
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment
    exit /b 1
)

:install_deps
echo [INFO] Installing Python dependencies...
call "%VENV_DIR%\Scripts\activate.bat"
pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    exit /b 1
)

REM Create directories
echo [INFO] Creating necessary directories...
if not exist "%DATA_DIR%" mkdir "%DATA_DIR%"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

echo [INFO] Directories created:
echo   - Data: %DATA_DIR%
echo   - Logs: %LOG_DIR%

REM Initialize database
echo [INFO] Initializing database...
call "%VENV_DIR%\Scripts\activate.bat"
python -c "from app import app, db; app.app_context().push(); db.create_all(); print('Database initialized successfully')"
if errorlevel 1 (
    echo [ERROR] Failed to initialize database
    exit /b 1
)

REM Create admin user
echo [INFO] Creating admin user...
python -c "from app import app, db, User; app.app_context().push(); admin = User.query.filter_by(username='admin').first(); admin = User(username='admin') if not admin else admin; admin.set_password('admin123'); db.session.add(admin) if not admin.id else None; db.session.commit(); print('Admin user created: admin/admin123')"

REM Create run script
echo [INFO] Creating run script...
(
echo @echo off
echo REM Run script for Incident Reports Application on Windows
echo set APP_DIR=%%~dp0
echo set VENV_DIR=%%APP_DIR%%venv
echo call "%%VENV_DIR%%\Scripts\activate.bat"
echo set FLASK_APP=app.py
echo set FLASK_ENV=development
echo set SECRET_KEY=your-secret-key-change-this-in-production
echo set DATABASE_URL=sqlite:///instance/incidents.db
echo echo Starting Incident Reports Application...
echo echo Application will be available at: http://localhost:8000
echo echo Admin panel: http://localhost:8000/admin/login
echo echo Press Ctrl+C to stop
echo echo.
echo python -m flask run --host=0.0.0.0 --port=8000
) > run.bat

echo [INFO] Run script created: run.bat

REM Create production run script
echo [INFO] Creating production run script...
(
echo @echo off
echo REM Production run script for Incident Reports Application on Windows
echo set APP_DIR=%%~dp0
echo set VENV_DIR=%%APP_DIR%%venv
echo call "%%VENV_DIR%%\Scripts\activate.bat"
echo set FLASK_APP=app.py
echo set FLASK_ENV=production
echo set SECRET_KEY=your-secret-key-change-this-in-production
echo set DATABASE_URL=sqlite:///instance/incidents.db
echo if not exist "logs" mkdir "logs"
echo echo Starting Incident Reports Application in production mode...
echo echo Application will be available at: http://localhost:8000
echo echo Admin panel: http://localhost:8000/admin/login
echo echo Logs will be written to logs\ directory
echo echo Press Ctrl+C to stop
echo echo.
echo gunicorn --config gunicorn.conf.py --bind 0.0.0.0:8000 app:app
) > run_prod.bat

echo [INFO] Production run script created: run_prod.bat

echo.
echo ==========================================
echo 🎉 Initialization completed successfully!
echo ==========================================
echo.
echo Application Information:
echo   - Virtual Environment: %VENV_DIR%
echo   - Database: %DATA_DIR%\incidents.db
echo   - Logs: %LOG_DIR%
echo.
echo Running the Application:
echo   - Development: run.bat
echo   - Production:  run_prod.bat
echo.
echo Access Information:
echo   - Application URL: http://localhost:8000
echo   - Admin URL: http://localhost:8000/admin/login
echo   - Default Admin: admin / admin123
echo.
echo ⚠️  IMPORTANT: Change the default admin password!
echo ⚠️  IMPORTANT: Update SECRET_KEY for production!
echo.

pause 