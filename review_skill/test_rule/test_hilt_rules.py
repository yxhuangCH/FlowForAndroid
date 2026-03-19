#!/usr/bin/env python3
"""
Unit tests for rules/hilt_rules.py
"""

import unittest
from rules.hilt_rules import run_hilt_rules


class TestHiltRules(unittest.TestCase):
    """Tests"""
    
    def test_run_hilt_rules_empty_code(self):
        """Tests"""
        findings = run_hilt_rules("")
        self.assertEqual(findings, [])
    
    def test_run_hilt_rules_singleton_activity(self):
        """Tests"""
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
        """Tests"""
        code = """@Singleton
        class MyRepository @Inject constructor() {
            // repository code
        }"""
        findings = run_hilt_rules(code)
        self.assertEqual(findings, [])
    
    def test_run_hilt_rules_activity_without_singleton(self):
        """Tests"""
        code = """class MainActivity : AppCompatActivity() {
            // activity code
        }"""
        findings = run_hilt_rules(code)
        self.assertEqual(findings, [])
    
    def test_run_hilt_rules_singleton_activity_separate(self):
        """Tests"""
        code = """@Singleton
        class MySingleton {
            // singleton code
        }
        
        class MyActivity : Activity() {
            // activity code
        }"""
        findings = run_hilt_rules(code)
        # ， @Singleton  Activity 
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule"], "singleton_activity")
    
    def test_run_hilt_rules_multiple_activities(self):
        """Tests"""
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
        """Tests"""
        code = """@singleton
        class MyClass {
            // lowercase singleton
        }
        
        class MyActivity : Activity() {
            // activity
        }"""
        findings = run_hilt_rules(code)
        # ，@singleton  @Singleton
        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()