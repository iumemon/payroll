"""
Security middleware for the payroll management system.

This module provides security enhancements including rate limiting,
request validation, and security headers.
"""

import time
import logging
from typing import Dict, Any, Optional
from collections import defaultdict, deque
from datetime import datetime, timedelta
import asyncio
from ipaddress import ip_address, IPv4Address, IPv6Address

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware to prevent abuse.
    
    Implements a sliding window rate limiter with different limits
    for different types of requests.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        default_requests_per_minute: int = 60,
        auth_requests_per_minute: int = 10,
        cleanup_interval: int = 300
    ):
        super().__init__(app)
        self.default_rpm = default_requests_per_minute
        self.auth_rpm = auth_requests_per_minute
        self.cleanup_interval = cleanup_interval
        
        # Store request timestamps for each IP
        self.request_history: Dict[str, deque] = defaultdict(deque)
        self.last_cleanup = time.time()
        
        # Define rate limits for different endpoints
        self.rate_limits = {
            '/api/v1/auth/login': auth_requests_per_minute,
            '/api/v1/auth/register': auth_requests_per_minute,
            '/api/v1/auth/refresh': auth_requests_per_minute,
            '/api/v1/auth/forgot-password': 3,  # Very restrictive
            '/api/v1/auth/reset-password': 3,   # Very restrictive
            'default': default_requests_per_minute
        }
    
    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""
        client_ip = self.get_client_ip(request)
        path = request.url.path
        
        # Check rate limit
        if not self.is_allowed(client_ip, path):
            logger.warning(f"Rate limit exceeded for IP {client_ip} on path {path}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "detail": "Too many requests. Please try again later.",
                    "retry_after": 60
                },
                headers={"Retry-After": "60"}
            )
        
        # Record the request
        self.record_request(client_ip)
        
        # Periodic cleanup
        if time.time() - self.last_cleanup > self.cleanup_interval:
            self.cleanup_old_requests()
            self.last_cleanup = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        limit = self.get_rate_limit(path)
        remaining = max(0, limit - len(self.request_history[client_ip]))
        
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time() + 60))
        
        return response
    
    def get_client_ip(self, request: Request) -> str:
        """Get client IP address with proxy support."""
        # Check for forwarded headers (common with proxies/load balancers)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        return request.client.host if request.client else "unknown"
    
    def get_rate_limit(self, path: str) -> int:
        """Get rate limit for a specific path."""
        # Check for exact match first
        if path in self.rate_limits:
            return self.rate_limits[path]
        
        # Check for pattern matches
        for pattern, limit in self.rate_limits.items():
            if pattern != 'default' and path.startswith(pattern):
                return limit
        
        return self.rate_limits['default']
    
    def is_allowed(self, client_ip: str, path: str) -> bool:
        """Check if request is allowed based on rate limits."""
        limit = self.get_rate_limit(path)
        now = time.time()
        cutoff = now - 60  # 1 minute window
        
        # Get request history for this IP
        history = self.request_history[client_ip]
        
        # Remove old requests (older than 1 minute)
        while history and history[0] < cutoff:
            history.popleft()
        
        # Check if under limit
        return len(history) < limit
    
    def record_request(self, client_ip: str) -> None:
        """Record a request timestamp for an IP."""
        self.request_history[client_ip].append(time.time())
    
    def cleanup_old_requests(self) -> None:
        """Clean up old request history data."""
        cutoff = time.time() - 3600  # Keep history for 1 hour
        
        for ip in list(self.request_history.keys()):
            history = self.request_history[ip]
            
            # Remove old requests
            while history and history[0] < cutoff:
                history.popleft()
            
            # Remove empty histories
            if not history:
                del self.request_history[ip]
        
        logger.info(f"Cleaned up rate limit history. Active IPs: {len(self.request_history)}")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Security headers middleware to add security-related HTTP headers.
    
    Adds headers to protect against common web vulnerabilities.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        
        # Define security headers
        self.security_headers = {
            # Prevent XSS attacks
            "X-XSS-Protection": "1; mode=block",
            
            # Prevent content type sniffing
            "X-Content-Type-Options": "nosniff",
            
            # Prevent clickjacking
            "X-Frame-Options": "DENY",
            
            # Content Security Policy
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; "
                "connect-src 'self'; "
                "font-src 'self'; "
                "object-src 'none'; "
                "base-uri 'self'; "
                "form-action 'self';"
            ),
            
            # Referrer Policy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            
            # Permissions Policy
            "Permissions-Policy": (
                "camera=(), "
                "microphone=(), "
                "geolocation=(), "
                "payment=(), "
                "usb=(), "
                "magnetometer=(), "
                "accelerometer=(), "
                "gyroscope=()"
            ),
            
            # Server information hiding
            "Server": "PayrollAPI/1.0",
            
            # Remove powered by headers
            "X-Powered-By": "",
        }
    
    async def dispatch(self, request: Request, call_next):
        """Add security headers to response."""
        response = await call_next(request)
        
        # Add security headers
        for header, value in self.security_headers.items():
            response.headers[header] = value
        
        return response


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """
    Request validation middleware for additional security checks.
    
    Validates requests for suspicious patterns and malicious content.
    """
    
    def __init__(self, app: ASGIApp, max_request_size: int = 10 * 1024 * 1024):  # 10MB default
        super().__init__(app)
        self.max_request_size = max_request_size
        
        # Define suspicious patterns
        self.suspicious_patterns = [
            # SQL injection patterns
            r"(?i)(union|select|insert|update|delete|drop|create|alter|exec|script)",
            # XSS patterns
            r"(?i)(<script|javascript:|on\w+\s*=)",
            # Path traversal patterns
            r"(\.\./|\.\.\\\|%2e%2e/|%2e%2e\\\\)",
            # Command injection patterns
            r"(?i)(;|\||&|`|\$\(|\$\{)",
        ]
    
    async def dispatch(self, request: Request, call_next):
        """Validate request before processing."""
        # Check request size
        if hasattr(request, 'headers'):
            content_length = request.headers.get('content-length')
            if content_length and int(content_length) > self.max_request_size:
                logger.warning(f"Request size too large: {content_length} bytes")
                return JSONResponse(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    content={"error": "Request too large"}
                )
        
        # Validate query parameters
        if request.url.query:
            if self.contains_suspicious_content(request.url.query):
                logger.warning(f"Suspicious query parameters: {request.url.query}")
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"error": "Invalid request parameters"}
                )
        
        # Validate headers
        for header_name, header_value in request.headers.items():
            if self.contains_suspicious_content(f"{header_name}:{header_value}"):
                logger.warning(f"Suspicious header: {header_name}={header_value}")
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"error": "Invalid request headers"}
                )
        
        return await call_next(request)
    
    def contains_suspicious_content(self, content: str) -> bool:
        """Check if content contains suspicious patterns."""
        import re
        
        for pattern in self.suspicious_patterns:
            if re.search(pattern, content):
                return True
        
        return False


class PerformanceMiddleware(BaseHTTPMiddleware):
    """
    Performance monitoring middleware.
    
    Tracks request duration and adds performance headers.
    """
    
    def __init__(self, app: ASGIApp, slow_request_threshold: float = 2.0):
        super().__init__(app)
        self.slow_request_threshold = slow_request_threshold
    
    async def dispatch(self, request: Request, call_next):
        """Track request performance."""
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Add performance headers
        response.headers["X-Response-Time"] = f"{duration:.4f}s"
        response.headers["X-Process-Time"] = f"{duration * 1000:.2f}ms"
        
        # Log slow requests
        if duration > self.slow_request_threshold:
            logger.warning(
                f"Slow request detected: {request.method} {request.url.path} "
                f"took {duration:.4f}s"
            )
        
        return response


class CacheControlMiddleware(BaseHTTPMiddleware):
    """
    Cache control middleware to set appropriate cache headers.
    
    Sets cache headers based on request path and content type.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        
        # Define cache policies for different paths
        self.cache_policies = {
            '/api/v1/health': 'no-cache',
            '/api/v1/auth/': 'no-cache, no-store, must-revalidate',
            '/api/v1/employees/': 'private, max-age=300',  # 5 minutes
            '/api/v1/reports/': 'private, max-age=600',    # 10 minutes
            '/api/docs': 'public, max-age=3600',           # 1 hour
            '/api/openapi.json': 'public, max-age=3600',   # 1 hour
            'default': 'private, max-age=300'               # 5 minutes default
        }
    
    async def dispatch(self, request: Request, call_next):
        """Set cache control headers."""
        response = await call_next(request)
        
        # Get cache policy for path
        cache_policy = self.get_cache_policy(request.url.path)
        
        # Set cache headers
        response.headers["Cache-Control"] = cache_policy
        
        # Add ETag for cacheable responses
        if response.status_code == 200 and 'max-age' in cache_policy:
            response.headers["ETag"] = f'"{hash(str(response.body))}"'
        
        return response
    
    def get_cache_policy(self, path: str) -> str:
        """Get cache policy for a path."""
        # Check for exact matches first
        if path in self.cache_policies:
            return self.cache_policies[path]
        
        # Check for pattern matches
        for pattern, policy in self.cache_policies.items():
            if pattern != 'default' and path.startswith(pattern):
                return policy
        
        return self.cache_policies['default'] 