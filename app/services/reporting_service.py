"""
Reporting Service Module.

This module provides business logic for generating various types of reports
including payroll reports, employee reports, compliance reports, and time tracking reports.
"""

import logging
import uuid
import csv
import io
import hashlib
import json
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import and_, or_, func, desc, asc
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse

from app.models.user import User
from app.models.employee import Employee
from app.models.payroll import PayrollRecord, PayPeriod
from app.models.time_entry import TimeEntry
from app.models.enums import (
    ReportType, ReportFormat, ReportPeriod, ReportStatus,
    EmployeeStatus, PayrollStatus, EmploymentType, ApprovalStatus
)
from app.schemas.reports import (
    ReportRequest, ReportMetadata, ReportResponse,
    PayRegisterReport, PayRegisterEntry,
    TaxLiabilityReport, TaxLiabilitySummary,
    EmployeeRosterReport, EmployeeRosterEntry,
    SalaryAnalysisReport, SalaryAnalysisEntry,
    ComplianceReport, ComplianceEntry,
    TimeSummaryReport, TimeSummaryEntry,
    ReportListResponse, ReportListEntry
)

logger = logging.getLogger(__name__)


class ReportingService:
    """Service class for report generation operations."""
    
    def __init__(self, db: Session):
        self.db = db
        self._cache: Dict[str, Any] = {}  # Simple in-memory cache
        self._cache_expiry: Dict[str, datetime] = {}  # Cache expiry times
        self._cache_ttl = 300  # 5 minutes default TTL
    
    def generate_report(self, request: ReportRequest, user_id: int, use_cache: bool = True) -> ReportResponse:
        """Generate a report based on the request."""
        try:
            # Generate cache key
            cache_key = self._generate_cache_key(request, user_id)
            
            # Check cache first
            if use_cache and self._is_cached(cache_key):
                logger.info(f"Returning cached report: {cache_key}")
                return self._get_cached_report(cache_key)
            
            # Generate unique report ID
            report_id = f"rpt_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
            
            # Calculate date range
            start_date, end_date = self._calculate_date_range(request.report_period, request.start_date, request.end_date)
            
            # Create metadata
            metadata = ReportMetadata(
                report_id=report_id,
                report_type=request.report_type,
                report_format=request.report_format,
                status=ReportStatus.GENERATING,
                generated_at=datetime.utcnow(),
                report_period_start=start_date,
                report_period_end=end_date,
                total_records=0,
                generated_by=user_id,
                filters_applied=self._extract_filters(request)
            )
            
            # Generate report based on type
            report_data = self._generate_report_by_type(request, start_date, end_date, metadata)
            
            # Update metadata
            metadata.status = ReportStatus.COMPLETED
            metadata.total_records = self._count_records_in_report(report_data)
            
            # Create response
            response = ReportResponse(
                metadata=metadata,
                data=report_data
            )
            
            # Cache the response if appropriate
            if use_cache and self._should_cache_report(request):
                self._cache_report(cache_key, response)
                logger.info(f"Report cached: {cache_key}")
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate report: {str(e)}"
            )
    
    def _generate_report_by_type(self, request: ReportRequest, start_date: date, end_date: date, metadata: ReportMetadata) -> Any:
        """Generate report based on type."""
        if request.report_type == ReportType.PAY_REGISTER:
            return self._generate_pay_register_report(request, start_date, end_date, metadata)
        elif request.report_type == ReportType.TAX_LIABILITY:
            return self._generate_tax_liability_report(request, start_date, end_date, metadata)
        elif request.report_type == ReportType.EMPLOYEE_ROSTER:
            return self._generate_employee_roster_report(request, start_date, end_date, metadata)
        elif request.report_type == ReportType.SALARY_ANALYSIS:
            return self._generate_salary_analysis_report(request, start_date, end_date, metadata)
        elif request.report_type == ReportType.I9_COMPLIANCE:
            return self._generate_compliance_report(request, start_date, end_date, metadata)
        elif request.report_type == ReportType.TIME_SUMMARY:
            return self._generate_time_summary_report(request, start_date, end_date, metadata)
        else:
            raise ValueError(f"Unsupported report type: {request.report_type}")
    
    def _generate_pay_register_report(self, request: ReportRequest, start_date: date, end_date: date, metadata: ReportMetadata) -> PayRegisterReport:
        """Generate pay register report."""
        try:
            # Build query
            query = self.db.query(PayrollRecord).join(Employee).join(PayPeriod)
            
            # Apply filters
            query = query.filter(
                PayPeriod.start_date >= start_date,
                PayPeriod.end_date <= end_date
            )
            
            if request.department:
                query = query.filter(Employee.department == request.department)
            
            if request.employee_ids:
                query = query.filter(Employee.id.in_(request.employee_ids))
            
            if not request.include_terminated:
                query = query.filter(Employee.status != EmployeeStatus.TERMINATED)
            
            # Execute query
            payroll_records = query.all()
            
            # Create entries
            entries = []
            total_gross_pay = Decimal('0.00')
            total_net_pay = Decimal('0.00')
            total_deductions = Decimal('0.00')
            
            for record in payroll_records:
                entry = PayRegisterEntry(
                    employee_id=record.employee.id,
                    employee_name=record.employee.full_name,
                    employee_number=record.employee.employee_id,
                    department=record.employee.department,
                    position=record.employee.position,
                    pay_period_start=record.pay_period.start_date,
                    pay_period_end=record.pay_period.end_date,
                    hours_worked=record.hours_worked,
                    overtime_hours=record.overtime_hours,
                    gross_pay=record.gross_pay,
                    regular_pay=record.gross_pay - (record.overtime_hours * (record.employee.hourly_rate or 0) * 1.5),
                    overtime_pay=record.overtime_hours * (record.employee.hourly_rate or 0) * 1.5,
                    federal_tax=record.federal_income_tax,
                    state_tax=record.state_income_tax,
                    social_security=record.social_security_tax,
                    medicare=record.medicare_tax,
                    benefit_deductions=record.health_insurance + record.dental_insurance + record.vision_insurance + record.retirement_401k,
                    other_deductions=record.other_deductions,
                    total_deductions=record.total_deductions,
                    net_pay=record.net_pay
                )
                entries.append(entry)
                
                total_gross_pay += record.gross_pay
                total_net_pay += record.net_pay
                total_deductions += record.total_deductions
            
            # Create summary
            summary = {
                "total_employees": len(entries),
                "total_gross_pay": float(total_gross_pay),
                "total_net_pay": float(total_net_pay),
                "total_deductions": float(total_deductions),
                "average_gross_pay": float(total_gross_pay / len(entries)) if entries else 0,
                "average_net_pay": float(total_net_pay / len(entries)) if entries else 0,
                "period_start": start_date,
                "period_end": end_date
            }
            
            return PayRegisterReport(
                metadata=metadata,
                summary=summary,
                entries=entries
            )
            
        except Exception as e:
            logger.error(f"Error generating pay register report: {e}")
            raise
    
    def _generate_tax_liability_report(self, request: ReportRequest, start_date: date, end_date: date, metadata: ReportMetadata) -> TaxLiabilityReport:
        """Generate tax liability report."""
        try:
            # Get payroll records for the period
            query = self.db.query(PayrollRecord).join(Employee).join(PayPeriod)
            query = query.filter(
                PayPeriod.start_date >= start_date,
                PayPeriod.end_date <= end_date
            )
            
            if request.department:
                query = query.filter(Employee.department == request.department)
            
            if not request.include_terminated:
                query = query.filter(Employee.status != EmployeeStatus.TERMINATED)
            
            payroll_records = query.all()
            
            # Calculate totals
            federal_income_tax = sum(r.federal_income_tax for r in payroll_records)
            state_income_tax = sum(r.state_income_tax for r in payroll_records)
            social_security_employee = sum(r.social_security_tax for r in payroll_records)
            medicare_employee = sum(r.medicare_tax for r in payroll_records)
            total_wages = sum(r.gross_pay for r in payroll_records)
            
            # Calculate employer taxes (matching contributions)
            social_security_employer = social_security_employee  # 6.2% each
            medicare_employer = medicare_employee  # 1.45% each
            state_unemployment = total_wages * Decimal('0.006')  # 0.6% SUTA (simplified)
            
            # Create summary
            tax_summary = TaxLiabilitySummary(
                period_start=start_date,
                period_end=end_date,
                federal_income_tax=federal_income_tax,
                social_security_employee=social_security_employee,
                social_security_employer=social_security_employer,
                medicare_employee=medicare_employee,
                medicare_employer=medicare_employer,
                state_income_tax=state_income_tax,
                state_unemployment=state_unemployment,
                total_employee_taxes=federal_income_tax + state_income_tax + social_security_employee + medicare_employee,
                total_employer_taxes=social_security_employer + medicare_employer + state_unemployment,
                total_tax_liability=federal_income_tax + state_income_tax + (social_security_employee + social_security_employer) + (medicare_employee + medicare_employer) + state_unemployment,
                total_wages=total_wages,
                total_employees=len(set(r.employee_id for r in payroll_records))
            )
            
            # Department breakdown (if requested)
            by_department = None
            if request.include_detailed_breakdown:
                dept_data = {}
                for record in payroll_records:
                    dept = record.employee.department or "Unknown"
                    if dept not in dept_data:
                        dept_data[dept] = {
                            "department": dept,
                            "employees": 0,
                            "total_wages": Decimal('0.00'),
                            "federal_tax": Decimal('0.00'),
                            "state_tax": Decimal('0.00'),
                            "social_security": Decimal('0.00'),
                            "medicare": Decimal('0.00')
                        }
                    
                    dept_data[dept]["employees"] += 1
                    dept_data[dept]["total_wages"] += record.gross_pay
                    dept_data[dept]["federal_tax"] += record.federal_income_tax
                    dept_data[dept]["state_tax"] += record.state_income_tax
                    dept_data[dept]["social_security"] += record.social_security_tax
                    dept_data[dept]["medicare"] += record.medicare_tax
                
                by_department = [
                    {
                        **data,
                        "total_wages": float(data["total_wages"]),
                        "federal_tax": float(data["federal_tax"]),
                        "state_tax": float(data["state_tax"]),
                        "social_security": float(data["social_security"]),
                        "medicare": float(data["medicare"])
                    }
                    for data in dept_data.values()
                ]
            
            return TaxLiabilityReport(
                metadata=metadata,
                summary=tax_summary,
                by_department=by_department,
                by_employee=None  # Can be implemented if needed
            )
            
        except Exception as e:
            logger.error(f"Error generating tax liability report: {e}")
            raise
    
    def _generate_employee_roster_report(self, request: ReportRequest, start_date: date, end_date: date, metadata: ReportMetadata) -> EmployeeRosterReport:
        """Generate employee roster report."""
        try:
            # Build query
            query = self.db.query(Employee)
            
            # Apply filters
            if request.department:
                query = query.filter(Employee.department == request.department)
            
            if request.employee_ids:
                query = query.filter(Employee.id.in_(request.employee_ids))
            
            if not request.include_terminated:
                query = query.filter(Employee.status != EmployeeStatus.TERMINATED)
            
            # Filter by hire date if needed
            if start_date and end_date:
                query = query.filter(
                    Employee.hire_date >= start_date,
                    Employee.hire_date <= end_date
                )
            
            employees = query.all()
            
            # Create entries
            entries = []
            for employee in employees:
                # Get manager name
                manager_name = None
                if employee.manager_id:
                    manager = self.db.query(Employee).filter(Employee.id == employee.manager_id).first()
                    if manager:
                        manager_name = manager.full_name
                
                entry = EmployeeRosterEntry(
                    employee_id=employee.id,
                    employee_number=employee.employee_id,
                    full_name=employee.full_name,
                    email=employee.email,
                    phone=employee.phone,
                    status=employee.status,
                    employment_type=employee.employment_type,
                    position=employee.position,
                    department=employee.department,
                    location=None,  # Add location field to Employee model if needed
                    hire_date=employee.hire_date,
                    termination_date=employee.termination_date,
                    manager_name=manager_name,
                    salary=employee.salary,
                    hourly_rate=employee.hourly_rate
                )
                entries.append(entry)
            
            # Create summary
            summary = {
                "total_employees": len(entries),
                "active_employees": len([e for e in entries if e.status == EmployeeStatus.ACTIVE]),
                "terminated_employees": len([e for e in entries if e.status == EmployeeStatus.TERMINATED]),
                "full_time_employees": len([e for e in entries if e.employment_type == EmploymentType.FULL_TIME]),
                "part_time_employees": len([e for e in entries if e.employment_type == EmploymentType.PART_TIME]),
                "departments": len(set(e.department for e in entries if e.department)),
                "report_date": datetime.utcnow().date()
            }
            
            return EmployeeRosterReport(
                metadata=metadata,
                summary=summary,
                employees=entries
            )
            
        except Exception as e:
            logger.error(f"Error generating employee roster report: {e}")
            raise
    
    def _generate_salary_analysis_report(self, request: ReportRequest, start_date: date, end_date: date, metadata: ReportMetadata) -> SalaryAnalysisReport:
        """Generate salary analysis report."""
        try:
            # Build query for active employees with salary information
            query = self.db.query(Employee).filter(
                Employee.status == EmployeeStatus.ACTIVE,
                or_(Employee.salary.isnot(None), Employee.hourly_rate.isnot(None))
            )
            
            if request.department:
                query = query.filter(Employee.department == request.department)
            
            employees = query.all()
            
            # Calculate annual salaries for all employees
            employee_data = []
            for emp in employees:
                annual_salary = emp.salary or (emp.hourly_rate * Decimal('2080'))  # 40 hours/week * 52 weeks
                employee_data.append({
                    'employee': emp,
                    'annual_salary': annual_salary,
                    'department': emp.department or 'Unknown',
                    'position': emp.position
                })
            
            # Analyze by department
            dept_analysis = {}
            for data in employee_data:
                dept = data['department']
                if dept not in dept_analysis:
                    dept_analysis[dept] = []
                dept_analysis[dept].append(data['annual_salary'])
            
            by_department = []
            for dept, salaries in dept_analysis.items():
                if salaries:
                    salaries_sorted = sorted(salaries)
                    median_index = len(salaries_sorted) // 2
                    median_salary = salaries_sorted[median_index] if len(salaries_sorted) % 2 == 1 else (salaries_sorted[median_index - 1] + salaries_sorted[median_index]) / 2
                    
                    by_department.append(SalaryAnalysisEntry(
                        department=dept,
                        position="All Positions",
                        employee_count=len(salaries),
                        min_salary=min(salaries),
                        max_salary=max(salaries),
                        avg_salary=sum(salaries) / len(salaries),
                        median_salary=median_salary,
                        total_salary_cost=sum(salaries),
                        salary_range=max(salaries) - min(salaries)
                    ))
            
            # Analyze by position
            pos_analysis = {}
            for data in employee_data:
                pos = data['position']
                if pos not in pos_analysis:
                    pos_analysis[pos] = []
                pos_analysis[pos].append(data['annual_salary'])
            
            by_position = []
            for pos, salaries in pos_analysis.items():
                if salaries:
                    salaries_sorted = sorted(salaries)
                    median_index = len(salaries_sorted) // 2
                    median_salary = salaries_sorted[median_index] if len(salaries_sorted) % 2 == 1 else (salaries_sorted[median_index - 1] + salaries_sorted[median_index]) / 2
                    
                    by_position.append(SalaryAnalysisEntry(
                        department="All Departments",
                        position=pos,
                        employee_count=len(salaries),
                        min_salary=min(salaries),
                        max_salary=max(salaries),
                        avg_salary=sum(salaries) / len(salaries),
                        median_salary=median_salary,
                        total_salary_cost=sum(salaries),
                        salary_range=max(salaries) - min(salaries)
                    ))
            
            # Overall summary
            all_salaries = [data['annual_salary'] for data in employee_data]
            summary = {
                "total_employees_analyzed": len(employee_data),
                "total_salary_cost": float(sum(all_salaries)),
                "average_salary": float(sum(all_salaries) / len(all_salaries)) if all_salaries else 0,
                "min_salary": float(min(all_salaries)) if all_salaries else 0,
                "max_salary": float(max(all_salaries)) if all_salaries else 0,
                "departments_analyzed": len(dept_analysis),
                "positions_analyzed": len(pos_analysis),
                "analysis_date": datetime.utcnow().date()
            }
            
            return SalaryAnalysisReport(
                metadata=metadata,
                summary=summary,
                by_department=by_department,
                by_position=by_position
            )
            
        except Exception as e:
            logger.error(f"Error generating salary analysis report: {e}")
            raise
    
    def _generate_compliance_report(self, request: ReportRequest, start_date: date, end_date: date, metadata: ReportMetadata) -> ComplianceReport:
        """Generate compliance report."""
        try:
            # Build query
            query = self.db.query(Employee)
            
            if request.department:
                query = query.filter(Employee.department == request.department)
            
            if not request.include_terminated:
                query = query.filter(Employee.status != EmployeeStatus.TERMINATED)
            
            employees = query.all()
            
            # Create entries
            entries = []
            compliance_stats = {
                "total_employees": 0,
                "i9_completed": 0,
                "w4_completed": 0,
                "background_check_completed": 0,
                "fully_compliant": 0
            }
            
            for employee in employees:
                # Calculate missing documents
                missing_docs = []
                if not employee.i9_completed:
                    missing_docs.append("I-9 Form")
                if not employee.w4_completed:
                    missing_docs.append("W-4 Form")
                if not employee.background_check_completed:
                    missing_docs.append("Background Check")
                
                # Calculate compliance score (0-100)
                compliance_score = 0
                if employee.i9_completed:
                    compliance_score += 33
                if employee.w4_completed:
                    compliance_score += 33
                if employee.background_check_completed:
                    compliance_score += 34
                
                entry = ComplianceEntry(
                    employee_id=employee.id,
                    employee_name=employee.full_name,
                    employee_number=employee.employee_id,
                    department=employee.department,
                    position=employee.position,
                    hire_date=employee.hire_date,
                    i9_completed=employee.i9_completed,
                    w4_completed=employee.w4_completed,
                    background_check_completed=employee.background_check_completed,
                    compliance_score=compliance_score,
                    missing_documents=missing_docs,
                    compliance_notes=None
                )
                entries.append(entry)
                
                # Update stats
                compliance_stats["total_employees"] += 1
                if employee.i9_completed:
                    compliance_stats["i9_completed"] += 1
                if employee.w4_completed:
                    compliance_stats["w4_completed"] += 1
                if employee.background_check_completed:
                    compliance_stats["background_check_completed"] += 1
                if compliance_score == 100:
                    compliance_stats["fully_compliant"] += 1
            
            # Calculate percentages
            total = compliance_stats["total_employees"]
            summary = {
                **compliance_stats,
                "i9_completion_rate": (compliance_stats["i9_completed"] / total * 100) if total > 0 else 0,
                "w4_completion_rate": (compliance_stats["w4_completed"] / total * 100) if total > 0 else 0,
                "background_check_rate": (compliance_stats["background_check_completed"] / total * 100) if total > 0 else 0,
                "full_compliance_rate": (compliance_stats["fully_compliant"] / total * 100) if total > 0 else 0,
                "report_date": datetime.utcnow().date()
            }
            
            return ComplianceReport(
                metadata=metadata,
                summary=summary,
                entries=entries
            )
            
        except Exception as e:
            logger.error(f"Error generating compliance report: {e}")
            raise
    
    def _generate_time_summary_report(self, request: ReportRequest, start_date: date, end_date: date, metadata: ReportMetadata) -> TimeSummaryReport:
        """Generate time summary report."""
        try:
            # Get time entries for the period
            query = self.db.query(TimeEntry).join(Employee)
            query = query.filter(
                TimeEntry.work_date >= start_date,
                TimeEntry.work_date <= end_date,
                TimeEntry.approval_status == ApprovalStatus.APPROVED
            )
            
            if request.department:
                query = query.filter(Employee.department == request.department)
            
            if request.employee_ids:
                query = query.filter(TimeEntry.employee_id.in_(request.employee_ids))
            
            time_entries = query.all()
            
            # Group by employee
            employee_data = {}
            for entry in time_entries:
                emp_id = entry.employee_id
                if emp_id not in employee_data:
                    employee_data[emp_id] = {
                        'employee': entry.employee,
                        'total_hours': Decimal('0.00'),
                        'regular_hours': Decimal('0.00'),
                        'overtime_hours': Decimal('0.00'),
                        'days_worked': set()
                    }
                
                employee_data[emp_id]['total_hours'] += entry.total_hours or Decimal('0.00')
                employee_data[emp_id]['regular_hours'] += entry.regular_hours or Decimal('0.00')
                employee_data[emp_id]['overtime_hours'] += entry.overtime_hours or Decimal('0.00')
                employee_data[emp_id]['days_worked'].add(entry.work_date)
            
            # Create entries
            entries = []
            total_hours_all = Decimal('0.00')
            total_overtime_all = Decimal('0.00')
            
            for emp_id, data in employee_data.items():
                days_worked = len(data['days_worked'])
                avg_hours_per_day = data['total_hours'] / days_worked if days_worked > 0 else Decimal('0.00')
                
                entry = TimeSummaryEntry(
                    employee_id=emp_id,
                    employee_name=data['employee'].full_name,
                    department=data['employee'].department,
                    total_hours=data['total_hours'],
                    regular_hours=data['regular_hours'],
                    overtime_hours=data['overtime_hours'],
                    days_worked=days_worked,
                    avg_hours_per_day=avg_hours_per_day
                )
                entries.append(entry)
                
                total_hours_all += data['total_hours']
                total_overtime_all += data['overtime_hours']
            
            # Create summary
            summary = {
                "total_employees": len(entries),
                "total_hours_worked": float(total_hours_all),
                "total_overtime_hours": float(total_overtime_all),
                "average_hours_per_employee": float(total_hours_all / len(entries)) if entries else 0,
                "period_start": start_date,
                "period_end": end_date,
                "report_date": datetime.utcnow().date()
            }
            
            return TimeSummaryReport(
                metadata=metadata,
                summary=summary,
                entries=entries
            )
            
        except Exception as e:
            logger.error(f"Error generating time summary report: {e}")
            raise
    
    def _calculate_date_range(self, period: ReportPeriod, start_date: Optional[date], end_date: Optional[date]) -> Tuple[date, date]:
        """Calculate date range based on period."""
        today = date.today()
        
        if period == ReportPeriod.CUSTOM:
            if not start_date or not end_date:
                raise ValueError("Start and end dates are required for custom period")
            return start_date, end_date
        
        elif period == ReportPeriod.DAILY:
            return today, today
        
        elif period == ReportPeriod.WEEKLY:
            # Last 7 days
            week_start = today - timedelta(days=7)
            return week_start, today
        
        elif period == ReportPeriod.BIWEEKLY:
            # Last 14 days
            biweek_start = today - timedelta(days=14)
            return biweek_start, today
        
        elif period == ReportPeriod.MONTHLY:
            # Current month
            month_start = today.replace(day=1)
            return month_start, today
        
        elif period == ReportPeriod.QUARTERLY:
            # Current quarter
            quarter_month = ((today.month - 1) // 3) * 3 + 1
            quarter_start = today.replace(month=quarter_month, day=1)
            return quarter_start, today
        
        elif period == ReportPeriod.YEARLY:
            # Current year
            year_start = today.replace(month=1, day=1)
            return year_start, today
        
        else:
            # Default to monthly
            month_start = today.replace(day=1)
            return month_start, today
    
    def _extract_filters(self, request: ReportRequest) -> Dict[str, Any]:
        """Extract filters from request for metadata."""
        filters = {}
        
        if request.department:
            filters["department"] = request.department
        if request.employee_ids:
            filters["employee_ids"] = request.employee_ids
        if request.location:
            filters["location"] = request.location
        if request.status_filter:
            filters["status"] = request.status_filter
        if request.include_terminated:
            filters["include_terminated"] = request.include_terminated
        
        return filters
    
    def _count_records_in_report(self, report_data: Any) -> int:
        """Count records in report data."""
        if hasattr(report_data, 'entries'):
            return len(report_data.entries)
        elif hasattr(report_data, 'employees'):
            return len(report_data.employees)
        else:
            return 0
    
    def get_available_report_types(self) -> List[Dict[str, Any]]:
        """Get available report types with descriptions."""
        return [
            {
                "type": ReportType.PAY_REGISTER,
                "name": "Pay Register",
                "description": "Detailed payroll register with earnings and deductions",
                "category": "Payroll"
            },
            {
                "type": ReportType.TAX_LIABILITY,
                "name": "Tax Liability",
                "description": "Tax liability summary and breakdowns",
                "category": "Payroll"
            },
            {
                "type": ReportType.EMPLOYEE_ROSTER,
                "name": "Employee Roster",
                "description": "Complete employee directory and information",
                "category": "Employee"
            },
            {
                "type": ReportType.SALARY_ANALYSIS,
                "name": "Salary Analysis",
                "description": "Salary statistics and analysis by department/position",
                "category": "Employee"
            },
            {
                "type": ReportType.I9_COMPLIANCE,
                "name": "Compliance Report",
                "description": "Employee compliance status (I-9, W-4, background checks)",
                "category": "Compliance"
            },
            {
                "type": ReportType.TIME_SUMMARY,
                "name": "Time Summary",
                "description": "Time tracking summary and statistics",
                "category": "Time Tracking"
            }
        ]
    
    def export_report_to_csv(self, report_data: Any, report_type: ReportType) -> StreamingResponse:
        """Export report data to CSV format."""
        try:
            # Create CSV content based on report type
            if report_type == ReportType.PAY_REGISTER:
                return self._export_pay_register_csv(report_data)
            elif report_type == ReportType.EMPLOYEE_ROSTER:
                return self._export_employee_roster_csv(report_data)
            elif report_type == ReportType.COMPLIANCE:
                return self._export_compliance_csv(report_data)
            elif report_type == ReportType.TIME_SUMMARY:
                return self._export_time_summary_csv(report_data)
            else:
                # Generic export for other types
                return self._export_generic_csv(report_data, report_type)
                
        except Exception as e:
            logger.error(f"Error exporting report to CSV: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to export report to CSV"
            )
    
    def _export_pay_register_csv(self, report_data: PayRegisterReport) -> StreamingResponse:
        """Export pay register report to CSV."""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            "Employee ID", "Employee Name", "Employee Number", "Department", "Position",
            "Pay Period Start", "Pay Period End", "Hours Worked", "Overtime Hours",
            "Gross Pay", "Regular Pay", "Overtime Pay", "Federal Tax", "State Tax",
            "Social Security", "Medicare", "Benefit Deductions", "Other Deductions",
            "Total Deductions", "Net Pay"
        ])
        
        # Write data rows
        for entry in report_data.entries:
            writer.writerow([
                entry.employee_id, entry.employee_name, entry.employee_number,
                entry.department or "", entry.position or "",
                entry.pay_period_start, entry.pay_period_end,
                entry.hours_worked, entry.overtime_hours,
                entry.gross_pay, entry.regular_pay, entry.overtime_pay,
                entry.federal_tax, entry.state_tax, entry.social_security,
                entry.medicare, entry.benefit_deductions, entry.other_deductions,
                entry.total_deductions, entry.net_pay
            ])
        
        output.seek(0)
        
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=pay_register_report.csv"}
        )
    
    def _export_employee_roster_csv(self, report_data: EmployeeRosterReport) -> StreamingResponse:
        """Export employee roster report to CSV."""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            "Employee ID", "Employee Number", "Full Name", "Email", "Phone",
            "Status", "Employment Type", "Position", "Department", "Location",
            "Hire Date", "Termination Date", "Manager", "Salary", "Hourly Rate"
        ])
        
        # Write data rows
        for entry in report_data.employees:
            writer.writerow([
                entry.employee_id, entry.employee_number, entry.full_name,
                entry.email, entry.phone or "", entry.status, entry.employment_type,
                entry.position, entry.department or "", entry.location or "",
                entry.hire_date, entry.termination_date or "",
                entry.manager_name or "", entry.salary or "", entry.hourly_rate or ""
            ])
        
        output.seek(0)
        
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=employee_roster_report.csv"}
        )
    
    def _export_compliance_csv(self, report_data: ComplianceReport) -> StreamingResponse:
        """Export compliance report to CSV."""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            "Employee ID", "Employee Name", "Employee Number", "Department",
            "Position", "Hire Date", "I-9 Completed", "W-4 Completed",
            "Background Check Completed", "Compliance Score", "Missing Documents"
        ])
        
        # Write data rows
        for entry in report_data.entries:
            writer.writerow([
                entry.employee_id, entry.employee_name, entry.employee_number,
                entry.department or "", entry.position, entry.hire_date,
                "Yes" if entry.i9_completed else "No",
                "Yes" if entry.w4_completed else "No",
                "Yes" if entry.background_check_completed else "No",
                entry.compliance_score or 0,
                ", ".join(entry.missing_documents)
            ])
        
        output.seek(0)
        
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=compliance_report.csv"}
        )
    
    def _export_time_summary_csv(self, report_data: TimeSummaryReport) -> StreamingResponse:
        """Export time summary report to CSV."""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            "Employee ID", "Employee Name", "Department", "Total Hours",
            "Regular Hours", "Overtime Hours", "Days Worked", "Avg Hours Per Day"
        ])
        
        # Write data rows
        for entry in report_data.entries:
            writer.writerow([
                entry.employee_id, entry.employee_name, entry.department or "",
                entry.total_hours, entry.regular_hours, entry.overtime_hours,
                entry.days_worked, entry.avg_hours_per_day
            ])
        
        output.seek(0)
        
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=time_summary_report.csv"}
        )
    
    def _export_generic_csv(self, report_data: Any, report_type: ReportType) -> StreamingResponse:
        """Export generic report to CSV."""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write basic information
        writer.writerow([f"Report Type: {report_type}"])
        writer.writerow([f"Generated At: {datetime.utcnow()}"])
        writer.writerow([])
        
        # Write summary if available
        if hasattr(report_data, 'summary') and report_data.summary:
            writer.writerow(["Summary"])
            for key, value in report_data.summary.items():
                writer.writerow([key, value])
            writer.writerow([])
        
        # Write basic data representation
        writer.writerow(["Data"])
        writer.writerow([f"Report data available in JSON format only"])
        
        output.seek(0)
        
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={report_type}_report.csv"}
        )
    
    def get_supported_export_formats(self) -> List[str]:
        """Get list of supported export formats."""
        return [
            ReportFormat.JSON.value,
            ReportFormat.CSV.value,
            # Note: PDF export would require additional libraries like reportlab
            # ReportFormat.PDF.value,
        ]
    
    # Cache Management Methods
    
    def _generate_cache_key(self, request: ReportRequest, user_id: int) -> str:
        """Generate a cache key for the report request."""
        # Create a deterministic key based on request parameters
        # Note: We include user_id for user-specific caching but exclude it for shared reports
        cache_data = {
            "report_type": request.report_type.value,
            "report_period": request.report_period.value,
            "start_date": request.start_date.isoformat() if request.start_date else None,
            "end_date": request.end_date.isoformat() if request.end_date else None,
            "department": request.department,
            "employee_ids": sorted(request.employee_ids) if request.employee_ids else None,
            "location": request.location,
            "status_filter": request.status_filter,
            "include_terminated": request.include_terminated,
            "include_detailed_breakdown": request.include_detailed_breakdown,
            "group_by": request.group_by,
            "sort_by": request.sort_by,
            # Include user_id only for user-specific reports
            "user_id": user_id if self._is_user_specific_report(request) else None
        }
        
        # Create hash of the cache data
        cache_string = json.dumps(cache_data, sort_keys=True, default=str)
        return hashlib.md5(cache_string.encode()).hexdigest()
    
    def _is_user_specific_report(self, request: ReportRequest) -> bool:
        """Check if report is user-specific and should not be shared."""
        # Most reports can be shared, but some might be user-specific
        # For now, all reports are shareable
        return False
    
    def _should_cache_report(self, request: ReportRequest) -> bool:
        """Determine if a report should be cached."""
        # Cache reports that are likely to be requested frequently
        # Don't cache real-time reports or very specific filters
        
        # Cache standard period reports
        if request.report_period in [ReportPeriod.MONTHLY, ReportPeriod.QUARTERLY, ReportPeriod.YEARLY]:
            return True
        
        # Cache reports with no specific employee filters
        if not request.employee_ids or len(request.employee_ids) > 10:
            return True
        
        # Cache department-level reports
        if request.department and not request.employee_ids:
            return True
        
        # Don't cache very specific or custom reports
        return False
    
    def _is_cached(self, cache_key: str) -> bool:
        """Check if a report is in cache and not expired."""
        if cache_key not in self._cache:
            return False
        
        # Check if cache has expired
        if cache_key in self._cache_expiry:
            if datetime.utcnow() > self._cache_expiry[cache_key]:
                # Remove expired cache entry
                del self._cache[cache_key]
                del self._cache_expiry[cache_key]
                return False
        
        return True
    
    def _get_cached_report(self, cache_key: str) -> ReportResponse:
        """Get cached report."""
        return self._cache[cache_key]
    
    def _cache_report(self, cache_key: str, response: ReportResponse) -> None:
        """Cache a report response."""
        self._cache[cache_key] = response
        self._cache_expiry[cache_key] = datetime.utcnow() + timedelta(seconds=self._cache_ttl)
        
        # Clean up old cache entries periodically
        self._cleanup_cache()
    
    def _cleanup_cache(self) -> None:
        """Clean up expired cache entries."""
        current_time = datetime.utcnow()
        expired_keys = [
            key for key, expiry in self._cache_expiry.items()
            if current_time > expiry
        ]
        
        for key in expired_keys:
            if key in self._cache:
                del self._cache[key]
            if key in self._cache_expiry:
                del self._cache_expiry[key]
        
        # Also limit cache size to prevent memory issues
        if len(self._cache) > 100:  # Keep only 100 most recent reports
            # Remove oldest entries
            sorted_keys = sorted(
                self._cache_expiry.keys(),
                key=lambda k: self._cache_expiry[k]
            )
            for key in sorted_keys[:-100]:  # Keep last 100
                if key in self._cache:
                    del self._cache[key]
                if key in self._cache_expiry:
                    del self._cache_expiry[key]
    
    def clear_cache(self) -> None:
        """Clear all cached reports."""
        self._cache.clear()
        self._cache_expiry.clear()
        logger.info("Report cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        current_time = datetime.utcnow()
        active_entries = sum(
            1 for expiry in self._cache_expiry.values()
            if current_time <= expiry
        )
        
        return {
            "total_cached_reports": len(self._cache),
            "active_cached_reports": active_entries,
            "cache_ttl_seconds": self._cache_ttl,
            "cache_hit_rate": None  # Could implement hit rate tracking
        }
    
    def set_cache_ttl(self, ttl_seconds: int) -> None:
        """Set cache TTL (time to live) in seconds."""
        self._cache_ttl = ttl_seconds
        logger.info(f"Cache TTL set to {ttl_seconds} seconds") 