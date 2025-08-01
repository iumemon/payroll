# Troubleshooting Guide

## Overview

This guide provides solutions to common issues encountered when running the Payroll Management System. It covers installation problems, runtime errors, performance issues, and debugging techniques.

## Common Issues and Solutions

### 1. Installation and Setup Issues

#### Problem: Python Virtual Environment Not Working

**Symptoms:**
- Command not found errors
- Package installation failures
- Version conflicts

**Solution:**
```bash
# Check Python version
python --version

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows
venv\Scripts\activate
# On Unix/macOS
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt
```

#### Problem: Database Connection Error

**Symptoms:**
```
FATAL: database "payroll" does not exist
FATAL: password authentication failed for user "postgres"
```

**Solution:**
```bash
# Check PostgreSQL service status
sudo service postgresql status

# Start PostgreSQL if not running
sudo service postgresql start

# Create database
createdb payroll

# Check connection
psql -h localhost -U postgres -d payroll -c "SELECT 1;"

# Update .env file with correct credentials
DATABASE_URL=postgresql://username:password@localhost:5432/payroll
```

#### Problem: Redis Connection Error

**Symptoms:**
```
redis.exceptions.ConnectionError: Error 111 connecting to localhost:6379
```

**Solution:**
```bash
# Check Redis service status
sudo service redis-server status

# Start Redis if not running
sudo service redis-server start

# Test connection
redis-cli ping

# Update .env file
REDIS_URL=redis://localhost:6379/0
```

### 2. Runtime Errors

#### Problem: JWT Token Validation Error

**Symptoms:**
```
401 Unauthorized: Invalid token
403 Forbidden: Token expired
```

**Solution:**
```python
# Check token expiration
import jwt
from datetime import datetime

token = "your-jwt-token"
try:
    payload = jwt.decode(token, verify=False)
    exp = datetime.fromtimestamp(payload['exp'])
    print(f"Token expires at: {exp}")
except jwt.DecodeError:
    print("Invalid token format")

# Generate new token
from app.core.security import create_access_token
new_token = create_access_token(subject="user_id")
```

#### Problem: Database Migration Errors

**Symptoms:**
```
alembic.util.exc.CommandError: Target database is not up to date
SQLALCHEMY_DATABASE_URI not set
```

**Solution:**
```bash
# Check current migration status
alembic current

# Check migration history
alembic history

# Stamp database to current revision
alembic stamp head

# Run migrations
alembic upgrade head

# If migrations fail, rollback and try again
alembic downgrade -1
alembic upgrade head
```

#### Problem: Payroll Calculation Errors

**Symptoms:**
```
ValueError: Salary must be positive
TypeError: unsupported operand type(s) for *: 'NoneType' and 'float'
```

**Solution:**
```python
# Check employee data
from app.models import Employee
employee = Employee.query.filter_by(id=employee_id).first()
if not employee:
    raise ValueError("Employee not found")

if employee.salary is None or employee.salary <= 0:
    raise ValueError("Invalid salary amount")

# Validate tax rates
from app.models import TaxRate
tax_rates = TaxRate.query.filter_by(is_active=True).all()
if not tax_rates:
    raise ValueError("No active tax rates found")
```

### 3. Performance Issues

#### Problem: Slow Database Queries

**Symptoms:**
- API responses taking more than 5 seconds
- Database timeout errors
- High CPU usage

**Solution:**
```sql
-- Identify slow queries
SELECT query, mean_time, calls, total_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- Check for missing indexes
SELECT schemaname, tablename, attname, n_distinct, correlation
FROM pg_stats
WHERE schemaname = 'public'
  AND n_distinct > 100
ORDER BY n_distinct DESC;

-- Add missing indexes
CREATE INDEX idx_employees_department_status ON employees(department_id, status);
CREATE INDEX idx_payroll_items_employee_run ON payroll_items(employee_id, payroll_run_id);

-- Update table statistics
ANALYZE employees;
ANALYZE payroll_items;
```

#### Problem: Memory Usage Issues

**Symptoms:**
- Out of memory errors
- Application crashes
- High memory consumption

**Solution:**
```python
# Monitor memory usage
import psutil
import os

process = psutil.Process(os.getpid())
memory_info = process.memory_info()
print(f"Memory usage: {memory_info.rss / 1024 / 1024:.2f} MB")

# Optimize database connections
from app.core.database import async_engine

# Check connection pool settings
print(f"Pool size: {async_engine.pool.size()}")
print(f"Checked out connections: {async_engine.pool.checkedout()}")

# Reduce batch size for large operations
BATCH_SIZE = 100
for i in range(0, len(employee_ids), BATCH_SIZE):
    batch = employee_ids[i:i + BATCH_SIZE]
    process_batch(batch)
```

### 4. API Errors

#### Problem: 422 Validation Errors

**Symptoms:**
```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

**Solution:**
```python
# Check request payload
import json
from pydantic import ValidationError

try:
    # Validate data
    employee_data = EmployeeCreate(**request_data)
except ValidationError as e:
    print(f"Validation errors: {e.errors()}")
    
# Example valid payload
valid_payload = {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@company.com",
    "salary": 75000.00,
    "hire_date": "2023-01-15"
}
```

#### Problem: 500 Internal Server Error

**Symptoms:**
```
Internal Server Error
The server encountered an internal error and was unable to complete your request.
```

**Solution:**
```python
# Check application logs
import logging

logger = logging.getLogger(__name__)

try:
    # Your code here
    pass
except Exception as e:
    logger.error(f"Unexpected error: {str(e)}", exc_info=True)
    raise

# Check for common causes
# 1. Database connection issues
# 2. Missing environment variables
# 3. Unhandled exceptions
# 4. Invalid data types
```

### 5. Authentication and Authorization Issues

#### Problem: Login Failures

**Symptoms:**
```
401 Unauthorized: Invalid credentials
Account locked due to too many failed attempts
```

**Solution:**
```python
# Check user account status
from app.models import User
user = User.query.filter_by(username="admin").first()
if user:
    print(f"User active: {user.is_active}")
    print(f"Failed attempts: {user.failed_login_attempts}")
    print(f"Locked until: {user.locked_until}")

# Reset failed login attempts
user.failed_login_attempts = 0
user.locked_until = None
user.save()

# Verify password hash
from app.core.security import verify_password
is_valid = verify_password("password", user.password_hash)
print(f"Password valid: {is_valid}")
```

#### Problem: Permission Denied Errors

**Symptoms:**
```
403 Forbidden: Insufficient permissions
You don't have permission to access this resource
```

**Solution:**
```python
# Check user role and permissions
from app.models import User
user = User.query.filter_by(id=user_id).first()
print(f"User role: {user.role}")

# Check permission requirements
@require_permission("write:employees")
def create_employee():
    pass

# Update user role if needed
user.role = "hr_manager"
user.save()
```

### 6. Data Integrity Issues

#### Problem: Duplicate Employee IDs

**Symptoms:**
```
IntegrityError: (psycopg2.IntegrityError) duplicate key value violates unique constraint "employees_employee_id_key"
```

**Solution:**
```python
# Check for existing employee ID
from app.models import Employee
existing = Employee.query.filter_by(employee_id="EMP001").first()
if existing:
    print(f"Employee ID already exists: {existing.id}")

# Generate unique employee ID
import uuid
employee_id = f"EMP{uuid.uuid4().hex[:8].upper()}"

# Or use sequence
next_id = db.session.execute("SELECT nextval('employee_id_seq')").scalar()
employee_id = f"EMP{next_id:06d}"
```

#### Problem: Payroll Calculation Inconsistencies

**Symptoms:**
- Negative net pay amounts
- Tax calculations don't match expected values
- Rounding errors in calculations

**Solution:**
```python
from decimal import Decimal, ROUND_HALF_UP

# Use Decimal for financial calculations
gross_pay = Decimal('5000.00')
tax_rate = Decimal('0.22')
tax_amount = gross_pay * tax_rate

# Round to 2 decimal places
tax_amount = tax_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

# Validate calculations
assert gross_pay > 0, "Gross pay must be positive"
assert tax_amount >= 0, "Tax amount cannot be negative"
assert tax_amount <= gross_pay, "Tax amount cannot exceed gross pay"
```

## Debugging Techniques

### 1. Logging Configuration

```python
# Enable debug logging
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Log SQL queries
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Log HTTP requests
logging.getLogger('uvicorn.access').setLevel(logging.INFO)
```

### 2. Database Debugging

```sql
-- Check active connections
SELECT * FROM pg_stat_activity WHERE state = 'active';

-- Check locks
SELECT * FROM pg_locks WHERE NOT granted;

-- Check slow queries
SELECT query, mean_time, calls
FROM pg_stat_statements
WHERE mean_time > 1000
ORDER BY mean_time DESC;

-- Check table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### 3. API Testing

```bash
# Test API endpoints
curl -X GET "http://localhost:8000/health" -H "accept: application/json"

# Test authentication
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'

# Test with authentication token
curl -X GET "http://localhost:8000/api/v1/employees" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## Error Code Reference

### HTTP Status Codes

- **400 Bad Request**: Invalid request data
- **401 Unauthorized**: Authentication required
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Resource not found
- **409 Conflict**: Resource already exists
- **422 Unprocessable Entity**: Validation error
- **500 Internal Server Error**: Server error

### Application Error Codes

- **AUTH_001**: Invalid credentials
- **AUTH_002**: Token expired
- **AUTH_003**: Account locked
- **VAL_001**: Required field missing
- **VAL_002**: Invalid data format
- **VAL_003**: Data validation failed
- **DB_001**: Database connection error
- **DB_002**: Record not found
- **DB_003**: Constraint violation
- **PAY_001**: Payroll calculation error
- **PAY_002**: Invalid pay period
- **PAY_003**: Missing tax rates

## Performance Monitoring

### 1. Database Performance

```sql
-- Monitor query performance
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    rows
FROM pg_stat_statements
WHERE calls > 100
ORDER BY mean_time DESC
LIMIT 10;

-- Check index usage
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
```

### 2. Application Performance

```python
# Add performance monitoring
import time
from functools import wraps

def monitor_performance(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        result = await func(*args, **kwargs)
        duration = time.time() - start_time
        
        if duration > 1.0:  # Log slow operations
            print(f"Slow operation: {func.__name__} took {duration:.2f}s")
        
        return result
    return wrapper

@monitor_performance
async def process_payroll(employee_ids):
    # Implementation
    pass
```

## Recovery Procedures

### 1. Database Recovery

```bash
# Restore from backup
psql -h localhost -U postgres -d payroll < backup.sql

# Partial recovery
pg_restore -h localhost -U postgres -d payroll -t employees backup.dump

# Point-in-time recovery
pg_restore -h localhost -U postgres -d payroll -T payroll_runs backup.dump
```

### 2. Application Recovery

```bash
# Restart application
sudo systemctl restart payroll-app

# Check application status
sudo systemctl status payroll-app

# Check logs
sudo journalctl -u payroll-app -f
```

## Preventive Measures

### 1. Regular Maintenance

```bash
# Weekly database maintenance
#!/bin/bash
# maintenance.sh

# Update statistics
psql -d payroll -c "ANALYZE;"

# Vacuum tables
psql -d payroll -c "VACUUM ANALYZE;"

# Reindex if needed
psql -d payroll -c "REINDEX DATABASE payroll;"

# Check for corruption
psql -d payroll -c "SELECT * FROM pg_stat_database WHERE datname = 'payroll';"
```

### 2. Monitoring Scripts

```python
# health_check.py
import requests
import smtplib
from email.mime.text import MIMEText

def check_health():
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            return True
    except requests.RequestException:
        pass
    return False

def send_alert(message):
    msg = MIMEText(message)
    msg['Subject'] = 'Payroll System Alert'
    msg['From'] = 'admin@company.com'
    msg['To'] = 'it@company.com'
    
    server = smtplib.SMTP('localhost')
    server.send_message(msg)
    server.quit()

if not check_health():
    send_alert("Payroll system health check failed")
```

## Getting Help

### 1. Log Analysis

```bash
# Check application logs
tail -f logs/payroll.log

# Search for errors
grep -i "error" logs/payroll.log

# Check database logs
sudo tail -f /var/log/postgresql/postgresql-*.log
```

### 2. System Information

```bash
# System resources
free -h
df -h
top -p $(pgrep python)

# Network connections
netstat -tlnp | grep :8000
ss -tlnp | grep :8000
```

### 3. Support Channels

- **Documentation**: Check the docs/ directory
- **GitHub Issues**: https://github.com/yourusername/payroll-management-system/issues
- **Email Support**: support@payrollsystem.com
- **Emergency Contact**: +1-800-PAYROLL

## Frequently Asked Questions

### Q: How do I reset the admin password?

```python
from app.models import User
from app.core.security import get_password_hash

admin = User.query.filter_by(username="admin").first()
admin.password_hash = get_password_hash("new_password")
admin.save()
```

### Q: How do I fix payroll calculation errors?

1. Check employee salary and tax exemptions
2. Verify tax rates are up to date
3. Validate pay period dates
4. Check for missing deductions
5. Review calculation logic

### Q: How do I backup the database?

```bash
pg_dump -h localhost -U postgres payroll > backup_$(date +%Y%m%d).sql
```

### Q: How do I restore from backup?

```bash
psql -h localhost -U postgres -d payroll < backup_20231216.sql
```

This troubleshooting guide should help you identify and resolve common issues with the Payroll Management System. Always backup your data before making significant changes. 