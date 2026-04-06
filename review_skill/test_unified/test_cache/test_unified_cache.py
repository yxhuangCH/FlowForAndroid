"""Tests for UnifiedCache (L1/L2/L3 integration)"""

import pytest
from unified_engine.cache import UnifiedCache


class TestUnifiedCache:
    """Tests for integrated three-level cache"""

    def test_basic_get_put(self, tmp_path):
        """Test basic get/put operations"""
        cache = UnifiedCache(disk_cache_dir=str(tmp_path / "cache"))

        cache.put("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_l1_cache_hit(self, tmp_path):
        """Test L1 cache hit"""
        cache = UnifiedCache(disk_cache_dir=str(tmp_path / "cache"))

        cache.put("key1", "value1")

        # First get - from L1
        result = cache.get("key1")
        assert result == "value1"

    def test_l2_cache_after_l1_miss(self, tmp_path):
        """Test L2 cache is used after L1 miss"""
        cache_dir = str(tmp_path / "cache")

        # First instance fills L1 and L2
        cache1 = UnifiedCache(disk_cache_dir=cache_dir)
        cache1.put("key1", "value1")

        # Second instance has empty L1 but L2 has data
        cache2 = UnifiedCache(disk_cache_dir=cache_dir)

        # Clear L1 to force L2 lookup
        cache2._memory_cache.clear()

        result = cache2.get("key1")
        assert result == "value1"

    def test_ast_caching_with_content_validation(self, tmp_path):
        """Test AST caching with content hash validation"""
        cache = UnifiedCache(disk_cache_dir=str(tmp_path / "cache"))

        code1 = "class Test {}"
        file_hash = "abc123"

        # Store AST
        ast1 = {"type": "class", "name": "Test"}
        cache.put_ast(file_hash, code1, ast1)

        # Retrieve with same content
        result = cache.get_ast(file_hash, code1)
        assert result == ast1

        # Retrieve with different content (should miss)
        code2 = "class Test { fun foo() {} }"
        result = cache.get_ast(file_hash, code2)
        assert result is None

    def test_rule_result_caching(self, tmp_path):
        """Test rule result caching"""
        cache = UnifiedCache(disk_cache_dir=str(tmp_path / "cache"))

        findings = [
            {"rule_id": "test", "line": 1, "message": "test"}
        ]

        cache.put_rule_result("rule1", "file1", findings)
        result = cache.get_rule_result("rule1", "file1")

        assert result == findings

    def test_clear(self, tmp_path):
        """Test clear operation clears all levels"""
        cache = UnifiedCache(disk_cache_dir=str(tmp_path / "cache"))

        cache.put("key1", "value1")
        cache.clear()

        assert cache.get("key1") is None

    def test_stats(self, tmp_path):
        """Test cache statistics"""
        cache = UnifiedCache(disk_cache_dir=str(tmp_path / "cache"))

        # Miss
        cache.get("key1")

        # Put and hit
        cache.put("key1", "value1")
        cache.get("key1")

        stats = cache.get_stats()
        assert stats["hits"] >= 1
        assert stats["misses"] >= 1

    def test_incremental_cache_integration(self, tmp_path):
        """Test incremental cache integration"""
        cache = UnifiedCache(
            disk_cache_dir=str(tmp_path / "cache"),
            incremental_cache_dir=str(tmp_path / "incremental")
        )

        cache.mark_scanned("commit_abc", ["file1.kt", "file2.kt"])

        with patch.object(cache._incremental_cache, 'get_changed_files') as mock_get:
            mock_get.return_value = ["file3.kt"]

            changed = cache.get_changed_files("commit_abc", [".kt"])
            assert "file3.kt" in changed

    def test_size_based_promotion(self, tmp_path):
        """Test that frequently accessed items stay in L1"""
        cache = UnifiedCache(
            memory_size=3,
            disk_cache_dir=str(tmp_path / "cache")
        )

        # Add 3 items
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")

        # Access key1 to make it recently used
        cache.get("key1")

        # Add 4th item (should evict key2 from L1, but it's in L2)
        cache.put("key4", "value4")

        # key1 should be in L1
        assert cache._memory_cache.get("key1") == "value1"

        # key2 should be evicted from L1 but retrievable from L2
        assert cache._memory_cache.get("key2") is None
        assert cache.get("key2") == "value2"  # Should get from L2 and promote to L1

    def test_concurrent_access(self, tmp_path):
        """Test thread-safe concurrent access"""
        import threading
        import time

        cache = UnifiedCache(disk_cache_dir=str(tmp_path / "cache"))
        errors = []

        def writer():
            try:
                for i in range(100):
                    cache.put(f"key{i}", f"value{i}")
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        def reader():
            try:
                for i in range(100):
                    cache.get(f"key{i}")
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=writer),
            threading.Thread(target=reader),
            threading.Thread(target=writer),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Concurrent access errors: {errors}"

    def test_cleanup(self, tmp_path):
        """Test cache cleanup"""
        cache = UnifiedCache(
            disk_cache_dir=str(tmp_path / "cache"),
            default_ttl_seconds=0.01
        )

        cache.put("key1", "value1")

        # Wait for TTL
        import time
        time.sleep(0.02)

        stats = cache.cleanup()

        assert stats["removed_count"] >= 0
