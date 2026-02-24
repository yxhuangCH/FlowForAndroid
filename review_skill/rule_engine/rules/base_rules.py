"""
重写的基础规则（新格式）
"""
from typing import List
import re
from ..interfaces import Rule, RuleMetadata, RuleSeverity, RuleCategory, Finding
from ..context import RuleContext
from ..adapters.decorators import rule


class NoGlobalScopeRule(Rule):
    """禁止使用GlobalScope规则"""
    
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="no_globalscope",
            name="禁止使用GlobalScope",
            description="GlobalScope.launch可能导致内存泄漏，应使用生命周期感知的协程作用域",
            severity=RuleSeverity.CRITICAL,
            category=RuleCategory.LIFECYCLE,
            tags=["android", "kotlin", "coroutine", "lifecycle"],
            weight=1.5,
            suggested_fix="使用viewModelScope、lifecycleScope或自定义CoroutineScope替代GlobalScope",
            reference_url="https://developer.android.com/kotlin/coroutines/coroutines-best-practices"
        )
    
    def check(self, context: RuleContext) -> List[Finding]:
        findings = []
        
        # 查找GlobalScope.launch
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
    name="ViewModel不应持有Context",
    description="ViewModel不应直接持有Android Context，这可能导致内存泄漏",
    severity=RuleSeverity.MAJOR,
    category=RuleCategory.LIFECYCLE,
    tags=["android", "kotlin", "viewmodel", "context"],
    suggested_fix="使用Application Context或通过AndroidViewModel获取Context",
    weight=1.2
)
def viewmodel_context_rule(context: RuleContext) -> List[Finding]:
    """ViewModel持有Context检测规则"""
    findings = []
    
    # 检查是否在ViewModel类中持有Context
    lines = context.get_lines(normalized=True)
    
    in_viewmodel = False
    for i, line in enumerate(lines, 1):
        # 检测ViewModel类定义
        if "class" in line and "ViewModel" in line and (":" in line or "extends" in line):
            in_viewmodel = True
            continue
        
        if in_viewmodel:
            # 检查是否包含Context参数
            if "Context" in line and ("val " in line or "var " in line):
                findings.append(Finding(
                    rule_id="viewmodel_context",
                    message="ViewModel不应直接持有Android Context",
                    severity=RuleSeverity.MAJOR,
                    file_path=context.file_path,
                    line_number=i,
                    code_snippet=line,
                    suggestion="使用Application Context或通过AndroidViewModel获取Context"
                ))
    
    return findings


@rule(
    rule_id="main_thread_io",
    name="主线程IO操作",
    description="在主线程执行IO操作可能导致ANR（应用无响应）",
    severity=RuleSeverity.CRITICAL,
    category=RuleCategory.PERFORMANCE,
    tags=["android", "kotlin", "coroutine", "io", "anr"]
)
def main_thread_io_rule(context: RuleContext) -> List[Finding]:
    """主线程IO操作检测"""
    findings = []
    
    # 简化检测：如果包含Dispatchers.Main并且有IO相关操作
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
            message="检测到在主线程执行IO操作的风险",
            severity=RuleSeverity.CRITICAL,
            file_path=context.file_path,
            suggestion="将IO操作移到Dispatchers.IO或后台线程"
        ))
    
    return findings


# 为了向后兼容，保留原始函数
def run_base_rules(code: str) -> List[dict]:
    """
    旧版规则函数，用于向后兼容
    
    Args:
        code: 代码内容
        
    Returns:
        发现的问题列表（旧格式）
    """
    findings = []
    
    # GlobalScope 检测
    if "GlobalScope.launch" in code:
        findings.append({
            "severity": "critical",
            "rule": "no_globalscope",
            "message": "GlobalScope is lifecycle unsafe."
        })
    
    # ViewModel 持有 Context
    pattern = r"class\s+\w+ViewModel.*Context"
    if re.search(pattern, code):
        findings.append({
            "severity": "major",
            "rule": "viewmodel_context",
            "message": "ViewModel should not hold Android Context."
        })
    
    return findings