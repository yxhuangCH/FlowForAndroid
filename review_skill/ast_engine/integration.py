"""
AST Engine Integration - AST引擎集成模块

提供AST引擎与现有review流程的集成。
"""

import os
import time
from typing import Dict, List, Optional, Any
from pathlib import Path

from .parser_v2 import parse_kotlin_ast
from .nodes import ASTNode, NodeType
from .rules.base_ast_rule import RuleRegistry, Finding, RuleSeverity


class ASTReviewResult:
    """AST审查结果"""
    
    def __init__(self):
        self.findings: List[Finding] = []
        self.file_results: Dict[str, List[Finding]] = {}
        self.parse_errors: List[Dict] = []
        self.files_scanned: int = 0
        self.files_from_cache: int = 0
        self.total_time: float = 0.0
        self.engine_info: Dict[str, Any] = {}
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "findings": [f.to_dict() for f in self.findings],
            "file_results": {k: [f.to_dict() for f in v] for k, v in self.file_results.items()},
            "parse_errors": self.parse_errors,
            "files_scanned": self.files_scanned,
            "files_from_cache": self.files_from_cache,
            "total_time": self.total_time,
            "engine_info": self.engine_info
        }


class ASTEngine:
    """
    AST引擎主类
    
    整合AST解析和规则检查功能。
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化AST引擎
        
        Args:
            config: 配置选项
                - enabled_rules: 启用的规则ID列表
                - disabled_rules: 禁用的规则ID列表
                - severity_threshold: 严重级别阈值
                - parallel: 是否并行处理
        """
        self.config = config or {}
        self._setup_rules()
    
    def _setup_rules(self):
        """设置规则"""
        # 获取所有已注册的规则
        all_rules = RuleRegistry.get_all_rules()
        
        # 过滤启用的规则
        enabled_rules = self.config.get("enabled_rules", [])
        disabled_rules = self.config.get("disabled_rules", [])
        
        if enabled_rules:
            self.rules = [r for r in all_rules if r.rule_id in enabled_rules]
        else:
            self.rules = [r for r in all_rules if r.rule_id not in disabled_rules]
        
        print(f"✓ AST引擎加载了 {len(self.rules)} 条规则")
    
    def get_engine_info(self) -> Dict:
        """获取引擎信息"""
        return {
            "type": "ast_engine",
            "version": "2.0.0",
            "rules_count": len(self.rules),
            "rules": [
                {
                    "id": r.rule_id,
                    "name": r.rule_name,
                    "severity": r.severity.value,
                    "category": r.category.value
                }
                for r in self.rules
            ]
        }
    
    def review_code(self, code: str, file_path: str = "unknown.kt") -> List[Finding]:
        """
        审查代码
        
        Args:
            code: Kotlin代码
            file_path: 文件路径
            
        Returns:
            发现的问题列表
        """
        findings = []
        
        try:
            # 解析AST
            ast = parse_kotlin_ast(code)
            
            # 应用所有规则
            for rule in self.rules:
                try:
                    rule_findings = rule.check(ast, file_path)
                    findings.extend(rule_findings)
                except Exception as e:
                    print(f"⚠ 规则 {rule.rule_id} 执行失败: {e}")
        
        except Exception as e:
            # 记录解析错误但不中断
            print(f"⚠ AST解析失败 [{file_path}]: {e}")
        
        return findings
    
    def review_file(self, file_path: str) -> List[Finding]:
        """
        审查文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            发现的问题列表
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            return self.review_code(code, file_path)
        except Exception as e:
            print(f"⚠ 无法读取文件 {file_path}: {e}")
            return []
    
    def review_diff(self, diff_text: str) -> ASTReviewResult:
        """
        审查Git diff
        
        Args:
            diff_text: Git diff文本
            
        Returns:
            审查结果
        """
        start_time = time.time()
        result = ASTReviewResult()
        
        # 解析diff获取文件变更
        file_changes = self._parse_diff(diff_text)
        
        for file_change in file_changes:
            file_path = file_change["path"]
            new_content = file_change["new_content"]
            
            # 只处理Kotlin文件
            if not file_path.endswith(".kt"):
                continue
            
            result.files_scanned += 1
            
            # 审查代码
            findings = self.review_code(new_content, file_path)
            
            if findings:
                result.file_results[file_path] = findings
                result.findings.extend(findings)
        
        result.total_time = time.time() - start_time
        result.engine_info = self.get_engine_info()
        
        return result
    
    def _parse_diff(self, diff_text: str) -> List[Dict]:
        """
        解析Git diff
        
        Args:
            diff_text: Git diff文本
            
        Returns:
            文件变更列表
        """
        changes = []
        current_file = None
        current_content = []
        in_new_content = False
        
        for line in diff_text.split('\n'):
            # 文件头
            if line.startswith('diff --git '):
                # 保存上一个文件
                if current_file and current_content:
                    changes.append({
                        "path": current_file,
                        "new_content": '\n'.join(current_content)
                    })
                
                # 解析新文件路径
                parts = line.split(' ')
                if len(parts) >= 4:
                    # 取 b/ 后面的路径
                    b_path = parts[3]
                    if b_path.startswith('b/'):
                        current_file = b_path[2:]
                    else:
                        current_file = b_path
                current_content = []
                in_new_content = False
            
            # 新文件标记
            elif line.startswith('+++ '):
                in_new_content = True
            
            # 新文件内容行
            elif line.startswith('+') and not line.startswith('+++'):
                current_content.append(line[1:])
            
            # 上下文行（保留代码）
            elif line.startswith(' '):
                current_content.append(line[1:])
        
        # 保存最后一个文件
        if current_file and current_content:
            changes.append({
                "path": current_file,
                "new_content": '\n'.join(current_content)
            })
        
        return changes


def create_ast_engine(config: Optional[Dict] = None) -> ASTEngine:
    """
    创建AST引擎实例
    
    Args:
        config: 配置选项
        
    Returns:
        AST引擎实例
    """
    return ASTEngine(config)


# 环境变量检查
def is_ast_engine_enabled() -> bool:
    """检查是否启用AST引擎"""
    return os.getenv('USE_AST_ENGINE', 'false').lower() == 'true'


def should_use_ast_engine() -> bool:
    """
    判断是否应该使用AST引擎
    
    优先级:
    1. 环境变量 USE_AST_ENGINE
    2. 配置文件设置
    3. 默认False（使用旧引擎）
    """
    # 检查环境变量
    env_value = os.getenv('USE_AST_ENGINE', '').lower()
    if env_value in ('true', '1', 'yes'):
        return True
    if env_value in ('false', '0', 'no'):
        return False
    
    # 默认使用旧引擎（向后兼容）
    return False