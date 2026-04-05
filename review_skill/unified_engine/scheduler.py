"""Rule Scheduler

规则调度器

本模块提供 RuleScheduler 类，负责：
- 根据规则执行模式创建执行计划
- 智能调度规则执行顺序
- 收集执行统计信息
- 支持并行执行
"""

import time
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from .interfaces import (
    UnifiedRule,
    ExecutionMode,
    ExecutionPlan,
    ExecutionStats,
    Finding,
    RuleExecutionError,
)
from .context import UnifiedContext
from .registry import UnifiedRegistry


class RuleScheduler:
    """规则调度器

    负责创建执行计划并调度规则执行。核心功能：
    - 按执行模式分组规则
    - 智能执行顺序（Fast → Hybrid → Precise）
    - 支持并行执行
    - 详细的执行统计

    Example:
        ```python
        registry = UnifiedRegistry()
        # ... 注册规则 ...

        scheduler = RuleScheduler(registry)
        context = UnifiedContext(code, file_path)

        # 创建执行计划
        plan = scheduler.create_execution_plan()
        print(f"Total rules: {plan.total_rules}")

        # 执行规则
        findings, stats = scheduler.execute(context)

        # 查看统计
        print(f"Total time: {stats.total_time_ms}ms")
        print(f"Cache hit rate: {stats.cache_hit_rate}")
        ```
    """

    def __init__(
        self,
        registry: Optional[UnifiedRegistry] = None,
        max_workers: int = 4,
        enable_parallel: bool = True,
        execution_timeout: Optional[float] = None,
    ):
        """初始化调度器

        Args:
            registry: 规则注册表，默认使用全局单例
            max_workers: 并行执行的最大工作线程数
            enable_parallel: 是否启用并行执行
            execution_timeout: 单条规则执行超时时间（秒）
        """
        self.registry = registry or UnifiedRegistry()
        self.max_workers = max_workers
        self.enable_parallel = enable_parallel
        self.execution_timeout = execution_timeout

    def create_execution_plan(
        self, rule_filter: Optional[callable] = None
    ) -> ExecutionPlan:
        """创建执行计划

        获取所有启用的规则，并按执行模式分组。

        Args:
            rule_filter: 可选的规则过滤函数

        Returns:
            ExecutionPlan: 执行计划
        """
        all_rules = self.registry.get_all_rules(enabled_only=True)

        if rule_filter:
            all_rules = [r for r in all_rules if rule_filter(r)]

        # 按执行模式分组
        fast_rules = [r for r in all_rules if r.execution_mode == ExecutionMode.FAST]
        hybrid_rules = [
            r for r in all_rules if r.execution_mode == ExecutionMode.HYBRID
        ]
        precise_rules = [
            r for r in all_rules if r.execution_mode == ExecutionMode.PRECISE
        ]

        # 按严重程度排序（严重问题优先）
        severity_order = {
            "blocker": 0,
            "critical": 1,
            "major": 2,
            "minor": 3,
            "info": 4,
        }

        def sort_key(rule: UnifiedRule) -> int:
            return severity_order.get(rule.metadata.severity.value, 5)

        fast_rules.sort(key=sort_key)
        hybrid_rules.sort(key=sort_key)
        precise_rules.sort(key=sort_key)

        return ExecutionPlan(
            fast_rules=fast_rules,
            hybrid_rules=hybrid_rules,
            precise_rules=precise_rules,
        )

    def execute(
        self,
        context: UnifiedContext,
        plan: Optional[ExecutionPlan] = None,
        progress_callback: Optional[callable] = None,
    ) -> Tuple[List[Finding], ExecutionStats]:
        """执行规则

        按照执行计划运行所有规则，收集结果和统计信息。

        Args:
            context: 执行上下文
            plan: 执行计划，默认自动创建
            progress_callback: 进度回调函数，参数为 (current, total, rule_id)

        Returns:
            Tuple[List[Finding], ExecutionStats]: (问题列表, 执行统计)
        """
        if plan is None:
            plan = self.create_execution_plan()

        stats = ExecutionStats()
        all_findings: List[Finding] = []

        total_rules = plan.total_rules
        executed_count = 0

        start_time = time.time()

        # Phase 1: 执行 Fast Rules（纯正则）
        if plan.fast_rules:
            findings = self._execute_rule_group(
                plan.fast_rules,
                context,
                stats,
                lambda: progress_callback(
                    executed_count + 1, total_rules, plan.fast_rules[0].metadata.id
                )
                if progress_callback
                else None,
            )
            all_findings.extend(findings)
            executed_count += len(plan.fast_rules)

        # Phase 2: 执行 Hybrid Rules
        if plan.hybrid_rules:
            findings = self._execute_rule_group(
                plan.hybrid_rules,
                context,
                stats,
                lambda: progress_callback(
                    executed_count + 1, total_rules, plan.hybrid_rules[0].metadata.id
                )
                if progress_callback
                else None,
            )
            all_findings.extend(findings)
            executed_count += len(plan.hybrid_rules)

        # Phase 3: 执行 Precise Rules（需要 AST）
        if plan.precise_rules:
            # 确保 AST 已解析
            if context.ast_available or not context.ast_available:
                ast_start = time.time()
                _ = context.ast  # 触发解析
                stats.record_ast_parse_time((time.time() - ast_start) * 1000)

            findings = self._execute_rule_group(
                plan.precise_rules,
                context,
                stats,
                lambda: progress_callback(
                    executed_count + 1,
                    total_rules,
                    plan.precise_rules[0].metadata.id,
                )
                if progress_callback
                else None,
            )
            all_findings.extend(findings)
            executed_count += len(plan.precise_rules)

        stats.total_time_ms = (time.time() - start_time) * 1000

        return all_findings, stats

    def _execute_rule_group(
        self,
        rules: List[UnifiedRule],
        context: UnifiedContext,
        stats: ExecutionStats,
        progress_callback: Optional[callable],
    ) -> List[Finding]:
        """执行一组规则

        Args:
            rules: 规则列表
            context: 执行上下文
            stats: 统计对象
            progress_callback: 进度回调

        Returns:
            List[Finding]: 发现的问题列表
        """
        if self.enable_parallel and len(rules) > 1:
            return self._execute_rules_parallel(
                rules, context, stats, progress_callback
            )
        else:
            return self._execute_rules_sequential(
                rules, context, stats, progress_callback
            )

    def _execute_rules_sequential(
        self,
        rules: List[UnifiedRule],
        context: UnifiedContext,
        stats: ExecutionStats,
        progress_callback: Optional[callable],
    ) -> List[Finding]:
        """顺序执行规则"""
        all_findings: List[Finding] = []

        for rule in rules:
            try:
                findings = self._execute_single_rule(rule, context, stats)
                all_findings.extend(findings)
            except Exception as e:
                # 记录错误但继续执行其他规则
                print(
                    f"Error executing rule {rule.metadata.id}: {e}"
                )

            if progress_callback:
                progress_callback()

        return all_findings

    def _execute_rules_parallel(
        self,
        rules: List[UnifiedRule],
        context: UnifiedContext,
        stats: ExecutionStats,
        progress_callback: Optional[callable],
    ) -> List[Finding]:
        """并行执行规则"""
        all_findings: List[Finding] = []
        findings_lock = threading.Lock()

        def execute_rule(rule: UnifiedRule) -> Tuple[str, List[Finding]]:
            try:
                findings = self._execute_single_rule(rule, context, stats)
                return rule.metadata.id, findings
            except Exception as e:
                print(f"Error executing rule {rule.metadata.id}: {e}")
                return rule.metadata.id, []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(execute_rule, rule): rule for rule in rules}

            for future in as_completed(futures):
                rule_id, findings = future.result()
                with findings_lock:
                    all_findings.extend(findings)

                if progress_callback:
                    progress_callback()

        return all_findings

    def _execute_single_rule(
        self, rule: UnifiedRule, context: UnifiedContext, stats: ExecutionStats
    ) -> List[Finding]:
        """执行单条规则"""
        start_time = time.time()

        try:
            findings = rule.check(context)

            elapsed_ms = (time.time() - start_time) * 1000
            stats.add_rule_time(
                rule_id=rule.metadata.id,
                mode=rule.execution_mode,
                elapsed_ms=elapsed_ms,
                findings_count=len(findings),
            )

            return findings

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            stats.add_rule_time(
                rule_id=rule.metadata.id,
                mode=rule.execution_mode,
                elapsed_ms=elapsed_ms,
                findings_count=0,
            )
            raise RuleExecutionError(
                f"Rule {rule.metadata.id} execution failed: {e}"
            ) from e

    def execute_single(
        self, rule_id: str, context: UnifiedContext
    ) -> Tuple[List[Finding], float]:
        """执行单条规则

        Args:
            rule_id: 规则 ID
            context: 执行上下文

        Returns:
            Tuple[List[Finding], float]: (问题列表, 执行时间ms)
        """
        rule = self.registry.get_rule(rule_id)
        if not rule:
            raise ValueError(f"Rule '{rule_id}' not found")

        start_time = time.time()
        findings = rule.check(context)
        elapsed_ms = (time.time() - start_time) * 1000

        return findings, elapsed_ms

    def warmup(self, contexts: List[UnifiedContext]) -> None:
        """预热缓存

        对给定的上下文列表执行所有规则，预热 AST 缓存和规则结果缓存。

        Args:
            contexts: 上下文列表
        """
        plan = self.create_execution_plan()

        for context in contexts:
            # 触发 AST 解析
            if plan.needs_ast_parsing:
                _ = context.ast

            # 执行所有规则
            self.execute(context, plan)

    def __repr__(self) -> str:
        return f"RuleScheduler(registry={self.registry}, parallel={self.enable_parallel})"
