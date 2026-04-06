"""
Unified Execution Engine - 统一执行引擎

整合所有组件的统一执行引擎，提供完整的代码审查功能。

Features:
- 整合缓存、调度器、监控
- 支持批量文件扫描
- 增量扫描支持
- 完整的性能报告
"""

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from rule_engine.interfaces import Finding

from .cache import UnifiedCache
from .scheduler import RuleScheduler
from .monitor import ExecutionMonitor
from .strategy import AdaptiveStrategy
from .interfaces import UnifiedRule, ExecutionStats
from .context import UnifiedContext
from .rules import get_all_rules


@dataclass
class ScanResult:
    """扫描结果"""

    findings: List["Finding"] = field(default_factory=list)
    execution_time: float = 0.0
    files_scanned: int = 0
    rules_executed: int = 0
    cache_hits: int = 0
    cache_misses: int = 0


class UnifiedExecutionEngine:
    """
    统一执行引擎

    整合缓存、调度器、监控等所有组件，提供完整的代码审查功能。

    Example:
        ```python
        # 初始化引擎
        engine = UnifiedExecutionEngine(
            cache=UnifiedCache(),
            max_workers=4,
        )

        # 扫描单个文件
        result = engine.scan_file("app/src/MainActivity.kt")
        print(f"Found {len(result.findings)} issues")

        # 扫描多个文件
        results = engine.scan_files([
            "app/src/MainActivity.kt",
            "app/src/Utils.kt",
        ])

        # 增量扫描
        changed_files = engine.get_changed_files()
        results = engine.scan_files(changed_files)

        # 性能报告
        engine.print_performance_report()
        ```
    """

    def __init__(
        self,
        cache: Optional[UnifiedCache] = None,
        scheduler: Optional[RuleScheduler] = None,
        max_workers: int = 4,
        enable_parallel: bool = True,
        enable_monitor: bool = True,
        enable_adaptive: bool = True,
        rules: Optional[List[UnifiedRule]] = None,
    ):
        """
        初始化执行引擎

        Args:
            cache: 统一缓存，None 则创建默认实例
            scheduler: 规则调度器，None 则创建默认实例
            max_workers: 并行执行的最大工作线程数
            enable_parallel: 是否启用并行执行
            enable_monitor: 是否启用执行监控
            enable_adaptive: 是否启用自适应策略
            rules: 规则列表，None 则使用 get_all_rules()
        """
        # 组件
        self.cache = cache or UnifiedCache()
        self.scheduler = scheduler or RuleScheduler(
            max_workers=max_workers,
            enable_parallel=enable_parallel,
            enable_monitor=enable_monitor,
            enable_adaptive=enable_adaptive,
        )
        self.monitor = self.scheduler.monitor

        # 规则
        self.rules = rules or get_all_rules()

        # 注册规则到调度器的注册表
        for rule in self.rules:
            try:
                if not self.scheduler.registry.has_rule(rule.metadata.id):
                    self.scheduler.registry.register(rule)
            except ValueError:
                pass  # Already registered

        # 自适应策略
        self.adaptive_strategy = AdaptiveStrategy() if enable_adaptive else None

        # 统计
        self._total_files_scanned = 0
        self._total_rules_executed = 0

    def scan_file(
        self,
        file_path: str,
        content: Optional[str] = None,
    ) -> ScanResult:
        """
        扫描单个文件

        Args:
            file_path: 文件路径
            content: 文件内容，None 则自动读取

        Returns:
            ScanResult: 扫描结果
        """
        start_time = time.perf_counter()

        # 读取文件内容
        if content is None:
            try:
                content = Path(file_path).read_text(encoding="utf-8")
            except Exception as e:
                print(f"Error reading file {file_path}: {e}")
                return ScanResult()

        # 创建执行上下文
        context = UnifiedContext(
            code=content,
            file_path=file_path,
        )

        # 创建执行计划（自适应）
        plan = self.scheduler.create_execution_plan(
            file_size=len(content),
            line_count=len(content.split("\n")),
        )

        # 执行规则
        findings, stats = self.scheduler.execute(context, plan)

        # 计算执行时间
        execution_time = (time.perf_counter() - start_time) * 1000

        # 更新统计
        self._total_files_scanned += 1
        self._total_rules_executed += plan.total_rules

        return ScanResult(
            findings=findings,
            execution_time=execution_time,
            files_scanned=1,
            rules_executed=plan.total_rules,
        )

    def scan_files(
        self,
        file_paths: List[str],
        show_progress: bool = True,
    ) -> Dict[str, ScanResult]:
        """
        扫描多个文件

        Args:
            file_paths: 文件路径列表
            show_progress: 是否显示进度

        Returns:
            文件路径 -> 扫描结果 的字典
        """
        results = {}
        total_files = len(file_paths)

        for i, file_path in enumerate(file_paths, 1):
            if show_progress:
                print(f"[{i}/{total_files}] Scanning {file_path}...")

            result = self.scan_file(file_path)
            results[file_path] = result

            if show_progress and result.findings:
                print(f"  Found {len(result.findings)} issues")

        return results

    def scan_code(
        self,
        code: str,
        file_path: str = "<inline>",
    ) -> ScanResult:
        """
        扫描代码字符串

        Args:
            code: 代码内容
            file_path: 虚拟文件路径（用于报告）

        Returns:
            ScanResult: 扫描结果
        """
        return self.scan_file(file_path, code)

    def get_changed_files(
        self,
        since_commit: Optional[str] = None,
        file_extensions: Optional[List[str]] = None,
    ) -> List[str]:
        """
        获取变更文件列表（增量扫描）

        Args:
            since_commit: 起始提交，None 则使用上次扫描的提交
            file_extensions: 文件扩展名过滤，如 [".kt"]

        Returns:
            变更文件路径列表
        """
        return self.cache.get_changed_files(since_commit, file_extensions)

    def mark_scanned(self, commit_hash: str, files: List[str]) -> None:
        """
        标记已扫描（用于增量扫描）

        Args:
            commit_hash: 提交哈希
            files: 扫描的文件列表
        """
        self.cache.mark_scanned(commit_hash, files)

    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        report = {
            "engine": {
                "total_files_scanned": self._total_files_scanned,
                "total_rules_executed": self._total_rules_executed,
            },
        }

        # 调度器监控报告
        if self.scheduler:
            report["scheduler"] = self.scheduler.get_performance_report()

        # 缓存统计
        if self.cache:
            report["cache"] = self.cache.get_stats()

        return report

    def print_performance_report(self) -> None:
        """打印性能报告"""
        print("\n" + "=" * 60)
        print("Unified Execution Engine Performance Report")
        print("=" * 60)

        print(f"\n📊 Overall:")
        print(f"  Total Files Scanned: {self._total_files_scanned}")
        print(f"  Total Rules Executed: {self._total_rules_executed}")

        # 调度器报告
        if self.scheduler and self.scheduler.monitor:
            self.scheduler.print_performance_report()

        # 缓存统计
        if self.cache:
            cache_stats = self.cache.get_stats()
            perf = cache_stats.get("performance", {})
            print(f"\n💾 Cache Performance:")
            print(f"  Hit Rate: {perf.get('hit_rate', 0):.2%}")
            print(f"  Total Requests: {perf.get('total_requests', 0)}")

    def reset_stats(self) -> None:
        """重置统计信息"""
        self._total_files_scanned = 0
        self._total_rules_executed = 0
        if self.monitor:
            self.monitor.reset()

    def cleanup(self) -> Dict[str, int]:
        """
        清理过期缓存

        Returns:
            清理统计
        """
        return self.cache.cleanup()

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.scheduler.shutdown()
        return False

    def __repr__(self) -> str:
        return (
            f"UnifiedExecutionEngine("
            f"rules={len(self.rules)}, "
            f"parallel={self.scheduler.enable_parallel}, "
            f"monitor={self.scheduler.enable_monitor}"
            f")"
        )
