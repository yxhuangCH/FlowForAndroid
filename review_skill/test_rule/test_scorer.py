#!/usr/bin/env python3
"""
单元测试 for scorer.py
"""

import unittest
from scorer import run_base_rules, calculate_score


class TestScorer(unittest.TestCase):
    """测试 scorer 模块"""
    
    def test_run_base_rules_empty_code(self):
        """测试空代码"""
        findings = run_base_rules("")
        self.assertEqual(findings, [])
    
    def test_run_base_rules_globalscope(self):
        """测试 GlobalScope.launch 检测"""
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
        """测试 ViewModel 持有 Context 检测"""
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
        """测试同时包含两个问题"""
        code = """class MyViewModel(private val context: Context) {
            fun test() {
                GlobalScope.launch {
                    // do something
                }
            }
        }"""
        findings = run_base_rules(code)
        self.assertEqual(len(findings), 2)
        # 检查两个问题都被检测到
        rules_found = {f["rule"] for f in findings}
        self.assertIn("no_globalscope", rules_found)
        self.assertIn("viewmodel_context", rules_found)
    
    def test_calculate_score_empty_findings(self):
        """测试空 findings 的分数"""
        score = calculate_score([])
        self.assertEqual(score, 100)
    
    def test_calculate_score_critical_finding(self):
        """测试 critical 问题扣分"""
        findings = [
            {"severity": "critical", "rule": "test", "message": "test"}
        ]
        score = calculate_score(findings)
        self.assertEqual(score, 80)  # 100 - 20 = 80
    
    def test_calculate_score_multiple_findings(self):
        """测试多个问题扣分"""
        findings = [
            {"severity": "critical", "rule": "test1", "message": "test"},
            {"severity": "major", "rule": "test2", "message": "test"},
            {"severity": "minor", "rule": "test3", "message": "test"}
        ]
        score = calculate_score(findings)
        self.assertEqual(score, 65)  # 100 - 20 - 10 - 5 = 65
    
    def test_calculate_score_minimum_zero(self):
        """测试分数最低为0"""
        findings = [
            {"severity": "critical", "rule": "test", "message": "test"},
            {"severity": "critical", "rule": "test2", "message": "test"},
            {"severity": "critical", "rule": "test3", "message": "test"},
            {"severity": "critical", "rule": "test4", "message": "test"},
            {"severity": "critical", "rule": "test5", "message": "test"},
            {"severity": "critical", "rule": "test6", "message": "test"},
        ]
        score = calculate_score(findings)  # 6 * 20 = 120, 但100-120=-20 -> 最大为0
        self.assertEqual(score, 0)
    
    def test_calculate_score_maximum_100(self):
        """测试分数最高为100"""
        findings = []  # 空 findings
        score = calculate_score(findings)
        self.assertEqual(score, 100)
    
    def test_calculate_score_unknown_severity(self):
        """测试未知严重级别"""
        findings = [
            {"severity": "unknown", "rule": "test", "message": "test"}
        ]
        score = calculate_score(findings)
        # 未知严重级别不会扣分（根据实际实现）
        self.assertEqual(score, 100)


if __name__ == "__main__":
    unittest.main()