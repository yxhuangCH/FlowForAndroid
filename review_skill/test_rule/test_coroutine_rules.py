#!/usr/bin/env python3
"""
Unit tests for rule_engine/rules/coroutine_rules.py
"""

import unittest
import sys
import os

# Add
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from rule_engine.integration.review_runner import EnhancedReviewRunner


class TestCoroutineRules(unittest.TestCase):
    """Tests"""
    
    def setUp(self):
        """Testrunner"""
        self.runner = EnhancedReviewRunner()
        self.runner.initialize()
    
    def test_main_thread_io_detection(self):
        """Tests"""
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
        
        # Check if main thread IO issue is detected
        main_thread_io_found = False
        for finding in findings:
            if "Main" in finding.get("message", "") and "IO" in finding.get("message", ""):
                main_thread_io_found = True
                self.assertEqual(finding["severity"], "major", "IOmajor")
                break
        self.assertTrue(main_thread_io_found, "IO")
    
    def test_unspecified_scope_detection(self):
        """Tests"""
        code = """fun test() {
    launch {
        // do something
    }
}"""
        result = self.runner.review_code(code, "Test.kt")
        findings = result["findings"]
        
        # Check
        unspecified_scope_found = False
        for finding in findings:
            if "launch" in finding.get("message", "").lower() and "scope" in finding.get("message", "").lower():
                unspecified_scope_found = True
                self.assertEqual(finding["severity"], "minor", "minor")
                break
        self.assertTrue(unspecified_scope_found, "")
    
    def test_viewmodelscope_launch_not_detected(self):
        """Tests"""
        code = """class MyViewModel {
    fun test() {
        viewModelScope.launch {
            // do something
        }
    }
}"""
        result = self.runner.review_code(code, "Test.kt")
        findings = result["findings"]
        
        # 
        unspecified_scope_found = False
        for finding in findings:
            if "launch" in finding.get("message", "").lower() and "scope" in finding.get("message", "").lower():
                unspecified_scope_found = True
                break
        self.assertFalse(unspecified_scope_found, "viewModelScope.launch")
    
    def test_lifecyclescope_launch_not_detected(self):
        """Tests"""
        code = """class MyFragment {
    fun test() {
        lifecycleScope.launch {
            // do something
        }
    }
}"""
        result = self.runner.review_code(code, "Test.kt")
        findings = result["findings"]
        
        # 
        unspecified_scope_found = False
        for finding in findings:
            if "launch" in finding.get("message", "").lower() and "scope" in finding.get("message", "").lower():
                unspecified_scope_found = True
                break
        self.assertFalse(unspecified_scope_found, "lifecycleScope.launch")
    
    def test_multiple_coroutine_issues_detection(self):
        """Tests"""
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
        
        # Should detect at least 2 issues
        self.assertGreaterEqual(len(findings), 2, "2")
        
        # Check
        issue_types = set()
        for finding in findings:
            if "Main" in finding.get("message", "") and "IO" in finding.get("message", ""):
                issue_types.add("main_thread_io")
            if "launch" in finding.get("message", "").lower() and "scope" in finding.get("message", "").lower():
                issue_types.add("unspecified_scope")
        
        self.assertIn("main_thread_io", issue_types, "IO")
        self.assertIn("unspecified_scope", issue_types, "")
    
    def test_coroutine_engine_categories(self):
        """Tests"""
        info = self.runner.get_engine_info()
        stats = info["statistics"]
        
        # Check
        self.assertIn("categories", stats, "Countcategories")
        
        # CheckRule（Ruleconcurrency）
        categories = stats["categories"]
        if "concurrency" in categories:
            self.assertGreater(categories["concurrency"], 0, "Rule")
        
        # CheckRule
        self.assertIn("tags", stats, "Counttags")
        tags = stats["tags"]
        
        # Rulecoroutine
        self.assertIn("coroutine", tags, "Rulecoroutine")
        self.assertGreater(tags["coroutine"], 0, "Rule")
        
        # Ruleandroid
        self.assertIn("android", tags, "Ruleandroid")
        self.assertGreater(tags["android"], 0, "AndroidRule")
    
    def test_coroutine_rule_scoring(self):
        """Tests"""
        # 
        problematic_code = """class MyRepository {
    fun fetchData() {
        Dispatchers.Main.run {
            repository.getData()
        }
    }
}"""
        
        # 
        clean_code = """class MyRepository {
    fun fetchData() {
        viewModelScope.launch {
            repository.getData()
        }
    }
}"""
        
        # Test
        problematic_result = self.runner.review_code(problematic_code, "Problematic.kt")
        problematic_score = problematic_result["score"]
        
        # Test
        clean_result = self.runner.review_code(clean_code, "Clean.kt")
        clean_score = clean_result["score"]
        
        # 
        self.assertLess(problematic_score, clean_score, 
                       f"({problematic_score})({clean_score})")
        
        # （0-100）
        self.assertGreaterEqual(problematic_score, 0, "0")
        self.assertLessEqual(problematic_score, 100, "100")
        
        # 100
        self.assertGreaterEqual(clean_score, 80, "80")


if __name__ == "__main__":
    unittest.main()
