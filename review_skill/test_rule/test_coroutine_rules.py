#!/usr/bin/env python3
"""
单元测试 for rules/coroutine_rules.py
"""

import unittest
from rules.coroutine_rules import run_coroutine_rules


class TestCoroutineRules(unittest.TestCase):
    """测试 coroutine_rules 模块"""
    
    def test_run_coroutine_rules_empty_code(self):
        """测试空代码"""
        findings = run_coroutine_rules("")
        self.assertEqual(findings, [])
    
    def test_run_coroutine_rules_main_thread_io(self):
        """测试 Main thread IO 检测"""
        code = """class MyRepository {
            fun fetchData() {
                Dispatchers.Main.run {
                    // IO operation
                    repository.getData()
                }
            }
        }"""
        findings = run_coroutine_rules(code)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["severity"], "major")
        self.assertEqual(findings[0]["rule"], "main_thread_io")
        self.assertEqual(findings[0]["message"], "Possible IO on Main thread.")
    
    def test_run_coroutine_rules_main_thread_io_multiple_lines(self):
        """测试 Main thread IO 检测（多行）"""
        code = """
        Dispatchers.Main
            .run {
                repository.getData()
            }
        """
        findings = run_coroutine_rules(code)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule"], "main_thread_io")
    
    def test_run_coroutine_rules_unspecified_scope(self):
        """测试未指定 scope 的 launch"""
        code = """fun test() {
            launch {
                // do something
            }
        }"""
        findings = run_coroutine_rules(code)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["severity"], "minor")
        self.assertEqual(findings[0]["rule"], "unspecified_scope")
        self.assertEqual(findings[0]["message"], "Coroutine launched without lifecycle scope.")
    
    def test_run_coroutine_rules_viewmodelscope_launch(self):
        """测试 viewModelScope launch（不应检测）"""
        code = """class MyViewModel {
            fun test() {
                viewModelScope.launch {
                    // do something
                }
            }
        }"""
        findings = run_coroutine_rules(code)
        # viewModelScope.launch 不应该触发 unspecified_scope 规则
        self.assertEqual(findings, [])
    
    def test_run_coroutine_rules_lifecyscope_launch(self):
        """测试 lifecycleScope launch - 当前实现只检查 viewModelScope"""
        code = """class MyFragment {
            fun test() {
                lifecycleScope.launch {
                    // do something
                }
            }
        }"""
        findings = run_coroutine_rules(code)
        # 当前实现只检查 viewModelScope，所以 lifecycleScope.launch 会触发规则
        # 因为 "viewModelScope" not in code
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule"], "unspecified_scope")
    
    def test_run_coroutine_rules_both_issues(self):
        """测试同时包含两个问题"""
        code = """class MyRepository {
            fun test() {
                Dispatchers.Main.run {
                    repository.getData()
                }
                
                launch {
                    // do something
                }
            }
        }"""
        findings = run_coroutine_rules(code)
        self.assertEqual(len(findings), 2)
        # 检查两个问题都被检测到
        rules_found = {f["rule"] for f in findings}
        self.assertIn("main_thread_io", rules_found)
        self.assertIn("unspecified_scope", rules_found)
    
    def test_run_coroutine_rules_main_thread_io_no_repository(self):
        """测试 Main thread 但没有 repository（不应检测）"""
        code = """Dispatchers.Main.run {
            // some operation
        }"""
        findings = run_coroutine_rules(code)
        # 没有 "repository" 关键字，不应该触发 main_thread_io 规则
        self.assertEqual(findings, [])
    
    def test_run_coroutine_rules_unspecified_scope_with_other_text(self):
        """测试 launch 在其他文本中（应该检测）"""
        code = """// This is a launch function
        fun myLaunchFunction() {
            launch {
                // do something
            }
        }"""
        findings = run_coroutine_rules(code)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule"], "unspecified_scope")


if __name__ == "__main__":
    unittest.main()