"""
Rule execution context
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
import hashlib


@dataclass
class RuleContext:
    """Rule execution context"""
    code: str                      # Code content
    file_path: str                 # File path
    language: str                  # Programming language (kotlin/java, etc.)
    file_hash: str = ""            # File hash (for caching)
    ast: Optional[Any] = None      # AST (if parsed)
    project_info: Dict[str, Any] = field(default_factory=dict)  # Project info
    config: Dict[str, Any] = field(default_factory=dict)  # Rule config
    
    # Cache related
    _cache: Dict[str, Any] = field(default_factory=dict, init=False)
    _line_cache: Dict[str, List[str]] = field(default_factory=dict, init=False)
    
    def __post_init__(self):
        """Post-init processing"""
        if not self.file_hash:
            self.file_hash = self._calculate_file_hash()
        
        # Preprocess line cache
        if self.code:
            self._line_cache["raw"] = self.code.split('\n')
    
    def _calculate_file_hash(self) -> str:
        """Calculate file hash"""
        content = f"{self.file_path}:{self.code}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def get_cached(self, key: str, default: Any = None) -> Any:
        """Get cached value"""
        return self._cache.get(key, default)
    
    def set_cached(self, key: str, value: Any):
        """Set cache value"""
        self._cache[key] = value
    
    def clear_cache(self):
        """Clear cache"""
        self._cache.clear()
        self._line_cache.clear()
    
    def get_lines(self, normalized: bool = False) -> List[str]:
        """
        Get code line list
        
        Args:
            normalized: Whether to normalize (remove leading/trailing whitespace)
            
        Returns:
            List of code lines
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
        Get content of specified line
        
        Args:
            line_number: Line number (1-based)
            normalized: Whether normalized
            
        Returns:
            Line content or None (if line number invalid)
        """
        lines = self.get_lines(normalized)
        if 1 <= line_number <= len(lines):
            return lines[line_number - 1]
        return None
    
    def find_pattern_in_lines(self, pattern: str, case_sensitive: bool = True) -> List[int]:
        """
        Find pattern in code lines
        
        Args:
            pattern: Pattern to find
            case_sensitive: Whether case sensitive
            
        Returns:
            List of matching line numbers (1-based)
        """
        lines = self.get_lines()
        matches = []
        
        for i, line in enumerate(lines, 1):
            search_line = line if case_sensitive else line.lower()
            search_pattern = pattern if case_sensitive else pattern.lower()
            
            if search_pattern in search_line:
                matches.append(i)
        
        return matches
