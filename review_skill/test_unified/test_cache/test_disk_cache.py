"""Tests for DiskCache (L2 cache)"""

import pytest
import json
from unified_engine.cache.disk_cache import DiskCache


class TestDiskCache:
    """Tests for persistent disk cache"""

    def test_basic_get_put(self, tmp_path):
        """Test basic get/put operations"""
        cache = DiskCache(cache_dir=str(tmp_path / "cache"))

        cache.put("key1", {"data": "value1"})
        result = cache.get("key1")

        assert result == {"data": "value1"}

    def test_get_nonexistent(self, tmp_path):
        """Test get returns None for non-existent key"""
        cache = DiskCache(cache_dir=str(tmp_path / "cache"))
        assert cache.get("nonexistent") is None

    def test_persistence(self, tmp_path):
        """Test data persists across cache instances"""
        cache_dir = str(tmp_path / "cache")

        # First instance
        cache1 = DiskCache(cache_dir=cache_dir)
        cache1.put("key1", {"test": "data"})

        # Second instance (same directory)
        cache2 = DiskCache(cache_dir=cache_dir)
        result = cache2.get("key1")

        assert result == {"test": "data"}

    def test_clear(self, tmp_path):
        """Test clear operation"""
        cache = DiskCache(cache_dir=str(tmp_path / "cache"))

        cache.put("key1", {"data": 1})
        cache.put("key2", {"data": 2})

        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_ttl_expiration(self, tmp_path):
        """Test TTL expiration"""
        cache = DiskCache(
            cache_dir=str(tmp_path / "cache"),
            default_ttl_seconds=0.01
        )

        cache.put("key1", {"data": "value1"})

        # Wait for TTL to expire
        import time
        time.sleep(0.02)

        assert cache.get("key1") is None

    def test_stats(self, tmp_path):
        """Test cache statistics"""
        cache = DiskCache(cache_dir=str(tmp_path / "cache"))

        # Miss
        cache.get("key1")
        assert cache.stats.misses == 1

        # Put and hit
        cache.put("key1", {"data": 1})
        cache.get("key1")
        assert cache.stats.hits == 1

    def test_contains(self, tmp_path):
        """Test __contains__ method"""
        cache = DiskCache(cache_dir=str(tmp_path / "cache"))

        cache.put("key1", {"data": 1})

        assert "key1" in cache
        assert "key2" not in cache

    def test_invalid_json(self, tmp_path):
        """Test handling of corrupted cache files"""
        cache_dir = tmp_path / "cache"
        cache = DiskCache(cache_dir=str(cache_dir))

        cache.put("key1", {"data": 1})

        # Corrupt the file
        cache_file = cache_dir / "key1.json"
        cache_file.write_text("invalid json")

        # Should return None for corrupted file
        assert cache.get("key1") is None

    def test_complex_data(self, tmp_path):
        """Test caching complex nested data"""
        cache = DiskCache(cache_dir=str(tmp_path / "cache"))

        complex_data = {
            "ast": {
                "type": "class",
                "name": "Test",
                "methods": [
                    {"name": "foo", "return_type": "void"},
                    {"name": "bar", "return_type": "int"}
                ]
            },
            "metadata": {
                "version": 1,
                "timestamp": 1234567890
            }
        }

        cache.put("complex", complex_data)
        result = cache.get("complex")

        assert result == complex_data
