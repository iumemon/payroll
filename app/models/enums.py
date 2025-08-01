"""
Enumerations for the Payroll Management System.

This module defines all enum types used across the application
for consistent data validation and type safety.
"""

from enum import Enum


class UserRole(str, Enum):
    """User roles for role-based access control."""
    
    USER = "user"
    EMPLOYEE = "employee"
    MANAGER = "manager"
    HR = "hr"
    PAYROLL_ADMIN = "payroll_admin"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class UserStatus(str, Enum):
    """User account status."""
    
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"
    LOCKED = "locked"


class EmployeeStatus(str, Enum):
    """Employee employment status."""
    
    ACTIVE = "active"
    INACTIVE = "inactive"
    TERMINATED = "terminated"
    ON_LEAVE = "on_leave"
    SUSPENDED = "suspended"
    PROBATION = "probation"


class EmploymentType(str, Enum):
    """Employee employment type."""
    
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    TEMPORARY = "temporary"
    INTERN = "intern"
    CONSULTANT = "consultant"


class PayrollStatus(str, Enum):
    """Payroll run status."""
    
    DRAFT = "draft"
    CALCULATING = "calculating"
    REVIEW = "review"
    APPROVED = "approved"
    PROCESSED = "processed"
    PAID = "paid"
    CANCELLED = "cancelled"
    ERROR = "error"


class PayrollFrequency(str, Enum):
    """Payroll payment frequency."""
    
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    SEMI_MONTHLY = "semi_monthly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUALLY = "annually"


class PayrollType(str, Enum):
    """Payroll type."""
    
    REGULAR = "regular"
    BONUS = "bonus"
    COMMISSION = "commission"
    OVERTIME = "overtime"
    ADJUSTMENT = "adjustment"
    FINAL = "final"


class BenefitType(str, Enum):
    """Employee benefit types."""
    
    HEALTH_INSURANCE = "health_insurance"
    DENTAL_INSURANCE = "dental_insurance"
    VISION_INSURANCE = "vision_insurance"
    LIFE_INSURANCE = "life_insurance"
    DISABILITY_INSURANCE = "disability_insurance"
    RETIREMENT_401K = "retirement_401k"
    PAID_TIME_OFF = "paid_time_off"
    SICK_LEAVE = "sick_leave"
    MATERNITY_LEAVE = "maternity_leave"
    PATERNITY_LEAVE = "paternity_leave"
    FLEXIBLE_SPENDING = "flexible_spending"
    COMMUTER_BENEFITS = "commuter_benefits"
    WELLNESS_PROGRAM = "wellness_program"
    EDUCATION_ASSISTANCE = "education_assistance"
    OTHER = "other"


class DeductionType(str, Enum):
    """Payroll deduction types."""
    
    # Taxes
    FEDERAL_INCOME_TAX = "federal_income_tax"
    STATE_INCOME_TAX = "state_income_tax"
    LOCAL_INCOME_TAX = "local_income_tax"
    SOCIAL_SECURITY = "social_security"
    MEDICARE = "medicare"
    
    # Benefits
    HEALTH_INSURANCE = "health_insurance"
    DENTAL_INSURANCE = "dental_insurance"
    VISION_INSURANCE = "vision_insurance"
    LIFE_INSURANCE = "life_insurance"
    DISABILITY_INSURANCE = "disability_insurance"
    RETIREMENT_401K = "retirement_401k"
    
    # Other
    UNION_DUES = "union_dues"
    GARNISHMENT = "garnishment"
    CHILD_SUPPORT = "child_support"
    LOAN_REPAYMENT = "loan_repayment"
    PARKING = "parking"
    MEAL_PLAN = "meal_plan"
    OTHER = "other"


class EarningType(str, Enum):
    """Payroll earning types."""
    
    REGULAR_SALARY = "regular_salary"
    HOURLY_WAGES = "hourly_wages"
    OVERTIME = "overtime"
    DOUBLE_TIME = "double_time"
    BONUS = "bonus"
    COMMISSION = "commission"
    TIPS = "tips"
    HOLIDAY_PAY = "holiday_pay"
    SICK_PAY = "sick_pay"
    VACATION_PAY = "vacation_pay"
    SEVERANCE = "severance"
    BACK_PAY = "back_pay"
    ALLOWANCE = "allowance"
    REIMBURSEMENT = "reimbursement"
    OTHER = "other"


class TaxType(str, Enum):
    """Tax types."""
    
    FEDERAL_INCOME = "federal_income"
    STATE_INCOME = "state_income"
    LOCAL_INCOME = "local_income"
    SOCIAL_SECURITY = "social_security"
    MEDICARE = "medicare"
    UNEMPLOYMENT = "unemployment"
    DISABILITY = "disability"
    WORKERS_COMP = "workers_comp"
    OTHER = "other"


class ReportType(str, Enum):
    """Report types."""
    
    PAYROLL_SUMMARY = "payroll_summary"
    EMPLOYEE_EARNINGS = "employee_earnings"
    TAX_SUMMARY = "tax_summary"
    BENEFIT_SUMMARY = "benefit_summary"
    DEDUCTION_SUMMARY = "deduction_summary"
    QUARTERLY_REPORT = "quarterly_report"
    ANNUAL_REPORT = "annual_report"
    AUDIT_REPORT = "audit_report"
    CUSTOM = "custom"


class AuditAction(str, Enum):
    """Audit log actions."""
    
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    EXPORT = "export"
    IMPORT = "import"
    APPROVE = "approve"
    REJECT = "reject"
    PROCESS = "process"
    CANCEL = "cancel"
    OTHER = "other"


class LeaveType(str, Enum):
    """Employee leave types."""
    
    VACATION = "vacation"
    SICK = "sick"
    PERSONAL = "personal"
    MATERNITY = "maternity"
    PATERNITY = "paternity"
    BEREAVEMENT = "bereavement"
    JURY_DUTY = "jury_duty"
    MILITARY = "military"
    UNPAID = "unpaid"
    FMLA = "fmla"
    OTHER = "other"


class LeaveStatus(str, Enum):
    """Leave request status."""
    
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class TimesheetStatus(str, Enum):
    """Timesheet status."""
    
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    PROCESSED = "processed"


class TimeEntryStatus(str, Enum):
    """Time entry status."""
    
    DRAFT = "draft"
    CLOCKED_IN = "clocked_in"
    CLOCKED_OUT = "clocked_out"
    ON_BREAK = "on_break"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    PROCESSED = "processed"


class TimeEntryType(str, Enum):
    """Time entry types."""
    
    REGULAR = "regular"
    OVERTIME = "overtime"
    DOUBLE_TIME = "double_time"
    HOLIDAY = "holiday"
    SICK = "sick"
    VACATION = "vacation"
    BREAK = "break"
    LUNCH = "lunch"
    TRAINING = "training"
    MEETING = "meeting"
    TRAVEL = "travel"
    OTHER = "other"


class ApprovalStatus(str, Enum):
    """General approval status."""
    
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class ReportType(str, Enum):
    """Report types."""
    
    # Payroll Reports
    PAY_REGISTER = "pay_register"
    TAX_LIABILITY = "tax_liability"
    DEPARTMENT_SUMMARY = "department_summary"
    PAYROLL_SUMMARY = "payroll_summary"
    
    # Employee Reports
    EMPLOYEE_ROSTER = "employee_roster"
    SALARY_ANALYSIS = "salary_analysis"
    BENEFIT_ENROLLMENT = "benefit_enrollment"
    EMPLOYEE_SUMMARY = "employee_summary"
    
    # Compliance Reports
    I9_COMPLIANCE = "i9_compliance"
    W4_STATUS = "w4_status"
    BACKGROUND_CHECK = "background_check"
    COMPLIANCE_SUMMARY = "compliance_summary"
    
    # Time Tracking Reports
    TIME_SUMMARY = "time_summary"
    ATTENDANCE_REPORT = "attendance_report"
    OVERTIME_REPORT = "overtime_report"
    
    # Custom Reports
    CUSTOM = "custom"


class ReportFormat(str, Enum):
    """Report export formats."""
    
    JSON = "json"
    CSV = "csv"
    PDF = "pdf"
    EXCEL = "excel"
    HTML = "html"


class ReportPeriod(str, Enum):
    """Report time periods."""
    
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CUSTOM = "custom"


class ReportStatus(str, Enum):
    """Report generation status."""
    
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired" 