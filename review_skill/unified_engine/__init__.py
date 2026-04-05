"""Unified Engine - 统一代码审查引擎

本模块提供统一的代码审查引擎，整合 AST Engine 和 Rule Engine 的优点：
- 精确性：基于 AST 的语义分析
- 灵活性：支持正则快速匹配
- 智能调度：自动选择最佳执行策略

快速开始:
    ```python
    from review_skill.unified_engine import (
        UnifiedRule,
        UnifiedContext,
        UnifiedRegistry,
        RuleScheduler,
        ExecutionMode,
    )

    # 定义规则
    class MyRule(UnifiedRule):
        execution_mode = ExecutionMode.HYBRID

        @property
        def metadata(self):
            return RuleMetadata(
                id="my_rule",
                name="My Rule",
                description="Description",
                severity=RuleSeverity.WARNING,
                category=RuleCategory.BEST_PRACTICE,
            )

        def check(self, context: UnifiedContext):
            findings = []
            # 快速筛选
            if not context.contains_pattern(r"pattern"):
                return findings
            # AST 验证
            for node in context.query_ast("Call[name='xxx']"):
                findings.append(Finding(...))
            return findings

    # 注册规则
    registry = UnifiedRegistry()
    registry.register(MyRule())

    # 执行审查
    scheduler = RuleScheduler(registry)
    context = UnifiedContext(code, file_path)
    findings, stats = scheduler.execute(context)
    ```
"""

# 核心接口
from .interfaces import (
    # 执行模式
    ExecutionMode,
    # 规则基类
    UnifiedRule,
    # 执行计划和统计
    ExecutionPlan,
    ExecutionStats,
    RuleExecutionTime,
    # 从 rule_engine 复用的类型
    RuleMetadata,
    Finding,
    RuleSeverity,
    RuleCategory,
    RuleExecutionError,
    ConfigurationError,
)

# 统一上下文
from .context import (
    UnifiedContext,
    LineMatch,
)

# 统一注册表
from .registry import (
    UnifiedRegistry,
    unified_rule,
    unified_rule_instance,
)

# 规则调度器
from .scheduler import (
    RuleScheduler,
)

__all__ = [
    # 执行模式
    "ExecutionMode",
    # 规则基类
    "UnifiedRule",
    # 执行计划和统计
    "ExecutionPlan",
    "ExecutionStats",
    "RuleExecutionTime",
    # 上下文
    "UnifiedContext",
    "LineMatch",
    # 注册表
    "UnifiedRegistry",
    "unified_rule",
    "unified_rule_instance",
    # 调度器
    "RuleScheduler",
    # 复用的类型
    "RuleMetadata",
    "Finding",
    "RuleSeverity",
    "RuleCategory",
    "RuleExecutionError",
    "ConfigurationError",
]

__version__ = "1.0.0"
