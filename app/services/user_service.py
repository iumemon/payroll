"""
User service for business logic operations.

This module provides business logic for user management including
authentication, authorization, and user account operations.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.enums import UserRole, UserStatus
from app.schemas.user import UserCreate, UserUpdate, UserLogin
from app.core.security import (
    create_access_token, 
    create_refresh_token, 
    verify_password, 
    get_password_hash, 
    verify_token,
    validate_password_strength
)

logger = logging.getLogger(__name__)


class UserService:
    """Service class for user-related operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_user(self, user_data: UserCreate) -> User:
        """
        Create a new user account.
        
        Args:
            user_data: User creation data
            
        Returns:
            Created user object
            
        Raises:
            ValueError: If validation fails
            Exception: If database operation fails
        """
        try:
            # Validate password strength
            password_validation = validate_password_strength(user_data.password)
            if not password_validation["valid"]:
                raise ValueError(f"Password validation failed: {', '.join(password_validation['errors'])}")
            
            # Check if passwords match
            if user_data.password != user_data.confirm_password:
                raise ValueError("Passwords do not match")
            
            # Check if email already exists
            existing_user = self.get_user_by_email(user_data.email)
            if existing_user:
                raise ValueError("Email already registered")
            
            # Check if username already exists
            existing_username = self.get_user_by_username(user_data.username)
            if existing_username:
                raise ValueError("Username already taken")
            
            # Hash password
            hashed_password = get_password_hash(user_data.password)
            
            # Create user
            user = User(
                email=user_data.email,
                username=user_data.username,
                hashed_password=hashed_password,
                first_name=user_data.first_name,
                last_name=user_data.last_name,
                phone=user_data.phone,
                role=user_data.role,
                is_active=user_data.is_active,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            
            logger.info(f"User created successfully: {user.email}")
            return user
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating user: {e}")
            raise
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """
        Authenticate user with username/email and password.
        
        Args:
            username: Username or email
            password: Password
            
        Returns:
            User object if authentication successful, None otherwise
        """
        try:
            # Find user by username or email
            user = self.get_user_by_username(username)
            if not user:
                user = self.get_user_by_email(username)
            
            if not user:
                logger.warning(f"Authentication failed: User not found - {username}")
                return None
            
            # Check if user is active
            if not user.is_active:
                logger.warning(f"Authentication failed: User inactive - {username}")
                return None
            
            # Check if account is locked
            if user.is_locked:
                logger.warning(f"Authentication failed: Account locked - {username}")
                return None
            
            # Verify password
            if not verify_password(password, user.hashed_password):
                # Increment failed login attempts
                self._increment_failed_login_attempts(user)
                logger.warning(f"Authentication failed: Invalid password - {username}")
                return None
            
            # Reset failed login attempts and update last login
            self._reset_failed_login_attempts(user)
            self._update_last_login(user)
            
            logger.info(f"User authenticated successfully: {user.email}")
            return user
            
        except Exception as e:
            logger.error(f"Error authenticating user: {e}")
            return None
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        try:
            return self.db.query(User).filter(User.id == user_id).first()
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            return None
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        try:
            return self.db.query(User).filter(User.email == email).first()
        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            return None
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        try:
            return self.db.query(User).filter(User.username == username).first()
        except Exception as e:
            logger.error(f"Error getting user by username: {e}")
            return None
    
    def update_user(self, user_id: int, user_data: UserUpdate) -> Optional[User]:
        """Update user information."""
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return None
            
            # Update only provided fields
            update_data = user_data.model_dump(exclude_unset=True)
            
            # Check for email uniqueness if email is being updated
            if "email" in update_data and update_data["email"] != user.email:
                existing_user = self.get_user_by_email(update_data["email"])
                if existing_user:
                    raise ValueError("Email already registered")
            
            # Check for username uniqueness if username is being updated
            if "username" in update_data and update_data["username"] != user.username:
                existing_user = self.get_user_by_username(update_data["username"])
                if existing_user:
                    raise ValueError("Username already taken")
            
            # Update user attributes
            for field, value in update_data.items():
                setattr(user, field, value)
            
            user.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(user)
            
            logger.info(f"User updated successfully: {user.email}")
            return user
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating user: {e}")
            raise
    
    def delete_user(self, user_id: int) -> bool:
        """
        Delete a user account.
        
        Args:
            user_id: User ID to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return False
            
            self.db.delete(user)
            self.db.commit()
            
            logger.info(f"User deleted successfully: {user_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting user: {e}")
            return False
    
    def get_users(
        self, 
        skip: int = 0, 
        limit: int = 100,
        role: Optional[UserRole] = None,
        status: Optional[UserStatus] = None,
        search: Optional[str] = None
    ) -> List[User]:
        """
        Get list of users with optional filtering.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            role: Filter by user role
            status: Filter by user status
            search: Search term for name/email
            
        Returns:
            List of user objects
        """
        try:
            query = self.db.query(User)
            
            # Apply filters
            if role:
                query = query.filter(User.role == role)
            if status:
                query = query.filter(User.status == status)
            if search:
                search_filter = f"%{search}%"
                query = query.filter(
                    (User.first_name.ilike(search_filter)) |
                    (User.last_name.ilike(search_filter)) |
                    (User.email.ilike(search_filter)) |
                    (User.username.ilike(search_filter))
                )
            
            return query.offset(skip).limit(limit).all()
            
        except Exception as e:
            logger.error(f"Error getting users: {e}")
            return []
    
    def get_user_count(
        self,
        role: Optional[UserRole] = None,
        status: Optional[UserStatus] = None,
        search: Optional[str] = None
    ) -> int:
        """
        Get count of users with optional filtering.
        
        Args:
            role: Filter by user role
            status: Filter by user status
            search: Search term for name/email
            
        Returns:
            Number of users matching criteria
        """
        try:
            query = self.db.query(User)
            
            # Apply filters
            if role:
                query = query.filter(User.role == role)
            if status:
                query = query.filter(User.status == status)
            if search:
                search_filter = f"%{search}%"
                query = query.filter(
                    (User.first_name.ilike(search_filter)) |
                    (User.last_name.ilike(search_filter)) |
                    (User.email.ilike(search_filter)) |
                    (User.username.ilike(search_filter))
                )
            
            return query.count()
            
        except Exception as e:
            logger.error(f"Error getting user count: {e}")
            return 0
    
    def change_password(self, user_id: int, current_password: str, new_password: str) -> bool:
        """
        Change user password.
        
        Args:
            user_id: User ID
            current_password: Current password
            new_password: New password
            
        Returns:
            True if password changed successfully, False otherwise
        """
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return False
            
            # Verify current password
            if not verify_password(current_password, user.hashed_password):
                return False
            
            # Validate new password strength
            password_validation = validate_password_strength(new_password)
            if not password_validation["valid"]:
                raise ValueError(f"Password validation failed: {', '.join(password_validation['errors'])}")
            
            # Hash new password
            user.hashed_password = get_password_hash(new_password)
            user.updated_at = datetime.utcnow()
            
            self.db.commit()
            logger.info(f"Password changed successfully for user: {user.email}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error changing password: {e}")
            return False
    
    def update_password(self, user_id: int, new_password_hash: str) -> bool:
        """
        Update user password hash directly.
        
        Args:
            user_id: User ID
            new_password_hash: New password hash
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return False
            
            user.hashed_password = new_password_hash
            user.updated_at = datetime.utcnow()
            
            self.db.commit()
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating password: {e}")
            return False
    
    def update_last_login(self, user_id: int) -> bool:
        """
        Update user's last login timestamp.
        
        Args:
            user_id: User ID
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return False
            
            user.last_login = datetime.utcnow()
            user.updated_at = datetime.utcnow()
            
            self.db.commit()
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating last login: {e}")
            return False
    
    def _increment_failed_login_attempts(self, user: User) -> None:
        """Increment failed login attempts for a user."""
        try:
            user.failed_login_attempts += 1
            user.updated_at = datetime.utcnow()
            
            # Lock account if too many failed attempts
            if user.failed_login_attempts >= 5:
                user.locked_until = datetime.utcnow() + timedelta(minutes=30)
                logger.warning(f"Account locked due to failed login attempts: {user.email}")
            
            self.db.commit()
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error incrementing failed login attempts: {e}")
    
    def _reset_failed_login_attempts(self, user: User) -> None:
        """Reset failed login attempts for a user."""
        try:
            user.failed_login_attempts = 0
            user.locked_until = None
            user.updated_at = datetime.utcnow()
            
            self.db.commit()
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error resetting failed login attempts: {e}")
    
    def _update_last_login(self, user: User) -> None:
        """Update last login timestamp for a user."""
        try:
            user.last_login = datetime.utcnow()
            user.updated_at = datetime.utcnow()
            
            self.db.commit()
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating last login: {e}")
    
    def create_tokens(self, user: User) -> Dict[str, str]:
        """
        Create access and refresh tokens for a user.
        
        Args:
            user: User object
            
        Returns:
            Dictionary containing tokens
        """
        access_token = create_access_token(subject=user.id)
        refresh_token = create_refresh_token(subject=user.id)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    
    def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, str]]:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            Dictionary containing new tokens or None if invalid
        """
        try:
            payload = verify_token(refresh_token)
            user_id = payload.get("sub")
            
            if user_id is None:
                return None
            
            user = self.get_user_by_id(int(user_id))
            if not user or not user.is_active:
                return None
            
            return self.create_tokens(user)
            
        except Exception as e:
            logger.error(f"Error refreshing access token: {e}")
            return None 