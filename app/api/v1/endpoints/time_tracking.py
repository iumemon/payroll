"""
Time Tracking API endpoints.

This module provides API endpoints for time tracking operations including
clock in/out, break management, time entry CRUD, approval workflow, and reporting.
"""

from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.employee import Employee
from app.models.time_entry import TimeEntry
from app.models.enums import TimeEntryStatus, TimeEntryType, ApprovalStatus
from app.services.time_tracking_service import TimeTrackingService
from app.schemas.time_entry import (
    TimeEntryCreate, TimeEntryUpdate, TimeEntryResponse, TimeEntryList,
    TimeEntrySummary, TimeEntryStats, ClockInRequest, ClockOutRequest,
    BreakRequest, TimeEntryApproval, EmployeeTimeReport
)

router = APIRouter()


def get_time_tracking_service(db: Session = Depends(get_db)) -> TimeTrackingService:
    """Get time tracking service instance."""
    return TimeTrackingService(db)


def get_current_employee(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Employee:
    """Get current employee from current user."""
    employee = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found"
        )
    return employee


@router.post("/clock-in", response_model=TimeEntryResponse)
def clock_in(
    clock_in_data: ClockInRequest,
    service: TimeTrackingService = Depends(get_time_tracking_service),
    current_user: User = Depends(get_current_user)
):
    """Clock in an employee."""
    # For now, allow any user to clock in any employee
    # In a real system, you'd check permissions here
    time_entry = service.clock_in(clock_in_data)
    return service._time_entry_to_response(time_entry)


@router.post("/clock-out", response_model=TimeEntryResponse)
def clock_out(
    clock_out_data: ClockOutRequest,
    service: TimeTrackingService = Depends(get_time_tracking_service),
    current_user: User = Depends(get_current_user)
):
    """Clock out an employee."""
    time_entry = service.clock_out(clock_out_data)
    return service._time_entry_to_response(time_entry)


@router.post("/start-break", response_model=TimeEntryResponse)
def start_break(
    break_data: BreakRequest,
    service: TimeTrackingService = Depends(get_time_tracking_service),
    current_user: User = Depends(get_current_user)
):
    """Start a break for an employee."""
    time_entry = service.start_break(break_data)
    return service._time_entry_to_response(time_entry)


@router.post("/end-break", response_model=TimeEntryResponse)
def end_break(
    break_data: BreakRequest,
    service: TimeTrackingService = Depends(get_time_tracking_service),
    current_user: User = Depends(get_current_user)
):
    """End a break for an employee."""
    time_entry = service.end_break(break_data)
    return service._time_entry_to_response(time_entry)


@router.post("/", response_model=TimeEntryResponse)
def create_time_entry(
    time_entry_data: TimeEntryCreate,
    service: TimeTrackingService = Depends(get_time_tracking_service),
    current_user: User = Depends(get_current_user)
):
    """Create a new time entry."""
    time_entry = service.create_time_entry(time_entry_data)
    return service._time_entry_to_response(time_entry)


@router.get("/", response_model=TimeEntryList)
def get_time_entries(
    employee_id: Optional[int] = Query(None, description="Filter by employee ID"),
    work_date: Optional[date] = Query(None, description="Filter by work date"),
    start_date: Optional[date] = Query(None, description="Filter by start date"),
    end_date: Optional[date] = Query(None, description="Filter by end date"),
    status: Optional[TimeEntryStatus] = Query(None, description="Filter by status"),
    approval_status: Optional[ApprovalStatus] = Query(None, description="Filter by approval status"),
    entry_type: Optional[TimeEntryType] = Query(None, description="Filter by entry type"),
    department: Optional[str] = Query(None, description="Filter by department"),
    project_code: Optional[str] = Query(None, description="Filter by project code"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    service: TimeTrackingService = Depends(get_time_tracking_service),
    current_user: User = Depends(get_current_user)
):
    """Get time entries with filtering and pagination."""
    return service.get_time_entries(
        employee_id=employee_id,
        work_date=work_date,
        start_date=start_date,
        end_date=end_date,
        status=status,
        approval_status=approval_status,
        entry_type=entry_type,
        department=department,
        project_code=project_code,
        page=page,
        per_page=per_page
    )


@router.get("/{time_entry_id}", response_model=TimeEntryResponse)
def get_time_entry(
    time_entry_id: int,
    service: TimeTrackingService = Depends(get_time_tracking_service),
    current_user: User = Depends(get_current_user)
):
    """Get a specific time entry."""
    time_entry = service.get_time_entry(time_entry_id)
    if not time_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Time entry not found"
        )
    return service._time_entry_to_response(time_entry)


@router.put("/{time_entry_id}", response_model=TimeEntryResponse)
def update_time_entry(
    time_entry_id: int,
    update_data: TimeEntryUpdate,
    service: TimeTrackingService = Depends(get_time_tracking_service),
    current_user: User = Depends(get_current_user)
):
    """Update a time entry."""
    time_entry = service.update_time_entry(time_entry_id, update_data, current_user.id)
    return service._time_entry_to_response(time_entry)


@router.delete("/{time_entry_id}")
def delete_time_entry(
    time_entry_id: int,
    service: TimeTrackingService = Depends(get_time_tracking_service),
    current_user: User = Depends(get_current_user)
):
    """Delete a time entry."""
    success = service.delete_time_entry(time_entry_id)
    if success:
        return {"message": "Time entry deleted successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to delete time entry"
        )


@router.get("/employee/{employee_id}/current", response_model=TimeEntryResponse)
def get_employee_current_time_entry(
    employee_id: int,
    service: TimeTrackingService = Depends(get_time_tracking_service),
    current_user: User = Depends(get_current_user)
):
    """Get employee's current active time entry."""
    time_entry = service.get_employee_current_time_entry(employee_id)
    if not time_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active time entry found for employee"
        )
    return service._time_entry_to_response(time_entry)


@router.post("/submit-for-approval", response_model=List[TimeEntryResponse])
def submit_for_approval(
    time_entry_ids: List[int],
    service: TimeTrackingService = Depends(get_time_tracking_service),
    current_user: User = Depends(get_current_user)
):
    """Submit time entries for approval."""
    time_entries = service.submit_for_approval(time_entry_ids)
    return [service._time_entry_to_response(entry) for entry in time_entries]


@router.post("/approve", response_model=List[TimeEntryResponse])
def approve_time_entries(
    approval_data: TimeEntryApproval,
    service: TimeTrackingService = Depends(get_time_tracking_service),
    current_user: User = Depends(get_current_user)
):
    """Approve or reject time entries."""
    # Get current employee to use as approver
    current_employee = get_current_employee(current_user)
    time_entries = service.approve_time_entries(approval_data, current_employee.id)
    return [service._time_entry_to_response(entry) for entry in time_entries]


@router.get("/pending-approvals/manager/{manager_id}", response_model=List[TimeEntryResponse])
def get_pending_approvals(
    manager_id: int,
    service: TimeTrackingService = Depends(get_time_tracking_service),
    current_user: User = Depends(get_current_user)
):
    """Get time entries pending approval for a manager."""
    time_entries = service.get_pending_approvals(manager_id)
    return [service._time_entry_to_response(entry) for entry in time_entries]


@router.get("/stats", response_model=TimeEntryStats)
def get_time_entry_stats(
    start_date: Optional[date] = Query(None, description="Filter by start date"),
    end_date: Optional[date] = Query(None, description="Filter by end date"),
    department: Optional[str] = Query(None, description="Filter by department"),
    service: TimeTrackingService = Depends(get_time_tracking_service),
    current_user: User = Depends(get_current_user)
):
    """Get time entry statistics."""
    return service.get_time_entry_stats(
        start_date=start_date,
        end_date=end_date,
        department=department
    )


@router.get("/reports/employee/{employee_id}", response_model=EmployeeTimeReport)
def get_employee_time_report(
    employee_id: int,
    start_date: date = Query(..., description="Report start date"),
    end_date: date = Query(..., description="Report end date"),
    service: TimeTrackingService = Depends(get_time_tracking_service),
    current_user: User = Depends(get_current_user)
):
    """Get time report for a specific employee."""
    return service.get_employee_time_report(employee_id, start_date, end_date)


@router.get("/validate/{time_entry_id}")
def validate_time_entry(
    time_entry_id: int,
    service: TimeTrackingService = Depends(get_time_tracking_service),
    current_user: User = Depends(get_current_user)
):
    """Validate a time entry and return validation errors."""
    time_entry = service.get_time_entry(time_entry_id)
    if not time_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Time entry not found"
        )
    
    errors = service.validate_time_entry(time_entry)
    return {
        "time_entry_id": time_entry_id,
        "is_valid": len(errors) == 0,
        "errors": errors
    }


@router.get("/employee/{employee_id}/summary", response_model=List[TimeEntrySummary])
def get_employee_time_summary(
    employee_id: int,
    start_date: Optional[date] = Query(None, description="Filter by start date"),
    end_date: Optional[date] = Query(None, description="Filter by end date"),
    service: TimeTrackingService = Depends(get_time_tracking_service),
    current_user: User = Depends(get_current_user)
):
    """Get time entry summary for a specific employee."""
    time_entries = service.get_time_entries(
        employee_id=employee_id,
        start_date=start_date,
        end_date=end_date,
        per_page=1000  # Get all entries for summary
    )
    
    return [
        TimeEntrySummary(
            id=entry.id,
            employee_id=entry.employee_id,
            work_date=entry.work_date,
            status=entry.status,
            approval_status=entry.approval_status,
            total_hours=entry.total_hours,
            overtime_hours=entry.overtime_hours,
            entry_type=entry.entry_type
        )
        for entry in time_entries.time_entries
    ]


@router.get("/departments", response_model=List[str])
def get_departments(
    service: TimeTrackingService = Depends(get_time_tracking_service),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get list of departments with time entries."""
    departments = db.query(TimeEntry.department).filter(
        TimeEntry.department.isnot(None)
    ).distinct().all()
    
    return [dept[0] for dept in departments if dept[0]]


@router.get("/projects", response_model=List[str])
def get_projects(
    service: TimeTrackingService = Depends(get_time_tracking_service),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get list of project codes with time entries."""
    projects = db.query(TimeEntry.project_code).filter(
        TimeEntry.project_code.isnot(None)
    ).distinct().all()
    
    return [proj[0] for proj in projects if proj[0]]


@router.get("/dashboard/employee/{employee_id}")
def get_employee_dashboard(
    employee_id: int,
    service: TimeTrackingService = Depends(get_time_tracking_service),
    current_user: User = Depends(get_current_user)
):
    """Get dashboard data for a specific employee."""
    # Get current time entry
    current_entry = service.get_employee_current_time_entry(employee_id)
    
    # Get this week's time entries
    from datetime import timedelta
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    
    week_entries = service.get_time_entries(
        employee_id=employee_id,
        start_date=week_start,
        end_date=week_end,
        per_page=100
    )
    
    # Calculate week totals
    week_total_hours = sum(
        entry.total_hours or 0
        for entry in week_entries.time_entries
        if entry.total_hours
    )
    
    week_overtime_hours = sum(
        entry.overtime_hours or 0
        for entry in week_entries.time_entries
        if entry.overtime_hours
    )
    
    return {
        "employee_id": employee_id,
        "current_entry": service._time_entry_to_response(current_entry) if current_entry else None,
        "is_clocked_in": current_entry.is_clocked_in if current_entry else False,
        "is_on_break": current_entry.is_on_break if current_entry else False,
        "week_total_hours": week_total_hours,
        "week_overtime_hours": week_overtime_hours,
        "week_entries_count": len(week_entries.time_entries),
        "pending_approvals": len([
            entry for entry in week_entries.time_entries
            if entry.approval_status == ApprovalStatus.PENDING
        ])
    }


@router.get("/dashboard/manager/{manager_id}")
def get_manager_dashboard(
    manager_id: int,
    service: TimeTrackingService = Depends(get_time_tracking_service),
    current_user: User = Depends(get_current_user)
):
    """Get dashboard data for a manager."""
    # Get pending approvals
    pending_entries = service.get_pending_approvals(manager_id)
    
    # Get team stats for current week
    from datetime import timedelta
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    
    team_stats = service.get_time_entry_stats(
        start_date=week_start,
        end_date=week_end
    )
    
    return {
        "manager_id": manager_id,
        "pending_approvals_count": len(pending_entries),
        "pending_approvals": [
            service._time_entry_to_response(entry) for entry in pending_entries[:10]
        ],  # Limit to 10 most recent
        "team_stats": team_stats
    }


@router.post("/send-approval-reminders")
def send_approval_reminders(
    service: TimeTrackingService = Depends(get_time_tracking_service),
    current_user: User = Depends(get_current_user)
):
    """Send approval reminders for pending time entries."""
    result = service.send_approval_reminders()
    return result


@router.get("/notifications/manager/{manager_id}")
def get_manager_notification_summary(
    manager_id: int,
    service: TimeTrackingService = Depends(get_time_tracking_service),
    current_user: User = Depends(get_current_user)
):
    """Get notification summary for a manager."""
    return service.get_manager_notification_summary(manager_id)


@router.get("/notifications/pending")
def get_pending_notifications(
    service: TimeTrackingService = Depends(get_time_tracking_service),
    current_user: User = Depends(get_current_user)
):
    """Get pending notifications for current user."""
    # Get notifications from notification service
    notifications = service.notification_service.get_pending_notifications(current_user.id)
    return {
        "user_id": current_user.id,
        "notifications": notifications,
        "total_pending": len(notifications)
    }


@router.post("/notifications/{notification_id}/mark-read")
def mark_notification_as_read(
    notification_id: int,
    service: TimeTrackingService = Depends(get_time_tracking_service),
    current_user: User = Depends(get_current_user)
):
    """Mark a notification as read."""
    success = service.notification_service.mark_notification_as_read(notification_id, current_user.id)
    if success:
        return {"message": "Notification marked as read"}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to mark notification as read"
        ) 