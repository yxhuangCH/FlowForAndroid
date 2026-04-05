"""
Memory Cache - L1 内存缓存

基于 LRU 策略的进程内缓存，提供最快的访问速度。

特性:
- 线程安全 (threading.RLock)
- LRU 淘汰策略
- TTL 过期机制
- 大小限制
"""

import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, Generic, Optional, TypeVar

T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    """缓存条目"""

    value: T
    created_at: datetime
    expires_at: Optional[datetime] = None
    access_count: int = 0

    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at


class MemoryCache:
    """
    L1 内存缓存 - 基于 LRU 策略

    使用 OrderedDict 实现 O(1) 的 LRU 操作。
    支持 TTL 过期检查和线程安全访问。

    Example:
        ```python
        cache = MemoryCache(max_size=1000, ttl_seconds=3600)

        # 存储
        cache.put("key", value, ttl_seconds=1800)  # 自定义 TTL

        # 获取
        value = cache.get("key")

        # 批量操作
        cache.put_batch({"k1": v1, "k2": v2})
        values = cache.get_batch(["k1", "k2"])
        ```
    """

    def __init__(
        self,
        max_size: int = 1000,
        ttl_seconds: int = 3600,
        default_ttl_seconds: Optional[int] = None,
    ):
        """
        初始化内存缓存

        Args:
            max_size: 最大条目数，超过将触发 LRU 淘汰
            ttl_seconds: 默认 TTL（秒）
            default_ttl_seconds: 默认 TTL 的别名，与 ttl_seconds 相同
        """
        self.max_size = max_size
        self.default_ttl = timedelta(
            seconds=default_ttl_seconds if default_ttl_seconds else ttl_seconds
        )

        # 使用 OrderedDict 实现 LRU: 最近访问的放到末尾
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()

        # 统计
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值

        如果 key 存在，会将其移动到 LRU 队列末尾（标记为最近使用）。
        如果 key 不存在或已过期，返回 None。

        Args:
            key: 缓存键

        Returns:
            缓存值或 None
        """
        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._misses += 1
                return None

            if entry.is_expired():
                # 过期，删除
                del self._cache[key]
                self._misses += 1
                return None

            # 移动到末尾（最近使用）
            self._cache.move_to_end(key)
            entry.access_count += 1

            self._hits += 1
            return entry.value

    def put(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """
        存储缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl_seconds: 自定义 TTL（秒），None 使用默认值
        """
        with self._lock:
            # 计算过期时间
            expires_at = None
            if ttl_seconds is not None and ttl_seconds > 0:
                expires_at = datetime.now() + timedelta(seconds=ttl_seconds)
            elif self.default_ttl.total_seconds() > 0:
                expires_at = datetime.now() + self.default_ttl

            # 创建条目
            entry = CacheEntry(
                value=value,
                created_at=datetime.now(),
                expires_at=expires_at,
            )

            # 如果 key 已存在，先删除（后面会重新添加，确保在 LRU 队列末尾）
            if key in self._cache:
                del self._cache[key]

            # 检查是否需要淘汰
            self._evict_if_needed()

            # 添加到缓存
            self._cache[key] = entry

    def put_batch(self, items: Dict[str, Any], ttl_seconds: Optional[int] = None) -> None:
        """
        批量存储

        Args:
            items: 键值对字典
            ttl_seconds: 自定义 TTL（秒）
        """
        for key, value in items.items():
            self.put(key, value, ttl_seconds)

    def get_batch(self, keys: list) -> Dict[str, Any]:
        """
        批量获取

        Args:
            keys: 键列表

        Returns:
            存在的键值对字典
        """
        result = {}
        for key in keys:
            value = self.get(key)
            if value is not None:
                result[key] = value
        return result

    def delete(self, key: str) -> bool:
        """
        删除缓存

        Args:
            key: 缓存键

        Returns:
            True 如果 key 存在并被删除
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def delete_batch(self, keys: list) -> int:
        """
        批量删除

        Args:
            keys: 键列表

        Returns:
            实际删除的数量
        """
        count = 0
        for key in keys:
            if self.delete(key):
                count += 1
        return count

    def clear(self) -> None:
        """清空所有缓存"""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
            self._evictions = 0

    def contains(self, key: str) -> bool:
        """
        检查 key 是否存在（不过期检查）

        Args:
            key: 缓存键

        Returns:
            True 如果 key 存在
        """
        with self._lock:
            return key in self._cache

    def keys(self) -> list:
        """获取所有缓存键"""
        with self._lock:
            return list(self._cache.keys())

    def size(self) -> int:
        """获取当前缓存条目数"""
        with self._lock:
            return len(self._cache)

    def _evict_if_needed(self) -> None:
        """如果需要，淘汰最旧的条目"""
        while len(self._cache) >= self.max_size:
            # 淘汰最旧的（OrderedDict 的第一个元素）
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
            self._evictions += 1

    def cleanup_expired(self) -> int:
        """
        清理过期条目

        Returns:
            清理的条目数
        """
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items() if entry.is_expired()
            ]
            for key in expired_keys:
                del self._cache[key]
            return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计

        Returns:
            统计信息字典
        """
        with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0.0

            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(hit_rate, 4),
                "evictions": self._evictions,
                "default_ttl_seconds": self.default_ttl.total_seconds(),
            }

    def __len__(self) -> int:
        """返回缓存条目数"""
        return self.size()

    def __contains__(self, key: str) -> bool:
        """检查 key 是否存在"""
        return self.contains(key)
