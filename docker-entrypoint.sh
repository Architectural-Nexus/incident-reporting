#!/bin/bash

# Docker entrypoint script for Incident Reports Application
set -e

echo "🚀 Starting Incident Reports Application..."

# Function to initialize database
init_database() {
    echo "📊 Initializing database..."
    python -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('Database initialized successfully')
"
}

# Function to create default admin user
create_admin_user() {
    echo "👤 Creating default admin user..."
    python -c "
from app import app, db, User
with app.app_context():
    # Check if admin user already exists
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(username='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print('Default admin user created: admin/admin123')
    else:
        print('Admin user already exists')
"
}

# Function to check if database exists
check_database() {
    if [ ! -f "/app/instance/incidents.db" ]; then
        echo "🗄️ Database not found, initializing..."
        init_database
        create_admin_user
    else
        echo "🗄️ Database found, skipping initialization"
    fi
}

# Function to wait for database to be ready
wait_for_database() {
    echo "⏳ Waiting for database to be ready..."
    python -c "
import time
from app import app, db
with app.app_context():
    max_attempts = 30
    for attempt in range(max_attempts):
        try:
            db.engine.execute('SELECT 1')
            print('Database is ready')
            break
        except Exception as e:
            if attempt == max_attempts - 1:
                print(f'Database not ready after {max_attempts} attempts')
                exit(1)
            print(f'Database not ready, attempt {attempt + 1}/{max_attempts}')
            time.sleep(2)
"
}

# Main execution
echo "🔧 Setting up application..."

# Check and initialize database
check_database

# Wait for database to be ready (useful for external databases)
wait_for_database

echo "✅ Application setup complete"

# Execute the main command
exec "$@" 