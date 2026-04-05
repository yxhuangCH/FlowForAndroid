"""
Parallel Executor - 并行执行器

使用 ThreadPoolExecutor 并行执行 FAST 规则，提升扫描速度。

特性:
- 线程池并行执行
- 超时机制
- 异常处理
- 结果合并
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from rule_engine.interfaces import Finding
    from .interfaces import UnifiedRule
    from .context import UnifiedContext


class ParallelExecutor:
    """
    并行执行器

    使用 ThreadPoolExecutor 并行执行独立的 FAST 规则，
    充分利用多核 CPU 提升扫描速度。

    Example:
        ```python
        executor = ParallelExecutor(max_workers=4)

        # 并行执行 FAST 规则
        findings = executor.execute_rules(fast_rules, context)

        # 完成后关闭
        executor.shutdown()
        ```
    """

    def __init__(self, max_workers: int = 4):
        """
        初始化并行执行器

        Args:
            max_workers: 最大工作线程数，默认 4
        """
        self.max_workers = max_workers
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    def execute_rules(
        self,
        rules: List["UnifiedRule"],
        context: "UnifiedContext",
        timeout: float = 5.0,
    ) -> List["Finding"]:
        """
        并行执行规则

        Args:
            rules: 规则列表（应该是 FAST 规则）
            context: 执行上下文
            timeout: 单条规则超时时间（秒）

        Returns:
            合并的问题列表
        """
        if not rules:
            return []

        findings = []
        completed = 0
        failed = 0
        timed_out = 0

        # 提交所有任务
        futures = {}
        for rule in rules:
            future = self._executor.submit(self._execute_rule_safe, rule, context)
            futures[future] = rule

        # 收集结果
        for future in as_completed(futures):
            rule = futures[future]
            try:
                result = future.result(timeout=timeout)
                if result:
                    findings.extend(result)
                completed += 1
            except TimeoutError:
                timed_out += 1
                print(f"⚠️ Rule {rule.metadata.id} timed out after {timeout}s")
            except Exception as e:
                failed += 1
                print(f"⚠️ Rule {rule.metadata.id} failed: {e}")

        return findings

    def _execute_rule_safe(
        self, rule: "UnifiedRule", context: "UnifiedContext"
    ) -> List["Finding"]:
        """
        安全执行规则（捕获异常）

        Args:
            rule: 规则实例
            context: 执行上下文

        Returns:
            问题列表或空列表
        """
        try:
            return rule.check(context) or []
        except Exception as e:
            print(f"Rule {rule.metadata.id} execution error: {e}")
            return []

    def shutdown(self, wait: bool = True) -> None:
        """
        关闭执行器

        Args:
            wait: 是否等待所有任务完成
        """
        self._executor.shutdown(wait=wait)

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.shutdown()
        return False
