"""
集成模块 - 将规则引擎集成到现有系统中 - 增强版
"""

from .review_runner import EnhancedReviewRunner
from .config_loader import ConfigLoader, get_config_loader, get_config

# 向后兼容别名
ReviewRunner = EnhancedReviewRunner

__all__ = ['EnhancedReviewRunner', 'ReviewRunner', 'ConfigLoader', 'get_config_loader', 'get_config']
