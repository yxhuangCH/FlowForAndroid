"""
Flow生命周期相关规则 - 迁移到新引擎格式
"""
from typing import List
from ..interfaces import Rule, RuleMetadata, RuleSeverity, RuleCategory, Finding
from ..context import RuleContext
from ..adapters.decorators import rule


@rule(
    rule_id="statein_globalscope",
    name="stateIn使用GlobalScope",
    description="StateFlow使用GlobalScope可能导致内存泄漏",
    severity=RuleSeverity.CRITICAL,
    category=RuleCategory.LIFECYCLE,
    tags=["android", "kotlin", "flow", "stateflow", "globalscope", "memory_leak"],
    suggested_fix="使用viewModelScope或lifecycleScope替代GlobalScope",
    weight=1.0
)
def statein_globalscope_rule(context: RuleContext) -> List[Finding]:
    """检测stateIn(GlobalScope)使用"""
    findings = []
    
    lines = context.get_lines()
    for i, line in enumerate(lines, 1):
        if "statein(globalscope" in line.lower():
            findings.append(Finding(
                rule_id="statein_globalscope",
                message="StateFlow使用GlobalScope可能导致内存泄漏",
                severity=RuleSeverity.CRITICAL,
                file_path=context.file_path,
                line_number=i,
                code_snippet=line,
                suggestion="使用viewModelScope或lifecycleScope替代GlobalScope"
            ))
    
    return findings


@rule(
    rule_id="sharein_globalscope",
    name="shareIn使用GlobalScope",
    description="SharedFlow使用GlobalScope可能导致内存泄漏",
    severity=RuleSeverity.CRITICAL,
    category=RuleCategory.LIFECYCLE,
    tags=["android", "kotlin", "flow", "sharedflow", "globalscope", "memory_leak"],
    suggested_fix="使用viewModelScope或lifecycleScope替代GlobalScope",
    weight=1.0
)
def sharein_globalscope_rule(context: RuleContext) -> List[Finding]:
    """检测shareIn(GlobalScope)使用"""
    findings = []
    
    lines = context.get_lines()
    for i, line in enumerate(lines, 1):
        if "sharein(globalscope" in line.lower():
            findings.append(Finding(
                rule_id="sharein_globalscope",
                message="SharedFlow使用GlobalScope可能导致内存泄漏",
                severity=RuleSeverity.CRITICAL,
                file_path=context.file_path,
                line_number=i,
                code_snippet=line,
                suggestion="使用viewModelScope或lifecycleScope替代GlobalScope"
            ))
    
    return findings


@rule(
    rule_id="collect_without_repeat",
    name="Flow collect未使用repeatOnLifecycle",
    description="UI层collect Flow未使用repeatOnLifecycle可能导致生命周期问题",
    severity=RuleSeverity.MAJOR,
    category=RuleCategory.LIFECYCLE,
    tags=["android", "kotlin", "flow", "collect", "lifecycle", "ui"],
    suggested_fix="使用repeatOnLifecycle包装collect操作",
    weight=0.9
)
def collect_without_repeat_rule(context: RuleContext) -> List[Finding]:
    """检测collect未使用repeatOnLifecycle"""
    findings = []
    
    lines = context.get_lines()
    in_ui_layer = False
    has_collect = False
    
    for i, line in enumerate(lines, 1):
        line_lower = line.lower()
        # 检测是否在UI层（Activity/Fragment/Compose）
        if any(keyword in line_lower for keyword in ["activity", "fragment", "composable", "@composable"]):
            in_ui_layer = True
        
        # 检测collect操作
        if "collect {" in line_lower:
            has_collect = True
            if in_ui_layer and "repeatonlifecycle" not in line_lower:
                # 检查前几行是否有repeatOnLifecycle
                has_repeat_nearby = False
                start = max(0, i - 3)
                end = min(len(lines), i + 1)
                for j in range(start, end):
                    if j != i and "repeatonlifecycle" in lines[j].lower():
                        has_repeat_nearby = True
                        break
                
                if not has_repeat_nearby:
                    findings.append(Finding(
                        rule_id="collect_without_repeat",
                        message="UI层collect Flow未使用repeatOnLifecycle可能导致生命周期问题",
                        severity=RuleSeverity.MAJOR,
                        file_path=context.file_path,
                        line_number=i,
                        code_snippet=line,
                        suggestion="使用repeatOnLifecycle包装collect操作"
                    ))
    
    return findings


@rule(
    rule_id="statein_without_viewmodelscope",
    name="ViewModel中stateIn未使用viewModelScope",
    description="ViewModel中使用stateIn但未指定viewModelScope",
    severity=RuleSeverity.MAJOR,
    category=RuleCategory.LIFECYCLE,
    tags=["android", "kotlin", "flow", "viewmodel", "scope"],
    suggested_fix="在ViewModel中使用stateIn(viewModelScope)",
    weight=0.8
)
def statein_without_viewmodelscope_rule(context: RuleContext) -> List[Finding]:
    """检测ViewModel中stateIn未使用viewModelScope"""
    findings = []
    
    lines = context.get_lines()
    in_viewmodel = False
    
    for i, line in enumerate(lines, 1):
        line_lower = line.lower()
        # 检测是否在ViewModel中
        if "viewmodel" in line_lower or ": viewmodel" in line_lower:
            in_viewmodel = True
        
        # 检测stateIn使用
        if in_viewmodel and "statein(" in line_lower:
            if "viewmodelscope" not in line_lower:
                findings.append(Finding(
                    rule_id="statein_without_viewmodelscope",
                    message="ViewModel中使用stateIn但未指定viewModelScope",
                    severity=RuleSeverity.MAJOR,
                    file_path=context.file_path,
                    line_number=i,
                    code_snippet=line,
                    suggestion="在ViewModel中使用stateIn(viewModelScope)"
                ))
    
    return findings


__all__ = [
    "statein_globalscope_rule",
    "sharein_globalscope_rule",
    "collect_without_repeat_rule",
    "statein_without_viewmodelscope_rule"
]