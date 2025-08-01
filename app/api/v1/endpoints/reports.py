"""
Reports API endpoints.

This module provides API endpoints for report generation and management
including payroll reports, employee reports, compliance reports, and time tracking reports.
"""

import logging
from datetime import date, datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_admin
from app.models.user import User
from app.models.enums import ReportType, ReportFormat, ReportPeriod
from app.services.reporting_service import ReportingService
from app.schemas.reports import (
    ReportRequest, ReportResponse, ReportListResponse,
    PayRegisterReport, TaxLiabilityReport, EmployeeRosterReport,
    SalaryAnalysisReport, ComplianceReport, TimeSummaryReport
)

router = APIRouter()
logger = logging.getLogger(__name__)


def get_reporting_service(db: Session = Depends(get_db)) -> ReportingService:
    """Get reporting service instance."""
    return ReportingService(db)


@router.post("/generate", response_model=ReportResponse)
async def generate_report(
    request: ReportRequest,
    background_tasks: BackgroundTasks,
    service: ReportingService = Depends(get_reporting_service),
    current_user: User = Depends(get_current_user)
):
    """
    Generate a new report.
    
    **Required permissions**: Any authenticated user
    
    **Features**:
    - Generate various report types (payroll, employee, compliance, time tracking)
    - Apply filters and date ranges
    - Support multiple output formats
    - Background processing for large reports
    """
    try:
        # Generate report
        report_response = service.generate_report(request, current_user.id)
        
        logger.info(f"Report generated: {report_response.metadata.report_id} by user {current_user.id}")
        
        return report_response
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/types")
async def get_available_report_types(
    service: ReportingService = Depends(get_reporting_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get available report types.
    
    **Required permissions**: Any authenticated user
    
    **Features**:
    - List all available report types
    - Include descriptions and categories
    - Help users choose appropriate reports
    """
    try:
        report_types = service.get_available_report_types()
        
        return {
            "available_types": report_types,
            "total_types": len(report_types),
            "categories": list(set(rt["category"] for rt in report_types))
        }
        
    except Exception as e:
        logger.error(f"Error getting report types: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# Specific Report Type Endpoints

@router.post("/payroll/pay-register", response_model=PayRegisterReport)
async def generate_pay_register_report(
    start_date: date = Query(..., description="Start date for report"),
    end_date: date = Query(..., description="End date for report"),
    department: Optional[str] = Query(None, description="Filter by department"),
    employee_ids: Optional[List[int]] = Query(None, description="Filter by employee IDs"),
    include_terminated: bool = Query(False, description="Include terminated employees"),
    service: ReportingService = Depends(get_reporting_service),
    current_user: User = Depends(get_current_user)
):
    """
    Generate pay register report.
    
    **Required permissions**: Any authenticated user
    
    **Features**:
    - Detailed payroll register with earnings and deductions
    - Filter by department, employees, and date range
    - Include summary statistics
    """
    try:
        request = ReportRequest(
            report_type=ReportType.PAY_REGISTER,
            report_period=ReportPeriod.CUSTOM,
            start_date=start_date,
            end_date=end_date,
            department=department,
            employee_ids=employee_ids,
            include_terminated=include_terminated
        )
        
        report_response = service.generate_report(request, current_user.id)
        return report_response.data
        
    except Exception as e:
        logger.error(f"Error generating pay register report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/payroll/tax-liability", response_model=TaxLiabilityReport)
async def generate_tax_liability_report(
    start_date: date = Query(..., description="Start date for report"),
    end_date: date = Query(..., description="End date for report"),
    department: Optional[str] = Query(None, description="Filter by department"),
    include_detailed_breakdown: bool = Query(True, description="Include detailed breakdown"),
    service: ReportingService = Depends(get_reporting_service),
    current_user: User = Depends(get_current_user)
):
    """
    Generate tax liability report.
    
    **Required permissions**: Any authenticated user
    
    **Features**:
    - Tax liability summary and breakdowns
    - Employee and employer tax calculations
    - Department-wise breakdown
    """
    try:
        request = ReportRequest(
            report_type=ReportType.TAX_LIABILITY,
            report_period=ReportPeriod.CUSTOM,
            start_date=start_date,
            end_date=end_date,
            department=department,
            include_detailed_breakdown=include_detailed_breakdown
        )
        
        report_response = service.generate_report(request, current_user.id)
        return report_response.data
        
    except Exception as e:
        logger.error(f"Error generating tax liability report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/employees/roster", response_model=EmployeeRosterReport)
async def generate_employee_roster_report(
    department: Optional[str] = Query(None, description="Filter by department"),
    employment_type: Optional[str] = Query(None, description="Filter by employment type"),
    include_terminated: bool = Query(False, description="Include terminated employees"),
    hire_date_start: Optional[date] = Query(None, description="Hire date range start"),
    hire_date_end: Optional[date] = Query(None, description="Hire date range end"),
    service: ReportingService = Depends(get_reporting_service),
    current_user: User = Depends(get_current_user)
):
    """
    Generate employee roster report.
    
    **Required permissions**: Any authenticated user
    
    **Features**:
    - Complete employee directory and information
    - Filter by department, employment type, hire date
    - Include compensation information
    """
    try:
        # Determine report period based on date filters
        report_period = ReportPeriod.YEARLY  # Default for employee roster
        start_date = hire_date_start
        end_date = hire_date_end
        
        # If both dates are provided, use custom period
        if hire_date_start is not None and hire_date_end is not None:
            report_period = ReportPeriod.CUSTOM
        # If only start date is provided, set end date to today
        elif hire_date_start is not None and hire_date_end is None:
            report_period = ReportPeriod.CUSTOM
            end_date = date.today()
        # If only end date is provided, set start date to beginning of year
        elif hire_date_start is None and hire_date_end is not None:
            report_period = ReportPeriod.CUSTOM
            start_date = date(hire_date_end.year, 1, 1)
        
        request = ReportRequest(
            report_type=ReportType.EMPLOYEE_ROSTER,
            report_period=report_period,
            start_date=start_date,
            end_date=end_date,
            department=department,
            include_terminated=include_terminated,
            status_filter=employment_type
        )
        
        report_response = service.generate_report(request, current_user.id)
        return report_response.data
        
    except Exception as e:
        logger.error(f"Error generating employee roster report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/employees/salary-analysis", response_model=SalaryAnalysisReport)
async def generate_salary_analysis_report(
    department: Optional[str] = Query(None, description="Filter by department"),
    position: Optional[str] = Query(None, description="Filter by position"),
    service: ReportingService = Depends(get_reporting_service),
    current_user: User = Depends(require_admin)
):
    """
    Generate salary analysis report.
    
    **Required permissions**: Admin
    
    **Features**:
    - Salary statistics and analysis by department/position
    - Min, max, average, median calculations
    - Salary range and distribution analysis
    """
    try:
        request = ReportRequest(
            report_type=ReportType.SALARY_ANALYSIS,
            report_period=ReportPeriod.YEARLY,
            department=department,
            status_filter=position,
            include_detailed_breakdown=True
        )
        
        report_response = service.generate_report(request, current_user.id)
        return report_response.data
        
    except Exception as e:
        logger.error(f"Error generating salary analysis report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/compliance/i9-status", response_model=ComplianceReport)
async def generate_compliance_report(
    department: Optional[str] = Query(None, description="Filter by department"),
    include_terminated: bool = Query(False, description="Include terminated employees"),
    service: ReportingService = Depends(get_reporting_service),
    current_user: User = Depends(get_current_user)
):
    """
    Generate compliance report.
    
    **Required permissions**: Any authenticated user
    
    **Features**:
    - Employee compliance status (I-9, W-4, background checks)
    - Compliance scores and missing documents
    - Department-wise compliance rates
    """
    try:
        request = ReportRequest(
            report_type=ReportType.I9_COMPLIANCE,
            report_period=ReportPeriod.YEARLY,
            department=department,
            include_terminated=include_terminated,
            include_detailed_breakdown=True
        )
        
        report_response = service.generate_report(request, current_user.id)
        return report_response.data
        
    except Exception as e:
        logger.error(f"Error generating compliance report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/time-tracking/summary", response_model=TimeSummaryReport)
async def generate_time_summary_report(
    start_date: date = Query(..., description="Start date for report"),
    end_date: date = Query(..., description="End date for report"),
    department: Optional[str] = Query(None, description="Filter by department"),
    employee_ids: Optional[List[int]] = Query(None, description="Filter by employee IDs"),
    service: ReportingService = Depends(get_reporting_service),
    current_user: User = Depends(get_current_user)
):
    """
    Generate time tracking summary report.
    
    **Required permissions**: Any authenticated user
    
    **Features**:
    - Time tracking summary and statistics
    - Regular hours, overtime, and totals
    - Employee-wise breakdown
    """
    try:
        request = ReportRequest(
            report_type=ReportType.TIME_SUMMARY,
            report_period=ReportPeriod.CUSTOM,
            start_date=start_date,
            end_date=end_date,
            department=department,
            employee_ids=employee_ids
        )
        
        report_response = service.generate_report(request, current_user.id)
        return report_response.data
        
    except Exception as e:
        logger.error(f"Error generating time summary report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# Report Management Endpoints

@router.get("/dashboard/summary")
async def get_reporting_dashboard(
    service: ReportingService = Depends(get_reporting_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get reporting dashboard summary.
    
    **Required permissions**: Any authenticated user
    
    **Features**:
    - Quick overview of key metrics
    - Recent report statistics
    - Popular report types
    """
    try:
        # Get current month data for dashboard
        today = date.today()
        month_start = today.replace(day=1)
        
        # Generate quick summaries for dashboard
        employee_request = ReportRequest(
            report_type=ReportType.EMPLOYEE_ROSTER,
            report_period=ReportPeriod.MONTHLY
        )
        employee_report = service.generate_report(employee_request, current_user.id)
        
        compliance_request = ReportRequest(
            report_type=ReportType.I9_COMPLIANCE,
            report_period=ReportPeriod.YEARLY
        )
        compliance_report = service.generate_report(compliance_request, current_user.id)
        
        dashboard_data = {
            "summary": {
                "total_employees": employee_report.data.summary.get("total_employees", 0),
                "active_employees": employee_report.data.summary.get("active_employees", 0),
                "compliance_rate": compliance_report.data.summary.get("full_compliance_rate", 0),
                "dashboard_date": today
            },
            "available_reports": service.get_available_report_types(),
            "quick_actions": [
                {
                    "name": "Employee Roster",
                    "description": "View current employee directory",
                    "endpoint": "/api/v1/reports/employees/roster"
                },
                {
                    "name": "Compliance Status",
                    "description": "Check employee compliance",
                    "endpoint": "/api/v1/reports/compliance/i9-status"
                },
                {
                    "name": "Monthly Payroll",
                    "description": "Generate payroll register",
                    "endpoint": "/api/v1/reports/payroll/pay-register"
                }
            ]
        }
        
        return dashboard_data
        
    except Exception as e:
        logger.error(f"Error getting reporting dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/departments")
async def get_departments_for_reports(
    service: ReportingService = Depends(get_reporting_service),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get list of departments for report filtering.
    
    **Required permissions**: Any authenticated user
    
    **Features**:
    - List all departments in the system
    - Used for report filtering dropdowns
    """
    try:
        from app.models.employee import Employee
        
        departments = db.query(Employee.department).filter(
            Employee.department.isnot(None)
        ).distinct().all()
        
        dept_list = [dept[0] for dept in departments if dept[0]]
        
        return {
            "departments": sorted(dept_list),
            "total_departments": len(dept_list)
        }
        
    except Exception as e:
        logger.error(f"Error getting departments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/positions")
async def get_positions_for_reports(
    service: ReportingService = Depends(get_reporting_service),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get list of positions for report filtering.
    
    **Required permissions**: Any authenticated user
    
    **Features**:
    - List all positions in the system
    - Used for report filtering dropdowns
    """
    try:
        from app.models.employee import Employee
        
        positions = db.query(Employee.position).filter(
            Employee.position.isnot(None)
        ).distinct().all()
        
        position_list = [pos[0] for pos in positions if pos[0]]
        
        return {
            "positions": sorted(position_list),
            "total_positions": len(position_list)
        }
        
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# Utility Endpoints

@router.get("/date-ranges")
async def get_common_date_ranges(
    current_user: User = Depends(get_current_user)
):
    """
    Get common date ranges for reports.
    
    **Required permissions**: Any authenticated user
    
    **Features**:
    - Predefined date ranges for quick selection
    - Current month, quarter, year
    - Last month, quarter, year
    """
    try:
        today = date.today()
        
        # Current periods
        current_month_start = today.replace(day=1)
        current_quarter_month = ((today.month - 1) // 3) * 3 + 1
        current_quarter_start = today.replace(month=current_quarter_month, day=1)
        current_year_start = today.replace(month=1, day=1)
        
        # Previous periods
        if today.month == 1:
            prev_month_start = today.replace(year=today.year - 1, month=12, day=1)
            prev_month_end = today.replace(day=1) - timedelta(days=1)
        else:
            prev_month_start = today.replace(month=today.month - 1, day=1)
            prev_month_end = today.replace(day=1) - timedelta(days=1)
        
        date_ranges = {
            "current_month": {
                "name": "Current Month",
                "start_date": current_month_start,
                "end_date": today
            },
            "previous_month": {
                "name": "Previous Month",
                "start_date": prev_month_start,
                "end_date": prev_month_end
            },
            "current_quarter": {
                "name": "Current Quarter",
                "start_date": current_quarter_start,
                "end_date": today
            },
            "current_year": {
                "name": "Current Year",
                "start_date": current_year_start,
                "end_date": today
            },
            "last_30_days": {
                "name": "Last 30 Days",
                "start_date": today - timedelta(days=30),
                "end_date": today
            },
            "last_90_days": {
                "name": "Last 90 Days",
                "start_date": today - timedelta(days=90),
                "end_date": today
            }
        }
        
        return date_ranges
        
    except Exception as e:
        logger.error(f"Error getting date ranges: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# Export Endpoints

@router.get("/export/formats")
async def get_supported_export_formats(
    service: ReportingService = Depends(get_reporting_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get supported export formats.
    
    **Required permissions**: Any authenticated user
    
    **Features**:
    - List supported export formats
    - Format descriptions and limitations
    """
    try:
        formats = service.get_supported_export_formats()
        
        return {
            "supported_formats": formats,
            "format_descriptions": {
                "json": "JavaScript Object Notation - structured data format",
                "csv": "Comma-Separated Values - suitable for Excel and data analysis",
                "pdf": "Portable Document Format - formatted for printing (coming soon)"
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting export formats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/export/csv")
async def export_report_to_csv(
    request: ReportRequest,
    service: ReportingService = Depends(get_reporting_service),
    current_user: User = Depends(get_current_user)
):
    """
    Export report to CSV format.
    
    **Required permissions**: Any authenticated user
    
    **Features**:
    - Export any report type to CSV
    - Automatic file download
    - Structured data format suitable for Excel
    """
    try:
        # Generate the report first
        report_response = service.generate_report(request, current_user.id)
        
        # Export to CSV
        csv_response = service.export_report_to_csv(report_response.data, request.report_type)
        
        logger.info(f"Report exported to CSV: {report_response.metadata.report_id} by user {current_user.id}")
        
        return csv_response
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error exporting report to CSV: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# Quick Export Endpoints for Specific Report Types

@router.get("/export/payroll/pay-register/csv")
async def export_pay_register_csv(
    start_date: date = Query(..., description="Start date for report"),
    end_date: date = Query(..., description="End date for report"),
    department: Optional[str] = Query(None, description="Filter by department"),
    employee_ids: Optional[List[int]] = Query(None, description="Filter by employee IDs"),
    include_terminated: bool = Query(False, description="Include terminated employees"),
    service: ReportingService = Depends(get_reporting_service),
    current_user: User = Depends(get_current_user)
):
    """
    Export pay register report to CSV.
    
    **Required permissions**: Any authenticated user
    
    **Features**:
    - Quick export pay register to CSV
    - Automatic file download
    - Detailed payroll data
    """
    try:
        request = ReportRequest(
            report_type=ReportType.PAY_REGISTER,
            report_period=ReportPeriod.CUSTOM,
            start_date=start_date,
            end_date=end_date,
            department=department,
            employee_ids=employee_ids,
            include_terminated=include_terminated
        )
        
        report_response = service.generate_report(request, current_user.id)
        csv_response = service.export_report_to_csv(report_response.data, request.report_type)
        
        return csv_response
        
    except Exception as e:
        logger.error(f"Error exporting pay register CSV: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/export/employees/roster/csv")
async def export_employee_roster_csv(
    department: Optional[str] = Query(None, description="Filter by department"),
    employment_type: Optional[str] = Query(None, description="Filter by employment type"),
    include_terminated: bool = Query(False, description="Include terminated employees"),
    service: ReportingService = Depends(get_reporting_service),
    current_user: User = Depends(get_current_user)
):
    """
    Export employee roster report to CSV.
    
    **Required permissions**: Any authenticated user
    
    **Features**:
    - Quick export employee roster to CSV
    - Automatic file download
    - Complete employee information
    """
    try:
        request = ReportRequest(
            report_type=ReportType.EMPLOYEE_ROSTER,
            report_period=ReportPeriod.YEARLY,
            department=department,
            include_terminated=include_terminated,
            status_filter=employment_type
        )
        
        report_response = service.generate_report(request, current_user.id)
        csv_response = service.export_report_to_csv(report_response.data, request.report_type)
        
        return csv_response
        
    except Exception as e:
        logger.error(f"Error exporting employee roster CSV: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/export/compliance/csv")
async def export_compliance_csv(
    department: Optional[str] = Query(None, description="Filter by department"),
    include_terminated: bool = Query(False, description="Include terminated employees"),
    service: ReportingService = Depends(get_reporting_service),
    current_user: User = Depends(get_current_user)
):
    """
    Export compliance report to CSV.
    
    **Required permissions**: Any authenticated user
    
    **Features**:
    - Quick export compliance report to CSV
    - Automatic file download
    - Compliance status and missing documents
    """
    try:
        request = ReportRequest(
            report_type=ReportType.I9_COMPLIANCE,
            report_period=ReportPeriod.YEARLY,
            department=department,
            include_terminated=include_terminated
        )
        
        report_response = service.generate_report(request, current_user.id)
        csv_response = service.export_report_to_csv(report_response.data, request.report_type)
        
        return csv_response
        
    except Exception as e:
        logger.error(f"Error exporting compliance CSV: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/export/time-tracking/csv")
async def export_time_summary_csv(
    start_date: date = Query(..., description="Start date for report"),
    end_date: date = Query(..., description="End date for report"),
    department: Optional[str] = Query(None, description="Filter by department"),
    employee_ids: Optional[List[int]] = Query(None, description="Filter by employee IDs"),
    service: ReportingService = Depends(get_reporting_service),
    current_user: User = Depends(get_current_user)
):
    """
    Export time tracking summary report to CSV.
    
    **Required permissions**: Any authenticated user
    
    **Features**:
    - Quick export time tracking summary to CSV
    - Automatic file download
    - Time tracking statistics
    """
    try:
        request = ReportRequest(
            report_type=ReportType.TIME_SUMMARY,
            report_period=ReportPeriod.CUSTOM,
            start_date=start_date,
            end_date=end_date,
            department=department,
            employee_ids=employee_ids
        )
        
        report_response = service.generate_report(request, current_user.id)
        csv_response = service.export_report_to_csv(report_response.data, request.report_type)
        
        return csv_response
        
    except Exception as e:
        logger.error(f"Error exporting time summary CSV: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# Cache Management Endpoints

@router.get("/cache/stats")
async def get_cache_stats(
    service: ReportingService = Depends(get_reporting_service),
    current_user: User = Depends(require_admin)
):
    """
    Get cache statistics.
    
    **Required permissions**: Admin
    
    **Features**:
    - View cache performance metrics
    - Monitor cache usage
    - Troubleshoot caching issues
    """
    try:
        stats = service.get_cache_stats()
        
        return {
            "cache_stats": stats,
            "cache_enabled": True,
            "cache_description": "In-memory caching for frequently requested reports"
        }
        
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/cache/clear")
async def clear_cache(
    service: ReportingService = Depends(get_reporting_service),
    current_user: User = Depends(require_admin)
):
    """
    Clear all cached reports.
    
    **Required permissions**: Admin
    
    **Features**:
    - Clear all cached reports
    - Force fresh report generation
    - Troubleshoot caching issues
    """
    try:
        service.clear_cache()
        
        return {
            "message": "Cache cleared successfully",
            "cleared_by": current_user.id,
            "cleared_at": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.put("/cache/ttl")
async def set_cache_ttl(
    ttl_seconds: int = Query(..., description="Cache TTL in seconds", ge=60, le=3600),
    service: ReportingService = Depends(get_reporting_service),
    current_user: User = Depends(require_admin)
):
    """
    Set cache TTL (time to live).
    
    **Required permissions**: Admin
    
    **Features**:
    - Configure cache expiration time
    - Optimize cache performance
    - Balance between performance and data freshness
    """
    try:
        service.set_cache_ttl(ttl_seconds)
        
        return {
            "message": "Cache TTL updated successfully",
            "new_ttl_seconds": ttl_seconds,
            "updated_by": current_user.id,
            "updated_at": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Error setting cache TTL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/generate/no-cache")
async def generate_report_no_cache(
    request: ReportRequest,
    service: ReportingService = Depends(get_reporting_service),
    current_user: User = Depends(get_current_user)
):
    """
    Generate a report without using cache.
    
    **Required permissions**: Any authenticated user
    
    **Features**:
    - Force fresh report generation
    - Bypass cache for real-time data
    - Useful for testing and troubleshooting
    """
    try:
        # Generate report without caching
        report_response = service.generate_report(request, current_user.id, use_cache=False)
        
        logger.info(f"Report generated without cache: {report_response.metadata.report_id} by user {current_user.id}")
        
        return report_response
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error generating report without cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        ) 