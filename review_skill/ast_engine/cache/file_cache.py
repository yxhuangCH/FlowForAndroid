"""
File Cache - 文件内容缓存

缓存文件内容以减少磁盘IO。
"""

import hashlib
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta


class FileCache:
    """文件内容缓存"""
    
    def __init__(
        self,
        cache_dir: str = ".file_cache",
        ttl_days: int = 7
    ):
        """
        初始化文件缓存
        
        Args:
            cache_dir: 缓存目录
            ttl_days: 过期天数
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.ttl = timedelta(days=ttl_days)
        self._memory_cache: Dict[str, Dict] = {}
        self._index_file = self.cache_dir / "index.json"
        self._load_index()
    
    def _compute_hash(self, file_path: str) -> str:
        """计算文件路径哈希"""
        return hashlib.md5(file_path.encode()).hexdigest()[:16]
    
    def _load_index(self):
        """加载索引文件"""
        if self._index_file.exists():
            try:
                with open(self._index_file, 'r') as f:
                    self._index = json.load(f)
            except Exception:
                self._index = {}
        else:
            self._index = {}
    
    def _save_index(self):
        """保存索引文件"""
        try:
            with open(self._index_file, 'w') as f:
                json.dump(self._index, f)
        except Exception as e:
            print(f"Warning: Failed to save index: {e}")
    
    def get(self, file_path: str) -> Optional[str]:
        """
        获取缓存的文件内容
        
        Args:
            file_path: 文件路径
            
        Returns:
            缓存的文件内容或None
        """
        file_hash = self._compute_hash(file_path)
        
        # 检查索引
        if file_hash not in self._index:
            return None
        
        entry = self._index[file_hash]
        
        # 检查是否过期
        cached_time = datetime.fromisoformat(entry['cached_at'])
        if datetime.now() - cached_time > self.ttl:
            self.invalidate(file_path)
            return None
        
        # 检查源文件是否已修改
        try:
            mtime = Path(file_path).stat().st_mtime
            if mtime > entry.get('mtime', 0):
                self.invalidate(file_path)
                return None
        except Exception:
            return None
        
        # 内存缓存
        if file_hash in self._memory_cache:
            return self._memory_cache[file_hash]['content']
        
        # 磁盘缓存
        cache_file = self.cache_dir / f"{file_hash}.content"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                self._memory_cache[file_hash] = {
                    'content': content,
                    'cached_at': datetime.now().isoformat()
                }
                return content
            except Exception:
                pass
        
        return None
    
    def put(self, file_path: str, content: str):
        """
        缓存文件内容
        
        Args:
            file_path: 文件路径
            content: 文件内容
        """
        file_hash = self._compute_hash(file_path)
        
        try:
            mtime = Path(file_path).stat().st_mtime
        except Exception:
            mtime = 0
        
        # 内存缓存
        self._memory_cache[file_hash] = {
            'content': content,
            'cached_at': datetime.now().isoformat()
        }
        
        # 磁盘缓存
        cache_file = self.cache_dir / f"{file_hash}.content"
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            print(f"Warning: Failed to write file cache: {e}")
        
        # 更新索引
        self._index[file_hash] = {
            'file_path': file_path,
            'cached_at': datetime.now().isoformat(),
            'mtime': mtime
        }
        self._save_index()
    
    def invalidate(self, file_path: str):
        """
        使文件缓存失效
        
        Args:
            file_path: 文件路径
        """
        file_hash = self._compute_hash(file_path)
        
        # 内存缓存
        if file_hash in self._memory_cache:
            del self._memory_cache[file_hash]
        
        # 磁盘缓存
        cache_file = self.cache_dir / f"{file_hash}.content"
        if cache_file.exists():
            cache_file.unlink()
        
        # 索引
        if file_hash in self._index:
            del self._index[file_hash]
            self._save_index()
    
    def clear(self):
        """清空所有缓存"""
        self._memory_cache.clear()
        
        for cache_file in self.cache_dir.glob("*.content"):
            try:
                cache_file.unlink()
            except Exception:
                pass
        
        self._index = {}
        self._save_index()
    
    def get_stats(self) -> Dict:
        """获取缓存统计"""
        return {
            "memory_entries": len(self._memory_cache),
            "disk_entries": len(self._index),
            "cache_dir": str(self.cache_dir)
        }


def create_file_cache(
    cache_dir: str = ".file_cache",
    ttl_days: int = 7
) -> FileCache:
    """
    创建文件缓存实例
    """
    return FileCache(cache_dir=cache_dir, ttl_days=ttl_days)
