"""
Structured logging configuration for the payroll management system.

This module provides structured logging with JSON formatting,
request correlation IDs, and performance monitoring.
"""

import json
import logging
import logging.config
import sys
import time
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from contextlib import contextmanager

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.config import get_settings

settings = get_settings()


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        import socket
        try:
            self.hostname = socket.gethostname()
        except Exception:
            self.hostname = "unknown"
        self.service_name = "payroll-api"
        self.version = "1.0.0"
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self.service_name,
            "version": self.version,
            "hostname": self.hostname,
            "process_id": record.process,
            "thread_id": record.thread,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add correlation ID if available
        if hasattr(record, 'correlation_id'):
            log_data["correlation_id"] = record.correlation_id
        
        # Add request info if available
        if hasattr(record, 'request_id'):
            log_data["request_id"] = record.request_id
        
        if hasattr(record, 'user_id'):
            log_data["user_id"] = record.user_id
        
        if hasattr(record, 'ip_address'):
            log_data["ip_address"] = record.ip_address
        
        if hasattr(record, 'method'):
            log_data["http_method"] = record.method
        
        if hasattr(record, 'path'):
            log_data["http_path"] = record.path
        
        if hasattr(record, 'status_code'):
            log_data["http_status"] = record.status_code
        
        if hasattr(record, 'duration'):
            log_data["duration_ms"] = record.duration
        
        # Add exception info if available
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key.startswith('extra_'):
                log_data[key[6:]] = value  # Remove 'extra_' prefix
        
        return json.dumps(log_data, ensure_ascii=False)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Request logging middleware for structured request/response logging.
    
    Adds correlation IDs and logs request/response details.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.logger = logging.getLogger("app.request")
    
    async def dispatch(self, request: Request, call_next):
        """Log request and response details."""
        # Generate correlation ID
        correlation_id = str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Get client IP
        client_ip = self.get_client_ip(request)
        
        # Start timer
        start_time = time.time()
        
        # Log request
        self.logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                'correlation_id': correlation_id,
                'request_id': request_id,
                'method': request.method,
                'path': request.url.path,
                'query_params': str(request.query_params),
                'ip_address': client_ip,
                'user_agent': request.headers.get('user-agent', ''),
                'extra_event': 'request_start'
            }
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Log response
            self.logger.info(
                f"Request completed: {request.method} {request.url.path} - {response.status_code}",
                extra={
                    'correlation_id': correlation_id,
                    'request_id': request_id,
                    'method': request.method,
                    'path': request.url.path,
                    'status_code': response.status_code,
                    'duration': duration,
                    'ip_address': client_ip,
                    'extra_event': 'request_end'
                }
            )
            
            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # Calculate duration
            duration = (time.time() - start_time) * 1000
            
            # Log error
            self.logger.error(
                f"Request failed: {request.method} {request.url.path} - {type(e).__name__}: {str(e)}",
                extra={
                    'correlation_id': correlation_id,
                    'request_id': request_id,
                    'method': request.method,
                    'path': request.url.path,
                    'duration': duration,
                    'ip_address': client_ip,
                    'extra_event': 'request_error',
                    'extra_error_type': type(e).__name__,
                    'extra_error_message': str(e)
                },
                exc_info=True
            )
            
            raise
    
    def get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        # Check for forwarded headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"


class DatabaseLoggingFilter(logging.Filter):
    """Filter for database query logging."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter database logs based on configuration."""
        # Skip SQLAlchemy engine logs in production unless they're errors
        if record.name.startswith('sqlalchemy.engine') and settings.ENVIRONMENT == 'production':
            return record.levelno >= logging.WARNING
        
        return True


class PerformanceMonitor:
    """Performance monitoring utility."""
    
    def __init__(self):
        self.logger = logging.getLogger("app.performance")
        self.metrics = {
            'requests_total': 0,
            'requests_by_status': {},
            'slow_requests': 0,
            'avg_response_time': 0,
            'max_response_time': 0,
            'min_response_time': float('inf')
        }
    
    def record_request(self, duration: float, status_code: int, path: str):
        """Record request metrics."""
        self.metrics['requests_total'] += 1
        
        # Update status code counts
        status_group = f"{status_code // 100}xx"
        self.metrics['requests_by_status'][status_group] = (
            self.metrics['requests_by_status'].get(status_group, 0) + 1
        )
        
        # Update timing metrics
        duration_ms = duration * 1000
        
        if duration_ms > 2000:  # 2 seconds threshold
            self.metrics['slow_requests'] += 1
            
            # Log slow request
            self.logger.warning(
                f"Slow request detected: {path} took {duration_ms:.2f}ms",
                extra={
                    'extra_event': 'slow_request',
                    'extra_duration_ms': duration_ms,
                    'extra_path': path,
                    'extra_status_code': status_code
                }
            )
        
        # Update response time stats
        self.metrics['max_response_time'] = max(self.metrics['max_response_time'], duration_ms)
        self.metrics['min_response_time'] = min(self.metrics['min_response_time'], duration_ms)
        
        # Update average (simple moving average)
        current_avg = self.metrics['avg_response_time']
        total_requests = self.metrics['requests_total']
        self.metrics['avg_response_time'] = (
            (current_avg * (total_requests - 1) + duration_ms) / total_requests
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        return self.metrics.copy()
    
    def log_metrics(self):
        """Log current metrics."""
        self.logger.info(
            "Performance metrics",
            extra={
                'extra_event': 'performance_metrics',
                'extra_metrics': self.get_metrics()
            }
        )


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


def setup_logging():
    """Setup structured logging configuration."""
    
    # Define logging configuration
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": JSONFormatter,
            },
            "simple": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            }
        },
        "filters": {
            "database_filter": {
                "()": DatabaseLoggingFilter,
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "json" if settings.ENVIRONMENT == "production" else "simple",
                "stream": sys.stdout,
                "filters": ["database_filter"]
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "json",
                "filename": "logs/payroll-api.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "filters": ["database_filter"]
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "json",
                "filename": "logs/payroll-api-errors.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "level": "ERROR"
            }
        },
        "loggers": {
            "app": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False
            },
            "app.request": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False
            },
            "app.performance": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False
            },
            "app.security": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False
            },
            "sqlalchemy.engine": {
                "level": "INFO" if settings.DEBUG else "WARNING",
                "handlers": ["console"],
                "propagate": False
            },
            "uvicorn.access": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False
            }
        },
        "root": {
            "level": "INFO",
            "handlers": ["console", "error_file"]
        }
    }
    
    # Apply logging configuration
    logging.config.dictConfig(logging_config)
    
    # Create logs directory if it doesn't exist
    import os
    os.makedirs("logs", exist_ok=True)
    
    # Log startup message
    logger = logging.getLogger("app")
    logger.info(
        "Structured logging initialized",
        extra={
            'extra_event': 'logging_init',
            'extra_environment': settings.ENVIRONMENT,
            'extra_debug': settings.DEBUG
        }
    )


@contextmanager
def log_performance(operation_name: str, logger: Optional[logging.Logger] = None):
    """Context manager for logging performance of operations."""
    if logger is None:
        logger = logging.getLogger("app.performance")
    
    start_time = time.time()
    
    try:
        yield
        
        duration = time.time() - start_time
        logger.info(
            f"Operation completed: {operation_name}",
            extra={
                'extra_event': 'operation_performance',
                'extra_operation': operation_name,
                'extra_duration_ms': duration * 1000,
                'extra_status': 'success'
            }
        )
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            f"Operation failed: {operation_name} - {type(e).__name__}: {str(e)}",
            extra={
                'extra_event': 'operation_performance',
                'extra_operation': operation_name,
                'extra_duration_ms': duration * 1000,
                'extra_status': 'error',
                'extra_error_type': type(e).__name__,
                'extra_error_message': str(e)
            },
            exc_info=True
        )
        raise


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name."""
    return logging.getLogger(f"app.{name}")


# Initialize logging on module import
if settings.ENVIRONMENT in ["production", "staging"]:
    setup_logging() 