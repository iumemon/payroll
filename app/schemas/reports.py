"""
Report schemas for API request/response validation.

This module defines Pydantic schemas for various reporting operations
including payroll reports, employee reports, and compliance reports.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict, field_validator

from app.models.enums import (
    ReportType, ReportFormat, ReportPeriod, ReportStatus, 
    EmployeeStatus, PayrollStatus, EmploymentType
)


class ReportFilterBase(BaseModel):
    """Base schema for report filters."""
    
    start_date: Optional[date] = Field(None, description="Filter start date")
    end_date: Optional[date] = Field(None, description="Filter end date")
    department: Optional[str] = Field(None, description="Filter by department")
    location: Optional[str] = Field(None, description="Filter by location")
    
    @field_validator("end_date")
    @classmethod
    def validate_date_range(cls, v, info):
        """Validate that end date is after start date."""
        if v is not None and "start_date" in info.data:
            start_date = info.data["start_date"]
            if start_date is not None and v < start_date:
                raise ValueError("End date must be after start date")
        return v


class ReportRequest(BaseModel):
    """Base schema for report generation requests."""
    
    report_type: ReportType = Field(..., description="Type of report to generate")
    report_format: ReportFormat = Field(ReportFormat.JSON, description="Output format")
    report_period: ReportPeriod = Field(ReportPeriod.MONTHLY, description="Report period")
    
    # Date range (required for custom period)
    start_date: Optional[date] = Field(None, description="Custom start date")
    end_date: Optional[date] = Field(None, description="Custom end date")
    
    # Filters
    employee_ids: Optional[List[int]] = Field(None, description="Filter by employee IDs")
    department: Optional[str] = Field(None, description="Filter by department")
    location: Optional[str] = Field(None, description="Filter by location")
    status_filter: Optional[str] = Field(None, description="Filter by status")
    
    # Report options
    include_terminated: bool = Field(False, description="Include terminated employees")
    include_detailed_breakdown: bool = Field(True, description="Include detailed breakdown")
    group_by: Optional[str] = Field(None, description="Group results by field")
    sort_by: Optional[str] = Field(None, description="Sort results by field")
    
    @field_validator("end_date")
    @classmethod
    def validate_custom_dates(cls, v, info):
        """Validate custom date range."""
        if "report_period" in info.data and info.data["report_period"] == ReportPeriod.CUSTOM:
            if "start_date" not in info.data or info.data["start_date"] is None:
                raise ValueError("Start date is required for custom period")
            if v is None:
                raise ValueError("End date is required for custom period")
            if v < info.data["start_date"]:
                raise ValueError("End date must be after start date")
        return v
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "report_type": "employee_roster",
                "report_format": "json",
                "report_period": "monthly",
                "department": "Engineering",
                "include_terminated": False,
                "include_detailed_breakdown": True
            }
        }
    )


class ReportMetadata(BaseModel):
    """Schema for report metadata."""
    
    report_id: str = Field(..., description="Unique report identifier")
    report_type: ReportType = Field(..., description="Type of report")
    report_format: ReportFormat = Field(..., description="Report format")
    status: ReportStatus = Field(..., description="Report generation status")
    
    # Date information
    generated_at: datetime = Field(..., description="Report generation timestamp")
    report_period_start: Optional[date] = Field(None, description="Report period start")
    report_period_end: Optional[date] = Field(None, description="Report period end")
    
    # Metadata
    total_records: int = Field(..., description="Total number of records")
    generated_by: int = Field(..., description="User ID who generated report")
    filters_applied: Dict[str, Any] = Field(..., description="Filters applied to report")
    
    # File information (if exported)
    file_size: Optional[int] = Field(None, description="File size in bytes")
    download_url: Optional[str] = Field(None, description="Download URL")
    expires_at: Optional[datetime] = Field(None, description="Download expiration")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "report_id": "rpt_20240107_001",
                "report_type": "employee_roster",
                "report_format": "json",
                "status": "completed",
                "generated_at": "2024-01-07T10:30:00Z",
                "total_records": 25,
                "generated_by": 1,
                "filters_applied": {"department": "Engineering"}
            }
        }
    )


# Payroll Report Schemas

class PayrollReportFilter(ReportFilterBase):
    """Filters for payroll reports."""
    
    pay_period_ids: Optional[List[int]] = Field(None, description="Filter by pay period IDs")
    employee_ids: Optional[List[int]] = Field(None, description="Filter by employee IDs")
    min_gross_pay: Optional[Decimal] = Field(None, description="Minimum gross pay filter")
    max_gross_pay: Optional[Decimal] = Field(None, description="Maximum gross pay filter")
    payroll_status: Optional[PayrollStatus] = Field(None, description="Filter by payroll status")


class PayRegisterEntry(BaseModel):
    """Schema for pay register entry."""
    
    employee_id: int = Field(..., description="Employee ID")
    employee_name: str = Field(..., description="Employee name")
    employee_number: str = Field(..., description="Employee number")
    department: Optional[str] = Field(None, description="Department")
    position: Optional[str] = Field(None, description="Position")
    
    # Pay information
    pay_period_start: date = Field(..., description="Pay period start")
    pay_period_end: date = Field(..., description="Pay period end")
    hours_worked: Decimal = Field(..., description="Hours worked")
    overtime_hours: Decimal = Field(..., description="Overtime hours")
    
    # Earnings
    gross_pay: Decimal = Field(..., description="Gross pay")
    regular_pay: Decimal = Field(..., description="Regular pay")
    overtime_pay: Decimal = Field(..., description="Overtime pay")
    
    # Deductions
    federal_tax: Decimal = Field(..., description="Federal income tax")
    state_tax: Decimal = Field(..., description="State income tax")
    social_security: Decimal = Field(..., description="Social Security tax")
    medicare: Decimal = Field(..., description="Medicare tax")
    benefit_deductions: Decimal = Field(..., description="Benefit deductions")
    other_deductions: Decimal = Field(..., description="Other deductions")
    total_deductions: Decimal = Field(..., description="Total deductions")
    
    # Net pay
    net_pay: Decimal = Field(..., description="Net pay")
    
    model_config = ConfigDict(from_attributes=True)


class PayRegisterReport(BaseModel):
    """Schema for pay register report."""
    
    metadata: ReportMetadata = Field(..., description="Report metadata")
    summary: Dict[str, Any] = Field(..., description="Report summary")
    entries: List[PayRegisterEntry] = Field(..., description="Pay register entries")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "metadata": {
                    "report_id": "rpt_payregister_001",
                    "report_type": "pay_register",
                    "total_records": 25
                },
                "summary": {
                    "total_employees": 25,
                    "total_gross_pay": 125000.00,
                    "total_net_pay": 95000.00
                },
                "entries": []
            }
        }
    )


class TaxLiabilitySummary(BaseModel):
    """Schema for tax liability summary."""
    
    period_start: date = Field(..., description="Period start date")
    period_end: date = Field(..., description="Period end date")
    
    # Federal taxes
    federal_income_tax: Decimal = Field(..., description="Federal income tax withheld")
    social_security_employee: Decimal = Field(..., description="Employee Social Security")
    social_security_employer: Decimal = Field(..., description="Employer Social Security")
    medicare_employee: Decimal = Field(..., description="Employee Medicare")
    medicare_employer: Decimal = Field(..., description="Employer Medicare")
    
    # State taxes
    state_income_tax: Decimal = Field(..., description="State income tax withheld")
    state_unemployment: Decimal = Field(..., description="State unemployment tax")
    
    # Totals
    total_employee_taxes: Decimal = Field(..., description="Total employee taxes")
    total_employer_taxes: Decimal = Field(..., description="Total employer taxes")
    total_tax_liability: Decimal = Field(..., description="Total tax liability")
    
    # Payroll totals
    total_wages: Decimal = Field(..., description="Total wages subject to tax")
    total_employees: int = Field(..., description="Number of employees")


class TaxLiabilityReport(BaseModel):
    """Schema for tax liability report."""
    
    metadata: ReportMetadata = Field(..., description="Report metadata")
    summary: TaxLiabilitySummary = Field(..., description="Tax liability summary")
    by_department: Optional[List[Dict[str, Any]]] = Field(None, description="Department breakdown")
    by_employee: Optional[List[Dict[str, Any]]] = Field(None, description="Employee breakdown")


# Employee Report Schemas

class EmployeeReportFilter(ReportFilterBase):
    """Filters for employee reports."""
    
    employee_status: Optional[EmployeeStatus] = Field(None, description="Filter by employee status")
    employment_type: Optional[EmploymentType] = Field(None, description="Filter by employment type")
    hire_date_start: Optional[date] = Field(None, description="Hire date range start")
    hire_date_end: Optional[date] = Field(None, description="Hire date range end")
    position: Optional[str] = Field(None, description="Filter by position")
    manager_id: Optional[int] = Field(None, description="Filter by manager")


class EmployeeRosterEntry(BaseModel):
    """Schema for employee roster entry."""
    
    employee_id: int = Field(..., description="Employee ID")
    employee_number: str = Field(..., description="Employee number")
    full_name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    
    # Employment details
    status: EmployeeStatus = Field(..., description="Employment status")
    employment_type: EmploymentType = Field(..., description="Employment type")
    position: str = Field(..., description="Position")
    department: Optional[str] = Field(None, description="Department")
    location: Optional[str] = Field(None, description="Location")
    
    # Dates
    hire_date: date = Field(..., description="Hire date")
    termination_date: Optional[date] = Field(None, description="Termination date")
    
    # Manager information
    manager_name: Optional[str] = Field(None, description="Manager name")
    
    # Compensation
    salary: Optional[Decimal] = Field(None, description="Annual salary")
    hourly_rate: Optional[Decimal] = Field(None, description="Hourly rate")
    
    model_config = ConfigDict(from_attributes=True)


class EmployeeRosterReport(BaseModel):
    """Schema for employee roster report."""
    
    metadata: ReportMetadata = Field(..., description="Report metadata")
    summary: Dict[str, Any] = Field(..., description="Report summary")
    employees: List[EmployeeRosterEntry] = Field(..., description="Employee roster entries")


class SalaryAnalysisEntry(BaseModel):
    """Schema for salary analysis entry."""
    
    department: str = Field(..., description="Department")
    position: str = Field(..., description="Position")
    employee_count: int = Field(..., description="Number of employees")
    
    # Salary statistics
    min_salary: Decimal = Field(..., description="Minimum salary")
    max_salary: Decimal = Field(..., description="Maximum salary")
    avg_salary: Decimal = Field(..., description="Average salary")
    median_salary: Decimal = Field(..., description="Median salary")
    total_salary_cost: Decimal = Field(..., description="Total salary cost")
    
    # Additional statistics
    salary_range: Decimal = Field(..., description="Salary range (max - min)")
    std_deviation: Optional[Decimal] = Field(None, description="Standard deviation")


class SalaryAnalysisReport(BaseModel):
    """Schema for salary analysis report."""
    
    metadata: ReportMetadata = Field(..., description="Report metadata")
    summary: Dict[str, Any] = Field(..., description="Overall summary")
    by_department: List[SalaryAnalysisEntry] = Field(..., description="Analysis by department")
    by_position: List[SalaryAnalysisEntry] = Field(..., description="Analysis by position")


# Compliance Report Schemas

class ComplianceReportFilter(ReportFilterBase):
    """Filters for compliance reports."""
    
    compliance_type: Optional[str] = Field(None, description="Type of compliance check")
    status: Optional[str] = Field(None, description="Compliance status")
    due_date_start: Optional[date] = Field(None, description="Due date range start")
    due_date_end: Optional[date] = Field(None, description="Due date range end")


class ComplianceEntry(BaseModel):
    """Schema for compliance entry."""
    
    employee_id: int = Field(..., description="Employee ID")
    employee_name: str = Field(..., description="Employee name")
    employee_number: str = Field(..., description="Employee number")
    department: Optional[str] = Field(None, description="Department")
    position: str = Field(..., description="Position")
    hire_date: date = Field(..., description="Hire date")
    
    # Compliance status
    i9_completed: bool = Field(..., description="I-9 form completed")
    w4_completed: bool = Field(..., description="W-4 form completed")
    background_check_completed: bool = Field(..., description="Background check completed")
    
    # Additional compliance fields
    compliance_score: Optional[int] = Field(None, description="Overall compliance score")
    missing_documents: List[str] = Field(default_factory=list, description="Missing documents")
    compliance_notes: Optional[str] = Field(None, description="Compliance notes")
    
    model_config = ConfigDict(from_attributes=True)


class ComplianceReport(BaseModel):
    """Schema for compliance report."""
    
    metadata: ReportMetadata = Field(..., description="Report metadata")
    summary: Dict[str, Any] = Field(..., description="Compliance summary")
    entries: List[ComplianceEntry] = Field(..., description="Compliance entries")


# Time Tracking Report Schemas

class TimeTrackingReportFilter(ReportFilterBase):
    """Filters for time tracking reports."""
    
    employee_ids: Optional[List[int]] = Field(None, description="Filter by employee IDs")
    approval_status: Optional[str] = Field(None, description="Filter by approval status")
    entry_type: Optional[str] = Field(None, description="Filter by entry type")
    min_hours: Optional[Decimal] = Field(None, description="Minimum hours filter")
    max_hours: Optional[Decimal] = Field(None, description="Maximum hours filter")


class TimeSummaryEntry(BaseModel):
    """Schema for time summary entry."""
    
    employee_id: int = Field(..., description="Employee ID")
    employee_name: str = Field(..., description="Employee name")
    department: Optional[str] = Field(None, description="Department")
    
    # Time totals
    total_hours: Decimal = Field(..., description="Total hours worked")
    regular_hours: Decimal = Field(..., description="Regular hours worked")
    overtime_hours: Decimal = Field(..., description="Overtime hours worked")
    days_worked: int = Field(..., description="Number of days worked")
    
    # Averages
    avg_hours_per_day: Decimal = Field(..., description="Average hours per day")
    
    model_config = ConfigDict(from_attributes=True)


class TimeSummaryReport(BaseModel):
    """Schema for time summary report."""
    
    metadata: ReportMetadata = Field(..., description="Report metadata")
    summary: Dict[str, Any] = Field(..., description="Time summary")
    entries: List[TimeSummaryEntry] = Field(..., description="Time summary entries")


# Generic Report Response

class ReportResponse(BaseModel):
    """Generic schema for report responses."""
    
    metadata: ReportMetadata = Field(..., description="Report metadata")
    data: Union[
        PayRegisterReport,
        TaxLiabilityReport,
        EmployeeRosterReport,
        SalaryAnalysisReport,
        ComplianceReport,
        TimeSummaryReport,
        Dict[str, Any]
    ] = Field(..., description="Report data")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "metadata": {
                    "report_id": "rpt_001",
                    "report_type": "employee_roster",
                    "status": "completed"
                },
                "data": {"entries": []}
            }
        }
    )


# Report List and Management

class ReportListEntry(BaseModel):
    """Schema for report list entry."""
    
    report_id: str = Field(..., description="Report ID")
    report_type: ReportType = Field(..., description="Report type")
    report_format: ReportFormat = Field(..., description="Report format")
    status: ReportStatus = Field(..., description="Report status")
    generated_at: datetime = Field(..., description="Generation timestamp")
    generated_by: int = Field(..., description="Generated by user ID")
    total_records: int = Field(..., description="Total records")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    download_url: Optional[str] = Field(None, description="Download URL")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")


class ReportListResponse(BaseModel):
    """Schema for report list response."""
    
    reports: List[ReportListEntry] = Field(..., description="List of reports")
    total: int = Field(..., description="Total number of reports")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Number of reports per page")
    pages: int = Field(..., description="Total number of pages")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "reports": [],
                "total": 10,
                "page": 1,
                "per_page": 10,
                "pages": 1
            }
        }
    ) 