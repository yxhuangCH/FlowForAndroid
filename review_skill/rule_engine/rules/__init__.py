"""
Rule modules

Rules are organized by category but can be imported directly from this package.
"""
from .base_rules import NoGlobalScopeRule, viewmodel_context_rule, main_thread_io_rule
from .android_rules import startactivity_without_trycatch_rule

# Batch 1 rules (v3.0.1)
from .memory_leak_static_context import memory_leak_static_context_rule
from .blocking_main_thread import blocking_main_thread_rule
from .coroutine_exception import coroutine_exception_rule
from .compose_remember_missing import compose_remember_missing_rule
from .lifecycle_oncreate_super import lifecycle_oncreate_super_rule
from .mutable_livedata_exposed import mutable_livedata_exposed_rule
from .fragment_arg_constructor import fragment_arg_constructor_rule
from .hardcoded_string import hardcoded_string_rule
from .hilt_module_injection import hilt_module_injection_rule
from .intent_extra_key import intent_extra_key_rule

__all__ = [
    # Base rules
    'NoGlobalScopeRule',
    'viewmodel_context_rule',
    'main_thread_io_rule',
    # Android rules
    'startactivity_without_trycatch_rule',
    # Batch 1 rules
    'memory_leak_static_context_rule',
    'blocking_main_thread_rule',
    'coroutine_exception_rule',
    'compose_remember_missing_rule',
    'lifecycle_oncreate_super_rule',
    'mutable_livedata_exposed_rule',
    'fragment_arg_constructor_rule',
    'hardcoded_string_rule',
    'hilt_module_injection_rule',
    'intent_extra_key_rule',
]
