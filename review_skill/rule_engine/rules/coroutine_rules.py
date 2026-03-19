"""
Coroutine-related rules - Migrated to new engine format
"""
from typing import List
from ..interfaces import Rule, RuleMetadata, RuleSeverity, RuleCategory, Finding
from ..context import RuleContext
from ..adapters.decorators import rule


@rule(
    rule_id="coroutine_main_thread_io",
    name="Coroutine main thread IO operation",
    description="Executing IO operations in coroutine main thread may cause ANR (Application Not Responding)",
    severity=RuleSeverity.CRITICAL,
    category=RuleCategory.PERFORMANCE,
    tags=["android", "kotlin", "coroutine", "io", "anr"],
    suggested_fix="Move IO operations to Dispatchers.IO or background thread",
    weight=1.0
)
def coroutine_main_thread_io_rule(context: RuleContext) -> List[Finding]:
    """Coroutine main thread IO operation detection"""
    findings = []
    
    # Simplified detection: if contains Dispatchers.Main and has IO related operations
    lines = context.get_lines()
    has_main_dispatcher = False
    has_io_operation = False
    
    for i, line in enumerate(lines, 1):
        line_lower = line.lower()
        if "dispatchers.main" in line.lower():
            has_main_dispatcher = True
        
        io_keywords = ["read", "write", "file", "network", "database", "sharedpreferences", "repository"]
        if any(keyword in line_lower for keyword in io_keywords):
            has_io_operation = True
            
            # If found IO operation and main thread dispatcher, record specific location
            if has_main_dispatcher:
                findings.append(Finding(
                    rule_id="coroutine_main_thread_io",
                    message="Detected risk of executing IO operations in coroutine main thread",
                    severity=RuleSeverity.CRITICAL,
                    file_path=context.file_path,
                    line_number=i,
                    code_snippet=line,
                    suggestion="Move IO operations to Dispatchers.IO or background thread"
                ))
    
    # General detection (if specific line not found)
    if has_main_dispatcher and has_io_operation and not findings:
        findings.append(Finding(
            rule_id="coroutine_main_thread_io",
            message="Detected risk of executing IO operations in coroutine main thread",
            severity=RuleSeverity.CRITICAL,
            file_path=context.file_path,
            suggestion="Move IO operations to Dispatchers.IO or background thread"
        ))
    
    return findings


@rule(
    rule_id="unspecified_scope",
    name="Unspecified coroutine scope",
    description="Coroutine launch without specifying lifecycle scope",
    severity=RuleSeverity.MINOR,
    category=RuleCategory.LIFECYCLE,
    tags=["android", "kotlin", "coroutine", "lifecycle"],
    suggested_fix="Explicitly specify coroutine scope, such as viewModelScope or lifecycleScope",
    weight=0.8
)
def unspecified_scope_rule(context: RuleContext) -> List[Finding]:
    """Unspecified coroutine scope detection"""
    findings = []
    
    lines = context.get_lines()
    for i, line in enumerate(lines, 1):
        line_stripped = line.strip()
        
        # Check if contains launch { but no scope specified
        if "launch {" in line_stripped or line_stripped.startswith("launch {") or "launch(" in line_stripped:
            # Check if explicit scope exists
            if not any(scope in line_stripped for scope in ["viewModelScope", "lifecycleScope", "GlobalScope", "coroutineScope"]):
                findings.append(Finding(
                    rule_id="unspecified_scope",
                    message="Coroutine launch without specifying lifecycle scope",
                    severity=RuleSeverity.MINOR,
                    file_path=context.file_path,
                    line_number=i,
                    code_snippet=line,
                    suggestion="Explicitly specify coroutine scope, such as viewModelScope or lifecycleScope"
                ))
    
    return findings


__all__ = ["coroutine_main_thread_io_rule", "unspecified_scope_rule"]
