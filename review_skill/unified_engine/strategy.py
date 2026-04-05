"""
Adaptive Strategy - 自适应执行策略

根据文件大小/复杂度动态调整执行策略，优化性能和准确性平衡。

特性:
- 根据文件大小选择策略
- 动态规则筛选
- 超时时间调整
- 策略矩阵实现
"""

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from rule_engine.interfaces import RuleSeverity
    from .interfaces import UnifiedRule


class ExecutionStrategy(Enum):
    """执行策略枚举"""

    STANDARD = "standard"  # 标准模式：执行所有规则
    OPTIMIZED = "optimized"  # 优化模式：跳过部分非关键规则
    REDUCED = "reduced"  # 精简模式：只执行关键规则
    MINIMAL = "minimal"  # 最小模式：只执行最重要的规则


@dataclass
class StrategyConfig:
    """策略配置"""

    name: str
    max_file_size: int  # 字节
    severity_threshold: "RuleSeverity"  # 最低严重程度
    enable_fast_rules: bool
    enable_hybrid_rules: bool
    enable_precise_rules: bool
    timeout_multiplier: float  # 超时时间倍数


class AdaptiveStrategy:
    """
    自适应执行策略

    根据文件特性动态调整规则执行方式，在大文件时减少规则数量，
    保证性能的同时尽可能发现关键问题。

    Example:
        ```python
        strategy = AdaptiveStrategy()

        # 选择执行策略
        strategy_type = strategy.select_strategy(file_size=50000)

        # 选择要执行的规则
        selected_rules = strategy.select_rules(all_rules, file_size, line_count)

        # 获取超时时间
        timeout = strategy.get_timeout(file_size)
        ```
    """

    # 文件大小阈值（字节）
    SIZE_SMALL = 10_000  # 10KB
    SIZE_MEDIUM = 100_000  # 100KB
    SIZE_LARGE = 500_000  # 500KB

    def __init__(self):
        """初始化自适应策略"""
        # 导入 RuleSeverity
        from rule_engine.interfaces import RuleSeverity

        self.severity = RuleSeverity

        # 策略配置矩阵
        self._strategies = {
            ExecutionStrategy.STANDARD: StrategyConfig(
                name="Standard",
                max_file_size=self.SIZE_SMALL,
                severity_threshold=RuleSeverity.INFO,
                enable_fast_rules=True,
                enable_hybrid_rules=True,
                enable_precise_rules=True,
                timeout_multiplier=1.0,
            ),
            ExecutionStrategy.OPTIMIZED: StrategyConfig(
                name="Optimized",
                max_file_size=self.SIZE_MEDIUM,
                severity_threshold=RuleSeverity.MINOR,
                enable_fast_rules=True,
                enable_hybrid_rules=True,
                enable_precise_rules=True,
                timeout_multiplier=1.5,
            ),
            ExecutionStrategy.REDUCED: StrategyConfig(
                name="Reduced",
                max_file_size=self.SIZE_LARGE,
                severity_threshold=RuleSeverity.MAJOR,
                enable_fast_rules=True,
                enable_hybrid_rules=True,
                enable_precise_rules=False,
                timeout_multiplier=2.0,
            ),
            ExecutionStrategy.MINIMAL: StrategyConfig(
                name="Minimal",
                max_file_size=float("inf"),
                severity_threshold=RuleSeverity.CRITICAL,
                enable_fast_rules=True,
                enable_hybrid_rules=False,
                enable_precise_rules=False,
                timeout_multiplier=3.0,
            ),
        }

    def select_strategy(self, file_size: int, line_count: int = 0):
        """
        选择执行策略

        Args:
            file_size: 文件大小（字节）
            line_count: 代码行数（可选）

        Returns:
            执行策略
        """
        if file_size < self.SIZE_SMALL:
            return ExecutionStrategy.STANDARD
        elif file_size < self.SIZE_MEDIUM:
            return ExecutionStrategy.OPTIMIZED
        elif file_size < self.SIZE_LARGE:
            return ExecutionStrategy.REDUCED
        else:
            return ExecutionStrategy.MINIMAL

    def select_rules(
        self,
        rules: List["UnifiedRule"],
        file_size: int,
        line_count: int = 0,
    ) -> List["UnifiedRule"]:
        """
        选择要执行的规则

        根据文件大小和策略，筛选出需要执行的规则。

        Args:
            rules: 所有可用规则
            file_size: 文件大小
            line_count: 代码行数

        Returns:
            筛选后的规则列表
        """
        strategy = self.select_strategy(file_size, line_count)
        config = self._strategies[strategy]

        selected = []
        for rule in rules:
            # 检查严重程度
            if not self._severity_meets_threshold(
                rule.metadata.severity, config.severity_threshold
            ):
                continue

            # 检查执行模式
            if rule.execution_mode.value == "fast" and not config.enable_fast_rules:
                continue
            if rule.execution_mode.value == "hybrid" and not config.enable_hybrid_rules:
                continue
            if rule.execution_mode.value == "precise" and not config.enable_precise_rules:
                continue

            selected.append(rule)

        return selected

    def _severity_meets_threshold(
        self, severity: "RuleSeverity", threshold: "RuleSeverity"
    ) -> bool:
        """
        检查严重程度是否满足阈值

        Args:
            severity: 规则严重程度
            threshold: 阈值

        Returns:
            True 如果 severity >= threshold
        """
        # 严重程度排序（从高到低）
        severity_order = {
            self.severity.BLOCKER: 5,
            self.severity.CRITICAL: 4,
            self.severity.MAJOR: 3,
            self.severity.MINOR: 2,
            self.severity.INFO: 1,
        }

        return severity_order.get(severity, 0) >= severity_order.get(threshold, 0)

    def get_timeout(self, file_size: int, base_timeout: float = 5.0) -> float:
        """
        获取超时时间

        根据文件大小动态调整超时时间。

        Args:
            file_size: 文件大小
            base_timeout: 基础超时时间（秒）

        Returns:
            调整后的超时时间
        """
        strategy = self.select_strategy(file_size)
        config = self._strategies[strategy]

        return base_timeout * config.timeout_multiplier

    def should_parse_ast(self, file_size: int) -> bool:
        """
        是否应该解析 AST

        大文件时可能跳过 AST 解析以提升性能。

        Args:
            file_size: 文件大小

        Returns:
            True 如果需要解析 AST
        """
        strategy = self.select_strategy(file_size)
        config = self._strategies[strategy]
        return config.enable_precise_rules or config.enable_hybrid_rules

    def get_strategy_info(self, file_size: int) -> dict:
        """
        获取策略信息

        Args:
            file_size: 文件大小

        Returns:
            策略信息字典
        """
        strategy = self.select_strategy(file_size)
        config = self._strategies[strategy]

        return {
            "strategy": strategy.value,
            "name": config.name,
            "severity_threshold": config.severity_threshold.value,
            "enable_fast_rules": config.enable_fast_rules,
            "enable_hybrid_rules": config.enable_hybrid_rules,
            "enable_precise_rules": config.enable_precise_rules,
            "timeout_multiplier": config.timeout_multiplier,
        }
