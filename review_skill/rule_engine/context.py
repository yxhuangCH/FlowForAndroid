"""
规则执行上下文
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
import hashlib


@dataclass
class RuleContext:
    """规则执行上下文"""
    code: str                      # 代码内容
    file_path: str                 # 文件路径
    language: str                  # 编程语言（kotlin/java等）
    file_hash: str = ""            # 文件哈希（用于缓存）
    ast: Optional[Any] = None      # AST（如果已解析）
    project_info: Dict[str, Any] = field(default_factory=dict)  # 项目信息
    config: Dict[str, Any] = field(default_factory=dict)  # 规则配置
    
    # 缓存相关
    _cache: Dict[str, Any] = field(default_factory=dict, init=False)
    _line_cache: Dict[str, List[str]] = field(default_factory=dict, init=False)
    
    def __post_init__(self):
        """后初始化处理"""
        if not self.file_hash:
            self.file_hash = self._calculate_file_hash()
        
        # 预处理行缓存
        if self.code:
            self._line_cache["raw"] = self.code.split('\n')
    
    def _calculate_file_hash(self) -> str:
        """计算文件哈希"""
        content = f"{self.file_path}:{self.code}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def get_cached(self, key: str, default: Any = None) -> Any:
        """获取缓存值"""
        return self._cache.get(key, default)
    
    def set_cached(self, key: str, value: Any):
        """设置缓存值"""
        self._cache[key] = value
    
    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()
        self._line_cache.clear()
    
    def get_lines(self, normalized: bool = False) -> List[str]:
        """
        获取代码行列表
        
        Args:
            normalized: 是否标准化（去除前后空白）
            
        Returns:
            代码行列表
        """
        cache_key = "normalized" if normalized else "raw"
        if cache_key not in self._line_cache:
            if normalized:
                lines = [line.strip() for line in self.code.split('\n')]
                self._line_cache[cache_key] = lines
            else:
                self._line_cache[cache_key] = self.code.split('\n')
        
        return self._line_cache[cache_key]
    
    def get_line_at(self, line_number: int, normalized: bool = False) -> Optional[str]:
        """
        获取指定行的内容
        
        Args:
            line_number: 行号（从1开始）
            normalized: 是否标准化
            
        Returns:
            行内容或None（如果行号无效）
        """
        lines = self.get_lines(normalized)
        if 1 <= line_number <= len(lines):
            return lines[line_number - 1]
        return None
    
    def find_pattern_in_lines(self, pattern: str, case_sensitive: bool = True) -> List[int]:
        """
        在代码行中查找模式
        
        Args:
            pattern: 查找模式
            case_sensitive: 是否大小写敏感
            
        Returns:
            匹配的行号列表（从1开始）
        """
        lines = self.get_lines()
        matches = []
        
        for i, line in enumerate(lines, 1):
            search_line = line if case_sensitive else line.lower()
            search_pattern = pattern if case_sensitive else pattern.lower()
            
            if search_pattern in search_line:
                matches.append(i)
        
        return matches