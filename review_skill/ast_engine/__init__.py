"""
AST Engine - Kotlin AST解析引擎

提供基于抽象语法树的代码分析和规则检查能力。
"""

# v2 真正的Kotlin AST解析器 (推荐)
from .parser_v2 import parse_kotlin_ast, analyze_kotlin_file
from .nodes import ASTNode, ASTVisitor, NodeType, Position, SourceRange

# 向后兼容 - 旧版解析器
from .parser import KotlinASTParser, ASTParseError

__all__ = [
    # v2 API (推荐)
    'parse_kotlin_ast',
    'analyze_kotlin_file',
    # 数据模型
    'ASTNode',
    'ASTVisitor',
    'NodeType',
    'Position',
    'SourceRange',
    # v1 API (向后兼容)
    'KotlinASTParser',
    'ASTParseError',
]

__version__ = '2.0.0'
