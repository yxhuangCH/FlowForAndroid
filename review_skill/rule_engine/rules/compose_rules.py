"""Compose Related Rules - Migrated to new engine format
"""
from typing import List
from ..interfaces import Rule, RuleMetadata, RuleSeverity, RuleCategory, Finding
from ..context import RuleContext
from ..adapters.decorators import rule


@rule(
    rule_id="launched_effect_unit",
    name="LaunchedEffect(Unit) Issue",
    description="LaunchedEffect(Unit) may cause unnecessary recompositions",
    severity=RuleSeverity.MINOR,
    category=RuleCategory.CORRECTNESS,
    tags=["android", "compose", "kotlin"],
    suggested_fix="Use appropriate key parameter instead of Unit to avoid unnecessary recompositions",
    weight=0.7
)
def launched_effect_unit_rule(context: RuleContext) -> List[Finding]:
    """LaunchedEffect(Unit) detection"""
    findings = []
    
    lines = context.get_lines()
    for i, line in enumerate(lines, 1):
        if "LaunchedEffect(Unit)" in line:
            findings.append(Finding(
                rule_id="launched_effect_unit",
                message="LaunchedEffect(Unit) may cause unnecessary recompositions",
                severity=RuleSeverity.MINOR,
                file_path=context.file_path,
                line_number=i,
                code_snippet=line,
                suggestion="Use appropriate key parameter instead of Unit to avoid unnecessary recompositions"
            ))
    
    return findings


@rule(
    rule_id="remember_context",
    name="remember holding Context",
    description="Holding Context in remember may cause memory leaks",
    severity=RuleSeverity.MAJOR,
    category=RuleCategory.LIFECYCLE,
    tags=["android", "compose", "kotlin", "context"],
    suggested_fix="Avoid holding Context in remember, consider using ViewModel or other approaches",
    weight=1.0
)
def remember_context_rule(context: RuleContext) -> List[Finding]:
    """remember holding Context detection"""
    findings = []
    
    lines = context.get_lines()
    in_remember_block = False
    block_start_line = 0
    
    for i, line in enumerate(lines, 1):
        line_lower = line.lower()
        
        # Detect remember { block start
        if "remember {" in line_lower:
            in_remember_block = True
            block_start_line = i
            # Check if same line contains context
            if "context" in line_lower:
                findings.append(Finding(
                    rule_id="remember_context",
                    message="Holding Context in remember may cause memory leaks",
                    severity=RuleSeverity.MAJOR,
                    file_path=context.file_path,
                    line_number=i,
                    code_snippet=line,
                    suggestion="Avoid holding Context in remember, consider using ViewModel or other approaches"
                ))
                in_remember_block = False
        
        # Detect context inside remember block
        elif in_remember_block:
            if "context" in line_lower:
                findings.append(Finding(
                    rule_id="remember_context",
                    message="Holding Context in remember may cause memory leaks",
                    severity=RuleSeverity.MAJOR,
                    file_path=context.file_path,
                    line_number=i,
                    code_snippet=line,
                    suggestion="Avoid holding Context in remember, consider using ViewModel or other approaches"
                ))
            
            # Detect block end
            if line.strip() == "}":
                in_remember_block = False
    
    return findings


__all__ = ["launched_effect_unit_rule", "remember_context_rule"]
