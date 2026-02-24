"""
规则引擎适配器模块
提供向后兼容的适配器和装饰器支持
"""

from .legacy_adapter import LegacyRuleAdapter, create_legacy_adapter
from .decorators import rule, pattern_rule

__all__ = [
    'LegacyRuleAdapter',
    'create_legacy_adapter',
    'rule',
    'pattern_rule'
]