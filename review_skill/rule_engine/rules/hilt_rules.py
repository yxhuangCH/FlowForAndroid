"""
Hilt依赖注入相关规则 - 迁移到新引擎格式
"""
from typing import List
from ..interfaces import Rule, RuleMetadata, RuleSeverity, RuleCategory, Finding
from ..context import RuleContext
from ..adapters.decorators import rule


@rule(
    rule_id="singleton_activity",
    name="@Singleton注入到Activity作用域",
    description="@Singleton组件注入到Activity作用域可能导致生命周期不匹配",
    severity=RuleSeverity.MAJOR,
    category=RuleCategory.LIFECYCLE,
    tags=["android", "kotlin", "hilt", "di", "singleton", "activity", "lifecycle"],
    suggested_fix="考虑使用@ActivityScoped替代@Singleton，或重新设计依赖关系",
    weight=0.9
)
def singleton_activity_rule(context: RuleContext) -> List[Finding]:
    """检测@Singleton注入到Activity作用域"""
    findings = []
    
    lines = context.get_lines()
    has_singleton = False
    has_activity = False
    singleton_line = 0
    
    for i, line in enumerate(lines, 1):
        line_lower = line.lower()
        
        # 检测@Singleton
        if "@singleton" in line_lower:
            has_singleton = True
            singleton_line = i
        
        # 检测Activity
        if "activity" in line_lower and ("class " in line_lower or ": activity" in line_lower):
            has_activity = True
        
        # 如果同时存在@Singleton和Activity
        if has_singleton and has_activity:
            findings.append(Finding(
                rule_id="singleton_activity",
                message="@Singleton组件注入到Activity作用域可能导致生命周期不匹配",
                severity=RuleSeverity.MAJOR,
                file_path=context.file_path,
                line_number=singleton_line,
                code_snippet=line,
                suggestion="考虑使用@ActivityScoped替代@Singleton，或重新设计依赖关系"
            ))
            break
    
    return findings


__all__ = ["singleton_activity_rule"]