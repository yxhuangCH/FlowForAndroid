"""
Rule decorators for simplifying rule definition
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
    Rule decorator, converts function to Rule object
    
    Args:
        rule_id: Rule ID
        name: Rule name (default: converted from rule_id)
        description: Rule description
        severity: Severity level
        category: Rule category
        enabled: Whether enabled
        weight: Weight
        tags: Tag list
        **kwargs: Other RuleMetadata parameters
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable[[RuleContext], List[Finding]]):
        """Actual decorator"""
        
        class FunctionRule(Rule):
            """Function-based rule"""
            
            def __init__(self):
                self._metadata = RuleMetadata(
                    id=rule_id,
                    name=name or rule_id.replace("_", " ").title(),
                    description=description or f"Rule: {rule_id}",
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
        
        # Save original function reference
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
    Pattern matching rule decorator
    
    Args:
        pattern: Pattern to match
        rule_id: Rule ID (default: auto-generated)
        message: Issue description (default: uses pattern)
        case_sensitive: Whether case sensitive
        **rule_kwargs: Parameters passed to rule decorator
        
    Returns:
        Decorator function
    """
    if rule_id is None:
        # Generate rule ID based on pattern
        rule_id = f"pattern_{hash(pattern) % 10000:04d}"
    
    if message is None:
        message = f"Code contains pattern: {pattern}"
    
    @rule(rule_id=rule_id, message=message, **rule_kwargs)
    def pattern_checker(context: RuleContext) -> List[Finding]:
        findings = []
        
        # Find pattern
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
