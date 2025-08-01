# Security Guide

## Overview

The Payroll Management System implements comprehensive security measures to protect sensitive employee and financial data. This guide covers security architecture, authentication, authorization, data protection, and best practices.

## Security Architecture

### Defense in Depth

The system implements multiple layers of security:

1. **Network Security**: HTTPS encryption, firewall configuration
2. **Application Security**: Input validation, authentication, authorization
3. **Data Security**: Encryption at rest and in transit
4. **Infrastructure Security**: Server hardening, monitoring
5. **Access Control**: Role-based permissions, audit logging

### Security Principles

- **Principle of Least Privilege**: Users have minimum required permissions
- **Defense in Depth**: Multiple security layers
- **Fail Securely**: System defaults to secure state on failure
- **Complete Mediation**: All access requests are checked
- **Security by Design**: Security integrated from the start

## Authentication

### JWT Token Authentication

The system uses JSON Web Tokens (JWT) for authentication:

```python
# Token structure
{
  "sub": "user_id",
  "exp": 1640995200,
  "iat": 1640991600,
  "type": "access",
  "permissions": ["read:employees", "write:payroll"]
}
```

### Token Types

1. **Access Token**: Short-lived (30 minutes), used for API requests
2. **Refresh Token**: Long-lived (7 days), used to obtain new access tokens

### Token Security

- Tokens are signed with HMAC-SHA256
- Secret keys are stored securely in environment variables
- Tokens include expiration times
- Refresh tokens are invalidated on logout

### Password Security

```python
# Password requirements
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number
- At least one special character

# Password hashing
- Uses bcrypt with salt
- Cost factor: 12 rounds
- Passwords are never stored in plain text
```

## Authorization

### Role-Based Access Control (RBAC)

The system implements fine-grained permissions:

```python
# User roles
ADMIN = "admin"           # Full system access
HR_MANAGER = "hr_manager"  # Employee and payroll management
PAYROLL_CLERK = "payroll_clerk"  # Payroll processing only
EMPLOYEE = "employee"      # Read-only access to own data

# Permissions
permissions = {
    "admin": ["*"],
    "hr_manager": [
        "read:employees", "write:employees",
        "read:payroll", "write:payroll",
        "read:reports"
    ],
    "payroll_clerk": [
        "read:employees", "read:payroll",
        "write:payroll", "read:reports"
    ],
    "employee": [
        "read:own_data"
    ]
}
```

### Permission Checking

```python
from functools import wraps
from fastapi import HTTPException, Depends

def require_permission(permission: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user = get_current_user()
            if not user.has_permission(permission):
                raise HTTPException(
                    status_code=403,
                    detail="Insufficient permissions"
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Usage
@require_permission("write:employees")
async def create_employee(employee_data: EmployeeCreate):
    # Implementation
    pass
```

## Data Protection

### Encryption at Rest

Sensitive data is encrypted before storage:

```python
# Encrypted fields
- Bank account numbers
- Social Security Numbers
- Tax identification numbers
- Salary information
- Personal identification data

# Encryption method
- AES-256 encryption
- Unique encryption keys per field
- Keys stored in secure key management system
```

### Encryption in Transit

All communication uses HTTPS:

```python
# HTTPS configuration
- TLS 1.2 or higher
- Strong cipher suites only
- HSTS headers enabled
- Certificate pinning for API clients
```

### Data Masking

Sensitive data is masked in logs and non-production environments:

```python
# Masking examples
"ssn": "***-**-1234"      # Show only last 4 digits
"account": "****5678"      # Show only last 4 digits
"salary": "[REDACTED]"     # Hide completely in logs
```

## Input Validation

### Data Validation

All input data is validated using Pydantic schemas:

```python
from pydantic import BaseModel, validator, EmailStr
from typing import Optional
import re

class EmployeeCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    ssn: str
    salary: float
    
    @validator('first_name', 'last_name')
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError('Name cannot be empty')
        if len(v) > 50:
            raise ValueError('Name too long')
        if not re.match(r'^[a-zA-Z\s\-\.]+$', v):
            raise ValueError('Invalid name format')
        return v.strip()
    
    @validator('ssn')
    def validate_ssn(cls, v):
        # Remove dashes and validate format
        ssn = re.sub(r'[^\d]', '', v)
        if len(ssn) != 9:
            raise ValueError('Invalid SSN format')
        return ssn
    
    @validator('salary')
    def validate_salary(cls, v):
        if v <= 0:
            raise ValueError('Salary must be positive')
        if v > 1000000:  # Reasonable upper limit
            raise ValueError('Salary exceeds maximum')
        return v
```

### SQL Injection Prevention

- All database queries use parameterized statements
- SQLAlchemy ORM prevents SQL injection
- Input sanitization for dynamic queries

```python
# Safe query example
def get_employee_by_id(db: Session, employee_id: int):
    return db.query(Employee).filter(Employee.id == employee_id).first()

# Unsafe query (never do this)
# query = f"SELECT * FROM employees WHERE id = {employee_id}"
```

## Security Headers

### HTTP Security Headers

```python
# Implemented security headers
{
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'",
    "Referrer-Policy": "strict-origin-when-cross-origin"
}
```

### CORS Configuration

```python
# CORS settings
CORS_ALLOWED_ORIGINS = [
    "https://app.payrollsystem.com",
    "https://admin.payrollsystem.com"
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = ["GET", "POST", "PUT", "DELETE"]
CORS_ALLOW_HEADERS = ["Authorization", "Content-Type"]
```

## Audit Logging

### Audit Trail

All system actions are logged for compliance:

```python
# Audit log structure
{
    "timestamp": "2023-12-16T10:00:00Z",
    "user_id": "user123",
    "action": "employee.create",
    "resource": "employee",
    "resource_id": "EMP001",
    "ip_address": "192.168.1.100",
    "user_agent": "PayrollApp/1.0",
    "success": true,
    "details": {
        "employee_name": "John Doe",
        "department": "Engineering"
    }
}
```

### Logged Actions

- User authentication/logout
- Employee creation/modification
- Payroll processing
- Report generation
- Configuration changes
- Failed access attempts

### Log Security

- Logs are tamper-proof
- Centralized log management
- Encrypted log storage
- Access restricted to authorized personnel

## Session Management

### Session Security

```python
# Session configuration
SESSION_TIMEOUT = 1800  # 30 minutes
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_REGENERATE_ON_AUTH = True
```

### Session Tracking

- Track concurrent sessions
- Limit sessions per user
- Automatic session cleanup
- Session invalidation on password change

## Rate Limiting

### API Rate Limiting

```python
# Rate limits by endpoint type
RATE_LIMITS = {
    "auth": "10/minute",      # Authentication endpoints
    "api": "100/minute",      # Regular API endpoints
    "reports": "5/minute",    # Report generation
    "bulk": "1/minute"        # Bulk operations
}

# Rate limiting by user role
ROLE_RATE_LIMITS = {
    "admin": "1000/hour",
    "hr_manager": "500/hour",
    "payroll_clerk": "300/hour",
    "employee": "100/hour"
}
```

### DDoS Protection

- Rate limiting at multiple levels
- IP-based blocking
- CAPTCHA for suspicious activity
- Load balancer protection

## Vulnerability Management

### Security Scanning

```bash
# Dependency vulnerability scanning
pip-audit

# Code security scanning
bandit -r app/

# Static analysis
semgrep --config=auto app/

# Docker image scanning
trivy image payroll-system:latest
```

### Penetration Testing

- Regular security assessments
- Automated vulnerability scanning
- Manual penetration testing
- Bug bounty program

## Incident Response

### Security Incident Response Plan

1. **Detection**: Automated monitoring and alerting
2. **Analysis**: Incident classification and impact assessment
3. **Containment**: Isolate affected systems
4. **Eradication**: Remove threat and fix vulnerabilities
5. **Recovery**: Restore systems and services
6. **Lessons Learned**: Document and improve processes

### Security Monitoring

```python
# Security events to monitor
- Failed authentication attempts
- Unusual access patterns
- Privilege escalation attempts
- Data export activities
- System configuration changes
- Network anomalies
```

## Compliance

### Regulatory Compliance

- **GDPR**: Data protection and privacy rights
- **CCPA**: California Consumer Privacy Act
- **SOX**: Sarbanes-Oxley Act compliance
- **PCI DSS**: Payment card industry standards (if applicable)

### Data Retention

```python
# Data retention policies
{
    "employee_records": "7 years after termination",
    "payroll_records": "4 years",
    "tax_records": "7 years",
    "audit_logs": "10 years",
    "session_logs": "1 year"
}
```

### Data Subject Rights

- Right to access personal data
- Right to rectification
- Right to erasure
- Right to data portability
- Right to restrict processing

## Security Configuration

### Environment Variables

```bash
# Security-related environment variables
SECRET_KEY="your-secret-key-here"
DATABASE_URL="postgresql://user:pass@localhost/db"
REDIS_URL="redis://localhost:6379"
ENCRYPTION_KEY="your-encryption-key"
JWT_SECRET="your-jwt-secret"
```

### Security Best Practices

1. **Use Strong Passwords**: Enforce password complexity
2. **Enable 2FA**: Multi-factor authentication for admin accounts
3. **Regular Updates**: Keep dependencies up to date
4. **Secure Deployment**: Use secure hosting and configuration
5. **Monitor Logs**: Implement comprehensive logging and monitoring
6. **Backup Data**: Regular encrypted backups
7. **Network Security**: Use VPNs and firewalls
8. **Employee Training**: Security awareness training

## Security Testing

### Test Cases

```python
# Security test examples
def test_authentication_required():
    response = client.get("/api/v1/employees")
    assert response.status_code == 401

def test_authorization_required():
    token = create_token(permissions=["read:employees"])
    response = client.post(
        "/api/v1/employees",
        headers={"Authorization": f"Bearer {token}"},
        json=employee_data
    )
    assert response.status_code == 403

def test_input_validation():
    response = client.post(
        "/api/v1/employees",
        json={"first_name": "<script>alert('xss')</script>"}
    )
    assert response.status_code == 422
```

### Security Checklist

- [ ] All endpoints require authentication
- [ ] Role-based access control implemented
- [ ] Input validation on all endpoints
- [ ] SQL injection prevention
- [ ] XSS protection
- [ ] CSRF protection
- [ ] Rate limiting configured
- [ ] Security headers implemented
- [ ] Audit logging enabled
- [ ] Encryption at rest and in transit
- [ ] Regular security updates
- [ ] Vulnerability scanning
- [ ] Incident response plan
- [ ] Security documentation updated

## Security Contacts

### Reporting Security Issues

- **Security Team**: security@payrollsystem.com
- **Bug Bounty**: https://bugbounty.payrollsystem.com
- **Emergency Contact**: +1-800-SECURITY

### Security Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [CIS Controls](https://www.cisecurity.org/controls/)
- [SANS Security Policies](https://www.sans.org/information-security-policy/)

---

**Note**: This security guide should be regularly reviewed and updated as new threats emerge and security best practices evolve. 