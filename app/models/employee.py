"""
Employee model for payroll management.

This module defines the Employee model which handles employee information,
compensation, benefits, and payroll-related data.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Enum, ForeignKey, Integer, 
    Numeric, String, Text, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.enums import (
    EmployeeStatus, EmploymentType, PayrollFrequency
)


class Employee(Base):
    """Employee model for payroll management."""
    
    __tablename__ = "employees"
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String(20), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Personal Information
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    middle_name = Column(String(50), nullable=True)
    preferred_name = Column(String(50), nullable=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(20), nullable=True)
    emergency_contact_name = Column(String(100), nullable=True)
    emergency_contact_phone = Column(String(20), nullable=True)
    
    # Address Information
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(50), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(100), default="USA")
    
    # Employment Information
    status = Column(Enum(EmployeeStatus), default=EmployeeStatus.ACTIVE)
    employment_type = Column(Enum(EmploymentType), default=EmploymentType.FULL_TIME)
    hire_date = Column(Date, nullable=False)
    termination_date = Column(Date, nullable=True)
    department = Column(String(100), nullable=True)
    position = Column(String(100), nullable=False)
    manager_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    
    # Compensation Information
    salary = Column(Numeric(10, 2), nullable=True)  # Annual salary
    hourly_rate = Column(Numeric(10, 2), nullable=True)  # Hourly rate
    payroll_frequency = Column(Enum(PayrollFrequency), default=PayrollFrequency.BIWEEKLY)
    overtime_rate = Column(Numeric(10, 2), nullable=True)  # Overtime multiplier
    
    # Tax Information
    ssn = Column(String(11), nullable=True)  # Encrypted
    tax_id = Column(String(20), nullable=True)  # Alternative to SSN
    federal_allowances = Column(Integer, default=0)
    state_allowances = Column(Integer, default=0)
    additional_federal_withholding = Column(Numeric(10, 2), default=0)
    additional_state_withholding = Column(Numeric(10, 2), default=0)
    
    # Benefits Information
    health_insurance = Column(Boolean, default=False)
    dental_insurance = Column(Boolean, default=False)
    vision_insurance = Column(Boolean, default=False)
    life_insurance = Column(Boolean, default=False)
    disability_insurance = Column(Boolean, default=False)
    retirement_401k = Column(Boolean, default=False)
    retirement_401k_percent = Column(Numeric(5, 2), default=0)
    retirement_401k_match = Column(Numeric(5, 2), default=0)
    
    # PTO Information
    vacation_days_per_year = Column(Integer, default=0)
    sick_days_per_year = Column(Integer, default=0)
    personal_days_per_year = Column(Integer, default=0)
    vacation_days_used = Column(Integer, default=0)
    sick_days_used = Column(Integer, default=0)
    personal_days_used = Column(Integer, default=0)
    
    # Banking Information (Encrypted)
    bank_name = Column(String(100), nullable=True)
    bank_routing_number = Column(String(20), nullable=True)
    bank_account_number = Column(String(30), nullable=True)
    bank_account_type = Column(String(20), nullable=True)  # checking, savings
    
    # Compliance Information
    i9_completed = Column(Boolean, default=False)
    w4_completed = Column(Boolean, default=False)
    background_check_completed = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Profile
    profile_picture = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="employee")
    manager = relationship("Employee", remote_side=[id])
    subordinates = relationship("Employee", back_populates="manager")
    payroll_records = relationship("PayrollRecord", back_populates="employee")
    time_entries = relationship("TimeEntry", foreign_keys="TimeEntry.employee_id", back_populates="employee")
    approved_time_entries = relationship("TimeEntry", foreign_keys="TimeEntry.approved_by", back_populates="approver")
    adjusted_time_entries = relationship("TimeEntry", foreign_keys="TimeEntry.adjusted_by", back_populates="adjuster")
    # leave_requests = relationship("LeaveRequest", back_populates="employee")
    # benefits = relationship("EmployeeBenefit", back_populates="employee")
    
    # Constraints and Indexes for Performance
    __table_args__ = (
        UniqueConstraint("employee_id", name="uq_employee_id"),
        # Performance indexes based on common query patterns
        Index('idx_employee_department', 'department'),
        Index('idx_employee_status', 'status'),
        Index('idx_employee_employment_type', 'employment_type'),
        Index('idx_employee_hire_date', 'hire_date'),
        Index('idx_employee_manager_id', 'manager_id'),
        Index('idx_employee_name_search', 'first_name', 'last_name'),
        Index('idx_employee_created_at', 'created_at'),
        Index('idx_employee_updated_at', 'updated_at'),
        # Composite indexes for common filter combinations
        Index('idx_employee_status_dept', 'status', 'department'),
        Index('idx_employee_status_emp_type', 'status', 'employment_type'),
        Index('idx_employee_dept_emp_type', 'department', 'employment_type'),
        Index('idx_employee_active_hire_date', 'status', 'hire_date'),
    )
    
    def __repr__(self) -> str:
        return f"<Employee(id={self.id}, employee_id='{self.employee_id}', name='{self.full_name}')>"
    
    @property
    def full_name(self) -> str:
        """Get the employee's full name."""
        if self.middle_name:
            return f"{self.first_name} {self.middle_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"
    
    @property
    def display_name(self) -> str:
        """Get the employee's display name (preferred or full name)."""
        return self.preferred_name or self.full_name
    
    @property
    def is_active(self) -> bool:
        """Check if employee is active."""
        return self.status == EmployeeStatus.ACTIVE
    
    @property
    def is_terminated(self) -> bool:
        """Check if employee is terminated."""
        return self.status == EmployeeStatus.TERMINATED
    
    @property
    def is_salaried(self) -> bool:
        """Check if employee is salaried."""
        return self.salary is not None and self.salary > 0
    
    @property
    def is_hourly(self) -> bool:
        """Check if employee is hourly."""
        return self.hourly_rate is not None and self.hourly_rate > 0
    
    @property
    def age(self) -> Optional[int]:
        """Calculate employee age (would need birth_date field)."""
        # This would require a birth_date field to implement
        return None
    
    @property
    def years_of_service(self) -> int:
        """Calculate years of service."""
        if self.hire_date:
            end_date = self.termination_date or date.today()
            return (end_date - self.hire_date).days // 365
        return 0
    
    @property
    def vacation_days_remaining(self) -> int:
        """Calculate remaining vacation days."""
        return max(0, self.vacation_days_per_year - self.vacation_days_used)
    
    @property
    def sick_days_remaining(self) -> int:
        """Calculate remaining sick days."""
        return max(0, self.sick_days_per_year - self.sick_days_used)
    
    @property
    def personal_days_remaining(self) -> int:
        """Calculate remaining personal days."""
        return max(0, self.personal_days_per_year - self.personal_days_used)
    
    def calculate_gross_pay(self, hours_worked: float = 0, pay_periods: int = 1) -> Decimal:
        """Calculate gross pay based on salary or hourly rate."""
        if self.is_salaried:
            # Calculate salary per pay period
            if self.payroll_frequency == PayrollFrequency.WEEKLY:
                return Decimal(str(self.salary)) / 52 * pay_periods
            elif self.payroll_frequency == PayrollFrequency.BIWEEKLY:
                return Decimal(str(self.salary)) / 26 * pay_periods
            elif self.payroll_frequency == PayrollFrequency.SEMI_MONTHLY:
                return Decimal(str(self.salary)) / 24 * pay_periods
            elif self.payroll_frequency == PayrollFrequency.MONTHLY:
                return Decimal(str(self.salary)) / 12 * pay_periods
            else:
                return Decimal(str(self.salary)) * pay_periods
        
        elif self.is_hourly:
            return Decimal(str(self.hourly_rate)) * Decimal(str(hours_worked))
        
        return Decimal('0.00')
    
    def calculate_overtime_pay(self, overtime_hours: float) -> Decimal:
        """Calculate overtime pay."""
        if self.is_hourly and self.hourly_rate and overtime_hours > 0:
            overtime_rate = self.overtime_rate or Decimal('1.5')
            return Decimal(str(self.hourly_rate)) * overtime_rate * Decimal(str(overtime_hours))
        return Decimal('0.00')
    
    def is_eligible_for_benefits(self) -> bool:
        """Check if employee is eligible for benefits."""
        # Basic eligibility check - can be extended with more complex rules
        return (
            self.is_active and
            self.employment_type in [EmploymentType.FULL_TIME, EmploymentType.PART_TIME] and
            self.years_of_service >= 0  # Immediate eligibility, can be modified
        )
    
    def get_full_address(self) -> str:
        """Get formatted full address."""
        parts = [
            self.address_line1,
            self.address_line2,
            self.city,
            self.state,
            self.postal_code,
            self.country
        ]
        return ", ".join(filter(None, parts)) 