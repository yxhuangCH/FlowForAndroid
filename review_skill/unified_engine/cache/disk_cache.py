"""
Disk Cache - L2 磁盘缓存

提供跨进程持久化的缓存存储，支持压缩和原子写入。

特性:
- JSON/二进制序列化
- 可选压缩 (gzip)
- 原子写入 (临时文件 + rename)
- TTL 过期清理
- 文件大小限制
"""

import gzip
import hashlib
import json
import pickle
import tempfile
import threading
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, Union


@dataclass
class DiskCacheEntry:
    """磁盘缓存条目元数据"""

    key: str
    data_file: str
    created_at: str
    expires_at: Optional[str]
    data_type: str  # 'json', 'pickle', 'binary'
    compressed: bool
    size_bytes: int


class DiskCache:
    """
    L2 磁盘缓存 - 持久化存储

    支持多种序列化格式:
    - JSON: 人类可读，适合简单数据
    - Pickle: Python 对象，适合 AST 节点
    - Binary: 原始字节，适合压缩数据

    Example:
        ```python
        cache = DiskCache(cache_dir=".cache", ttl_days=7, compression=True)

        # 存储 JSON 数据
        cache.put_json("key1", {"data": "value"})

        # 存储 Python 对象
        cache.put_object("key2", ast_node)

        # 获取
        data = cache.get_json("key1")
        obj = cache.get_object("key2")
        ```
    """

    def __init__(
        self,
        cache_dir: str = ".unified_cache",
        ttl_days: int = 7,
        compression: bool = True,
        max_size_mb: int = 500,
    ):
        """
        初始化磁盘缓存

        Args:
            cache_dir: 缓存目录
            ttl_days: 默认过期天数
            compression: 是否启用压缩
            max_size_mb: 最大缓存大小（MB）
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # 子目录
        self.data_dir = self.cache_dir / "data"
        self.data_dir.mkdir(exist_ok=True)

        self.ttl = timedelta(days=ttl_days)
        self.compression = compression
        self.max_size_bytes = max_size_mb * 1024 * 1024

        # 索引文件
        self._index_file = self.cache_dir / "index.json"
        self._index: Dict[str, DiskCacheEntry] = {}
        self._index_lock = threading.RLock()

        # 加载索引
        self._load_index()

        # 统计
        self._hits = 0
        self._misses = 0

    def _load_index(self) -> None:
        """加载索引文件"""
        if self._index_file.exists():
            try:
                with open(self._index_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._index = {
                        k: DiskCacheEntry(**v) for k, v in data.get("entries", {}).items()
                    }
            except Exception:
                self._index = {}
        else:
            self._index = {}

    def _save_index(self) -> None:
        """保存索引文件"""
        try:
            data = {
                "version": "1.0",
                "updated_at": datetime.now().isoformat(),
                "entries": {k: asdict(v) for k, v in self._index.items()},
            }

            # 原子写入
            temp_file = self._index_file.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            temp_file.replace(self._index_file)
        except Exception as e:
            print(f"Warning: Failed to save cache index: {e}")

    def _compute_hash(self, key: str) -> str:
        """计算键的哈希"""
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    def _get_data_path(self, key_hash: str) -> Path:
        """获取数据文件路径"""
        # 使用子目录分散文件，避免单目录文件过多
        subdir = key_hash[:2]
        subdir_path = self.data_dir / subdir
        subdir_path.mkdir(exist_ok=True)
        return subdir_path / key_hash

    def _is_expired(self, entry: DiskCacheEntry) -> bool:
        """检查条目是否过期"""
        if entry.expires_at is None:
            return False
        expires = datetime.fromisoformat(entry.expires_at)
        return datetime.now() > expires

    def _write_data(
        self, data_path: Path, data: bytes, compressed: bool
    ) -> int:
        """写入数据文件，返回写入大小"""
        if compressed:
            data = gzip.compress(data)

        # 原子写入
        temp_file = data_path.with_suffix(".tmp")
        with open(temp_file, "wb") as f:
            f.write(data)
        temp_file.replace(data_path)

        return len(data)

    def _read_data(self, data_path: Path, compressed: bool) -> Optional[bytes]:
        """读取数据文件"""
        try:
            with open(data_path, "rb") as f:
                data = f.read()

            if compressed:
                data = gzip.decompress(data)

            return data
        except Exception:
            return None

    def put_json(
        self,
        key: str,
        value: dict,
        ttl_days: Optional[int] = None,
    ) -> bool:
        """
        存储 JSON 数据

        Args:
            key: 缓存键
            value: JSON 可序列化字典
            ttl_days: 自定义过期天数

        Returns:
            True 如果存储成功
        """
        try:
            data = json.dumps(value, ensure_ascii=False).encode("utf-8")
            return self._put_raw(key, data, "json", ttl_days)
        except Exception as e:
            print(f"Warning: Failed to cache JSON data: {e}")
            return False

    def put_object(
        self,
        key: str,
        value: Any,
        ttl_days: Optional[int] = None,
    ) -> bool:
        """
        存储 Python 对象 (使用 pickle)

        Args:
            key: 缓存键
            value: Python 对象
            ttl_days: 自定义过期天数

        Returns:
            True 如果存储成功
        """
        try:
            data = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
            return self._put_raw(key, data, "pickle", ttl_days)
        except Exception as e:
            print(f"Warning: Failed to cache object: {e}")
            return False

    def put_binary(
        self,
        key: str,
        data: bytes,
        ttl_days: Optional[int] = None,
    ) -> bool:
        """
        存储二进制数据

        Args:
            key: 缓存键
            data: 二进制数据
            ttl_days: 自定义过期天数

        Returns:
            True 如果存储成功
        """
        return self._put_raw(key, data, "binary", ttl_days)

    def _put_raw(
        self,
        key: str,
        data: bytes,
        data_type: str,
        ttl_days: Optional[int] = None,
    ) -> bool:
        """原始数据存储"""
        with self._index_lock:
            key_hash = self._compute_hash(key)
            data_path = self._get_data_path(key_hash)

            # 计算过期时间
            expires_at = None
            ttl = timedelta(days=ttl_days) if ttl_days else self.ttl
            if ttl.total_seconds() > 0:
                expires_at = (datetime.now() + ttl).isoformat()

            # 写入数据
            size = self._write_data(data_path, data, self.compression)

            # 更新索引
            entry = DiskCacheEntry(
                key=key,
                data_file=str(data_path.relative_to(self.cache_dir)),
                created_at=datetime.now().isoformat(),
                expires_at=expires_at,
                data_type=data_type,
                compressed=self.compression,
                size_bytes=size,
            )
            self._index[key] = entry
            self._save_index()

            return True

    def get_json(self, key: str) -> Optional[dict]:
        """
        获取 JSON 数据

        Args:
            key: 缓存键

        Returns:
            字典或 None
        """
        data = self._get_raw(key)
        if data is None:
            return None

        try:
            return json.loads(data.decode("utf-8"))
        except Exception:
            return None

    def get_object(self, key: str) -> Optional[Any]:
        """
        获取 Python 对象

        Args:
            key: 缓存键

        Returns:
            Python 对象或 None
        """
        data = self._get_raw(key)
        if data is None:
            return None

        try:
            return pickle.loads(data)
        except Exception:
            return None

    def get_binary(self, key: str) -> Optional[bytes]:
        """
        获取二进制数据

        Args:
            key: 缓存键

        Returns:
            二进制数据或 None
        """
        return self._get_raw(key)

    def _get_raw(self, key: str) -> Optional[bytes]:
        """获取原始数据"""
        with self._index_lock:
            entry = self._index.get(key)

            if entry is None:
                self._misses += 1
                return None

            # 检查是否过期
            if self._is_expired(entry):
                self.delete(key)
                self._misses += 1
                return None

            # 读取数据
            data_path = self.cache_dir / entry.data_file
            data = self._read_data(data_path, entry.compressed)

            if data is None:
                # 数据文件损坏，删除索引
                del self._index[key]
                self._save_index()
                self._misses += 1
                return None

            self._hits += 1
            return data

    def delete(self, key: str) -> bool:
        """
        删除缓存

        Args:
            key: 缓存键

        Returns:
            True 如果删除成功
        """
        with self._index_lock:
            entry = self._index.get(key)
            if entry is None:
                return False

            # 删除数据文件
            data_path = self.cache_dir / entry.data_file
            try:
                if data_path.exists():
                    data_path.unlink()
            except Exception:
                pass

            # 删除索引
            del self._index[key]
            self._save_index()
            return True

    def clear(self) -> None:
        """清空所有缓存"""
        with self._index_lock:
            # 删除所有数据文件
            for entry in self._index.values():
                try:
                    data_path = self.cache_dir / entry.data_file
                    if data_path.exists():
                        data_path.unlink()
                except Exception:
                    pass

            # 清空索引
            self._index.clear()
            self._save_index()

            # 重置统计
            self._hits = 0
            self._misses = 0

    def cleanup_expired(self) -> int:
        """
        清理过期条目

        Returns:
            清理的条目数
        """
        with self._index_lock:
            expired_keys = [
                k for k, v in self._index.items() if self._is_expired(v)
            ]
            for key in expired_keys:
                self.delete(key)
            return len(expired_keys)

    def cleanup_size(self) -> int:
        """
        按大小清理，删除最旧的条目

        Returns:
            清理的条目数
        """
        with self._index_lock:
            # 计算总大小
            total_size = sum(e.size_bytes for e in self._index.values())

            if total_size <= self.max_size_bytes:
                return 0

            # 按创建时间排序
            sorted_entries = sorted(
                self._index.items(),
                key=lambda x: x[1].created_at,
            )

            deleted = 0
            for key, _ in sorted_entries:
                if total_size <= self.max_size_bytes * 0.8:  # 清理到 80%
                    break

                entry = self._index.get(key)
                if entry:
                    total_size -= entry.size_bytes
                    self.delete(key)
                    deleted += 1

            return deleted

    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计

        Returns:
            统计信息字典
        """
        with self._index_lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0.0

            total_size = sum(e.size_bytes for e in self._index.values())

            return {
                "entries": len(self._index),
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(hit_rate, 4),
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "max_size_mb": self.max_size_bytes / (1024 * 1024),
                "cache_dir": str(self.cache_dir),
            }

    def keys(self) -> list:
        """获取所有缓存键"""
        with self._index_lock:
            return list(self._index.keys())

    def size(self) -> int:
        """获取缓存条目数"""
        with self._index_lock:
            return len(self._index)
