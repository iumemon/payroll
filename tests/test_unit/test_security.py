"""
Unit tests for the security module.

Tests JWT token creation/verification, password hashing, and security utilities.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_token,
    verify_password,
    get_password_hash,
    validate_password_strength,
    generate_password_reset_token,
    verify_password_reset_token
)
from app.core.config import get_settings

settings = get_settings()


@pytest.mark.unit
class TestJWTTokens:
    """Test JWT token creation and verification."""
    
    def test_create_access_token(self):
        """Test access token creation."""
        subject = "test_user_123"
        token = create_access_token(subject=subject)
        
        assert isinstance(token, str)
        assert len(token) > 0
        assert "." in token  # JWT format check
    
    def test_create_access_token_with_custom_expiry(self):
        """Test access token with custom expiration."""
        subject = "test_user_123"
        custom_expiry = timedelta(minutes=60)
        token = create_access_token(subject=subject, expires_delta=custom_expiry)
        
        payload = verify_token(token)
        assert payload is not None
        assert payload["sub"] == subject
        assert payload["type"] == "access"
    
    def test_create_refresh_token(self):
        """Test refresh token creation."""
        subject = "test_user_123"
        token = create_refresh_token(subject=subject)
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        payload = verify_token(token, token_type="refresh")
        assert payload is not None
        assert payload["sub"] == subject
        assert payload["type"] == "refresh"
    
    def test_verify_valid_access_token(self):
        """Test verification of valid access token."""
        subject = "test_user_123"
        token = create_access_token(subject=subject)
        
        payload = verify_token(token)
        assert payload is not None
        assert payload["sub"] == subject
        assert payload["type"] == "access"
        assert "exp" in payload
    
    def test_verify_valid_refresh_token(self):
        """Test verification of valid refresh token."""
        subject = "test_user_123"
        token = create_refresh_token(subject=subject)
        
        payload = verify_token(token, token_type="refresh")
        assert payload is not None
        assert payload["sub"] == subject
        assert payload["type"] == "refresh"
    
    def test_verify_invalid_token(self):
        """Test verification of invalid token."""
        invalid_token = "invalid.token.here"
        payload = verify_token(invalid_token)
        assert payload is None
    
    def test_verify_token_type_mismatch(self):
        """Test token type mismatch."""
        subject = "test_user_123"
        access_token = create_access_token(subject=subject)
        
        # Try to verify access token as refresh token
        payload = verify_token(access_token, token_type="refresh")
        assert payload is None
    
    def test_verify_expired_token(self):
        """Test verification of expired token."""
        subject = "test_user_123"
        # Create token that expires immediately
        expired_token = create_access_token(
            subject=subject, 
            expires_delta=timedelta(seconds=-1)
        )
        
        payload = verify_token(expired_token)
        assert payload is None
    
    def test_token_without_subject(self):
        """Test token creation and verification edge cases."""
        # This tests the internal validation - normally create_access_token
        # always includes a subject, but we test the verify function's validation
        with patch('app.core.security.jwt.decode') as mock_decode:
            mock_decode.return_value = {"exp": datetime.utcnow().timestamp() + 3600, "type": "access"}
            payload = verify_token("dummy_token")
            assert payload is None


@pytest.mark.unit
class TestPasswordSecurity:
    """Test password hashing and verification."""
    
    def test_password_hashing(self):
        """Test password hashing."""
        password = "test_password_123"
        hashed = get_password_hash(password)
        
        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed != password  # Should be hashed, not plain text
        assert hashed.startswith("$2b$")  # bcrypt format
    
    def test_password_verification_success(self):
        """Test successful password verification."""
        password = "test_password_123"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True
    
    def test_password_verification_failure(self):
        """Test failed password verification."""
        password = "test_password_123"
        wrong_password = "wrong_password"
        hashed = get_password_hash(password)
        
        assert verify_password(wrong_password, hashed) is False
    
    def test_password_verification_with_invalid_hash(self):
        """Test password verification with invalid hash."""
        password = "test_password_123"
        invalid_hash = "invalid_hash"
        
        assert verify_password(password, invalid_hash) is False
    
    def test_same_password_different_hashes(self):
        """Test that same password generates different hashes (salt)."""
        password = "test_password_123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        assert hash1 != hash2  # Different due to salt
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


@pytest.mark.unit
class TestPasswordValidation:
    """Test password strength validation."""
    
    def test_valid_strong_password(self):
        """Test validation of strong password."""
        strong_password = "StrongPass123!"
        result = validate_password_strength(strong_password)
        
        assert result["valid"] is True
        assert result["errors"] == []
    
    def test_password_too_short(self):
        """Test password too short validation."""
        short_password = "Short1!"
        result = validate_password_strength(short_password)
        
        assert result["valid"] is False
        assert any("at least" in error for error in result["errors"])
    
    def test_password_missing_uppercase(self):
        """Test password missing uppercase validation."""
        password = "lowercase123!"
        result = validate_password_strength(password)
        
        assert result["valid"] is False
        assert any("uppercase" in error for error in result["errors"])
    
    def test_password_missing_lowercase(self):
        """Test password missing lowercase validation."""
        password = "UPPERCASE123!"
        result = validate_password_strength(password)
        
        assert result["valid"] is False
        assert any("lowercase" in error for error in result["errors"])
    
    def test_password_missing_numbers(self):
        """Test password missing numbers validation."""
        password = "NoNumbers!"
        result = validate_password_strength(password)
        
        assert result["valid"] is False
        assert any("number" in error for error in result["errors"])
    
    def test_password_missing_symbols(self):
        """Test password missing symbols validation."""
        password = "NoSymbols123"
        result = validate_password_strength(password)
        
        assert result["valid"] is False
        assert any("special character" in error for error in result["errors"])
    
    def test_password_multiple_violations(self):
        """Test password with multiple validation failures."""
        weak_password = "weak"
        result = validate_password_strength(weak_password)
        
        assert result["valid"] is False
        assert len(result["errors"]) > 1  # Multiple errors


@pytest.mark.unit
class TestPasswordReset:
    """Test password reset token functionality."""
    
    def test_generate_password_reset_token(self):
        """Test password reset token generation."""
        email = "test@example.com"
        token = generate_password_reset_token(email)
        
        assert isinstance(token, str)
        assert len(token) > 0
        assert "." in token  # JWT format
    
    def test_verify_valid_password_reset_token(self):
        """Test verification of valid password reset token."""
        email = "test@example.com"
        token = generate_password_reset_token(email)
        
        verified_email = verify_password_reset_token(token)
        assert verified_email == email
    
    def test_verify_invalid_password_reset_token(self):
        """Test verification of invalid password reset token."""
        invalid_token = "invalid.token.here"
        result = verify_password_reset_token(invalid_token)
        assert result is None
    
    def test_verify_expired_password_reset_token(self):
        """Test verification of expired password reset token."""
        email = "test@example.com"
        
        # Mock expired token
        with patch('app.core.security.jwt.decode') as mock_decode:
            from jose import jwt
            mock_decode.side_effect = jwt.ExpiredSignatureError()
            
            result = verify_password_reset_token("expired_token")
            assert result is None
    
    def test_verify_wrong_type_password_reset_token(self):
        """Test verification of wrong token type."""
        # Create an access token instead of password reset token
        access_token = create_access_token(subject="test@example.com")
        result = verify_password_reset_token(access_token)
        assert result is None


@pytest.mark.unit
class TestSecurityEdgeCases:
    """Test edge cases and error handling in security functions."""
    
    def test_empty_password_hash(self):
        """Test hashing empty password."""
        # Empty password should be hashed normally, not raise an error
        hashed = get_password_hash("")
        assert isinstance(hashed, str)
        assert len(hashed) > 0
    
    def test_none_password_hash(self):
        """Test hashing None password."""
        with pytest.raises((TypeError, AttributeError)):
            get_password_hash(None)
    
    def test_verify_password_with_none_values(self):
        """Test password verification with None values."""
        assert verify_password(None, "hash") is False
        assert verify_password("password", None) is False
        assert verify_password(None, None) is False
    
    def test_verify_empty_token(self):
        """Test token verification with empty token."""
        assert verify_token("") is None
        assert verify_token(None) is None
    
    def test_password_strength_empty_password(self):
        """Test password strength validation with empty password."""
        result = validate_password_strength("")
        assert result["valid"] is False
        assert len(result["errors"]) > 0
    
    def test_password_strength_none_password(self):
        """Test password strength validation with None password."""
        with pytest.raises((TypeError, AttributeError)):
            validate_password_strength(None)


@pytest.mark.unit
class TestSecurityConfiguration:
    """Test security configuration and settings."""
    
    def test_security_settings_loaded(self):
        """Test that security settings are properly loaded."""
        assert settings.SECRET_KEY is not None
        assert settings.ALGORITHM is not None
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES > 0
        assert settings.REFRESH_TOKEN_EXPIRE_DAYS > 0
    
    def test_password_policy_settings(self):
        """Test password policy settings."""
        assert isinstance(settings.PASSWORD_MIN_LENGTH, int)
        assert settings.PASSWORD_MIN_LENGTH > 0
        assert isinstance(settings.PASSWORD_REQUIRE_UPPERCASE, bool)
        assert isinstance(settings.PASSWORD_REQUIRE_LOWERCASE, bool)
        assert isinstance(settings.PASSWORD_REQUIRE_NUMBERS, bool)
        assert isinstance(settings.PASSWORD_REQUIRE_SYMBOLS, bool)
    
    def test_token_expiry_configuration(self):
        """Test token expiry configuration."""
        # Test that tokens respect configuration
        subject = "test_user"
        token = create_access_token(subject=subject)
        payload = verify_token(token)
        
        # Check that expiry is set correctly (approximately)
        expected_exp = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        actual_exp = datetime.fromtimestamp(payload["exp"])
        
        # Allow 10 second variance for test execution time
        assert abs((expected_exp - actual_exp).total_seconds()) < 10