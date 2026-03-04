"""
规则引擎适配器模块
提供规则装饰器支持
"""

from .decorators import rule, pattern_rule

__all__ = [
    'rule',
    'pattern_rule'
]
