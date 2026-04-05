"""Rule Scheduler

规则调度器

本模块提供 RuleScheduler 类，负责：
- 根据规则执行模式创建执行计划
- 智能调度规则执行顺序
- 收集执行统计信息
- 支持并行执行
- 集成性能监控
- 自适应策略调整
"""

import time
from typing import List, Dict, Any, Optional, Tuple, Callable
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
from .parallel_executor import ParallelExecutor
from .monitor import ExecutionMonitor
from .strategy import AdaptiveStrategy, ExecutionStrategy


class RuleScheduler:
    """规则调度器 (Phase 4 增强版)

    负责创建执行计划并调度规则执行。核心功能：
    - 按执行模式分组规则
    - 智能执行顺序（Fast → Hybrid → Precise）
    - 支持并行执行（FAST 规则）
    - 详细的执行统计和监控
    - 自适应策略（根据文件大小调整）

    Example:
        ```python
        scheduler = RuleScheduler(
            max_workers=4,
            enable_parallel=True,
            enable_monitor=True,
        )

        # 创建执行计划
        plan = scheduler.create_execution_plan(file_size=50000)
        print(f"Selected rules: {plan.total_rules}")

        # 执行规则
        findings, stats = scheduler.execute(context)

        # 查看性能报告
        scheduler.monitor.print_report()
        ```
    """

    def __init__(
        self,
        registry: Optional[UnifiedRegistry] = None,
        max_workers: int = 4,
        enable_parallel: bool = True,
        execution_timeout: Optional[float] = None,
        enable_monitor: bool = True,
        enable_adaptive: bool = True,
    ):
        """初始化调度器

        Args:
            registry: 规则注册表，默认使用全局单例
            max_workers: 并行执行的最大工作线程数
            enable_parallel: 是否启用并行执行
            execution_timeout: 单条规则执行超时时间（秒）
            enable_monitor: 是否启用执行监控
            enable_adaptive: 是否启用自适应策略
        """
        self.registry = registry or UnifiedRegistry()
        self.max_workers = max_workers
        self.enable_parallel = enable_parallel
        self.execution_timeout = execution_timeout or 5.0
        self.enable_monitor = enable_monitor
        self.enable_adaptive = enable_adaptive

        # 子组件
        self.parallel_executor = ParallelExecutor(max_workers=max_workers)
        self.monitor = ExecutionMonitor() if enable_monitor else None
        self.adaptive_strategy = AdaptiveStrategy() if enable_adaptive else None

    def create_execution_plan(
        self,
        file_size: int = 0,
        line_count: int = 0,
        rule_filter: Optional[Callable] = None,
    ) -> ExecutionPlan:
        """创建执行计划

        获取所有启用的规则，按执行模式分组，并根据文件大小自适应调整。

        Args:
            file_size: 文件大小（字节），用于自适应策略
            line_count: 代码行数，用于自适应策略
            rule_filter: 可选的规则过滤函数

        Returns:
            ExecutionPlan: 执行计划
        """
        all_rules = self.registry.get_all_rules(enabled_only=True)

        if rule_filter:
            all_rules = [r for r in all_rules if rule_filter(r)]

        # 自适应策略：根据文件大小筛选规则
        if self.enable_adaptive and file_size > 0:
            all_rules = self.adaptive_strategy.select_rules(
                all_rules, file_size, line_count
            )

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

        # 确定执行策略
        strategy = ExecutionStrategy.STANDARD
        if self.enable_adaptive and file_size > 0:
            strategy = self.adaptive_strategy.select_strategy(file_size, line_count)

        return ExecutionPlan(
            fast_rules=fast_rules,
            hybrid_rules=hybrid_rules,
            precise_rules=precise_rules,
            strategy=strategy,
        )

    def execute(
        self,
        context: UnifiedContext,
        plan: Optional[ExecutionPlan] = None,
        progress_callback: Optional[Callable] = None,
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
            # 自动创建计划，使用文件大小
            content = context.code if hasattr(context, "code") else ""
            plan = self.create_execution_plan(
                file_size=len(content),
                line_count=len(content.split("\n")),
            )

        stats = ExecutionStats()
        all_findings: List[Finding] = []

        total_rules = plan.total_rules
        executed_count = 0

        start_time = time.time()

        # 文件执行监控
        file_record = None
        if self.monitor:
            content = context.code if hasattr(context, "code") else ""
            file_record = self.monitor.start_file_execution(
                context.file_path, content
            )

        # Phase 1: 执行 Fast Rules（并行）
        if plan.fast_rules:
            findings = self._execute_fast_rules(
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

        # Phase 2: 执行 Hybrid Rules（串行，可能有 AST 解析）
        if plan.hybrid_rules:
            findings = self._execute_hybrid_rules(
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

        # Phase 3: 执行 Precise Rules（需要 AST，复用已解析的）
        if plan.precise_rules:
            findings = self._execute_precise_rules(
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

        # 文件执行监控结束
        if self.monitor and file_record:
            self.monitor.end_file_execution(
                file_record,
                rules_executed=executed_count,
                findings_count=len(all_findings),
            )

        return all_findings, stats

    def _execute_fast_rules(
        self,
        rules: List[UnifiedRule],
        context: UnifiedContext,
        stats: ExecutionStats,
        progress_callback: Optional[Callable],
    ) -> List[Finding]:
        """执行 FAST 规则（并行）"""
        if not rules:
            return []

        # 使用并行执行器
        if self.enable_parallel and len(rules) > 1:
            return self._execute_rules_parallel_fast(rules, context, stats, progress_callback)
        else:
            return self._execute_rules_sequential(rules, context, stats, progress_callback)

    def _execute_hybrid_rules(
        self,
        rules: List[UnifiedRule],
        context: UnifiedContext,
        stats: ExecutionStats,
        progress_callback: Optional[Callable],
    ) -> List[Finding]:
        """执行 HYBRID 规则（串行）"""
        return self._execute_rules_sequential(rules, context, stats, progress_callback)

    def _execute_precise_rules(
        self,
        rules: List[UnifiedRule],
        context: UnifiedContext,
        stats: ExecutionStats,
        progress_callback: Optional[Callable],
    ) -> List[Finding]:
        """执行 PRECISE 规则（需要 AST）"""
        # 确保 AST 已解析（只解析一次）
        if not context.ast_available:
            ast_start = time.time()
            _ = context.ast  # 触发解析
            stats.record_ast_parse_time((time.time() - ast_start) * 1000)

        return self._execute_rules_sequential(rules, context, stats, progress_callback)

    def _execute_rules_parallel_fast(
        self,
        rules: List[UnifiedRule],
        context: UnifiedContext,
        stats: ExecutionStats,
        progress_callback: Optional[Callable],
    ) -> List[Finding]:
        """并行执行 FAST 规则"""
        # 使用 ParallelExecutor
        findings = self.parallel_executor.execute_rules(
            rules, context, timeout=self.execution_timeout
        )

        # 记录统计
        for rule in rules:
            stats.add_rule_time(
                rule_id=rule.metadata.id,
                mode=rule.execution_mode,
                elapsed_ms=0,  # 并行执行无法精确记录单条时间
                findings_count=0,
            )
            if progress_callback:
                progress_callback()

        return findings

    def _execute_rules_sequential(
        self,
        rules: List[UnifiedRule],
        context: UnifiedContext,
        stats: ExecutionStats,
        progress_callback: Optional[Callable],
    ) -> List[Finding]:
        """顺序执行规则"""
        all_findings: List[Finding] = []

        for rule in rules:
            try:
                findings = self._execute_single_rule(rule, context, stats)
                all_findings.extend(findings)
            except Exception as e:
                print(f"Error executing rule {rule.metadata.id}: {e}")

            if progress_callback:
                progress_callback()

        return all_findings

    def _execute_single_rule(
        self, rule: UnifiedRule, context: UnifiedContext, stats: ExecutionStats
    ) -> List[Finding]:
        """执行单条规则"""
        start_time = time.perf_counter()

        # 监控开始
        monitor_record = None
        if self.monitor:
            content = context.code if hasattr(context, "code") else ""
            monitor_record = self.monitor.start_rule_execution(
                rule, context.file_path, content
            )

        try:
            findings = rule.check(context)

            elapsed_ms = (time.perf_counter() - start_time) * 1000
            stats.add_rule_time(
                rule_id=rule.metadata.id,
                mode=rule.execution_mode,
                elapsed_ms=elapsed_ms,
                findings_count=len(findings),
            )

            # 监控结束
            if self.monitor and monitor_record:
                self.monitor.end_rule_execution(monitor_record, findings)

            return findings

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            stats.add_rule_time(
                rule_id=rule.metadata.id,
                mode=rule.execution_mode,
                elapsed_ms=elapsed_ms,
                findings_count=0,
            )

            # 监控结束（失败）
            if self.monitor and monitor_record:
                self.monitor.end_rule_execution(monitor_record, [])

            raise RuleExecutionError(
                f"Rule {rule.metadata.id} execution failed: {e}"
            ) from e

    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        if self.monitor:
            return self.monitor.generate_report()
        return {}

    def print_performance_report(self) -> None:
        """打印性能报告"""
        if self.monitor:
            self.monitor.print_report()

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

        start_time = time.perf_counter()
        findings = rule.check(context)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

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

    def shutdown(self) -> None:
        """关闭调度器，释放资源"""
        self.parallel_executor.shutdown()

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.shutdown()
        return False

    def __repr__(self) -> str:
        return f"RuleScheduler(parallel={self.enable_parallel}, monitor={self.enable_monitor})"
