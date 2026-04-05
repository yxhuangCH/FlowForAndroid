"""
Cache Consistency Manager - 缓存一致性管理

处理缓存失效和一致性保证。

场景:
- 文件内容变更 -> 失效 AST 和规则结果
- 规则代码更新 -> 失效所有该规则的结果
- 引擎版本更新 -> 清空所有缓存
"""

import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Set

if TYPE_CHECKING:
    from .unified_cache import UnifiedCache


class CacheConsistencyManager:
    """
    缓存一致性管理器

    确保缓存数据与实际文件状态一致，处理各种失效场景。
    """

    # 引擎版本，修改后会使所有缓存失效
    ENGINE_VERSION = "1.0.0"

    def __init__(self, cache: "UnifiedCache", version_file: str = ".cache_version"):
        """
        初始化一致性管理器

        Args:
            cache: 统一缓存实例
            version_file: 版本文件路径
        """
        self.cache = cache
        self.version_file = Path(version_file)

    def check_version(self) -> bool:
        """
        检查缓存版本

        如果版本不匹配，清空所有缓存。

        Returns:
            True 如果版本匹配，False 如果不匹配已清空
        """
        current_version = self._get_engine_version()

        if not self.version_file.exists():
            self._write_version(current_version)
            return True

        try:
            cached_version = self.version_file.read_text().strip()
            if cached_version != current_version:
                # 版本不匹配，清空缓存
                self.cache.clear()
                self._write_version(current_version)
                return False
        except Exception:
            # 读取失败，清空缓存
            self.cache.clear()
            self._write_version(current_version)
            return False

        return True

    def _get_engine_version(self) -> str:
        """获取引擎版本"""
        # 可以基于代码哈希计算版本
        return self.ENGINE_VERSION

    def _write_version(self, version: str) -> None:
        """写入版本文件"""
        try:
            self.version_file.write_text(version)
        except Exception as e:
            print(f"Warning: Failed to write cache version: {e}")

    def invalidate_for_file(self, file_path: str, content_hash: Optional[str] = None) -> None:
        """
        文件变更时失效相关缓存

        Args:
            file_path: 文件路径
            content_hash: 新的内容哈希（可选）
        """
        # 删除该文件的所有缓存
        self.cache.invalidate_file(file_path)

    def invalidate_for_rule(self, rule_id: str) -> None:
        """
        规则更新时失效该规则的所有结果缓存

        Args:
            rule_id: 规则ID
        """
        self.cache.invalidate_rule(rule_id)

    def invalidate_pattern(self, pattern: str) -> None:
        """
        按模式失效缓存

        Args:
            pattern: 键匹配模式
        """
        self.cache.invalidate_pattern(pattern)

    def get_cache_key(self, file_path: str, content: str) -> str:
        """
        生成缓存键

        Args:
            file_path: 文件路径
            content: 文件内容

        Returns:
            缓存键
        """
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        return f"{file_path}:{content_hash}"

    def get_rule_cache_key(self, file_path: str, content: str, rule_id: str) -> str:
        """
        生成规则结果缓存键

        Args:
            file_path: 文件路径
            content: 文件内容
            rule_id: 规则ID

        Returns:
            缓存键
        """
        base_key = self.get_cache_key(file_path, content)
        return f"{base_key}:{rule_id}"


class FileWatcher:
    """
    文件变更监视器（简化版）

    检测文件修改时间变化，触发缓存失效。
    """

    def __init__(self, consistency_manager: CacheConsistencyManager):
        self.cm = consistency_manager
        self._file_mtimes: dict = {}

    def check_file(self, file_path: str) -> bool:
        """
        检查文件是否变更

        Args:
            file_path: 文件路径

        Returns:
            True 如果文件已变更
        """
        path = Path(file_path)
        if not path.exists():
            # 文件被删除
            if file_path in self._file_mtimes:
                self.cm.invalidate_for_file(file_path)
                del self._file_mtimes[file_path]
            return True

        current_mtime = path.stat().st_mtime
        last_mtime = self._file_mtimes.get(file_path)

        if last_mtime is None or current_mtime != last_mtime:
            # 文件变更
            if last_mtime is not None:
                self.cm.invalidate_for_file(file_path)
            self._file_mtimes[file_path] = current_mtime
            return True

        return False

    def reset(self):
        """重置监视器"""
        self._file_mtimes.clear()
