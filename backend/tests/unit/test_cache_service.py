"""Unit tests for Redis caching service."""
import json
from unittest.mock import MagicMock, patch

import pytest

from services.cache_service import CacheService


class TestCacheService:
    """Tests for CacheService caching operations."""

    def test_cache_service_ttl_constants(self):
        """Test TTL configuration constants."""
        assert CacheService.TTL_RECOMMENDATIONS == 3600  # 1 hour
        assert CacheService.TTL_CLOTHING_ITEMS == 1800  # 30 minutes
        assert CacheService.TTL_OUTFITS == 1800  # 30 minutes
        assert CacheService.TTL_VISION_ANALYSIS == 604800  # 7 days
        assert CacheService.TTL_USER_ANALYSES == 1800  # 30 minutes

    def test_cache_key_prefixes(self):
        """Test key prefix constants."""
        assert CacheService.PREFIX_RECOMMENDATIONS == "recommendations"
        assert CacheService.PREFIX_CLOTHING_ITEMS == "clothing_items"
        assert CacheService.PREFIX_OUTFITS == "outfits"
        assert CacheService.PREFIX_VISION_ANALYSIS == "vision_analysis"

    @patch("services.cache_service.redis.Redis")
    def test_get_client_creates_singleton(self, mock_redis_class):
        """Test that get_client creates a Redis singleton."""
        # Reset singleton
        CacheService._client = None

        # Create mock client
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_redis_class.return_value = mock_client

        # First call should create client
        client1 = CacheService.get_client()
        assert client1 is not None

        # Second call should return same client
        client2 = CacheService.get_client()
        assert client1 is client2

    @patch("services.cache_service.redis.Redis")
    def test_get_client_handles_connection_failure(self, mock_redis_class):
        """Test that get_client handles Redis connection failures gracefully."""
        # Reset singleton
        CacheService._client = None

        # Make Redis raise exception
        mock_redis_class.side_effect = Exception("Connection failed")

        # Should return None on failure
        client = CacheService.get_client()
        assert client is None

    @patch.object(CacheService, "get_client")
    def test_get_cache_with_valid_key(self, mock_get_client):
        """Test retrieving value from cache."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        test_data = {"key": "value"}
        mock_client.get.return_value = json.dumps(test_data)

        result = CacheService.get_cache("test_key")

        assert result == test_data
        mock_client.get.assert_called_once_with("test_key")

    @patch.object(CacheService, "get_client")
    def test_get_cache_miss(self, mock_get_client):
        """Test cache miss returns None."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get.return_value = None

        result = CacheService.get_cache("nonexistent_key")

        assert result is None

    @patch.object(CacheService, "get_client")
    def test_get_cache_no_client(self, mock_get_client):
        """Test get_cache returns None when Redis unavailable."""
        mock_get_client.return_value = None

        result = CacheService.get_cache("test_key")

        assert result is None

    @patch.object(CacheService, "get_client")
    def test_set_cache(self, mock_get_client):
        """Test storing value in cache."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        test_data = {"key": "value"}
        result = CacheService.set_cache("test_key", test_data, ttl=3600)

        assert result is True
        mock_client.setex.assert_called_once()
        call_args = mock_client.setex.call_args
        assert call_args[0] == ("test_key", 3600, json.dumps(test_data))

    @patch.object(CacheService, "get_client")
    def test_set_cache_no_client(self, mock_get_client):
        """Test set_cache returns False when Redis unavailable."""
        mock_get_client.return_value = None

        result = CacheService.set_cache("test_key", {"data": "value"})

        assert result is False

    @patch.object(CacheService, "get_client")
    def test_delete_cache(self, mock_get_client):
        """Test deleting key from cache."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.delete.return_value = 1

        result = CacheService.delete_cache("test_key")

        assert result is True
        mock_client.delete.assert_called_once_with("test_key")

    @patch.object(CacheService, "get_client")
    def test_delete_cache_key_not_found(self, mock_get_client):
        """Test deleting non-existent key."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.delete.return_value = 0

        result = CacheService.delete_cache("nonexistent_key")

        assert result is False

    @patch.object(CacheService, "get_client")
    def test_invalidate_pattern(self, mock_get_client):
        """Test invalidating cache by pattern."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.keys.return_value = ["key1", "key2", "key3"]
        mock_client.delete.return_value = 3

        result = CacheService.invalidate_pattern("prefix:*")

        assert result == 3
        mock_client.keys.assert_called_once_with("prefix:*")
        mock_client.delete.assert_called_once()

    @patch.object(CacheService, "get_client")
    def test_invalidate_pattern_no_matches(self, mock_get_client):
        """Test invalidating pattern with no matches."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.keys.return_value = []

        result = CacheService.invalidate_pattern("nomatch:*")

        assert result == 0
        mock_client.delete.assert_not_called()

    @patch.object(CacheService, "get_cache")
    @patch.object(CacheService, "set_cache")
    def test_get_recommendations(self, mock_set, mock_get):
        """Test recommendation caching."""
        test_recs = [{"item": "test"}]
        mock_get.return_value = test_recs

        result = CacheService.get_recommendations(user_id=1, reference_image_id=100)

        assert result == test_recs
        mock_get.assert_called_once_with("recommendations:user:1:image:100")

    @patch.object(CacheService, "get_cache")
    @patch.object(CacheService, "set_cache")
    def test_set_recommendations(self, mock_set, mock_get):
        """Test setting recommendation cache."""
        test_recs = [{"item": "test"}]
        mock_set.return_value = True

        result = CacheService.set_recommendations(
            user_id=1, reference_image_id=100, recommendations=test_recs
        )

        assert result is True
        mock_set.assert_called_once()
        call_args = mock_set.call_args
        assert call_args[0] == ("recommendations:user:1:image:100", test_recs, 3600)

    @patch.object(CacheService, "invalidate_pattern")
    def test_invalidate_user_recommendations(self, mock_invalidate):
        """Test invalidating user recommendations."""
        mock_invalidate.return_value = 5

        result = CacheService.invalidate_user_recommendations(user_id=1)

        assert result == 5
        mock_invalidate.assert_called_once_with("recommendations:user:1:*")

    @patch.object(CacheService, "get_cache")
    @patch.object(CacheService, "set_cache")
    def test_get_clothing_items(self, mock_set, mock_get):
        """Test clothing items caching."""
        test_items = {"items": [], "total": 0}
        mock_get.return_value = test_items

        result = CacheService.get_clothing_items(
            user_id=1, limit=50, offset=0
        )

        assert result == test_items
        mock_get.assert_called_once_with("clothing_items:user:1:limit:50:offset:0")

    @patch.object(CacheService, "invalidate_pattern")
    @patch.object(CacheService, "invalidate_user_recommendations")
    def test_invalidate_user_clothing_items(self, mock_invalidate_recs, mock_invalidate):
        """Test invalidating clothing items also invalidates recommendations."""
        mock_invalidate.return_value = 3
        mock_invalidate_recs.return_value = 2

        result = CacheService.invalidate_user_clothing_items(user_id=1)

        # Should invalidate both clothing items and recommendations
        assert result == 5
        mock_invalidate.assert_called_once_with("clothing_items:user:1:*")
        mock_invalidate_recs.assert_called_once_with(1)

    @patch.object(CacheService, "get_cache")
    @patch.object(CacheService, "set_cache")
    def test_get_outfits(self, mock_set, mock_get):
        """Test outfits caching."""
        test_outfits = {"outfits": [], "total": 0}
        mock_get.return_value = test_outfits

        result = CacheService.get_outfits(user_id=1, limit=50, offset=0)

        assert result == test_outfits
        mock_get.assert_called_once_with("outfits:user:1:limit:50:offset:0")

    @patch.object(CacheService, "set_cache")
    def test_set_outfits(self, mock_set):
        """Test setting outfits cache."""
        test_outfits = {"outfits": [], "total": 0}
        mock_set.return_value = True

        result = CacheService.set_outfits(
            user_id=1, limit=50, offset=0, outfits=test_outfits
        )

        assert result is True
        mock_set.assert_called_once()
        call_args = mock_set.call_args
        assert call_args[0] == ("outfits:user:1:limit:50:offset:0", test_outfits, 1800)

    @patch.object(CacheService, "invalidate_pattern")
    def test_invalidate_user_outfits(self, mock_invalidate):
        """Test invalidating user outfits."""
        mock_invalidate.return_value = 3

        result = CacheService.invalidate_user_outfits(user_id=1)

        assert result == 3
        mock_invalidate.assert_called_once_with("outfits:user:1:*")

    @patch.object(CacheService, "get_cache")
    @patch.object(CacheService, "set_cache")
    def test_get_vision_analysis(self, mock_set, mock_get):
        """Test vision analysis caching."""
        test_analysis = {"clothing_type": "shirt"}
        mock_get.return_value = test_analysis

        result = CacheService.get_vision_analysis(image_id=100)

        assert result == test_analysis
        mock_get.assert_called_once_with("vision_analysis:image:100")

    @patch.object(CacheService, "set_cache")
    def test_set_vision_analysis(self, mock_set):
        """Test setting vision analysis cache with long TTL."""
        test_analysis = {"clothing_type": "shirt"}
        mock_set.return_value = True

        result = CacheService.set_vision_analysis(
            image_id=100, analysis=test_analysis
        )

        assert result is True
        mock_set.assert_called_once()
        call_args = mock_set.call_args
        # Should use 7-day TTL
        assert call_args[0] == ("vision_analysis:image:100", test_analysis, 604800)

    @patch.object(CacheService, "get_cache")
    @patch.object(CacheService, "set_cache")
    def test_get_user_analyses(self, mock_set, mock_get):
        """Test user analyses caching."""
        test_analyses = {"analyses": [], "total": 0}
        mock_get.return_value = test_analyses

        result = CacheService.get_user_analyses(user_id=1, limit=50, offset=0)

        assert result == test_analyses
        mock_get.assert_called_once_with("vision_analysis:user:1:limit:50:offset:0")

    @patch.object(CacheService, "invalidate_pattern")
    def test_invalidate_user_analyses(self, mock_invalidate):
        """Test invalidating user analyses."""
        mock_invalidate.return_value = 4

        result = CacheService.invalidate_user_analyses(user_id=1)

        assert result == 4
        mock_invalidate.assert_called_once_with("vision_analysis:user:1:*")

    @patch.object(CacheService, "get_client")
    def test_clear_all(self, mock_get_client):
        """Test clearing all cache."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        result = CacheService.clear_all()

        assert result is True
        mock_client.flushdb.assert_called_once()

    @patch.object(CacheService, "get_client")
    def test_clear_all_no_client(self, mock_get_client):
        """Test clear_all returns False when Redis unavailable."""
        mock_get_client.return_value = None

        result = CacheService.clear_all()

        assert result is False

    @patch.object(CacheService, "get_client")
    def test_cache_service_with_exception(self, mock_get_client):
        """Test cache service handles exceptions gracefully."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get.side_effect = Exception("Redis error")

        # Should return None on exception, not crash
        result = CacheService.get_cache("test_key")
        assert result is None
