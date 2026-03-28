"""
AST Parser - Kotlin AST解析器

由于tree-sitter安装限制，提供简化版的Kotlin AST解析器。
支持基本的Kotlin语法结构解析。
"""

import re
import hashlib
from typing import List, Optional, Tuple
from .nodes import ASTNode, NodeType, Position, SourceRange, ASTNodeBuilder


class ASTParseError(Exception):
    """AST解析错误"""
    pass


class KotlinASTParser:
    """
    Kotlin AST解析器
    
    使用正则表达式和简单语法分析构建AST。
    适用于常见Kotlin代码结构的分析。
    """
    
    def __init__(self):
        self.builder = ASTNodeBuilder()
        self.line_offsets = []
    
    def parse(self, code: str) -> ASTNode:
        """
        解析Kotlin代码为AST
        
        Args:
            code: Kotlin源代码
            
        Returns:
            AST根节点
        """
        self.line_offsets = self._calculate_line_offsets(code)
        
        children = []
        
        # 解析包声明
        package_node = self._parse_package(code)
        if package_node:
            children.append(package_node)
        
        # 解析导入语句
        import_nodes = self._parse_imports(code)
        children.extend(import_nodes)
        
        # 解析顶层声明（类、函数、属性等）
        declaration_nodes = self._parse_declarations(code)
        children.extend(declaration_nodes)
        
        # 创建文件根节点
        return ASTNodeBuilder.create_file_node(code, children)
    
    def parse_file(self, file_path: str) -> ASTNode:
        """
        解析Kotlin文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            AST根节点
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            return self.parse(code)
        except FileNotFoundError:
            raise ASTParseError(f"File not found: {file_path}")
        except UnicodeDecodeError:
            raise ASTParseError(f"Cannot decode file: {file_path}")
    
    def get_file_hash(self, content: str) -> str:
        """计算文件内容哈希"""
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def get_ast_hash(self, ast: ASTNode) -> str:
        """计算AST哈希"""
        return hashlib.md5(ast.text.encode('utf-8')).hexdigest()
    
    # ==================== 私有解析方法 ====================
    
    def _calculate_line_offsets(self, code: str) -> List[int]:
        """计算每行的起始偏移量"""
        offsets = [0]
        for i, char in enumerate(code):
            if char == '\n':
                offsets.append(i + 1)
        return offsets
    
    def _get_position(self, offset: int) -> Position:
        """将偏移量转换为行列位置"""
        line = 0
        for i, line_offset in enumerate(self.line_offsets):
            if line_offset > offset:
                line = i - 1
                break
            line = i
        
        column = offset - self.line_offsets[line] if line < len(self.line_offsets) else 0
        return Position(line=line, column=column, offset=offset)
    
    def _parse_package(self, code: str) -> Optional[ASTNode]:
        """解析包声明"""
        pattern = r'^\s*package\s+([\w.]+)'
        match = re.search(pattern, code, re.MULTILINE)
        if match:
            start_pos = self._get_position(match.start())
            end_pos = self._get_position(match.end())
            return ASTNode(
                node_type=NodeType.PACKAGE_HEADER,
                text=match.group(0),
                range=SourceRange(start=start_pos, end=end_pos),
                children=[]
            )
        return None
    
    def _parse_imports(self, code: str) -> List[ASTNode]:
        """解析导入语句"""
        pattern = r'^\s*import\s+([\w.*]+)(?:\s+as\s+(\w+))?'
        nodes = []
        for match in re.finditer(pattern, code, re.MULTILINE):
            start_pos = self._get_position(match.start())
            end_pos = self._get_position(match.end())
            node = ASTNode(
                node_type=NodeType.IMPORT_HEADER,
                text=match.group(0),
                range=SourceRange(start=start_pos, end=end_pos),
                children=[]
            )
            nodes.append(node)
        return nodes
    
    def _parse_declarations(self, code: str) -> List[ASTNode]:
        """解析顶层声明"""
        nodes = []
        
        # 解析类声明
        class_nodes = self._parse_classes(code)
        nodes.extend(class_nodes)
        
        # 解析函数声明
        function_nodes = self._parse_functions(code)
        nodes.extend(function_nodes)
        
        # 解析属性声明
        property_nodes = self._parse_properties(code)
        nodes.extend(property_nodes)
        
        # 解析对象声明
        object_nodes = self._parse_objects(code)
        nodes.extend(object_nodes)
        
        return nodes
    
    def _parse_classes(self, code: str) -> List[ASTNode]:
        """解析类声明"""
        # 匹配类、接口、数据类、密封类等
        pattern = r'(abstract\s+)?(sealed\s+)?(data\s+)?(class|interface|enum\s+class)\s+(\w+)'
        nodes = []
        for match in re.finditer(pattern, code):
            start_pos = self._get_position(match.start())
            end_pos = self._get_position(match.end())
            
            # 提取类体
            class_name = match.group(5)
            body_start = match.end()
            body = self._extract_body(code, body_start)
            
            children = []
            if body:
                # 递归解析类体内部
                inner_functions = self._parse_functions(body)
                inner_properties = self._parse_properties(body)
                children.extend(inner_functions)
                children.extend(inner_properties)
            
            node = ASTNode(
                node_type=NodeType.CLASS_DECLARATION,
                text=match.group(0) + (body or ''),
                range=SourceRange(start=start_pos, end=end_pos),
                children=children,
                metadata={'class_name': class_name}
            )
            nodes.append(node)
        
        return nodes
    
    def _parse_functions(self, code: str) -> List[ASTNode]:
        """解析函数声明"""
        # 匹配函数声明，包括挂起函数
        pattern = r'(override\s+)?(abstract\s+)?(suspend\s+)?fun\s+(?:<\w+>\s+)?(\w+)\s*\([^)]*\)'
        nodes = []
        for match in re.finditer(pattern, code):
            start_pos = self._get_position(match.start())
            end_pos = self._get_position(match.end())
            
            function_name = match.group(4)
            is_suspend = 'suspend' in match.group(0)
            
            # 提取函数体
            func_start = match.end()
            body = self._extract_body(code, func_start)
            
            children = []
            if body:
                # 解析函数体内的调用表达式
                call_nodes = self._parse_call_expressions(body)
                children.extend(call_nodes)
            
            node = ASTNode(
                node_type=NodeType.FUNCTION_DECLARATION,
                text=match.group(0) + (body or ''),
                range=SourceRange(start=start_pos, end=end_pos),
                children=children,
                metadata={
                    'function_name': function_name,
                    'is_suspend': is_suspend
                }
            )
            nodes.append(node)
        
        return nodes
    
    def _parse_properties(self, code: str) -> List[ASTNode]:
        """解析属性声明"""
        pattern = r'(val|var)\s+(?:lateinit\s+)?(\w+)\s*:'
        nodes = []
        for match in re.finditer(pattern, code):
            start_pos = self._get_position(match.start())
            end_pos = self._get_position(match.end())
            node = ASTNode(
                node_type=NodeType.PROPERTY_DECLARATION,
                text=match.group(0),
                range=SourceRange(start=start_pos, end=end_pos),
                children=[]
            )
            nodes.append(node)
        return nodes
    
    def _parse_objects(self, code: str) -> List[ASTNode]:
        """解析对象声明"""
        pattern = r'(companion\s+)?object\s+(?:(\w+)\s*)?'
        nodes = []
        for match in re.finditer(pattern, code):
            start_pos = self._get_position(match.start())
            end_pos = self._get_position(match.end())
            
            is_companion = 'companion' in match.group(0)
            object_name = match.group(2) or 'anonymous'
            
            node_type = NodeType.COMPANION_OBJECT if is_companion else NodeType.OBJECT_DECLARATION
            
            node = ASTNode(
                node_type=node_type,
                text=match.group(0),
                range=SourceRange(start=start_pos, end=end_pos),
                children=[],
                metadata={'object_name': object_name}
            )
            nodes.append(node)
        return nodes
    
    def _parse_call_expressions(self, code: str) -> List[ASTNode]:
        """解析调用表达式"""
        # 匹配函数调用，包括链式调用
        pattern = r'(\w+(?:\.\w+)*)\s*\([^)]*\)'
        nodes = []
        for match in re.finditer(pattern, code):
            start_pos = self._get_position(match.start())
            end_pos = self._get_position(match.end())
            
            call_text = match.group(0)
            receiver = match.group(1)
            
            # 识别特定的协程调用
            is_coroutine_call = any(keyword in call_text for keyword in [
                'launch', 'async', 'runBlocking', 'withContext',
                'GlobalScope', 'lifecycleScope', 'viewModelScope'
            ])
            
            node = ASTNode(
                node_type=NodeType.CALL_EXPRESSION,
                text=call_text,
                range=SourceRange(start=start_pos, end=end_pos),
                children=[],
                metadata={
                    'receiver': receiver,
                    'is_coroutine_call': is_coroutine_call
                }
            )
            nodes.append(node)
        return nodes
    
    def _extract_body(self, code: str, start_pos: int) -> Optional[str]:
        """提取代码块体（花括号包围的内容）"""
        # 跳过空白字符
        i = start_pos
        while i < len(code) and code[i] in ' \t\n':
            i += 1
        
        if i >= len(code) or code[i] != '{':
            return None
        
        # 匹配花括号
        brace_count = 0
        start = i
        while i < len(code):
            if code[i] == '{':
                brace_count += 1
            elif code[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    return code[start:i+1]
            elif code[i] == '"':
                # 跳过字符串
                i = self._skip_string(code, i)
                continue
            i += 1
        
        return None
    
    def _skip_string(self, code: str, start: int) -> int:
        """跳过字符串字面量"""
        i = start + 1
        while i < len(code):
            if code[i] == '\\':
                i += 2
            elif code[i] == '"':
                return i
            else:
                i += 1
        return i


class SimpleKotlinParser:
    """
    简化版Kotlin解析器
    
    针对特定模式的快速解析，用于规则检查。
    """
    
    @staticmethod
    def find_pattern(code: str, pattern: str) -> List[Tuple[int, str]]:
        """查找代码中的特定模式"""
        results = []
        for match in re.finditer(pattern, code):
            line = code[:match.start()].count('\n') + 1
            results.append((line, match.group(0)))
        return results
    
    @staticmethod
    def contains_globalscope(code: str) -> List[Tuple[int, str]]:
        """检测GlobalScope使用"""
        pattern = r'GlobalScope\.(launch|async)'
        return SimpleKotlinParser.find_pattern(code, pattern)
    
    @staticmethod
    def contains_main_thread_io(code: str) -> List[Tuple[int, str]]:
        """检测主线程IO操作"""
        io_patterns = [
            r'Dispatchers\.Main.*\.(readText|writeText|readBytes|writeBytes)',
            r'withContext\(Dispatchers\.Main\).*\.(read|write|openConnection)',
        ]
        results = []
        for pattern in io_patterns:
            results.extend(SimpleKotlinParser.find_pattern(code, pattern))
        return results
    
    @staticmethod
    def contains_unspecified_scope(code: str) -> List[Tuple[int, str]]:
        """检测未指定作用域的协程启动"""
        # 匹配直接的 launch { } 或 async { } 但没有明确作用域
        pattern = r'(?<!\.)\b(launch|async)\s*\{[^}]*\}'
        return SimpleKotlinParser.find_pattern(code, pattern)
    
    @staticmethod
    def contains_compose_remember_issues(code: str) -> List[Tuple[int, str]]:
        """检测Compose remember问题"""
        # 检测 remember { mutableStateOf(...) }
        pattern = r'remember\s*\{[^}]*mutableStateOf'
        return SimpleKotlinParser.find_pattern(code, pattern)
    
    @staticmethod
    def contains_viewmodel_context(code: str) -> List[Tuple[int, str]]:
        """检测ViewModel持有Context"""
        # 检测ViewModel中有Context类型的属性
        pattern = r'class\s+\w+ViewModel.*\{[^}]*val\s+\w+:\s*Context'
        return SimpleKotlinParser.find_pattern(code, pattern, re.DOTALL)


def parse_kotlin_simple(code: str) -> ASTNode:
    """便捷函数：简化解析"""
    parser = KotlinASTParser()
    return parser.parse(code)
