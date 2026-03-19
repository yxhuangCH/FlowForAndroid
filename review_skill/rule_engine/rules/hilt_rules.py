"""
Hilt dependency injection related rules - Migrated to new engine format
"""
from typing import List
from ..interfaces import Rule, RuleMetadata, RuleSeverity, RuleCategory, Finding
from ..context import RuleContext
from ..adapters.decorators import rule


@rule(
    rule_id="singleton_activity",
    name="@Singleton injected into Activity scope",
    description="@Singleton component injected into Activity scope may cause lifecycle mismatch",
    severity=RuleSeverity.MAJOR,
    category=RuleCategory.LIFECYCLE,
    tags=["android", "kotlin", "hilt", "di", "singleton", "activity", "lifecycle"],
    suggested_fix="Consider using @ActivityScoped instead of @Singleton, or redesign dependencies",
    weight=0.9
)
def singleton_activity_rule(context: RuleContext) -> List[Finding]:
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
                rule_id="singleton_activity",
                message="@Singleton component injected into Activity scope may cause lifecycle mismatch",
                severity=RuleSeverity.MAJOR,
                file_path=context.file_path,
                line_number=singleton_line,
                code_snippet=line,
                suggestion="Consider using @ActivityScoped instead of @Singleton, or redesign dependencies"
            ))
            break
    
    return findings


__all__ = ["singleton_activity_rule"]
