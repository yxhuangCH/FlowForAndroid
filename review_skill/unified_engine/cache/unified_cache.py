"""
Unified Cache - 统一缓存管理器

整合 L1/L2/L3 三级缓存，提供统一的缓存访问接口。
自动处理缓存层级间的数据流动。

Features:
- 三级缓存架构 (Memory -> Disk -> Incremental)
- 自动数据提升 (promotion)
- 统一的缓存键管理
- 完整的统计监控
"""

import hashlib
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ast_engine.nodes import ASTNode
    from unified_engine.interfaces import Finding

from .memory_cache import MemoryCache
from .disk_cache import DiskCache
from .incremental_cache import IncrementalCache
from .stats import CacheStats
from .consistency import CacheConsistencyManager


class UnifiedCache:
    """
    统一缓存管理器

    整合内存缓存、磁盘缓存和增量缓存，为规则引擎提供统一的缓存接口。

    Example:
        ```python
        cache = UnifiedCache()

        # AST 缓存
        ast = cache.get_ast(file_path, content)
        if ast is None:
            ast = parse_ast(content)
            cache.put_ast(file_path, content, ast)

        # 规则结果缓存
        findings = cache.get_rule_result(rule_id, file_path, content)
        if findings is None:
            findings = rule.check(context)
            cache.put_rule_result(rule_id, file_path, content, findings)
        ```
    """

    def __init__(
        self,
        memory_cache: Optional[MemoryCache] = None,
        disk_cache: Optional[DiskCache] = None,
        incremental_cache: Optional[IncrementalCache] = None,
        enable_stats: bool = True,
        auto_check_version: bool = True,
    ):
        """
        初始化统一缓存

        Args:
            memory_cache: L1 内存缓存，None 则创建默认实例
            disk_cache: L2 磁盘缓存，None 则创建默认实例
            incremental_cache: L3 增量缓存，None 则创建默认实例
            enable_stats: 是否启用统计
            auto_check_version: 自动检查引擎版本
        """
        # 三级缓存
        self.memory = memory_cache or MemoryCache()
        self.disk = disk_cache or DiskCache()
        self.incremental = incremental_cache or IncrementalCache()

        # 统计
        self.stats = CacheStats() if enable_stats else None

        # 一致性管理
        self.consistency = CacheConsistencyManager(self)

        # 版本检查
        if auto_check_version:
            self.consistency.check_version()

    def _compute_hash(self, content: str) -> str:
        """计算内容哈希"""
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _make_cache_key(self, file_path: str, content: str) -> str:
        """生成缓存键"""
        content_hash = self._compute_hash(content)
        return f"{file_path}:{content_hash}"

    def _make_rule_cache_key(self, rule_id: str, file_path: str, content: str) -> str:
        """生成规则结果缓存键"""
        base_key = self._make_cache_key(file_path, content)
        return f"{base_key}:{rule_id}"

    # ==================== AST 缓存 ====================

    def get_ast(self, file_path: str, content: str) -> Optional["ASTNode"]:
        """
        获取缓存的 AST

        查找顺序: L1 内存 -> L2 磁盘

        Args:
            file_path: 文件路径
            content: 文件内容

        Returns:
            AST 节点或 None
        """
        cache_key = self._make_cache_key(file_path, content)

        # 1. 尝试 L1 内存缓存
        ast = self.memory.get(cache_key)
        if ast is not None:
            if self.stats:
                self.stats.record_hit("memory", "ast")
            return ast

        # 2. 尝试 L2 磁盘缓存
        ast = self.disk.get_object(cache_key)
        if ast is not None:
            if self.stats:
                self.stats.record_hit("disk", "ast")
            # 提升到 L1
            self.memory.put(cache_key, ast)
            return ast

        if self.stats:
            self.stats.record_miss("ast")
        return None

    def put_ast(self, file_path: str, content: str, ast: "ASTNode") -> None:
        """
        存储 AST 到缓存

        存储到 L1 内存和 L2 磁盘

        Args:
            file_path: 文件路径
            content: 文件内容
            ast: AST 节点
        """
        cache_key = self._make_cache_key(file_path, content)

        # L1 内存
        self.memory.put(cache_key, ast)

        # L2 磁盘（异步/后台）
        try:
            self.disk.put_object(cache_key, ast)
        except Exception:
            pass

    # ==================== 规则结果缓存 ====================

    def get_rule_result(
        self, rule_id: str, file_path: str, content: str
    ) -> Optional[List["Finding"]]:
        """
        获取规则结果缓存

        Args:
            rule_id: 规则ID
            file_path: 文件路径
            content: 文件内容

        Returns:
            问题列表或 None
        """
        cache_key = self._make_rule_cache_key(rule_id, file_path, content)

        # 1. 尝试 L1 内存缓存
        findings = self.memory.get(cache_key)
        if findings is not None:
            if self.stats:
                self.stats.record_hit("memory", "rule_result")
            return findings

        # 2. 尝试 L2 磁盘缓存
        findings = self.disk.get_object(cache_key)
        if findings is not None:
            if self.stats:
                self.stats.record_hit("disk", "rule_result")
            # 提升到 L1
            self.memory.put(cache_key, findings)
            return findings

        if self.stats:
            self.stats.record_miss("rule_result")
        return None

    def put_rule_result(
        self,
        rule_id: str,
        file_path: str,
        content: str,
        findings: List["Finding"],
    ) -> None:
        """
        存储规则结果到缓存

        Args:
            rule_id: 规则ID
            file_path: 文件路径
            content: 文件内容
            findings: 问题列表
        """
        cache_key = self._make_rule_cache_key(rule_id, file_path, content)

        # L1 内存
        self.memory.put(cache_key, findings)

        # L2 磁盘
        try:
            self.disk.put_object(cache_key, findings)
        except Exception:
            pass

    def get_rule_results_batch(
        self,
        rule_ids: List[str],
        file_path: str,
        content: str,
    ) -> Dict[str, Optional[List["Finding"]]]:
        """
        批量获取规则结果

        Args:
            rule_ids: 规则ID列表
            file_path: 文件路径
            content: 文件内容

        Returns:
            规则ID -> 问题列表 的字典
        """
        return {
            rule_id: self.get_rule_result(rule_id, file_path, content)
            for rule_id in rule_ids
        }

    # ==================== 增量缓存 ====================

    def get_changed_files(
        self,
        since_commit: Optional[str] = None,
        file_extensions: Optional[List[str]] = None,
    ) -> List[str]:
        """
        获取变更文件列表

        Args:
            since_commit: 起始提交，None 使用上次扫描的提交
            file_extensions: 文件扩展名过滤

        Returns:
            变更文件路径列表
        """
        return self.incremental.get_changed_files(since_commit, file_extensions)

    def mark_scanned(
        self,
        commit_hash: str,
        files: List[str],
    ) -> None:
        """
        标记已扫描

        Args:
            commit_hash: 提交哈希
            files: 扫描的文件列表
        """
        self.incremental.mark_scanned(commit_hash, files)

    def is_fully_cached(self, commit_hash: str) -> bool:
        """
        检查提交是否已完全缓存

        Args:
            commit_hash: 提交哈希

        Returns:
            True 如果已完全缓存
        """
        return self.incremental.is_fully_cached(commit_hash)

    # ==================== 缓存失效 ====================

    def invalidate_file(self, file_path: str) -> None:
        """
        使文件的所有缓存失效

        Args:
            file_path: 文件路径
        """
        # 收集要删除的键
        keys_to_delete = []

        # 内存缓存
        for key in self.memory.keys():
            if key.startswith(f"{file_path}:"):
                keys_to_delete.append(key)

        # 批量删除
        for key in keys_to_delete:
            self.memory.delete(key)
            self.disk.delete(key)

    def invalidate_rule(self, rule_id: str) -> None:
        """
        使规则的所有结果缓存失效

        Args:
            rule_id: 规则ID
        """
        # 收集要删除的键（包含规则ID）
        keys_to_delete = []

        for key in self.memory.keys():
            if f":{rule_id}" in key:
                keys_to_delete.append(key)

        for key in keys_to_delete:
            self.memory.delete(key)
            self.disk.delete(key)

    def invalidate_pattern(self, pattern: str) -> None:
        """
        按模式失效缓存

        Args:
            pattern: 键匹配模式
        """
        # 简单实现：删除包含 pattern 的所有键
        for key in list(self.memory.keys()):
            if pattern in key:
                self.memory.delete(key)
                self.disk.delete(key)

    def clear(self) -> None:
        """清空所有缓存"""
        self.memory.clear()
        self.disk.clear()
        self.incremental.clear()
        if self.stats:
            self.stats.reset()

    # ==================== 维护 ====================

    def cleanup(self) -> Dict[str, int]:
        """
        清理过期缓存

        Returns:
            清理统计
        """
        memory_cleaned = self.memory.cleanup_expired()
        disk_cleaned = self.disk.cleanup_expired()
        incremental_cleaned = len(self.incremental._commits) - self.incremental.max_commits
        if incremental_cleaned > 0:
            self.incremental._cleanup_old_commits()

        return {
            "memory": memory_cleaned,
            "disk": disk_cleaned,
            "incremental": max(0, incremental_cleaned),
        }

    # ==================== 统计 ====================

    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计

        Returns:
            统计信息字典
        """
        result = {
            "memory": self.memory.get_stats(),
            "disk": self.disk.get_stats(),
            "incremental": self.incremental.get_stats(),
        }

        if self.stats:
            result["performance"] = self.stats.get_summary()

        return result

    def print_stats(self) -> None:
        """打印缓存统计"""
        stats = self.get_stats()

        print("=" * 50)
        print("Cache Statistics")
        print("=" * 50)

        # 性能统计
        perf = stats.get("performance", {})
        print(f"\nPerformance:")
        print(f"  Total Requests: {perf.get('total_requests', 0)}")
        print(f"  Hit Rate: {perf.get('hit_rate', 0):.2%}")
        print(f"  Memory Hits: {perf.get('memory_hits', 0)}")
        print(f"  Disk Hits: {perf.get('disk_hits', 0)}")

        # 内存缓存
        mem = stats.get("memory", {})
        print(f"\nMemory Cache (L1):")
        print(f"  Size: {mem.get('size', 0)} / {mem.get('max_size', 0)}")
        print(f"  Hit Rate: {mem.get('hit_rate', 0):.2%}")

        # 磁盘缓存
        disk = stats.get("disk", {})
        print(f"\nDisk Cache (L2):")
        print(f"  Entries: {disk.get('entries', 0)}")
        print(f"  Size: {disk.get('total_size_mb', 0):.2f} MB")
        print(f"  Hit Rate: {disk.get('hit_rate', 0):.2%}")

        # 增量缓存
        inc = stats.get("incremental", {})
        print(f"\nIncremental Cache (L3):")
        print(f"  Commits: {inc.get('commits_tracked', 0)}")
        print(f"  Current: {inc.get('current_commit', 'N/A')[:8] if inc.get('current_commit') else 'N/A'}")

        print("=" * 50)
