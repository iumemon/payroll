"""
Pydantic schemas for the Payroll Management System.

This module imports all schemas for API request/response validation.
"""

from app.schemas.user import (
    UserBase,
    UserCreate,
    UserUpdate,
    UserResponse,
    UserLogin,
    UserLoginResponse,
    TokenRefresh,
    PasswordChange,
    PasswordReset,
    PasswordResetConfirm,
    UserList,
)

from app.schemas.employee import (
    EmployeeBase,
    EmployeeCreate,
    EmployeeUpdate,
    EmployeeResponse,
    EmployeeList,
    EmployeeSummary,
)

from app.schemas.payroll import (
    PayrollCalculationRequest,
    PayrollCalculationResponse,
    PayPeriodCreate,
    PayPeriodResponse,
    PayrollRecordCreate,
    PayrollRecordResponse,
    PayrollBatchRequest,
    PayrollBatchResponse,
    PayrollSummary,
)

from app.schemas.time_entry import (
    TimeEntryBase,
    TimeEntryCreate,
    TimeEntryUpdate,
    TimeEntryResponse,
    TimeEntryList,
    TimeEntrySummary,
    TimeEntryStats,
    ClockInRequest,
    ClockOutRequest,
    BreakRequest,
    TimeEntryApproval,
    EmployeeTimeReport,
)

from app.schemas.reports import (
    ReportRequest,
    ReportMetadata,
    ReportResponse,
    ReportListResponse,
    PayRegisterReport,
    TaxLiabilityReport,
    EmployeeRosterReport,
    SalaryAnalysisReport,
    ComplianceReport,
    TimeSummaryReport,
    PayRegisterEntry,
    EmployeeRosterEntry,
    ComplianceEntry,
    TimeSummaryEntry,
)

__all__ = [
    # User schemas
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserLogin",
    "UserLoginResponse",
    "TokenRefresh",
    "PasswordChange",
    "PasswordReset",
    "PasswordResetConfirm",
    "UserList",
    # Employee schemas
    "EmployeeBase",
    "EmployeeCreate",
    "EmployeeUpdate",
    "EmployeeResponse",
    "EmployeeList",
    "EmployeeSummary",
    # Payroll schemas
    "PayrollCalculationRequest",
    "PayrollCalculationResponse",
    "PayPeriodCreate",
    "PayPeriodResponse",
    "PayrollRecordCreate",
    "PayrollRecordResponse",
    "PayrollBatchRequest",
    "PayrollBatchResponse",
    "PayrollSummary",
    # Time Entry schemas
    "TimeEntryBase",
    "TimeEntryCreate",
    "TimeEntryUpdate",
    "TimeEntryResponse",
    "TimeEntryList",
    "TimeEntrySummary",
    "TimeEntryStats",
    "ClockInRequest",
    "ClockOutRequest",
    "BreakRequest",
    "TimeEntryApproval",
    "EmployeeTimeReport",
    # Report schemas
    "ReportRequest",
    "ReportMetadata",
    "ReportResponse",
    "ReportListResponse",
    "PayRegisterReport",
    "TaxLiabilityReport",
    "EmployeeRosterReport",
    "SalaryAnalysisReport",
    "ComplianceReport",
    "TimeSummaryReport",
    "PayRegisterEntry",
    "EmployeeRosterEntry",
    "ComplianceEntry",
    "TimeSummaryEntry",
] 