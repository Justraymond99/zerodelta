from __future__ import annotations

import json
import hashlib
from typing import Any, Optional
from functools import wraps
from .utils.logger import get_logger

logger = get_logger(__name__)

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available. Caching disabled.")


class Cache:
    """Simple caching layer with Redis backend."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0", default_ttl: int = 3600):
        self.default_ttl = default_ttl
        self.redis_client = None
        
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                self.redis_client.ping()
                logger.info("Redis cache connected")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}. Caching disabled.")
                self.redis_client = None
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.redis_client:
            return None
        
        try:
            value = self.redis_client.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
        
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        if not self.redis_client:
            return False
        
        try:
            ttl = ttl or self.default_ttl
            serialized = json.dumps(value, default=str)
            self.redis_client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self.redis_client:
            return False
        
        try:
            self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern."""
        if not self.redis_client:
            return 0
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return 0


# Global cache instance
_cache_instance: Optional[Cache] = None


def get_cache() -> Cache:
    """Get global cache instance."""
    global _cache_instance
    if _cache_instance is None:
        import os
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        _cache_instance = Cache(redis_url=redis_url)
    return _cache_instance


def cached(ttl: int = 3600, key_prefix: str = ""):
    """Decorator to cache function results."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_cache()
            
            # Generate cache key
            key_parts = [key_prefix, func.__name__]
            if args:
                key_parts.append(str(hash(str(args))))
            if kwargs:
                key_parts.append(str(hash(str(sorted(kwargs.items())))))
            cache_key = ":".join(key_parts)
            
            # Try cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Cache result
            cache.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator

