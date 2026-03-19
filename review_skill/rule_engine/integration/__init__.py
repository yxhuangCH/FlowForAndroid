"""
Integration module - Integrates rule engine into existing system - Enhanced version
"""

from .review_runner import EnhancedReviewRunner
from .config_loader import ConfigLoader, get_config_loader, get_config

# Backward compatible alias
ReviewRunner = EnhancedReviewRunner

__all__ = ['EnhancedReviewRunner', 'ReviewRunner', 'ConfigLoader', 'get_config_loader', 'get_config']
