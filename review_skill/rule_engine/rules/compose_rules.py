"""
Compose相关规则 - 迁移到新引擎格式
"""
from typing import List
from ..interfaces import Rule, RuleMetadata, RuleSeverity, RuleCategory, Finding
from ..context import RuleContext
from ..adapters.decorators import rule


@rule(
    rule_id="launched_effect_unit",
    name="LaunchedEffect(Unit)问题",
    description="LaunchedEffect(Unit)可能导致不必要的重新组合",
    severity=RuleSeverity.MINOR,
    category=RuleCategory.CORRECTNESS,
    tags=["android", "compose", "kotlin"],
    suggested_fix="使用合适的key参数替代Unit，避免不必要的重新组合",
    weight=0.7
)
def launched_effect_unit_rule(context: RuleContext) -> List[Finding]:
    """LaunchedEffect(Unit)检测"""
    findings = []
    
    lines = context.get_lines()
    for i, line in enumerate(lines, 1):
        if "LaunchedEffect(Unit)" in line:
            findings.append(Finding(
                rule_id="launched_effect_unit",
                message="LaunchedEffect(Unit)可能导致不必要的重新组合",
                severity=RuleSeverity.MINOR,
                file_path=context.file_path,
                line_number=i,
                code_snippet=line,
                suggestion="使用合适的key参数替代Unit，避免不必要的重新组合"
            ))
    
    return findings


@rule(
    rule_id="remember_context",
    name="remember持有Context",
    description="remember中持有Context可能导致内存泄漏",
    severity=RuleSeverity.MAJOR,
    category=RuleCategory.LIFECYCLE,
    tags=["android", "compose", "kotlin", "context"],
    suggested_fix="避免在remember中持有Context，考虑使用ViewModel或其他方式",
    weight=1.0
)
def remember_context_rule(context: RuleContext) -> List[Finding]:
    """remember持有Context检测"""
    findings = []
    
    lines = context.get_lines()
    in_remember_block = False
    block_start_line = 0
    
    for i, line in enumerate(lines, 1):
        line_lower = line.lower()
        
        # 检测remember { 块开始
        if "remember {" in line_lower:
            in_remember_block = True
            block_start_line = i
            # 检查同一行是否包含context
            if "context" in line_lower:
                findings.append(Finding(
                    rule_id="remember_context",
                    message="remember中持有Context可能导致内存泄漏",
                    severity=RuleSeverity.MAJOR,
                    file_path=context.file_path,
                    line_number=i,
                    code_snippet=line,
                    suggestion="避免在remember中持有Context，考虑使用ViewModel或其他方式"
                ))
                in_remember_block = False
        
        # 在remember块中检测context
        elif in_remember_block:
            if "context" in line_lower:
                findings.append(Finding(
                    rule_id="remember_context",
                    message="remember中持有Context可能导致内存泄漏",
                    severity=RuleSeverity.MAJOR,
                    file_path=context.file_path,
                    line_number=i,
                    code_snippet=line,
                    suggestion="避免在remember中持有Context，考虑使用ViewModel或其他方式"
                ))
            
            # 检测块结束
            if line.strip() == "}":
                in_remember_block = False
    
    return findings


__all__ = ["launched_effect_unit_rule", "remember_context_rule"]