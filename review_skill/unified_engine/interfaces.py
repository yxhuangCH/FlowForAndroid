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


if TYPE_CHECKING:
    from .context import UnifiedContext


# ============================================================
# 核心类型定义 (从 rule_engine 复制过来，保持兼容)
# ============================================================

class RuleSeverity(Enum):
    """Rule severity levels"""
    INFO = "info"           # Informational (no deduction)
    MINOR = "minor"         # Minor issue (deduct 5 points)
    MAJOR = "major"         # Major issue (deduct 10 points)
    CRITICAL = "critical"   # Critical issue (deduct 20 points)
    BLOCKER = "blocker"     # Blocker issue (deduct 100 points, block PR)


class RuleCategory(Enum):
    """Rule categories"""
    SECURITY = "security"            # Security
    PERFORMANCE = "performance"      # Performance
    BEST_PRACTICE = "best_practice"  # Best Practice
    MAINTAINABILITY = "maintainability"  # Maintainability
    CORRECTNESS = "correctness"      # Correctness
    STYLE = "style"                  # Code Style
    CONCURRENCY = "concurrency"      # Concurrency
    LIFECYCLE = "lifecycle"          # Lifecycle Management


@dataclass
class RuleMetadata:
    """Rule metadata"""
    id: str                         # Unique rule identifier (e.g.: no_globalscope)
    name: str                       # Rule name (human-readable)
    description: str                # Detailed rule description
    severity: RuleSeverity          # Severity level
    category: RuleCategory          # Category
    enabled: bool = True            # Whether enabled
    weight: float = 1.0             # Weight (affects scoring)
    tags: List[str] = field(default_factory=list)  # Tags
    suggested_fix: Optional[str] = None  # Suggested fix
    reference_url: Optional[str] = None  # Reference URL
    min_score_deduction: Optional[int] = None  # Min deduction
    max_score_deduction: Optional[int] = None  # Max deduction
    
    def __post_init__(self):
        if not self.id:
            raise ValueError("Rule ID cannot be empty")
        if not self.name:
            raise ValueError("Rule name cannot be empty")
        if not self.description:
            raise ValueError("Rule description cannot be empty")


@dataclass
class Finding:
    """Review finding/issue"""
    rule_id: str                     # Rule ID
    message: str                     # Issue description
    severity: RuleSeverity           # Severity level
    file_path: Optional[str] = None  # File path
    line_number: Optional[int] = None  # Line number (1-based)
    column: Optional[int] = None     # Column number (1-based)
    code_snippet: Optional[str] = None  # Code snippet
    suggestion: Optional[str] = None  # Fix suggestion
    confidence: float = 1.0          # Detection confidence (0.0-1.0)
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional metadata
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict format"""
        return {
            "rule": self.rule_id,
            "severity": self.severity.value,
            "message": self.message,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "column": self.column,
            "code_snippet": self.code_snippet,
            "suggestion": self.suggestion,
            "confidence": self.confidence,
            **self.metadata
        }


# Error handling classes
class ReviewError(Exception):
    """Review system base error class"""
    pass


class RuleExecutionError(ReviewError):
    """Rule execution error"""
    pass


class ConfigurationError(ReviewError):
    """Configuration error"""
    pass


class IntegrationError(ReviewError):
    """Integration error"""
    pass


# ============================================================
# 统一引擎特有定义
# ============================================================

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
