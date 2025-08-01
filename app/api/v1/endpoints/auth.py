"""
Authentication API endpoints.

This module provides authentication endpoints including login, registration,
token refresh, and password management.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.user_service import UserService
from app.schemas.user import (
    UserCreate, UserLogin, UserResponse, UserUpdate,
    UserLoginResponse, TokenRefresh, PasswordChange, 
    PasswordReset, PasswordResetConfirm
)
from app.core.security import (
    create_access_token, create_refresh_token, verify_token,
    get_password_hash, verify_password
)
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()


def get_current_user(
    token: str = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user."""
    try:
        payload = verify_token(token.credentials)
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user_service = UserService(db)
        user = user_service.get_user_by_id(int(user_id))
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return user
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """Register a new user account."""
    try:
        user_service = UserService(db)
        
        # Check if user already exists
        if user_service.get_user_by_email(user_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        if user_service.get_user_by_username(user_data.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        
        # Create user
        user = user_service.create_user(user_data)
        return UserResponse(**user.__dict__)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error during registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/login", response_model=UserLoginResponse)
def login(
    login_data: UserLogin,
    db: Session = Depends(get_db)
):
    """Authenticate user and return tokens."""
    try:
        user_service = UserService(db)
        
        # Find user by username or email
        user = user_service.get_user_by_username(login_data.username)
        if not user:
            user = user_service.get_user_by_email(login_data.username)
        
        if not user or not verify_password(login_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )
        
        # Create tokens
        access_token = create_access_token(subject=user.id)
        refresh_token = create_refresh_token(subject=user.id)
        
        # Update last login
        user_service.update_last_login(user.id)
        
        return UserLoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=UserResponse(**user.__dict__)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/refresh", response_model=UserLoginResponse)
def refresh_token(
    refresh_data: TokenRefresh,
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token."""
    try:
        payload = verify_token(refresh_data.refresh_token)
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user_service = UserService(db)
        user = user_service.get_user_by_id(int(user_id))
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create new tokens
        access_token = create_access_token(subject=user.id)
        new_refresh_token = create_refresh_token(subject=user.id)
        
        return UserLoginResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            user=UserResponse(**user.__dict__)
        )
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return UserResponse(**current_user.__dict__)


@router.put("/me", response_model=UserResponse)
def update_me(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user information."""
    try:
        user_service = UserService(db)
        updated_user = user_service.update_user(current_user.id, user_update)
        return UserResponse(**updated_user.__dict__)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/change-password")
def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password."""
    try:
        # Verify current password
        if not verify_password(password_data.current_password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect current password"
            )
        
        # Update password
        user_service = UserService(db)
        new_password_hash = get_password_hash(password_data.new_password)
        user_service.update_password(current_user.id, new_password_hash)
        
        return {"message": "Password updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/forgot-password")
def forgot_password(
    reset_data: PasswordReset,
    db: Session = Depends(get_db)
):
    """Request password reset (placeholder implementation)."""
    # This is a placeholder - in production you would:
    # 1. Verify the email exists
    # 2. Generate a reset token
    # 3. Send reset email
    # 4. Store the token for verification
    
    return {"message": "If an account with that email exists, you will receive a password reset link"}


@router.post("/reset-password")
def reset_password(
    reset_data: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """Reset password using reset token (placeholder implementation)."""
    # This is a placeholder - in production you would:
    # 1. Verify the reset token
    # 2. Check token expiration
    # 3. Update the user's password
    # 4. Invalidate the reset token
    
    return {"message": "Password reset successfully"} 