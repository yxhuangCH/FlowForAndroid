"""Unified Execution Context

统一执行上下文实现

本模块提供 UnifiedContext 类，它是统一引擎的核心组件，提供：
- 按需 AST 解析（延迟加载）
- 正则模式匹配
- AST 查询接口
- 代码行级操作
"""

import re
from typing import List, Dict, Any, Optional, Match, TYPE_CHECKING
from dataclasses import dataclass

# AST 相关导入
from ast_engine.parser_v2 import parse_kotlin_ast
from ast_engine.nodes import ASTNode

if TYPE_CHECKING:
    from ast_engine.nodes import NodeType


@dataclass
class LineMatch:
    """行匹配结果"""

    line_number: int  # 1-based
    line_content: str
    match: Match


class UnifiedContext:
    """统一执行上下文

    为规则执行提供统一的上下文环境。核心特性是"按需 AST 解析"，
    即 AST 只在首次访问时才会被解析，避免不必要的开销。

    Example:
        ```python
        context = UnifiedContext(code, file_path)

        # 快速正则匹配（不触发 AST 解析）
        matches = context.find_pattern(r"GlobalScope\.\w+")

        # 行级操作（不触发 AST 解析）
        line_numbers = context.find_pattern_in_lines(r"GlobalScope")

        # AST 查询（首次访问时触发 AST 解析）
        nodes = context.query_ast("Call[receiver='GlobalScope']")

        # 直接访问 AST（已解析则直接返回）
        ast = context.ast
        ```
    """

    def __init__(
        self, code: str, file_path: str, language: str = "kotlin", file_hash: str = ""
    ):
        """初始化统一上下文

        Args:
            code: 源代码内容
            file_path: 文件路径
            language: 编程语言（默认 kotlin）
            file_hash: 文件哈希值（用于缓存）
        """
        self._code = code
        self._file_path = file_path
        self._language = language
        self._file_hash = file_hash

        # AST 延迟解析相关
        self._ast: Optional[ASTNode] = None
        self._ast_parsed = False
        self._ast_parse_error: Optional[Exception] = None

        # 内部缓存
        self._cache: Dict[str, Any] = {}
        self._lines_cache: Optional[List[str]] = None

    # ==================== 基本属性 ====================

    @property
    def code(self) -> str:
        """源代码内容"""
        return self._code

    @property
    def file_path(self) -> str:
        """文件路径"""
        return self._file_path

    @property
    def language(self) -> str:
        """编程语言"""
        return self._language

    @property
    def file_hash(self) -> str:
        """文件哈希值"""
        return self._file_hash

    @property
    def ast(self) -> Optional[ASTNode]:
        """AST 节点 - 按需解析

        首次访问时会触发 AST 解析，后续访问直接返回缓存的 AST。
        如果解析失败，返回 None。

        Returns:
            ASTNode: 解析后的 AST 根节点，或 None（如果解析失败）
        """
        if not self._ast_parsed:
            self._ast = self._parse_ast()
            self._ast_parsed = True
        return self._ast

    @property
    def ast_available(self) -> bool:
        """AST 是否可用"""
        return self.ast is not None

    # ==================== 正则匹配 ====================

    def find_pattern(
        self, pattern: str, case_sensitive: bool = True
    ) -> List[Match[str]]:
        """在代码中查找正则模式

        此操作不会触发 AST 解析，是纯文本匹配。

        Args:
            pattern: 正则表达式模式
            case_sensitive: 是否区分大小写

        Returns:
            List[Match]: 匹配对象列表
        """
        flags = 0 if case_sensitive else re.IGNORECASE
        return list(re.finditer(pattern, self._code, flags))

    def find_pattern_with_lines(
        self, pattern: str, case_sensitive: bool = True
    ) -> List[LineMatch]:
        """查找模式并返回行信息

        Args:
            pattern: 正则表达式模式
            case_sensitive: 是否区分大小写

        Returns:
            List[LineMatch]: 包含行号的匹配结果列表
        """
        matches = self.find_pattern(pattern, case_sensitive)
        results = []
        lines = self._get_lines()

        for match in matches:
            # 计算行号
            line_number = self._code[: match.start()].count("\n") + 1
            line_content = lines[line_number - 1] if line_number <= len(lines) else ""
            results.append(LineMatch(line_number, line_content, match))

        return results

    def find_pattern_in_lines(self, pattern: str) -> List[int]:
        """在代码行中查找模式

        返回匹配的行号列表（1-based）。此操作不会触发 AST 解析。

        Args:
            pattern: 正则表达式模式

        Returns:
            List[int]: 匹配的行号列表（1-based）
        """
        lines = self._get_lines()
        matches = []
        for i, line in enumerate(lines, 1):
            if re.search(pattern, line):
                matches.append(i)
        return matches

    def contains_pattern(self, pattern: str, case_sensitive: bool = True) -> bool:
        """检查代码是否包含指定模式

        Args:
            pattern: 正则表达式模式
            case_sensitive: 是否区分大小写

        Returns:
            bool: 是否包含匹配
        """
        flags = 0 if case_sensitive else re.IGNORECASE
        return re.search(pattern, self._code, flags) is not None

    # ==================== AST 查询 ====================

    def query_ast(self, selector: str) -> List[ASTNode]:
        """使用 CSS-like 选择器查询 AST

        支持的简单选择器语法：
        - "Function" - 查找所有函数声明
        - "Call[name='launch']" - 查找指定名称的调用
        - "Call[receiver='GlobalScope']" - 查找指定接收者的调用

        Args:
            selector: CSS-like 选择器字符串

        Returns:
            List[ASTNode]: 匹配的 AST 节点列表
        """
        if not self.ast:
            return []
        return self._execute_selector(selector)

    def find_nodes_by_type(self, node_type: "NodeType") -> List[ASTNode]:
        """按类型查找 AST 节点

        Args:
            node_type: 节点类型

        Returns:
            List[ASTNode]: 匹配的节点列表
        """
        if not self.ast:
            return []
        return self.ast.find_all(node_type)

    def find_first_node_by_type(self, node_type: "NodeType") -> Optional[ASTNode]:
        """查找第一个指定类型的 AST 节点

        Args:
            node_type: 节点类型

        Returns:
            Optional[ASTNode]: 第一个匹配的节点，或 None
        """
        if not self.ast:
            return None
        return self.ast.find_first(node_type)

    def find_call_expressions(self, function_name: str) -> List[ASTNode]:
        """查找指定的函数调用表达式

        Args:
            function_name: 函数名称（如 "launch", "GlobalScope.launch"）

        Returns:
            List[ASTNode]: 调用表达式节点列表
        """
        if not self.ast:
            return []
        return self.ast.find_call_expression(function_name)

    # ==================== 代码行操作 ====================

    def get_lines(self) -> List[str]:
        """获取代码行列表

        Returns:
            List[str]: 代码行列表
        """
        return self._get_lines()

    def get_line_at(self, line_number: int) -> str:
        """获取指定行的内容

        Args:
            line_number: 行号（1-based）

        Returns:
            str: 行内容，如果行号无效则返回空字符串
        """
        lines = self._get_lines()
        if 1 <= line_number <= len(lines):
            return lines[line_number - 1]
        return ""

    def get_code_at_range(
        self, start_line: int, end_line: int, include_line_numbers: bool = False
    ) -> str:
        """获取指定行范围的代码

        Args:
            start_line: 起始行号（1-based，包含）
            end_line: 结束行号（1-based，包含）
            include_line_numbers: 是否包含行号

        Returns:
            str: 代码片段
        """
        lines = self._get_lines()
        if start_line < 1:
            start_line = 1
        if end_line > len(lines):
            end_line = len(lines)

        selected_lines = lines[start_line - 1 : end_line]

        if include_line_numbers:
            selected_lines = [
                f"{i + start_line:4d} | {line}"
                for i, line in enumerate(selected_lines)
            ]

        return "\n".join(selected_lines)

    def get_line_count(self) -> int:
        """获取代码总行数"""
        return len(self._get_lines())

    # ==================== 缓存接口 ====================

    def get_cached(self, key: str, default: Any = None) -> Any:
        """获取缓存值

        Args:
            key: 缓存键
            default: 默认值

        Returns:
            Any: 缓存值或默认值
        """
        return self._cache.get(key, default)

    def set_cached(self, key: str, value: Any) -> None:
        """设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
        """
        self._cache[key] = value

    def clear_cache(self) -> None:
        """清除内部缓存"""
        self._cache.clear()
        self._lines_cache = None

    # ==================== 私有方法 ====================

    def _get_lines(self) -> List[str]:
        """获取代码行列表（带缓存）"""
        if self._lines_cache is None:
            self._lines_cache = self._code.split("\n")
        return self._lines_cache

    def _parse_ast(self) -> Optional[ASTNode]:
        """解析 AST

        Returns:
            Optional[ASTNode]: 解析后的 AST，或 None（如果解析失败）
        """
        try:
            if self._language == "kotlin":
                return parse_kotlin_ast(self._code)
            else:
                # 其他语言暂不支持
                self._ast_parse_error = NotImplementedError(
                    f"Language '{self._language}' is not supported for AST parsing"
                )
                return None
        except Exception as e:
            self._ast_parse_error = e
            return None

    def _execute_selector(self, selector: str) -> List[ASTNode]:
        """执行 AST 选择器

        当前支持简单的选择器语法：
        - "NodeType" - 按节点类型查找
        - "NodeType[name='xxx']" - 按名称属性查找
        - "NodeType[receiver='xxx']" - 按接收者属性查找

        Args:
            selector: 选择器字符串

        Returns:
            List[ASTNode]: 匹配的节点列表
        """
        from ast_engine.nodes import NodeType

        if not self.ast:
            return []

        # 解析简单选择器
        selector = selector.strip()

        # 解析属性条件 [key='value']
        attr_conditions = {}
        if "[" in selector and "]" in selector:
            attr_start = selector.index("[")
            attr_end = selector.index("]")
            attr_str = selector[attr_start + 1 : attr_end]
            selector = selector[:attr_start]

            # 解析 key='value' 或 key="value"
            if "=" in attr_str:
                key, value = attr_str.split("=", 1)
                key = key.strip()
                value = value.strip().strip("'\"")
                attr_conditions[key] = value

        # 根据节点类型查找
        results = []
        node_type_value = selector.strip()

        # 遍历所有节点
        for node in self.ast:
            # 检查节点类型是否匹配
            if node_type_value and node.node_type.value != node_type_value.lower():
                continue

            # 检查属性条件
            match = True
            for key, value in attr_conditions.items():
                if key == "name":
                    # 检查 metadata 中的 function_name, property_name 等
                    node_name = node.metadata.get("function_name") or node.metadata.get(
                        "property_name"
                    )
                    if node_name != value:
                        match = False
                        break
                elif key == "receiver":
                    # 检查调用表达式的接收者
                    callee_name = node.metadata.get("callee_name", "")
                    if not callee_name.startswith(value + "."):
                        match = False
                        break

            if match:
                results.append(node)

        return results

    def __repr__(self) -> str:
        ast_status = "parsed" if self._ast_parsed else "lazy"
        if self._ast_parsed and self._ast is None:
            ast_status = "failed"
        return f"UnifiedContext({self._file_path}, {self._language}, ast={ast_status})"
