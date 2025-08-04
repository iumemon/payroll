"""
Test configuration and fixtures for the payroll management system.

This module provides pytest fixtures for database testing, API client testing,
and common test data.
"""

import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.main import app
from app.core.database import Base, get_db
from app.core.config import get_settings
from app.models import User, Employee, PayrollRecord, PayPeriod, TimeEntry
from app.models.enums import UserRole, UserStatus, EmployeeStatus, EmploymentType
from app.core.security import get_password_hash

# Test database URL
TEST_DATABASE_URL = "sqlite:///./test_payroll.db"
TEST_ASYNC_DATABASE_URL = "sqlite+aiosqlite:///./test_payroll.db"

settings = get_settings()


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def test_db_engine():
    """Create a test database engine."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
async def test_async_db_engine():
    """Create a test async database engine."""
    engine = create_async_engine(
        TEST_ASYNC_DATABASE_URL,
        echo=False
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture(scope="function")
def test_db_session(test_db_engine) -> Generator[Session, None, None]:
    """Create a test database session."""
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_db_engine
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest_asyncio.fixture(scope="function")
async def test_async_db_session(test_async_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test async database session."""
    TestingAsyncSessionLocal = async_sessionmaker(
        bind=test_async_db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    async with TestingAsyncSessionLocal() as session:
        yield session


@pytest.fixture(scope="function")
def override_get_db(test_db_session):
    """Override the database dependency for testing."""
    def _override_get_db():
        yield test_db_session
    
    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def test_client(override_get_db) -> AsyncGenerator[AsyncClient, None]:
    """Create a test HTTP client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# Test data fixtures
@pytest.fixture
def test_user_data():
    """Sample user data for testing."""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPass123!",
        "first_name": "Test",
        "last_name": "User",
        "role": UserRole.USER,
        "status": UserStatus.ACTIVE
    }


@pytest.fixture
def test_admin_data():
    """Sample admin user data for testing."""
    return {
        "username": "admin",
        "email": "admin@example.com",
        "password": "AdminPass123!",
        "first_name": "Admin",
        "last_name": "User",
        "role": UserRole.ADMIN,
        "status": UserStatus.ACTIVE
    }


@pytest.fixture
def test_employee_data():
    """Sample employee data for testing."""
    return {
        "employee_id": "EMP001",
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@company.com",
        "phone": "555-1234",
        "address": "123 Main St",
        "city": "Anytown",
        "state": "CA",
        "zip_code": "12345",
        "department": "Engineering",
        "position": "Software Developer",
        "employment_type": EmploymentType.FULL_TIME,
        "status": EmployeeStatus.ACTIVE,
        "salary": 75000.00,
        "hourly_rate": 36.06
    }


@pytest.fixture
def test_user(test_db_session, test_user_data) -> User:
    """Create a test user in the database."""
    user_data = test_user_data.copy()
    password = user_data.pop("password")
    user = User(**user_data)
    user.hashed_password = get_password_hash(password)
    user.is_active = True
    user.is_verified = True
    
    test_db_session.add(user)
    test_db_session.commit()
    test_db_session.refresh(user)
    return user


@pytest.fixture
def test_admin(test_db_session, test_admin_data) -> User:
    """Create a test admin user in the database."""
    admin_data = test_admin_data.copy()
    password = admin_data.pop("password")
    admin = User(**admin_data)
    admin.hashed_password = get_password_hash(password)
    admin.is_active = True
    admin.is_verified = True
    admin.is_superuser = True
    
    test_db_session.add(admin)
    test_db_session.commit()
    test_db_session.refresh(admin)
    return admin


@pytest.fixture
def test_employee(test_db_session, test_employee_data) -> Employee:
    """Create a test employee in the database."""
    employee = Employee(**test_employee_data)
    test_db_session.add(employee)
    test_db_session.commit()
    test_db_session.refresh(employee)
    return employee


@pytest.fixture
def auth_headers(test_user):
    """Create authentication headers for test requests."""
    from app.core.security import create_access_token
    
    access_token = create_access_token(subject=test_user.id)
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def admin_auth_headers(test_admin):
    """Create admin authentication headers for test requests."""
    from app.core.security import create_access_token
    
    access_token = create_access_token(subject=test_admin.id)
    return {"Authorization": f"Bearer {access_token}"}


# Test utilities
@pytest.fixture
def test_utils():
    """Utility functions for testing."""
    class TestUtils:
        @staticmethod
        def create_test_user(session: Session, **kwargs) -> User:
            """Create a test user with default values."""
            defaults = {
                "username": "testuser",
                "email": "test@example.com",
                "first_name": "Test",
                "last_name": "User",
                "role": UserRole.USER,
                "status": UserStatus.ACTIVE,
                "is_active": True,
                "is_verified": True
            }
            defaults.update(kwargs)
            
            if "password" in defaults:
                password = defaults.pop("password")
                defaults["hashed_password"] = get_password_hash(password)
            
            user = User(**defaults)
            session.add(user)
            session.commit()
            session.refresh(user)
            return user
        
        @staticmethod
        def create_test_employee(session: Session, **kwargs) -> Employee:
            """Create a test employee with default values."""
            defaults = {
                "employee_id": "EMP001",
                "first_name": "John",
                "last_name": "Doe",
                "email": "john.doe@company.com",
                "department": "Engineering",
                "position": "Software Developer",
                "employment_type": EmploymentType.FULL_TIME,
                "status": EmployeeStatus.ACTIVE,
                "salary": 75000.00
            }
            defaults.update(kwargs)
            
            employee = Employee(**defaults)
            session.add(employee)
            session.commit()
            session.refresh(employee)
            return employee
    
    return TestUtils()