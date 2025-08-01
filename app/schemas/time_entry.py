"""
Time Entry schemas for API request/response validation.

This module defines Pydantic schemas for time tracking operations
including time entry creation, updates, clock operations, and approval workflow.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, field_validator

from app.models.enums import TimeEntryStatus, TimeEntryType, ApprovalStatus


class TimeEntryBase(BaseModel):
    """Base time entry schema with common fields."""
    
    employee_id: int = Field(..., description="Employee ID")
    work_date: date = Field(..., description="Work date")
    entry_type: TimeEntryType = Field(TimeEntryType.REGULAR, description="Type of time entry")
    location: Optional[str] = Field(None, max_length=255, description="Work location")
    project_code: Optional[str] = Field(None, max_length=50, description="Project code")
    department: Optional[str] = Field(None, max_length=100, description="Department")
    notes: Optional[str] = Field(None, max_length=1000, description="Employee notes")


class TimeEntryCreate(TimeEntryBase):
    """Schema for creating a new time entry."""
    
    clock_in_time: Optional[datetime] = Field(None, description="Clock in time")
    clock_out_time: Optional[datetime] = Field(None, description="Clock out time")
    
    # Break times
    break_start_time: Optional[datetime] = Field(None, description="Break start time")
    break_end_time: Optional[datetime] = Field(None, description="Break end time")
    lunch_start_time: Optional[datetime] = Field(None, description="Lunch start time")
    lunch_end_time: Optional[datetime] = Field(None, description="Lunch end time")
    
    # Manual entry fields
    is_manual_entry: bool = Field(False, description="Is this a manual entry")
    manual_entry_reason: Optional[str] = Field(None, max_length=500, description="Reason for manual entry")
    
    # Manual time fields (for manual entries)
    total_hours: Optional[Decimal] = Field(None, ge=0, le=24, description="Total hours worked")
    regular_hours: Optional[Decimal] = Field(None, ge=0, le=24, description="Regular hours worked")
    overtime_hours: Optional[Decimal] = Field(None, ge=0, le=24, description="Overtime hours worked")
    
    @field_validator("clock_out_time")
    @classmethod
    def validate_clock_out_time(cls, v, info):
        """Validate that clock out time is after clock in time."""
        if v is not None and "clock_in_time" in info.data:
            clock_in_time = info.data["clock_in_time"]
            if clock_in_time is not None and v <= clock_in_time:
                raise ValueError("Clock out time must be after clock in time")
        return v
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "employee_id": 1,
                "work_date": "2024-01-15",
                "entry_type": "regular",
                "clock_in_time": "2024-01-15T09:00:00",
                "clock_out_time": "2024-01-15T17:30:00",
                "lunch_start_time": "2024-01-15T12:00:00",
                "lunch_end_time": "2024-01-15T13:00:00",
                "location": "Main Office",
                "project_code": "PROJ001",
                "notes": "Regular workday"
            }
        }
    )


class TimeEntryUpdate(BaseModel):
    """Schema for updating time entry information."""
    
    work_date: Optional[date] = Field(None, description="Work date")
    entry_type: Optional[TimeEntryType] = Field(None, description="Type of time entry")
    
    # Time fields
    clock_in_time: Optional[datetime] = Field(None, description="Clock in time")
    clock_out_time: Optional[datetime] = Field(None, description="Clock out time")
    break_start_time: Optional[datetime] = Field(None, description="Break start time")
    break_end_time: Optional[datetime] = Field(None, description="Break end time")
    lunch_start_time: Optional[datetime] = Field(None, description="Lunch start time")
    lunch_end_time: Optional[datetime] = Field(None, description="Lunch end time")
    
    # Manual adjustments
    adjusted_hours: Optional[Decimal] = Field(None, ge=0, le=24, description="Adjusted hours")
    adjustment_reason: Optional[str] = Field(None, max_length=500, description="Reason for adjustment")
    
    # Location and project
    location: Optional[str] = Field(None, max_length=255, description="Work location")
    project_code: Optional[str] = Field(None, max_length=50, description="Project code")
    department: Optional[str] = Field(None, max_length=100, description="Department")
    
    # Notes
    notes: Optional[str] = Field(None, max_length=1000, description="Employee notes")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "clock_out_time": "2024-01-15T17:30:00",
                "notes": "Updated clock out time",
                "adjustment_reason": "Forgot to clock out"
            }
        }
    )


class ClockInRequest(BaseModel):
    """Schema for clock in request."""
    
    employee_id: int = Field(..., description="Employee ID")
    work_date: Optional[date] = Field(None, description="Work date (defaults to today)")
    clock_in_time: Optional[datetime] = Field(None, description="Clock in time (defaults to now)")
    location: Optional[str] = Field(None, max_length=255, description="Work location")
    project_code: Optional[str] = Field(None, max_length=50, description="Project code")
    notes: Optional[str] = Field(None, max_length=500, description="Notes")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "employee_id": 1,
                "location": "Main Office",
                "project_code": "PROJ001",
                "notes": "Starting work day"
            }
        }
    )


class ClockOutRequest(BaseModel):
    """Schema for clock out request."""
    
    time_entry_id: int = Field(..., description="Time entry ID")
    clock_out_time: Optional[datetime] = Field(None, description="Clock out time (defaults to now)")
    notes: Optional[str] = Field(None, max_length=500, description="Notes")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "time_entry_id": 1,
                "notes": "End of work day"
            }
        }
    )


class BreakRequest(BaseModel):
    """Schema for break start/end request."""
    
    time_entry_id: int = Field(..., description="Time entry ID")
    break_time: Optional[datetime] = Field(None, description="Break time (defaults to now)")
    is_lunch: bool = Field(False, description="Is this a lunch break")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "time_entry_id": 1,
                "is_lunch": True
            }
        }
    )


class TimeEntryApproval(BaseModel):
    """Schema for time entry approval/rejection."""
    
    time_entry_ids: List[int] = Field(..., description="List of time entry IDs")
    approval_status: ApprovalStatus = Field(..., description="Approval status")
    notes: Optional[str] = Field(None, max_length=1000, description="Approval notes")
    rejection_reason: Optional[str] = Field(None, max_length=500, description="Rejection reason")
    
    @field_validator("rejection_reason")
    @classmethod
    def validate_rejection_reason(cls, v, info):
        """Validate that rejection reason is provided when rejecting."""
        if "approval_status" in info.data:
            approval_status = info.data["approval_status"]
            if approval_status == ApprovalStatus.REJECTED and not v:
                raise ValueError("Rejection reason is required when rejecting time entries")
        return v
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "time_entry_ids": [1, 2, 3],
                "approval_status": "approved",
                "notes": "All time entries look correct"
            }
        }
    )


class TimeEntryResponse(TimeEntryBase):
    """Schema for time entry response data."""
    
    id: int = Field(..., description="Time entry ID")
    status: TimeEntryStatus = Field(..., description="Time entry status")
    approval_status: ApprovalStatus = Field(..., description="Approval status")
    
    # Time fields
    clock_in_time: Optional[datetime] = Field(None, description="Clock in time")
    clock_out_time: Optional[datetime] = Field(None, description="Clock out time")
    break_start_time: Optional[datetime] = Field(None, description="Break start time")
    break_end_time: Optional[datetime] = Field(None, description="Break end time")
    lunch_start_time: Optional[datetime] = Field(None, description="Lunch start time")
    lunch_end_time: Optional[datetime] = Field(None, description="Lunch end time")
    
    # Calculated time fields
    total_hours: Optional[Decimal] = Field(None, description="Total hours worked")
    regular_hours: Optional[Decimal] = Field(None, description="Regular hours worked")
    overtime_hours: Optional[Decimal] = Field(None, description="Overtime hours worked")
    double_time_hours: Optional[Decimal] = Field(None, description="Double time hours worked")
    break_duration: Optional[Decimal] = Field(None, description="Break duration in hours")
    lunch_duration: Optional[Decimal] = Field(None, description="Lunch duration in hours")
    
    # Approval fields
    approved_by: Optional[int] = Field(None, description="Approved by employee ID")
    approved_at: Optional[datetime] = Field(None, description="Approval timestamp")
    rejection_reason: Optional[str] = Field(None, description="Rejection reason")
    
    # Manual entry fields
    is_manual_entry: bool = Field(..., description="Is this a manual entry")
    manual_entry_reason: Optional[str] = Field(None, description="Reason for manual entry")
    
    # Adjustment fields
    adjusted_hours: Optional[Decimal] = Field(None, description="Adjusted hours")
    adjustment_reason: Optional[str] = Field(None, description="Reason for adjustment")
    adjusted_by: Optional[int] = Field(None, description="Adjusted by employee ID")
    adjusted_at: Optional[datetime] = Field(None, description="Adjustment timestamp")
    
    # Admin notes
    admin_notes: Optional[str] = Field(None, description="Admin notes")
    
    # Timestamps
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    submitted_at: Optional[datetime] = Field(None, description="Submission timestamp")
    
    # Computed properties
    is_clocked_in: bool = Field(..., description="Is currently clocked in")
    is_on_break: bool = Field(..., description="Is currently on break")
    is_complete: bool = Field(..., description="Is time entry complete")
    worked_duration_hours: Optional[Decimal] = Field(None, description="Worked duration in hours")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "employee_id": 1,
                "work_date": "2024-01-15",
                "entry_type": "regular",
                "status": "approved",
                "approval_status": "approved",
                "clock_in_time": "2024-01-15T09:00:00",
                "clock_out_time": "2024-01-15T17:30:00",
                "lunch_start_time": "2024-01-15T12:00:00",
                "lunch_end_time": "2024-01-15T13:00:00",
                "total_hours": "7.50",
                "regular_hours": "7.50",
                "overtime_hours": "0.00",
                "location": "Main Office",
                "project_code": "PROJ001",
                "is_manual_entry": False,
                "is_clocked_in": False,
                "is_on_break": False,
                "is_complete": True,
                "worked_duration_hours": "7.50"
            }
        }
    )


class TimeEntryList(BaseModel):
    """Schema for paginated time entry list."""
    
    time_entries: List[TimeEntryResponse] = Field(..., description="List of time entries")
    total: int = Field(..., description="Total number of time entries")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Number of time entries per page")
    pages: int = Field(..., description="Total number of pages")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "time_entries": [],
                "total": 25,
                "page": 1,
                "per_page": 10,
                "pages": 3
            }
        }
    )


class TimeEntrySummary(BaseModel):
    """Schema for time entry summary information."""
    
    id: int = Field(..., description="Time entry ID")
    employee_id: int = Field(..., description="Employee ID")
    work_date: date = Field(..., description="Work date")
    status: TimeEntryStatus = Field(..., description="Status")
    approval_status: ApprovalStatus = Field(..., description="Approval status")
    total_hours: Optional[Decimal] = Field(None, description="Total hours worked")
    overtime_hours: Optional[Decimal] = Field(None, description="Overtime hours worked")
    entry_type: TimeEntryType = Field(..., description="Entry type")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "employee_id": 1,
                "work_date": "2024-01-15",
                "status": "approved",
                "approval_status": "approved",
                "total_hours": "8.00",
                "overtime_hours": "0.00",
                "entry_type": "regular"
            }
        }
    )


class TimeEntryStats(BaseModel):
    """Schema for time entry statistics."""
    
    total_entries: int = Field(..., description="Total number of time entries")
    pending_approval: int = Field(..., description="Number of entries pending approval")
    approved_entries: int = Field(..., description="Number of approved entries")
    rejected_entries: int = Field(..., description="Number of rejected entries")
    total_hours: Decimal = Field(..., description="Total hours worked")
    regular_hours: Decimal = Field(..., description="Total regular hours")
    overtime_hours: Decimal = Field(..., description="Total overtime hours")
    employees_with_entries: int = Field(..., description="Number of employees with time entries")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_entries": 150,
                "pending_approval": 12,
                "approved_entries": 125,
                "rejected_entries": 3,
                "total_hours": "1200.00",
                "regular_hours": "1000.00",
                "overtime_hours": "200.00",
                "employees_with_entries": 25
            }
        }
    )


class EmployeeTimeReport(BaseModel):
    """Schema for employee time report."""
    
    employee_id: int = Field(..., description="Employee ID")
    employee_name: str = Field(..., description="Employee name")
    date_range: str = Field(..., description="Date range for report")
    total_entries: int = Field(..., description="Total number of entries")
    total_hours: Decimal = Field(..., description="Total hours worked")
    regular_hours: Decimal = Field(..., description="Regular hours worked")
    overtime_hours: Decimal = Field(..., description="Overtime hours worked")
    average_hours_per_day: Decimal = Field(..., description="Average hours per day")
    days_worked: int = Field(..., description="Number of days worked")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "employee_id": 1,
                "employee_name": "John Doe",
                "date_range": "2024-01-01 to 2024-01-31",
                "total_entries": 22,
                "total_hours": "176.00",
                "regular_hours": "160.00",
                "overtime_hours": "16.00",
                "average_hours_per_day": "8.00",
                "days_worked": 22
            }
        }
    ) 