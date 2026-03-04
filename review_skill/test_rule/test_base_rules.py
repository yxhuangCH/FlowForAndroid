#!/usr/bin/env python3
"""
单元测试 for rule_engine/rules/base_rules.py
"""

import unittest
import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from rule_engine.integration.review_runner import EnhancedReviewRunner


class TestBaseRules(unittest.TestCase):
    """测试新的 rule_engine 中的基础规则"""
    
    def setUp(self):
        """每个测试前创建新的runner"""
        self.runner = EnhancedReviewRunner()
        self.runner.initialize()
    
    def test_global_scope_detection(self):
        """测试 GlobalScope.launch 检测"""
        code = """class MyViewModel {
            fun test() {
                GlobalScope.launch {
                    // do something
                }
            }
        }"""
        result = self.runner.review_code(code, "Test.kt")
        findings = result["findings"]
        
        # 检查是否检测到GlobalScope问题
        global_scope_found = False
        for finding in findings:
            if "GlobalScope" in finding.get("message", ""):
                global_scope_found = True
                self.assertEqual(finding["severity"], "critical")
                break
        self.assertTrue(global_scope_found, "应该检测到GlobalScope问题")
    
    def test_viewmodel_context_detection(self):
        """测试 ViewModel 持有 Context 检测"""
        code = """class MyViewModel(private val context: Context) {
            fun test() {
                // do something
            }
        }"""
        result = self.runner.review_code(code, "Test.kt")
        findings = result["findings"]
        
        # 检查是否检测到ViewModel持有Context问题
        context_found = False
        for finding in findings:
            if "ViewModel" in finding.get("message", "") and "Context" in finding.get("message", ""):
                context_found = True
                self.assertEqual(finding["severity"], "major")
                break
        self.assertTrue(context_found, "应该检测到ViewModel持有Context问题")
    
    def test_viewmodel_context_with_spaces(self):
        """测试 ViewModel 持有 Context 检测（带空格）"""
        code = """class MyViewModel( private val context : Context ) {
            fun test() {
                // do something
            }
        }"""
        result = self.runner.review_code(code, "Test.kt")
        findings = result["findings"]
        
        context_found = False
        for finding in findings:
            if "ViewModel" in finding.get("message", "") and "Context" in finding.get("message", ""):
                context_found = True
                break
        self.assertTrue(context_found, "应该检测到ViewModel持有Context问题（带空格）")
    
    def test_viewmodel_no_context(self):
        """测试没有 Context 的 ViewModel"""
        code = """class MyViewModel(private val repo: Repository) {
            fun test() {
                // do something
            }
        }"""
        result = self.runner.review_code(code, "Test.kt")
        findings = result["findings"]
        
        # 不应该检测到ViewModel持有Context问题
        context_not_found = True
        for finding in findings:
            if "ViewModel" in finding.get("message", "") and "Context" in finding.get("message", ""):
                context_not_found = False
                break
        self.assertTrue(context_not_found, "不应该检测到ViewModel持有Context问题")
    
    def test_multiple_issues_detection(self):
        """测试同时检测多个问题"""
        code = """class MyViewModel(private val context: Context) {
            fun test() {
                GlobalScope.launch {
                    // do something
                }
            }
        }"""
        result = self.runner.review_code(code, "Test.kt")
        findings = result["findings"]
        
        # 应该检测到至少2个问题
        self.assertGreaterEqual(len(findings), 2, "应该检测到至少2个问题")
        
        # 检查具体问题类型
        issue_types = set()
        for finding in findings:
            if "GlobalScope" in finding.get("message", ""):
                issue_types.add("global_scope")
            if "ViewModel" in finding.get("message", "") and "Context" in finding.get("message", ""):
                issue_types.add("viewmodel_context")
        
        self.assertIn("global_scope", issue_types, "应该检测到GlobalScope问题")
        self.assertIn("viewmodel_context", issue_types, "应该检测到ViewModel持有Context问题")
    
    def test_engine_initialization(self):
        """测试引擎初始化状态"""
        info = self.runner.get_engine_info()
        self.assertTrue(info["initialized"], "引擎应该已初始化")
        self.assertGreater(info["rule_count"], 0, "应该有注册的规则")
        
        # 检查统计信息
        stats = info["statistics"]
        self.assertIn("total_rules", stats, "统计信息应包含total_rules")
        self.assertIn("enabled_rules", stats, "统计信息应包含enabled_rules")
        self.assertIn("categories", stats, "统计信息应包含categories")
    
    def test_empty_code_review(self):
        """测试空代码审查"""
        result = self.runner.review_code("", "Empty.kt")
        findings = result["findings"]
        
        # 空代码不应该有发现问题
        self.assertEqual(len(findings), 0, "空代码不应该有发现问题")
        
        # 分数应该是100
        self.assertEqual(result["score"], 100, "空代码分数应该是100")


if __name__ == "__main__":
    unittest.main()