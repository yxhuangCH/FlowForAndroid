"""
Hilt Rules for Unified Engine

Hilt 依赖注入相关规则 - 使用 FAST 模式
"""
from typing import List
from unified_engine.interfaces import UnifiedRule, ExecutionMode, RuleMetadata, Finding, RuleSeverity, RuleCategory
from unified_engine.context import UnifiedContext


__all__ = [
    "SingletonActivityRule",
]


class SingletonActivityRule(UnifiedRule):
    """
    @Singleton 注入到 Activity 作用域检测规则

    @Singleton 组件注入到 Activity 作用域可能导致生命周期不匹配。
    """

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="singleton_activity",
            name="@Singleton injected into Activity scope",
            description="@Singleton component injected into Activity scope may cause lifecycle mismatch",
            severity=RuleSeverity.MAJOR,
            category=RuleCategory.LIFECYCLE,
            tags=["android", "kotlin", "hilt", "di", "singleton", "activity", "lifecycle"],
            weight=0.9,
            suggested_fix="Consider using @ActivityScoped instead of @Singleton, or redesign dependencies",
            reference_url=""
        )

    execution_mode = ExecutionMode.FAST

    def check(self, context: UnifiedContext) -> List[Finding]:
        """Detect @Singleton injected into Activity scope"""
        findings = []

        lines = context.get_lines()
        has_singleton = False
        has_activity = False
        singleton_line = 0

        for i, line in enumerate(lines, 1):
            line_lower = line.lower()

            # Detect @Singleton
            if "@singleton" in line_lower:
                has_singleton = True
                singleton_line = i

            # Detect Activity
            if "activity" in line_lower and ("class " in line_lower or ": activity" in line_lower):
                has_activity = True

            # If both @Singleton and Activity exist
            if has_singleton and has_activity:
                findings.append(Finding(
                    rule_id=self.metadata.id,
                    message="@Singleton component injected into Activity scope may cause lifecycle mismatch",
                    severity=self.metadata.severity,
                    file_path=context.file_path,
                    line_number=singleton_line,
                    code_snippet=line,
                    suggestion=self.metadata.suggested_fix
                ))
                break

        return findings


def get_rules() -> List[UnifiedRule]:
    """返回此模块中的所有规则"""
    return [
        SingletonActivityRule(),
    ]
