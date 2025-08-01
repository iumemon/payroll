"""
Main API router for version 1.

This module combines all API endpoint routers into a single router
for the v1 API version.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, employees, payroll, time_tracking, reports

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(employees.router, prefix="/employees", tags=["employees"])
api_router.include_router(payroll.router, prefix="/payroll", tags=["payroll"])
api_router.include_router(time_tracking.router, prefix="/time-tracking", tags=["time-tracking"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])

# Add a health check endpoint for the API
@api_router.get("/health", tags=["health"])
async def api_health():
    """API health check endpoint."""
    return {
        "status": "healthy",
        "service": "payroll-management-api",
        "version": "1.0.0"
    } 