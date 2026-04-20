# Production Deployment Guide — Dhanyada

## Quick Start (Local Development)

Get the full stack running locally with docker-compose in 5 minutes:

```bash
# Clone repository
git clone https://github.com/yourusername/dhanyada.git
cd dhanyada

# Copy environment file (edit with your values)
cp .env.example .env

# Start all services
docker-compose up -d

# Wait for services to be healthy (check logs)
docker-compose logs -f app

# Test health endpoint
curl http://localhost:8000/health

# Access admin dashboard
# URL: http://localhost:8000/admin/
# Username: admin
# Password: changeme
```

**Services Running:**
- FastAPI app: http://localhost:8000
- Admin dashboard: http://localhost:8000/admin/
- PostgreSQL: localhost:5432
- Redis: localhost:6379
- Celery worker: (background)
- Celery beat: (background)

---

## Environment Setup

### Required Environment Variables

Create a `.env` file in the project root with the following:

```bash
# Database (PostgreSQL)
DATABASE_URL=postgresql+asyncpg://dhanyada:dhanyada_secure_dev_password@postgres:5432/dhanyada

# Redis Cache
REDIS_URL=redis://redis:6379

# WhatsApp Configuration
WHATSAPP_PHONE_ID=your_phone_id
WHATSAPP_TOKEN=your_access_token
WHATSAPP_BUSINESS_ACCOUNT_ID=your_business_account_id
WHATSAPP_VERIFY_TOKEN=your_verify_token

# API Keys
OPENWEATHER_API_KEY=your_openweather_key
AGROMONITORING_API_KEY=your_agromonitoring_key
AGMARKNET_API_KEY=your_agmarknet_key

# Admin Dashboard
ADMIN_USERNAME=admin
ADMIN_PASSWORD=changeme
JWT_SECRET=your-secret-key-change-in-production

# Email/SMTP (for alerts)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
ADMIN_EMAIL=your-email@gmail.com

# Monitoring & Alerting
ALERT_ERROR_THRESHOLD=5.0
ALERT_LATENCY_THRESHOLD=1000
HEALTH_CHECK_INTERVAL_MINUTES=60
LOG_LEVEL=INFO
```

### Production Environment Variables

For production, use a secrets management system (not `.env` files):

**AWS Parameter Store / AWS Secrets Manager:**
```bash
# Store each secret with /dhanyada/ prefix
aws secretsmanager create-secret --name /dhanyada/WHATSAPP_TOKEN --secret-string "your-token"
aws secretsmanager create-secret --name /dhanyada/DATABASE_URL --secret-string "postgresql://user:pass@host:5432/db"
```

**Or Kubernetes Secrets:**
```bash
kubectl create secret generic dhanyada-secrets \
  --from-literal=WHATSAPP_TOKEN=token \
  --from-literal=SMTP_PASSWORD=password \
  -n dhanyada
```

---

## Database Setup

### Local Development (with docker-compose)

```bash
# Services start automatically, migrations run on first boot
docker-compose up -d postgres

# Wait for PostgreSQL to be healthy
docker-compose exec postgres pg_isready -U dhanyada

# Run migrations
docker-compose exec app alembic upgrade head

# Check migration status
docker-compose exec app alembic current
```

### Production Database Setup

#### Option 1: AWS RDS PostgreSQL

```bash
# Create RDS instance
aws rds create-db-instance \
  --db-instance-identifier dhanyada-db \
  --engine postgres \
  --engine-version 16.1 \
  --db-instance-class db.t3.micro \
  --allocated-storage 100 \
  --master-username dhanyada \
  --master-user-password "secure-password" \
  --vpc-security-group-ids sg-xxx \
  --publicly-accessible false

# After instance is available, run migrations
DATABASE_URL="postgresql://dhanyada:password@dhanyada-db.xxx.us-east-1.rds.amazonaws.com:5432/dhanyada" \
  alembic upgrade head

# Enable automated backups
aws rds modify-db-instance \
  --db-instance-identifier dhanyada-db \
  --backup-retention-period 30 \
  --enable-iam-database-authentication
```

#### Option 2: Self-Hosted PostgreSQL on EC2

```bash
# SSH into EC2 instance
ssh -i your-key.pem ubuntu@your-instance-ip

# Install PostgreSQL 16
sudo apt-get update
sudo apt-get install -y postgresql-16 postgresql-contrib-16

# Start PostgreSQL
sudo systemctl start postgresql

# Create database and user
sudo -u postgres psql << EOF
CREATE USER dhanyada WITH PASSWORD 'secure-password';
CREATE DATABASE dhanyada OWNER dhanyada;
GRANT ALL PRIVILEGES ON DATABASE dhanyada TO dhanyada;
\connect dhanyada
ALTER SCHEMA public OWNER TO dhanyada;
EOF

# Configure PostgreSQL for remote connections
sudo nano /etc/postgresql/16/main/postgresql.conf
# Change: listen_addresses = 'localhost' → listen_addresses = '*'

sudo nano /etc/postgresql/16/main/pg_hba.conf
# Add: host    dhanyada    dhanyada    10.0.0.0/8    md5

sudo systemctl restart postgresql
```

### Database Migrations

```bash
# Check current schema version
docker-compose exec app alembic current

# List all migrations
docker-compose exec app alembic history

# Run migrations
docker-compose exec app alembic upgrade head

# Rollback one version
docker-compose exec app alembic downgrade -1

# Create a new migration (after model changes)
docker-compose exec app alembic revision --autogenerate -m "Add new_column to user_table"
```

---

## Docker Setup

### Build Docker Image Locally

```bash
# Build image with production optimizations
docker build -t dhanyada:latest .

# Check image size
docker image ls dhanyada

# Expected size: ~200MB (multi-stage build optimization)

# Test image locally
docker run -p 8000:8000 \
  -e DATABASE_URL="sqlite:///./test.db" \
  -e REDIS_URL="redis://redis:6379" \
  --name dhanyada-test \
  dhanyada:latest

# Health check
curl http://localhost:8000/health

# Stop container
docker stop dhanyada-test
```

### Push to Docker Hub

```bash
# Login to Docker Hub
docker login -u your-username

# Tag image
docker tag dhanyada:latest your-username/dhanyada:latest
docker tag dhanyada:latest your-username/dhanyada:v1.0.0

# Push to Docker Hub
docker push your-username/dhanyada:latest
docker push your-username/dhanyada:v1.0.0

# Verify image is available
docker pull your-username/dhanyada:latest
```

### GitHub Actions Automatic Builds

Merges to main branch automatically:
1. Run tests and lint checks
2. Build Docker image
3. Push to Docker Hub with tags: `latest`, `git-sha`, `branch-name`

No manual docker push needed — CI/CD handles it.

---

## VPS Deployment (DigitalOcean / Linode / AWS EC2)

### Step 1: Provision VPS

**Recommended:** Ubuntu 22.04 LTS, 2GB RAM, 50GB SSD (~$6/month)

```bash
# SSH into VPS
ssh -i your-key.pem root@your-server-ip

# Update system
apt-get update && apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Add user to docker group
usermod -aG docker $USER
newgrp docker

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

### Step 2: Clone and Configure

```bash
# Clone repository
git clone https://github.com/yourusername/dhanyada.git /app
cd /app

# Create .env file with production secrets
nano .env
# Edit with your credentials (see Environment Setup section)

# Ensure proper permissions
chmod 600 .env
```

### Step 3: Start Services

```bash
# Pull latest image from Docker Hub
docker-compose pull

# Start all services (database, cache, app, workers)
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f app

# Wait ~30 seconds for app to start, then test
curl http://localhost:8000/health
```

### Step 4: Setup Reverse Proxy (Nginx)

```bash
# Install Nginx
apt-get install -y nginx

# Create Nginx config
nano /etc/nginx/sites-available/dhanyada

# Paste this configuration:
```

```nginx
upstream dhanyada_app {
    server localhost:8000;
}

server {
    listen 80;
    server_name your-domain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL certificates (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;

    # Proxy requests to FastAPI
    location / {
        proxy_pass http://dhanyada_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # Webhook (high timeout for message processing)
    location /webhook/ {
        proxy_pass http://dhanyada_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 30s;
        proxy_connect_timeout 10s;
    }
}
```

```bash
# Enable site
ln -s /etc/nginx/sites-available/dhanyada /etc/nginx/sites-enabled/
rm /etc/nginx/sites-enabled/default

# Test Nginx config
nginx -t

# Start Nginx
systemctl start nginx
systemctl enable nginx
```

### Step 5: Enable HTTPS (Let's Encrypt)

```bash
# Install Certbot
apt-get install -y certbot python3-certbot-nginx

# Get certificate
certbot certonly --standalone -d your-domain.com

# Auto-renewal
certbot renew --dry-run

# Restart Nginx with SSL config
systemctl restart nginx
```

### Step 6: Update WhatsApp Webhook URL

In Meta App Dashboard:
1. Go to **App Configuration** → **WhatsApp**
2. Update webhook URL to: `https://your-domain.com/webhook/whatsapp`
3. Verify token: (use `WHATSAPP_VERIFY_TOKEN` from .env)

---

## Monitoring & Health Checks

### Service Health Status

```bash
# Check all services are healthy
docker-compose ps

# Should show:
# postgres      ✓ healthy
# redis         ✓ healthy
# app           ✓ healthy
# worker        ✓ running (no health check)
# beat          ✓ running (no health check)
```

### API Health Endpoint

```bash
# Test health endpoint
curl https://your-domain.com/health

# Response:
# {
#   "status": "ok",
#   "services": {
#     "postgres": "ok",
#     "redis": "ok",
#     "whatsapp_api": "ok"
#   }
# }
```

### Admin Dashboard

Access error logs and service health:
- URL: `https://your-domain.com/admin/`
- Username: `admin`
- Password: (from `ADMIN_PASSWORD` .env)

Tabs:
- **Overview** — Key metrics (DAU, messages, broadcasts)
- **System Health** — Service status (green/yellow/red)
- **Error Logs** — Last 50 errors with filters
- **Alerts** — Email alerts triggered and when

### Monitoring Services

To monitor production instance:

```bash
# SSH into server
ssh -i your-key.pem ubuntu@your-server-ip

# View logs in real-time
docker-compose logs -f app

# Check database connection
docker-compose exec postgres pg_isready -U dhanyada

# Check Redis connection
docker-compose exec redis redis-cli ping

# Monitor system resources
htop

# View disk usage
df -h

# View PostgreSQL database size
docker-compose exec postgres psql -U dhanyada -d dhanyada -c "SELECT pg_size_pretty(pg_database_size('dhanyada'));"
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check service logs
docker-compose logs postgres
docker-compose logs app
docker-compose logs worker

# Common issues:
# 1. Port already in use: "bind: address already in use"
#    Fix: Change port in docker-compose.yml or stop conflicting process

# 2. Database connection refused
#    Fix: Wait 30 seconds for postgres to start, check DATABASE_URL env var

# 3. Out of disk space
#    Fix: docker system prune  (removes unused images/containers)
```

### High Memory Usage

```bash
# Check which containers use most memory
docker stats

# Reduce Redis/PostgreSQL memory:
# In docker-compose.yml, add limits:
# services:
#   redis:
#     deploy:
#       resources:
#         limits:
#           memory: 256M
#   postgres:
#     deploy:
#       resources:
#         limits:
#           memory: 512M

# Restart services
docker-compose down
docker-compose up -d
```

### Database Disk Growing Too Fast

```bash
# Check largest tables
docker-compose exec postgres psql -U dhanyada -d dhanyada << EOF
SELECT 
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
EOF

# Error logs growing too large?
# Truncate old error logs:
docker-compose exec postgres psql -U dhanyada -d dhanyada << EOF
DELETE FROM error_log WHERE created_at < NOW() - INTERVAL '90 days';
VACUUM error_log;
EOF

# Or configure in config.py: error_retention_days = 30
```

### WhatsApp Webhook Not Receiving Messages

```bash
# 1. Check webhook URL in Meta Dashboard
#    - Should be: https://your-domain.com/webhook/whatsapp
#    - Not localhost!

# 2. Check logs for errors
docker-compose logs -f app | grep webhook

# 3. Verify verify token
docker-compose logs app | grep -i "token"

# 4. Check Nginx is proxying correctly
curl -H "hub.verify_token: your_token" \
     -H "hub.challenge: test" \
     "https://your-domain.com/webhook/whatsapp"

# 5. Check CORS if frontend issues
#    - CORS should be configured for your domain in src/main.py
```

---

## Updating Application

### Pull Latest Code

```bash
# SSH into production server
ssh -i your-key.pem ubuntu@your-server-ip
cd /app

# Pull latest changes
git pull origin main

# Restart services with new image
docker-compose down
docker-compose pull
docker-compose up -d

# Verify all services started
docker-compose ps
docker-compose logs -f app
```

### Database Migrations

```bash
# After pulling code with schema changes
docker-compose exec app alembic upgrade head

# Verify migration
docker-compose exec app alembic current

# Rollback if needed
docker-compose exec app alembic downgrade -1
```

### Zero-Downtime Deployment (Advanced)

Using health checks and gradual rollout:

```bash
# 1. Update docker-compose to run 2 app instances
#    (behind Nginx load balancer)

# 2. Drain traffic from first instance
docker-compose pause app_1

# 3. Pull and restart
docker-compose up -d app_1

# 4. Verify health
curl http://localhost:8000/health

# 5. Resume traffic
docker-compose unpause app_1

# 6. Repeat for app_2
```

---

## Scaling (Horizontal Expansion)

### Add More Workers

For high message volume, run multiple Celery workers:

```yaml
# docker-compose.yml
services:
  worker-1:
    build: .
    command: celery -A src.scheduler.celery_app worker -l info -n worker1@%h
    depends_on:
      - redis
      - postgres
    environment:
      DATABASE_URL: ${DATABASE_URL}
      REDIS_URL: ${REDIS_URL}

  worker-2:
    build: .
    command: celery -A src.scheduler.celery_app worker -l info -n worker2@%h
    depends_on:
      - redis
      - postgres
```

```bash
# Start with multiple workers
docker-compose up -d worker-1 worker-2

# Monitor task queue
docker-compose exec redis redis-cli LLEN celery
```

### Load Balancer Setup (Multiple Instances)

Using AWS ELB or Nginx upstream:

```nginx
upstream dhanyada_apps {
    server app-instance-1:8000;
    server app-instance-2:8000;
    server app-instance-3:8000;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    location / {
        proxy_pass http://dhanyada_apps;
        # ... other proxy settings
    }
}
```

---

## Backup & Recovery

### Database Backups

```bash
# Backup PostgreSQL database
docker-compose exec postgres pg_dump -U dhanyada dhanyada > dhanyada_backup.sql

# Backup to compressed file
docker-compose exec postgres pg_dump -U dhanyada -Fc dhanyada > dhanyada_backup.dump

# Restore from backup
docker-compose exec -T postgres pg_restore -U dhanyada -d dhanyada < dhanyada_backup.dump
```

### Automated Daily Backups

```bash
# Create backup script
nano /app/backup.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/backups/dhanyada"
mkdir -p $BACKUP_DIR

# PostgreSQL backup
docker-compose exec -T postgres pg_dump -U dhanyada -Fc dhanyada > \
  $BACKUP_DIR/db_$(date +%Y%m%d_%H%M%S).dump

# Keep only last 7 days
find $BACKUP_DIR -name "db_*.dump" -mtime +7 -delete

# Optional: Upload to S3
# aws s3 sync $BACKUP_DIR s3://your-backup-bucket/dhanyada/
```

```bash
# Make executable
chmod +x /app/backup.sh

# Add to crontab (daily at 2 AM)
crontab -e
# Add: 0 2 * * * /app/backup.sh
```

### Restore from Backup

```bash
# List available backups
ls -la /backups/dhanyada/

# Restore specific backup
docker-compose exec -T postgres pg_restore -U dhanyada -d dhanyada \
  < /backups/dhanyada/db_20260418_020000.dump
```

---

## Security Hardening

### Firewall Rules

```bash
# UFW (on Ubuntu)
ufw allow 22/tcp      # SSH
ufw allow 80/tcp      # HTTP
ufw allow 443/tcp     # HTTPS
ufw enable
```

### SSH Key Management

```bash
# Disable password authentication
nano /etc/ssh/sshd_config
# Set: PasswordAuthentication no
# Set: PubkeyAuthentication yes

systemctl restart ssh
```

### Environment Secrets

**Never commit .env to Git:**

```bash
# .gitignore should include:
.env
.env.local
.env.*.local
```

**Use secrets management:**

```bash
# AWS Secrets Manager
aws secretsmanager create-secret \
  --name dhanyada/production \
  --secret-string file://production-secrets.json

# Then reference in docker-compose or deployment:
# DATABASE_URL: ${DATABASE_PASSWORD} (from AWS Secrets Manager)
```

---

## Performance Tuning

### PostgreSQL Optimization

```bash
# SSH into postgres container and edit config
docker-compose exec postgres nano /etc/postgresql/16/main/postgresql.conf

# For small instances (2GB RAM):
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100

# Restart
docker-compose restart postgres
```

### Redis Optimization

```bash
# For caching (no persistence needed in this config)
# Current config uses AOF (appendonly yes) — good for data freshness

# Monitor Redis memory
docker-compose exec redis redis-cli info memory

# Set max memory policy
docker-compose exec redis redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

### FastAPI Application Tuning

In production, run multiple workers:

```yaml
# docker-compose.yml - app service
services:
  app:
    build: .
    command: gunicorn src.main:app -w 4 -b 0.0.0.0:8000 --worker-class uvicorn.workers.UvicornWorker
    # -w 4 = 4 worker processes (adjust based on CPU cores)
```

---

## Production Checklist

See [PRODUCTION_CHECKLIST.md](./PRODUCTION_CHECKLIST.md) for detailed pre-launch validation.

Key items:
- ✅ All tests pass locally
- ✅ Docker image builds successfully
- ✅ All services healthy in docker-compose
- ✅ Environment variables configured (no secrets in code)
- ✅ Database migrations run
- ✅ HTTPS/SSL certificate installed
- ✅ WhatsApp webhook URL updated
- ✅ Email alerts configured
- ✅ Monitoring dashboard accessible
- ✅ Backups tested

---

## Support & Debugging

For debugging in production:

```bash
# 1. Check service status
docker-compose ps

# 2. View application logs (last 100 lines)
docker-compose logs app --tail=100

# 3. Check database integrity
docker-compose exec postgres psql -U dhanyada -d dhanyada \
  -c "SELECT COUNT(*) FROM user_table;"

# 4. Monitor in real-time
docker stats

# 5. Check API response times
curl -w "Time: %{time_total}s\n" https://your-domain.com/health
```

---

## Next Steps

1. **[Deploy to VPS](#vps-deployment-digitalocean--linode--aws-ec2)** using DigitalOcean or AWS EC2
2. **[Configure HTTPS](#step-5-enable-https-lets-encrypt)** with Let's Encrypt
3. **[Update WhatsApp Webhook](#step-6-update-whatsapp-webhook-url)** in Meta Dashboard
4. **[Setup Monitoring](#monitoring--health-checks)** via Admin Dashboard
5. **[Configure Backups](#backup--recovery)** for disaster recovery
6. **[Test End-to-End](#troubleshooting)** with real WhatsApp messages

For Kubernetes deployment, see Phase 4 documentation.
