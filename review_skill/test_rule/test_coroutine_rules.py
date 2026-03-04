#!/usr/bin/env python3
"""
单元测试 for rule_engine/rules/coroutine_rules.py
"""

import unittest
import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from rule_engine.integration.review_runner import EnhancedReviewRunner


class TestCoroutineRules(unittest.TestCase):
    """测试新的 rule_engine 中的协程规则"""
    
    def setUp(self):
        """每个测试前创建新的runner"""
        self.runner = EnhancedReviewRunner()
        self.runner.initialize()
    
    def test_main_thread_io_detection(self):
        """测试 Main thread IO 检测"""
        code = """class MyRepository {
    fun fetchData() {
        Dispatchers.Main.run {
            // IO operation
            repository.getData()
        }
    }
}"""
        result = self.runner.review_code(code, "Test.kt")
        findings = result["findings"]
        
        # 检查是否检测到主线程IO问题
        main_thread_io_found = False
        for finding in findings:
            if "Main" in finding.get("message", "") and "IO" in finding.get("message", ""):
                main_thread_io_found = True
                self.assertEqual(finding["severity"], "major", "主线程IO应该是major级别")
                break
        self.assertTrue(main_thread_io_found, "应该检测到主线程IO问题")
    
    def test_unspecified_scope_detection(self):
        """测试未指定 scope 的 launch"""
        code = """fun test() {
    launch {
        // do something
    }
}"""
        result = self.runner.review_code(code, "Test.kt")
        findings = result["findings"]
        
        # 检查是否检测到未指定作用域问题
        unspecified_scope_found = False
        for finding in findings:
            if "launch" in finding.get("message", "").lower() and "scope" in finding.get("message", "").lower():
                unspecified_scope_found = True
                self.assertEqual(finding["severity"], "minor", "未指定作用域应该是minor级别")
                break
        self.assertTrue(unspecified_scope_found, "应该检测到未指定作用域问题")
    
    def test_viewmodelscope_launch_not_detected(self):
        """测试 viewModelScope launch（不应检测）"""
        code = """class MyViewModel {
    fun test() {
        viewModelScope.launch {
            // do something
        }
    }
}"""
        result = self.runner.review_code(code, "Test.kt")
        findings = result["findings"]
        
        # 不应该检测到未指定作用域问题
        unspecified_scope_found = False
        for finding in findings:
            if "launch" in finding.get("message", "").lower() and "scope" in finding.get("message", "").lower():
                unspecified_scope_found = True
                break
        self.assertFalse(unspecified_scope_found, "viewModelScope.launch不应该被检测")
    
    def test_lifecyclescope_launch_not_detected(self):
        """测试 lifecycleScope launch（不应检测）"""
        code = """class MyFragment {
    fun test() {
        lifecycleScope.launch {
            // do something
        }
    }
}"""
        result = self.runner.review_code(code, "Test.kt")
        findings = result["findings"]
        
        # 不应该检测到未指定作用域问题
        unspecified_scope_found = False
        for finding in findings:
            if "launch" in finding.get("message", "").lower() and "scope" in finding.get("message", "").lower():
                unspecified_scope_found = True
                break
        self.assertFalse(unspecified_scope_found, "lifecycleScope.launch不应该被检测")
    
    def test_multiple_coroutine_issues_detection(self):
        """测试同时检测多个协程问题"""
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
        result = self.runner.review_code(code, "Test.kt")
        findings = result["findings"]
        
        # 应该检测到至少2个问题
        self.assertGreaterEqual(len(findings), 2, "应该检测到至少2个问题")
        
        # 检查具体问题类型
        issue_types = set()
        for finding in findings:
            if "Main" in finding.get("message", "") and "IO" in finding.get("message", ""):
                issue_types.add("main_thread_io")
            if "launch" in finding.get("message", "").lower() and "scope" in finding.get("message", "").lower():
                issue_types.add("unspecified_scope")
        
        self.assertIn("main_thread_io", issue_types, "应该检测到主线程IO问题")
        self.assertIn("unspecified_scope", issue_types, "应该检测到未指定作用域问题")
    
    def test_coroutine_engine_categories(self):
        """测试协程规则分类"""
        info = self.runner.get_engine_info()
        stats = info["statistics"]
        
        # 检查是否包含协程相关的分类
        self.assertIn("categories", stats, "统计信息应包含categories")
        
        # 检查是否有并发性相关规则（协程规则通常属于concurrency分类）
        categories = stats["categories"]
        if "concurrency" in categories:
            self.assertGreater(categories["concurrency"], 0, "应该有并发性相关规则")
        
        # 检查规则标签
        self.assertIn("tags", stats, "统计信息应包含tags")
        tags = stats["tags"]
        
        # 协程规则应该包含coroutine标签
        self.assertIn("coroutine", tags, "规则应该包含coroutine标签")
        self.assertGreater(tags["coroutine"], 0, "应该有协程相关规则")
        
        # 协程规则应该包含android标签
        self.assertIn("android", tags, "规则应该包含android标签")
        self.assertGreater(tags["android"], 0, "应该有Android相关规则")
    
    def test_coroutine_rule_scoring(self):
        """测试协程规则分数计算"""
        # 包含问题的代码
        problematic_code = """class MyRepository {
    fun fetchData() {
        Dispatchers.Main.run {
            repository.getData()
        }
    }
}"""
        
        # 没有问题的代码
        clean_code = """class MyRepository {
    fun fetchData() {
        viewModelScope.launch {
            repository.getData()
        }
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
