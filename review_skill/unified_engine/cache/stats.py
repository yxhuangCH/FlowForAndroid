"""
Cache Statistics - 缓存统计

提供缓存性能监控和统计功能。
"""

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class CacheMetrics:
    """缓存指标"""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_time_ms: float = 0.0

    @property
    def total_requests(self) -> int:
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.hits / self.total_requests

    def record_hit(self, elapsed_ms: float = 0):
        self.hits += 1
        self.total_time_ms += elapsed_ms

    def record_miss(self, elapsed_ms: float = 0):
        self.misses += 1
        self.total_time_ms += elapsed_ms

    def record_eviction(self):
        self.evictions += 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "hit_rate": round(self.hit_rate, 4),
            "avg_time_ms": round(self.total_time_ms / max(self.total_requests, 1), 4),
        }


class CacheStats:
    """
    缓存统计器

    收集各级缓存的命中/未命中统计，支持按数据类型细分。

    Example:
        ```python
        stats = CacheStats()

        # 记录命中
        stats.record_hit("memory", "ast")
        stats.record_hit("disk", "rule_result")

        # 记录未命中
        stats.record_miss("ast")

        # 获取统计
        print(stats.get_summary())
        ```
    """

    def __init__(self):
        # 按层级统计
        self._memory_metrics: Dict[str, CacheMetrics] = defaultdict(CacheMetrics)
        self._disk_metrics: Dict[str, CacheMetrics] = defaultdict(CacheMetrics)

        # 总体统计
        self._overall = CacheMetrics()

        # 锁
        self._lock = threading.Lock()

    def record_hit(self, level: str, data_type: str, elapsed_ms: float = 0):
        """
        记录缓存命中

        Args:
            level: 缓存层级 ('memory', 'disk')
            data_type: 数据类型 ('ast', 'rule_result', etc.)
            elapsed_ms: 耗时（毫秒）
        """
        with self._lock:
            if level == "memory":
                self._memory_metrics[data_type].record_hit(elapsed_ms)
            elif level == "disk":
                self._disk_metrics[data_type].record_hit(elapsed_ms)

            self._overall.record_hit(elapsed_ms)

    def record_miss(self, data_type: str, elapsed_ms: float = 0):
        """
        记录缓存未命中

        Args:
            data_type: 数据类型
            elapsed_ms: 耗时（毫秒）
        """
        with self._lock:
            self._overall.record_miss(elapsed_ms)

    def record_eviction(self, level: str, data_type: str):
        """
        记录缓存淘汰

        Args:
            level: 缓存层级
            data_type: 数据类型
        """
        with self._lock:
            if level == "memory":
                self._memory_metrics[data_type].record_eviction()
            elif level == "disk":
                self._disk_metrics[data_type].record_eviction()

    def get_memory_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取内存缓存统计"""
        with self._lock:
            return {k: v.to_dict() for k, v in self._memory_metrics.items()}

    def get_disk_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取磁盘缓存统计"""
        with self._lock:
            return {k: v.to_dict() for k, v in self._disk_metrics.items()}

    def get_summary(self) -> Dict[str, Any]:
        """
        获取统计摘要

        Returns:
            统计摘要字典
        """
        with self._lock:
            memory_hits = sum(m.hits for m in self._memory_metrics.values())
            memory_misses = sum(m.misses for m in self._memory_metrics.values())
            disk_hits = sum(m.hits for m in self._disk_metrics.values())
            disk_misses = sum(m.misses for m in self._disk_metrics.values())

            total_hits = memory_hits + disk_hits
            total_misses = memory_misses + disk_misses
            total = total_hits + total_misses

            return {
                "total_requests": total,
                "total_hits": total_hits,
                "total_misses": total_misses,
                "hit_rate": round(total_hits / total, 4) if total > 0 else 0.0,
                "memory_hits": memory_hits,
                "disk_hits": disk_hits,
                "memory_hit_rate": (
                    round(memory_hits / (memory_hits + memory_misses), 4)
                    if (memory_hits + memory_misses) > 0
                    else 0.0
                ),
                "disk_hit_rate": (
                    round(disk_hits / (disk_hits + disk_misses), 4)
                    if (disk_hits + disk_misses) > 0
                    else 0.0
                ),
            }

    def reset(self):
        """重置统计"""
        with self._lock:
            self._memory_metrics.clear()
            self._disk_metrics.clear()
            self._overall = CacheMetrics()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "summary": self.get_summary(),
            "memory": self.get_memory_stats(),
            "disk": self.get_disk_stats(),
        }
