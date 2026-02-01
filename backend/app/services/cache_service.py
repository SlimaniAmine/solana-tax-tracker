"""Caching service."""
from typing import Optional, Any
from datetime import datetime, timedelta
from app.config import settings
import json
import hashlib

# TODO: Implement proper caching in Phase 3
class CacheService:
    """Service for caching API responses and computed data."""
    
    def __init__(self):
        self.enabled = settings.enable_cache
        self.ttl_seconds = settings.cache_ttl_seconds
        # In-memory cache for now (can be upgraded to Redis)
        self._cache: dict[str, tuple[Any, datetime]] = {}
    
    def _make_key(self, prefix: str, *args) -> str:
        """Generate cache key from prefix and arguments."""
        key_data = json.dumps(args, sort_keys=True, default=str)
        key_hash = hashlib.md5(key_data.encode()).hexdigest()
        return f"{prefix}:{key_hash}"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.enabled:
            return None
        
        if key not in self._cache:
            return None
        
        value, expiry = self._cache[key]
        if datetime.utcnow() > expiry:
            del self._cache[key]
            return None
        
        return value
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None):
        """Set value in cache."""
        if not self.enabled:
            return
        
        ttl = ttl_seconds or self.ttl_seconds
        expiry = datetime.utcnow() + timedelta(seconds=ttl)
        self._cache[key] = (value, expiry)
    
    def delete(self, key: str):
        """Delete value from cache."""
        if key in self._cache:
            del self._cache[key]
    
    def clear(self):
        """Clear all cache."""
        self._cache.clear()
