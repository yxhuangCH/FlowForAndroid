#!/usr/bin/env python3
"""
Unit tests for rule_engine/rules/compose_rules.py
"""

import unittest
import sys
import os

# Add
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from rule_engine.integration.review_runner import EnhancedReviewRunner


class TestComposeRules(unittest.TestCase):
    """Tests"""
    
    def setUp(self):
        """Testrunner"""
        self.runner = EnhancedReviewRunner()
        self.runner.initialize()
    
    def test_launched_effect_unit_detection(self):
        """Tests"""
        code = """@Composable
fun MyScreen() {
    LaunchedEffect(Unit) {
        // do something
    }
}"""
        result = self.runner.review_code(code, "Test.kt")
        findings = result["findings"]
        
        # CheckLaunchedEffect(Unit)
        launched_effect_found = False
        for finding in findings:
            if "LaunchedEffect" in finding.get("message", "") and "Unit" in finding.get("message", ""):
                launched_effect_found = True
                self.assertEqual(finding["severity"], "minor", "LaunchedEffect(Unit)minor")
                break
        self.assertTrue(launched_effect_found, "LaunchedEffect(Unit)")
    
    def test_remember_context_detection(self):
        """Tests"""
        code = """@Composable
fun MyScreen(context: Context) {
    val remembered = remember {
        // using context
        context.getString(R.string.app_name)
    }
}"""
        result = self.runner.review_code(code, "Test.kt")
        findings = result["findings"]
        
        # Checkremembercontext
        remember_context_found = False
        for finding in findings:
            if "remember" in finding.get("message", "").lower() and "context" in finding.get("message", "").lower():
                remember_context_found = True
                self.assertEqual(finding["severity"], "major", "remembercontextmajor")
                break
        self.assertTrue(remember_context_found, "remembercontext")
    
    def test_launched_effect_with_key_not_detected(self):
        """Tests"""
        code = """LaunchedEffect(key1) {
    // do something
}"""
        result = self.runner.review_code(code, "Test.kt")
        findings = result["findings"]
        
        # LaunchedEffect
        launched_effect_found = False
        for finding in findings:
            if "LaunchedEffect" in finding.get("message", ""):
                launched_effect_found = True
                break
        self.assertFalse(launched_effect_found, "LaunchedEffectkey")
    
    def test_remember_no_context_not_detected(self):
        """Tests"""
        code = """val remembered = remember {
    // just a number
    42
}"""
        result = self.runner.review_code(code, "Test.kt")
        findings = result["findings"]
        
        # remembercontext
        remember_context_found = False
        for finding in findings:
            if "remember" in finding.get("message", "").lower() and "context" in finding.get("message", "").lower():
                remember_context_found = True
                break
        self.assertFalse(remember_context_found, "remembercontext")
    
    def test_multiple_compose_issues_detection(self):
        """Tests"""
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
        
        # Should detect at least 2 issues
        self.assertGreaterEqual(len(findings), 2, "2")
        
        # Check
        issue_types = set()
        for finding in findings:
            if "LaunchedEffect" in finding.get("message", "") and "Unit" in finding.get("message", ""):
                issue_types.add("launched_effect_unit")
            if "remember" in finding.get("message", "").lower() and "context" in finding.get("message", "").lower():
                issue_types.add("remember_context")
        
        self.assertIn("launched_effect_unit", issue_types, "LaunchedEffect(Unit)")
        self.assertIn("remember_context", issue_types, "remembercontext")
    
    def test_compose_engine_categories(self):
        """Tests"""
        info = self.runner.get_engine_info()
        stats = info["statistics"]
        
        # CheckCompose
        self.assertIn("categories", stats, "Countcategories")
        
        # CheckRule（ComposeRulecorrectness）
        categories = stats["categories"]
        if "correctness" in categories:
            self.assertGreater(categories["correctness"], 0, "Rule")
        
        # CheckRule
        self.assertIn("tags", stats, "Counttags")
        tags = stats["tags"]
        
        # ComposeRulecompose
        self.assertIn("compose", tags, "Rulecompose")
        self.assertGreater(tags["compose"], 0, "ComposeRule")
    
    def test_compose_rule_scoring(self):
        """Tests"""
        # 
        problematic_code = """@Composable
fun MyScreen() {
    LaunchedEffect(Unit) {
        // do something
    }
}"""
        
        # 
        clean_code = """@Composable
fun MyScreen() {
    LaunchedEffect(key1) {
        // do something
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