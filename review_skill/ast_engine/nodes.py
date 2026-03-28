"""
AST Node Definitions - AST节点定义

定义抽象语法树的节点类型和操作。
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Callable, Iterator
from enum import Enum


class NodeType(Enum):
    """Kotlin AST节点类型"""
    # 声明
    FILE = "file"
    PACKAGE_HEADER = "package_header"
    IMPORT_LIST = "import_list"
    IMPORT_HEADER = "import_header"
    
    # 类/接口声明
    CLASS_DECLARATION = "class_declaration"
    OBJECT_DECLARATION = "object_declaration"
    COMPANION_OBJECT = "companion_object"
    INTERFACE_DECLARATION = "interface_declaration"
    
    # 函数声明
    FUNCTION_DECLARATION = "function_declaration"
    PROPERTY_DECLARATION = "property_declaration"
    
    # 表达式
    CALL_EXPRESSION = "call_expression"
    DOT_QUALIFIED_EXPRESSION = "dot_qualified_expression"
    NAVIGATION_EXPRESSION = "navigation_expression"
    LAMBDA_EXPRESSION = "lambda_expression"
    FUNCTION_LITERAL = "function_literal"
    
    # 控制流
    IF_EXPRESSION = "if_expression"
    WHEN_EXPRESSION = "when_expression"
    FOR_STATEMENT = "for_statement"
    WHILE_STATEMENT = "while_statement"
    DO_WHILE_STATEMENT = "do_while_statement"
    TRY_EXPRESSION = "try_expression"
    
    # 协程相关
    COROUTINE_CONTEXT = "coroutine_context"
    SUSPEND_MODIFIER = "suspend_modifier"
    
    # 基础
    IDENTIFIER = "identifier"
    SIMPLE_IDENTIFIER = "simple_identifier"
    STRING_LITERAL = "string_literal"
    INTEGER_LITERAL = "integer_literal"
    BOOLEAN_LITERAL = "boolean_literal"
    NULL_LITERAL = "null_literal"
    
    # 类型
    TYPE_REFERENCE = "type_reference"
    USER_TYPE = "user_type"
    FUNCTION_TYPE = "function_type"
    
    # 其他
    BLOCK = "block"
    STATEMENT = "statement"
    COMMENT = "comment"
    UNKNOWN = "unknown"


@dataclass
class Position:
    """代码位置信息"""
    line: int
    column: int
    offset: int = 0
    
    def __repr__(self) -> str:
        return f"Position(line={self.line}, column={self.column})"


@dataclass
class SourceRange:
    """源代码范围"""
    start: Position
    end: Position
    
    def __repr__(self) -> str:
        return f"SourceRange({self.start} - {self.end})"


@dataclass
class ASTNode:
    """
    AST节点基类
    
    表示抽象语法树中的一个节点。
    """
    node_type: NodeType
    text: str
    range: SourceRange
    children: List['ASTNode'] = field(default_factory=list)
    parent: Optional['ASTNode'] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """初始化后设置父节点引用"""
        for child in self.children:
            child.parent = self
    
    # ==================== 查询方法 ====================
    
    def find_all(self, node_type: NodeType) -> List['ASTNode']:
        """递归查找所有指定类型的节点"""
        results = []
        if self.node_type == node_type:
            results.append(self)
        for child in self.children:
            results.extend(child.find_all(node_type))
        return results
    
    def find_first(self, node_type: NodeType) -> Optional['ASTNode']:
        """查找第一个指定类型的节点"""
        if self.node_type == node_type:
            return self
        for child in self.children:
            result = child.find_first(node_type)
            if result:
                return result
        return None
    
    def find_parent(self, node_type: NodeType) -> Optional['ASTNode']:
        """向上查找指定类型的父节点"""
        current = self.parent
        while current:
            if current.node_type == node_type:
                return current
            current = current.parent
        return None
    
    def find_ancestors(self, node_type: Optional[NodeType] = None) -> List['ASTNode']:
        """查找所有祖先节点"""
        results = []
        current = self.parent
        while current:
            if node_type is None or current.node_type == node_type:
                results.append(current)
            current = current.parent
        return results
    
    def find_children(self, node_type: NodeType) -> List['ASTNode']:
        """查找直接子节点中指定类型的节点"""
        return [child for child in self.children if child.node_type == node_type]
    
    def find_by_text(self, text: str) -> List['ASTNode']:
        """查找包含指定文本的所有节点"""
        results = []
        if text in self.text:
            results.append(self)
        for child in self.children:
            results.extend(child.find_by_text(text))
        return results
    
    def find_call_expression(self, function_name: str) -> List['ASTNode']:
        """查找特定的函数调用表达式"""
        results = []
        calls = self.find_all(NodeType.CALL_EXPRESSION)
        for call in calls:
            if function_name in call.text:
                results.append(call)
        return results
    
    # ==================== 属性访问 ====================
    
    @property
    def line_number(self) -> int:
        """获取行号（1-based）"""
        return self.range.start.line + 1
    
    @property
    def column_number(self) -> int:
        """获取列号（1-based）"""
        return self.range.start.column + 1
    
    @property
    def is_leaf(self) -> bool:
        """是否为叶子节点"""
        return len(self.children) == 0
    
    @property
    def depth(self) -> int:
        """节点深度"""
        if not self.parent:
            return 0
        return self.parent.depth + 1
    
    # ==================== 遍历方法 ====================
    
    def traverse(self, visitor: Callable[['ASTNode'], bool]) -> None:
        """
        遍历树，访问每个节点
        
        Args:
            visitor: 访问函数，返回False则停止遍历该分支
        """
        if not visitor(self):
            return
        for child in self.children:
            child.traverse(visitor)
    
    def __iter__(self) -> Iterator['ASTNode']:
        """迭代器，深度优先遍历"""
        yield self
        for child in self.children:
            yield from child
    
    def __repr__(self) -> str:
        return f"ASTNode({self.node_type.value}, line={self.line_number}, text={self.text[:30]!r})"


class ASTVisitor:
    """
    AST访问器基类
    
    实现访问者模式，用于遍历和处理AST节点。
    """
    
    def __init__(self):
        self.findings: List[Dict[str, Any]] = []
    
    def visit(self, node: ASTNode) -> None:
        """访问节点入口"""
        method_name = f"visit_{node.node_type.value}"
        visitor_method = getattr(self, method_name, self.generic_visit)
        visitor_method(node)
        
        # 递归访问子节点
        for child in node.children:
            self.visit(child)
    
    def generic_visit(self, node: ASTNode) -> None:
        """通用访问方法"""
        pass
    
    def visit_file(self, node: ASTNode) -> None:
        """访问文件节点"""
        pass
    
    def visit_function_declaration(self, node: ASTNode) -> None:
        """访问函数声明节点"""
        pass
    
    def visit_call_expression(self, node: ASTNode) -> None:
        """访问调用表达式节点"""
        pass
    
    def visit_class_declaration(self, node: ASTNode) -> None:
        """访问类声明节点"""
        pass
    
    def add_finding(self, 
                   node: ASTNode, 
                   rule_id: str, 
                   message: str,
                   severity: str = "warning") -> None:
        """添加发现项"""
        self.findings.append({
            "rule": rule_id,
            "message": message,
            "severity": severity,
            "line": node.line_number,
            "column": node.column_number,
            "code_snippet": node.text[:200]
        })


class ASTNodeBuilder:
    """
    AST节点构建器
    
    用于简化AST节点的创建。
    """
    
    @staticmethod
    def create_file_node(text: str, children: List[ASTNode] = None) -> ASTNode:
        """创建文件根节点"""
        lines = text.split('\n')
        end_line = len(lines)
        end_column = len(lines[-1]) if lines else 0
        
        return ASTNode(
            node_type=NodeType.FILE,
            text=text,
            range=SourceRange(
                start=Position(line=0, column=0),
                end=Position(line=end_line - 1, column=end_column)
            ),
            children=children or []
        )
    
    @staticmethod
    def create_simple_node(
        node_type: NodeType,
        text: str,
        line: int = 0,
        column: int = 0,
        children: List[ASTNode] = None
    ) -> ASTNode:
        """创建简单节点"""
        end_column = column + len(text)
        return ASTNode(
            node_type=node_type,
            text=text,
            range=SourceRange(
                start=Position(line=line, column=column),
                end=Position(line=line, column=end_column)
            ),
            children=children or []
        )


# ==================== 便捷函数 ====================

def is_coroutine_function(node: ASTNode) -> bool:
    """检查节点是否为挂起函数"""
    if node.node_type != NodeType.FUNCTION_DECLARATION:
        return False
    # 检查是否有suspend修饰符
    modifiers = node.find_children(NodeType.SUSPEND_MODIFIER)
    return len(modifiers) > 0 or 'suspend' in node.text


def get_function_name(node: ASTNode) -> Optional[str]:
    """获取函数名称"""
    if node.node_type != NodeType.FUNCTION_DECLARATION:
        return None
    identifier = node.find_first(NodeType.SIMPLE_IDENTIFIER)
    return identifier.text if identifier else None


def contains_node_type(root: ASTNode, node_type: NodeType) -> bool:
    """检查树中是否包含指定类型的节点"""
    return root.find_first(node_type) is not None


def find_all_calls(root: ASTNode, function_name: str) -> List[ASTNode]:
    """查找所有特定函数调用"""
    calls = root.find_all(NodeType.CALL_EXPRESSION)
    return [call for call in calls if function_name in call.text]
