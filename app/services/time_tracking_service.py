"""
Time Tracking Service Module.

This module provides business logic for time tracking operations including
clock in/out, break management, overtime calculations, and approval workflow.
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import and_, or_, func, desc, asc
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.time_entry import TimeEntry
from app.models.employee import Employee
from app.models.enums import TimeEntryStatus, TimeEntryType, ApprovalStatus, EmployeeStatus
from app.services.notification_service import NotificationService
from app.schemas.time_entry import (
    TimeEntryCreate, TimeEntryUpdate, TimeEntryResponse, TimeEntryList,
    TimeEntrySummary, TimeEntryStats, ClockInRequest, ClockOutRequest,
    BreakRequest, TimeEntryApproval, EmployeeTimeReport
)


class TimeTrackingService:
    """Service class for time tracking operations."""
    
    def __init__(self, db: Session):
        self.db = db
        self.notification_service = NotificationService(db)
    
    def create_time_entry(self, time_entry_data: TimeEntryCreate) -> TimeEntry:
        """Create a new time entry."""
        # Validate employee exists and is active
        employee = self.db.query(Employee).filter(
            Employee.id == time_entry_data.employee_id,
            Employee.status == EmployeeStatus.ACTIVE
        ).first()
        
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee not found or inactive"
            )
        
        # Check for duplicate entries on the same date
        existing_entry = self.db.query(TimeEntry).filter(
            TimeEntry.employee_id == time_entry_data.employee_id,
            TimeEntry.work_date == time_entry_data.work_date
        ).first()
        
        if existing_entry:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Time entry already exists for this employee on this date"
            )
        
        # Create time entry
        time_entry = TimeEntry(
            employee_id=time_entry_data.employee_id,
            work_date=time_entry_data.work_date,
            entry_type=time_entry_data.entry_type,
            clock_in_time=time_entry_data.clock_in_time,
            clock_out_time=time_entry_data.clock_out_time,
            break_start_time=time_entry_data.break_start_time,
            break_end_time=time_entry_data.break_end_time,
            lunch_start_time=time_entry_data.lunch_start_time,
            lunch_end_time=time_entry_data.lunch_end_time,
            location=time_entry_data.location,
            project_code=time_entry_data.project_code,
            department=time_entry_data.department or employee.department,
            notes=time_entry_data.notes,
            is_manual_entry=time_entry_data.is_manual_entry,
            manual_entry_reason=time_entry_data.manual_entry_reason,
            total_hours=time_entry_data.total_hours,
            regular_hours=time_entry_data.regular_hours,
            overtime_hours=time_entry_data.overtime_hours,
        )
        
        # If it's a complete entry, calculate hours automatically
        if time_entry.is_complete:
            time_entry.calculate_break_duration()
            time_entry.calculate_hours()
        
        self.db.add(time_entry)
        self.db.commit()
        self.db.refresh(time_entry)
        
        return time_entry
    
    def clock_in(self, clock_in_data: ClockInRequest) -> TimeEntry:
        """Clock in an employee."""
        # Validate employee exists and is active
        employee = self.db.query(Employee).filter(
            Employee.id == clock_in_data.employee_id,
            Employee.status == EmployeeStatus.ACTIVE
        ).first()
        
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee not found or inactive"
            )
        
        # Check if employee is already clocked in
        work_date = clock_in_data.work_date or date.today()
        existing_entry = self.db.query(TimeEntry).filter(
            TimeEntry.employee_id == clock_in_data.employee_id,
            TimeEntry.work_date == work_date,
            TimeEntry.status.in_([TimeEntryStatus.CLOCKED_IN, TimeEntryStatus.ON_BREAK])
        ).first()
        
        if existing_entry:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Employee is already clocked in"
            )
        
        # Create new time entry
        time_entry = TimeEntry(
            employee_id=clock_in_data.employee_id,
            work_date=work_date,
            location=clock_in_data.location,
            project_code=clock_in_data.project_code,
            department=employee.department,
            notes=clock_in_data.notes,
        )
        
        # Clock in
        time_entry.clock_in(clock_in_data.clock_in_time)
        
        self.db.add(time_entry)
        self.db.commit()
        self.db.refresh(time_entry)
        
        return time_entry
    
    def clock_out(self, clock_out_data: ClockOutRequest) -> TimeEntry:
        """Clock out an employee."""
        time_entry = self.db.query(TimeEntry).filter(
            TimeEntry.id == clock_out_data.time_entry_id
        ).first()
        
        if not time_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Time entry not found"
            )
        
        # Update notes if provided
        if clock_out_data.notes:
            time_entry.notes = clock_out_data.notes
        
        # Clock out
        try:
            time_entry.clock_out(clock_out_data.clock_out_time)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        
        self.db.commit()
        self.db.refresh(time_entry)
        
        return time_entry
    
    def start_break(self, break_data: BreakRequest) -> TimeEntry:
        """Start a break for an employee."""
        time_entry = self.db.query(TimeEntry).filter(
            TimeEntry.id == break_data.time_entry_id
        ).first()
        
        if not time_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Time entry not found"
            )
        
        try:
            if break_data.is_lunch:
                time_entry.start_lunch(break_data.break_time)
            else:
                time_entry.start_break(break_data.break_time)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        
        self.db.commit()
        self.db.refresh(time_entry)
        
        return time_entry
    
    def end_break(self, break_data: BreakRequest) -> TimeEntry:
        """End a break for an employee."""
        time_entry = self.db.query(TimeEntry).filter(
            TimeEntry.id == break_data.time_entry_id
        ).first()
        
        if not time_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Time entry not found"
            )
        
        try:
            time_entry.end_break(break_data.break_time)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        
        self.db.commit()
        self.db.refresh(time_entry)
        
        return time_entry
    
    def get_time_entry(self, time_entry_id: int) -> Optional[TimeEntry]:
        """Get a specific time entry by ID."""
        return self.db.query(TimeEntry).filter(TimeEntry.id == time_entry_id).first()
    
    def get_time_entries(
        self,
        employee_id: Optional[int] = None,
        work_date: Optional[date] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        status: Optional[TimeEntryStatus] = None,
        approval_status: Optional[ApprovalStatus] = None,
        entry_type: Optional[TimeEntryType] = None,
        department: Optional[str] = None,
        project_code: Optional[str] = None,
        page: int = 1,
        per_page: int = 10,
    ) -> TimeEntryList:
        """Get time entries with filtering and pagination."""
        query = self.db.query(TimeEntry)
        
        # Apply filters
        if employee_id:
            query = query.filter(TimeEntry.employee_id == employee_id)
        
        if work_date:
            query = query.filter(TimeEntry.work_date == work_date)
        
        if start_date:
            query = query.filter(TimeEntry.work_date >= start_date)
        
        if end_date:
            query = query.filter(TimeEntry.work_date <= end_date)
        
        if status:
            query = query.filter(TimeEntry.status == status)
        
        if approval_status:
            query = query.filter(TimeEntry.approval_status == approval_status)
        
        if entry_type:
            query = query.filter(TimeEntry.entry_type == entry_type)
        
        if department:
            query = query.filter(TimeEntry.department == department)
        
        if project_code:
            query = query.filter(TimeEntry.project_code == project_code)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * per_page
        time_entries = query.order_by(desc(TimeEntry.work_date), desc(TimeEntry.created_at)).offset(offset).limit(per_page).all()
        
        # Calculate pagination info
        pages = (total + per_page - 1) // per_page
        
        return TimeEntryList(
            time_entries=[self._time_entry_to_response(entry) for entry in time_entries],
            total=total,
            page=page,
            per_page=per_page,
            pages=pages
        )
    
    def update_time_entry(self, time_entry_id: int, update_data: TimeEntryUpdate, updater_id: int) -> TimeEntry:
        """Update a time entry."""
        time_entry = self.db.query(TimeEntry).filter(TimeEntry.id == time_entry_id).first()
        
        if not time_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Time entry not found"
            )
        
        # Check if time entry can be updated
        if time_entry.approval_status == ApprovalStatus.APPROVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot update approved time entry"
            )
        
        # Update fields
        update_fields = update_data.model_dump(exclude_unset=True)
        
        # Handle adjustments
        if update_data.adjusted_hours is not None:
            time_entry.adjusted_hours = update_data.adjusted_hours
            time_entry.adjustment_reason = update_data.adjustment_reason
            time_entry.adjusted_by = updater_id
            time_entry.adjusted_at = datetime.utcnow()
        
        # Update other fields
        for field, value in update_fields.items():
            if field not in ['adjusted_hours', 'adjustment_reason']:
                setattr(time_entry, field, value)
        
        # Recalculate hours if time fields changed
        if any(field in update_fields for field in ['clock_in_time', 'clock_out_time', 'break_start_time', 'break_end_time', 'lunch_start_time', 'lunch_end_time']):
            if time_entry.is_complete:
                time_entry.calculate_break_duration()
                time_entry.calculate_hours()
        
        time_entry.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(time_entry)
        
        return time_entry
    
    def delete_time_entry(self, time_entry_id: int) -> bool:
        """Delete a time entry."""
        time_entry = self.db.query(TimeEntry).filter(TimeEntry.id == time_entry_id).first()
        
        if not time_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Time entry not found"
            )
        
        # Check if time entry can be deleted
        if time_entry.approval_status == ApprovalStatus.APPROVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete approved time entry"
            )
        
        self.db.delete(time_entry)
        self.db.commit()
        
        return True
    
    def submit_for_approval(self, time_entry_ids: List[int]) -> List[TimeEntry]:
        """Submit time entries for approval."""
        time_entries = self.db.query(TimeEntry).filter(TimeEntry.id.in_(time_entry_ids)).all()
        
        if len(time_entries) != len(time_entry_ids):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or more time entries not found"
            )
        
        updated_entries = []
        for time_entry in time_entries:
            try:
                time_entry.submit_for_approval()
                updated_entries.append(time_entry)
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot submit time entry {time_entry.id}: {str(e)}"
                )
        
        self.db.commit()
        
        # Send notifications to managers
        self._notify_managers_of_submissions(updated_entries)
        
        return updated_entries
    
    def approve_time_entries(self, approval_data: TimeEntryApproval, approver_id: int) -> List[TimeEntry]:
        """Approve or reject time entries."""
        time_entries = self.db.query(TimeEntry).filter(TimeEntry.id.in_(approval_data.time_entry_ids)).all()
        
        if len(time_entries) != len(approval_data.time_entry_ids):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or more time entries not found"
            )
        
        updated_entries = []
        for time_entry in time_entries:
            if approval_data.approval_status == ApprovalStatus.APPROVED:
                time_entry.approve(approver_id, approval_data.notes)
            elif approval_data.approval_status == ApprovalStatus.REJECTED:
                time_entry.reject(approver_id, approval_data.rejection_reason)
            
            updated_entries.append(time_entry)
        
        self.db.commit()
        
        # Send notifications to employees
        self._notify_employees_of_approval_decision(updated_entries, approver_id, approval_data)
        
        return updated_entries
    
    def get_employee_current_time_entry(self, employee_id: int) -> Optional[TimeEntry]:
        """Get employee's current active time entry."""
        return self.db.query(TimeEntry).filter(
            TimeEntry.employee_id == employee_id,
            TimeEntry.status.in_([TimeEntryStatus.CLOCKED_IN, TimeEntryStatus.ON_BREAK])
        ).first()
    
    def get_time_entry_stats(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        department: Optional[str] = None
    ) -> TimeEntryStats:
        """Get time entry statistics."""
        query = self.db.query(TimeEntry)
        
        # Apply filters
        if start_date:
            query = query.filter(TimeEntry.work_date >= start_date)
        
        if end_date:
            query = query.filter(TimeEntry.work_date <= end_date)
        
        if department:
            query = query.filter(TimeEntry.department == department)
        
        # Get counts
        total_entries = query.count()
        pending_approval = query.filter(TimeEntry.approval_status == ApprovalStatus.PENDING).count()
        approved_entries = query.filter(TimeEntry.approval_status == ApprovalStatus.APPROVED).count()
        rejected_entries = query.filter(TimeEntry.approval_status == ApprovalStatus.REJECTED).count()
        
        # Get hour totals
        hour_totals = query.with_entities(
            func.sum(TimeEntry.total_hours).label('total_hours'),
            func.sum(TimeEntry.regular_hours).label('regular_hours'),
            func.sum(TimeEntry.overtime_hours).label('overtime_hours')
        ).first()
        
        # Get unique employee count
        employees_with_entries = query.with_entities(TimeEntry.employee_id).distinct().count()
        
        return TimeEntryStats(
            total_entries=total_entries,
            pending_approval=pending_approval,
            approved_entries=approved_entries,
            rejected_entries=rejected_entries,
            total_hours=hour_totals.total_hours or Decimal('0.00'),
            regular_hours=hour_totals.regular_hours or Decimal('0.00'),
            overtime_hours=hour_totals.overtime_hours or Decimal('0.00'),
            employees_with_entries=employees_with_entries
        )
    
    def get_employee_time_report(
        self,
        employee_id: int,
        start_date: date,
        end_date: date
    ) -> EmployeeTimeReport:
        """Get time report for a specific employee."""
        employee = self.db.query(Employee).filter(Employee.id == employee_id).first()
        
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee not found"
            )
        
        # Get time entries for the period
        time_entries = self.db.query(TimeEntry).filter(
            TimeEntry.employee_id == employee_id,
            TimeEntry.work_date >= start_date,
            TimeEntry.work_date <= end_date
        ).all()
        
        # Calculate totals
        total_entries = len(time_entries)
        total_hours = sum(entry.total_hours or Decimal('0.00') for entry in time_entries)
        regular_hours = sum(entry.regular_hours or Decimal('0.00') for entry in time_entries)
        overtime_hours = sum(entry.overtime_hours or Decimal('0.00') for entry in time_entries)
        
        # Calculate days worked
        days_worked = len(set(entry.work_date for entry in time_entries))
        
        # Calculate average hours per day
        average_hours_per_day = total_hours / days_worked if days_worked > 0 else Decimal('0.00')
        
        return EmployeeTimeReport(
            employee_id=employee_id,
            employee_name=employee.full_name,
            date_range=f"{start_date} to {end_date}",
            total_entries=total_entries,
            total_hours=total_hours,
            regular_hours=regular_hours,
            overtime_hours=overtime_hours,
            average_hours_per_day=average_hours_per_day,
            days_worked=days_worked
        )
    
    def validate_time_entry(self, time_entry: TimeEntry) -> List[str]:
        """Validate time entry and return list of validation errors."""
        errors = []
        
        # Check for overlapping time entries
        overlapping_entries = self.db.query(TimeEntry).filter(
            TimeEntry.employee_id == time_entry.employee_id,
            TimeEntry.work_date == time_entry.work_date,
            TimeEntry.id != time_entry.id
        ).all()
        
        if overlapping_entries:
            errors.append("Overlapping time entry exists for this date")
        
        # Check maximum hours per day
        if time_entry.total_hours and time_entry.total_hours > 24:
            errors.append("Total hours cannot exceed 24 hours per day")
        
        # Check break duration
        if time_entry.break_duration and time_entry.break_duration > 4:
            errors.append("Break duration cannot exceed 4 hours")
        
        # Check if clock out is after clock in
        if time_entry.clock_in_time and time_entry.clock_out_time:
            if time_entry.clock_out_time <= time_entry.clock_in_time:
                errors.append("Clock out time must be after clock in time")
        
        # Check break times
        if time_entry.break_start_time and time_entry.break_end_time:
            if time_entry.break_end_time <= time_entry.break_start_time:
                errors.append("Break end time must be after break start time")
        
        # Check lunch times
        if time_entry.lunch_start_time and time_entry.lunch_end_time:
            if time_entry.lunch_end_time <= time_entry.lunch_start_time:
                errors.append("Lunch end time must be after lunch start time")
        
        return errors
    
    def get_pending_approvals(self, manager_id: int) -> List[TimeEntry]:
        """Get time entries pending approval for a manager."""
        # Get employees managed by this manager
        managed_employees = self.db.query(Employee).filter(Employee.manager_id == manager_id).all()
        employee_ids = [emp.id for emp in managed_employees]
        
        if not employee_ids:
            return []
        
        # Get pending time entries for managed employees
        pending_entries = self.db.query(TimeEntry).filter(
            TimeEntry.employee_id.in_(employee_ids),
            TimeEntry.approval_status == ApprovalStatus.PENDING
        ).order_by(TimeEntry.work_date.desc()).all()
        
        return pending_entries
    
    def _time_entry_to_response(self, time_entry: TimeEntry) -> TimeEntryResponse:
        """Convert TimeEntry model to TimeEntryResponse schema."""
        return TimeEntryResponse(
            id=time_entry.id,
            employee_id=time_entry.employee_id,
            work_date=time_entry.work_date,
            entry_type=time_entry.entry_type,
            status=time_entry.status,
            approval_status=time_entry.approval_status,
            clock_in_time=time_entry.clock_in_time,
            clock_out_time=time_entry.clock_out_time,
            break_start_time=time_entry.break_start_time,
            break_end_time=time_entry.break_end_time,
            lunch_start_time=time_entry.lunch_start_time,
            lunch_end_time=time_entry.lunch_end_time,
            total_hours=time_entry.total_hours,
            regular_hours=time_entry.regular_hours,
            overtime_hours=time_entry.overtime_hours,
            double_time_hours=time_entry.double_time_hours,
            break_duration=time_entry.break_duration,
            lunch_duration=time_entry.lunch_duration,
            location=time_entry.location,
            project_code=time_entry.project_code,
            department=time_entry.department,
            notes=time_entry.notes,
            approved_by=time_entry.approved_by,
            approved_at=time_entry.approved_at,
            rejection_reason=time_entry.rejection_reason,
            is_manual_entry=time_entry.is_manual_entry,
            manual_entry_reason=time_entry.manual_entry_reason,
            adjusted_hours=time_entry.adjusted_hours,
            adjustment_reason=time_entry.adjustment_reason,
            adjusted_by=time_entry.adjusted_by,
            adjusted_at=time_entry.adjusted_at,
            admin_notes=time_entry.admin_notes,
            created_at=time_entry.created_at,
            updated_at=time_entry.updated_at,
            submitted_at=time_entry.submitted_at,
            is_clocked_in=time_entry.is_clocked_in,
            is_on_break=time_entry.is_on_break,
            is_complete=time_entry.is_complete,
            worked_duration_hours=time_entry.worked_duration_hours
        )
    
    def _notify_managers_of_submissions(self, time_entries: List[TimeEntry]) -> None:
        """Send notifications to managers about submitted time entries."""
        try:
            # Group time entries by manager
            manager_entries = {}
            for time_entry in time_entries:
                if time_entry.employee and time_entry.employee.manager_id:
                    manager_id = time_entry.employee.manager_id
                    if manager_id not in manager_entries:
                        manager_entries[manager_id] = []
                    manager_entries[manager_id].append(time_entry)
            
            # Send notifications to each manager
            for manager_id, entries in manager_entries.items():
                manager = self.db.query(Employee).filter(Employee.id == manager_id).first()
                if manager:
                    self.notification_service.notify_manager_of_submission(entries, manager)
                    
        except Exception as e:
            # Log error but don't fail the operation
            logger.error(f"Error sending manager notifications: {e}")
    
    def _notify_employees_of_approval_decision(
        self, 
        time_entries: List[TimeEntry], 
        approver_id: int, 
        approval_data: TimeEntryApproval
    ) -> None:
        """Send notifications to employees about approval decisions."""
        try:
            approver = self.db.query(Employee).filter(Employee.id == approver_id).first()
            if not approver:
                return
            
            # Group time entries by employee
            employee_entries = {}
            for time_entry in time_entries:
                if time_entry.employee_id not in employee_entries:
                    employee_entries[time_entry.employee_id] = []
                employee_entries[time_entry.employee_id].append(time_entry)
            
            # Send notifications to each employee
            for employee_id, entries in employee_entries.items():
                employee = self.db.query(Employee).filter(Employee.id == employee_id).first()
                if employee:
                    if approval_data.approval_status == ApprovalStatus.APPROVED:
                        self.notification_service.notify_employee_of_approval(entries, employee, approver)
                    elif approval_data.approval_status == ApprovalStatus.REJECTED:
                        self.notification_service.notify_employee_of_rejection(
                            entries, employee, approver, approval_data.rejection_reason
                        )
                        
        except Exception as e:
            # Log error but don't fail the operation
            logger.error(f"Error sending employee notifications: {e}")
    
    def send_approval_reminders(self) -> Dict[str, Any]:
        """Send approval reminders for pending time entries."""
        try:
            return self.notification_service.send_reminder_notifications()
            
        except Exception as e:
            logger.error(f"Error sending approval reminders: {e}")
            return {"error": str(e)}
    
    def get_manager_notification_summary(self, manager_id: int) -> Dict[str, Any]:
        """Get notification summary for a manager."""
        try:
            pending_entries = self.get_pending_approvals(manager_id)
            
            # Group by employee
            employee_summaries = {}
            for entry in pending_entries:
                employee_id = entry.employee_id
                if employee_id not in employee_summaries:
                    employee_summaries[employee_id] = {
                        "employee_id": employee_id,
                        "employee_name": entry.employee.full_name if entry.employee else "Unknown",
                        "entries_count": 0,
                        "total_hours": 0,
                        "oldest_submission": None
                    }
                
                employee_summaries[employee_id]["entries_count"] += 1
                employee_summaries[employee_id]["total_hours"] += float(entry.total_hours or 0)
                
                if entry.submitted_at:
                    if (employee_summaries[employee_id]["oldest_submission"] is None or 
                        entry.submitted_at < employee_summaries[employee_id]["oldest_submission"]):
                        employee_summaries[employee_id]["oldest_submission"] = entry.submitted_at
            
            return {
                "manager_id": manager_id,
                "total_pending_entries": len(pending_entries),
                "employees_with_pending": len(employee_summaries),
                "employee_summaries": list(employee_summaries.values())
            }
            
        except Exception as e:
            logger.error(f"Error getting manager notification summary: {e}")
            return {"error": str(e)} 