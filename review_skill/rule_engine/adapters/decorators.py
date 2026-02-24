"""
规则装饰器，用于简化规则定义
"""
from functools import wraps
from typing import Callable, List, Optional, Dict, Any
from ..interfaces import Rule, RuleMetadata, RuleSeverity, RuleCategory, Finding
from ..context import RuleContext


def rule(
    rule_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    severity: RuleSeverity = RuleSeverity.MINOR,
    category: RuleCategory = RuleCategory.CORRECTNESS,
    enabled: bool = True,
    weight: float = 1.0,
    tags: Optional[List[str]] = None,
    **kwargs
):
    """
    规则装饰器，将函数转换为Rule对象
    
    Args:
        rule_id: 规则ID
        name: 规则名称（默认使用rule_id转换）
        description: 规则描述
        severity: 严重级别
        category: 规则分类
        enabled: 是否启用
        weight: 权重
        tags: 标签列表
        **kwargs: 其他RuleMetadata参数
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable[[RuleContext], List[Finding]]):
        """实际的装饰器"""
        
        class FunctionRule(Rule):
            """函数式规则"""
            
            def __init__(self):
                self._metadata = RuleMetadata(
                    id=rule_id,
                    name=name or rule_id.replace("_", " ").title(),
                    description=description or f"规则: {rule_id}",
                    severity=severity,
                    category=category,
                    enabled=enabled,
                    weight=weight,
                    tags=tags or [],
                    **kwargs
                )
            
            @property
            def metadata(self) -> RuleMetadata:
                return self._metadata
            
            def check(self, context: RuleContext) -> List[Finding]:
                return func(context)
        
        # 保存原始函数引用
        FunctionRule._original_func = func
        
        return FunctionRule()
    
    return decorator


def pattern_rule(
    pattern: str,
    rule_id: Optional[str] = None,
    message: Optional[str] = None,
    case_sensitive: bool = True,
    **rule_kwargs
):
    """
    模式匹配规则装饰器
    
    Args:
        pattern: 要匹配的模式
        rule_id: 规则ID（默认自动生成）
        message: 问题描述（默认使用pattern）
        case_sensitive: 是否大小写敏感
        **rule_kwargs: 传递给rule装饰器的参数
        
    Returns:
        装饰器函数
    """
    if rule_id is None:
        # 基于模式生成规则ID
        rule_id = f"pattern_{hash(pattern) % 10000:04d}"
    
    if message is None:
        message = f"代码中包含模式: {pattern}"
    
    @rule(rule_id=rule_id, message=message, **rule_kwargs)
    def pattern_checker(context: RuleContext) -> List[Finding]:
        findings = []
        
        # 查找模式
        line_numbers = context.find_pattern_in_lines(pattern, case_sensitive)
        
        for line_number in line_numbers:
            code_line = context.get_line_at(line_number)
            
            findings.append(Finding(
                rule_id=rule_id,
                message=message,
                severity=rule_kwargs.get("severity", RuleSeverity.MINOR),
                file_path=context.file_path,
                line_number=line_number,
                code_snippet=code_line
            ))
        
        return findings
    
    return pattern_checker