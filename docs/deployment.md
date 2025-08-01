# Deployment Guide

## Overview

This guide covers deploying the Payroll Management System across different environments, from local development to production. It includes Docker deployment, cloud platforms, monitoring, and best practices.

## Prerequisites

### System Requirements

- **Operating System**: Ubuntu 20.04 LTS or later, CentOS 8+, or macOS 10.15+
- **Python**: 3.9 or higher
- **PostgreSQL**: 12 or higher
- **Redis**: 6.0 or higher
- **Memory**: Minimum 2GB RAM (4GB recommended for production)
- **Storage**: Minimum 20GB available space

### Dependencies

```bash
# System dependencies
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv postgresql redis-server nginx

# Python dependencies
pip install -r requirements.txt
```

## Environment Setup

### Development Environment

```bash
# Clone repository
git clone https://github.com/yourusername/payroll-management-system.git
cd payroll-management-system

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp env.example .env
# Edit .env with your configuration

# Create development database
createdb payroll_dev

# Run migrations
alembic upgrade head

# Start development server
python -m app.main
```

### Staging Environment

```bash
# Environment variables for staging
export ENVIRONMENT=staging
export DEBUG=False
export DATABASE_URL=postgresql://user:pass@staging-db:5432/payroll_staging
export REDIS_URL=redis://staging-redis:6379/0
export SECRET_KEY=your-staging-secret-key

# Install production dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start with Gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

## Docker Deployment

### Dockerfile

```dockerfile
# Dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["gunicorn", "app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000"]
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/payroll
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=your-secret-key
    depends_on:
      - db
      - redis
    volumes:
      - ./uploads:/app/uploads
      - ./logs:/app/logs
    restart: unless-stopped

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=payroll
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - app
    restart: unless-stopped

  celery:
    build: .
    command: celery -A app.worker worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/payroll
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=your-secret-key
    depends_on:
      - db
      - redis
    volumes:
      - ./uploads:/app/uploads
      - ./logs:/app/logs
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

### Docker Commands

```bash
# Build and start services
docker-compose up -d

# View logs
docker-compose logs -f app

# Run migrations
docker-compose exec app alembic upgrade head

# Access application shell
docker-compose exec app python

# Stop services
docker-compose down

# Rebuild and restart
docker-compose down && docker-compose up -d --build
```

## Cloud Deployment

### AWS Deployment

#### EC2 Instance Setup

```bash
# Launch EC2 instance (Ubuntu 20.04 LTS)
# Security group: Allow ports 22, 80, 443, 8000

# Connect to instance
ssh -i your-key.pem ubuntu@your-ec2-instance

# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
sudo usermod -aG docker ubuntu

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.0.1/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Clone and deploy
git clone https://github.com/yourusername/payroll-management-system.git
cd payroll-management-system
docker-compose up -d
```

#### RDS Database Setup

```bash
# Create RDS PostgreSQL instance
aws rds create-db-instance \
    --db-instance-identifier payroll-db \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --engine-version 15.3 \
    --master-username admin \
    --master-user-password your-password \
    --allocated-storage 20 \
    --vpc-security-group-ids sg-12345678

# Update environment variables
DATABASE_URL=postgresql://admin:password@payroll-db.region.rds.amazonaws.com:5432/payroll
```

#### ElastiCache Redis Setup

```bash
# Create ElastiCache Redis cluster
aws elasticache create-cache-cluster \
    --cache-cluster-id payroll-redis \
    --cache-node-type cache.t3.micro \
    --engine redis \
    --num-cache-nodes 1

# Update environment variables
REDIS_URL=redis://payroll-redis.region.cache.amazonaws.com:6379/0
```

### Google Cloud Platform

#### Cloud Run Deployment

```bash
# Build and push to Container Registry
gcloud builds submit --tag gcr.io/project-id/payroll-system

# Deploy to Cloud Run
gcloud run deploy payroll-system \
    --image gcr.io/project-id/payroll-system \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --set-env-vars DATABASE_URL=postgresql://...,REDIS_URL=redis://...
```

#### Cloud SQL Setup

```bash
# Create Cloud SQL instance
gcloud sql instances create payroll-db \
    --database-version POSTGRES_15 \
    --tier db-f1-micro \
    --region us-central1

# Create database and user
gcloud sql databases create payroll --instance payroll-db
gcloud sql users create payroll-user --instance payroll-db --password your-password
```

### Azure Deployment

#### Container Instances

```bash
# Create resource group
az group create --name payroll-rg --location eastus

# Create container instance
az container create \
    --resource-group payroll-rg \
    --name payroll-app \
    --image your-registry/payroll-system:latest \
    --ports 8000 \
    --environment-variables DATABASE_URL=postgresql://... REDIS_URL=redis://...
```

## Production Configuration

### Nginx Configuration

```nginx
# nginx.conf
events {
    worker_connections 1024;
}

http {
    upstream app {
        server app:8000;
    }

    server {
        listen 80;
        server_name your-domain.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name your-domain.com;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

        client_max_body_size 10M;

        location / {
            proxy_pass http://app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /health {
            access_log off;
            proxy_pass http://app;
        }
    }
}
```

### SSL Certificate Setup

```bash
# Using Let's Encrypt
sudo apt-get install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

### Environment Variables

```bash
# Production environment variables
export ENVIRONMENT=production
export DEBUG=False
export SECRET_KEY=your-production-secret-key
export DATABASE_URL=postgresql://user:pass@prod-db:5432/payroll
export REDIS_URL=redis://prod-redis:6379/0
export ALLOWED_HOSTS=your-domain.com,www.your-domain.com
```

## Database Management

### Backup Strategy

```bash
# Daily database backup
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"
DB_NAME="payroll"

# Create backup
pg_dump $DATABASE_URL > $BACKUP_DIR/payroll_backup_$DATE.sql

# Compress backup
gzip $BACKUP_DIR/payroll_backup_$DATE.sql

# Remove backups older than 30 days
find $BACKUP_DIR -name "payroll_backup_*.sql.gz" -mtime +30 -delete

# Upload to S3 (optional)
aws s3 cp $BACKUP_DIR/payroll_backup_$DATE.sql.gz s3://your-backup-bucket/
```

### Migration Management

```bash
# Run migrations
alembic upgrade head

# Rollback migrations
alembic downgrade -1

# Generate new migration
alembic revision --autogenerate -m "Add new table"

# Check migration status
alembic current
alembic history
```

## Monitoring and Logging

### Health Checks

```python
# app/health.py
from fastapi import APIRouter
from app.core.database import check_database_health
from app.core.redis import check_redis_health

router = APIRouter()

@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "payroll-management-system"}

@router.get("/health/database")
async def database_health():
    healthy = await check_database_health()
    return {"status": "healthy" if healthy else "unhealthy", "service": "database"}

@router.get("/health/redis")
async def redis_health():
    healthy = await check_redis_health()
    return {"status": "healthy" if healthy else "unhealthy", "service": "redis"}
```

### Logging Configuration

```python
# app/core/logging.py
import logging
import logging.config
from pathlib import Path

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
        "json": {
            "format": '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}',
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "level": "INFO",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/payroll.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "formatter": "json",
            "level": "INFO",
        },
    },
    "loggers": {
        "app": {
            "level": "INFO",
            "handlers": ["console", "file"],
            "propagate": False,
        },
        "uvicorn": {
            "level": "INFO",
            "handlers": ["console", "file"],
            "propagate": False,
        },
    },
}

def setup_logging():
    Path("logs").mkdir(exist_ok=True)
    logging.config.dictConfig(LOGGING_CONFIG)
```

### Monitoring with Prometheus

```python
# app/monitoring.py
from prometheus_client import Counter, Histogram, generate_latest
from fastapi import Response

# Metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')

@app.middleware("http")
async def add_prometheus_middleware(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path).inc()
    REQUEST_DURATION.observe(duration)
    
    return response

@app.get("/metrics")
async def get_metrics():
    return Response(generate_latest(), media_type="text/plain")
```

## Performance Optimization

### Database Optimization

```python
# Database connection pooling
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600,
)
```

### Caching Strategy

```python
# Redis caching
import redis
from functools import wraps

redis_client = redis.Redis.from_url(REDIS_URL)

def cache_result(expiry=300):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            cached = redis_client.get(key)
            if cached:
                return json.loads(cached)
            
            result = await func(*args, **kwargs)
            redis_client.setex(key, expiry, json.dumps(result))
            return result
        return wrapper
    return decorator
```

### Load Balancing

```bash
# HAProxy configuration
global
    daemon

defaults
    mode http
    timeout connect 5000ms
    timeout client 50000ms
    timeout server 50000ms

frontend payroll_frontend
    bind *:80
    default_backend payroll_backend

backend payroll_backend
    balance roundrobin
    server app1 app1:8000 check
    server app2 app2:8000 check
    server app3 app3:8000 check
```

## Security in Production

### Firewall Configuration

```bash
# UFW firewall setup
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### Secret Management

```bash
# Using AWS Secrets Manager
aws secretsmanager create-secret \
    --name payroll-secrets \
    --secret-string '{"DATABASE_URL":"postgresql://...","SECRET_KEY":"..."}'

# Retrieve secrets
SECRET=$(aws secretsmanager get-secret-value --secret-id payroll-secrets --query SecretString --output text)
export DATABASE_URL=$(echo $SECRET | jq -r .DATABASE_URL)
export SECRET_KEY=$(echo $SECRET | jq -r .SECRET_KEY)
```

## Troubleshooting

### Common Issues

1. **Database Connection Error**
   ```bash
   # Check database connectivity
   pg_isready -h localhost -p 5432
   
   # Check database logs
   docker-compose logs db
   ```

2. **Redis Connection Error**
   ```bash
   # Check Redis connectivity
   redis-cli ping
   
   # Check Redis logs
   docker-compose logs redis
   ```

3. **Application Not Starting**
   ```bash
   # Check application logs
   docker-compose logs app
   
   # Check environment variables
   docker-compose exec app env
   ```

### Performance Issues

```bash
# Check system resources
top
htop
df -h

# Check database performance
docker-compose exec db psql -U postgres -c "SELECT * FROM pg_stat_activity;"

# Check Redis performance
docker-compose exec redis redis-cli info
```

## Backup and Recovery

### Automated Backups

```bash
# Backup script
#!/bin/bash
# /scripts/backup.sh

set -e

# Configuration
BACKUP_DIR="/backups"
S3_BUCKET="your-backup-bucket"
RETENTION_DAYS=30

# Create backup directory
mkdir -p $BACKUP_DIR

# Database backup
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump $DATABASE_URL | gzip > $BACKUP_DIR/db_backup_$DATE.sql.gz

# Upload to S3
aws s3 cp $BACKUP_DIR/db_backup_$DATE.sql.gz s3://$S3_BUCKET/database/

# Clean old backups
find $BACKUP_DIR -name "db_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete
aws s3 ls s3://$S3_BUCKET/database/ | grep "db_backup_" | head -n -$RETENTION_DAYS | awk '{print $4}' | xargs -I {} aws s3 rm s3://$S3_BUCKET/database/{}

echo "Backup completed successfully"
```

### Recovery Process

```bash
# Database recovery
gunzip -c db_backup_20231216_100000.sql.gz | psql $DATABASE_URL

# Application recovery
docker-compose down
docker-compose up -d
```

## Deployment Checklist

### Pre-deployment

- [ ] Code review completed
- [ ] Tests passing
- [ ] Security scan completed
- [ ] Database migrations tested
- [ ] Environment variables configured
- [ ] SSL certificates installed
- [ ] Backup strategy implemented
- [ ] Monitoring configured

### Deployment

- [ ] Application deployed
- [ ] Database migrations applied
- [ ] Health checks passing
- [ ] SSL certificate valid
- [ ] Monitoring active
- [ ] Logs accessible
- [ ] Performance acceptable

### Post-deployment

- [ ] Smoke tests completed
- [ ] User acceptance testing
- [ ] Performance monitoring
- [ ] Error monitoring
- [ ] Backup verification
- [ ] Documentation updated

---

This deployment guide provides comprehensive instructions for deploying the Payroll Management System across different environments. Always test deployments in staging before production and maintain proper backup and monitoring procedures. 