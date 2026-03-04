"""
统一规则引擎
提供可扩展、高性能、模块化的规则引擎系统
"""

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

# 适配器
from .adapters import (
    rule,
    pattern_rule
)

# 规则
from .rules import (
    NoGlobalScopeRule,
    viewmodel_context_rule,
    main_thread_io_rule
)

__version__ = "1.0.0"

__all__ = [
    # 核心接口
    'Rule',
    'RuleMetadata',
    'RuleSeverity',
    'RuleCategory',
    'Finding',
    
    # 核心组件
    'RuleContext',
    'RuleRegistry',
    'RuleEngine',
    
    # 适配器
    'rule',
    'pattern_rule',
    
    # 规则示例
    'NoGlobalScopeRule',
    'viewmodel_context_rule',
    'main_thread_io_rule',
    
    # 版本
    '__version__'
]


def get_version():
    """获取规则引擎版本"""
    return __version__


def create_engine(registry: RuleRegistry = None) -> RuleEngine:
    """
    创建规则引擎的快捷函数
    
    Args:
        registry: 规则注册表，如果为None则创建新的
        
    Returns:
        规则引擎实例
    """
    return RuleEngine(registry)