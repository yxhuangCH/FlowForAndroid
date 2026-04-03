"""
Cache - 缓存模块

提供AST缓存、文件缓存和统一缓存管理功能。
"""

from .ast_cache import ASTCache, create_ast_cache
from .file_cache import FileCache, create_file_cache
from .cache_manager import CacheManager, get_cache_manager, reset_cache_manager

__all__ = [
    'ASTCache',
    'create_ast_cache',
    'FileCache',
    'create_file_cache',
    'CacheManager',
    'get_cache_manager',
    'reset_cache_manager',
]
