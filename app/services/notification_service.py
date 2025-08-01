"""
Notification Service Module.

This module provides notification capabilities for the time tracking approval workflow,
including email notifications, system notifications, and audit logging.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.employee import Employee
from app.models.time_entry import TimeEntry
from app.models.enums import TimeEntryStatus, ApprovalStatus

logger = logging.getLogger(__name__)


class NotificationService:
    """Service class for managing notifications."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def notify_manager_of_submission(
        self, 
        time_entries: List[TimeEntry], 
        manager: Employee
    ) -> bool:
        """Notify manager of time entries submitted for approval."""
        try:
            # Get unique employees from time entries
            employee_ids = list(set(entry.employee_id for entry in time_entries))
            employees = self.db.query(Employee).filter(Employee.id.in_(employee_ids)).all()
            
            # Create notification data
            notification_data = {
                "manager_id": manager.id,
                "manager_name": manager.full_name,
                "manager_email": manager.email,
                "time_entries_count": len(time_entries),
                "employees": [
                    {
                        "employee_id": emp.id,
                        "employee_name": emp.full_name,
                        "employee_email": emp.email,
                        "entries_count": len([entry for entry in time_entries if entry.employee_id == emp.id])
                    }
                    for emp in employees
                ],
                "submission_date": datetime.utcnow(),
                "notification_type": "time_entry_submission"
            }
            
            # Log notification
            logger.info(f"Notifying manager {manager.full_name} of {len(time_entries)} time entries for approval")
            
            # In a real system, you would send an email here
            # For now, we'll just log it
            self._log_notification(notification_data)
            
            return True
            
        except Exception as e:
            logger.error(f"Error notifying manager of submission: {e}")
            return False
    
    def notify_employee_of_approval(
        self, 
        time_entries: List[TimeEntry], 
        employee: Employee, 
        approver: Employee
    ) -> bool:
        """Notify employee of time entry approval."""
        try:
            # Calculate total hours approved
            total_hours = sum(entry.total_hours or 0 for entry in time_entries)
            
            notification_data = {
                "employee_id": employee.id,
                "employee_name": employee.full_name,
                "employee_email": employee.email,
                "approver_id": approver.id,
                "approver_name": approver.full_name,
                "time_entries_count": len(time_entries),
                "total_hours": float(total_hours),
                "approval_date": datetime.utcnow(),
                "notification_type": "time_entry_approval"
            }
            
            logger.info(f"Notifying employee {employee.full_name} of {len(time_entries)} approved time entries")
            
            self._log_notification(notification_data)
            
            return True
            
        except Exception as e:
            logger.error(f"Error notifying employee of approval: {e}")
            return False
    
    def notify_employee_of_rejection(
        self, 
        time_entries: List[TimeEntry], 
        employee: Employee, 
        approver: Employee, 
        rejection_reason: str
    ) -> bool:
        """Notify employee of time entry rejection."""
        try:
            notification_data = {
                "employee_id": employee.id,
                "employee_name": employee.full_name,
                "employee_email": employee.email,
                "approver_id": approver.id,
                "approver_name": approver.full_name,
                "time_entries_count": len(time_entries),
                "rejection_reason": rejection_reason,
                "rejection_date": datetime.utcnow(),
                "notification_type": "time_entry_rejection"
            }
            
            logger.info(f"Notifying employee {employee.full_name} of {len(time_entries)} rejected time entries")
            
            self._log_notification(notification_data)
            
            return True
            
        except Exception as e:
            logger.error(f"Error notifying employee of rejection: {e}")
            return False
    
    def notify_admin_of_anomaly(
        self, 
        time_entry: TimeEntry, 
        anomaly_type: str, 
        details: str
    ) -> bool:
        """Notify administrators of time entry anomalies."""
        try:
            notification_data = {
                "time_entry_id": time_entry.id,
                "employee_id": time_entry.employee_id,
                "employee_name": time_entry.employee.full_name if time_entry.employee else "Unknown",
                "anomaly_type": anomaly_type,
                "details": details,
                "work_date": time_entry.work_date,
                "detection_date": datetime.utcnow(),
                "notification_type": "time_entry_anomaly"
            }
            
            logger.warning(f"Time entry anomaly detected: {anomaly_type} for employee {time_entry.employee_id}")
            
            self._log_notification(notification_data)
            
            return True
            
        except Exception as e:
            logger.error(f"Error notifying admin of anomaly: {e}")
            return False
    
    def notify_payroll_of_approved_entries(
        self, 
        time_entries: List[TimeEntry], 
        pay_period_start: datetime, 
        pay_period_end: datetime
    ) -> bool:
        """Notify payroll team of approved time entries ready for processing."""
        try:
            # Group by employee
            employee_data = {}
            for entry in time_entries:
                if entry.employee_id not in employee_data:
                    employee_data[entry.employee_id] = {
                        "employee_id": entry.employee_id,
                        "employee_name": entry.employee.full_name if entry.employee else "Unknown",
                        "entries_count": 0,
                        "total_hours": 0,
                        "total_overtime": 0
                    }
                
                employee_data[entry.employee_id]["entries_count"] += 1
                employee_data[entry.employee_id]["total_hours"] += float(entry.total_hours or 0)
                employee_data[entry.employee_id]["total_overtime"] += float(entry.overtime_hours or 0)
            
            notification_data = {
                "pay_period_start": pay_period_start,
                "pay_period_end": pay_period_end,
                "total_entries": len(time_entries),
                "total_employees": len(employee_data),
                "employee_data": list(employee_data.values()),
                "notification_date": datetime.utcnow(),
                "notification_type": "payroll_ready"
            }
            
            logger.info(f"Notifying payroll team of {len(time_entries)} approved time entries for {len(employee_data)} employees")
            
            self._log_notification(notification_data)
            
            return True
            
        except Exception as e:
            logger.error(f"Error notifying payroll team: {e}")
            return False
    
    def get_pending_notifications(self, user_id: int) -> List[Dict[str, Any]]:
        """Get pending notifications for a user."""
        try:
            # In a real system, you would query a notifications table
            # For now, we'll return mock data
            return [
                {
                    "id": 1,
                    "type": "time_entry_submission",
                    "title": "Time Entries Pending Approval",
                    "message": "You have 5 time entries pending approval",
                    "created_at": datetime.utcnow(),
                    "is_read": False
                }
            ]
            
        except Exception as e:
            logger.error(f"Error getting pending notifications: {e}")
            return []
    
    def mark_notification_as_read(self, notification_id: int, user_id: int) -> bool:
        """Mark a notification as read."""
        try:
            # In a real system, you would update the notification status
            logger.info(f"Marking notification {notification_id} as read for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error marking notification as read: {e}")
            return False
    
    def send_reminder_notifications(self) -> Dict[str, Any]:
        """Send reminder notifications for pending approvals."""
        try:
            # Get all pending time entries older than 24 hours
            from datetime import timedelta
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            
            pending_entries = self.db.query(TimeEntry).filter(
                TimeEntry.approval_status == ApprovalStatus.PENDING,
                TimeEntry.submitted_at < cutoff_time
            ).all()
            
            if not pending_entries:
                return {"reminders_sent": 0, "managers_notified": 0}
            
            # Group by manager
            manager_entries = {}
            for entry in pending_entries:
                manager_id = entry.employee.manager_id if entry.employee else None
                if manager_id:
                    if manager_id not in manager_entries:
                        manager_entries[manager_id] = []
                    manager_entries[manager_id].append(entry)
            
            reminders_sent = 0
            managers_notified = 0
            
            for manager_id, entries in manager_entries.items():
                manager = self.db.query(Employee).filter(Employee.id == manager_id).first()
                if manager:
                    # Send reminder
                    self._send_approval_reminder(manager, entries)
                    reminders_sent += len(entries)
                    managers_notified += 1
            
            logger.info(f"Sent {reminders_sent} reminder notifications to {managers_notified} managers")
            
            return {
                "reminders_sent": reminders_sent,
                "managers_notified": managers_notified,
                "total_pending_entries": len(pending_entries)
            }
            
        except Exception as e:
            logger.error(f"Error sending reminder notifications: {e}")
            return {"reminders_sent": 0, "managers_notified": 0, "error": str(e)}
    
    def _send_approval_reminder(self, manager: Employee, time_entries: List[TimeEntry]) -> bool:
        """Send approval reminder to manager."""
        try:
            notification_data = {
                "manager_id": manager.id,
                "manager_name": manager.full_name,
                "manager_email": manager.email,
                "time_entries_count": len(time_entries),
                "pending_since": min(entry.submitted_at for entry in time_entries if entry.submitted_at),
                "reminder_date": datetime.utcnow(),
                "notification_type": "approval_reminder"
            }
            
            logger.info(f"Sending approval reminder to manager {manager.full_name} for {len(time_entries)} entries")
            
            self._log_notification(notification_data)
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending approval reminder: {e}")
            return False
    
    def _log_notification(self, notification_data: Dict[str, Any]) -> None:
        """Log notification data for audit purposes."""
        try:
            # In a real system, you would save this to a notifications table
            logger.info(f"Notification logged: {notification_data['notification_type']}")
            
        except Exception as e:
            logger.error(f"Error logging notification: {e}")
    
    def _send_email_notification(self, email: str, subject: str, body: str) -> bool:
        """Send email notification (placeholder for actual email service)."""
        try:
            # In a real system, you would integrate with an email service
            logger.info(f"Email notification sent to {email}: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email notification: {e}")
            return False 