#!/usr/bin/env python3
"""
Unit tests for scorer.py
"""

import unittest
from scorer import run_base_rules, calculate_score


class TestScorer(unittest.TestCase):
    """Tests"""
    
    def test_run_base_rules_empty_code(self):
        """Tests"""
        findings = run_base_rules("")
        self.assertEqual(findings, [])
    
    def test_run_base_rules_globalscope(self):
        """Tests"""
        code = """class MyViewModel {
            fun test() {
                GlobalScope.launch {
                    // do something
                }
            }
        }"""
        findings = run_base_rules(code)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["severity"], "critical")
        self.assertEqual(findings[0]["rule"], "no_globalscope")
        self.assertEqual(findings[0]["message"], "GlobalScope is lifecycle unsafe.")
    
    def test_run_base_rules_viewmodel_context(self):
        """Tests"""
        code = """class MyViewModel(private val context: Context) {
            fun test() {
                // do something
            }
        }"""
        findings = run_base_rules(code)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["severity"], "major")
        self.assertEqual(findings[0]["rule"], "viewmodel_context")
        self.assertEqual(findings[0]["message"], "ViewModel should not hold Android Context.")
    
    def test_run_base_rules_both_issues(self):
        """Tests"""
        code = """class MyViewModel(private val context: Context) {
            fun test() {
                GlobalScope.launch {
                    // do something
                }
            }
        }"""
        findings = run_base_rules(code)
        self.assertEqual(len(findings), 2)
        # Check
        rules_found = {f["rule"] for f in findings}
        self.assertIn("no_globalscope", rules_found)
        self.assertIn("viewmodel_context", rules_found)
    
    def test_calculate_score_empty_findings(self):
        """Tests"""
        score = calculate_score([])
        self.assertEqual(score, 100)
    
    def test_calculate_score_critical_finding(self):
        """Tests"""
        findings = [
            {"severity": "critical", "rule": "test", "message": "test"}
        ]
        score = calculate_score(findings)
        self.assertEqual(score, 80)  # 100 - 20 = 80
    
    def test_calculate_score_multiple_findings(self):
        """Tests"""
        findings = [
            {"severity": "critical", "rule": "test1", "message": "test"},
            {"severity": "major", "rule": "test2", "message": "test"},
            {"severity": "minor", "rule": "test3", "message": "test"}
        ]
        score = calculate_score(findings)
        self.assertEqual(score, 65)  # 100 - 20 - 10 - 5 = 65
    
    def test_calculate_score_minimum_zero(self):
        """Tests"""
        findings = [
            {"severity": "critical", "rule": "test", "message": "test"},
            {"severity": "critical", "rule": "test2", "message": "test"},
            {"severity": "critical", "rule": "test3", "message": "test"},
            {"severity": "critical", "rule": "test4", "message": "test"},
            {"severity": "critical", "rule": "test5", "message": "test"},
            {"severity": "critical", "rule": "test6", "message": "test"},
        ]
        score = calculate_score(findings)  # 6 * 20 = 120, 100-120=-20 -> 0
        self.assertEqual(score, 0)
    
    def test_calculate_score_maximum_100(self):
        """Tests"""
        findings = []  #  findings
        score = calculate_score(findings)
        self.assertEqual(score, 100)
    
    def test_calculate_score_unknown_severity(self):
        """Tests"""
        findings = [
            {"severity": "unknown", "rule": "test", "message": "test"}
        ]
        score = calculate_score(findings)
        # （）
        self.assertEqual(score, 100)


if __name__ == "__main__":
    unittest.main()