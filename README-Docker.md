# Docker Deployment Guide

This guide explains how to deploy the Incident Reports Application using Docker on an Ubuntu server.

## Prerequisites

- Ubuntu 20.04 or later
- Docker installed
- Docker Compose installed

## Quick Start

### 1. Install Docker (if not already installed)

```bash
# Update package list
sudo apt update

# Install required packages
sudo apt install -y apt-transport-https ca-certificates curl gnupg lsb-release

# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Add Docker repository
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Add current user to docker group
sudo usermod -aG docker $USER

# Log out and back in for group changes to take effect
```

### 2. Clone and Deploy

```bash
# Clone the repository (if not already done)
git clone <your-repo-url>
cd work_incidents

# Make deployment script executable
chmod +x deploy.sh

# Deploy the application
./deploy.sh deploy
```

## Deployment Options

### Development Mode
```bash
./deploy.sh deploy
```
- Runs on port 80 (standard HTTP port)
- Includes all features
- Good for testing and development

### Production Mode
```bash
./deploy.sh deploy-prod
```
- Runs with Nginx reverse proxy
- Includes resource limits
- Better security configuration
- Runs on ports 80 and 443

## Environment Configuration

### 1. Environment Variables

Create a `.env` file in the project root:

```bash
# Generate a secure secret key
SECRET_KEY=$(openssl rand -hex 32)

# Create .env file
cat > .env << EOF
SECRET_KEY=$SECRET_KEY
DATABASE_URL=sqlite:///instance/incidents.db
FLASK_ENV=production
EOF
```

### 2. Production Environment Variables

For production, consider these additional variables:

```bash
# Database (if using external database)
DATABASE_URL=postgresql://user:password@host:port/database

# Security
SECRET_KEY=your-very-secure-secret-key
FLASK_ENV=production

# Logging
LOG_LEVEL=INFO
```

## Management Commands

### View Application Status
```bash
./deploy.sh status
```

### View Logs
```bash
./deploy.sh logs
```

### Stop Application
```bash
./deploy.sh stop
```

### Restart Application
```bash
./deploy.sh restart
```

### Manual Docker Commands

```bash
# Build and start
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Production mode
docker-compose -f docker-compose.prod.yml up -d --build
```

## Security Considerations

### 1. Default Admin User
- Username: `admin`
- Password: `admin123`
- **IMPORTANT**: Change this password immediately after deployment

### 2. Secret Key
- Always use a strong, unique secret key in production
- Generate using: `openssl rand -hex 32`

### 3. Database Security
- Use external database for production
- Implement proper backup strategies
- Consider using PostgreSQL or MySQL for production

### 4. Network Security
- Configure firewall rules
- Use HTTPS in production
- Consider using a reverse proxy (Nginx)

## Monitoring and Logs

### Application Logs
```bash
# View application logs
docker-compose logs -f incident-reports

# View nginx logs (production mode)
docker-compose logs -f nginx
```

### Health Checks
The application includes health checks that monitor:
- Application availability
- Database connectivity
- Service responsiveness

### Resource Monitoring
```bash
# View container resource usage
docker stats

# View disk usage
docker system df
```

## Backup and Recovery

### Database Backup
```bash
# Backup SQLite database
docker exec incident-reports-app sqlite3 /app/instance/incidents.db ".backup /app/backup/incidents_$(date +%Y%m%d_%H%M%S).db"

# Or copy the database file
docker cp incident-reports-app:/app/instance/incidents.db ./backup/
```

### Volume Backup
```bash
# Backup all data volumes
docker run --rm -v incident_data:/data -v $(pwd):/backup alpine tar czf /backup/incident_data_$(date +%Y%m%d_%H%M%S).tar.gz -C /data .
```

## Troubleshooting

### Common Issues

1. **Port already in use**
   ```bash
       # Check what's using the port
    sudo netstat -tulpn | grep :80
   
   # Stop conflicting service
   sudo systemctl stop conflicting-service
   ```

2. **Permission denied**
   ```bash
   # Fix Docker permissions
   sudo chmod 666 /var/run/docker.sock
   # Or add user to docker group and restart session
   ```

3. **Database initialization failed**
   ```bash
   # Check container logs
   docker-compose logs incident-reports
   
   # Manually initialize database
   docker exec -it incident-reports-app python -c "from app import app, db; app.app_context().push(); db.create_all()"
   ```

4. **Container won't start**
   ```bash
   # Check container status
   docker-compose ps
   
   # View detailed logs
   docker-compose logs incident-reports
   
   # Rebuild container
   docker-compose down
   docker-compose up -d --build
   ```

### Performance Tuning

1. **Increase worker processes**
   Edit `gunicorn.conf.py`:
   ```python
   workers = multiprocessing.cpu_count() * 2 + 1
   ```

2. **Adjust memory limits**
   Edit `docker-compose.prod.yml`:
   ```yaml
   deploy:
     resources:
       limits:
         memory: 1G
         cpus: '1.0'
   ```

3. **Enable caching**
   Consider adding Redis for session storage and caching.

## SSL/HTTPS Setup

### Using Let's Encrypt

1. Install Certbot:
   ```bash
   sudo apt install certbot python3-certbot-nginx
   ```

2. Obtain certificate:
   ```bash
   sudo certbot --nginx -d yourdomain.com
   ```

3. Update nginx configuration to use SSL certificates.

### Manual SSL Setup

1. Place SSL certificates in `./ssl/` directory
2. Update `nginx.conf` with SSL configuration
3. Restart nginx container

## Scaling

### Horizontal Scaling
```bash
# Scale application instances
docker-compose up -d --scale incident-reports=3
```

### Load Balancing
Use Nginx or HAProxy for load balancing multiple application instances.

## Maintenance

### Regular Maintenance Tasks

1. **Update dependencies**
   ```bash
   # Rebuild with updated requirements
   docker-compose down
   docker-compose up -d --build
   ```

2. **Clean up old images**
   ```bash
   docker system prune -a
   ```

3. **Monitor disk space**
   ```bash
   docker system df
   ```

4. **Backup data**
   ```bash
   # Create regular backups
   ./backup.sh
   ```

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review application logs
3. Check Docker and system logs
4. Verify configuration files

## File Structure

```
work_incidents/
├── Dockerfile                 # Main Docker image definition
├── docker-compose.yml         # Development deployment
├── docker-compose.prod.yml    # Production deployment
├── docker-entrypoint.sh       # Container initialization script
├── deploy.sh                  # Deployment automation script
├── .dockerignore             # Files to exclude from Docker build
├── nginx.conf                # Nginx configuration
├── requirements.txt          # Python dependencies
├── app.py                    # Main application
└── templates/                # HTML templates
```

This Docker deployment provides a robust, scalable, and secure way to run the Incident Reports Application on Ubuntu servers. 