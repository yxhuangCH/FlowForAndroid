"""Unified Engine Core Interfaces

统一引擎核心接口定义

本模块定义了统一规则引擎的核心抽象接口，包括：
- UnifiedRule: 统一规则基类
- ExecutionMode: 规则执行模式枚举
- ExecutionPlan: 执行计划
- ExecutionStats: 执行统计
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional, Type, TYPE_CHECKING
import time

# 从 Rule Engine 复用核心数据类
from rule_engine.interfaces import (
    RuleMetadata,
    Finding,
    RuleSeverity,
    RuleCategory,
    RuleExecutionError,
    ConfigurationError,
)

if TYPE_CHECKING:
    from .context import UnifiedContext


class ExecutionMode(Enum):
    """规则执行模式

    根据规则复杂度选择不同的执行策略：
    - FAST: 仅使用正则快速匹配，适用于简单模式检测
    - PRECISE: 必须使用 AST 分析，适用于复杂语义检测
    - HYBRID: 先快速筛选，再 AST 验证，平衡速度和精确性
    """

    FAST = "fast"  # 仅正则快速匹配 (<10ms)
    PRECISE = "precise"  # 必须使用 AST (50-200ms)
    HYBRID = "hybrid"  # 先快速筛选，再 AST 验证 (10-100ms)


class UnifiedRule(ABC):
    """统一规则基类

    所有规则必须继承此类。统一引擎通过此接口与规则交互，
    无论规则内部使用正则还是 AST 分析。

    Example:
        ```python
        class NoGlobalScopeRule(UnifiedRule):
            execution_mode = ExecutionMode.HYBRID

            @property
            def metadata(self) -> RuleMetadata:
                return RuleMetadata(
                    id="no_globalscope",
                    name="Prohibit GlobalScope usage",
                    description="GlobalScope.launch may cause memory leaks",
                    severity=RuleSeverity.BLOCKER,
                    category=RuleCategory.LIFECYCLE,
                )

            def check(self, context: UnifiedContext) -> List[Finding]:
                findings = []
                # Phase 1: Fast screening
                candidates = context.find_pattern(r"GlobalScope\.\w+")
                if not candidates:
                    return findings

                # Phase 2: AST validation
                for node in context.query_ast("Call[receiver='GlobalScope']"):
                    findings.append(Finding(...))
                return findings
        ```
    """

    @property
    @abstractmethod
    def metadata(self) -> RuleMetadata:
        """规则元数据

        Returns:
            RuleMetadata 包含规则的 ID、名称、描述、严重程度等信息
        """
        pass

    @property
    def execution_mode(self) -> ExecutionMode:
        """规则执行模式

        子类可以覆盖此属性来指定执行模式：
        - ExecutionMode.FAST: 简单规则，仅需正则匹配
        - ExecutionMode.PRECISE: 复杂规则，必须 AST 分析
        - ExecutionMode.HYBRID: 混合模式（默认），先正则筛选再 AST 验证

        Returns:
            ExecutionMode 枚举值
        """
        return ExecutionMode.HYBRID

    @abstractmethod
    def check(self, context: "UnifiedContext") -> List[Finding]:
        """执行规则检查

        Args:
            context: 统一上下文，包含代码内容、文件路径、AST 访问接口等

        Returns:
            List[Finding]: 发现的问题列表，如果没有问题则返回空列表

        Raises:
            RuleExecutionError: 规则执行出错时抛出
        """
        pass

    def on_register(self) -> None:
        """规则注册时的回调（可选）

        子类可以覆盖此方法，在规则被注册到注册表时执行初始化操作。
        """
        pass

    def on_unregister(self) -> None:
        """规则注销时的回调（可选）

        子类可以覆盖此方法，在规则从注册表移除时执行清理操作。
        """
        pass

    def get_score_deduction(self, severity: RuleSeverity) -> int:
        """根据严重程度计算扣分

        Args:
            severity: 严重程度级别

        Returns:
            int: 扣分值
        """
        if (
            self.metadata.min_score_deduction is not None
            and self.metadata.max_score_deduction is not None
        ):
            # 使用规则特定的扣分范围
            default_deductions = {
                RuleSeverity.INFO: 0,
                RuleSeverity.MINOR: 5,
                RuleSeverity.MAJOR: 10,
                RuleSeverity.CRITICAL: 20,
                RuleSeverity.BLOCKER: 100,
            }
            deduction = default_deductions.get(severity, 0)
            return min(
                self.metadata.max_score_deduction,
                max(self.metadata.min_score_deduction, deduction),
            )

        # 使用默认扣分
        default_deductions = {
            RuleSeverity.INFO: 0,
            RuleSeverity.MINOR: 5,
            RuleSeverity.MAJOR: 10,
            RuleSeverity.CRITICAL: 20,
            RuleSeverity.BLOCKER: 100,
        }
        return default_deductions.get(severity, 0)

    def __repr__(self) -> str:
        return f"UnifiedRule({self.metadata.id}, mode={self.execution_mode.value})"


@dataclass
class ExecutionPlan:
    """规则执行计划

    由调度器创建，包含按执行模式分类的规则列表。
    """

    fast_rules: List[UnifiedRule] = field(default_factory=list)
    hybrid_rules: List[UnifiedRule] = field(default_factory=list)
    precise_rules: List[UnifiedRule] = field(default_factory=list)
    strategy: Any = field(default=None)  # ExecutionStrategy, optional

    @property
    def total_rules(self) -> int:
        """总规则数"""
        return len(self.fast_rules) + len(self.hybrid_rules) + len(self.precise_rules)

    @property
    def needs_ast_parsing(self) -> bool:
        """是否需要解析 AST"""
        return len(self.precise_rules) > 0 or len(self.hybrid_rules) > 0


@dataclass
class RuleExecutionTime:
    """单条规则的执行时间记录"""

    rule_id: str
    execution_mode: ExecutionMode
    elapsed_ms: float
    findings_count: int


@dataclass
class ExecutionStats:
    """执行统计信息

    记录规则执行的性能指标和统计信息。
    """

    rule_times: List[RuleExecutionTime] = field(default_factory=list)
    total_time_ms: float = 0.0
    ast_parse_time_ms: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0

    def add_rule_time(
        self, rule_id: str, mode: ExecutionMode, elapsed_ms: float, findings_count: int = 0
    ) -> None:
        """添加规则执行时间记录"""
        self.rule_times.append(
            RuleExecutionTime(
                rule_id=rule_id,
                execution_mode=mode,
                elapsed_ms=elapsed_ms,
                findings_count=findings_count,
            )
        )

    def record_ast_parse_time(self, elapsed_ms: float) -> None:
        """记录 AST 解析时间"""
        self.ast_parse_time_ms = elapsed_ms

    def record_cache_hit(self) -> None:
        """记录缓存命中"""
        self.cache_hits += 1

    def record_cache_miss(self) -> None:
        """记录缓存未命中"""
        self.cache_misses += 1

    @property
    def rule_count(self) -> int:
        """执行的规则数量"""
        return len(self.rule_times)

    def get_slowest_rules(self, n: int = 5) -> List[RuleExecutionTime]:
        """获取最慢的规则"""
        return sorted(self.rule_times, key=lambda x: x.elapsed_ms, reverse=True)[:n]

    @property
    def cache_hit_rate(self) -> float:
        """缓存命中率"""
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return self.cache_hits / total

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "total_time_ms": round(self.total_time_ms, 2),
            "ast_parse_time_ms": round(self.ast_parse_time_ms, 2),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": round(self.cache_hit_rate, 2),
            "rule_count": len(self.rule_times),
            "slowest_rules": [
                {
                    "rule_id": rt.rule_id,
                    "mode": rt.execution_mode.value,
                    "elapsed_ms": round(rt.elapsed_ms, 2),
                    "findings": rt.findings_count,
                }
                for rt in self.get_slowest_rules(5)
            ],
        }


# 导出所有公共接口
__all__ = [
    # 执行模式
    "ExecutionMode",
    # 规则基类
    "UnifiedRule",
    # 执行计划
    "ExecutionPlan",
    # 执行统计
    "ExecutionStats",
    "RuleExecutionTime",
    # 从 rule_engine 复用的类型
    "RuleMetadata",
    "Finding",
    "RuleSeverity",
    "RuleCategory",
    "RuleExecutionError",
    "ConfigurationError",
]
