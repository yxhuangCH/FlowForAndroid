"""
Rule definitions
"""

from .base_rules import NoGlobalScopeRule, viewmodel_context_rule, main_thread_io_rule
from .android_rules import startactivity_without_trycatch_rule

__all__ = [
    'NoGlobalScopeRule',
    'viewmodel_context_rule',
    'main_thread_io_rule',
    'startactivity_without_trycatch_rule',
]
