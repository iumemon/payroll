"""
Security utilities for the Payroll Management System.

This module provides authentication, authorization, and security
utilities including JWT token management and password hashing.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from jose import jwt
from passlib.context import CryptContext
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db

settings = get_settings()

# Configure logging
logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Token constants
ALGORITHM = settings.ALGORITHM
SECRET_KEY = settings.SECRET_KEY
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS


def create_access_token(
    subject: Union[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        subject: The subject (usually user ID or username)
        expires_delta: Optional custom expiration time
        
    Returns:
        str: Encoded JWT token
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(subject: Union[str, Any]) -> str:
    """
    Create a JWT refresh token.
    
    Args:
        subject: The subject (usually user ID or username)
        
    Returns:
        str: Encoded JWT refresh token
    """
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
    """
    Verify and decode a JWT token.
    
    Args:
        token: The JWT token to verify
        token_type: Expected token type ('access' or 'refresh')
        
    Returns:
        Dict containing token payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        token_data = payload.get("sub")
        token_exp = payload.get("exp")
        payload_type = payload.get("type")
        
        if token_data is None:
            logger.warning("Token missing subject")
            return None
            
        if token_exp is None:
            logger.warning("Token missing expiration")
            return None
            
        if payload_type != token_type:
            logger.warning(f"Token type mismatch: expected {token_type}, got {payload_type}")
            return None
            
        # Check if token is expired
        if datetime.utcnow() > datetime.fromtimestamp(token_exp):
            logger.warning("Token has expired")
            return None
            
        return payload
        
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return None
    except jwt.JWTError as e:
        logger.warning(f"Token validation error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error verifying token: {e}")
        return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        plain_password: The plain text password
        hashed_password: The hashed password
        
    Returns:
        bool: True if password matches, False otherwise
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Error verifying password: {e}")
        return False


def get_password_hash(password: str) -> str:
    """
    Hash a password.
    
    Args:
        password: The plain text password
        
    Returns:
        str: Hashed password
    """
    try:
        return pwd_context.hash(password)
    except Exception as e:
        logger.error(f"Error hashing password: {e}")
        raise


def validate_password_strength(password: str) -> Dict[str, Any]:
    """
    Validate password strength according to security requirements.
    
    Args:
        password: The password to validate
        
    Returns:
        Dict containing validation results
    """
    errors = []
    
    if len(password) < settings.PASSWORD_MIN_LENGTH:
        errors.append(f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters long")
    
    if settings.PASSWORD_REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter")
    
    if settings.PASSWORD_REQUIRE_LOWERCASE and not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter")
    
    if settings.PASSWORD_REQUIRE_NUMBERS and not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one number")
    
    if settings.PASSWORD_REQUIRE_SYMBOLS and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        errors.append("Password must contain at least one special character")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors
    }


def generate_password_reset_token(email: str) -> str:
    """
    Generate a password reset token.
    
    Args:
        email: User's email address
        
    Returns:
        str: Password reset token
    """
    delta = timedelta(hours=1)  # Reset token expires in 1 hour
    now = datetime.utcnow()
    expires = now + delta
    exp = expires.timestamp()
    encoded_jwt = jwt.encode(
        {"exp": exp, "nbf": now, "sub": email, "type": "password_reset"},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    return encoded_jwt


def verify_password_reset_token(token: str) -> Optional[str]:
    """
    Verify a password reset token.
    
    Args:
        token: The password reset token
        
    Returns:
        str: Email if token is valid, None otherwise
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        token_type = payload.get("type")
        if token_type != "password_reset":
            return None
        email = payload.get("sub")
        return email
    except jwt.ExpiredSignatureError:
        logger.warning("Password reset token has expired")
        return None
    except jwt.JWTError as e:
        logger.warning(f"Password reset token validation error: {e}")
        return None


# Authentication dependencies
security = HTTPBearer()


def get_current_user(
    token: str = Depends(security),
    db: Session = Depends(get_db)
) -> "User":
    """Get current authenticated user."""
    from app.models.user import User
    
    payload = verify_token(token.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    # Use sync database query instead of async UserService
    try:
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive"
            )
        
        return user
    except Exception as e:
        logger.error(f"Error getting current user: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )


def require_admin(current_user: "User" = Depends(get_current_user)) -> "User":
    """Require admin privileges."""
    from app.models.enums import UserRole
    
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.PAYROLL_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    return current_user


def require_super_admin(current_user: "User" = Depends(get_current_user)) -> "User":
    """Require super admin privileges."""
    from app.models.enums import UserRole
    
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin privileges required"
        )
    
    return current_user 