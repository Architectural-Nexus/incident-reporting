#!/bin/bash

# Server Configuration Check Script
# Run this on incidents.archnexus.com to check current setup

echo "=== Server Information ==="
echo "Hostname: $(hostname)"
echo "OS: $(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)"
echo "Kernel: $(uname -r)"
echo ""

echo "=== Current Application Status ==="
if [ -d "/opt/incident-reporting" ]; then
    echo "✅ Application directory exists: /opt/incident-reporting"
    ls -la /opt/incident-reporting/ | head -20
else
    echo "❌ Application directory NOT found"
fi
echo ""

echo "=== Systemd Service Status ==="
if systemctl list-units | grep -q "incident"; then
    systemctl status incident-reporting 2>/dev/null || systemctl status incident-reports 2>/dev/null || echo "Service found but status unavailable"
else
    echo "❌ No incident reporting service found"
fi
echo ""

echo "=== Web Server Configuration ==="
if [ -f "/etc/nginx/sites-available/incident-reporting" ]; then
    echo "✅ Nginx config found"
    cat /etc/nginx/sites-available/incident-reporting
elif [ -f "/etc/httpd/conf.d/incident-reports.conf" ]; then
    echo "✅ Apache config found"
    cat /etc/httpd/conf.d/incident-reports.conf
else
    echo "❌ No web server config found for incident reporting"
fi
echo ""

echo "=== Database Status ==="
if [ -f "/opt/incident-reporting/instance/incidents.db" ]; then
    echo "✅ Database file exists"
    ls -lh /opt/incident-reporting/instance/incidents.db
elif [ -f "/var/lib/incident-reports/incidents.db" ]; then
    echo "✅ Database file exists (alternative location)"
    ls -lh /var/lib/incident-reports/incidents.db
else
    echo "❌ Database file NOT found"
fi
echo ""

echo "=== Python Environment ==="
if [ -d "/opt/incident-reporting/venv" ]; then
    echo "✅ Virtual environment exists"
    /opt/incident-reporting/venv/bin/python --version
    echo "Installed packages:"
    /opt/incident-reporting/venv/bin/pip list | grep -E "(Flask|gunicorn|SQLAlchemy)"
else
    echo "❌ Virtual environment NOT found"
fi
echo ""

echo "=== Environment Configuration ==="
if [ -f "/opt/incident-reporting/.env" ]; then
    echo "✅ .env file exists"
    echo "File permissions:"
    ls -la /opt/incident-reporting/.env
    echo "⚠️  (Not showing contents for security)"
else
    echo "❌ .env file NOT found"
fi
echo ""

echo "=== Port Status ==="
echo "Listening ports:"
netstat -tlnp 2>/dev/null | grep -E ":(80|443|8000|5002)" || ss -tlnp 2>/dev/null | grep -E ":(80|443|8000|5002)"
echo ""

echo "=== Disk Space ==="
df -h /opt/incident-reporting 2>/dev/null || df -h /
echo ""

echo "=== Recent Logs (if available) ==="
if [ -f "/var/log/incident-reports/error.log" ]; then
    echo "Last 10 lines of error log:"
    tail -10 /var/log/incident-reports/error.log
elif journalctl -u incident-reporting -n 10 2>/dev/null | head -1; then
    echo "Last 10 systemd log entries:"
    journalctl -u incident-reporting -n 10 --no-pager 2>/dev/null
else
    echo "No logs found"
fi
