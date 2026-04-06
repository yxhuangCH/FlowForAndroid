"""
AST Engine - Internal AST解析引擎

DEPRECATION NOTICE:
This module is now internal to unified_engine.
外部用户不应直接使用此模块 - 请使用 unified_engine 代替。
For internal use only.
"""

import warnings

warnings.warn(
    "ast_engine is for internal use only. Use unified_engine instead. "
    "See docs/MIGRATION_GUIDE.md",
    DeprecationWarning,
    stacklevel=2
)

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
