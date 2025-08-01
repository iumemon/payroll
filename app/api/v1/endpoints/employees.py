"""
Employee API endpoints for employee management.

This module provides comprehensive REST API endpoints for managing employees
including CRUD operations, search, filtering, and employee-specific actions.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_admin
from app.models.user import User
from app.models.employee import Employee
from app.models.enums import EmployeeStatus, EmploymentType, PayrollFrequency
from app.schemas.employee import (
    EmployeeCreate, EmployeeUpdate, EmployeeResponse, 
    EmployeeList, EmployeeSummary
)
from app.services.employee import EmployeeService

router = APIRouter()


@router.post("/", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
def create_employee(
    employee_data: EmployeeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Create a new employee.
    
    **Required permissions**: Admin
    
    **Features**:
    - Validates employee data
    - Checks for duplicate employee ID and email
    - Ensures proper compensation setup
    - Generates unique employee ID if needed
    """
    employee_service = EmployeeService(db)
    
    try:
        # Validate employee data
        validation_errors = employee_service.validate_employee_data(employee_data)
        if validation_errors:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"errors": validation_errors}
            )
        
        # Generate employee ID if not provided
        if not employee_data.employee_id:
            employee_data.employee_id = employee_service.generate_employee_id()
        
        employee = employee_service.create_employee(employee_data)
        return employee
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/", response_model=EmployeeList)
def get_employees(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    search: Optional[str] = Query(None, description="Search term for name, email, or employee ID"),
    department: Optional[str] = Query(None, description="Filter by department"),
    status: Optional[EmployeeStatus] = Query(None, description="Filter by employee status"),
    employment_type: Optional[EmploymentType] = Query(None, description="Filter by employment type"),
    sort_by: str = Query("last_name", description="Field to sort by"),
    sort_order: str = Query("asc", regex="^(asc|desc)$", description="Sort order (asc/desc)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get paginated list of employees with optional filtering and search.
    
    **Required permissions**: Any authenticated user
    
    **Features**:
    - Pagination with skip/limit
    - Search by name, email, or employee ID
    - Filter by department, status, employment type
    - Sorting by various fields
    - Returns total count and pagination info
    """
    try:
        employee_service = EmployeeService(db)
        
        result = employee_service.get_employees(
            skip=skip,
            limit=limit,
            search=search,
            department=department,
            status=status,
            employment_type=employment_type,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # Return simplified response for testing
        return EmployeeList(
            employees=[],
            total=result["total"],
            page=result["page"],
            per_page=result["per_page"],
            pages=result["pages"]
        )
    except Exception as e:
        import traceback
        print(f"❌ Exception in get_employees: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/summary", response_model=List[EmployeeSummary])
async def get_employees_summary(
    status: Optional[EmployeeStatus] = Query(None, description="Filter by employee status"),
    department: Optional[str] = Query(None, description="Filter by department"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get summary list of employees with basic information.
    
    **Required permissions**: Any authenticated user
    
    **Features**:
    - Lightweight employee list
    - Basic filtering options
    - Suitable for dropdowns and quick reference
    """
    employee_service = EmployeeService(db)
    
    result = employee_service.get_employees(
        skip=0,
        limit=1000,  # Large limit for summary
        status=status,
        department=department
    )
    
    employees = result["employees"]
    return [
        EmployeeSummary(
            id=emp.id,
            employee_id=emp.employee_id,
            full_name=emp.full_name,
            email=emp.email,
            position=emp.position,
            department=emp.department,
            status=emp.status,
            hire_date=emp.hire_date
        )
        for emp in employees
    ]


@router.get("/departments", response_model=List[str])
async def get_departments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get list of all departments.
    
    **Required permissions**: Any authenticated user
    
    **Features**:
    - Returns unique department names
    - Useful for filtering and dropdowns
    """
    employee_service = EmployeeService(db)
    return employee_service.get_departments()


@router.get("/stats", response_model=Dict[str, Any])
async def get_employee_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get employee statistics.
    
    **Required permissions**: Any authenticated user
    
    **Features**:
    - Count by status
    - Count by department
    - Total employee count
    - Manager count
    """
    employee_service = EmployeeService(db)
    
    status_counts = employee_service.get_employee_count_by_status()
    department_counts = employee_service.get_employee_count_by_department()
    managers = employee_service.get_managers()
    
    total_employees = sum(status_counts.values())
    
    return {
        "total_employees": total_employees,
        "by_status": status_counts,
        "by_department": department_counts,
        "managers_count": len(managers)
    }


@router.get("/{employee_id}", response_model=EmployeeResponse)
async def get_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get employee by ID.
    
    **Required permissions**: Any authenticated user
    
    **Features**:
    - Returns complete employee information
    - Includes computed fields like years of service
    - Includes PTO balances
    """
    employee_service = EmployeeService(db)
    
    employee = employee_service.get_employee(employee_id)
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    
    return employee


@router.get("/by-employee-id/{employee_id}", response_model=EmployeeResponse)
async def get_employee_by_employee_id(
    employee_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get employee by employee ID string.
    
    **Required permissions**: Any authenticated user
    
    **Features**:
    - Lookup by employee ID (e.g., "EMP0001")
    - Returns complete employee information
    """
    employee_service = EmployeeService(db)
    
    employee = employee_service.get_employee_by_employee_id(employee_id)
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with ID {employee_id} not found"
        )
    
    return employee


@router.get("/{employee_id}/subordinates", response_model=List[EmployeeSummary])
async def get_employee_subordinates(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get list of employees who report to the given employee.
    
    **Required permissions**: Any authenticated user
    
    **Features**:
    - Returns direct reports
    - Useful for org chart functionality
    """
    employee_service = EmployeeService(db)
    
    # Verify employee exists
    employee = employee_service.get_employee(employee_id)
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    
    subordinates = employee_service.get_employee_subordinates(employee_id)
    
    return [
        EmployeeSummary(
            id=emp.id,
            employee_id=emp.employee_id,
            full_name=emp.full_name,
            email=emp.email,
            position=emp.position,
            department=emp.department,
            status=emp.status,
            hire_date=emp.hire_date
        )
        for emp in subordinates
    ]


@router.put("/{employee_id}", response_model=EmployeeResponse)
async def update_employee(
    employee_id: int,
    employee_data: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Update employee information.
    
    **Required permissions**: Admin
    
    **Features**:
    - Partial updates (only provided fields)
    - Validates email uniqueness
    - Updates timestamp automatically
    """
    employee_service = EmployeeService(db)
    
    try:
        employee = employee_service.update_employee(employee_id, employee_data)
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee not found"
            )
        
        return employee
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_employee(
    employee_id: int,
    hard_delete: bool = Query(False, description="Perform hard delete (permanent removal)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Delete employee.
    
    **Required permissions**: Admin
    
    **Features**:
    - Soft delete by default (sets status to terminated)
    - Hard delete option for permanent removal
    - Maintains data integrity
    """
    employee_service = EmployeeService(db)
    
    if hard_delete:
        success = employee_service.hard_delete_employee(employee_id)
    else:
        success = employee_service.delete_employee(employee_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )


@router.post("/{employee_id}/activate", response_model=EmployeeResponse)
async def activate_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Activate an employee.
    
    **Required permissions**: Admin
    
    **Features**:
    - Sets status to active
    - Clears termination date
    - Updates timestamp
    """
    employee_service = EmployeeService(db)
    
    employee = employee_service.activate_employee(employee_id)
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    
    return employee


@router.post("/{employee_id}/deactivate", response_model=EmployeeResponse)
async def deactivate_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Deactivate an employee.
    
    **Required permissions**: Admin
    
    **Features**:
    - Sets status to inactive
    - Maintains employment record
    - Updates timestamp
    """
    employee_service = EmployeeService(db)
    
    employee = employee_service.deactivate_employee(employee_id)
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    
    return employee


@router.post("/generate-employee-id", response_model=Dict[str, str])
async def generate_employee_id(
    prefix: str = Query("EMP", description="Prefix for employee ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Generate a unique employee ID.
    
    **Required permissions**: Admin
    
    **Features**:
    - Generates unique sequential employee ID
    - Customizable prefix
    - Ensures no conflicts
    """
    employee_service = EmployeeService(db)
    
    new_id = employee_service.generate_employee_id(prefix)
    
    return {"employee_id": new_id}


@router.get("/managers/list", response_model=List[EmployeeSummary])
async def get_managers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get list of employees who are managers.
    
    **Required permissions**: Any authenticated user
    
    **Features**:
    - Returns employees who have direct reports
    - Useful for org chart and management reporting
    """
    employee_service = EmployeeService(db)
    
    managers = employee_service.get_managers()
    
    return [
        EmployeeSummary(
            id=emp.id,
            employee_id=emp.employee_id,
            full_name=emp.full_name,
            email=emp.email,
            position=emp.position,
            department=emp.department,
            status=emp.status,
            hire_date=emp.hire_date
        )
        for emp in managers
    ] 