"""
Configuration settings for the Payroll Management System.

This module defines all configuration settings using Pydantic BaseSettings
for automatic environment variable loading and validation.
"""

from functools import lru_cache
from typing import Any, Dict, List, Optional, Union

from pydantic import AnyHttpUrl, EmailStr, Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application Settings
    APP_NAME: str = Field(default="Payroll Management System")
    APP_VERSION: str = Field(default="0.1.0")
    DEBUG: bool = Field(default=False)
    ENVIRONMENT: str = Field(default="production")
    LOG_LEVEL: str = Field(default="INFO")

    # Server Configuration
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)
    RELOAD: bool = Field(default=False)

    # API Configuration
    API_V1_STR: str = Field(default="/api/v1")
    ALLOWED_HOSTS: List[str] = Field(default=["*"])

    # Database Configuration
    DATABASE_URL: str = Field(
        default="sqlite:///./payroll.db"
    )
    DATABASE_TEST_URL: str = Field(
        default="sqlite:///./payroll_test.db"
    )

    # Security Configuration
    SECRET_KEY: str = Field(
        default="your-super-secret-key-here-change-this-in-production"
    )
    ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)

    # Password Security
    PASSWORD_MIN_LENGTH: int = Field(default=8)
    PASSWORD_REQUIRE_UPPERCASE: bool = Field(default=True)
    PASSWORD_REQUIRE_LOWERCASE: bool = Field(default=True)
    PASSWORD_REQUIRE_NUMBERS: bool = Field(default=True)
    PASSWORD_REQUIRE_SYMBOLS: bool = Field(default=True)

    # CORS Configuration
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = Field(default=[])

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    @field_validator("ALLOWED_FILE_EXTENSIONS", mode="before")
    @classmethod
    def assemble_file_extensions(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        """Parse file extensions from string or list."""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip().strip('"') for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Email Configuration (Optional)
    SMTP_HOST: Optional[str] = Field(default=None)
    SMTP_PORT: Optional[int] = Field(default=587)
    SMTP_USERNAME: Optional[str] = Field(default=None)
    SMTP_PASSWORD: Optional[str] = Field(default=None)
    SMTP_FROM_EMAIL: Optional[EmailStr] = Field(default=None)
    SMTP_FROM_NAME: Optional[str] = Field(default=None)

    # Redis Configuration
    REDIS_URL: str = Field(default="redis://localhost:6379/0")

    # Celery Configuration
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/0")

    # File Upload Configuration
    MAX_FILE_SIZE: int = Field(default=10485760)  # 10MB in bytes
    ALLOWED_FILE_EXTENSIONS: List[str] = Field(
        default=[".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png"]
    )
    UPLOAD_DIRECTORY: str = Field(default="uploads")

    # Tax Configuration
    SOCIAL_SECURITY_RATE: float = Field(default=0.062, description="Social Security tax rate")
    MEDICARE_RATE: float = Field(default=0.0145, description="Medicare tax rate")
    DEFAULT_TAX_RATE: float = Field(default=0.20, description="Default tax rate for calculations")
    FEDERAL_UNEMPLOYMENT_RATE: float = Field(default=0.006, description="Federal unemployment tax rate")
    STATE_UNEMPLOYMENT_RATE: float = Field(default=0.034, description="State unemployment tax rate")

    # Company Information
    COMPANY_NAME: str = Field(default="Your Company Name")
    COMPANY_ADDRESS: str = Field(default="123 Main St, City, State 12345")
    COMPANY_PHONE: str = Field(default="(555) 123-4567")
    COMPANY_EMAIL: EmailStr = Field(default="info@yourcompany.com")
    COMPANY_EIN: str = Field(default="12-3456789")

    # Banking Information (Encrypted)
    BANK_NAME: Optional[str] = Field(default=None)
    BANK_ROUTING_NUMBER: Optional[str] = Field(default=None)
    BANK_ACCOUNT_NUMBER: Optional[str] = Field(default=None)

    # External API Keys (if needed)
    EXTERNAL_TAX_API_KEY: Optional[str] = Field(default=None)
    BANK_API_KEY: Optional[str] = Field(default=None)
    ACCOUNTING_API_KEY: Optional[str] = Field(default=None)

    # Monitoring and Logging
    SENTRY_DSN: Optional[str] = Field(default=None)
    LOG_FILE_PATH: str = Field(default="logs/payroll.log")
    LOG_ROTATION_SIZE: str = Field(default="10MB")
    LOG_RETENTION_DAYS: int = Field(default=30)

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings() 