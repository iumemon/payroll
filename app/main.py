"""
FastAPI Application Entry Point.

This module sets up the FastAPI application with all necessary middleware,
routers, and configuration.
"""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
import time
import json

from app.core.config import get_settings
from app.core.database import init_db
from app.core.cache import start_cleanup_task
from app.api.v1.api import api_router
from app.core.middleware import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    RequestValidationMiddleware,
    PerformanceMiddleware,
    CacheControlMiddleware
)
from app.core.logging import RequestLoggingMiddleware, setup_logging

# Configure logging
setup_logging()
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    # Startup
    logger.info("Starting up Payroll Management System...")
    await init_db()
    logger.info("Database initialized successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Payroll Management System...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="A comprehensive payroll management system with advanced features",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan
    )
    
    # Add middleware (order matters - first added is outermost)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_HOSTS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request logging middleware (should be early to capture all requests)
    app.add_middleware(RequestLoggingMiddleware)

    # Security middleware
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestValidationMiddleware, max_request_size=10 * 1024 * 1024)  # 10MB
    app.add_middleware(RateLimitMiddleware, default_requests_per_minute=60, auth_requests_per_minute=10)

    # Performance middleware
    app.add_middleware(PerformanceMiddleware, slow_request_threshold=2.0)
    app.add_middleware(CacheControlMiddleware)

    # Compression middleware
    app.add_middleware(GZipMiddleware, minimum_size=500, compresslevel=6)

    # Session middleware
    app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

    # Trusted hosts middleware
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)
    
    # Include API router
    app.include_router(api_router, prefix=settings.API_V1_STR)
    
    return app


# Create the app instance
app = create_app()


# Exception handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": time.time()
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors."""
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation error",
            "details": exc.errors(),
            "status_code": 422,
            "timestamp": time.time()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "timestamp": time.time()
        }
    )


# Health check endpoint
@app.get("/", tags=["Health"])
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": time.time()
    }


# Root redirect
@app.get("/api", tags=["Root"])
async def api_root():
    """API root endpoint."""
    return {
        "message": "Payroll Management API",
        "version": settings.APP_VERSION,
        "docs_url": "/api/docs",
        "redoc_url": "/api/redoc",
        "openapi_url": "/api/openapi.json"
    }


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info("Starting up Payroll Management System...")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized successfully")
    
    # Start cache cleanup task
    start_cleanup_task(interval=300)  # Clean up every 5 minutes
    logger.info("Cache cleanup task started")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        access_log=True,
        log_level="info"
    ) 