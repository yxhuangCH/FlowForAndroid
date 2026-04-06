"""Unified Rule Engine - DEPRECATED
Provides extensible, high-performance, modular Rule Engine system

DEPRECATION NOTICE:
This module is deprecated and will be removed in v5.0.0.
Please use unified_engine instead.
See: docs/MIGRATION_GUIDE.md
"""

import warnings

warnings.warn(
    "rule_engine is deprecated and will be removed in v5.0.0. "
    "Use unified_engine instead. See docs/MIGRATION_GUIDE.md",
    DeprecationWarning,
    stacklevel=2
)

from .interfaces import (
    Rule,
    RuleMetadata,
    RuleSeverity,
    RuleCategory,
    Finding
)

from .context import RuleContext
from .registry import RuleRegistry
from .engine import RuleEngine

# Adapters
from .adapters import (
    rule,
    pattern_rule
)

# Rule examples
from .rules import (
    NoGlobalScopeRule,
    viewmodel_context_rule,
    main_thread_io_rule
)

__version__ = "1.0.0"

__all__ = [
    # Core interfaces
    'Rule',
    'RuleMetadata',
    'RuleSeverity',
    'RuleCategory',
    'Finding',
    
    # Core components
    'RuleContext',
    'RuleRegistry',
    'RuleEngine',
    
    # Adapters
    'rule',
    'pattern_rule',
    
    # Rule examples
    'NoGlobalScopeRule',
    'viewmodel_context_rule',
    'main_thread_io_rule',
    
    # Version
    '__version__'
]


def get_version():
    """Get Rule Engine version"""
    return __version__


def create_engine(registry: RuleRegistry = None) -> RuleEngine:
    """
    Quick function to create Rule Engine
    
    Args:
        registry: Rule registry, if None creates a new one
        
    Returns:
        Rule Engine instance
    """
    return RuleEngine(registry)
