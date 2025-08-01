"""
Time Entry model for time tracking system.

This module defines the TimeEntry model which handles employee time tracking,
including clock in/out, break times, overtime calculations, and approval workflow.
"""

from datetime import datetime, date, time
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Enum, ForeignKey, Integer, 
    Numeric, String, Text, Time, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.enums import TimeEntryStatus, TimeEntryType, ApprovalStatus


class TimeEntry(Base):
    """Time entry model for employee time tracking."""
    
    __tablename__ = "time_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    
    # Date and Time Information
    work_date = Column(Date, nullable=False)
    clock_in_time = Column(DateTime, nullable=True)
    clock_out_time = Column(DateTime, nullable=True)
    
    # Break Information
    break_start_time = Column(DateTime, nullable=True)
    break_end_time = Column(DateTime, nullable=True)
    lunch_start_time = Column(DateTime, nullable=True)
    lunch_end_time = Column(DateTime, nullable=True)
    
    # Calculated Time Fields
    total_hours = Column(Numeric(8, 2), nullable=True)
    regular_hours = Column(Numeric(8, 2), nullable=True)
    overtime_hours = Column(Numeric(8, 2), nullable=True)
    double_time_hours = Column(Numeric(8, 2), nullable=True)
    break_duration = Column(Numeric(8, 2), nullable=True)  # In hours
    lunch_duration = Column(Numeric(8, 2), nullable=True)  # In hours
    
    # Entry Information
    entry_type = Column(Enum(TimeEntryType), default=TimeEntryType.REGULAR)
    status = Column(Enum(TimeEntryStatus), default=TimeEntryStatus.DRAFT)
    
    # Approval Workflow
    approval_status = Column(Enum(ApprovalStatus), default=ApprovalStatus.PENDING)
    approved_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # Manual Entry Fields
    is_manual_entry = Column(Boolean, default=False)
    manual_entry_reason = Column(Text, nullable=True)
    
    # Adjustment Fields
    adjusted_hours = Column(Numeric(8, 2), nullable=True)
    adjustment_reason = Column(Text, nullable=True)
    adjusted_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    adjusted_at = Column(DateTime, nullable=True)
    
    # Location/Project Information
    location = Column(String(255), nullable=True)
    project_code = Column(String(50), nullable=True)
    department = Column(String(100), nullable=True)
    
    # Notes and Comments
    notes = Column(Text, nullable=True)
    admin_notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    submitted_at = Column(DateTime, nullable=True)
    
    # Relationships
    employee = relationship("Employee", foreign_keys=[employee_id], back_populates="time_entries")
    approver = relationship("Employee", foreign_keys=[approved_by], back_populates="approved_time_entries")
    adjuster = relationship("Employee", foreign_keys=[adjusted_by], back_populates="adjusted_time_entries")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_time_entries_employee_date', 'employee_id', 'work_date'),
        Index('idx_time_entries_status', 'status'),
        Index('idx_time_entries_approval_status', 'approval_status'),
        Index('idx_time_entries_work_date', 'work_date'),
    )
    
    def __repr__(self) -> str:
        return f"<TimeEntry(id={self.id}, employee_id={self.employee_id}, work_date={self.work_date})>"
    
    @property
    def is_clocked_in(self) -> bool:
        """Check if employee is currently clocked in."""
        return self.clock_in_time is not None and self.clock_out_time is None
    
    @property
    def is_on_break(self) -> bool:
        """Check if employee is currently on break."""
        return (self.break_start_time is not None and self.break_end_time is None) or \
               (self.lunch_start_time is not None and self.lunch_end_time is None)
    
    @property
    def is_complete(self) -> bool:
        """Check if time entry is complete (clocked in and out)."""
        return self.clock_in_time is not None and self.clock_out_time is not None
    
    @property
    def worked_duration_minutes(self) -> int:
        """Calculate total worked duration in minutes."""
        if not self.is_complete:
            return 0
        
        total_minutes = int((self.clock_out_time - self.clock_in_time).total_seconds() / 60)
        
        # Subtract break time
        if self.break_duration:
            total_minutes -= int(float(self.break_duration) * 60)
        
        # Subtract lunch time
        if self.lunch_duration:
            total_minutes -= int(float(self.lunch_duration) * 60)
        
        return max(0, total_minutes)
    
    @property
    def worked_duration_hours(self) -> Decimal:
        """Calculate total worked duration in hours."""
        return Decimal(str(self.worked_duration_minutes / 60))
    
    def calculate_hours(self) -> None:
        """Calculate and update hour fields based on clock times."""
        if not self.is_complete:
            return
        
        # Calculate total worked hours
        total_worked = self.worked_duration_hours
        
        # Determine regular vs overtime hours
        # Standard assumption: 8 hours regular, anything over is overtime
        regular_hours_limit = Decimal('8.0')
        overtime_hours_limit = Decimal('12.0')  # Double time after 12 hours
        
        if total_worked <= regular_hours_limit:
            self.regular_hours = total_worked
            self.overtime_hours = Decimal('0.0')
            self.double_time_hours = Decimal('0.0')
        elif total_worked <= overtime_hours_limit:
            self.regular_hours = regular_hours_limit
            self.overtime_hours = total_worked - regular_hours_limit
            self.double_time_hours = Decimal('0.0')
        else:
            self.regular_hours = regular_hours_limit
            self.overtime_hours = overtime_hours_limit - regular_hours_limit
            self.double_time_hours = total_worked - overtime_hours_limit
        
        self.total_hours = total_worked
    
    def calculate_break_duration(self) -> None:
        """Calculate break duration in hours."""
        total_break_minutes = 0
        
        # Calculate break time
        if self.break_start_time and self.break_end_time:
            break_minutes = int((self.break_end_time - self.break_start_time).total_seconds() / 60)
            total_break_minutes += break_minutes
        
        # Calculate lunch time
        if self.lunch_start_time and self.lunch_end_time:
            lunch_minutes = int((self.lunch_end_time - self.lunch_start_time).total_seconds() / 60)
            total_break_minutes += lunch_minutes
            self.lunch_duration = Decimal(str(lunch_minutes / 60))
        
        if total_break_minutes > 0:
            self.break_duration = Decimal(str(total_break_minutes / 60))
    
    def clock_in(self, clock_time: Optional[datetime] = None) -> None:
        """Clock in the employee."""
        if self.is_clocked_in:
            raise ValueError("Employee is already clocked in")
        
        self.clock_in_time = clock_time or datetime.utcnow()
        self.status = TimeEntryStatus.CLOCKED_IN
        self.updated_at = datetime.utcnow()
    
    def clock_out(self, clock_time: Optional[datetime] = None) -> None:
        """Clock out the employee."""
        if not self.is_clocked_in:
            raise ValueError("Employee is not clocked in")
        
        self.clock_out_time = clock_time or datetime.utcnow()
        self.status = TimeEntryStatus.CLOCKED_OUT
        self.updated_at = datetime.utcnow()
        
        # Calculate hours automatically
        self.calculate_break_duration()
        self.calculate_hours()
    
    def start_break(self, break_time: Optional[datetime] = None) -> None:
        """Start a break period."""
        if not self.is_clocked_in:
            raise ValueError("Employee must be clocked in to start break")
        
        if self.is_on_break:
            raise ValueError("Employee is already on break")
        
        self.break_start_time = break_time or datetime.utcnow()
        self.status = TimeEntryStatus.ON_BREAK
        self.updated_at = datetime.utcnow()
    
    def end_break(self, break_time: Optional[datetime] = None) -> None:
        """End a break period."""
        if not self.is_on_break:
            raise ValueError("Employee is not on break")
        
        if self.break_start_time and not self.break_end_time:
            self.break_end_time = break_time or datetime.utcnow()
        elif self.lunch_start_time and not self.lunch_end_time:
            self.lunch_end_time = break_time or datetime.utcnow()
        
        self.status = TimeEntryStatus.CLOCKED_IN
        self.updated_at = datetime.utcnow()
    
    def start_lunch(self, lunch_time: Optional[datetime] = None) -> None:
        """Start lunch break."""
        if not self.is_clocked_in:
            raise ValueError("Employee must be clocked in to start lunch")
        
        if self.is_on_break:
            raise ValueError("Employee is already on break")
        
        self.lunch_start_time = lunch_time or datetime.utcnow()
        self.status = TimeEntryStatus.ON_BREAK
        self.updated_at = datetime.utcnow()
    
    def submit_for_approval(self) -> None:
        """Submit time entry for approval."""
        if not self.is_complete:
            raise ValueError("Time entry must be complete before submission")
        
        self.status = TimeEntryStatus.SUBMITTED
        self.approval_status = ApprovalStatus.PENDING
        self.submitted_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def approve(self, approved_by_id: int, notes: Optional[str] = None) -> None:
        """Approve the time entry."""
        self.approval_status = ApprovalStatus.APPROVED
        self.approved_by = approved_by_id
        self.approved_at = datetime.utcnow()
        self.status = TimeEntryStatus.APPROVED
        if notes:
            self.admin_notes = notes
        self.updated_at = datetime.utcnow()
    
    def reject(self, approved_by_id: int, reason: str) -> None:
        """Reject the time entry."""
        self.approval_status = ApprovalStatus.REJECTED
        self.approved_by = approved_by_id
        self.approved_at = datetime.utcnow()
        self.rejection_reason = reason
        self.status = TimeEntryStatus.REJECTED
        self.updated_at = datetime.utcnow()
    
    def is_valid_for_payroll(self) -> bool:
        """Check if time entry is valid for payroll processing."""
        return (
            self.approval_status == ApprovalStatus.APPROVED and
            self.is_complete and
            self.total_hours is not None and
            self.total_hours > 0
        ) 