"""
User model for authentication and authorization.

This module defines the User model which handles user accounts,
authentication, and role-based access control.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, Enum, Integer, String, Text, Index
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.enums import UserRole, UserStatus


class User(Base):
    """User model for authentication and authorization."""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    # Personal Information
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    phone = Column(String(20), nullable=True)
    
    # Account Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_superuser = Column(Boolean, default=False)
    role = Column(Enum(UserRole), default=UserRole.USER)
    status = Column(Enum(UserStatus), default=UserStatus.ACTIVE)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # Security
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    password_reset_token = Column(String(255), nullable=True)
    password_reset_expires = Column(DateTime, nullable=True)
    
    # Profile
    profile_picture = Column(String(255), nullable=True)
    bio = Column(Text, nullable=True)
    
    # Relationships
    employee = relationship("Employee", back_populates="user", uselist=False)
    # audit_logs = relationship("AuditLog", back_populates="user")
    
    # Performance indexes
    __table_args__ = (
        Index('idx_user_role', 'role'),
        Index('idx_user_status', 'status'),
        Index('idx_user_is_active', 'is_active'),
        Index('idx_user_is_verified', 'is_verified'),
        Index('idx_user_is_superuser', 'is_superuser'),
        Index('idx_user_created_at', 'created_at'),
        Index('idx_user_updated_at', 'updated_at'),
        Index('idx_user_last_login', 'last_login'),
        Index('idx_user_failed_attempts', 'failed_login_attempts'),
        Index('idx_user_locked_until', 'locked_until'),
        Index('idx_user_name_search', 'first_name', 'last_name'),
        # Composite indexes for common filter combinations
        Index('idx_user_role_status', 'role', 'status'),
        Index('idx_user_active_role', 'is_active', 'role'),
        Index('idx_user_status_active', 'status', 'is_active'),
        Index('idx_user_role_verified', 'role', 'is_verified'),
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"
    
    @property
    def full_name(self) -> str:
        """Get the user's full name."""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def is_admin(self) -> bool:
        """Check if user is an admin."""
        return self.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]
    
    @property
    def is_hr(self) -> bool:
        """Check if user is HR personnel."""
        return self.role in [UserRole.HR, UserRole.ADMIN, UserRole.SUPER_ADMIN]
    
    @property
    def is_manager(self) -> bool:
        """Check if user is a manager."""
        return self.role in [UserRole.MANAGER, UserRole.HR, UserRole.ADMIN, UserRole.SUPER_ADMIN]
    
    @property
    def is_locked(self) -> bool:
        """Check if user account is locked."""
        if self.locked_until is None:
            return False
        return datetime.utcnow() < self.locked_until
    
    def can_access_employee_data(self, employee_id: int) -> bool:
        """Check if user can access specific employee data."""
        if self.is_admin or self.is_hr:
            return True
        # Users can access their own employee data
        # This would need to be implemented with proper employee relationship
        return False
    
    def can_modify_payroll(self) -> bool:
        """Check if user can modify payroll data."""
        return self.role in [UserRole.PAYROLL_ADMIN, UserRole.ADMIN, UserRole.SUPER_ADMIN]
    
    def can_view_reports(self) -> bool:
        """Check if user can view reports."""
        return self.role in [UserRole.MANAGER, UserRole.HR, UserRole.PAYROLL_ADMIN, UserRole.ADMIN, UserRole.SUPER_ADMIN] 