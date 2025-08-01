"""
Payroll models for payroll management.

This module defines the PayrollRecord and PayPeriod models for handling
payroll calculations, pay periods, and payroll history.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean, Column, Date, DateTime, ForeignKey, Integer, 
    Numeric, String, Text, Enum, Index
)
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.enums import PayrollFrequency, PayrollStatus


class PayPeriod(Base):
    """Pay period model for tracking payroll periods."""
    
    __tablename__ = "pay_periods"
    
    id = Column(Integer, primary_key=True, index=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    pay_date = Column(Date, nullable=False)
    frequency = Column(Enum(PayrollFrequency), nullable=False)
    description = Column(String(255), nullable=True)
    is_holiday_period = Column(Boolean, default=False)
    is_processed = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    payroll_records = relationship("PayrollRecord", back_populates="pay_period")
    
    # Performance indexes
    __table_args__ = (
        Index('idx_pay_period_dates', 'start_date', 'end_date'),
        Index('idx_pay_period_start_date', 'start_date'),
        Index('idx_pay_period_end_date', 'end_date'),
        Index('idx_pay_period_pay_date', 'pay_date'),
        Index('idx_pay_period_frequency', 'frequency'),
        Index('idx_pay_period_is_processed', 'is_processed'),
        Index('idx_pay_period_created_at', 'created_at'),
        # Composite indexes for common queries
        Index('idx_pay_period_active_dates', 'start_date', 'end_date', 'is_processed'),
        Index('idx_pay_period_frequency_processed', 'frequency', 'is_processed'),
    )
    
    def __repr__(self) -> str:
        return f"<PayPeriod(id={self.id}, start_date='{self.start_date}', end_date='{self.end_date}')>"
    
    @property
    def period_days(self) -> int:
        """Calculate the number of days in the pay period."""
        return (self.end_date - self.start_date).days + 1
    
    @property
    def is_current_period(self) -> bool:
        """Check if this is the current pay period."""
        today = date.today()
        return self.start_date <= today <= self.end_date


class PayrollRecord(Base):
    """Payroll record model for storing payroll calculations."""
    
    __tablename__ = "payroll_records"
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    pay_period_id = Column(Integer, ForeignKey("pay_periods.id"), nullable=False)
    
    # Pay Information
    hours_worked = Column(Numeric(8, 2), default=0)
    overtime_hours = Column(Numeric(8, 2), default=0)
    gross_pay = Column(Numeric(10, 2), nullable=False)
    net_pay = Column(Numeric(10, 2), nullable=False)
    
    # Tax Deductions
    federal_income_tax = Column(Numeric(10, 2), default=0)
    state_income_tax = Column(Numeric(10, 2), default=0)
    social_security_tax = Column(Numeric(10, 2), default=0)
    medicare_tax = Column(Numeric(10, 2), default=0)
    
    # Benefit Deductions
    health_insurance = Column(Numeric(10, 2), default=0)
    dental_insurance = Column(Numeric(10, 2), default=0)
    vision_insurance = Column(Numeric(10, 2), default=0)
    life_insurance = Column(Numeric(10, 2), default=0)
    disability_insurance = Column(Numeric(10, 2), default=0)
    retirement_401k = Column(Numeric(10, 2), default=0)
    
    # Other Deductions
    other_deductions = Column(Numeric(10, 2), default=0)
    total_deductions = Column(Numeric(10, 2), nullable=False)
    
    # Status and Processing
    status = Column(Enum(PayrollStatus), default=PayrollStatus.DRAFT)
    processed_at = Column(DateTime, nullable=True)
    processed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Banking Information
    direct_deposit_amount = Column(Numeric(10, 2), nullable=True)
    check_number = Column(String(20), nullable=True)
    
    # Notes and Comments
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    employee = relationship("Employee", back_populates="payroll_records")
    pay_period = relationship("PayPeriod", back_populates="payroll_records")
    processed_by_user = relationship("User", foreign_keys=[processed_by])
    
    # Performance indexes
    __table_args__ = (
        Index('idx_payroll_employee_id', 'employee_id'),
        Index('idx_payroll_pay_period_id', 'pay_period_id'),
        Index('idx_payroll_status', 'status'),
        Index('idx_payroll_processed_at', 'processed_at'),
        Index('idx_payroll_processed_by', 'processed_by'),
        Index('idx_payroll_created_at', 'created_at'),
        Index('idx_payroll_updated_at', 'updated_at'),
        # Composite indexes for common queries
        Index('idx_payroll_employee_period', 'employee_id', 'pay_period_id'),
        Index('idx_payroll_employee_status', 'employee_id', 'status'),
        Index('idx_payroll_period_status', 'pay_period_id', 'status'),
        Index('idx_payroll_employee_processed', 'employee_id', 'processed_at'),
        Index('idx_payroll_status_processed', 'status', 'processed_at'),
    )
    
    def __repr__(self) -> str:
        return f"<PayrollRecord(id={self.id}, employee_id={self.employee_id}, net_pay={self.net_pay})>"
    
    @property
    def is_processed(self) -> bool:
        """Check if payroll record has been processed."""
        return self.status == PayrollStatus.PROCESSED
    
    @property
    def is_draft(self) -> bool:
        """Check if payroll record is still in draft status."""
        return self.status == PayrollStatus.DRAFT
    
    @property
    def effective_hourly_rate(self) -> Optional[Decimal]:
        """Calculate effective hourly rate based on gross pay and hours."""
        if self.hours_worked and self.hours_worked > 0:
            return self.gross_pay / self.hours_worked
        return None
    
    @property
    def tax_deductions_total(self) -> Decimal:
        """Calculate total tax deductions."""
        return (
            self.federal_income_tax + 
            self.state_income_tax + 
            self.social_security_tax + 
            self.medicare_tax
        )
    
    @property
    def benefit_deductions_total(self) -> Decimal:
        """Calculate total benefit deductions."""
        return (
            self.health_insurance + 
            self.dental_insurance + 
            self.vision_insurance + 
            self.life_insurance + 
            self.disability_insurance + 
            self.retirement_401k
        )
    
    @property
    def take_home_percentage(self) -> Decimal:
        """Calculate take-home pay percentage."""
        if self.gross_pay > 0:
            return (self.net_pay / self.gross_pay) * 100
        return Decimal('0.00') 