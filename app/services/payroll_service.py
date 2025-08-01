"""
Payroll service for business logic operations.

This module provides business logic for payroll calculations, 
tax computations, and payroll processing.
"""

import logging
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List, Dict, Any
import uuid

from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import and_, or_, func
from sqlalchemy.exc import IntegrityError

from app.models.employee import Employee
from app.models.payroll import PayrollRecord, PayPeriod
from app.models.user import User
from app.models.time_entry import TimeEntry
from app.models.enums import EmployeeStatus, PayrollFrequency, PayrollStatus, ApprovalStatus
from app.schemas.payroll import (
    PayrollCalculationRequest, PayrollCalculationResponse,
    PayPeriodCreate, PayrollRecordCreate,
    PayrollBatchRequest, PayrollBatchResponse,
    PayrollSummary
)
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class PayrollService:
    """Service class for payroll-related operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def calculate_employee_payroll(
        self, 
        employee_id: int, 
        pay_period_start: date, 
        pay_period_end: date,
        hours_worked: float = 0,
        overtime_hours: float = 0,
        bonus_amount: float = 0,
        additional_deductions: float = 0,
        use_time_entries: bool = True
    ) -> Dict[str, Any]:
        """
        Calculate payroll for a specific employee.
        
        Args:
            employee_id: Employee ID
            pay_period_start: Start date of pay period
            pay_period_end: End date of pay period
            hours_worked: Regular hours worked (for hourly employees, used if no time entries)
            overtime_hours: Overtime hours worked (used if no time entries)
            bonus_amount: Additional bonus amount
            additional_deductions: Additional deductions
            use_time_entries: Whether to use time entries data if available
            
        Returns:
            Dictionary with payroll calculations
        """
        try:
            # Get employee
            employee = self.get_employee_by_id(employee_id)
            if not employee:
                raise ValueError(f"Employee not found: {employee_id}")
            
            if employee.status != EmployeeStatus.ACTIVE:
                raise ValueError(f"Employee is not active: {employee_id}")
            
            # Get time data (from time entries if available, otherwise use provided hours)
            time_data = self._get_time_data(employee_id, pay_period_start, pay_period_end, hours_worked, overtime_hours, use_time_entries)
            
            # Calculate gross pay
            gross_pay = self._calculate_gross_pay(employee, time_data["hours_worked"], time_data["overtime_hours"], bonus_amount)
            
            # Calculate deductions
            deductions = self._calculate_deductions(employee, gross_pay)
            
            # Add additional deductions
            if additional_deductions > 0:
                deductions["other_deductions"] = Decimal(str(additional_deductions))
                deductions["total_deductions"] += Decimal(str(additional_deductions))
            
            # Calculate net pay
            net_pay = gross_pay - deductions["total_deductions"]
            
            # Prepare payroll data
            payroll_data = {
                "employee_id": employee_id,
                "employee_name": employee.full_name,
                "pay_period_start": pay_period_start,
                "pay_period_end": pay_period_end,
                "hours_worked": Decimal(str(time_data["hours_worked"])),
                "overtime_hours": Decimal(str(time_data["overtime_hours"])),
                "regular_hours": Decimal(str(time_data["regular_hours"])),
                "double_time_hours": Decimal(str(time_data["double_time_hours"])),
                "time_entries_used": time_data["time_entries_used"],
                "time_entries_count": time_data["time_entries_count"],
                "gross_pay": gross_pay,
                "tax_deductions": {
                    "federal_income_tax": deductions.get("federal_income_tax", Decimal('0.00')),
                    "state_income_tax": deductions.get("state_income_tax", Decimal('0.00')),
                    "social_security_tax": deductions.get("social_security_tax", Decimal('0.00')),
                    "medicare_tax": deductions.get("medicare_tax", Decimal('0.00'))
                },
                "benefit_deductions": {
                    "health_insurance": deductions.get("health_insurance", Decimal('0.00')),
                    "dental_insurance": deductions.get("dental_insurance", Decimal('0.00')),
                    "vision_insurance": deductions.get("vision_insurance", Decimal('0.00')),
                    "retirement_401k": deductions.get("retirement_401k", Decimal('0.00'))
                },
                "other_deductions": {
                    "other_deductions": deductions.get("other_deductions", Decimal('0.00'))
                },
                "total_deductions": deductions["total_deductions"],
                "net_pay": net_pay,
                "calculated_at": datetime.utcnow()
            }
            
            logger.info(f"Payroll calculated for employee {employee_id}: ${net_pay}")
            return payroll_data
            
        except Exception as e:
            logger.error(f"Error calculating payroll for employee {employee_id}: {e}")
            raise
    
    def _calculate_gross_pay(
        self, 
        employee: Employee, 
        hours_worked: float, 
        overtime_hours: float,
        bonus_amount: float = 0
    ) -> Decimal:
        """Calculate gross pay for an employee."""
        try:
            gross_pay = Decimal('0.00')
            
            if employee.is_salaried:
                # Calculate salary-based pay
                if employee.payroll_frequency == PayrollFrequency.WEEKLY:
                    gross_pay = Decimal(str(employee.salary)) / 52
                elif employee.payroll_frequency == PayrollFrequency.BIWEEKLY:
                    gross_pay = Decimal(str(employee.salary)) / 26
                elif employee.payroll_frequency == PayrollFrequency.SEMI_MONTHLY:
                    gross_pay = Decimal(str(employee.salary)) / 24
                elif employee.payroll_frequency == PayrollFrequency.MONTHLY:
                    gross_pay = Decimal(str(employee.salary)) / 12
                else:
                    gross_pay = Decimal(str(employee.salary))
            
            elif employee.is_hourly:
                # Calculate hourly-based pay
                regular_pay = Decimal(str(employee.hourly_rate)) * Decimal(str(hours_worked))
                overtime_pay = employee.calculate_overtime_pay(overtime_hours)
                gross_pay = regular_pay + overtime_pay
            
            # Add bonus
            if bonus_amount > 0:
                gross_pay += Decimal(str(bonus_amount))
            
            return gross_pay.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
        except Exception as e:
            logger.error(f"Error calculating gross pay: {e}")
            raise
    
    def _get_time_data(
        self, 
        employee_id: int, 
        pay_period_start: date, 
        pay_period_end: date, 
        fallback_hours: float = 0, 
        fallback_overtime: float = 0,
        use_time_entries: bool = True
    ) -> Dict[str, Any]:
        """Get time data from time entries or fallback to provided hours."""
        try:
            time_data = {
                "hours_worked": fallback_hours,
                "regular_hours": fallback_hours,
                "overtime_hours": fallback_overtime,
                "double_time_hours": 0.0,
                "time_entries_used": False,
                "time_entries_count": 0
            }
            
            if not use_time_entries:
                return time_data
            
            # Get approved time entries for the pay period
            time_entries = self.db.query(TimeEntry).filter(
                TimeEntry.employee_id == employee_id,
                TimeEntry.work_date >= pay_period_start,
                TimeEntry.work_date <= pay_period_end,
                TimeEntry.approval_status == ApprovalStatus.APPROVED
            ).all()
            
            if time_entries:
                # Calculate totals from time entries
                total_hours = sum(entry.total_hours or Decimal('0.00') for entry in time_entries)
                regular_hours = sum(entry.regular_hours or Decimal('0.00') for entry in time_entries)
                overtime_hours = sum(entry.overtime_hours or Decimal('0.00') for entry in time_entries)
                double_time_hours = sum(entry.double_time_hours or Decimal('0.00') for entry in time_entries)
                
                time_data.update({
                    "hours_worked": float(total_hours),
                    "regular_hours": float(regular_hours),
                    "overtime_hours": float(overtime_hours),
                    "double_time_hours": float(double_time_hours),
                    "time_entries_used": True,
                    "time_entries_count": len(time_entries)
                })
                
                logger.info(f"Using time entries for employee {employee_id}: {len(time_entries)} entries, {total_hours} total hours")
            else:
                logger.info(f"No approved time entries found for employee {employee_id}, using fallback hours: {fallback_hours}")
            
            return time_data
            
        except Exception as e:
            logger.error(f"Error getting time data for employee {employee_id}: {e}")
            # Return fallback data on error
            return {
                "hours_worked": fallback_hours,
                "regular_hours": fallback_hours,
                "overtime_hours": fallback_overtime,
                "double_time_hours": 0.0,
                "time_entries_used": False,
                "time_entries_count": 0
            }
    
    def _calculate_deductions(self, employee: Employee, gross_pay: Decimal) -> Dict[str, Any]:
        """Calculate all deductions for an employee."""
        try:
            deductions = {}
            
            # Tax deductions
            tax_deductions = self._calculate_tax_deductions(employee, gross_pay)
            deductions.update(tax_deductions)
            
            # Benefit deductions
            benefit_deductions = self._calculate_benefit_deductions(employee, gross_pay)
            deductions.update(benefit_deductions)
            
            # Calculate total deductions
            total_deductions = sum(
                value for key, value in deductions.items() 
                if key != "total_deductions" and isinstance(value, Decimal)
            )
            
            deductions["total_deductions"] = total_deductions.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            return deductions
            
        except Exception as e:
            logger.error(f"Error calculating deductions: {e}")
            raise
    
    def _calculate_tax_deductions(self, employee: Employee, gross_pay: Decimal) -> Dict[str, Decimal]:
        """Calculate tax deductions."""
        try:
            tax_deductions = {}
            
            # Federal income tax (simplified calculation)
            federal_income_tax = self._calculate_federal_income_tax(employee, gross_pay)
            tax_deductions["federal_income_tax"] = federal_income_tax
            
            # State income tax (simplified calculation)
            state_income_tax = self._calculate_state_income_tax(employee, gross_pay)
            tax_deductions["state_income_tax"] = state_income_tax
            
            # Social Security tax (6.2% up to wage base)
            social_security_tax = gross_pay * Decimal(str(settings.SOCIAL_SECURITY_RATE))
            tax_deductions["social_security_tax"] = social_security_tax.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            # Medicare tax (1.45%)
            medicare_tax = gross_pay * Decimal(str(settings.MEDICARE_RATE))
            tax_deductions["medicare_tax"] = medicare_tax.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            return tax_deductions
            
        except Exception as e:
            logger.error(f"Error calculating tax deductions: {e}")
            raise
    
    def _calculate_federal_income_tax(self, employee: Employee, gross_pay: Decimal) -> Decimal:
        """Calculate federal income tax (simplified)."""
        try:
            # This is a simplified calculation
            # In a real system, you would use actual tax tables and brackets
            
            # Base calculation using default tax rate
            base_tax = gross_pay * Decimal(str(settings.DEFAULT_TAX_RATE))
            
            # Apply allowances (simplified)
            allowance_reduction = Decimal(str(employee.federal_allowances)) * Decimal('50.00')
            federal_tax = base_tax - allowance_reduction
            
            # Add additional withholding
            federal_tax += Decimal(str(employee.additional_federal_withholding))
            
            # Ensure tax is not negative
            federal_tax = max(federal_tax, Decimal('0.00'))
            
            return federal_tax.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
        except Exception as e:
            logger.error(f"Error calculating federal income tax: {e}")
            return Decimal('0.00')
    
    def _calculate_state_income_tax(self, employee: Employee, gross_pay: Decimal) -> Decimal:
        """Calculate state income tax (simplified)."""
        try:
            # This is a simplified calculation
            # In a real system, you would use state-specific tax tables
            
            # Base calculation (5% as example)
            base_tax = gross_pay * Decimal('0.05')
            
            # Apply allowances (simplified)
            allowance_reduction = Decimal(str(employee.state_allowances)) * Decimal('25.00')
            state_tax = base_tax - allowance_reduction
            
            # Add additional withholding
            state_tax += Decimal(str(employee.additional_state_withholding))
            
            # Ensure tax is not negative
            state_tax = max(state_tax, Decimal('0.00'))
            
            return state_tax.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
        except Exception as e:
            logger.error(f"Error calculating state income tax: {e}")
            return Decimal('0.00')
    
    def _calculate_benefit_deductions(self, employee: Employee, gross_pay: Decimal) -> Dict[str, Decimal]:
        """Calculate benefit deductions."""
        try:
            benefit_deductions = {}
            
            # Health insurance
            if employee.health_insurance:
                health_insurance = self._prorate_monthly_deduction(
                    Decimal('200.00'), 
                    employee.payroll_frequency
                )
                benefit_deductions["health_insurance"] = health_insurance
            
            # Dental insurance
            if employee.dental_insurance:
                dental_insurance = self._prorate_monthly_deduction(
                    Decimal('50.00'), 
                    employee.payroll_frequency
                )
                benefit_deductions["dental_insurance"] = dental_insurance
            
            # Vision insurance
            if employee.vision_insurance:
                vision_insurance = self._prorate_monthly_deduction(
                    Decimal('25.00'), 
                    employee.payroll_frequency
                )
                benefit_deductions["vision_insurance"] = vision_insurance
            
            # 401k contribution
            if employee.retirement_401k and employee.retirement_401k_percent > 0:
                retirement_401k = gross_pay * (Decimal(str(employee.retirement_401k_percent)) / 100)
                benefit_deductions["retirement_401k"] = retirement_401k.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            return benefit_deductions
            
        except Exception as e:
            logger.error(f"Error calculating benefit deductions: {e}")
            raise
    
    def _prorate_monthly_deduction(self, monthly_amount: Decimal, frequency: PayrollFrequency) -> Decimal:
        """Prorate monthly deduction amount based on payroll frequency."""
        try:
            if frequency == PayrollFrequency.WEEKLY:
                return (monthly_amount * 12 / 52).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            elif frequency == PayrollFrequency.BIWEEKLY:
                return (monthly_amount * 12 / 26).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            elif frequency == PayrollFrequency.SEMI_MONTHLY:
                return (monthly_amount / 2).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            elif frequency == PayrollFrequency.MONTHLY:
                return monthly_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            else:
                return monthly_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                
        except Exception as e:
            logger.error(f"Error prorating monthly deduction: {e}")
            return Decimal('0.00')
    
    def get_employee_by_id(self, employee_id: int) -> Optional[Employee]:
        """Get employee by ID with optimized loading."""
        return self.db.query(Employee).options(
            joinedload(Employee.user),
            joinedload(Employee.manager)
        ).filter(Employee.id == employee_id).first()
    
    def create_payroll_record(
        self, 
        employee_id: int, 
        pay_period_id: int, 
        hours_worked: float = 0,
        overtime_hours: float = 0,
        process_immediately: bool = False
    ) -> PayrollRecord:
        """Create a payroll record for an employee."""
        try:
            # Get pay period
            pay_period = self.get_pay_period(pay_period_id)
            if not pay_period:
                raise ValueError(f"Pay period not found: {pay_period_id}")
            
            # Calculate payroll
            payroll_data = self.calculate_employee_payroll(
                employee_id=employee_id,
                pay_period_start=pay_period.start_date,
                pay_period_end=pay_period.end_date,
                hours_worked=hours_worked,
                overtime_hours=overtime_hours
            )
            
            # Create payroll record
            payroll_record = PayrollRecord(
                employee_id=employee_id,
                pay_period_id=pay_period_id,
                hours_worked=payroll_data["hours_worked"],
                overtime_hours=payroll_data["overtime_hours"],
                gross_pay=payroll_data["gross_pay"],
                net_pay=payroll_data["net_pay"],
                federal_income_tax=payroll_data["tax_deductions"]["federal_income_tax"],
                state_income_tax=payroll_data["tax_deductions"]["state_income_tax"],
                social_security_tax=payroll_data["tax_deductions"]["social_security_tax"],
                medicare_tax=payroll_data["tax_deductions"]["medicare_tax"],
                health_insurance=payroll_data["benefit_deductions"]["health_insurance"],
                dental_insurance=payroll_data["benefit_deductions"]["dental_insurance"],
                vision_insurance=payroll_data["benefit_deductions"]["vision_insurance"],
                retirement_401k=payroll_data["benefit_deductions"]["retirement_401k"],
                other_deductions=payroll_data["other_deductions"].get("other_deductions", Decimal('0.00')),
                total_deductions=payroll_data["total_deductions"],
                status=PayrollStatus.PROCESSED if process_immediately else PayrollStatus.DRAFT,
                processed_at=datetime.utcnow() if process_immediately else None
            )
            
            self.db.add(payroll_record)
            self.db.commit()
            self.db.refresh(payroll_record)
            
            return payroll_record
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating payroll record: {e}")
            raise
    
    def create_pay_period(self, pay_period_data: PayPeriodCreate) -> PayPeriod:
        """Create a new pay period."""
        try:
            # Check for overlapping pay periods with improved logic
            # Two periods overlap if one starts before the other ends
            # Period A overlaps with Period B if:
            # (A.start <= B.end) AND (B.start <= A.end)
            existing_period = self.db.query(PayPeriod).filter(
                and_(
                    PayPeriod.start_date <= pay_period_data.end_date,
                    PayPeriod.end_date >= pay_period_data.start_date
                )
            ).first()
            
            if existing_period:
                # Check for exact adjacent periods (end of one = start of next)
                # These should be allowed as they don't actually overlap
                if (existing_period.end_date == pay_period_data.start_date or 
                    existing_period.start_date == pay_period_data.end_date):
                    # Adjacent periods are OK, continue with creation
                    pass
                else:
                    raise ValueError(
                        f"Pay period ({pay_period_data.start_date} to {pay_period_data.end_date}) "
                        f"overlaps with existing period ({existing_period.start_date} to {existing_period.end_date})"
                    )
            
            # Validate that start date is before end date
            if pay_period_data.start_date >= pay_period_data.end_date:
                raise ValueError("Pay period start date must be before end date")
            
            # Validate that pay date is not before start date
            if pay_period_data.pay_date < pay_period_data.start_date:
                raise ValueError("Pay date cannot be before the start of the pay period")
            
            pay_period = PayPeriod(**pay_period_data.model_dump())
            self.db.add(pay_period)
            self.db.commit()
            self.db.refresh(pay_period)
            
            return pay_period
            
        except IntegrityError as e:
            self.db.rollback()
            raise ValueError(f"Database integrity error: {str(e)}")
        except Exception as e:
            self.db.rollback()
            raise
    
    def get_pay_period(self, pay_period_id: int) -> Optional[PayPeriod]:
        """Get pay period by ID."""
        return self.db.query(PayPeriod).filter(PayPeriod.id == pay_period_id).first()
    
    def get_pay_periods(
        self, 
        skip: int = 0, 
        limit: int = 100,
        frequency: Optional[PayrollFrequency] = None,
        is_processed: Optional[bool] = None
    ) -> List[PayPeriod]:
        """Get pay periods with optimized loading and filtering."""
        query = self.db.query(PayPeriod).options(
            selectinload(PayPeriod.payroll_records)
        )
        
        # Apply filters
        if frequency:
            query = query.filter(PayPeriod.frequency == frequency)
        
        if is_processed is not None:
            query = query.filter(PayPeriod.is_processed == is_processed)
        
        # Order by most recent first
        query = query.order_by(PayPeriod.start_date.desc())
        
        return query.offset(skip).limit(limit).all()
    
    def get_current_pay_period(self) -> Optional[PayPeriod]:
        """Get the current pay period with optimized loading."""
        today = date.today()
        return self.db.query(PayPeriod).options(
            selectinload(PayPeriod.payroll_records)
        ).filter(
            and_(
                PayPeriod.start_date <= today,
                PayPeriod.end_date >= today
            )
        ).first()
    
    def process_payroll_batch(
        self, 
        pay_period_id: int, 
        employee_ids: List[int],
        process_immediately: bool = False
    ) -> Dict[str, Any]:
        """Process payroll for multiple employees."""
        try:
            start_time = datetime.utcnow()
            batch_id = f"batch_{start_time.strftime('%Y_%m_%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
            
            processed_count = 0
            error_count = 0
            errors = []
            total_gross_pay = Decimal('0.00')
            total_net_pay = Decimal('0.00')
            total_deductions = Decimal('0.00')
            
            for employee_id in employee_ids:
                try:
                    # Create payroll record for each employee
                    payroll_record = self.create_payroll_record(
                        employee_id=employee_id,
                        pay_period_id=pay_period_id,
                        process_immediately=process_immediately
                    )
                    
                    processed_count += 1
                    total_gross_pay += payroll_record.gross_pay
                    total_net_pay += payroll_record.net_pay
                    total_deductions += payroll_record.total_deductions
                    
                except Exception as e:
                    error_count += 1
                    errors.append(f"Employee {employee_id}: {str(e)}")
                    logger.error(f"Error processing payroll for employee {employee_id}: {e}")
            
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds()
            
            return {
                "batch_id": batch_id,
                "pay_period_id": pay_period_id,
                "processed_count": processed_count,
                "error_count": error_count,
                "total_gross_pay": total_gross_pay,
                "total_net_pay": total_net_pay,
                "total_deductions": total_deductions,
                "processing_time": processing_time,
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"Error processing payroll batch: {e}")
            raise
    
    def get_payroll_records(
        self, 
        pay_period_id: Optional[int] = None,
        employee_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[PayrollRecord]:
        """Get payroll records with optimized loading and filtering."""
        query = self.db.query(PayrollRecord).options(
            joinedload(PayrollRecord.employee),
            joinedload(PayrollRecord.pay_period),
            joinedload(PayrollRecord.processed_by_user)
        )
        
        if pay_period_id:
            query = query.filter(PayrollRecord.pay_period_id == pay_period_id)
        
        if employee_id:
            query = query.filter(PayrollRecord.employee_id == employee_id)
        
        # Order by most recent first
        query = query.order_by(PayrollRecord.created_at.desc())
        
        return query.offset(skip).limit(limit).all()
    
    def get_payroll_record_by_id(self, record_id: int) -> Optional[PayrollRecord]:
        """Get payroll record by ID with optimized loading."""
        return self.db.query(PayrollRecord).options(
            joinedload(PayrollRecord.employee),
            joinedload(PayrollRecord.pay_period),
            joinedload(PayrollRecord.processed_by_user)
        ).filter(PayrollRecord.id == record_id).first()
    
    def get_payroll_summary(self, pay_period_id: int) -> Dict[str, Any]:
        """Get payroll summary for a pay period with optimized queries."""
        try:
            # Get pay period with records
            pay_period = self.db.query(PayPeriod).options(
                selectinload(PayPeriod.payroll_records)
            ).filter(PayPeriod.id == pay_period_id).first()
            
            if not pay_period:
                raise ValueError(f"Pay period not found: {pay_period_id}")
            
            # Use aggregation query for summary statistics
            summary_query = self.db.query(
                func.count(PayrollRecord.id).label('total_records'),
                func.sum(PayrollRecord.gross_pay).label('total_gross_pay'),
                func.sum(PayrollRecord.net_pay).label('total_net_pay'),
                func.sum(PayrollRecord.total_deductions).label('total_deductions'),
                func.sum(PayrollRecord.federal_income_tax).label('total_federal_tax'),
                func.sum(PayrollRecord.state_income_tax).label('total_state_tax'),
                func.sum(PayrollRecord.social_security_tax).label('total_social_security'),
                func.sum(PayrollRecord.medicare_tax).label('total_medicare'),
                func.sum(PayrollRecord.hours_worked).label('total_hours_worked'),
                func.sum(PayrollRecord.overtime_hours).label('total_overtime_hours')
            ).filter(PayrollRecord.pay_period_id == pay_period_id)
            
            summary = summary_query.first()
            
            # Get count by status
            status_counts = self.db.query(
                PayrollRecord.status,
                func.count(PayrollRecord.id).label('count')
            ).filter(
                PayrollRecord.pay_period_id == pay_period_id
            ).group_by(PayrollRecord.status).all()
            
            return {
                "pay_period_id": pay_period_id,
                "period_start": pay_period.start_date,
                "period_end": pay_period.end_date,
                "pay_date": pay_period.pay_date,
                "total_records": summary.total_records or 0,
                "total_gross_pay": summary.total_gross_pay or Decimal('0.00'),
                "total_net_pay": summary.total_net_pay or Decimal('0.00'),
                "total_deductions": summary.total_deductions or Decimal('0.00'),
                "total_federal_tax": summary.total_federal_tax or Decimal('0.00'),
                "total_state_tax": summary.total_state_tax or Decimal('0.00'),
                "total_social_security": summary.total_social_security or Decimal('0.00'),
                "total_medicare": summary.total_medicare or Decimal('0.00'),
                "total_hours_worked": summary.total_hours_worked or Decimal('0.00'),
                "total_overtime_hours": summary.total_overtime_hours or Decimal('0.00'),
                "status_counts": {status.value: count for status, count in status_counts}
            }
            
        except Exception as e:
            logger.error(f"Error getting payroll summary: {e}")
            raise
    
    def get_time_entries_for_payroll(
        self, 
        employee_id: int, 
        pay_period_start: date, 
        pay_period_end: date
    ) -> List[TimeEntry]:
        """Get time entries for payroll processing with optimized loading."""
        try:
            time_entries = self.db.query(TimeEntry).options(
                joinedload(TimeEntry.employee),
                joinedload(TimeEntry.approver)
            ).filter(
                TimeEntry.employee_id == employee_id,
                TimeEntry.work_date >= pay_period_start,
                TimeEntry.work_date <= pay_period_end,
                TimeEntry.approval_status == ApprovalStatus.APPROVED
            ).order_by(TimeEntry.work_date).all()
            
            return time_entries
            
        except Exception as e:
            logger.error(f"Error getting time entries for payroll: {e}")
            raise
    
    def validate_time_entries_for_payroll(
        self, 
        employee_id: int, 
        pay_period_start: date, 
        pay_period_end: date
    ) -> Dict[str, Any]:
        """Validate time entries for payroll processing."""
        try:
            time_entries = self.get_time_entries_for_payroll(employee_id, pay_period_start, pay_period_end)
            
            total_entries = len(time_entries)
            total_hours = sum(entry.total_hours or Decimal('0.00') for entry in time_entries)
            total_overtime = sum(entry.overtime_hours or Decimal('0.00') for entry in time_entries)
            
            # Check for missing days (business days only)
            from datetime import timedelta
            business_days = []
            current_date = pay_period_start
            while current_date <= pay_period_end:
                if current_date.weekday() < 5:  # Monday to Friday
                    business_days.append(current_date)
                current_date += timedelta(days=1)
            
            entry_dates = [entry.work_date for entry in time_entries]
            missing_days = [day for day in business_days if day not in entry_dates]
            
            validation_result = {
                "employee_id": employee_id,
                "pay_period_start": pay_period_start,
                "pay_period_end": pay_period_end,
                "total_entries": total_entries,
                "total_hours": float(total_hours),
                "total_overtime": float(total_overtime),
                "business_days_count": len(business_days),
                "missing_days_count": len(missing_days),
                "missing_days": missing_days,
                "has_missing_days": len(missing_days) > 0,
                "is_valid_for_payroll": len(missing_days) == 0 and total_hours > 0,
                "validation_warnings": []
            }
            
            # Add warnings
            if len(missing_days) > 0:
                validation_result["validation_warnings"].append(f"Missing time entries for {len(missing_days)} business days")
            
            if total_hours == 0:
                validation_result["validation_warnings"].append("No hours recorded for pay period")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating time entries for payroll: {e}")
            raise 