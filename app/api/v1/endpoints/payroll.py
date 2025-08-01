"""
Payroll API endpoints for payroll management.

This module provides comprehensive REST API endpoints for managing payroll
including calculations, pay periods, batch processing, and payroll records.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_admin
from app.models.user import User
from app.models.payroll import PayrollRecord, PayPeriod
from app.models.enums import PayrollStatus, PayrollFrequency
from app.schemas.payroll import (
    PayrollCalculationRequest, PayrollCalculationResponse,
    PayPeriodCreate, PayPeriodResponse,
    PayrollRecordCreate, PayrollRecordResponse,
    PayrollBatchRequest, PayrollBatchResponse,
    PayrollSummary
)
from app.services.payroll_service import PayrollService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/calculate", response_model=PayrollCalculationResponse)
async def calculate_payroll(
    request: PayrollCalculationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Calculate payroll for a single employee.
    
    **Required permissions**: Admin
    
    **Features**:
    - Calculate gross pay based on salary or hourly rate
    - Calculate tax deductions (federal, state, social security, medicare)
    - Calculate benefit deductions
    - Calculate net pay
    - Support for bonus, commission, and overtime
    """
    try:
        payroll_service = PayrollService(db)
        
        # Calculate payroll
        payroll_data = payroll_service.calculate_employee_payroll(
            employee_id=request.employee_id,
            pay_period_start=request.pay_period_start,
            pay_period_end=request.pay_period_end,
            hours_worked=float(request.hours_worked or 0),
            overtime_hours=float(request.overtime_hours or 0),
            bonus_amount=float(request.bonus_amount or 0),
            additional_deductions=float(request.additional_deductions or 0)
        )
        
        return PayrollCalculationResponse(**payroll_data)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error calculating payroll: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during payroll calculation"
        )


@router.post("/process-batch", response_model=PayrollBatchResponse)
async def process_payroll_batch(
    request: PayrollBatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Process payroll for multiple employees in batch.
    
    **Required permissions**: Admin
    
    **Features**:
    - Process multiple employees simultaneously
    - Create payroll records for all employees
    - Option to save as draft or process immediately
    - Detailed error reporting
    - Performance metrics
    """
    try:
        payroll_service = PayrollService(db)
        
        # Process batch
        batch_result = payroll_service.process_payroll_batch(
            pay_period_id=request.pay_period_id,
            employee_ids=request.employee_ids,
            process_immediately=request.process_immediately
        )
        
        return PayrollBatchResponse(**batch_result)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error processing payroll batch: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during batch processing"
        )


@router.get("/records", response_model=List[PayrollRecordResponse])
async def get_payroll_records(
    pay_period_id: Optional[int] = Query(None, description="Filter by pay period ID"),
    employee_id: Optional[int] = Query(None, description="Filter by employee ID"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get payroll records with optional filtering.
    
    **Required permissions**: Any authenticated user
    
    **Features**:
    - Filter by pay period or employee
    - Pagination support
    - Detailed payroll information
    - Computed fields (tax totals, take-home percentage)
    """
    try:
        payroll_service = PayrollService(db)
        
        records = payroll_service.get_payroll_records(
            pay_period_id=pay_period_id,
            employee_id=employee_id,
            skip=skip,
            limit=limit
        )
        
        # Convert to response format
        response_records = []
        for record in records:
            response_records.append(PayrollRecordResponse(
                id=record.id,
                employee_id=record.employee_id,
                pay_period_id=record.pay_period_id,
                hours_worked=record.hours_worked,
                overtime_hours=record.overtime_hours,
                gross_pay=record.gross_pay,
                net_pay=record.net_pay,
                federal_income_tax=record.federal_income_tax,
                state_income_tax=record.state_income_tax,
                social_security_tax=record.social_security_tax,
                medicare_tax=record.medicare_tax,
                health_insurance=record.health_insurance,
                dental_insurance=record.dental_insurance,
                vision_insurance=record.vision_insurance,
                retirement_401k=record.retirement_401k,
                total_deductions=record.total_deductions,
                status=record.status,
                processed_at=record.processed_at,
                notes=record.notes,
                tax_deductions_total=record.tax_deductions_total,
                benefit_deductions_total=record.benefit_deductions_total,
                take_home_percentage=record.take_home_percentage,
                created_at=record.created_at,
                updated_at=record.updated_at
            ))
        
        return response_records
        
    except Exception as e:
        logger.error(f"Error getting payroll records: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/records/{record_id}", response_model=PayrollRecordResponse)
async def get_payroll_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get specific payroll record by ID.
    
    **Required permissions**: Any authenticated user
    
    **Features**:
    - Detailed payroll record information
    - Computed fields and breakdowns
    """
    try:
        record = db.query(PayrollRecord).filter(PayrollRecord.id == record_id).first()
        
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payroll record not found"
            )
        
        return PayrollRecordResponse(
            id=record.id,
            employee_id=record.employee_id,
            pay_period_id=record.pay_period_id,
            hours_worked=record.hours_worked,
            overtime_hours=record.overtime_hours,
            gross_pay=record.gross_pay,
            net_pay=record.net_pay,
            federal_income_tax=record.federal_income_tax,
            state_income_tax=record.state_income_tax,
            social_security_tax=record.social_security_tax,
            medicare_tax=record.medicare_tax,
            health_insurance=record.health_insurance,
            dental_insurance=record.dental_insurance,
            vision_insurance=record.vision_insurance,
            retirement_401k=record.retirement_401k,
            total_deductions=record.total_deductions,
            status=record.status,
            processed_at=record.processed_at,
            notes=record.notes,
            tax_deductions_total=record.tax_deductions_total,
            benefit_deductions_total=record.benefit_deductions_total,
            take_home_percentage=record.take_home_percentage,
            created_at=record.created_at,
            updated_at=record.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting payroll record: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/summary/{pay_period_id}", response_model=PayrollSummary)
async def get_payroll_summary(
    pay_period_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get payroll summary for a specific pay period.
    
    **Required permissions**: Any authenticated user
    
    **Features**:
    - Total employees processed
    - Aggregate payroll amounts
    - Average pay calculations
    - Processing status breakdown
    """
    try:
        payroll_service = PayrollService(db)
        
        summary = payroll_service.get_payroll_summary(pay_period_id)
        
        return PayrollSummary(**summary)
        
    except Exception as e:
        logger.error(f"Error getting payroll summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# Pay Period Endpoints
@router.post("/pay-periods", response_model=PayPeriodResponse, status_code=status.HTTP_201_CREATED)
async def create_pay_period(
    pay_period_data: PayPeriodCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Create a new pay period.
    
    **Required permissions**: Admin
    
    **Features**:
    - Validate pay period dates
    - Check for overlapping periods
    - Support for different frequencies
    - Holiday period marking
    """
    try:
        payroll_service = PayrollService(db)
        
        pay_period = payroll_service.create_pay_period(pay_period_data)
        
        return PayPeriodResponse(
            id=pay_period.id,
            start_date=pay_period.start_date,
            end_date=pay_period.end_date,
            pay_date=pay_period.pay_date,
            frequency=pay_period.frequency,
            description=pay_period.description,
            is_holiday_period=pay_period.is_holiday_period,
            is_processed=pay_period.is_processed,
            period_days=pay_period.period_days,
            is_current_period=pay_period.is_current_period,
            created_at=pay_period.created_at,
            updated_at=pay_period.updated_at
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating pay period: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/pay-periods", response_model=List[PayPeriodResponse])
async def get_pay_periods(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get list of pay periods.
    
    **Required permissions**: Any authenticated user
    
    **Features**:
    - Pagination support
    - Chronological ordering
    - Computed fields (period days, current period)
    """
    try:
        payroll_service = PayrollService(db)
        
        pay_periods = payroll_service.get_pay_periods(skip=skip, limit=limit)
        
        response_periods = []
        for period in pay_periods:
            response_periods.append(PayPeriodResponse(
                id=period.id,
                start_date=period.start_date,
                end_date=period.end_date,
                pay_date=period.pay_date,
                frequency=period.frequency,
                description=period.description,
                is_holiday_period=period.is_holiday_period,
                is_processed=period.is_processed,
                period_days=period.period_days,
                is_current_period=period.is_current_period,
                created_at=period.created_at,
                updated_at=period.updated_at
            ))
        
        return response_periods
        
    except Exception as e:
        logger.error(f"Error getting pay periods: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/pay-periods/{pay_period_id}", response_model=PayPeriodResponse)
async def get_pay_period(
    pay_period_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get specific pay period by ID.
    
    **Required permissions**: Any authenticated user
    
    **Features**:
    - Detailed pay period information
    - Computed fields
    """
    try:
        payroll_service = PayrollService(db)
        
        pay_period = payroll_service.get_pay_period(pay_period_id)
        
        if not pay_period:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pay period not found"
            )
        
        return PayPeriodResponse(
            id=pay_period.id,
            start_date=pay_period.start_date,
            end_date=pay_period.end_date,
            pay_date=pay_period.pay_date,
            frequency=pay_period.frequency,
            description=pay_period.description,
            is_holiday_period=pay_period.is_holiday_period,
            is_processed=pay_period.is_processed,
            period_days=pay_period.period_days,
            is_current_period=pay_period.is_current_period,
            created_at=pay_period.created_at,
            updated_at=pay_period.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting pay period: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/pay-periods/current", response_model=PayPeriodResponse)
async def get_current_pay_period(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the current pay period.
    
    **Required permissions**: Any authenticated user
    
    **Features**:
    - Automatically determine current period based on today's date
    - Useful for payroll processing
    """
    try:
        payroll_service = PayrollService(db)
        
        pay_period = payroll_service.get_current_pay_period()
        
        if not pay_period:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No current pay period found"
            )
        
        return PayPeriodResponse(
            id=pay_period.id,
            start_date=pay_period.start_date,
            end_date=pay_period.end_date,
            pay_date=pay_period.pay_date,
            frequency=pay_period.frequency,
            description=pay_period.description,
            is_holiday_period=pay_period.is_holiday_period,
            is_processed=pay_period.is_processed,
            period_days=pay_period.period_days,
            is_current_period=pay_period.is_current_period,
            created_at=pay_period.created_at,
            updated_at=pay_period.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting current pay period: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# Time Entry Integration Endpoints
@router.get("/time-entries/validate/{employee_id}")
async def validate_time_entries_for_payroll(
    employee_id: int,
    pay_period_start: date = Query(..., description="Pay period start date"),
    pay_period_end: date = Query(..., description="Pay period end date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Validate time entries for payroll processing.
    
    **Required permissions**: Any authenticated user
    
    **Features**:
    - Validate time entries completeness
    - Check for missing business days
    - Calculate total hours and overtime
    - Provide validation warnings
    """
    try:
        payroll_service = PayrollService(db)
        
        validation_result = payroll_service.validate_time_entries_for_payroll(
            employee_id=employee_id,
            pay_period_start=pay_period_start,
            pay_period_end=pay_period_end
        )
        
        return validation_result
        
    except Exception as e:
        logger.error(f"Error validating time entries for payroll: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/time-entries/{employee_id}")
async def get_time_entries_for_payroll(
    employee_id: int,
    pay_period_start: date = Query(..., description="Pay period start date"),
    pay_period_end: date = Query(..., description="Pay period end date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get time entries for payroll processing.
    
    **Required permissions**: Any authenticated user
    
    **Features**:
    - Get approved time entries for pay period
    - Calculate total hours worked
    - Include overtime calculations
    """
    try:
        payroll_service = PayrollService(db)
        
        time_entries = payroll_service.get_time_entries_for_payroll(
            employee_id=employee_id,
            pay_period_start=pay_period_start,
            pay_period_end=pay_period_end
        )
        
        # Calculate totals
        total_hours = sum(entry.total_hours or 0 for entry in time_entries)
        total_overtime = sum(entry.overtime_hours or 0 for entry in time_entries)
        total_regular = sum(entry.regular_hours or 0 for entry in time_entries)
        
        return {
            "employee_id": employee_id,
            "pay_period_start": pay_period_start,
            "pay_period_end": pay_period_end,
            "time_entries_count": len(time_entries),
            "total_hours": float(total_hours),
            "total_regular_hours": float(total_regular),
            "total_overtime_hours": float(total_overtime),
            "time_entries": [
                {
                    "id": entry.id,
                    "work_date": entry.work_date,
                    "total_hours": float(entry.total_hours or 0),
                    "regular_hours": float(entry.regular_hours or 0),
                    "overtime_hours": float(entry.overtime_hours or 0),
                    "status": entry.status,
                    "approval_status": entry.approval_status
                }
                for entry in time_entries
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting time entries for payroll: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/calculate-with-time-entries", response_model=PayrollCalculationResponse)
async def calculate_payroll_with_time_entries(
    request: PayrollCalculationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Calculate payroll using time entries data.
    
    **Required permissions**: Admin
    
    **Features**:
    - Automatically use approved time entries
    - Fallback to manual hours if no time entries
    - Include time entry validation
    - Enhanced payroll calculations
    """
    try:
        payroll_service = PayrollService(db)
        
        # Calculate payroll with time entries integration
        payroll_data = payroll_service.calculate_employee_payroll(
            employee_id=request.employee_id,
            pay_period_start=request.pay_period_start,
            pay_period_end=request.pay_period_end,
            hours_worked=request.hours_worked,
            overtime_hours=request.overtime_hours,
            bonus_amount=request.bonus_amount,
            additional_deductions=request.additional_deductions,
            use_time_entries=True  # Enable time entries integration
        )
        
        return PayrollCalculationResponse(
            employee_id=payroll_data["employee_id"],
            employee_name=payroll_data["employee_name"],
            pay_period_start=payroll_data["pay_period_start"],
            pay_period_end=payroll_data["pay_period_end"],
            hours_worked=payroll_data["hours_worked"],
            overtime_hours=payroll_data["overtime_hours"],
            gross_pay=payroll_data["gross_pay"],
            federal_income_tax=payroll_data["tax_deductions"]["federal_income_tax"],
            state_income_tax=payroll_data["tax_deductions"]["state_income_tax"],
            social_security_tax=payroll_data["tax_deductions"]["social_security_tax"],
            medicare_tax=payroll_data["tax_deductions"]["medicare_tax"],
            health_insurance=payroll_data["benefit_deductions"]["health_insurance"],
            dental_insurance=payroll_data["benefit_deductions"]["dental_insurance"],
            vision_insurance=payroll_data["benefit_deductions"]["vision_insurance"],
            retirement_401k=payroll_data["benefit_deductions"]["retirement_401k"],
            other_deductions=payroll_data["other_deductions"]["other_deductions"],
            total_deductions=payroll_data["total_deductions"],
            net_pay=payroll_data["net_pay"],
            calculated_at=payroll_data["calculated_at"],
            # Additional time entry fields
            time_entries_used=payroll_data.get("time_entries_used", False),
            time_entries_count=payroll_data.get("time_entries_count", 0),
            regular_hours=payroll_data.get("regular_hours", payroll_data["hours_worked"]),
            double_time_hours=payroll_data.get("double_time_hours", 0)
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error calculating payroll with time entries: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        ) 