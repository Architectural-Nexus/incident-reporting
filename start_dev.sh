#!/bin/bash

# Incident Reporting System - Development Server Startup Script
# This script activates the virtual environment and starts the Flask development server

echo "🚀 Starting Incident Reporting System Development Server..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run setup first."
    exit 1
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source venv/bin/activate

# Check if database exists
if [ ! -f "incidents.db" ]; then
    echo "🗄️  Database not found. Initializing database..."
    flask init-db
fi

echo ""
echo "🌐 Starting Flask development server..."
echo "📍 Application will be available at: http://localhost:5002"
echo "🔐 Admin login: http://localhost:5002/admin/login"
echo "👤 Default admin credentials: admin / admin123"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the Flask development server
python app.py
