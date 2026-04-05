"""
Unified Engine Cache Module

统一缓存模块，提供三级缓存架构：
- L1 Memory Cache: 进程内 LRU 缓存，延迟 ~1ms
- L2 Disk Cache: 持久化存储，延迟 ~10ms
- L3 Incremental Cache: Git 感知的增量缓存

Example:
    ```python
    from unified_engine.cache import UnifiedCache

    # 创建缓存
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

    # 增量扫描
    changed_files = cache.get_changed_files()
    ```
"""

from .memory_cache import MemoryCache
from .disk_cache import DiskCache
from .incremental_cache import IncrementalCache
from .unified_cache import UnifiedCache
from .stats import CacheStats, CacheMetrics
from .consistency import CacheConsistencyManager, FileWatcher

__all__ = [
    # 主类
    "UnifiedCache",
    # 各级缓存
    "MemoryCache",
    "DiskCache",
    "IncrementalCache",
    # 统计
    "CacheStats",
    "CacheMetrics",
    # 一致性
    "CacheConsistencyManager",
    "FileWatcher",
]
