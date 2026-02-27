"""
Cache module for MatchLearn application.

This module provides caching functionality for expensive operations
like LLM API calls and database queries.
"""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Optional
from collections import OrderedDict


# Simple in-memory cache with LRU eviction
class LRUCache:
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        """
        Initialize LRU cache.

        Args:
            max_size: Maximum number of items in cache
            default_ttl: Default time-to-live in seconds
        """
        self.cache: OrderedDict[str, dict] = OrderedDict()
        self.max_size = max_size
        self.default_ttl = default_ttl

    def _generate_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        key_parts = []

        # Add positional arguments
        for arg in args:
            if isinstance(arg, (str, int, float, bool, type(None))):
                key_parts.append(str(arg))
            elif isinstance(arg, (list, dict)):
                key_parts.append(json.dumps(arg, sort_keys=True))
            else:
                key_parts.append(str(arg))

        # Add keyword arguments
        for key, value in sorted(kwargs.items()):
            key_parts.append(
                f"{key}:{json.dumps(value, sort_keys=True) if isinstance(value, (list, dict)) else value}"
            )

        # Create hash
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()

    def get(self, *args, **kwargs) -> Optional[Any]:
        """Get item from cache."""
        key = self._generate_key(*args, **kwargs)

        if key not in self.cache:
            return None

        item = self.cache[key]

        # Check if item has expired
        if item["expires_at"] < datetime.now():
            del self.cache[key]
            return None

        # Move to end (most recently used)
        self.cache.move_to_end(key)
        return item["value"]

    def set(self, value: Any, *args, ttl: Optional[int] = None, **kwargs) -> None:
        """Set item in cache."""
        key = self._generate_key(*args, **kwargs)

        # Calculate expiration time
        ttl = ttl if ttl is not None else self.default_ttl
        expires_at = datetime.now() + timedelta(seconds=ttl)

        # Add to cache
        self.cache[key] = {
            "value": value,
            "expires_at": expires_at,
            "created_at": datetime.now(),
        }

        # Move to end (most recently used)
        self.cache.move_to_end(key)

        # Evict if cache is full
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)

    def clear(self) -> None:
        """Clear all items from cache."""
        self.cache.clear()

    def size(self) -> int:
        """Get current cache size."""
        return len(self.cache)

    def cleanup(self) -> int:
        """Remove expired items and return number removed."""
        removed = 0
        now = datetime.now()

        # Create list of keys to remove (can't modify dict during iteration)
        keys_to_remove = []
        for key, item in self.cache.items():
            if item["expires_at"] < now:
                keys_to_remove.append(key)

        # Remove expired items
        for key in keys_to_remove:
            del self.cache[key]
            removed += 1

        return removed


# Global cache instances
llm_cache = LRUCache(max_size=500, default_ttl=86400)  # 24 hours for LLM results
api_cache = LRUCache(max_size=1000, default_ttl=300)  # 5 minutes for API responses


def cache_llm_result(func):
    """
    Decorator to cache LLM function results.

    Usage:
        @cache_llm_result
        async def analyze_gap(resume_json, jd_json, completed_courses):
            # LLM call here
    """

    async def wrapper(*args, **kwargs):
        # Skip caching if force_analyze is True
        if "force_analyze" in kwargs and kwargs["force_analyze"]:
            return await func(*args, **kwargs)

        # Try to get from cache
        cached_result = llm_cache.get(*args, **kwargs)
        if cached_result is not None:
            print(f"DEBUG: Cache hit for {func.__name__}")
            return cached_result

        # Call function and cache result
        result = await func(*args, **kwargs)

        # Only cache successful results (not errors)
        if isinstance(result, dict) and "error" not in result:
            llm_cache.set(result, *args, **kwargs)
            print(f"DEBUG: Cached result for {func.__name__}")

        return result

    return wrapper


def cache_api_response(ttl: int = 300):
    """
    Decorator to cache API endpoint responses.

    Args:
        ttl: Time-to-live in seconds
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Try to get from cache
            cached_result = api_cache.get(func.__name__, *args, **kwargs)
            if cached_result is not None:
                print(f"DEBUG: API cache hit for {func.__name__}")
                return cached_result

            # Call function and cache result
            result = await func(*args, **kwargs)

            # Cache successful responses
            if not isinstance(result, dict) or "error" not in result:
                api_cache.set(result, func.__name__, *args, ttl=ttl, **kwargs)
                print(f"DEBUG: Cached API response for {func.__name__}")

            return result

        return wrapper

    return decorator
