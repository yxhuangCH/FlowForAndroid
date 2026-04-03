"""
Parallel Scanner - 并行扫描器

利用多核CPU并行扫描多个文件。
"""

import os
import concurrent.futures
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ..parser_v2 import parse_kotlin_ast
from ..integration import ASTEngine
from ..cache import CacheManager


@dataclass
class ScanResult:
    """扫描结果"""
    file_path: str
    findings: List[Any]
    error: Optional[str] = None


class ParallelScanner:
    """并行扫描器"""
    
    def __init__(
        self,
        cache_manager: Optional[CacheManager] = None,
        max_workers: Optional[int] = None
    ):
        """
        初始化并行扫描器
        
        Args:
            cache_manager: 缓存管理器
            max_workers: 最大工作线程数，默认CPU核心数
        """
        if max_workers is None:
            max_workers = os.cpu_count() or 4
        
        self.max_workers = max_workers
        self.cache_manager = cache_manager or CacheManager()
        self.engine = ASTEngine()
    
    def scan_file(self, file_path: str, content: str) -> ScanResult:
        """
        扫描单个文件
        
        Args:
            file_path: 文件路径
            content: 文件内容
            
        Returns:
            扫描结果
        """
        try:
            # 检查缓存
            cached_ast = self.cache_manager.get_ast(file_path, content)
            
            if cached_ast is not None:
                return ScanResult(
                    file_path=file_path,
                    findings=[],
                    error=None
                )
            
            # 解析并扫描
            ast = parse_kotlin_ast(content)
            findings = self.engine.review_code(content, file_path)
            
            # 存入缓存
            self.cache_manager.put_ast(file_path, content, ast)
            
            return ScanResult(
                file_path=file_path,
                findings=findings,
                error=None
            )
            
        except Exception as e:
            return ScanResult(
                file_path=file_path,
                findings=[],
                error=str(e)
            )
    
    def scan_files(self, files: List[tuple]) -> List[ScanResult]:
        """
        并行扫描多个文件
        
        Args:
            files: [(file_path, content), ...] 列表
            
        Returns:
            扫描结果列表
        """
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers
        ) as executor:
            # 提交所有任务
            future_to_file = {
                executor.submit(self.scan_file, path, content): path
                for path, content in files
            }
            
            # 收集结果
            for future in concurrent.futures.as_completed(future_to_file):
                path = future_to_file[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append(ScanResult(
                        file_path=path,
                        findings=[],
                        error=str(e)
                    ))
        
        return results
    
    def scan_files_sequential(self, files: List[tuple]) -> List[ScanResult]:
        """
        顺序扫描文件（用于对比）
        
        Args:
            files: [(file_path, content), ...] 列表
            
        Returns:
            扫描结果列表
        """
        results = []
        
        for file_path, content in files:
            result = self.scan_file(file_path, content)
            results.append(result)
        
        return results
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "max_workers": self.max_workers,
            "cache": self.cache_manager.get_stats()
        }


def create_parallel_scanner(
    cache_manager: Optional[CacheManager] = None,
    max_workers: Optional[int] = None
) -> ParallelScanner:
    """
    创建并行扫描器
    
    Args:
        cache_manager: 缓存管理器
        max_workers: 最大工作线程数
        
    Returns:
        ParallelScanner实例
    """
    return ParallelScanner(
        cache_manager=cache_manager,
        max_workers=max_workers
    )
