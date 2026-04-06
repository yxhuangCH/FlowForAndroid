"""Tests for MemoryCache (L1 cache)"""

import pytest
from unified_engine.cache.memory_cache import MemoryCache


class TestMemoryCache:
    """Tests for in-memory LRU cache"""

    def test_basic_get_put(self):
        """Test basic get/put operations"""
        cache = MemoryCache(maxsize=10)

        cache.put("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_nonexistent(self):
        """Test get returns None for non-existent key"""
        cache = MemoryCache(maxsize=10)
        assert cache.get("nonexistent") is None

    def test_lru_eviction(self):
        """Test LRU eviction when cache is full"""
        cache = MemoryCache(maxsize=3)

        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")

        # Access key1 to make it recently used
        cache.get("key1")

        # Add new item, should evict key2 (least recently used)
        cache.put("key4", "value4")

        assert cache.get("key1") == "value1"  # Still there
        assert cache.get("key2") is None  # Evicted
        assert cache.get("key3") == "value3"  # Still there
        assert cache.get("key4") == "value4"  # New item

    def test_ttl_expiration(self):
        """Test TTL expiration"""
        cache = MemoryCache(maxsize=10, ttl_seconds=0.01)

        cache.put("key1", "value1")
        assert cache.get("key1") == "value1"

        # Wait for TTL to expire
        import time
        time.sleep(0.02)

        assert cache.get("key1") is None

    def test_clear(self):
        """Test clear operation"""
        cache = MemoryCache(maxsize=10)

        cache.put("key1", "value1")
        cache.put("key2", "value2")

        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_stats(self):
        """Test cache statistics"""
        cache = MemoryCache(maxsize=10)

        # Miss
        cache.get("key1")
        assert cache.stats.misses == 1

        # Put and hit
        cache.put("key1", "value1")
        cache.get("key1")
        assert cache.stats.hits == 1

    def test_contains(self):
        """Test __contains__ method"""
        cache = MemoryCache(maxsize=10)

        cache.put("key1", "value1")

        assert "key1" in cache
        assert "key2" not in cache

    def test_size_limit(self):
        """Test cache respects size limit"""
        cache = MemoryCache(maxsize=5)

        for i in range(10):
            cache.put(f"key{i}", f"value{i}")

        # Only 5 items should be in cache
        count = sum(1 for i in range(10) if cache.get(f"key{i}") is not None)
        assert count == 5

    def test_update_existing_key(self):
        """Test updating existing key"""
        cache = MemoryCache(maxsize=10)

        cache.put("key1", "value1")
        cache.put("key1", "value2")

        assert cache.get("key1") == "value2"
