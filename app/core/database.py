"""
Database configuration and connection management.

This module provides database connection setup, session management,
and initialization functions for the payroll management system.
"""

import logging
from typing import AsyncGenerator
from sqlalchemy import create_engine, event, pool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import QueuePool, StaticPool

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Create the base class for declarative models
Base = declarative_base()

# Database connection strings
DATABASE_URL = settings.DATABASE_URL
if DATABASE_URL.startswith("sqlite://"):
    ASYNC_DATABASE_URL = DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://", 1)
else:
    ASYNC_DATABASE_URL = DATABASE_URL

# Connection pool configuration
POOL_CONFIG = {
    "pool_size": 10,           # Number of permanent connections to maintain
    "max_overflow": 20,        # Maximum number of connections to create beyond pool_size
    "pool_timeout": 30,        # Timeout for getting connection from pool
    "pool_recycle": 3600,      # Recycle connections after 1 hour
    "pool_pre_ping": True,     # Validate connections before use
}

# For SQLite, we need to use StaticPool for in-memory databases
# and NullPool for file-based databases (async compatibility)
if "memory" in DATABASE_URL:
    sqlite_pool_class = StaticPool
    async_pool_class = StaticPool
else:
    sqlite_pool_class = QueuePool
    async_pool_class = pool.NullPool  # Use NullPool for async SQLite

# Create sync engine with optimized settings
sync_engine = create_engine(
    DATABASE_URL,
    poolclass=sqlite_pool_class,
    pool_size=POOL_CONFIG["pool_size"],
    max_overflow=POOL_CONFIG["max_overflow"],
    pool_timeout=POOL_CONFIG["pool_timeout"],
    pool_recycle=POOL_CONFIG["pool_recycle"],
    pool_pre_ping=POOL_CONFIG["pool_pre_ping"],
    echo=settings.DEBUG,
    future=True,
    # SQLite-specific optimizations
    connect_args={
        "check_same_thread": False,
        "timeout": 20,
        # Performance optimizations
        "isolation_level": None,  # Use autocommit mode
    },
)

# Create async engine with optimized settings
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    poolclass=async_pool_class,
    echo=settings.DEBUG,
    future=True,
    # SQLite-specific optimizations
    connect_args={
        "check_same_thread": False,
        "timeout": 20,
    },
)

# Create session factories
sync_session_factory = sessionmaker(
    bind=sync_engine,
    class_=Session,
    autoflush=True,
    autocommit=False,
    expire_on_commit=False  # Keep objects accessible after commit
)

async_session_factory = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autoflush=True,
    autocommit=False,
    expire_on_commit=False  # Keep objects accessible after commit
)


# SQLite optimization event listeners
@event.listens_for(sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set SQLite pragmas for performance optimization."""
    cursor = dbapi_connection.cursor()
    
    # Performance optimizations
    cursor.execute("PRAGMA journal_mode=WAL")          # Write-Ahead Logging
    cursor.execute("PRAGMA synchronous=NORMAL")        # Balanced durability/performance
    cursor.execute("PRAGMA cache_size=10000")          # Increase cache size
    cursor.execute("PRAGMA temp_store=MEMORY")         # Store temp tables in memory
    cursor.execute("PRAGMA mmap_size=268435456")       # 256MB memory-mapped I/O
    cursor.execute("PRAGMA page_size=4096")            # Optimal page size
    cursor.execute("PRAGMA busy_timeout=30000")        # 30-second busy timeout
    
    # Enable foreign key constraints
    cursor.execute("PRAGMA foreign_keys=ON")
    
    # Query optimization
    cursor.execute("PRAGMA optimize")
    
    cursor.close()
    
    logger.info("SQLite pragmas set for performance optimization")


@event.listens_for(async_engine.sync_engine, "connect")
def set_sqlite_pragma_async(dbapi_connection, connection_record):
    """Set SQLite pragmas for async engine."""
    set_sqlite_pragma(dbapi_connection, connection_record)


# Database session dependencies
def get_db() -> Session:
    """
    Get database session for dependency injection.
    
    Yields:
        Session: Database session
    """
    db = sync_session_factory()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get async database session for dependency injection.
    
    Yields:
        AsyncSession: Async database session
    """
    async with async_session_factory() as db:
        try:
            yield db
        except Exception as e:
            logger.error(f"Async database session error: {e}")
            await db.rollback()
            raise
        finally:
            await db.close()


# Database initialization
async def init_db() -> None:
    """Initialize database tables."""
    try:
        async with async_engine.begin() as conn:
            # Import all models to ensure they're registered
            from app.models import (
                User, Employee, PayrollRecord, PayPeriod, TimeEntry
            )
            
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            
        logger.info("Database tables created successfully")
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise


def init_sync_db() -> None:
    """Initialize database tables synchronously."""
    try:
        # Import all models to ensure they're registered
        from app.models import (
            User, Employee, PayrollRecord, PayPeriod, TimeEntry
        )
        
        # Create all tables
        Base.metadata.create_all(bind=sync_engine)
        
        logger.info("Database tables created successfully (sync)")
        
    except Exception as e:
        logger.error(f"Error initializing database (sync): {e}")
        raise


# Health check functions
def check_db_health() -> bool:
    """Check database health synchronously."""
    try:
        with sync_session_factory() as db:
            # Simple query to check connection
            db.execute("SELECT 1")
            return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


async def check_async_db_health() -> bool:
    """Check async database health."""
    try:
        async with async_session_factory() as db:
            # Simple query to check connection
            await db.execute("SELECT 1")
            return True
    except Exception as e:
        logger.error(f"Async database health check failed: {e}")
        return False


# Connection pool monitoring
def get_pool_status() -> dict:
    """Get connection pool status."""
    pool = sync_engine.pool
    return {
        "pool_size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "invalid": pool.invalid(),
        "total_connections": pool.size() + pool.overflow(),
        "available_connections": pool.checkedin()
    }


def get_async_pool_status() -> dict:
    """Get async connection pool status."""
    pool = async_engine.pool
    return {
        "pool_size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "invalid": pool.invalid(),
        "total_connections": pool.size() + pool.overflow(),
        "available_connections": pool.checkedin()
    }


# Cleanup function
async def cleanup_db():
    """Cleanup database connections."""
    try:
        await async_engine.dispose()
        sync_engine.dispose()
        logger.info("Database connections cleaned up")
    except Exception as e:
        logger.error(f"Error cleaning up database connections: {e}")


# Export commonly used items
__all__ = [
    "Base",
    "sync_engine",
    "async_engine",
    "sync_session_factory",
    "async_session_factory",
    "get_db",
    "get_async_db",
    "init_db",
    "init_sync_db",
    "check_db_health",
    "check_async_db_health",
    "get_pool_status",
    "get_async_pool_status",
    "cleanup_db"
] 