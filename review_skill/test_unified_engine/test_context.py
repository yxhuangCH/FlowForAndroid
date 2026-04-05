"""Tests for unified_engine/context.py"""

import unittest

from unified_engine.context import UnifiedContext, LineMatch


class TestUnifiedContext(unittest.TestCase):
    """测试 UnifiedContext"""

    def setUp(self):
        """设置测试数据"""
        self.sample_code = """package com.example

import kotlinx.coroutines.*

class MyClass {
    fun test() {
        GlobalScope.launch {
            // Do something
        }
    }
}
"""
        self.context = UnifiedContext(
            code=self.sample_code,
            file_path="/test/MyClass.kt",
            language="kotlin",
        )

    def test_basic_properties(self):
        """测试基本属性"""
        self.assertEqual(self.context.code, self.sample_code)
        self.assertEqual(self.context.file_path, "/test/MyClass.kt")
        self.assertEqual(self.context.language, "kotlin")

    def test_get_lines(self):
        """测试获取代码行"""
        lines = self.context.get_lines()
        self.assertEqual(len(lines), 12)  # 包括空行
        self.assertEqual(lines[0], "package com.example")
        self.assertEqual(lines[2], "import kotlinx.coroutines.*")

    def test_get_line_at(self):
        """测试获取指定行"""
        self.assertEqual(self.context.get_line_at(1), "package com.example")
        self.assertEqual(self.context.get_line_at(3), "import kotlinx.coroutines.*")
        self.assertEqual(self.context.get_line_at(100), "")  # 越界返回空
        self.assertEqual(self.context.get_line_at(0), "")  # 越界返回空

    def test_get_line_count(self):
        """测试获取行数"""
        self.assertEqual(self.context.get_line_count(), 12)

    def test_find_pattern(self):
        """测试正则匹配"""
        matches = self.context.find_pattern(r"GlobalScope\.\w+")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].group(), "GlobalScope.launch")

    def test_find_pattern_case_insensitive(self):
        """测试不区分大小写的匹配"""
        matches = self.context.find_pattern(r"globalscope", case_sensitive=False)
        self.assertEqual(len(matches), 1)

    def test_find_pattern_with_lines(self):
        """测试带行号的匹配"""
        matches = self.context.find_pattern_with_lines(r"GlobalScope")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].line_number, 7)  # 1-based
        self.assertIn("GlobalScope", matches[0].line_content)

    def test_find_pattern_in_lines(self):
        """测试行级匹配"""
        line_numbers = self.context.find_pattern_in_lines(r"fun ")
        self.assertEqual(len(line_numbers), 1)
        self.assertEqual(line_numbers[0], 6)  # fun test()

    def test_contains_pattern(self):
        """测试包含模式检查"""
        self.assertTrue(self.context.contains_pattern(r"GlobalScope"))
        self.assertFalse(self.context.contains_pattern(r"NonExistent"))

    def test_get_code_at_range(self):
        """测试获取代码范围"""
        code = self.context.get_code_at_range(1, 3)
        self.assertIn("package com.example", code)
        self.assertIn("import kotlinx.coroutines.*", code)

    def test_get_code_at_range_with_line_numbers(self):
        """测试带行号的代码范围"""
        code = self.context.get_code_at_range(1, 3, include_line_numbers=True)
        self.assertIn("1 | package com.example", code)
        self.assertIn("3 | import kotlinx.coroutines.*", code)

    def test_cache_operations(self):
        """测试缓存操作"""
        # 设置缓存
        self.context.set_cached("test_key", "test_value")
        self.assertEqual(self.context.get_cached("test_key"), "test_value")

        # 获取不存在的键
        self.assertIsNone(self.context.get_cached("non_existent"))

        # 获取带默认值的缓存
        self.assertEqual(
            self.context.get_cached("non_existent", default="default"), "default"
        )

        # 清除缓存
        self.context.clear_cache()
        self.assertIsNone(self.context.get_cached("test_key"))

    def test_lazy_ast_parsing(self):
        """测试延迟 AST 解析"""
        # 创建新上下文
        context = UnifiedContext(
            code="fun test() {}",
            file_path="/test/Test.kt",
            language="kotlin",
        )

        # 未访问 ast 前，不应该解析
        # 注意：由于无法直接检查私有变量，我们通过行为来验证
        # 如果 ast 解析出错，ast_available 应该返回 False

        # 首次访问 ast 会触发解析
        ast = context.ast
        self.assertIsNotNone(ast)
        self.assertTrue(context.ast_available)

    def test_ast_query(self):
        """测试 AST 查询"""
        context = UnifiedContext(
            code="""fun main() {
    GlobalScope.launch { }
}
""",
            file_path="/test/Test.kt",
            language="kotlin",
        )

        # 查询函数声明
        nodes = context.query_ast("function_declaration")
        self.assertGreaterEqual(len(nodes), 1)

    def test_find_nodes_by_type(self):
        """测试按类型查找节点"""
        from ast_engine.nodes import NodeType

        context = UnifiedContext(
            code="fun test() {}",
            file_path="/test/Test.kt",
            language="kotlin",
        )

        nodes = context.find_nodes_by_type(NodeType.FUNCTION_DECLARATION)
        self.assertGreaterEqual(len(nodes), 1)

    def test_find_call_expressions(self):
        """测试查找调用表达式"""
        context = UnifiedContext(
            code="""fun test() {
    println("hello")
}
""",
            file_path="/test/Test.kt",
            language="kotlin",
        )

        calls = context.find_call_expressions("println")
        # 注意：解析器可能将 println 识别为调用表达式
        # 这里只是测试接口是否正常工作

    def test_repr(self):
        """测试字符串表示"""
        repr_str = repr(self.context)
        self.assertIn("UnifiedContext", repr_str)
        self.assertIn("/test/MyClass.kt", repr_str)


class TestLineMatch(unittest.TestCase):
    """测试 LineMatch"""

    def test_line_match_creation(self):
        """测试创建 LineMatch"""
        import re

        match = re.search(r"test", "test line")
        line_match = LineMatch(line_number=1, line_content="test line", match=match)

        self.assertEqual(line_match.line_number, 1)
        self.assertEqual(line_match.line_content, "test line")
        self.assertEqual(line_match.match.group(), "test")


if __name__ == "__main__":
    unittest.main()
