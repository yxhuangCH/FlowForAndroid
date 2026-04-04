"""
Dagger2Rule - 
"""
import re
from typing import List
from ..interfaces import Rule, RuleMetadata, RuleSeverity, RuleCategory, Finding
from ..context import RuleContext
from ..adapters.decorators import rule


@rule(
    rule_id="singleton_component_inject_activity",
    name="@Singleton 与 ComponentActivity 生命周期不匹配",
    description="使用 @Singleton 作用域注入 Component/Activity 会导致生命周期不匹配，单例对象持有 Activity 引用会造成内存泄漏",
    severity=RuleSeverity.MAJOR,
    category=RuleCategory.LIFECYCLE,
    tags=["android", "kotlin", "dagger2", "di", "singleton", "component", "activity", "lifecycle"],
    suggested_fix="使用 @ActivityScoped 或 @FragmentScoped 替代 @Singleton 来注入 Activity",
    weight=0.9
)
def singleton_component_inject_activity_rule(context: RuleContext) -> List[Finding]:
    """@Singleton ComponentActivity"""
    findings = []
    
    lines = context.get_lines()
    has_singleton_component = False
    has_activity = False
    singleton_component_line = 0
    
    for i, line in enumerate(lines, 1):
        line_lower = line.lower()
        
        # @Singleton@Component
        if "@singleton" in line_lower and "@component" in line_lower:
            has_singleton_component = True
            singleton_component_line = i
        
        # Activity
        if "activity" in line_lower and ("class " in line_lower or ": activity" in line_lower):
            has_activity = True
        
        # @Singleton @ComponentActivity
        if has_singleton_component and has_activity:
            findings.append(Finding(
                rule_id="singleton_component_inject_activity",
                message="@Singleton ComponentActivity",
                severity=RuleSeverity.MAJOR,
                file_path=context.file_path,
                line_number=singleton_component_line,
                code_snippet=line,
                suggestion=""
            ))
            break
    
    return findings


@rule(
    rule_id="field_injection_detected",
    name="检测到字段注入",
    description="使用 @Inject lateinit var 进行字段注入不利于测试和维护，推荐使用构造函数注入",
    severity=RuleSeverity.MINOR,
    category=RuleCategory.BEST_PRACTICE,
    tags=["android", "kotlin", "dagger2", "di", "field_injection", "constructor_injection"],
    suggested_fix="将字段注入改为构造函数注入，提高可测试性和代码清晰度",
    weight=0.7
)
def field_injection_detected_rule(context: RuleContext) -> List[Finding]:
    """"""
    findings = []
    
    lines = context.get_lines()
    
    for i, line in enumerate(lines, 1):
        line_lower = line.lower()
        # @Inject lateinit var
        if "@inject" in line_lower and "lateinit" in line_lower and "var" in line_lower:
            # 
            pattern = r"@Inject\s+lateinit\s+var"
            if re.search(pattern, line, re.IGNORECASE):
                findings.append(Finding(
                    rule_id="field_injection_detected",
                    message="（@Inject lateinit var），",
                    severity=RuleSeverity.MINOR,
                    file_path=context.file_path,
                    line_number=i,
                    code_snippet=line,
                    suggestion=""
                ))
    
    return findings


@rule(
    rule_id="provides_without_scope",
    name="@Provides 方法缺少作用域",
    description="@Provides 方法未指定作用域（如 @Singleton），每次注入都会创建新实例，可能导致不必要的对象创建",
    severity=RuleSeverity.MINOR,
    category=RuleCategory.BEST_PRACTICE,
    tags=["android", "kotlin", "dagger2", "di", "provides", "scope"],
    suggested_fix="为 @Provides 方法添加合适的作用域注解，如 @Singleton、@ActivityScoped 等",
    weight=0.6
)
def provides_without_scope_rule(context: RuleContext) -> List[Finding]:
    """@Provides"""
    findings = []
    
    lines = context.get_lines()
    provides_line = 0
    in_provides_method = False
    
    for i, line in enumerate(lines, 1):
        line_lower = line.lower()
        
        # @Provides
        if "@provides" in line_lower:
            in_provides_method = True
            provides_line = i
        
        # @Provides
        if in_provides_method:
            # （fun）
            if "fun " in line_lower or "def " in line_lower:
                # Check（@Singleton, @ActivityScoped, etc.)
                has_scope = any(scope in line_lower for scope in ["@singleton", "@activityscoped", "@fragmentscoped", "@viewmodelscoped"])
                
                if not has_scope:
                    # Check
                    has_scope_nearby = False
                    start = max(0, i - 3)
                    for j in range(start, i):
                        if any(scope in lines[j].lower() for scope in ["@singleton", "@activityscoped", "@fragmentscoped", "@viewmodelscoped"]):
                            has_scope_nearby = True
                            break
                    
                    if not has_scope_nearby:
                        findings.append(Finding(
                            rule_id="provides_without_scope",
                            message="@Provides",
                            severity=RuleSeverity.MINOR,
                            file_path=context.file_path,
                            line_number=provides_line,
                            code_snippet=line,
                            suggestion="@ProvidesAdd，@Singleton"
                        ))
                
                in_provides_method = False
    
    return findings


__all__ = [
    "singleton_component_inject_activity_rule",
    "field_injection_detected_rule",
    "provides_without_scope_rule"
]