"""Flow Lifecycle Related Rules - 
"""
from typing import List
from ..interfaces import Rule, RuleMetadata, RuleSeverity, RuleCategory, Finding
from ..context import RuleContext
from ..adapters.decorators import rule


@rule(
    rule_id="statein_globalscope",
    name="StateFlow.stateIn 使用 GlobalScope",
    description="在 StateFlow.stateIn() 中使用 GlobalScope 会导致内存泄漏，因为 StateFlow 的生命周期与 GlobalScope 绑定，无法自动清理",
    severity=RuleSeverity.CRITICAL,
    category=RuleCategory.LIFECYCLE,
    tags=["android", "kotlin", "flow", "stateflow", "globalscope", "memory_leak"],
    suggested_fix="使用 viewModelScope 或 lifecycleScope 替代 GlobalScope，确保 StateFlow 在生命周期结束时自动清理",
    weight=1.0
)
def statein_globalscope_rule(context: RuleContext) -> List[Finding]:
    """stateIn(GlobalScope)"""
    findings = []
    
    lines = context.get_lines()
    for i, line in enumerate(lines, 1):
        if "statein(globalscope" in line.lower():
            findings.append(Finding(
                rule_id="statein_globalscope",
                message="StateFlowGlobalScope",
                severity=RuleSeverity.CRITICAL,
                file_path=context.file_path,
                line_number=i,
                code_snippet=line,
                suggestion="viewModelScopelifecycleScopeGlobalScope"
            ))
    
    return findings


@rule(
    rule_id="sharein_globalscope",
    name="SharedFlow.shareIn 使用 GlobalScope",
    description="在 SharedFlow.shareIn() 中使用 GlobalScope 会导致内存泄漏，因为 SharedFlow 的生命周期与 GlobalScope 绑定，无法自动清理",
    severity=RuleSeverity.CRITICAL,
    category=RuleCategory.LIFECYCLE,
    tags=["android", "kotlin", "flow", "sharedflow", "globalscope", "memory_leak"],
    suggested_fix="使用 viewModelScope 或 lifecycleScope 替代 GlobalScope，确保 SharedFlow 在生命周期结束时自动清理",
    weight=1.0
)
def sharein_globalscope_rule(context: RuleContext) -> List[Finding]:
    """shareIn(GlobalScope)"""
    findings = []
    
    lines = context.get_lines()
    for i, line in enumerate(lines, 1):
        if "sharein(globalscope" in line.lower():
            findings.append(Finding(
                rule_id="sharein_globalscope",
                message="SharedFlowGlobalScope",
                severity=RuleSeverity.CRITICAL,
                file_path=context.file_path,
                line_number=i,
                code_snippet=line,
                suggestion="viewModelScopelifecycleScopeGlobalScope"
            ))
    
    return findings


@rule(
    rule_id="collect_without_repeat",
    name="UI 层 Flow collect 缺少 repeatOnLifecycle",
    description="在 Activity/Fragment/Composable 中直接使用 collect 收集 Flow，当应用进入后台时仍会接收事件，可能导致崩溃或资源浪费",
    severity=RuleSeverity.MAJOR,
    category=RuleCategory.LIFECYCLE,
    tags=["android", "kotlin", "flow", "collect", "lifecycle", "ui"],
    suggested_fix="使用 repeatOnLifecycle 包装 collect，确保只在生命周期处于特定状态时接收事件",
    weight=0.9
)
def collect_without_repeat_rule(context: RuleContext) -> List[Finding]:
    """collectrepeatOnLifecycle"""
    findings = []
    
    lines = context.get_lines()
    in_ui_layer = False
    has_collect = False
    
    for i, line in enumerate(lines, 1):
        line_lower = line.lower()
        # UI（Activity/Fragment/Compose）
        if any(keyword in line_lower for keyword in ["activity", "fragment", "composable", "@composable"]):
            in_ui_layer = True
        
        # collect
        if "collect {" in line_lower:
            has_collect = True
            if in_ui_layer and "repeatonlifecycle" not in line_lower:
                # CheckrepeatOnLifecycle
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
                        message="UIcollect FlowrepeatOnLifecycle",
                        severity=RuleSeverity.MAJOR,
                        file_path=context.file_path,
                        line_number=i,
                        code_snippet=line,
                        suggestion="repeatOnLifecyclecollect"
                    ))
    
    return findings


@rule(
    rule_id="statein_without_viewmodelscope",
    name="ViewModel 中 stateIn 未使用 viewModelScope",
    description="在 ViewModel 中使用 stateIn 转换 Flow 时，应传入 viewModelScope 作为作用域，以确保与 ViewModel 生命周期绑定",
    severity=RuleSeverity.MAJOR,
    category=RuleCategory.LIFECYCLE,
    tags=["android", "kotlin", "flow", "viewmodel", "scope"],
    suggested_fix="在 ViewModel 中使用 stateIn(viewModelScope) 替代其他作用域",
    weight=0.8
)
def statein_without_viewmodelscope_rule(context: RuleContext) -> List[Finding]:
    """ViewModelstateInviewModelScope"""
    findings = []
    
    lines = context.get_lines()
    in_viewmodel = False
    
    for i, line in enumerate(lines, 1):
        line_lower = line.lower()
        # ViewModel
        if "viewmodel" in line_lower or ": viewmodel" in line_lower:
            in_viewmodel = True
        
        # stateIn
        if in_viewmodel and "statein(" in line_lower:
            if "viewmodelscope" not in line_lower:
                findings.append(Finding(
                    rule_id="statein_without_viewmodelscope",
                    message="ViewModelstateInviewModelScope",
                    severity=RuleSeverity.MAJOR,
                    file_path=context.file_path,
                    line_number=i,
                    code_snippet=line,
                    suggestion="ViewModelstateIn(viewModelScope)"
                ))
    
    return findings


__all__ = [
    "statein_globalscope_rule",
    "sharein_globalscope_rule",
    "collect_without_repeat_rule",
    "statein_without_viewmodelscope_rule"
]