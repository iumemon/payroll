# API Documentation

## Overview

The Payroll Management System API provides a comprehensive set of endpoints for managing employees, processing payroll, calculating taxes, and generating reports. All endpoints use RESTful conventions and return JSON responses.

## Base URL

```
Development: http://localhost:8000/api/v1
Production: https://your-domain.com/api/v1
```

## Authentication

All API endpoints require authentication using JWT tokens. Include the token in the Authorization header:

```
Authorization: Bearer <your-access-token>
```

### Authentication Endpoints

#### POST /auth/login
Authenticate user and get access token.

**Request:**
```json
{
  "username": "admin",
  "password": "password123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

#### POST /auth/refresh
Refresh access token using refresh token.

**Request:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

#### POST /auth/logout
Logout user and invalidate tokens.

**Request:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response:**
```json
{
  "message": "Successfully logged out"
}
```

## Employee Management

### GET /employees
Get list of employees with pagination.

**Query Parameters:**
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 10, max: 100)
- `search`: Search term for employee name or ID
- `department`: Filter by department
- `status`: Filter by employment status (active, inactive, terminated)

**Response:**
```json
{
  "employees": [
    {
      "id": 1,
      "employee_id": "EMP001",
      "first_name": "John",
      "last_name": "Doe",
      "email": "john.doe@company.com",
      "phone": "+1234567890",
      "department": "Engineering",
      "position": "Software Engineer",
      "hire_date": "2023-01-15",
      "salary": 75000.00,
      "status": "active",
      "created_at": "2023-01-15T10:00:00Z",
      "updated_at": "2023-01-15T10:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "pages": 1,
  "limit": 10
}
```

### POST /employees
Create a new employee.

**Request:**
```json
{
  "employee_id": "EMP002",
  "first_name": "Jane",
  "last_name": "Smith",
  "email": "jane.smith@company.com",
  "phone": "+1234567891",
  "department": "Marketing",
  "position": "Marketing Manager",
  "hire_date": "2023-02-01",
  "salary": 85000.00,
  "tax_exemptions": 2,
  "bank_account": {
    "account_number": "encrypted_account_number",
    "routing_number": "123456789",
    "bank_name": "First National Bank"
  }
}
```

**Response:**
```json
{
  "id": 2,
  "employee_id": "EMP002",
  "first_name": "Jane",
  "last_name": "Smith",
  "email": "jane.smith@company.com",
  "phone": "+1234567891",
  "department": "Marketing",
  "position": "Marketing Manager",
  "hire_date": "2023-02-01",
  "salary": 85000.00,
  "status": "active",
  "created_at": "2023-02-01T10:00:00Z",
  "updated_at": "2023-02-01T10:00:00Z"
}
```

### GET /employees/{id}
Get employee details by ID.

**Response:**
```json
{
  "id": 1,
  "employee_id": "EMP001",
  "first_name": "John",
  "last_name": "Doe",
  "email": "john.doe@company.com",
  "phone": "+1234567890",
  "department": "Engineering",
  "position": "Software Engineer",
  "hire_date": "2023-01-15",
  "salary": 75000.00,
  "status": "active",
  "tax_exemptions": 1,
  "bank_account": {
    "bank_name": "First National Bank",
    "account_last_four": "1234"
  },
  "created_at": "2023-01-15T10:00:00Z",
  "updated_at": "2023-01-15T10:00:00Z"
}
```

### PUT /employees/{id}
Update employee information.

**Request:**
```json
{
  "salary": 80000.00,
  "position": "Senior Software Engineer",
  "department": "Engineering"
}
```

**Response:**
```json
{
  "id": 1,
  "employee_id": "EMP001",
  "first_name": "John",
  "last_name": "Doe",
  "email": "john.doe@company.com",
  "phone": "+1234567890",
  "department": "Engineering",
  "position": "Senior Software Engineer",
  "hire_date": "2023-01-15",
  "salary": 80000.00,
  "status": "active",
  "updated_at": "2023-12-01T10:00:00Z"
}
```

### DELETE /employees/{id}
Deactivate employee (soft delete).

**Response:**
```json
{
  "message": "Employee successfully deactivated"
}
```

## Payroll Processing

### GET /payroll/calculate
Calculate payroll for specified period.

**Query Parameters:**
- `employee_id`: Specific employee ID (optional)
- `start_date`: Pay period start date (YYYY-MM-DD)
- `end_date`: Pay period end date (YYYY-MM-DD)
- `department`: Filter by department (optional)

**Response:**
```json
{
  "payroll_calculations": [
    {
      "employee_id": "EMP001",
      "employee_name": "John Doe",
      "gross_pay": 2916.67,
      "deductions": {
        "federal_tax": 350.00,
        "state_tax": 145.83,
        "social_security": 180.83,
        "medicare": 42.29,
        "health_insurance": 200.00
      },
      "net_pay": 1997.72,
      "pay_period": {
        "start_date": "2023-12-01",
        "end_date": "2023-12-15"
      }
    }
  ],
  "total_gross": 2916.67,
  "total_deductions": 918.95,
  "total_net": 1997.72
}
```

### POST /payroll/process
Process payroll for specified period.

**Request:**
```json
{
  "pay_period_start": "2023-12-01",
  "pay_period_end": "2023-12-15",
  "employee_ids": ["EMP001", "EMP002"],
  "payment_date": "2023-12-16"
}
```

**Response:**
```json
{
  "payroll_id": "PAY202312160001",
  "status": "processed",
  "employees_processed": 2,
  "total_gross": 5833.34,
  "total_deductions": 1837.90,
  "total_net": 3995.44,
  "payment_date": "2023-12-16",
  "created_at": "2023-12-16T10:00:00Z"
}
```

### GET /payroll/history
Get payroll processing history.

**Query Parameters:**
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 10)
- `employee_id`: Filter by employee ID
- `start_date`: Filter from date
- `end_date`: Filter to date

**Response:**
```json
{
  "payroll_history": [
    {
      "payroll_id": "PAY202312160001",
      "pay_period_start": "2023-12-01",
      "pay_period_end": "2023-12-15",
      "payment_date": "2023-12-16",
      "status": "processed",
      "employees_count": 2,
      "total_gross": 5833.34,
      "total_net": 3995.44,
      "created_at": "2023-12-16T10:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "pages": 1
}
```

## Tax Management

### GET /tax/rates
Get current tax rates.

**Response:**
```json
{
  "federal_tax_rate": 0.22,
  "state_tax_rate": 0.05,
  "social_security_rate": 0.062,
  "medicare_rate": 0.0145,
  "federal_unemployment_rate": 0.006,
  "state_unemployment_rate": 0.054,
  "effective_date": "2023-01-01"
}
```

### POST /tax/calculate
Calculate taxes for specific amount.

**Request:**
```json
{
  "gross_amount": 5000.00,
  "employee_id": "EMP001",
  "tax_exemptions": 1,
  "filing_status": "single"
}
```

**Response:**
```json
{
  "gross_amount": 5000.00,
  "federal_tax": 600.00,
  "state_tax": 250.00,
  "social_security": 310.00,
  "medicare": 72.50,
  "total_taxes": 1232.50,
  "net_amount": 3767.50
}
```

## Reports

### GET /reports/payroll
Generate payroll report.

**Query Parameters:**
- `start_date`: Report start date (YYYY-MM-DD)
- `end_date`: Report end date (YYYY-MM-DD)
- `format`: Report format (json, csv, pdf)
- `department`: Filter by department

**Response:**
```json
{
  "report_id": "RPT202312160001",
  "period": {
    "start_date": "2023-12-01",
    "end_date": "2023-12-31"
  },
  "summary": {
    "total_employees": 10,
    "total_gross": 50000.00,
    "total_deductions": 15000.00,
    "total_net": 35000.00
  },
  "by_department": [
    {
      "department": "Engineering",
      "employee_count": 5,
      "gross_pay": 30000.00,
      "net_pay": 21000.00
    }
  ],
  "generated_at": "2023-12-16T10:00:00Z"
}
```

### GET /reports/taxes
Generate tax report.

**Query Parameters:**
- `year`: Tax year (YYYY)
- `quarter`: Tax quarter (1, 2, 3, 4)
- `format`: Report format (json, csv, pdf)

**Response:**
```json
{
  "report_id": "TAX202312160001",
  "year": 2023,
  "quarter": 4,
  "summary": {
    "total_federal_tax": 12000.00,
    "total_state_tax": 5000.00,
    "total_social_security": 7440.00,
    "total_medicare": 1740.00,
    "total_withholdings": 26180.00
  },
  "by_employee": [
    {
      "employee_id": "EMP001",
      "employee_name": "John Doe",
      "federal_tax": 1200.00,
      "state_tax": 500.00,
      "social_security": 744.00,
      "medicare": 174.00
    }
  ],
  "generated_at": "2023-12-16T10:00:00Z"
}
```

## Error Handling

### Error Response Format

All API errors follow a consistent format:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {
      "field": "email",
      "error": "Invalid email format"
    }
  },
  "request_id": "req-123456789"
}
```

### Common Error Codes

- `AUTHENTICATION_ERROR`: Invalid or expired token
- `AUTHORIZATION_ERROR`: Insufficient permissions
- `VALIDATION_ERROR`: Invalid input data
- `NOT_FOUND`: Resource not found
- `DUPLICATE_ERROR`: Resource already exists
- `INTERNAL_ERROR`: Server error

### HTTP Status Codes

- `200 OK`: Successful request
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Access denied
- `404 Not Found`: Resource not found
- `409 Conflict`: Resource conflict
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server error

## Rate Limiting

API endpoints are rate-limited to prevent abuse:

- **Standard endpoints**: 100 requests per minute per user
- **Authentication endpoints**: 10 requests per minute per IP
- **Report generation**: 5 requests per minute per user

Rate limit headers are included in responses:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

## Pagination

List endpoints support pagination using query parameters:

- `page`: Page number (starts from 1)
- `limit`: Items per page (default: 10, max: 100)

Pagination information is included in responses:

```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "pages": 10,
    "limit": 10,
    "total": 100,
    "has_next": true,
    "has_prev": false
  }
}
```

## Filtering and Sorting

Many endpoints support filtering and sorting:

**Filtering:**
- Use query parameters matching field names
- Example: `?department=Engineering&status=active`

**Sorting:**
- Use `sort` parameter with field names
- Prefix with `-` for descending order
- Example: `?sort=-created_at,name`

## Webhooks

The system supports webhooks for real-time notifications:

### Webhook Events

- `employee.created`: New employee added
- `employee.updated`: Employee information updated
- `payroll.processed`: Payroll processing completed
- `payment.failed`: Payment processing failed

### Webhook Payload

```json
{
  "event": "payroll.processed",
  "data": {
    "payroll_id": "PAY202312160001",
    "status": "processed",
    "total_employees": 10,
    "total_amount": 50000.00
  },
  "timestamp": "2023-12-16T10:00:00Z"
}
```

## SDK and Examples

### Python SDK

```python
from payroll_sdk import PayrollClient

client = PayrollClient(
    base_url="https://api.payrollsystem.com",
    api_key="your-api-key"
)

# Get employees
employees = client.employees.list(page=1, limit=10)

# Create employee
employee = client.employees.create({
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@company.com",
    "salary": 75000.00
})

# Process payroll
payroll = client.payroll.process({
    "pay_period_start": "2023-12-01",
    "pay_period_end": "2023-12-15"
})
```

### JavaScript SDK

```javascript
const PayrollClient = require('payroll-sdk');

const client = new PayrollClient({
  baseUrl: 'https://api.payrollsystem.com',
  apiKey: 'your-api-key'
});

// Get employees
const employees = await client.employees.list({ page: 1, limit: 10 });

// Create employee
const employee = await client.employees.create({
  first_name: 'John',
  last_name: 'Doe',
  email: 'john.doe@company.com',
  salary: 75000.00
});

// Process payroll
const payroll = await client.payroll.process({
  pay_period_start: '2023-12-01',
  pay_period_end: '2023-12-15'
});
``` 