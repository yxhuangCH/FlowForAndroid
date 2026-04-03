"""
AST Cache - AST缓存管理器

提供AST解析结果的缓存功能，避免重复解析相同文件。
"""

import hashlib
import pickle
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import threading


class ASTCache:
    """AST缓存管理器"""
    
    def __init__(
        self, 
        cache_dir: str = ".ast_cache", 
        ttl_days: int = 7,
        max_memory_entries: int = 1000
    ):
        """
        初始化缓存管理器
        
        Args:
            cache_dir: 磁盘缓存目录
            ttl_days: 缓存过期天数
            max_memory_entries: 内存缓存最大条目数
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.ttl = timedelta(days=ttl_days)
        self.max_memory_entries = max_memory_entries
        self._memory_cache: Dict[str, tuple] = {}
        self._lock = threading.Lock()
    
    def _compute_hash(self, content: str) -> str:
        """计算内容哈希"""
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def get(self, file_path: str, content: str) -> Optional[Any]:
        """
        获取缓存的AST
        
        Args:
            file_path: 文件路径
            content: 文件内容
            
        Returns:
            缓存的AST或None
        """
        content_hash = self._compute_hash(content)
        
        # 1. 内存缓存查找
        cache_key = f"{file_path}:{content_hash}"
        with self._lock:
            if cache_key in self._memory_cache:
                ast, timestamp = self._memory_cache[cache_key]
                if datetime.now() - timestamp < self.ttl:
                    return ast
        
        # 2. 磁盘缓存查找
        cache_file = self.cache_dir / f"{content_hash}.ast"
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    data = pickle.load(f)
                # 验证文件路径
                if data.get('file_path') == file_path:
                    # 放入内存缓存
                    with self._lock:
                        self._evict_if_needed()
                        self._memory_cache[cache_key] = (data['ast'], data['timestamp'])
                    return data['ast']
            except Exception:
                pass
        
        return None
    
    def put(self, file_path: str, content: str, ast: Any):
        """
        存储AST到缓存
        
        Args:
            file_path: 文件路径
            content: 文件内容
            ast: AST节点
        """
        content_hash = self._compute_hash(content)
        cache_key = f"{file_path}:{content_hash}"
        now = datetime.now()
        
        # 内存缓存
        with self._lock:
            self._evict_if_needed()
            self._memory_cache[cache_key] = (ast, now)
        
        # 磁盘缓存
        cache_file = self.cache_dir / f"{content_hash}.ast"
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump({
                    'ast': ast,
                    'timestamp': now,
                    'file_path': file_path,
                    'content_hash': content_hash
                }, f)
        except Exception as e:
            print(f"Warning: Failed to write disk cache: {e}")
    
    def _evict_if_needed(self):
        """如果内存缓存已满，淘汰最旧的条目"""
        if len(self._memory_cache) >= self.max_memory_entries:
            # 按时间排序，删除最旧的条目
            sorted_items = sorted(
                self._memory_cache.items(),
                key=lambda x: x[1][1]
            )
            # 删除最旧的100个
            for key, _ in sorted_items[:100]:
                del self._memory_cache[key]
    
    def invalidate(self, file_path: str):
        """
        使文件缓存失效
        
        Args:
            file_path: 文件路径
        """
        with self._lock:
            # 删除内存缓存
            keys_to_delete = [
                k for k in self._memory_cache.keys()
                if k.startswith(f"{file_path}:")
            ]
            for key in keys_to_delete:
                del self._memory_cache[key]
        
        # 删除磁盘缓存
        for cache_file in self.cache_dir.glob("*.ast"):
            try:
                with open(cache_file, 'rb') as f:
                    data = pickle.load(f)
                if data.get('file_path') == file_path:
                    cache_file.unlink()
            except Exception:
                pass
    
    def clear(self):
        """清空所有缓存"""
        with self._lock:
            self._memory_cache.clear()
        
        for cache_file in self.cache_dir.glob("*.ast"):
            try:
                cache_file.unlink()
            except Exception:
                pass
    
    def cleanup(self):
        """清理过期缓存"""
        now = datetime.now()
        
        # 清理磁盘缓存
        for cache_file in self.cache_dir.glob("*.ast"):
            try:
                with open(cache_file, 'rb') as f:
                    data = pickle.load(f)
                if now - data['timestamp'] > self.ttl:
                    cache_file.unlink()
            except Exception:
                pass
        
        # 清理内存缓存
        with self._lock:
            keys_to_delete = []
            for key, (_, timestamp) in self._memory_cache.items():
                if now - timestamp > self.ttl:
                    keys_to_delete.append(key)
            for key in keys_to_delete:
                del self._memory_cache[key]
    
    def get_stats(self) -> Dict:
        """获取缓存统计信息"""
        with self._lock:
            memory_count = len(self._memory_cache)
        
        disk_count = len(list(self.cache_dir.glob("*.ast")))
        
        return {
            "memory_entries": memory_count,
            "disk_entries": disk_count,
            "max_memory_entries": self.max_memory_entries,
            "cache_dir": str(self.cache_dir),
            "ttl_days": self.ttl.days
        }


def create_ast_cache(
    cache_dir: str = ".ast_cache",
    ttl_days: int = 7
) -> ASTCache:
    """
    创建AST缓存实例
    
    Args:
        cache_dir: 缓存目录
        ttl_days: 过期天数
        
    Returns:
        ASTCache实例
    """
    return ASTCache(cache_dir=cache_dir, ttl_days=ttl_days)
