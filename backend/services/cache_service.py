"""Redis caching service for AI Fashion Discovery Platform."""
import json
import logging
from typing import Any, Optional

import redis

from core.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Manages Redis caching operations with TTL configurations."""

    # TTL configurations (in seconds)
    TTL_RECOMMENDATIONS = 3600  # 1 hour
    TTL_CLOTHING_ITEMS = 1800  # 30 minutes
    TTL_OUTFITS = 1800  # 30 minutes
    TTL_VISION_ANALYSIS = 604800  # 7 days
    TTL_USER_ANALYSES = 1800  # 30 minutes

    # Key prefixes for organization
    PREFIX_RECOMMENDATIONS = "recommendations"
    PREFIX_CLOTHING_ITEMS = "clothing_items"
    PREFIX_OUTFITS = "outfits"
    PREFIX_VISION_ANALYSIS = "vision_analysis"

    _client: Optional[redis.Redis] = None
    _unavailable: bool = False

    @classmethod
    def get_client(cls) -> Optional[redis.Redis]:
        """Get or create Redis client (singleton pattern)."""
        if cls._unavailable:
            return None
        if cls._client is None:
            try:
                cls._client = redis.Redis(
                    host=settings.redis_host,
                    port=settings.redis_port,
                    db=settings.redis_db,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_keepalive=True,
                    health_check_interval=30,
                )
                # Test connection
                cls._client.ping()
                logger.info("Redis connection established")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}. Cache operations will be skipped.")
                cls._client = None
                cls._unavailable = True
        return cls._client

    @classmethod
    def get_cache(cls, key: str) -> Optional[Any]:
        """Retrieve value from cache."""
        try:
            client = cls.get_client()
            if not client:
                return None

            value = client.get(key)
            if value:
                logger.debug(f"Cache hit: {key}")
                return json.loads(value)
            logger.debug(f"Cache miss: {key}")
            return None
        except Exception as e:
            logger.warning(f"Cache get failed for {key}: {e}")
            return None

    @classmethod
    def set_cache(cls, key: str, value: Any, ttl: int = 3600) -> bool:
        """Store value in cache with TTL."""
        try:
            client = cls.get_client()
            if not client:
                return False

            serialized = json.dumps(value)
            client.setex(key, ttl, serialized)
            logger.debug(f"Cache set: {key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.warning(f"Cache set failed for {key}: {e}")
            return False

    @classmethod
    def delete_cache(cls, key: str) -> bool:
        """Remove key from cache."""
        try:
            client = cls.get_client()
            if not client:
                return False

            result = client.delete(key)
            logger.debug(f"Cache deleted: {key}")
            return bool(result)
        except Exception as e:
            logger.warning(f"Cache delete failed for {key}: {e}")
            return False

    @classmethod
    def invalidate_pattern(cls, pattern: str) -> int:
        """Remove all keys matching pattern."""
        try:
            client = cls.get_client()
            if not client:
                return 0

            keys = client.keys(pattern)
            if keys:
                deleted = client.delete(*keys)
                logger.debug(f"Cache invalidated pattern '{pattern}': {deleted} keys deleted")
                return deleted
            return 0
        except Exception as e:
            logger.warning(f"Cache invalidate pattern failed for {pattern}: {e}")
            return 0

    # Recommendation cache helpers
    @classmethod
    def get_recommendations(cls, user_id: int, reference_image_id: int) -> Optional[Any]:
        """Retrieve cached recommendations."""
        key = f"{cls.PREFIX_RECOMMENDATIONS}:user:{user_id}:image:{reference_image_id}"
        return cls.get_cache(key)

    @classmethod
    def set_recommendations(cls, user_id: int, reference_image_id: int, recommendations: Any) -> bool:
        """Cache recommendations."""
        key = f"{cls.PREFIX_RECOMMENDATIONS}:user:{user_id}:image:{reference_image_id}"
        return cls.set_cache(key, recommendations, cls.TTL_RECOMMENDATIONS)

    @classmethod
    def invalidate_user_recommendations(cls, user_id: int) -> int:
        """Invalidate all recommendations for a user."""
        pattern = f"{cls.PREFIX_RECOMMENDATIONS}:user:{user_id}:*"
        return cls.invalidate_pattern(pattern)

    # Clothing items cache helpers
    @classmethod
    def get_clothing_items(cls, user_id: int, limit: int, offset: int) -> Optional[Any]:
        """Retrieve cached clothing items list."""
        key = f"{cls.PREFIX_CLOTHING_ITEMS}:user:{user_id}:limit:{limit}:offset:{offset}"
        return cls.get_cache(key)

    @classmethod
    def set_clothing_items(cls, user_id: int, limit: int, offset: int, items: Any) -> bool:
        """Cache clothing items list."""
        key = f"{cls.PREFIX_CLOTHING_ITEMS}:user:{user_id}:limit:{limit}:offset:{offset}"
        return cls.set_cache(key, items, cls.TTL_CLOTHING_ITEMS)

    @classmethod
    def invalidate_user_clothing_items(cls, user_id: int) -> int:
        """Invalidate all clothing items cache for a user."""
        pattern = f"{cls.PREFIX_CLOTHING_ITEMS}:user:{user_id}:*"
        count = cls.invalidate_pattern(pattern)
        # Also invalidate recommendations since new items affect them
        count += cls.invalidate_user_recommendations(user_id)
        return count

    # Outfits cache helpers
    @classmethod
    def get_outfits(cls, user_id: int, limit: int, offset: int) -> Optional[Any]:
        """Retrieve cached outfits list."""
        key = f"{cls.PREFIX_OUTFITS}:user:{user_id}:limit:{limit}:offset:{offset}"
        return cls.get_cache(key)

    @classmethod
    def set_outfits(cls, user_id: int, limit: int, offset: int, outfits: Any) -> bool:
        """Cache outfits list."""
        key = f"{cls.PREFIX_OUTFITS}:user:{user_id}:limit:{limit}:offset:{offset}"
        return cls.set_cache(key, outfits, cls.TTL_OUTFITS)

    @classmethod
    def invalidate_user_outfits(cls, user_id: int) -> int:
        """Invalidate all outfits cache for a user."""
        pattern = f"{cls.PREFIX_OUTFITS}:user:{user_id}:*"
        return cls.invalidate_pattern(pattern)

    # Vision analysis cache helpers
    @classmethod
    def get_vision_analysis(cls, image_id: int) -> Optional[Any]:
        """Retrieve cached vision analysis."""
        key = f"{cls.PREFIX_VISION_ANALYSIS}:image:{image_id}"
        return cls.get_cache(key)

    @classmethod
    def set_vision_analysis(cls, image_id: int, analysis: Any) -> bool:
        """Cache vision analysis (long TTL - immutable)."""
        key = f"{cls.PREFIX_VISION_ANALYSIS}:image:{image_id}"
        return cls.set_cache(key, analysis, cls.TTL_VISION_ANALYSIS)

    @classmethod
    def get_user_analyses(cls, user_id: int, limit: int, offset: int) -> Optional[Any]:
        """Retrieve cached user vision analyses list."""
        key = f"{cls.PREFIX_VISION_ANALYSIS}:user:{user_id}:limit:{limit}:offset:{offset}"
        return cls.get_cache(key)

    @classmethod
    def set_user_analyses(cls, user_id: int, limit: int, offset: int, analyses: Any) -> bool:
        """Cache user vision analyses list."""
        key = f"{cls.PREFIX_VISION_ANALYSIS}:user:{user_id}:limit:{limit}:offset:{offset}"
        return cls.set_cache(key, analyses, cls.TTL_USER_ANALYSES)

    @classmethod
    def invalidate_user_analyses(cls, user_id: int) -> int:
        """Invalidate all analyses cache for a user."""
        pattern = f"{cls.PREFIX_VISION_ANALYSIS}:user:{user_id}:*"
        return cls.invalidate_pattern(pattern)

    @classmethod
    def clear_all(cls) -> bool:
        """Clear all cache (use with caution)."""
        try:
            client = cls.get_client()
            if not client:
                return False

            client.flushdb()
            logger.info("Cache cleared")
            return True
        except Exception as e:
            logger.warning(f"Cache clear failed: {e}")
            return False
