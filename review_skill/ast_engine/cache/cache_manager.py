"""
Cache Manager - 缓存管理器

统一管理AST缓存、文件缓存和规则结果缓存。
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from .ast_cache import ASTCache
from .file_cache import FileCache


@dataclass
class CacheStats:
    """缓存统计信息"""
    ast_cache_memory: int
    ast_cache_disk: int
    file_cache_memory: int
    file_cache_disk: int


class CacheManager:
    """缓存管理器"""
    
    def __init__(
        self,
        ast_cache_dir: str = ".ast_cache",
        file_cache_dir: str = ".file_cache",
        ttl_days: int = 7
    ):
        """
        初始化缓存管理器
        
        Args:
            ast_cache_dir: AST缓存目录
            file_cache_dir: 文件缓存目录
            ttl_days: 缓存过期天数
        """
        self.ast_cache = ASTCache(
            cache_dir=ast_cache_dir,
            ttl_days=ttl_days
        )
        self.file_cache = FileCache(
            cache_dir=file_cache_dir,
            ttl_days=ttl_days
        )
        self.ttl_days = ttl_days
    
    def get_ast(self, file_path: str, content: str) -> Optional[Any]:
        """
        获取AST缓存
        
        Args:
            file_path: 文件路径
            content: 文件内容
            
        Returns:
            缓存的AST或None
        """
        return self.ast_cache.get(file_path, content)
    
    def put_ast(self, file_path: str, content: str, ast: Any):
        """
        存储AST到缓存
        
        Args:
            file_path: 文件路径
            content: 文件内容
            ast: AST节点
        """
        self.ast_cache.put(file_path, content, ast)
    
    def get_file_content(self, file_path: str) -> Optional[str]:
        """
        获取文件内容缓存
        
        Args:
            file_path: 文件路径
            
        Returns:
            缓存的文件内容或None
        """
        return self.file_cache.get(file_path)
    
    def put_file_content(self, file_path: str, content: str):
        """
        缓存文件内容
        
        Args:
            file_path: 文件路径
            content: 文件内容
        """
        self.file_cache.put(file_path, content)
    
    def invalidate(self, file_path: str):
        """
        使文件的所有缓存失效
        
        Args:
            file_path: 文件路径
        """
        self.ast_cache.invalidate(file_path)
        self.file_cache.invalidate(file_path)
    
    def clear(self):
        """清空所有缓存"""
        self.ast_cache.clear()
        self.file_cache.clear()
    
    def cleanup(self):
        """清理过期缓存"""
        self.ast_cache.cleanup()
    
    def get_stats(self) -> Dict:
        """
        获取缓存统计信息
        
        Returns:
            统计信息字典
        """
        ast_stats = self.ast_cache.get_stats()
        file_stats = self.file_cache.get_stats()
        
        return {
            "ast_cache": ast_stats,
            "file_cache": file_stats,
            "ttl_days": self.ttl_days
        }
    
    def should_rescan(self, file_path: str, content: str) -> bool:
        """
        判断是否需要重新扫描
        
        Args:
            file_path: 文件路径
            content: 文件内容
            
        Returns:
            True表示需要重新扫描，False表示可以使用缓存
        """
        cached_ast = self.get_ast(file_path, content)
        return cached_ast is None


# 全局缓存管理器实例
_default_cache_manager: Optional[CacheManager] = None


def get_cache_manager(
    ast_cache_dir: str = ".ast_cache",
    file_cache_dir: str = ".file_cache",
    ttl_days: int = 7
) -> CacheManager:
    """
    获取全局缓存管理器实例
    
    Args:
        ast_cache_dir: AST缓存目录
        file_cache_dir: 文件缓存目录
        ttl_days: 缓存过期天数
        
    Returns:
        CacheManager实例
    """
    global _default_cache_manager
    
    if _default_cache_manager is None:
        _default_cache_manager = CacheManager(
            ast_cache_dir=ast_cache_dir,
            file_cache_dir=file_cache_dir,
            ttl_days=ttl_days
        )
    
    return _default_cache_manager


def reset_cache_manager():
    """重置全局缓存管理器"""
    global _default_cache_manager
    _default_cache_manager = None
