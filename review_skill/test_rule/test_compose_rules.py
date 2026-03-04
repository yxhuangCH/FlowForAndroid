#!/usr/bin/env python3
"""
单元测试 for rule_engine/rules/compose_rules.py
"""

import unittest
import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from rule_engine.integration.review_runner import EnhancedReviewRunner


class TestComposeRules(unittest.TestCase):
    """测试新的 rule_engine 中的 Compose 规则"""
    
    def setUp(self):
        """每个测试前创建新的runner"""
        self.runner = EnhancedReviewRunner()
        self.runner.initialize()
    
    def test_launched_effect_unit_detection(self):
        """测试 LaunchedEffect(Unit) 检测"""
        code = """@Composable
fun MyScreen() {
    LaunchedEffect(Unit) {
        // do something
    }
}"""
        result = self.runner.review_code(code, "Test.kt")
        findings = result["findings"]
        
        # 检查是否检测到LaunchedEffect(Unit)问题
        launched_effect_found = False
        for finding in findings:
            if "LaunchedEffect" in finding.get("message", "") and "Unit" in finding.get("message", ""):
                launched_effect_found = True
                self.assertEqual(finding["severity"], "minor", "LaunchedEffect(Unit)应该是minor级别")
                break
        self.assertTrue(launched_effect_found, "应该检测到LaunchedEffect(Unit)问题")
    
    def test_remember_context_detection(self):
        """测试 remember 持有 context 检测"""
        code = """@Composable
fun MyScreen(context: Context) {
    val remembered = remember {
        // using context
        context.getString(R.string.app_name)
    }
}"""
        result = self.runner.review_code(code, "Test.kt")
        findings = result["findings"]
        
        # 检查是否检测到remember持有context问题
        remember_context_found = False
        for finding in findings:
            if "remember" in finding.get("message", "").lower() and "context" in finding.get("message", "").lower():
                remember_context_found = True
                self.assertEqual(finding["severity"], "major", "remember持有context应该是major级别")
                break
        self.assertTrue(remember_context_found, "应该检测到remember持有context问题")
    
    def test_launched_effect_with_key_not_detected(self):
        """测试 LaunchedEffect 有 key（不应检测）"""
        code = """LaunchedEffect(key1) {
    // do something
}"""
        result = self.runner.review_code(code, "Test.kt")
        findings = result["findings"]
        
        # 不应该检测到LaunchedEffect问题
        launched_effect_found = False
        for finding in findings:
            if "LaunchedEffect" in finding.get("message", ""):
                launched_effect_found = True
                break
        self.assertFalse(launched_effect_found, "LaunchedEffect有key时不应该被检测")
    
    def test_remember_no_context_not_detected(self):
        """测试 remember 但不包含 context（不应检测）"""
        code = """val remembered = remember {
    // just a number
    42
}"""
        result = self.runner.review_code(code, "Test.kt")
        findings = result["findings"]
        
        # 不应该检测到remember持有context问题
        remember_context_found = False
        for finding in findings:
            if "remember" in finding.get("message", "").lower() and "context" in finding.get("message", "").lower():
                remember_context_found = True
                break
        self.assertFalse(remember_context_found, "remember不持有context时不应该被检测")
    
    def test_multiple_compose_issues_detection(self):
        """测试同时检测多个Compose问题"""
        code = """@Composable
fun MyScreen(context: Context) {
    LaunchedEffect(Unit) {
        // do something
    }
    
    val remembered = remember {
        context.getString(R.string.app_name)
    }
}"""
        result = self.runner.review_code(code, "Test.kt")
        findings = result["findings"]
        
        # 应该检测到至少2个问题
        self.assertGreaterEqual(len(findings), 2, "应该检测到至少2个问题")
        
        # 检查具体问题类型
        issue_types = set()
        for finding in findings:
            if "LaunchedEffect" in finding.get("message", "") and "Unit" in finding.get("message", ""):
                issue_types.add("launched_effect_unit")
            if "remember" in finding.get("message", "").lower() and "context" in finding.get("message", "").lower():
                issue_types.add("remember_context")
        
        self.assertIn("launched_effect_unit", issue_types, "应该检测到LaunchedEffect(Unit)问题")
        self.assertIn("remember_context", issue_types, "应该检测到remember持有context问题")
    
    def test_compose_engine_categories(self):
        """测试Compose规则分类"""
        info = self.runner.get_engine_info()
        stats = info["statistics"]
        
        # 检查是否包含Compose相关的分类
        self.assertIn("categories", stats, "统计信息应包含categories")
        
        # 检查是否有正确性相关规则（Compose规则通常属于correctness分类）
        categories = stats["categories"]
        if "correctness" in categories:
            self.assertGreater(categories["correctness"], 0, "应该有正确性相关规则")
        
        # 检查规则标签
        self.assertIn("tags", stats, "统计信息应包含tags")
        tags = stats["tags"]
        
        # Compose规则应该包含compose标签
        self.assertIn("compose", tags, "规则应该包含compose标签")
        self.assertGreater(tags["compose"], 0, "应该有Compose相关规则")
    
    def test_compose_rule_scoring(self):
        """测试Compose规则分数计算"""
        # 包含问题的代码
        problematic_code = """@Composable
fun MyScreen() {
    LaunchedEffect(Unit) {
        // do something
    }
}"""
        
        # 没有问题的代码
        clean_code = """@Composable
fun MyScreen() {
    LaunchedEffect(key1) {
        // do something
    }
}"""
        
        # 测试有问题的代码
        problematic_result = self.runner.review_code(problematic_code, "Problematic.kt")
        problematic_score = problematic_result["score"]
        
        # 测试干净的代码
        clean_result = self.runner.review_code(clean_code, "Clean.kt")
        clean_score = clean_result["score"]
        
        # 有问题的代码分数应该低于干净的代码
        self.assertLess(problematic_score, clean_score, 
                       f"有问题的代码分数({problematic_score})应该低于干净的代码分数({clean_score})")
        
        # 分数应该在合理范围内（0-100）
        self.assertGreaterEqual(problematic_score, 0, "分数应该大于等于0")
        self.assertLessEqual(problematic_score, 100, "分数应该小于等于100")
        
        # 干净的代码应该接近100分
        self.assertGreaterEqual(clean_score, 80, "干净的代码应该至少80分")


if __name__ == "__main__":
    unittest.main()