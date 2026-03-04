"""
Dagger2依赖注入相关规则 - 迁移到新引擎格式
"""
import re
from typing import List
from ..interfaces import Rule, RuleMetadata, RuleSeverity, RuleCategory, Finding
from ..context import RuleContext
from ..adapters.decorators import rule


@rule(
    rule_id="singleton_component_inject_activity",
    name="@Singleton Component注入Activity",
    description="@Singleton Component注入Activity可能导致生命周期不匹配",
    severity=RuleSeverity.MAJOR,
    category=RuleCategory.LIFECYCLE,
    tags=["android", "kotlin", "dagger2", "di", "singleton", "component", "activity", "lifecycle"],
    suggested_fix="考虑使用自定义作用域或重新设计组件结构",
    weight=0.9
)
def singleton_component_inject_activity_rule(context: RuleContext) -> List[Finding]:
    """检测@Singleton Component注入Activity"""
    findings = []
    
    lines = context.get_lines()
    has_singleton_component = False
    has_activity = False
    singleton_component_line = 0
    
    for i, line in enumerate(lines, 1):
        line_lower = line.lower()
        
        # 检测@Singleton和@Component同时存在
        if "@singleton" in line_lower and "@component" in line_lower:
            has_singleton_component = True
            singleton_component_line = i
        
        # 检测Activity
        if "activity" in line_lower and ("class " in line_lower or ": activity" in line_lower):
            has_activity = True
        
        # 如果同时存在@Singleton @Component和Activity
        if has_singleton_component and has_activity:
            findings.append(Finding(
                rule_id="singleton_component_inject_activity",
                message="@Singleton Component注入Activity可能导致生命周期不匹配",
                severity=RuleSeverity.MAJOR,
                file_path=context.file_path,
                line_number=singleton_component_line,
                code_snippet=line,
                suggestion="考虑使用自定义作用域或重新设计组件结构"
            ))
            break
    
    return findings


@rule(
    rule_id="field_injection_detected",
    name="字段注入检测",
    description="检测到字段注入（@Inject lateinit var），建议使用构造函数注入",
    severity=RuleSeverity.MINOR,
    category=RuleCategory.BEST_PRACTICE,
    tags=["android", "kotlin", "dagger2", "di", "field_injection", "constructor_injection"],
    suggested_fix="使用构造函数注入替代字段注入",
    weight=0.7
)
def field_injection_detected_rule(context: RuleContext) -> List[Finding]:
    """检测字段注入"""
    findings = []
    
    lines = context.get_lines()
    
    for i, line in enumerate(lines, 1):
        line_lower = line.lower()
        # 检测@Inject lateinit var模式
        if "@inject" in line_lower and "lateinit" in line_lower and "var" in line_lower:
            # 使用正则表达式更精确匹配
            pattern = r"@Inject\s+lateinit\s+var"
            if re.search(pattern, line, re.IGNORECASE):
                findings.append(Finding(
                    rule_id="field_injection_detected",
                    message="检测到字段注入（@Inject lateinit var），建议使用构造函数注入",
                    severity=RuleSeverity.MINOR,
                    file_path=context.file_path,
                    line_number=i,
                    code_snippet=line,
                    suggestion="使用构造函数注入替代字段注入"
                ))
    
    return findings


@rule(
    rule_id="provides_without_scope",
    name="@Provides方法未指定作用域",
    description="@Provides方法未指定作用域可能导致创建多个实例",
    severity=RuleSeverity.MINOR,
    category=RuleCategory.BEST_PRACTICE,
    tags=["android", "kotlin", "dagger2", "di", "provides", "scope"],
    suggested_fix="为@Provides方法添加适当的作用域注解，如@Singleton或自定义作用域",
    weight=0.6
)
def provides_without_scope_rule(context: RuleContext) -> List[Finding]:
    """检测@Provides方法未指定作用域"""
    findings = []
    
    lines = context.get_lines()
    provides_line = 0
    in_provides_method = False
    
    for i, line in enumerate(lines, 1):
        line_lower = line.lower()
        
        # 检测@Provides开始
        if "@provides" in line_lower:
            in_provides_method = True
            provides_line = i
        
        # 如果在@Provides方法内
        if in_provides_method:
            # 检测方法定义（包含fun关键字）
            if "fun " in line_lower or "def " in line_lower:
                # 检查是否有作用域注解（@Singleton, @ActivityScoped等）
                has_scope = any(scope in line_lower for scope in ["@singleton", "@activityscoped", "@fragmentscoped", "@viewmodelscoped"])
                
                if not has_scope:
                    # 检查前几行是否有作用域注解
                    has_scope_nearby = False
                    start = max(0, i - 3)
                    for j in range(start, i):
                        if any(scope in lines[j].lower() for scope in ["@singleton", "@activityscoped", "@fragmentscoped", "@viewmodelscoped"]):
                            has_scope_nearby = True
                            break
                    
                    if not has_scope_nearby:
                        findings.append(Finding(
                            rule_id="provides_without_scope",
                            message="@Provides方法未指定作用域可能导致创建多个实例",
                            severity=RuleSeverity.MINOR,
                            file_path=context.file_path,
                            line_number=provides_line,
                            code_snippet=line,
                            suggestion="为@Provides方法添加适当的作用域注解，如@Singleton或自定义作用域"
                        ))
                
                in_provides_method = False
    
    return findings


__all__ = [
    "singleton_component_inject_activity_rule",
    "field_injection_detected_rule",
    "provides_without_scope_rule"
]