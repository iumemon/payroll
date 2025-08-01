"""
Payroll schemas for API request/response validation.

This module defines Pydantic schemas for payroll-related operations
including payroll calculations, pay periods, and payroll records.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator

from app.models.enums import PayrollFrequency, PayrollStatus, PayrollType


class PayrollCalculationRequest(BaseModel):
    """Schema for payroll calculation requests."""
    
    employee_id: int = Field(..., description="Employee ID")
    pay_period_start: date = Field(..., description="Pay period start date")
    pay_period_end: date = Field(..., description="Pay period end date")
    hours_worked: Optional[Decimal] = Field(None, ge=0, le=168, description="Regular hours worked")
    overtime_hours: Optional[Decimal] = Field(None, ge=0, le=168, description="Overtime hours worked")
    bonus_amount: Optional[Decimal] = Field(None, ge=0, description="Bonus amount")
    commission_amount: Optional[Decimal] = Field(None, ge=0, description="Commission amount")
    other_earnings: Optional[Decimal] = Field(None, ge=0, description="Other earnings")
    additional_deductions: Optional[Decimal] = Field(None, ge=0, description="Additional deductions")
    notes: Optional[str] = Field(None, max_length=1000, description="Payroll notes")
    
    @field_validator("pay_period_end")
    @classmethod
    def validate_pay_period(cls, v, info):
        """Validate that pay period end is after start."""
        if info.data.get("pay_period_start") and v <= info.data["pay_period_start"]:
            raise ValueError("Pay period end must be after start date")
        return v
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "employee_id": 1,
                "pay_period_start": "2024-01-01",
                "pay_period_end": "2024-01-14",
                "hours_worked": 80,
                "overtime_hours": 5,
                "bonus_amount": 500.00,
                "notes": "Year-end bonus included"
            }
        }
    )


class PayrollCalculationResponse(BaseModel):
    """Schema for payroll calculation responses."""
    
    employee_id: int = Field(..., description="Employee ID")
    employee_name: str = Field(..., description="Employee name")
    pay_period_start: date = Field(..., description="Pay period start date")
    pay_period_end: date = Field(..., description="Pay period end date")
    
    # Earnings
    hours_worked: Decimal = Field(..., description="Total hours worked")
    regular_hours: Optional[Decimal] = Field(None, description="Regular hours worked")
    overtime_hours: Decimal = Field(..., description="Overtime hours worked")
    double_time_hours: Optional[Decimal] = Field(None, description="Double time hours worked")
    gross_pay: Decimal = Field(..., description="Gross pay amount")
    
    # Time entry integration
    time_entries_used: Optional[bool] = Field(None, description="Whether time entries were used")
    time_entries_count: Optional[int] = Field(None, description="Number of time entries used")
    
    # Deductions breakdown
    tax_deductions: Dict[str, Decimal] = Field(..., description="Tax deductions")
    benefit_deductions: Dict[str, Decimal] = Field(..., description="Benefit deductions")
    other_deductions: Dict[str, Decimal] = Field(..., description="Other deductions")
    total_deductions: Decimal = Field(..., description="Total deductions")
    
    # Net pay
    net_pay: Decimal = Field(..., description="Net pay amount")
    
    # Meta information
    calculated_at: datetime = Field(..., description="Calculation timestamp")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "employee_id": 1,
                "employee_name": "John Doe",
                "pay_period_start": "2024-01-01",
                "pay_period_end": "2024-01-14",
                "hours_worked": 80,
                "overtime_hours": 5,
                "gross_pay": 3250.00,
                "tax_deductions": {
                    "federal_income_tax": 520.00,
                    "state_income_tax": 162.50,
                    "social_security_tax": 201.50,
                    "medicare_tax": 47.13
                },
                "benefit_deductions": {
                    "health_insurance": 150.00,
                    "dental_insurance": 25.00,
                    "retirement_401k": 195.00
                },
                "other_deductions": {},
                "total_deductions": 1301.13,
                "net_pay": 1948.87,
                "calculated_at": "2024-01-15T10:30:00Z"
            }
        }
    )


class PayPeriodCreate(BaseModel):
    """Schema for creating pay periods."""
    
    start_date: date = Field(..., description="Pay period start date")
    end_date: date = Field(..., description="Pay period end date")
    pay_date: date = Field(..., description="Pay date")
    frequency: PayrollFrequency = Field(..., description="Payroll frequency")
    description: Optional[str] = Field(None, max_length=255, description="Pay period description")
    is_holiday_period: bool = Field(False, description="Is this a holiday pay period")
    
    @field_validator("end_date")
    @classmethod
    def validate_end_date(cls, v, info):
        """Validate that end date is after start date."""
        if info.data.get("start_date") and v <= info.data["start_date"]:
            raise ValueError("End date must be after start date")
        return v
    
    @field_validator("pay_date")
    @classmethod
    def validate_pay_date(cls, v, info):
        """Validate that pay date is after end date."""
        if info.data.get("end_date") and v < info.data["end_date"]:
            raise ValueError("Pay date must be on or after end date")
        return v
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "start_date": "2024-01-01",
                "end_date": "2024-01-14",
                "pay_date": "2024-01-19",
                "frequency": "biweekly",
                "description": "First pay period of 2024",
                "is_holiday_period": False
            }
        }
    )


class PayPeriodResponse(BaseModel):
    """Schema for pay period responses."""
    
    id: int = Field(..., description="Pay period ID")
    start_date: date = Field(..., description="Pay period start date")
    end_date: date = Field(..., description="Pay period end date")
    pay_date: date = Field(..., description="Pay date")
    frequency: PayrollFrequency = Field(..., description="Payroll frequency")
    description: Optional[str] = Field(None, description="Pay period description")
    is_holiday_period: bool = Field(..., description="Is this a holiday pay period")
    is_processed: bool = Field(..., description="Is this pay period processed")
    period_days: int = Field(..., description="Number of days in period")
    is_current_period: bool = Field(..., description="Is this the current pay period")
    
    # Timestamps
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "start_date": "2024-01-01",
                "end_date": "2024-01-14",
                "pay_date": "2024-01-19",
                "frequency": "biweekly",
                "description": "First pay period of 2024",
                "is_holiday_period": False,
                "is_processed": False,
                "period_days": 14,
                "is_current_period": True,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }
    )


class PayrollRecordCreate(BaseModel):
    """Schema for creating payroll records."""
    
    employee_id: int = Field(..., description="Employee ID")
    pay_period_id: int = Field(..., description="Pay period ID")
    hours_worked: Decimal = Field(0, ge=0, description="Hours worked")
    overtime_hours: Decimal = Field(0, ge=0, description="Overtime hours")
    notes: Optional[str] = Field(None, max_length=1000, description="Payroll notes")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "employee_id": 1,
                "pay_period_id": 1,
                "hours_worked": 80,
                "overtime_hours": 5,
                "notes": "Worked overtime on project deadline"
            }
        }
    )


class PayrollRecordResponse(BaseModel):
    """Schema for payroll record responses."""
    
    id: int = Field(..., description="Payroll record ID")
    employee_id: int = Field(..., description="Employee ID")
    pay_period_id: int = Field(..., description="Pay period ID")
    
    # Pay information
    hours_worked: Decimal = Field(..., description="Hours worked")
    overtime_hours: Decimal = Field(..., description="Overtime hours")
    gross_pay: Decimal = Field(..., description="Gross pay")
    net_pay: Decimal = Field(..., description="Net pay")
    
    # Tax deductions
    federal_income_tax: Decimal = Field(..., description="Federal income tax")
    state_income_tax: Decimal = Field(..., description="State income tax")
    social_security_tax: Decimal = Field(..., description="Social security tax")
    medicare_tax: Decimal = Field(..., description="Medicare tax")
    
    # Benefit deductions
    health_insurance: Decimal = Field(..., description="Health insurance")
    dental_insurance: Decimal = Field(..., description="Dental insurance")
    vision_insurance: Decimal = Field(..., description="Vision insurance")
    retirement_401k: Decimal = Field(..., description="401k contribution")
    
    # Other information
    total_deductions: Decimal = Field(..., description="Total deductions")
    status: PayrollStatus = Field(..., description="Payroll status")
    processed_at: Optional[datetime] = Field(None, description="Processing timestamp")
    notes: Optional[str] = Field(None, description="Payroll notes")
    
    # Computed properties
    tax_deductions_total: Decimal = Field(..., description="Total tax deductions")
    benefit_deductions_total: Decimal = Field(..., description="Total benefit deductions")
    take_home_percentage: Decimal = Field(..., description="Take-home percentage")
    
    # Timestamps
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "employee_id": 1,
                "pay_period_id": 1,
                "hours_worked": 80,
                "overtime_hours": 5,
                "gross_pay": 3250.00,
                "net_pay": 1948.87,
                "federal_income_tax": 520.00,
                "state_income_tax": 162.50,
                "social_security_tax": 201.50,
                "medicare_tax": 47.13,
                "health_insurance": 150.00,
                "dental_insurance": 25.00,
                "vision_insurance": 0.00,
                "retirement_401k": 195.00,
                "total_deductions": 1301.13,
                "status": "processed",
                "processed_at": "2024-01-15T10:30:00Z",
                "notes": "Regular bi-weekly payroll",
                "tax_deductions_total": 931.13,
                "benefit_deductions_total": 370.00,
                "take_home_percentage": 60.0,
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }
    )


class PayrollBatchRequest(BaseModel):
    """Schema for batch payroll processing requests."""
    
    pay_period_id: int = Field(..., description="Pay period ID")
    employee_ids: List[int] = Field(..., description="List of employee IDs to process")
    process_immediately: bool = Field(False, description="Process immediately or save as draft")
    notes: Optional[str] = Field(None, max_length=1000, description="Batch processing notes")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "pay_period_id": 1,
                "employee_ids": [1, 2, 3, 4, 5],
                "process_immediately": False,
                "notes": "Bi-weekly payroll processing"
            }
        }
    )


class PayrollBatchResponse(BaseModel):
    """Schema for batch payroll processing responses."""
    
    batch_id: str = Field(..., description="Batch processing ID")
    pay_period_id: int = Field(..., description="Pay period ID")
    processed_count: int = Field(..., description="Number of records processed")
    error_count: int = Field(..., description="Number of errors")
    total_gross_pay: Decimal = Field(..., description="Total gross pay")
    total_net_pay: Decimal = Field(..., description="Total net pay")
    total_deductions: Decimal = Field(..., description="Total deductions")
    processing_time: float = Field(..., description="Processing time in seconds")
    errors: List[str] = Field(..., description="List of errors")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "batch_id": "batch_2024_01_15_001",
                "pay_period_id": 1,
                "processed_count": 5,
                "error_count": 0,
                "total_gross_pay": 16250.00,
                "total_net_pay": 9744.35,
                "total_deductions": 6505.65,
                "processing_time": 2.45,
                "errors": []
            }
        }
    )


class PayrollSummary(BaseModel):
    """Schema for payroll summary information."""
    
    total_employees: int = Field(..., description="Total number of employees")
    processed_employees: int = Field(..., description="Number of processed employees")
    pending_employees: int = Field(..., description="Number of pending employees")
    total_gross_pay: Decimal = Field(..., description="Total gross pay")
    total_net_pay: Decimal = Field(..., description="Total net pay")
    total_deductions: Decimal = Field(..., description="Total deductions")
    average_gross_pay: Decimal = Field(..., description="Average gross pay")
    average_net_pay: Decimal = Field(..., description="Average net pay")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_employees": 25,
                "processed_employees": 20,
                "pending_employees": 5,
                "total_gross_pay": 81250.00,
                "total_net_pay": 48721.75,
                "total_deductions": 32528.25,
                "average_gross_pay": 3250.00,
                "average_net_pay": 1948.87
            }
        }
    ) 