"""
Rewritten base rules (new format)
"""
from typing import List
import re
from ..interfaces import Rule, RuleMetadata, RuleSeverity, RuleCategory, Finding
from ..context import RuleContext
from ..adapters.decorators import rule


class NoGlobalScopeRule(Rule):
    """Prohibit using GlobalScope rule"""
    
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="no_globalscope",
            name="Prohibit GlobalScope usage",
            description="GlobalScope.launch may cause memory leaks, should use lifecycle-aware coroutine scopes",
            severity=RuleSeverity.CRITICAL,
            category=RuleCategory.LIFECYCLE,
            tags=["android", "kotlin", "coroutine", "lifecycle"],
            weight=1.5,
            suggested_fix="Use viewModelScope, lifecycleScope or custom CoroutineScope instead of GlobalScope",
            reference_url="https://developer.android.com/kotlin/coroutines/coroutines-best-practices"
        )
    
    def check(self, context: RuleContext) -> List[Finding]:
        findings = []
        
        # Find GlobalScope.launch
        line_numbers = context.find_pattern_in_lines("GlobalScope.launch", case_sensitive=False)
        
        for line_number in line_numbers:
            code_line = context.get_line_at(line_number)
            
            findings.append(Finding(
                rule_id=self.metadata.id,
                message=self.metadata.description,
                severity=self.metadata.severity,
                file_path=context.file_path,
                line_number=line_number,
                code_snippet=code_line,
                suggestion=self.metadata.suggested_fix
            ))
        
        return findings


@rule(
    rule_id="viewmodel_context",
    name="ViewModel should not hold Context",
    description="ViewModel should not directly hold Android Context, which may cause memory leaks",
    severity=RuleSeverity.MAJOR,
    category=RuleCategory.LIFECYCLE,
    tags=["android", "kotlin", "viewmodel", "context"],
    suggested_fix="Use Application Context or get Context through AndroidViewModel",
    weight=1.2
)
def viewmodel_context_rule(context: RuleContext) -> List[Finding]:
    """ViewModel holding Context detection rule"""
    findings = []
    
    # Check if ViewModel class holds Context
    lines = context.get_lines(normalized=True)
    
    in_viewmodel = False
    for i, line in enumerate(lines, 1):
        # Detect ViewModel class definition
        if "class" in line and "ViewModel" in line and (":" in line or "extends" in line):
            in_viewmodel = True
            continue
        
        if in_viewmodel:
            # Check if contains Context parameter
            if "Context" in line and ("val " in line or "var " in line):
                findings.append(Finding(
                    rule_id="viewmodel_context",
                    message="ViewModel should not directly hold Android Context",
                    severity=RuleSeverity.MAJOR,
                    file_path=context.file_path,
                    line_number=i,
                    code_snippet=line,
                    suggestion="Use Application Context or get Context through AndroidViewModel"
                ))
    
    return findings


@rule(
    rule_id="main_thread_io",
    name="Main thread IO operation",
    description="Executing IO operations on main thread may cause ANR (Application Not Responding)",
    severity=RuleSeverity.CRITICAL,
    category=RuleCategory.PERFORMANCE,
    tags=["android", "kotlin", "coroutine", "io", "anr"]
)
def main_thread_io_rule(context: RuleContext) -> List[Finding]:
    """Main thread IO operation detection"""
    findings = []
    
    # Simplified detection: if contains Dispatchers.Main and has IO related operations
    has_main_dispatcher = any(
        "Dispatchers.Main" in line or "Dispatchers.Main" in line.upper()
        for line in context.get_lines()
    )
    
    has_io_operation = any(
        keyword in line.lower()
        for line in context.get_lines()
        for keyword in ["read", "write", "file", "network", "database", "sharedpreferences"]
    )
    
    if has_main_dispatcher and has_io_operation:
        findings.append(Finding(
            rule_id="main_thread_io",
            message="Detected risk of executing IO operations on main thread",
            severity=RuleSeverity.CRITICAL,
            file_path=context.file_path,
            suggestion="Move IO operations to Dispatchers.IO or background thread"
        ))
    
    return findings


# Backward compatible alias
def run_base_rules(code: str) -> List[dict]:
    """
    Legacy rule function for backward compatibility
    
    Args:
        code: code content
        
    Returns:
        list of findings (old format)
    """
    findings = []
    
    # GlobalScope detection
    if "GlobalScope.launch" in code:
        findings.append({
            "severity": "critical",
            "rule": "no_globalscope",
            "message": "GlobalScope is lifecycle unsafe."
        })
    
    # ViewModel holding Context
    pattern = r"class\s+\w+ViewModel.*Context"
    if re.search(pattern, code):
        findings.append({
            "severity": "major",
            "rule": "viewmodel_context",
            "message": "ViewModel should not hold Android Context."
        })
    
    return findings
