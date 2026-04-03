"""
Incremental Scanner - 增量扫描器

只扫描变更的文件，结合缓存实现高效的增量扫描。
"""

import subprocess
import os
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from pathlib import Path

from ..parser_v2 import parse_kotlin_ast
from ..integration import ASTEngine
from ..cache import CacheManager


@dataclass
class FileChange:
    """文件变更"""
    path: str
    change_type: str  # A: added, M: modified, D: deleted
    old_content: str
    new_content: str


class IncrementalScanner:
    """增量扫描器"""
    
    def __init__(
        self,
        cache_manager: Optional[CacheManager] = None,
        max_workers: int = 4
    ):
        """
        初始化增量扫描器
        
        Args:
            cache_manager: 缓存管理器
            max_workers: 最大工作线程数
        """
        self.cache_manager = cache_manager or CacheManager()
        self.max_workers = max_workers
        self.engine = ASTEngine()
    
    def get_changed_files_from_git(self, base: str = "HEAD~1", head: str = "HEAD") -> List[FileChange]:
        """
        从Git获取变更的文件列表
        
        Args:
            base: 基准分支/提交
            head: HEAD分支/提交
            
        Returns:
            文件变更列表
        """
        try:
            result = subprocess.run(
                ["git", "diff", "--name-status", base, head],
                capture_output=True,
                text=True,
                cwd=os.getcwd()
            )
            
            if result.returncode != 0:
                print(f"Warning: git diff failed: {result.stderr}")
                return self._get_all_kt_files()
            
            return self._parse_git_diff(result.stdout)
        except Exception as e:
            print(f"Warning: Failed to get git changes: {e}")
            return self._get_all_kt_files()
    
    def _get_all_kt_files(self) -> List[FileChange]:
        """获取所有Kotlin文件（用于非git环境）"""
        changes = []
        for root, dirs, files in os.walk("."):
            # 跳过隐藏目录和缓存目录
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != 'node_modules']
            
            for file in files:
                if file.endswith('.kt'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        changes.append(FileChange(
                            path=file_path,
                            change_type='M',
                            old_content='',
                            new_content=content
                        ))
                    except Exception:
                        pass
        
        return changes
    
    def _parse_git_diff(self, diff_output: str) -> List[FileChange]:
        """
        解析git diff输出
        
        Args:
            diff_output: git diff --name-status输出
            
        Returns:
            文件变更列表
        """
        changes = []
        
        for line in diff_output.strip().split('\n'):
            if not line:
                continue
            
            # 解析: A\tpath, M\tpath, D\tpath
            parts = line.split('\t')
            if len(parts) < 2:
                continue
            
            status, path = parts[0].strip(), parts[1].strip()
            
            # 只处理Kotlin文件
            if not path.endswith('.kt'):
                continue
            
            # 读取文件内容
            new_content = ""
            old_content = ""
            
            if status != 'D':
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        new_content = f.read()
                except Exception as e:
                    print(f"Warning: Cannot read {path}: {e}")
                    continue
            
            changes.append(FileChange(
                path=path,
                change_type=status,
                old_content=old_content,
                new_content=new_content
            ))
        
        return changes
    
    def scan_incremental(self, diff_text: Optional[str] = None) -> Dict[str, Any]:
        """
        执行增量扫描
        
        Args:
            diff_text: git diff文本，如果为None则从git获取
            
        Returns:
            扫描结果字典
        """
        # 获取变更文件
        if diff_text:
            changes = self._parse_diff(diff_text)
        else:
            changes = self.get_changed_files_from_git()
        
        # 统计信息
        files_scanned = 0
        files_from_cache = 0
        files_skipped = 0
        all_findings = []
        
        for change in changes:
            # 跳过删除的文件
            if change.change_type == 'D':
                files_skipped += 1
                continue
            
            # 检查缓存
            cached_ast = self.cache_manager.get_ast(
                change.path, 
                change.new_content
            )
            
            if cached_ast is not None:
                # 使用缓存的AST
                files_from_cache += 1
                
                # 如果需要，可以从缓存中提取findings
                # 这里简化处理，只记录缓存命中
                continue
            
            # 需要重新解析和扫描
            files_scanned += 1
            
            try:
                ast = parse_kotlin_ast(change.new_content)
                findings = self.engine.review_code(change.new_content, change.path)
                
                # 存入缓存
                self.cache_manager.put_ast(change.path, change.new_content, ast)
                
                all_findings.extend(findings)
                
            except Exception as e:
                print(f"Error scanning {change.path}: {e}")
        
        return {
            "findings": all_findings,
            "files_scanned": files_scanned,
            "files_from_cache": files_from_cache,
            "files_skipped": files_skipped,
            "total_changes": len(changes)
        }
    
    def _parse_diff(self, diff_text: str) -> List[FileChange]:
        """
        解析diff文本
        
        Args:
            diff_text: diff文本
            
        Returns:
            文件变更列表
        """
        changes = []
        current_file = None
        new_content_lines = []
        
        for line in diff_text.split('\n'):
            # 文件头
            if line.startswith('diff --git '):
                if current_file:
                    changes.append(FileChange(
                        path=current_file,
                        change_type='M',
                        old_content='',
                        new_content='\n'.join(new_content_lines)
                    ))
                
                # 解析文件路径
                parts = line.split(' ')
                if len(parts) >= 4:
                    b_path = parts[3]
                    if b_path.startswith('b/'):
                        current_file = b_path[2:]
                    else:
                        current_file = b_path
                new_content_lines = []
            
            # 新内容
            elif line.startswith('+++ '):
                continue
            
            # 添加的行
            elif line.startswith('+') and not line.startswith('+++'):
                new_content_lines.append(line[1:])
            
            # 上下文和删除的行
            elif line.startswith('-') or line.startswith(' '):
                new_content_lines.append(line[1:] if line.startswith(' ') else '')
        
        # 最后一个文件
        if current_file and new_content_lines:
            changes.append(FileChange(
                path=current_file,
                change_type='M',
                old_content='',
                new_content='\n'.join(new_content_lines)
            ))
        
        return [c for c in changes if c.path.endswith('.kt')]
    
    def get_stats(self) -> Dict:
        """获取扫描统计"""
        return self.cache_manager.get_stats()


def create_incremental_scanner(
    cache_manager: Optional[CacheManager] = None,
    max_workers: int = 4
) -> IncrementalScanner:
    """
    创建增量扫描器
    
    Args:
        cache_manager: 缓存管理器
        max_workers: 最大工作线程数
        
    Returns:
        IncrementalScanner实例
    """
    return IncrementalScanner(
        cache_manager=cache_manager,
        max_workers=max_workers
    )
