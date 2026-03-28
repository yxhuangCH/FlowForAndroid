"""
Robust Kotlin Parser - 健壮的Kotlin解析器

处理复杂Kotlin代码的简化解析器，专注于代码审查所需的关键结构
"""

import re
from typing import List, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class Position:
    line: int
    column: int
    offset: int


@dataclass
class SourceRange:
    start: Position
    end: Position


@dataclass
class ASTNode:
    node_type: str
    text: str
    range: SourceRange
    children: List['ASTNode'] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.children is None:
            self.children = []
        if self.metadata is None:
            self.metadata = {}


class RobustKotlinParser:
    """健壮的Kotlin解析器 - 处理真实代码"""
    
    def __init__(self, source: str):
        self.source = source
        self.lines = source.splitlines()
        self.pos = 0
        self.length = len(source)
    
    def parse(self) -> ASTNode:
        """解析Kotlin文件为AST"""
        children = []
        
        # 使用正则表达式提取关键结构
        patterns = [
            (r'package\s+([\w.]+)', 'PACKAGE'),
            (r'import\s+([\w.*]+)', 'IMPORT'),
            (r'class\s+(\w+)', 'CLASS'),
            (r'interface\s+(\w+)', 'INTERFACE'),
            (r'object\s+(\w+)', 'OBJECT'),
            (r'companion\s+object', 'COMPANION_OBJECT'),
            (r'fun\s+(\w+)', 'FUNCTION'),
            (r'val\s+(\w+)', 'PROPERTY_VAL'),
            (r'var\s+(\w+)', 'PROPERTY_VAR'),
            (r'suspend\s+fun\s+(\w+)', 'SUSPEND_FUNCTION'),
        ]
        
        for line_num, line in enumerate(self.lines):
            line = line.strip()
            if not line or line.startswith('//') or line.startswith('/*'):
                continue
                
            for pattern, node_type in patterns:
                matches = re.finditer(pattern, line)
                for match in matches:
                    name = match.group(1) if match.groups() else ''
                    start_pos = Position(line_num, match.start(), 0)
                    end_pos = Position(line_num, match.end(), 0)
                    
                    metadata = {}
                    if node_type in ['CLASS', 'INTERFACE', 'OBJECT']:
                        metadata['class_name'] = name
                    elif node_type in ['FUNCTION', 'SUSPEND_FUNCTION']:
                        metadata['function_name'] = name
                        metadata['is_suspend'] = node_type == 'SUSPEND_FUNCTION'
                    elif node_type in ['PROPERTY_VAL', 'PROPERTY_VAR']:
                        metadata['property_name'] = name
                        metadata['is_mutable'] = node_type == 'PROPERTY_VAR'
                    
                    node = ASTNode(
                        node_type=node_type,
                        text=match.group(0),
                        range=SourceRange(start_pos, end_pos),
                        metadata=metadata
                    )
                    children.append(node)
        
        # 处理嵌套结构
        self._build_nesting_structure(children)
        
        return ASTNode(
            node_type='FILE',
            text=self.source,
            range=SourceRange(
                Position(0, 0, 0),
                Position(len(self.lines), 0, len(self.source))
            ),
            children=children
        )
    
    def _build_nesting_structure(self, nodes: List[ASTNode]):
        """构建嵌套结构 - 基于缩进和代码块"""
        stack = []
        
        for node in nodes:
            line_num = node.range.start.line
            if line_num < len(self.lines):
                line = self.lines[line_num]
                indent = len(line) - len(line.lstrip())
                
                # 找到合适的父节点
                while stack and stack[-1][1] >= indent:
                    stack.pop()
                
                if stack:
                    parent = stack[-1][0]
                    parent.children.append(node)
                
                stack.append((node, indent))
    
    def find_patterns(self, patterns: List[str]) -> List[Dict[str, Any]]:
        """查找特定代码模式"""
        findings = []
        
        for line_num, line in enumerate(self.lines):
            line = line.strip()
            for pattern in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    findings.append({
                        'pattern': pattern,
                        'line': line_num + 1,
                        'text': line.strip(),
                        'severity': 'WARNING'
                    })
        
        return findings


def parse_kotlin_simple(source: str) -> ASTNode:
    """简化的Kotlin解析器入口"""
    parser = RobustKotlinParser(source)
    return parser.parse()


def analyze_kotlin_patterns(source: str) -> Dict[str, Any]:
    """分析Kotlin代码模式"""
    parser = RobustKotlinParser(source)
    ast = parser.parse()
    
    # 定义检查规则
    patterns = {
        'global_scope': r'GlobalScope\.launch',
        'main_thread_io': r'Dispatchers\.Main.*IO',
        'unspecified_scope': r'launch\s*\{',
        'viewmodel_context': r'val.*Context.*Activity',
        'suspend_naming': r'fun\s+\w*[A-Z]\w*\s*\(',
    }
    
    findings = {}
    for rule_name, pattern in patterns.items():
        matches = parser.find_patterns([pattern])
        if matches:
            findings[rule_name] = matches
    
    # 统计信息
    stats = {
        'total_lines': len(source.splitlines()),
        'classes': len([n for n in ast.children if n.node_type in ['CLASS', 'INTERFACE', 'OBJECT']]),
        'functions': len([n for n in ast.children if 'FUNCTION' in n.node_type]),
        'properties': len([n for n in ast.children if 'PROPERTY' in n.node_type]),
        'suspend_functions': len([n for n in ast.children 
                               if n.node_type == 'SUSPEND_FUNCTION']),
    }
    
    return {
        'ast': ast,
        'findings': findings,
        'stats': stats
    }