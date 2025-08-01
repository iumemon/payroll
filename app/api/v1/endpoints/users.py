"""
User management API endpoints.

This module provides endpoints for user management including creating,
reading, updating, and deleting user accounts.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.user_service import UserService
from app.schemas.user import (
    UserCreate, UserUpdate, UserResponse, UserList
)
from app.models.user import User
from app.core.security import get_current_user, require_admin

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=UserList)
def get_users(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    search: Optional[str] = Query(None, description="Search users by name, email, or username"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get list of users with pagination and filtering."""
    try:
        user_service = UserService(db)
        
        # Only admins can see all users
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        
        users = user_service.get_users(skip=skip, limit=limit, search=search)
        total = user_service.count_users(search=search)
        
        pages = (total + limit - 1) // limit
        
        return UserList(
            users=[UserResponse(**user.__dict__) for user in users],
            total=total,
            page=(skip // limit) + 1,
            per_page=limit,
            pages=pages
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new user account."""
    try:
        # Only admins can create users
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        
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
        
        user = user_service.create_user(user_data)
        return UserResponse(**user.__dict__)
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user by ID."""
    try:
        user_service = UserService(db)
        
        # Users can only see their own profile, admins can see all
        if current_user.role != "admin" and current_user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        
        user = user_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return UserResponse(**user.__dict__)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user information."""
    try:
        user_service = UserService(db)
        
        # Users can only update their own profile, admins can update all
        if current_user.role != "admin" and current_user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        
        user = user_service.update_user(user_id, user_data)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return UserResponse(**user.__dict__)
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete user account."""
    try:
        # Only admins can delete users
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        
        # Users cannot delete themselves
        if current_user.id == user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own account"
            )
        
        user_service = UserService(db)
        success = user_service.delete_user(user_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return {"message": "User deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.put("/{user_id}/activate", response_model=UserResponse)
def activate_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Activate user account."""
    try:
        # Only admins can activate users
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        
        user_service = UserService(db)
        user = user_service.activate_user(user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return UserResponse(**user.__dict__)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error activating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.put("/{user_id}/deactivate", response_model=UserResponse)
def deactivate_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deactivate user account."""
    try:
        # Only admins can deactivate users
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        
        # Admins cannot deactivate themselves
        if current_user.id == user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate your own account"
            )
        
        user_service = UserService(db)
        user = user_service.deactivate_user(user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return UserResponse(**user.__dict__)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/search/", response_model=List[UserResponse])
def search_users(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of users to return"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Search users by name, email, or username."""
    try:
        # Only admins can search users
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        
        user_service = UserService(db)
        users = user_service.search_users(query=q, limit=limit)
        
        return [UserResponse(**user.__dict__) for user in users]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        ) 