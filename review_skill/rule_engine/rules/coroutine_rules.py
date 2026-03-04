"""
协程相关规则 - 迁移到新引擎格式
"""
from typing import List
from ..interfaces import Rule, RuleMetadata, RuleSeverity, RuleCategory, Finding
from ..context import RuleContext
from ..adapters.decorators import rule


@rule(
    rule_id="coroutine_main_thread_io",
    name="协程主线程IO操作",
    description="在协程主线程执行IO操作可能导致ANR（应用无响应）",
    severity=RuleSeverity.CRITICAL,
    category=RuleCategory.PERFORMANCE,
    tags=["android", "kotlin", "coroutine", "io", "anr"],
    suggested_fix="将IO操作移到Dispatchers.IO或后台线程",
    weight=1.0
)
def coroutine_main_thread_io_rule(context: RuleContext) -> List[Finding]:
    """协程主线程IO操作检测"""
    findings = []
    
    # 简化检测：如果包含Dispatchers.Main并且有IO相关操作
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
            
            # 如果找到IO操作和主线程调度器，记录具体位置
            if has_main_dispatcher:
                findings.append(Finding(
                    rule_id="coroutine_main_thread_io",
                    message="检测到在协程主线程执行IO操作的风险",
                    severity=RuleSeverity.CRITICAL,
                    file_path=context.file_path,
                    line_number=i,
                    code_snippet=line,
                    suggestion="将IO操作移到Dispatchers.IO或后台线程"
                ))
    
    # 通用检测（如果没有找到具体行）
    if has_main_dispatcher and has_io_operation and not findings:
        findings.append(Finding(
            rule_id="coroutine_main_thread_io",
            message="检测到在协程主线程执行IO操作的风险",
            severity=RuleSeverity.CRITICAL,
            file_path=context.file_path,
            suggestion="将IO操作移到Dispatchers.IO或后台线程"
        ))
    
    return findings


@rule(
    rule_id="unspecified_scope",
    name="未指定协程作用域",
    description="协程启动未指定生命周期作用域",
    severity=RuleSeverity.MINOR,
    category=RuleCategory.LIFECYCLE,
    tags=["android", "kotlin", "coroutine", "lifecycle"],
    suggested_fix="明确指定协程作用域，如viewModelScope或lifecycleScope",
    weight=0.8
)
def unspecified_scope_rule(context: RuleContext) -> List[Finding]:
    """未指定协程作用域检测"""
    findings = []
    
    lines = context.get_lines()
    for i, line in enumerate(lines, 1):
        line_stripped = line.strip()
        
        # 检查是否包含launch { 但没有指定作用域
        if "launch {" in line_stripped or line_stripped.startswith("launch {") or "launch(" in line_stripped:
            # 检查是否有明确的作用域
            if not any(scope in line_stripped for scope in ["viewModelScope", "lifecycleScope", "GlobalScope", "coroutineScope"]):
                findings.append(Finding(
                    rule_id="unspecified_scope",
                    message="协程启动未指定生命周期作用域",
                    severity=RuleSeverity.MINOR,
                    file_path=context.file_path,
                    line_number=i,
                    code_snippet=line,
                    suggestion="明确指定协程作用域，如viewModelScope或lifecycleScope"
                ))
    
    return findings


__all__ = ["coroutine_main_thread_io_rule", "unspecified_scope_rule"]
