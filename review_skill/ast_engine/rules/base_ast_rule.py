"""
Base AST Rule - AST规则基类

定义基于AST的规则检查基类和数据结构。
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

from ..nodes import ASTNode


class RuleSeverity(Enum):
    """规则严重级别"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    MINOR = "minor"


class RuleCategory(Enum):
    """规则类别"""
    COROUTINE = "coroutine"
    COMPOSE = "compose"
    MEMORY_LEAK = "memory_leak"
    PERFORMANCE = "performance"
    BEST_PRACTICE = "best_practice"
    CODE_STYLE = "code_style"


@dataclass
class Finding:
    """
    规则发现项
    
    表示代码审查中发现的问题。
    """
    rule_id: str
    message: str
    severity: RuleSeverity
    file_path: str
    line_number: int
    column_number: int
    suggestion: Optional[str] = None
    code_snippet: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "rule": self.rule_id,
            "message": self.message,
            "severity": self.severity.value,
            "file": self.file_path,
            "line": self.line_number,
            "column": self.column_number,
            "suggestion": self.suggestion,
            "code_snippet": self.code_snippet,
            **self.metadata
        }


class ASTBasedRule(ABC):
    """
    基于AST的规则基类
    
    所有AST规则必须继承此类并实现check方法。
    """
    
    @property
    @abstractmethod
    def rule_id(self) -> str:
        """规则唯一标识"""
        pass
    
    @property
    @abstractmethod
    def rule_name(self) -> str:
        """规则名称"""
        pass
    
    @property
    @abstractmethod
    def severity(self) -> RuleSeverity:
        """规则严重级别"""
        pass
    
    @property
    @abstractmethod
    def category(self) -> RuleCategory:
        """规则类别"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """规则描述"""
        pass
    
    @abstractmethod
    def check(self, ast: ASTNode, file_path: str) -> List[Finding]:
        """
        基于AST的检查逻辑
        
        Args:
            ast: 抽象语法树根节点
            file_path: 文件路径
            
        Returns:
            发现的问题列表
        """
        pass
    
    # ==================== 工具方法 ====================
    
    def get_line_number(self, node: ASTNode) -> int:
        """获取节点行号"""
        return node.line_number
    
    def get_column_number(self, node: ASTNode) -> int:
        """获取节点列号"""
        return node.column_number
    
    def get_code_snippet(self, node: ASTNode, max_length: int = 200) -> str:
        """获取代码片段"""
        return node.text[:max_length]
    
    def create_finding(
        self,
        node: ASTNode,
        file_path: str,
        message: str,
        suggestion: Optional[str] = None
    ) -> Finding:
        """便捷方法：创建发现项"""
        return Finding(
            rule_id=self.rule_id,
            message=message,
            severity=self.severity,
            file_path=file_path,
            line_number=self.get_line_number(node),
            column_number=self.get_column_number(node),
            suggestion=suggestion,
            code_snippet=self.get_code_snippet(node)
        )
    
    def find_calls(self, ast: ASTNode, function_name: str) -> List[ASTNode]:
        """查找特定函数调用"""
        return ast.find_call_expression(function_name)
    
    def contains_text(self, node: ASTNode, text: str) -> bool:
        """检查节点是否包含特定文本"""
        return text in node.text


class RuleRegistry:
    """
    规则注册表
    
    管理所有可用的AST规则。
    """
    
    _rules: Dict[str, ASTBasedRule] = {}
    
    @classmethod
    def register(cls, rule: ASTBasedRule) -> None:
        """注册规则"""
        cls._rules[rule.rule_id] = rule
    
    @classmethod
    def get_rule(cls, rule_id: str) -> Optional[ASTBasedRule]:
        """获取规则"""
        return cls._rules.get(rule_id)
    
    @classmethod
    def get_all_rules(cls) -> List[ASTBasedRule]:
        """获取所有规则"""
        return list(cls._rules.values())
    
    @classmethod
    def get_rules_by_category(cls, category: RuleCategory) -> List[ASTBasedRule]:
        """按类别获取规则"""
        return [r for r in cls._rules.values() if r.category == category]
    
    @classmethod
    def clear(cls) -> None:
        """清空注册表"""
        cls._rules.clear()


def register_rule(rule_class: type) -> type:
    """装饰器：自动注册规则类"""
    rule_instance = rule_class()
    RuleRegistry.register(rule_instance)
    return rule_class
