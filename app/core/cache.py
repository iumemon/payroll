"""
Caching layer for the payroll management system.

This module provides Redis-compatible caching functionality using an in-memory cache
with TTL support. Can be easily switched to Redis for production use.
"""

import json
import time
import threading
from typing import Any, Optional, Dict, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@dataclass
class CacheItem:
    """Represents a cached item with expiration."""
    value: Any
    expires_at: float
    created_at: float = field(default_factory=time.time)
    
    def is_expired(self) -> bool:
        """Check if the cache item has expired."""
        return time.time() > self.expires_at


class InMemoryCache:
    """
    In-memory cache implementation with Redis-compatible interface.
    
    This provides a simple caching layer that can be easily replaced with Redis
    for production use while maintaining the same interface.
    """
    
    def __init__(self, default_ttl: int = 300):
        """
        Initialize the cache.
        
        Args:
            default_ttl: Default time-to-live in seconds
        """
        self._cache: Dict[str, CacheItem] = {}
        self._lock = threading.RLock()
        self._default_ttl = default_ttl
        self._stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'evictions': 0
        }
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            if key not in self._cache:
                self._stats['misses'] += 1
                return None
            
            item = self._cache[key]
            if item.is_expired():
                del self._cache[key]
                self._stats['misses'] += 1
                self._stats['evictions'] += 1
                return None
            
            self._stats['hits'] += 1
            return item.value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds
            
        Returns:
            True if set successfully
        """
        try:
            with self._lock:
                expires_at = time.time() + (ttl or self._default_ttl)
                self._cache[key] = CacheItem(value=value, expires_at=expires_at)
                self._stats['sets'] += 1
                return True
        except Exception as e:
            logger.error(f"Error setting cache key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        Delete a key from the cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if key was deleted, False if not found
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._stats['deletes'] += 1
                return True
            return False
    
    def exists(self, key: str) -> bool:
        """
        Check if a key exists in the cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists and is not expired
        """
        return self.get(key) is not None
    
    def clear(self) -> bool:
        """
        Clear all cache entries.
        
        Returns:
            True if cleared successfully
        """
        try:
            with self._lock:
                self._cache.clear()
                return True
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False
    
    def keys(self, pattern: str = "*") -> list:
        """
        Get all keys matching a pattern.
        
        Args:
            pattern: Pattern to match (simplified glob-style)
            
        Returns:
            List of matching keys
        """
        with self._lock:
            # Simple pattern matching - just prefix/suffix for now
            if pattern == "*":
                return list(self._cache.keys())
            elif pattern.endswith("*"):
                prefix = pattern[:-1]
                return [key for key in self._cache.keys() if key.startswith(prefix)]
            elif pattern.startswith("*"):
                suffix = pattern[1:]
                return [key for key in self._cache.keys() if key.endswith(suffix)]
            else:
                return [key for key in self._cache.keys() if key == pattern]
    
    def ttl(self, key: str) -> int:
        """
        Get the time-to-live for a key.
        
        Args:
            key: Cache key
            
        Returns:
            TTL in seconds, -1 if key doesn't exist, -2 if expired
        """
        with self._lock:
            if key not in self._cache:
                return -1
            
            item = self._cache[key]
            if item.is_expired():
                return -2
            
            return int(item.expires_at - time.time())
    
    def cleanup_expired(self) -> int:
        """
        Remove expired items from the cache.
        
        Returns:
            Number of items removed
        """
        with self._lock:
            expired_keys = [
                key for key, item in self._cache.items()
                if item.is_expired()
            ]
            
            for key in expired_keys:
                del self._cache[key]
                self._stats['evictions'] += 1
            
            return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        with self._lock:
            hit_rate = (
                self._stats['hits'] / (self._stats['hits'] + self._stats['misses'])
                if (self._stats['hits'] + self._stats['misses']) > 0 else 0
            )
            
            return {
                **self._stats,
                'hit_rate': hit_rate,
                'total_keys': len(self._cache),
                'memory_usage': sum(
                    len(str(item.value)) for item in self._cache.values()
                )
            }
    
    def size(self) -> int:
        """Get the number of items in the cache."""
        return len(self._cache)


# Global cache instance
_cache = InMemoryCache(default_ttl=300)  # 5 minutes default TTL


def get_cache() -> InMemoryCache:
    """Get the global cache instance."""
    return _cache


def cache_key(*args, **kwargs) -> str:
    """
    Generate a cache key from arguments.
    
    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments
        
    Returns:
        Cache key string
    """
    key_parts = []
    
    # Add positional arguments
    for arg in args:
        if isinstance(arg, (str, int, float, bool)):
            key_parts.append(str(arg))
        else:
            key_parts.append(str(hash(str(arg))))
    
    # Add keyword arguments (sorted for consistency)
    for key, value in sorted(kwargs.items()):
        if isinstance(value, (str, int, float, bool)):
            key_parts.append(f"{key}:{value}")
        else:
            key_parts.append(f"{key}:{hash(str(value))}")
    
    return ":".join(key_parts)


def cached(ttl: int = 300, key_prefix: str = ""):
    """
    Decorator for caching function results.
    
    Args:
        ttl: Time-to-live in seconds
        key_prefix: Prefix for cache keys
        
    Returns:
        Decorator function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Generate cache key
            func_key = f"{key_prefix}{func.__name__}" if key_prefix else func.__name__
            key = cache_key(func_key, *args, **kwargs)
            
            # Try to get from cache
            result = _cache.get(key)
            if result is not None:
                logger.debug(f"Cache hit for {func.__name__}: {key}")
                return result
            
            # Execute function and cache result
            logger.debug(f"Cache miss for {func.__name__}: {key}")
            result = func(*args, **kwargs)
            _cache.set(key, result, ttl)
            
            return result
        
        return wrapper
    return decorator


# Background cleanup task
def start_cleanup_task(interval: int = 300):
    """
    Start a background task to clean up expired cache entries.
    
    Args:
        interval: Cleanup interval in seconds
    """
    def cleanup_worker():
        while True:
            try:
                removed = _cache.cleanup_expired()
                if removed > 0:
                    logger.info(f"Cleaned up {removed} expired cache entries")
                time.sleep(interval)
            except Exception as e:
                logger.error(f"Error in cache cleanup task: {e}")
                time.sleep(interval)
    
    cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
    cleanup_thread.start()
    logger.info(f"Started cache cleanup task with {interval}s interval")


# Cache utility functions for common operations
class CacheManager:
    """Manager class for common caching operations."""
    
    @staticmethod
    def get_employees_list(skip: int = 0, limit: int = 100, **filters) -> Optional[Any]:
        """Get cached employees list."""
        key = cache_key("employees_list", skip, limit, **filters)
        return _cache.get(key)
    
    @staticmethod
    def set_employees_list(employees_data: Any, skip: int = 0, limit: int = 100, **filters) -> bool:
        """Cache employees list."""
        key = cache_key("employees_list", skip, limit, **filters)
        return _cache.set(key, employees_data, ttl=300)  # 5 minutes
    
    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[Any]:
        """Get cached user by ID."""
        key = cache_key("user", user_id)
        return _cache.get(key)
    
    @staticmethod
    def set_user_by_id(user_id: int, user_data: Any) -> bool:
        """Cache user by ID."""
        key = cache_key("user", user_id)
        return _cache.set(key, user_data, ttl=600)  # 10 minutes
    
    @staticmethod
    def invalidate_user(user_id: int) -> bool:
        """Invalidate cached user data."""
        key = cache_key("user", user_id)
        return _cache.delete(key)
    
    @staticmethod
    def get_payroll_records(employee_id: int, **filters) -> Optional[Any]:
        """Get cached payroll records."""
        key = cache_key("payroll_records", employee_id, **filters)
        return _cache.get(key)
    
    @staticmethod
    def set_payroll_records(employee_id: int, records_data: Any, **filters) -> bool:
        """Cache payroll records."""
        key = cache_key("payroll_records", employee_id, **filters)
        return _cache.set(key, records_data, ttl=1800)  # 30 minutes
    
    @staticmethod
    def invalidate_pattern(pattern: str) -> int:
        """Invalidate all keys matching a pattern."""
        keys = _cache.keys(pattern)
        count = 0
        for key in keys:
            if _cache.delete(key):
                count += 1
        return count 