#!/usr/bin/env python3
"""
Unit tests for rule_engine/rules/base_rules.py
"""

import unittest
import sys
import os

# Add
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from rule_engine.integration.review_runner import EnhancedReviewRunner


class TestBaseRules(unittest.TestCase):
    """Tests"""
    
    def setUp(self):
        """Testrunner"""
        self.runner = EnhancedReviewRunner()
        self.runner.initialize()
    
    def test_global_scope_detection(self):
        """Tests"""
        code = """class MyViewModel {
            fun test() {
                GlobalScope.launch {
                    // do something
                }
            }
        }"""
        result = self.runner.review_code(code, "Test.kt")
        findings = result["findings"]
        
        # Check if GlobalScope issue is detected
        global_scope_found = False
        for finding in findings:
            if "GlobalScope" in finding.get("message", ""):
                global_scope_found = True
                self.assertEqual(finding["severity"], "critical")
                break
        self.assertTrue(global_scope_found, "GlobalScope")
    
    def test_viewmodel_context_detection(self):
        """Tests"""
        code = """class MyViewModel(private val context: Context) {
            fun test() {
                // do something
            }
        }"""
        result = self.runner.review_code(code, "Test.kt")
        findings = result["findings"]
        
        # Check if ViewModel holding Context issue is detected
        context_found = False
        for finding in findings:
            if "ViewModel" in finding.get("message", "") and "Context" in finding.get("message", ""):
                context_found = True
                self.assertEqual(finding["severity"], "major")
                break
        self.assertTrue(context_found, "ViewModelContext")
    
    def test_viewmodel_context_with_spaces(self):
        """Tests"""
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
        self.assertTrue(context_found, "ViewModelContext（）")
    
    def test_viewmodel_no_context(self):
        """Tests"""
        code = """class MyViewModel(private val repo: Repository) {
            fun test() {
                // do something
            }
        }"""
        result = self.runner.review_code(code, "Test.kt")
        findings = result["findings"]
        
        # ViewModelContext
        context_not_found = True
        for finding in findings:
            if "ViewModel" in finding.get("message", "") and "Context" in finding.get("message", ""):
                context_not_found = False
                break
        self.assertTrue(context_not_found, "ViewModelContext")
    
    def test_multiple_issues_detection(self):
        """Tests"""
        code = """class MyViewModel(private val context: Context) {
            fun test() {
                GlobalScope.launch {
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
            if "GlobalScope" in finding.get("message", ""):
                issue_types.add("global_scope")
            if "ViewModel" in finding.get("message", "") and "Context" in finding.get("message", ""):
                issue_types.add("viewmodel_context")
        
        self.assertIn("global_scope", issue_types, "GlobalScope")
        self.assertIn("viewmodel_context", issue_types, "ViewModelContext")
    
    def test_engine_initialization(self):
        """Tests"""
        info = self.runner.get_engine_info()
        self.assertTrue(info["initialized"], "Initialize")
        self.assertGreater(info["rule_count"], 0, "RegisterRule")
        
        # CheckCount
        stats = info["statistics"]
        self.assertIn("total_rules", stats, "Counttotal_rules")
        self.assertIn("enabled_rules", stats, "Countenabled_rules")
        self.assertIn("categories", stats, "Countcategories")
    
    def test_empty_code_review(self):
        """Tests"""
        result = self.runner.review_code("", "Empty.kt")
        findings = result["findings"]
        
        # 
        self.assertEqual(len(findings), 0, "")
        
        # 100
        self.assertEqual(result["score"], 100, "100")


if __name__ == "__main__":
    unittest.main()