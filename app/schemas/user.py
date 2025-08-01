"""
User schemas for API request/response validation.

This module defines Pydantic schemas for user-related operations
including authentication, user creation, and user information.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict

from app.models.enums import UserRole, UserStatus


class UserBase(BaseModel):
    """Base user schema with common fields."""
    
    email: EmailStr = Field(..., description="User's email address")
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    first_name: str = Field(..., min_length=1, max_length=50, description="First name")
    last_name: str = Field(..., min_length=1, max_length=50, description="Last name")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    role: UserRole = Field(UserRole.USER, description="User role")
    is_active: bool = Field(True, description="Whether user is active")


class UserCreate(UserBase):
    """Schema for creating a new user."""
    
    password: str = Field(..., min_length=8, description="User password")
    confirm_password: str = Field(..., min_length=8, description="Password confirmation")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "john.doe@example.com",
                "username": "johndoe",
                "first_name": "John",
                "last_name": "Doe",
                "phone": "+1-555-123-4567",
                "role": "user",
                "is_active": True,
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!"
            }
        }
    )


class UserUpdate(BaseModel):
    """Schema for updating user information."""
    
    email: Optional[EmailStr] = Field(None, description="User's email address")
    username: Optional[str] = Field(None, min_length=3, max_length=50, description="Username")
    first_name: Optional[str] = Field(None, min_length=1, max_length=50, description="First name")
    last_name: Optional[str] = Field(None, min_length=1, max_length=50, description="Last name")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    role: Optional[UserRole] = Field(None, description="User role")
    is_active: Optional[bool] = Field(None, description="Whether user is active")
    bio: Optional[str] = Field(None, max_length=1000, description="User bio")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "first_name": "John",
                "last_name": "Doe",
                "phone": "+1-555-123-4567",
                "bio": "HR Manager with 5+ years experience"
            }
        }
    )


class UserResponse(UserBase):
    """Schema for user response data."""
    
    id: int = Field(..., description="User ID")
    is_verified: bool = Field(..., description="Whether user is verified")
    is_superuser: bool = Field(..., description="Whether user is a superuser")
    status: UserStatus = Field(..., description="User status")
    created_at: datetime = Field(..., description="User creation timestamp")
    updated_at: datetime = Field(..., description="User last update timestamp")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    bio: Optional[str] = Field(None, description="User bio")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "email": "john.doe@example.com",
                "username": "johndoe",
                "first_name": "John",
                "last_name": "Doe",
                "phone": "+1-555-123-4567",
                "role": "user",
                "is_active": True,
                "is_verified": True,
                "is_superuser": False,
                "status": "active",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00",
                "last_login": "2024-01-01T12:00:00",
                "bio": "HR Manager with 5+ years experience"
            }
        }
    )


class UserLogin(BaseModel):
    """Schema for user login."""
    
    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="Password")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "username": "johndoe",
                "password": "SecurePass123!"
            }
        }
    )


class UserLoginResponse(BaseModel):
    """Schema for login response."""
    
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field("bearer", description="Token type")
    user: UserResponse = Field(..., description="User information")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                "token_type": "bearer",
                "user": {
                    "id": 1,
                    "email": "john.doe@example.com",
                    "username": "johndoe",
                    "first_name": "John",
                    "last_name": "Doe",
                    "role": "user",
                    "is_active": True
                }
            }
        }
    )


class TokenRefresh(BaseModel):
    """Schema for token refresh."""
    
    refresh_token: str = Field(..., description="Refresh token")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
            }
        }
    )


class PasswordChange(BaseModel):
    """Schema for password change."""
    
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")
    confirm_password: str = Field(..., min_length=8, description="Confirm new password")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "current_password": "OldPass123!",
                "new_password": "NewSecurePass123!",
                "confirm_password": "NewSecurePass123!"
            }
        }
    )


class PasswordReset(BaseModel):
    """Schema for password reset request."""
    
    email: EmailStr = Field(..., description="User's email address")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "john.doe@example.com"
            }
        }
    )


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation."""
    
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, description="New password")
    confirm_password: str = Field(..., min_length=8, description="Confirm new password")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "token": "abc123def456",
                "new_password": "NewSecurePass123!",
                "confirm_password": "NewSecurePass123!"
            }
        }
    )


class UserList(BaseModel):
    """Schema for paginated user list."""
    
    users: list[UserResponse] = Field(..., description="List of users")
    total: int = Field(..., description="Total number of users")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Number of users per page")
    pages: int = Field(..., description="Total number of pages")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "users": [
                    {
                        "id": 1,
                        "email": "john.doe@example.com",
                        "username": "johndoe",
                        "first_name": "John",
                        "last_name": "Doe",
                        "role": "user",
                        "is_active": True
                    }
                ],
                "total": 1,
                "page": 1,
                "per_page": 10,
                "pages": 1
            }
        }
    ) 