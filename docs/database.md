# Database Schema Documentation

## Overview

The Payroll Management System uses PostgreSQL as its primary database. This document describes the database schema, including tables, relationships, indexes, and constraints.

## Database Design Principles

- **Normalization**: Data is normalized to 3NF to reduce redundancy
- **Referential Integrity**: Foreign key constraints ensure data consistency
- **Audit Trail**: All tables include created_at and updated_at timestamps
- **Soft Deletes**: Important records are soft-deleted for audit purposes
- **Encryption**: Sensitive data is encrypted at the application level

## Entity Relationship Diagram

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Users       │    │   Employees     │    │   Departments   │
│─────────────────│    │─────────────────│    │─────────────────│
│ id (PK)         │    │ id (PK)         │    │ id (PK)         │
│ username        │    │ employee_id     │    │ name            │
│ email           │    │ user_id (FK)    │    │ description     │
│ password_hash   │    │ department_id   │    │ manager_id      │
│ role            │    │ first_name      │    │ budget          │
│ is_active       │    │ last_name       │    │ created_at      │
│ created_at      │    │ email           │    │ updated_at      │
│ updated_at      │    │ phone           │    └─────────────────┘
└─────────────────┘    │ hire_date       │            │
         │              │ termination_date│            │
         │              │ salary          │            │
         │              │ status          │            │
         │              │ created_at      │            │
         │              │ updated_at      │            │
         │              └─────────────────┘            │
         │                       │                     │
         └───────────────────────┘                     │
                                                       │
┌─────────────────┐    ┌─────────────────┐           │
│  Payroll_Runs   │    │  Payroll_Items  │           │
│─────────────────│    │─────────────────│           │
│ id (PK)         │    │ id (PK)         │           │
│ payroll_id      │    │ payroll_run_id  │           │
│ pay_period_start│    │ employee_id (FK)│           │
│ pay_period_end  │    │ gross_pay       │           │
│ payment_date    │    │ net_pay         │           │
│ status          │    │ federal_tax     │           │
│ total_gross     │    │ state_tax       │           │
│ total_net       │    │ social_security │           │
│ created_at      │    │ medicare        │           │
│ updated_at      │    │ other_deductions│           │
└─────────────────┘    │ created_at      │           │
         │              │ updated_at      │           │
         │              └─────────────────┘           │
         │                       │                    │
         └───────────────────────┘                    │
                                                      │
┌─────────────────┐    ┌─────────────────┐          │
│   Tax_Rates     │    │   Deductions    │          │
│─────────────────│    │─────────────────│          │
│ id (PK)         │    │ id (PK)         │          │
│ tax_type        │    │ employee_id (FK)│          │
│ rate            │    │ type            │          │
│ effective_date  │    │ amount          │          │
│ end_date        │    │ is_percentage   │          │
│ jurisdiction    │    │ is_active       │          │
│ created_at      │    │ effective_date  │          │
│ updated_at      │    │ end_date        │          │
└─────────────────┘    │ created_at      │          │
                       │ updated_at      │          │
                       └─────────────────┘          │
                                │                   │
                                └───────────────────┘
```

## Core Tables

### 1. Users Table

Stores user authentication and authorization information.

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'employee',
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_is_active ON users(is_active);

-- Check constraints
ALTER TABLE users ADD CONSTRAINT chk_users_role 
    CHECK (role IN ('admin', 'hr_manager', 'payroll_clerk', 'employee'));
```

### 2. Departments Table

Stores department information and hierarchy.

```sql
CREATE TABLE departments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    manager_id INTEGER REFERENCES users(id),
    parent_department_id INTEGER REFERENCES departments(id),
    budget DECIMAL(15,2),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_departments_name ON departments(name);
CREATE INDEX idx_departments_manager ON departments(manager_id);
CREATE INDEX idx_departments_parent ON departments(parent_department_id);
CREATE INDEX idx_departments_active ON departments(is_active);
```

### 3. Employees Table

Stores employee personal and employment information.

```sql
CREATE TABLE employees (
    id SERIAL PRIMARY KEY,
    employee_id VARCHAR(20) UNIQUE NOT NULL,
    user_id INTEGER REFERENCES users(id),
    department_id INTEGER REFERENCES departments(id),
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    middle_name VARCHAR(50),
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20),
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(50),
    zip_code VARCHAR(20),
    country VARCHAR(50) DEFAULT 'USA',
    ssn VARCHAR(255), -- Encrypted
    date_of_birth DATE,
    hire_date DATE NOT NULL,
    termination_date DATE,
    position VARCHAR(100),
    employment_type VARCHAR(20) DEFAULT 'full_time',
    salary DECIMAL(12,2) NOT NULL,
    hourly_rate DECIMAL(8,2),
    status VARCHAR(20) DEFAULT 'active',
    tax_exemptions INTEGER DEFAULT 0,
    filing_status VARCHAR(20) DEFAULT 'single',
    emergency_contact_name VARCHAR(100),
    emergency_contact_phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_employees_employee_id ON employees(employee_id);
CREATE INDEX idx_employees_user_id ON employees(user_id);
CREATE INDEX idx_employees_department ON employees(department_id);
CREATE INDEX idx_employees_status ON employees(status);
CREATE INDEX idx_employees_hire_date ON employees(hire_date);
CREATE INDEX idx_employees_name ON employees(last_name, first_name);

-- Check constraints
ALTER TABLE employees ADD CONSTRAINT chk_employees_status 
    CHECK (status IN ('active', 'inactive', 'terminated'));
ALTER TABLE employees ADD CONSTRAINT chk_employees_employment_type 
    CHECK (employment_type IN ('full_time', 'part_time', 'contract', 'intern'));
ALTER TABLE employees ADD CONSTRAINT chk_employees_filing_status 
    CHECK (filing_status IN ('single', 'married', 'head_of_household'));
ALTER TABLE employees ADD CONSTRAINT chk_employees_salary_positive 
    CHECK (salary > 0);
```

### 4. Bank Accounts Table

Stores employee banking information (encrypted).

```sql
CREATE TABLE bank_accounts (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER REFERENCES employees(id) ON DELETE CASCADE,
    account_type VARCHAR(20) DEFAULT 'checking',
    bank_name VARCHAR(100),
    routing_number VARCHAR(255), -- Encrypted
    account_number VARCHAR(255), -- Encrypted
    account_holder_name VARCHAR(100),
    is_primary BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_bank_accounts_employee ON bank_accounts(employee_id);
CREATE INDEX idx_bank_accounts_primary ON bank_accounts(is_primary);
CREATE INDEX idx_bank_accounts_active ON bank_accounts(is_active);

-- Check constraints
ALTER TABLE bank_accounts ADD CONSTRAINT chk_bank_accounts_type 
    CHECK (account_type IN ('checking', 'savings'));
```

### 5. Payroll Runs Table

Stores payroll processing runs.

```sql
CREATE TABLE payroll_runs (
    id SERIAL PRIMARY KEY,
    payroll_id VARCHAR(20) UNIQUE NOT NULL,
    pay_period_start DATE NOT NULL,
    pay_period_end DATE NOT NULL,
    payment_date DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'draft',
    total_employees INTEGER DEFAULT 0,
    total_gross DECIMAL(15,2) DEFAULT 0.00,
    total_deductions DECIMAL(15,2) DEFAULT 0.00,
    total_net DECIMAL(15,2) DEFAULT 0.00,
    processed_by INTEGER REFERENCES users(id),
    processed_at TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_payroll_runs_payroll_id ON payroll_runs(payroll_id);
CREATE INDEX idx_payroll_runs_period ON payroll_runs(pay_period_start, pay_period_end);
CREATE INDEX idx_payroll_runs_status ON payroll_runs(status);
CREATE INDEX idx_payroll_runs_payment_date ON payroll_runs(payment_date);

-- Check constraints
ALTER TABLE payroll_runs ADD CONSTRAINT chk_payroll_runs_status 
    CHECK (status IN ('draft', 'processing', 'processed', 'cancelled'));
ALTER TABLE payroll_runs ADD CONSTRAINT chk_payroll_runs_period 
    CHECK (pay_period_end >= pay_period_start);
```

### 6. Payroll Items Table

Stores individual employee payroll calculations.

```sql
CREATE TABLE payroll_items (
    id SERIAL PRIMARY KEY,
    payroll_run_id INTEGER REFERENCES payroll_runs(id) ON DELETE CASCADE,
    employee_id INTEGER REFERENCES employees(id),
    gross_pay DECIMAL(12,2) NOT NULL,
    regular_hours DECIMAL(8,2) DEFAULT 0.00,
    overtime_hours DECIMAL(8,2) DEFAULT 0.00,
    regular_rate DECIMAL(8,2) DEFAULT 0.00,
    overtime_rate DECIMAL(8,2) DEFAULT 0.00,
    bonus DECIMAL(12,2) DEFAULT 0.00,
    commission DECIMAL(12,2) DEFAULT 0.00,
    federal_tax DECIMAL(12,2) DEFAULT 0.00,
    state_tax DECIMAL(12,2) DEFAULT 0.00,
    social_security DECIMAL(12,2) DEFAULT 0.00,
    medicare DECIMAL(12,2) DEFAULT 0.00,
    unemployment_tax DECIMAL(12,2) DEFAULT 0.00,
    health_insurance DECIMAL(12,2) DEFAULT 0.00,
    dental_insurance DECIMAL(12,2) DEFAULT 0.00,
    vision_insurance DECIMAL(12,2) DEFAULT 0.00,
    retirement_401k DECIMAL(12,2) DEFAULT 0.00,
    other_deductions DECIMAL(12,2) DEFAULT 0.00,
    net_pay DECIMAL(12,2) NOT NULL,
    payment_method VARCHAR(20) DEFAULT 'direct_deposit',
    payment_status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_payroll_items_run ON payroll_items(payroll_run_id);
CREATE INDEX idx_payroll_items_employee ON payroll_items(employee_id);
CREATE INDEX idx_payroll_items_payment_status ON payroll_items(payment_status);
CREATE UNIQUE INDEX idx_payroll_items_unique ON payroll_items(payroll_run_id, employee_id);

-- Check constraints
ALTER TABLE payroll_items ADD CONSTRAINT chk_payroll_items_payment_method 
    CHECK (payment_method IN ('direct_deposit', 'check', 'cash'));
ALTER TABLE payroll_items ADD CONSTRAINT chk_payroll_items_payment_status 
    CHECK (payment_status IN ('pending', 'processed', 'failed', 'cancelled'));
```

### 7. Tax Rates Table

Stores tax rates for different jurisdictions and time periods.

```sql
CREATE TABLE tax_rates (
    id SERIAL PRIMARY KEY,
    tax_type VARCHAR(50) NOT NULL,
    rate DECIMAL(8,6) NOT NULL,
    effective_date DATE NOT NULL,
    end_date DATE,
    jurisdiction VARCHAR(50) DEFAULT 'federal',
    income_min DECIMAL(12,2) DEFAULT 0.00,
    income_max DECIMAL(12,2),
    filing_status VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_tax_rates_type ON tax_rates(tax_type);
CREATE INDEX idx_tax_rates_effective_date ON tax_rates(effective_date);
CREATE INDEX idx_tax_rates_jurisdiction ON tax_rates(jurisdiction);
CREATE INDEX idx_tax_rates_active ON tax_rates(is_active);

-- Check constraints
ALTER TABLE tax_rates ADD CONSTRAINT chk_tax_rates_type 
    CHECK (tax_type IN ('federal_income', 'state_income', 'social_security', 'medicare', 'unemployment'));
ALTER TABLE tax_rates ADD CONSTRAINT chk_tax_rates_filing_status 
    CHECK (filing_status IN ('single', 'married', 'head_of_household', 'all'));
ALTER TABLE tax_rates ADD CONSTRAINT chk_tax_rates_rate_positive 
    CHECK (rate >= 0);
```

### 8. Deductions Table

Stores employee-specific deductions.

```sql
CREATE TABLE deductions (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER REFERENCES employees(id) ON DELETE CASCADE,
    deduction_type VARCHAR(50) NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    is_percentage BOOLEAN DEFAULT FALSE,
    is_pre_tax BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    effective_date DATE NOT NULL,
    end_date DATE,
    frequency VARCHAR(20) DEFAULT 'monthly',
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_deductions_employee ON deductions(employee_id);
CREATE INDEX idx_deductions_type ON deductions(deduction_type);
CREATE INDEX idx_deductions_active ON deductions(is_active);
CREATE INDEX idx_deductions_effective_date ON deductions(effective_date);

-- Check constraints
ALTER TABLE deductions ADD CONSTRAINT chk_deductions_type 
    CHECK (deduction_type IN ('health_insurance', 'dental_insurance', 'vision_insurance', 
                              'retirement_401k', 'life_insurance', 'parking', 'other'));
ALTER TABLE deductions ADD CONSTRAINT chk_deductions_frequency 
    CHECK (frequency IN ('weekly', 'bi_weekly', 'monthly', 'quarterly', 'annually'));
ALTER TABLE deductions ADD CONSTRAINT chk_deductions_amount_positive 
    CHECK (amount > 0);
```

### 9. Time Entries Table

Stores employee time tracking information.

```sql
CREATE TABLE time_entries (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER REFERENCES employees(id) ON DELETE CASCADE,
    work_date DATE NOT NULL,
    clock_in TIMESTAMP,
    clock_out TIMESTAMP,
    break_duration INTEGER DEFAULT 0, -- minutes
    regular_hours DECIMAL(8,2) DEFAULT 0.00,
    overtime_hours DECIMAL(8,2) DEFAULT 0.00,
    total_hours DECIMAL(8,2) DEFAULT 0.00,
    status VARCHAR(20) DEFAULT 'draft',
    approved_by INTEGER REFERENCES users(id),
    approved_at TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_time_entries_employee ON time_entries(employee_id);
CREATE INDEX idx_time_entries_work_date ON time_entries(work_date);
CREATE INDEX idx_time_entries_status ON time_entries(status);
CREATE UNIQUE INDEX idx_time_entries_unique ON time_entries(employee_id, work_date);

-- Check constraints
ALTER TABLE time_entries ADD CONSTRAINT chk_time_entries_status 
    CHECK (status IN ('draft', 'submitted', 'approved', 'rejected'));
ALTER TABLE time_entries ADD CONSTRAINT chk_time_entries_hours_positive 
    CHECK (total_hours >= 0);
```

### 10. Audit Log Table

Stores audit trail for all system actions.

```sql
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(50) NOT NULL,
    table_name VARCHAR(50) NOT NULL,
    record_id INTEGER,
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_audit_log_user ON audit_log(user_id);
CREATE INDEX idx_audit_log_action ON audit_log(action);
CREATE INDEX idx_audit_log_table ON audit_log(table_name);
CREATE INDEX idx_audit_log_timestamp ON audit_log(timestamp);
CREATE INDEX idx_audit_log_record ON audit_log(table_name, record_id);
```

## Views

### 1. Employee Summary View

```sql
CREATE VIEW employee_summary AS
SELECT 
    e.id,
    e.employee_id,
    e.first_name,
    e.last_name,
    e.email,
    e.position,
    e.hire_date,
    e.salary,
    e.status,
    d.name AS department_name,
    u.username,
    u.role
FROM employees e
LEFT JOIN departments d ON e.department_id = d.id
LEFT JOIN users u ON e.user_id = u.id;
```

### 2. Current Payroll View

```sql
CREATE VIEW current_payroll AS
SELECT 
    pr.id AS payroll_run_id,
    pr.payroll_id,
    pr.pay_period_start,
    pr.pay_period_end,
    pr.payment_date,
    pr.status,
    e.employee_id,
    e.first_name,
    e.last_name,
    pi.gross_pay,
    pi.net_pay,
    pi.federal_tax,
    pi.state_tax,
    pi.social_security,
    pi.medicare
FROM payroll_runs pr
JOIN payroll_items pi ON pr.id = pi.payroll_run_id
JOIN employees e ON pi.employee_id = e.id
WHERE pr.status = 'processed';
```

### 3. Tax Summary View

```sql
CREATE VIEW tax_summary AS
SELECT 
    DATE_TRUNC('month', pr.payment_date) AS month,
    SUM(pi.gross_pay) AS total_gross,
    SUM(pi.federal_tax) AS total_federal_tax,
    SUM(pi.state_tax) AS total_state_tax,
    SUM(pi.social_security) AS total_social_security,
    SUM(pi.medicare) AS total_medicare,
    COUNT(DISTINCT pi.employee_id) AS employee_count
FROM payroll_runs pr
JOIN payroll_items pi ON pr.id = pi.payroll_run_id
WHERE pr.status = 'processed'
GROUP BY DATE_TRUNC('month', pr.payment_date);
```

## Functions and Procedures

### 1. Calculate Payroll Function

```sql
CREATE OR REPLACE FUNCTION calculate_payroll(
    p_employee_id INTEGER,
    p_pay_period_start DATE,
    p_pay_period_end DATE
) RETURNS TABLE (
    gross_pay DECIMAL(12,2),
    federal_tax DECIMAL(12,2),
    state_tax DECIMAL(12,2),
    social_security DECIMAL(12,2),
    medicare DECIMAL(12,2),
    net_pay DECIMAL(12,2)
) AS $$
DECLARE
    v_salary DECIMAL(12,2);
    v_tax_exemptions INTEGER;
    v_filing_status VARCHAR(20);
BEGIN
    -- Get employee information
    SELECT salary, tax_exemptions, filing_status
    INTO v_salary, v_tax_exemptions, v_filing_status
    FROM employees
    WHERE id = p_employee_id;
    
    -- Calculate gross pay (simplified - actual implementation would be more complex)
    gross_pay := v_salary / 12; -- Monthly salary
    
    -- Calculate taxes (simplified - actual implementation would use tax tables)
    federal_tax := gross_pay * 0.22;
    state_tax := gross_pay * 0.05;
    social_security := gross_pay * 0.062;
    medicare := gross_pay * 0.0145;
    
    -- Calculate net pay
    net_pay := gross_pay - federal_tax - state_tax - social_security - medicare;
    
    RETURN NEXT;
END;
$$ LANGUAGE plpgsql;
```

### 2. Update Timestamp Trigger

```sql
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to all tables
CREATE TRIGGER update_users_timestamp
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER update_employees_timestamp
    BEFORE UPDATE ON employees
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

-- ... apply to other tables
```

## Indexes and Performance

### Performance Indexes

```sql
-- Composite indexes for common queries
CREATE INDEX idx_employees_dept_status ON employees(department_id, status);
CREATE INDEX idx_payroll_items_employee_date ON payroll_items(employee_id, payroll_run_id);
CREATE INDEX idx_time_entries_employee_date ON time_entries(employee_id, work_date);

-- Partial indexes for active records
CREATE INDEX idx_employees_active ON employees(id) WHERE status = 'active';
CREATE INDEX idx_deductions_active ON deductions(employee_id) WHERE is_active = true;

-- Full-text search index
CREATE INDEX idx_employees_search ON employees USING gin(to_tsvector('english', first_name || ' ' || last_name));
```

### Query Optimization

```sql
-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM employees WHERE department_id = 1;

-- Update table statistics
ANALYZE employees;
ANALYZE payroll_items;
```

## Data Migration Scripts

### Initial Data Setup

```sql
-- Insert default tax rates
INSERT INTO tax_rates (tax_type, rate, effective_date, jurisdiction) VALUES
('federal_income', 0.22, '2023-01-01', 'federal'),
('state_income', 0.05, '2023-01-01', 'state'),
('social_security', 0.062, '2023-01-01', 'federal'),
('medicare', 0.0145, '2023-01-01', 'federal');

-- Insert default departments
INSERT INTO departments (name, description) VALUES
('Human Resources', 'Human Resources Department'),
('Engineering', 'Software Engineering Department'),
('Finance', 'Finance and Accounting Department'),
('Marketing', 'Marketing and Sales Department');

-- Insert admin user
INSERT INTO users (username, email, password_hash, role) VALUES
('admin', 'admin@company.com', '$2b$12$...', 'admin');
```

## Backup and Maintenance

### Backup Strategy

```sql
-- Full backup
pg_dump -h localhost -U postgres -d payroll > payroll_backup.sql

-- Schema-only backup
pg_dump -h localhost -U postgres -d payroll -s > payroll_schema.sql

-- Data-only backup
pg_dump -h localhost -U postgres -d payroll -a > payroll_data.sql

-- Specific table backup
pg_dump -h localhost -U postgres -d payroll -t employees > employees_backup.sql
```

### Maintenance Tasks

```sql
-- Update table statistics
ANALYZE;

-- Reindex tables
REINDEX DATABASE payroll;

-- Vacuum tables
VACUUM ANALYZE employees;
VACUUM ANALYZE payroll_items;

-- Check for unused indexes
SELECT schemaname, tablename, attname, n_distinct, correlation
FROM pg_stats
WHERE schemaname = 'public'
ORDER BY n_distinct DESC;
```

## Security Considerations

### Row-Level Security

```sql
-- Enable RLS on sensitive tables
ALTER TABLE employees ENABLE ROW LEVEL SECURITY;
ALTER TABLE payroll_items ENABLE ROW LEVEL SECURITY;

-- Create policies
CREATE POLICY employee_policy ON employees
    FOR ALL TO app_user
    USING (user_id = current_user_id());

CREATE POLICY payroll_policy ON payroll_items
    FOR ALL TO app_user
    USING (employee_id IN (SELECT id FROM employees WHERE user_id = current_user_id()));
```

### Data Encryption

```sql
-- Encrypt sensitive columns
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Encrypt SSN
UPDATE employees SET ssn = pgp_sym_encrypt(ssn, 'encryption_key');

-- Decrypt SSN
SELECT pgp_sym_decrypt(ssn::bytea, 'encryption_key') FROM employees;
```

## Troubleshooting

### Common Issues

1. **Slow Queries**: Use EXPLAIN ANALYZE to identify bottlenecks
2. **Lock Contention**: Monitor pg_locks table
3. **Disk Space**: Monitor table and index sizes
4. **Connection Limits**: Monitor active connections

### Useful Queries

```sql
-- Check table sizes
SELECT 
    table_name,
    pg_size_pretty(pg_total_relation_size(table_name::regclass)) as size
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY pg_total_relation_size(table_name::regclass) DESC;

-- Check slow queries
SELECT query, mean_time, calls
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- Check active connections
SELECT * FROM pg_stat_activity WHERE state = 'active';
```

This database schema provides a solid foundation for the payroll management system with proper normalization, indexing, and security considerations. 