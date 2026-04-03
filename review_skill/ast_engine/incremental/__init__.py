"""
Incremental - 增量扫描模块

提供增量扫描功能，只处理变更的文件。
"""

from .scanner import IncrementalScanner, FileChange, create_incremental_scanner

__all__ = [
    'IncrementalScanner',
    'FileChange',
    'create_incremental_scanner',
]
