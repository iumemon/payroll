"""
Employee schemas for API request/response validation.

This module defines Pydantic schemas for employee-related operations
including employee creation, updates, and payroll information.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator

from app.models.enums import (
    EmployeeStatus, EmploymentType, PayrollFrequency
)


class EmployeeBase(BaseModel):
    """Base employee schema with common fields."""
    
    employee_id: str = Field(..., min_length=1, max_length=20, description="Employee ID")
    first_name: str = Field(..., min_length=1, max_length=50, description="First name")
    last_name: str = Field(..., min_length=1, max_length=50, description="Last name")
    middle_name: Optional[str] = Field(None, max_length=50, description="Middle name")
    preferred_name: Optional[str] = Field(None, max_length=50, description="Preferred name")
    email: EmailStr = Field(..., description="Employee's email address")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    position: str = Field(..., min_length=1, max_length=100, description="Job position")
    department: Optional[str] = Field(None, max_length=100, description="Department")
    hire_date: date = Field(..., description="Hire date")
    status: EmployeeStatus = Field(EmployeeStatus.ACTIVE, description="Employee status")
    employment_type: EmploymentType = Field(EmploymentType.FULL_TIME, description="Employment type")


class EmployeeCreate(EmployeeBase):
    """Schema for creating a new employee."""
    
    user_id: Optional[int] = Field(None, description="Associated user ID")
    manager_id: Optional[int] = Field(None, description="Manager employee ID")
    
    # Address Information
    address_line1: Optional[str] = Field(None, max_length=255, description="Address line 1")
    address_line2: Optional[str] = Field(None, max_length=255, description="Address line 2")
    city: Optional[str] = Field(None, max_length=100, description="City")
    state: Optional[str] = Field(None, max_length=50, description="State")
    postal_code: Optional[str] = Field(None, max_length=20, description="Postal code")
    country: str = Field("USA", max_length=100, description="Country")
    
    # Emergency Contact
    emergency_contact_name: Optional[str] = Field(None, max_length=100, description="Emergency contact name")
    emergency_contact_phone: Optional[str] = Field(None, max_length=20, description="Emergency contact phone")
    
    # Compensation
    salary: Optional[Decimal] = Field(None, ge=0, description="Annual salary")
    hourly_rate: Optional[Decimal] = Field(None, ge=0, description="Hourly rate")
    payroll_frequency: PayrollFrequency = Field(PayrollFrequency.BIWEEKLY, description="Payroll frequency")
    overtime_rate: Optional[Decimal] = Field(None, ge=0, description="Overtime rate multiplier")
    
    # Tax Information
    federal_allowances: int = Field(0, ge=0, description="Federal tax allowances")
    state_allowances: int = Field(0, ge=0, description="State tax allowances")
    additional_federal_withholding: Decimal = Field(Decimal('0.00'), ge=0, description="Additional federal withholding")
    additional_state_withholding: Decimal = Field(Decimal('0.00'), ge=0, description="Additional state withholding")
    
    # Benefits
    health_insurance: bool = Field(False, description="Health insurance enrollment")
    dental_insurance: bool = Field(False, description="Dental insurance enrollment")
    vision_insurance: bool = Field(False, description="Vision insurance enrollment")
    life_insurance: bool = Field(False, description="Life insurance enrollment")
    disability_insurance: bool = Field(False, description="Disability insurance enrollment")
    retirement_401k: bool = Field(False, description="401k enrollment")
    retirement_401k_percent: Decimal = Field(Decimal('0.00'), ge=0, le=100, description="401k contribution percentage")
    
    # PTO
    vacation_days_per_year: int = Field(0, ge=0, description="Vacation days per year")
    sick_days_per_year: int = Field(0, ge=0, description="Sick days per year")
    personal_days_per_year: int = Field(0, ge=0, description="Personal days per year")
    
    @field_validator("salary", "hourly_rate")
    @classmethod
    def validate_compensation(cls, v, info):
        """Validate that either salary or hourly_rate is provided."""
        if info.field_name == "salary" and v is None:
            # Check if hourly_rate is provided in the data
            return v
        return v
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "employee_id": "EMP001",
                "first_name": "John",
                "last_name": "Doe",
                "email": "john.doe@company.com",
                "phone": "+1-555-123-4567",
                "position": "Software Engineer",
                "department": "Engineering",
                "hire_date": "2024-01-15",
                "status": "active",
                "employment_type": "full_time",
                "salary": 75000.00,
                "payroll_frequency": "biweekly",
                "address_line1": "123 Main St",
                "city": "Anytown",
                "state": "CA",
                "postal_code": "12345",
                "emergency_contact_name": "Jane Doe",
                "emergency_contact_phone": "+1-555-987-6543",
                "vacation_days_per_year": 20,
                "sick_days_per_year": 10
            }
        }
    )


class EmployeeUpdate(BaseModel):
    """Schema for updating employee information."""
    
    first_name: Optional[str] = Field(None, min_length=1, max_length=50, description="First name")
    last_name: Optional[str] = Field(None, min_length=1, max_length=50, description="Last name")
    middle_name: Optional[str] = Field(None, max_length=50, description="Middle name")
    preferred_name: Optional[str] = Field(None, max_length=50, description="Preferred name")
    email: Optional[EmailStr] = Field(None, description="Employee's email address")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    position: Optional[str] = Field(None, min_length=1, max_length=100, description="Job position")
    department: Optional[str] = Field(None, max_length=100, description="Department")
    status: Optional[EmployeeStatus] = Field(None, description="Employee status")
    employment_type: Optional[EmploymentType] = Field(None, description="Employment type")
    manager_id: Optional[int] = Field(None, description="Manager employee ID")
    termination_date: Optional[date] = Field(None, description="Termination date")
    
    # Address Information
    address_line1: Optional[str] = Field(None, max_length=255, description="Address line 1")
    address_line2: Optional[str] = Field(None, max_length=255, description="Address line 2")
    city: Optional[str] = Field(None, max_length=100, description="City")
    state: Optional[str] = Field(None, max_length=50, description="State")
    postal_code: Optional[str] = Field(None, max_length=20, description="Postal code")
    country: Optional[str] = Field(None, max_length=100, description="Country")
    
    # Emergency Contact
    emergency_contact_name: Optional[str] = Field(None, max_length=100, description="Emergency contact name")
    emergency_contact_phone: Optional[str] = Field(None, max_length=20, description="Emergency contact phone")
    
    # Compensation
    salary: Optional[Decimal] = Field(None, ge=0, description="Annual salary")
    hourly_rate: Optional[Decimal] = Field(None, ge=0, description="Hourly rate")
    payroll_frequency: Optional[PayrollFrequency] = Field(None, description="Payroll frequency")
    overtime_rate: Optional[Decimal] = Field(None, ge=0, description="Overtime rate multiplier")
    
    # Benefits
    health_insurance: Optional[bool] = Field(None, description="Health insurance enrollment")
    dental_insurance: Optional[bool] = Field(None, description="Dental insurance enrollment")
    vision_insurance: Optional[bool] = Field(None, description="Vision insurance enrollment")
    retirement_401k: Optional[bool] = Field(None, description="401k enrollment")
    retirement_401k_percent: Optional[Decimal] = Field(None, ge=0, le=100, description="401k contribution percentage")
    
    # PTO
    vacation_days_per_year: Optional[int] = Field(None, ge=0, description="Vacation days per year")
    sick_days_per_year: Optional[int] = Field(None, ge=0, description="Sick days per year")
    personal_days_per_year: Optional[int] = Field(None, ge=0, description="Personal days per year")
    
    # Notes
    notes: Optional[str] = Field(None, max_length=2000, description="Employee notes")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "position": "Senior Software Engineer",
                "department": "Engineering",
                "salary": 85000.00,
                "phone": "+1-555-123-4567",
                "notes": "Promoted to senior position"
            }
        }
    )


class EmployeeResponse(EmployeeBase):
    """Schema for employee response data."""
    
    id: int = Field(..., description="Employee ID")
    user_id: Optional[int] = Field(None, description="Associated user ID")
    manager_id: Optional[int] = Field(None, description="Manager employee ID")
    termination_date: Optional[date] = Field(None, description="Termination date")
    
    # Address Information
    address_line1: Optional[str] = Field(None, description="Address line 1")
    address_line2: Optional[str] = Field(None, description="Address line 2")
    city: Optional[str] = Field(None, description="City")
    state: Optional[str] = Field(None, description="State")
    postal_code: Optional[str] = Field(None, description="Postal code")
    country: Optional[str] = Field(None, description="Country")
    
    # Emergency Contact
    emergency_contact_name: Optional[str] = Field(None, description="Emergency contact name")
    emergency_contact_phone: Optional[str] = Field(None, description="Emergency contact phone")
    
    # Compensation
    salary: Optional[Decimal] = Field(None, description="Annual salary")
    hourly_rate: Optional[Decimal] = Field(None, description="Hourly rate")
    payroll_frequency: PayrollFrequency = Field(..., description="Payroll frequency")
    overtime_rate: Optional[Decimal] = Field(None, description="Overtime rate multiplier")
    
    # Benefits
    health_insurance: bool = Field(..., description="Health insurance enrollment")
    dental_insurance: bool = Field(..., description="Dental insurance enrollment")
    vision_insurance: bool = Field(..., description="Vision insurance enrollment")
    retirement_401k: bool = Field(..., description="401k enrollment")
    retirement_401k_percent: Decimal = Field(..., description="401k contribution percentage")
    
    # PTO
    vacation_days_per_year: int = Field(..., description="Vacation days per year")
    sick_days_per_year: int = Field(..., description="Sick days per year")
    personal_days_per_year: int = Field(..., description="Personal days per year")
    vacation_days_used: int = Field(..., description="Vacation days used")
    sick_days_used: int = Field(..., description="Sick days used")
    personal_days_used: int = Field(..., description="Personal days used")
    
    # Computed fields from Employee model properties
    full_name: str = Field(..., description="Full name")
    display_name: str = Field(..., description="Display name")
    is_active: bool = Field(..., description="Is active")
    is_salaried: bool = Field(..., description="Is salaried")
    is_hourly: bool = Field(..., description="Is hourly")
    vacation_days_remaining: int = Field(..., description="Vacation days remaining")
    sick_days_remaining: int = Field(..., description="Sick days remaining")
    personal_days_remaining: int = Field(..., description="Personal days remaining")
    years_of_service: int = Field(..., description="Years of service")
    
    # Timestamps
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    # Profile
    profile_picture: Optional[str] = Field(None, description="Profile picture URL")
    notes: Optional[str] = Field(None, description="Employee notes")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "employee_id": "EMP001",
                "first_name": "John",
                "last_name": "Doe",
                "email": "john.doe@company.com",
                "phone": "+1-555-123-4567",
                "position": "Software Engineer",
                "department": "Engineering",
                "hire_date": "2024-01-15",
                "status": "active",
                "employment_type": "full_time",
                "salary": 75000.00,
                "payroll_frequency": "biweekly",
                "vacation_days_per_year": 20,
                "sick_days_per_year": 10,
                "vacation_days_used": 5,
                "sick_days_used": 2,
                "vacation_days_remaining": 15,
                "sick_days_remaining": 8,
                "years_of_service": 1,
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00"
            }
        }
    )


class EmployeeList(BaseModel):
    """Schema for paginated employee list."""
    
    employees: list[EmployeeResponse] = Field(..., description="List of employees")
    total: int = Field(..., description="Total number of employees")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Number of employees per page")
    pages: int = Field(..., description="Total number of pages")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "employees": [
                    {
                        "id": 1,
                        "employee_id": "EMP001",
                        "first_name": "John",
                        "last_name": "Doe",
                        "email": "john.doe@company.com",
                        "position": "Software Engineer",
                        "department": "Engineering",
                        "status": "active",
                        "employment_type": "full_time"
                    }
                ],
                "total": 1,
                "page": 1,
                "per_page": 10,
                "pages": 1
            }
        }
    )


class EmployeeSummary(BaseModel):
    """Schema for employee summary information."""
    
    id: int = Field(..., description="Employee ID")
    employee_id: str = Field(..., description="Employee ID")
    full_name: str = Field(..., description="Full name")
    email: EmailStr = Field(..., description="Email address")
    position: str = Field(..., description="Position")
    department: Optional[str] = Field(None, description="Department")
    status: EmployeeStatus = Field(..., description="Status")
    hire_date: date = Field(..., description="Hire date")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "employee_id": "EMP001",
                "full_name": "John Doe",
                "email": "john.doe@company.com",
                "position": "Software Engineer",
                "department": "Engineering",
                "status": "active",
                "hire_date": "2024-01-15"
            }
        }
    ) 