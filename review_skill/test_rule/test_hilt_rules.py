#!/usr/bin/env python3
"""
单元测试 for rules/hilt_rules.py
"""

import unittest
from rules.hilt_rules import run_hilt_rules


class TestHiltRules(unittest.TestCase):
    """测试 hilt_rules 模块"""
    
    def test_run_hilt_rules_empty_code(self):
        """测试空代码"""
        findings = run_hilt_rules("")
        self.assertEqual(findings, [])
    
    def test_run_hilt_rules_singleton_activity(self):
        """测试 Singleton 注入 Activity 检测"""
        code = """@Singleton
        class MyRepository @Inject constructor() {
            // repository code
        }
        
        class MainActivity : AppCompatActivity() {
            @Inject
            lateinit var repository: MyRepository
        }"""
        findings = run_hilt_rules(code)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["severity"], "major")
        self.assertEqual(findings[0]["rule"], "singleton_activity")
        self.assertEqual(findings[0]["message"], "Singleton injected into Activity scope.")
    
    def test_run_hilt_rules_singleton_without_activity(self):
        """测试有 Singleton 但没有 Activity（不应检测）"""
        code = """@Singleton
        class MyRepository @Inject constructor() {
            // repository code
        }"""
        findings = run_hilt_rules(code)
        self.assertEqual(findings, [])
    
    def test_run_hilt_rules_activity_without_singleton(self):
        """测试有 Activity 但没有 Singleton（不应检测）"""
        code = """class MainActivity : AppCompatActivity() {
            // activity code
        }"""
        findings = run_hilt_rules(code)
        self.assertEqual(findings, [])
    
    def test_run_hilt_rules_singleton_activity_separate(self):
        """测试 Singleton 和 Activity 分开"""
        code = """@Singleton
        class MySingleton {
            // singleton code
        }
        
        class MyActivity : Activity() {
            // activity code
        }"""
        findings = run_hilt_rules(code)
        # 应该检测到，因为 @Singleton 和 Activity 都在代码中
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule"], "singleton_activity")
    
    def test_run_hilt_rules_multiple_activities(self):
        """测试多个 Activity"""
        code = """@Singleton
        class MySingleton {
            // singleton code
        }
        
        class FirstActivity : Activity() {
            // first activity
        }
        
        class SecondActivity : Activity() {
            // second activity
        }"""
        findings = run_hilt_rules(code)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule"], "singleton_activity")
    
    def test_run_hilt_rules_case_sensitive(self):
        """测试大小写敏感"""
        code = """@singleton
        class MyClass {
            // lowercase singleton
        }
        
        class MyActivity : Activity() {
            // activity
        }"""
        findings = run_hilt_rules(code)
        # 大小写敏感，@singleton 不会匹配 @Singleton
        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()