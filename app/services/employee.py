"""
Employee service for business logic operations.

This module provides business logic for employee management including
CRUD operations, search functionality, and data processing.
"""

import logging
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, date
from decimal import Decimal

from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import and_, or_, desc, asc, func
from sqlalchemy.exc import IntegrityError

from app.models.employee import Employee
from app.models.enums import EmployeeStatus, EmploymentType, PayrollFrequency
from app.schemas.employee import EmployeeCreate, EmployeeUpdate, EmployeeResponse
from app.core.cache import CacheManager, cached

logger = logging.getLogger(__name__)


class EmployeeService:
    """Service class for employee-related operations."""
    
    def __init__(self, db: Session):
        self.db = db
        self.cache = CacheManager()
    
    def create_employee(self, employee_data: EmployeeCreate, current_user_id: int) -> Employee:
        """
        Create a new employee.
        
        Args:
            employee_data: Employee creation data
            current_user_id: ID of the user creating the employee
            
        Returns:
            Created employee object
            
        Raises:
            ValueError: If validation fails
            IntegrityError: If database constraints are violated
        """
        try:
            # Validate employee data
            if not employee_data.first_name or not employee_data.last_name:
                raise ValueError("First name and last name are required")
            
            if not employee_data.email:
                raise ValueError("Email is required")
            
            if not employee_data.employee_id:
                raise ValueError("Employee ID is required")
            
            # Check if employee ID already exists
            existing_employee = self.db.query(Employee).filter(
                Employee.employee_id == employee_data.employee_id
            ).first()
            
            if existing_employee:
                raise ValueError(f"Employee ID {employee_data.employee_id} already exists")
            
            # Check if email already exists
            existing_email = self.db.query(Employee).filter(
                Employee.email == employee_data.email
            ).first()
            
            if existing_email:
                raise ValueError(f"Email {employee_data.email} already exists")
            
            # Create employee
            employee = Employee(
                **employee_data.model_dump(),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            self.db.add(employee)
            self.db.commit()
            self.db.refresh(employee)
            
            # Invalidate related caches
            self.cache.invalidate_pattern("employees_list*")
            
            logger.info(f"Employee created successfully: {employee.employee_id}")
            return employee
            
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Database integrity error creating employee: {e}")
            raise ValueError("Employee with this ID or email already exists")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating employee: {e}")
            raise
    
    def get_employee_by_id(self, employee_id: int) -> Optional[Employee]:
        """
        Get employee by ID with caching.
        
        Args:
            employee_id: Employee ID
            
        Returns:
            Employee object or None if not found
        """
        try:
            # Try cache first
            cached_employee = self.cache.get_user_by_id(employee_id)  # Reuse user cache pattern
            if cached_employee:
                return cached_employee
            
            # Query database with optimized loading
            employee = self.db.query(Employee).options(
                joinedload(Employee.user),
                joinedload(Employee.manager),
                selectinload(Employee.payroll_records)
            ).filter(Employee.id == employee_id).first()
            
            # Cache the result
            if employee:
                self.cache.set_user_by_id(employee_id, employee)
            
            return employee
            
        except Exception as e:
            logger.error(f"Error getting employee by ID: {e}")
            return None
    
    def get_employee_by_employee_id(self, employee_id: str) -> Optional[Employee]:
        """
        Get employee by employee ID string.
        
        Args:
            employee_id: Employee ID string
            
        Returns:
            Employee object or None if not found
        """
        try:
            return self.db.query(Employee).filter(
                Employee.employee_id == employee_id
            ).first()
        except Exception as e:
            logger.error(f"Error getting employee by employee ID: {e}")
            return None
    
    def get_employees(
        self, 
        skip: int = 0, 
        limit: int = 100,
        status: Optional[EmployeeStatus] = None,
        department: Optional[str] = None,
        employment_type: Optional[EmploymentType] = None,
        search: Optional[str] = None,
        sort_by: str = "last_name",
        sort_order: str = "asc"
    ) -> List[Employee]:
        """
        Get list of employees with filtering, sorting, and caching.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            status: Filter by employee status
            department: Filter by department
            employment_type: Filter by employment type
            search: Search term for name/email
            sort_by: Field to sort by
            sort_order: Sort order (asc/desc)
            
        Returns:
            List of employee objects
        """
        try:
            # Create cache key from parameters
            cache_filters = {
                'status': status.value if status else None,
                'department': department,
                'employment_type': employment_type.value if employment_type else None,
                'search': search,
                'sort_by': sort_by,
                'sort_order': sort_order
            }
            
            # Try cache first
            cached_employees = self.cache.get_employees_list(skip, limit, **cache_filters)
            if cached_employees:
                logger.debug(f"Cache hit for employees list: skip={skip}, limit={limit}")
                return cached_employees
            
            # Build query with optimized loading
            query = self.db.query(Employee).options(
                joinedload(Employee.user),
                joinedload(Employee.manager)
            )
            
            # Apply filters
            if status:
                query = query.filter(Employee.status == status)
            
            if department:
                query = query.filter(Employee.department == department)
            
            if employment_type:
                query = query.filter(Employee.employment_type == employment_type)
            
            if search:
                search_filter = f"%{search}%"
                query = query.filter(
                    or_(
                        Employee.first_name.ilike(search_filter),
                        Employee.last_name.ilike(search_filter),
                        Employee.email.ilike(search_filter),
                        Employee.employee_id.ilike(search_filter)
                    )
                )
            
            # Apply sorting
            if sort_order.lower() == "desc":
                query = query.order_by(desc(getattr(Employee, sort_by)))
            else:
                query = query.order_by(asc(getattr(Employee, sort_by)))
            
            # Apply pagination
            employees = query.offset(skip).limit(limit).all()
            
            # Cache the results
            self.cache.set_employees_list(employees, skip, limit, **cache_filters)
            logger.debug(f"Cached employees list: skip={skip}, limit={limit}")
            
            return employees
            
        except Exception as e:
            logger.error(f"Error getting employees: {e}")
            return []
    
    def get_employee_count(
        self,
        status: Optional[EmployeeStatus] = None,
        department: Optional[str] = None,
        employment_type: Optional[EmploymentType] = None,
        search: Optional[str] = None
    ) -> int:
        """
        Get count of employees with filtering.
        
        Args:
            status: Filter by employee status
            department: Filter by department
            employment_type: Filter by employment type
            search: Search term for name/email
            
        Returns:
            Number of employees matching criteria
        """
        try:
            query = self.db.query(Employee)
            
            # Apply same filters as get_employees
            if status:
                query = query.filter(Employee.status == status)
            
            if department:
                query = query.filter(Employee.department == department)
            
            if employment_type:
                query = query.filter(Employee.employment_type == employment_type)
            
            if search:
                search_filter = f"%{search}%"
                query = query.filter(
                    or_(
                        Employee.first_name.ilike(search_filter),
                        Employee.last_name.ilike(search_filter),
                        Employee.email.ilike(search_filter),
                        Employee.employee_id.ilike(search_filter)
                    )
                )
            
            return query.count()
            
        except Exception as e:
            logger.error(f"Error getting employee count: {e}")
            return 0
    
    def update_employee(self, employee_id: int, employee_data: EmployeeUpdate) -> Optional[Employee]:
        """
        Update employee information.
        
        Args:
            employee_id: Employee ID
            employee_data: Update data
            
        Returns:
            Updated employee object or None if not found
        """
        try:
            employee = self.get_employee_by_id(employee_id)
            if not employee:
                return None
            
            # Update only provided fields
            update_data = employee_data.model_dump(exclude_unset=True)
            
            # Check for unique constraints if being updated
            if "employee_id" in update_data and update_data["employee_id"] != employee.employee_id:
                existing = self.db.query(Employee).filter(
                    Employee.employee_id == update_data["employee_id"]
                ).first()
                if existing:
                    raise ValueError(f"Employee ID {update_data['employee_id']} already exists")
            
            if "email" in update_data and update_data["email"] != employee.email:
                existing = self.db.query(Employee).filter(
                    Employee.email == update_data["email"]
                ).first()
                if existing:
                    raise ValueError(f"Email {update_data['email']} already exists")
            
            # Update employee attributes
            for field, value in update_data.items():
                setattr(employee, field, value)
            
            employee.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(employee)
            
            # Invalidate related caches
            self.cache.invalidate_user(employee_id)
            self.cache.invalidate_pattern("employees_list*")
            
            logger.info(f"Employee updated successfully: {employee.employee_id}")
            return employee
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating employee: {e}")
            raise
    
    def delete_employee(self, employee_id: int) -> bool:
        """
        Delete an employee (soft delete by setting status to TERMINATED).
        
        Args:
            employee_id: Employee ID
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            employee = self.get_employee_by_id(employee_id)
            if not employee:
                return False
            
            # Soft delete by setting status to TERMINATED
            employee.status = EmployeeStatus.TERMINATED
            employee.termination_date = date.today()
            employee.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            # Invalidate related caches
            self.cache.invalidate_user(employee_id)
            self.cache.invalidate_pattern("employees_list*")
            
            logger.info(f"Employee terminated successfully: {employee.employee_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting employee: {e}")
            return False
    
    @cached(ttl=600, key_prefix="employee_stats:")
    def get_employee_statistics(self) -> Dict[str, Any]:
        """
        Get employee statistics with caching.
        
        Returns:
            Dictionary with employee statistics
        """
        try:
            stats = {}
            
            # Total employees
            stats['total_employees'] = self.db.query(Employee).count()
            
            # Active employees
            stats['active_employees'] = self.db.query(Employee).filter(
                Employee.status == EmployeeStatus.ACTIVE
            ).count()
            
            # Employees by status
            status_counts = self.db.query(
                Employee.status, func.count(Employee.id)
            ).group_by(Employee.status).all()
            
            stats['by_status'] = {
                status.value: count for status, count in status_counts
            }
            
            # Employees by department
            dept_counts = self.db.query(
                Employee.department, func.count(Employee.id)
            ).filter(Employee.department.isnot(None)).group_by(Employee.department).all()
            
            stats['by_department'] = {
                dept: count for dept, count in dept_counts
            }
            
            # Employees by employment type
            emp_type_counts = self.db.query(
                Employee.employment_type, func.count(Employee.id)
            ).group_by(Employee.employment_type).all()
            
            stats['by_employment_type'] = {
                emp_type.value: count for emp_type, count in emp_type_counts
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting employee statistics: {e}")
            return {}
    
    def get_departments(self) -> List[str]:
        """
        Get list of all departments.
        
        Returns:
            List of department names
        """
        try:
            departments = self.db.query(Employee.department).filter(
                Employee.department.isnot(None)
            ).distinct().all()
            
            return [dept[0] for dept in departments if dept[0]]
            
        except Exception as e:
            logger.error(f"Error getting departments: {e}")
            return []
    
    def get_managers(self) -> List[Employee]:
        """
        Get list of employees who are managers.
        
        Returns:
            List of manager employees
        """
        try:
            managers = self.db.query(Employee).filter(
                Employee.id.in_(
                    self.db.query(Employee.manager_id).filter(
                        Employee.manager_id.isnot(None)
                    ).distinct()
                )
            ).all()
            
            return managers
            
        except Exception as e:
            logger.error(f"Error getting managers: {e}")
            return []
    
    def get_employee_subordinates(self, employee_id: int) -> List[Employee]:
        """
        Get list of employees who report to the given employee.
        
        Args:
            employee_id: Manager's employee ID
            
        Returns:
            List of subordinate employees
        """
        try:
            subordinates = self.db.query(Employee).filter(
                Employee.manager_id == employee_id
            ).all()
            
            return subordinates
            
        except Exception as e:
            logger.error(f"Error getting subordinates: {e}")
            return [] 