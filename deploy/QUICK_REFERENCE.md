# Incident Reporting System - Ubuntu Deployment Quick Reference

## 🚀 Quick Deployment (5 minutes)

### 1. Upload Package
```bash
scp incident-reporting-ubuntu-deploy.tar.gz user@your-server:/tmp/
```

### 2. Install on Server
```bash
ssh user@your-server
cd /tmp
tar -xzf incident-reporting-ubuntu-deploy.tar.gz
cd incident-reporting-ubuntu-deploy
sudo ./deploy/install.sh
```

### 3. Configure
```bash
sudo nano /opt/incident-reporting/.env
# Update email settings and secret key
sudo systemctl restart incident-reporting
```

## 🔧 Service Management

| Command | Description |
|---------|-------------|
| `sudo systemctl status incident-reporting` | Check service status |
| `sudo systemctl restart incident-reporting` | Restart service |
| `sudo journalctl -u incident-reporting -f` | View live logs |
| `sudo systemctl stop incident-reporting` | Stop service |
| `sudo systemctl start incident-reporting` | Start service |

## 📁 Key Files & Locations

| File | Location | Purpose |
|------|----------|---------|
| Application | `/opt/incident-reporting/` | Main application directory |
| Database | `/opt/incident-reporting/instance/incidents.db` | SQLite database |
| Config | `/opt/incident-reporting/.env` | Environment variables |
| Service | `/etc/systemd/system/incident-reporting.service` | Systemd service |
| Nginx | `/etc/nginx/sites-available/incident-reporting` | Web server config |
| Logs | `journalctl -u incident-reporting` | Application logs |

## 🔐 Security Checklist

- [ ] Change default admin password (`admin` / `admin123`)
- [ ] Configure SSL certificate: `sudo certbot --nginx -d your-domain.com`
- [ ] Review firewall settings: `sudo ufw status`
- [ ] Check fail2ban status: `sudo systemctl status fail2ban`
- [ ] Verify file permissions: `ls -la /opt/incident-reporting/`

## 🔄 Maintenance Commands

### Backup Database
```bash
sudo cp /opt/incident-reporting/instance/incidents.db /opt/incident-reporting/backups/incidents-$(date +%Y%m%d).db
```

### Update Application
```bash
sudo ./deploy/update.sh
```

### Create Full Backup
```bash
sudo ./deploy/backup.sh
```

## 🐛 Troubleshooting

### Service Won't Start
```bash
sudo journalctl -u incident-reporting -n 50
sudo systemctl status incident-reporting
```

### Nginx Issues
```bash
sudo nginx -t
sudo systemctl status nginx
sudo tail -f /var/log/nginx/error.log
```

### Database Issues
```bash
ls -la /opt/incident-reporting/instance/
sudo chown www-data:www-data /opt/incident-reporting/instance/incidents.db
```

## 📊 Monitoring

### Check System Resources
```bash
# CPU and Memory
htop

# Disk Usage
df -h

# Service Status
sudo systemctl status incident-reporting nginx
```

### Application Health
- Access: `http://your-domain.com`
- Admin: `http://your-domain.com/admin/login`
- Default: `admin` / `admin123` ⚠️ **CHANGE IMMEDIATELY**

## 🔧 Configuration

### Environment Variables (.env)
```bash
# Required
SECRET_KEY=your-secret-key-here
FLASK_ENV=production

# Email (Optional)
MAIL_SERVER=smtp.your-domain.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@your-domain.com
MAIL_PASSWORD=your-email-password
```

### Nginx Domain Update
```bash
sudo sed -i 's/your-domain.com/your-actual-domain.com/g' /etc/nginx/sites-available/incident-reporting
sudo nginx -t && sudo systemctl reload nginx
```

## 📞 Support

- **Logs**: `sudo journalctl -u incident-reporting -f`
- **Status**: `sudo systemctl status incident-reporting`
- **Config Test**: `sudo nginx -t`
- **Manual Test**: `sudo -u www-data /opt/incident-reporting/venv/bin/python /opt/incident-reporting/app.py`

---
**⚠️ IMPORTANT**: Change the default admin password immediately after deployment!
