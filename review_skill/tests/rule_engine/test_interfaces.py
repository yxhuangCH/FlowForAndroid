"""Test Rule Engine"""
import unittest
from rule_engine.interfaces import (
    RuleSeverity,
    RuleCategory,
    RuleMetadata,
    Finding,
    Rule
)


class TestRuleSeverity(unittest.TestCase):
    """Tests"""
    
    def test_enum_values(self):
        """Tests"""
        self.assertEqual(RuleSeverity.INFO.value, "info")
        self.assertEqual(RuleSeverity.MINOR.value, "minor")
        self.assertEqual(RuleSeverity.MAJOR.value, "major")
        self.assertEqual(RuleSeverity.CRITICAL.value, "critical")
        self.assertEqual(RuleSeverity.BLOCKER.value, "blocker")
    
    def test_from_string(self):
        """Tests"""
        self.assertEqual(RuleSeverity("info"), RuleSeverity.INFO)
        self.assertEqual(RuleSeverity("minor"), RuleSeverity.MINOR)
        self.assertEqual(RuleSeverity("major"), RuleSeverity.MAJOR)
        self.assertEqual(RuleSeverity("critical"), RuleSeverity.CRITICAL)
        self.assertEqual(RuleSeverity("blocker"), RuleSeverity.BLOCKER)
        
        with self.assertRaises(ValueError):
            RuleSeverity("invalid")


class TestRuleCategory(unittest.TestCase):
    """Tests"""
    
    def test_enum_values(self):
        """Tests"""
        self.assertEqual(RuleCategory.SECURITY.value, "security")
        self.assertEqual(RuleCategory.PERFORMANCE.value, "performance")
        self.assertEqual(RuleCategory.BEST_PRACTICE.value, "best_practice")
        self.assertEqual(RuleCategory.MAINTAINABILITY.value, "maintainability")
        self.assertEqual(RuleCategory.CORRECTNESS.value, "correctness")
        self.assertEqual(RuleCategory.STYLE.value, "style")
        self.assertEqual(RuleCategory.CONCURRENCY.value, "concurrency")
        self.assertEqual(RuleCategory.LIFECYCLE.value, "lifecycle")
    
    def test_from_string(self):
        """Tests"""
        self.assertEqual(RuleCategory("security"), RuleCategory.SECURITY)
        self.assertEqual(RuleCategory("performance"), RuleCategory.PERFORMANCE)
        self.assertEqual(RuleCategory("correctness"), RuleCategory.CORRECTNESS)
        
        with self.assertRaises(ValueError):
            RuleCategory("invalid")


class TestRuleMetadata(unittest.TestCase):
    """Tests"""
    
    def test_basic_creation(self):
        """Tests"""
        metadata = RuleMetadata(
            id="test_rule",
            name="TestRule",
            description="TestRule",
            severity=RuleSeverity.MINOR,
            category=RuleCategory.CORRECTNESS
        )
        
        self.assertEqual(metadata.id, "test_rule")
        self.assertEqual(metadata.name, "TestRule")
        self.assertEqual(metadata.description, "TestRule")
        self.assertEqual(metadata.severity, RuleSeverity.MINOR)
        self.assertEqual(metadata.category, RuleCategory.CORRECTNESS)
        self.assertTrue(metadata.enabled)
        self.assertEqual(metadata.weight, 1.0)
        self.assertEqual(metadata.tags, [])
    
    def test_with_optional_fields(self):
        """Tests"""
        metadata = RuleMetadata(
            id="test_rule",
            name="TestRule",
            description="",
            severity=RuleSeverity.MAJOR,
            category=RuleCategory.PERFORMANCE,
            enabled=False,
            weight=1.5,
            tags=["android", "kotlin"],
            suggested_fix="",
            reference_url="https://example.com",
            min_score_deduction=5,
            max_score_deduction=15
        )
        
        self.assertFalse(metadata.enabled)
        self.assertEqual(metadata.weight, 1.5)
        self.assertEqual(metadata.tags, ["android", "kotlin"])
        self.assertEqual(metadata.suggested_fix, "")
        self.assertEqual(metadata.reference_url, "https://example.com")
        self.assertEqual(metadata.min_score_deduction, 5)
        self.assertEqual(metadata.max_score_deduction, 15)
    
    def test_validation(self):
        """Tests"""
        with self.assertRaises(ValueError):
            RuleMetadata(
                id="",
                name="TestRule",
                description="",
                severity=RuleSeverity.MINOR,
                category=RuleCategory.CORRECTNESS
            )
        
        with self.assertRaises(ValueError):
            RuleMetadata(
                id="test_rule",
                name="",
                description="",
                severity=RuleSeverity.MINOR,
                category=RuleCategory.CORRECTNESS
            )
        
        with self.assertRaises(ValueError):
            RuleMetadata(
                id="test_rule",
                name="TestRule",
                description="",
                severity=RuleSeverity.MINOR,
                category=RuleCategory.CORRECTNESS
            )


class TestFinding(unittest.TestCase):
    """Tests"""
    
    def test_basic_creation(self):
        """Tests"""
        finding = Finding(
            rule_id="no_globalscope",
            message="GlobalScope",
            severity=RuleSeverity.CRITICAL,
            file_path="Test.kt",
            line_number=42,
            column=10,
            code_snippet="GlobalScope.launch { }",
            suggestion="viewModelScope",
            confidence=0.9
        )
        
        self.assertEqual(finding.rule_id, "no_globalscope")
        self.assertEqual(finding.message, "GlobalScope")
        self.assertEqual(finding.severity, RuleSeverity.CRITICAL)
        self.assertEqual(finding.file_path, "Test.kt")
        self.assertEqual(finding.line_number, 42)
        self.assertEqual(finding.column, 10)
        self.assertEqual(finding.code_snippet, "GlobalScope.launch { }")
        self.assertEqual(finding.suggestion, "viewModelScope")
        self.assertEqual(finding.confidence, 0.9)
        self.assertEqual(finding.metadata, {})
    
    def test_to_dict(self):
        """Tests"""
        finding = Finding(
            rule_id="test_rule",
            message="Test",
            severity=RuleSeverity.MINOR,
            file_path="file.kt",
            line_number=10,
            metadata={"extra": "data"}
        )
        
        result = finding.to_dict()
        
        self.assertEqual(result["rule"], "test_rule")
        self.assertEqual(result["severity"], "minor")
        self.assertEqual(result["message"], "Test")
        self.assertEqual(result["file_path"], "file.kt")
        self.assertEqual(result["line_number"], 10)
        self.assertEqual(result["confidence"], 1.0)
        self.assertEqual(result["extra"], "data")
    
    def test_optional_fields(self):
        """Tests"""
        finding = Finding(
            rule_id="test_rule",
            message="Test",
            severity=RuleSeverity.MAJOR
        )
        
        self.assertIsNone(finding.file_path)
        self.assertIsNone(finding.line_number)
        self.assertIsNone(finding.column)
        self.assertIsNone(finding.code_snippet)
        self.assertIsNone(finding.suggestion)
        self.assertEqual(finding.confidence, 1.0)


class TestRuleBaseClass(unittest.TestCase):
    """Tests"""
    
    def test_abstract_methods(self):
        """Tests"""
        # TestRule
        self.assertTrue(issubclass(Rule, object))
        
        # 
        class ConcreteRule(Rule):
            @property
            def metadata(self):
                return RuleMetadata(
                    id="concrete_rule",
                    name="Rule",
                    description="Rule",
                    severity=RuleSeverity.MINOR,
                    category=RuleCategory.CORRECTNESS
                )
            
            def check(self, context):
                return []
        
        rule = ConcreteRule()
        
        # Test
        self.assertEqual(rule.metadata.id, "concrete_rule")
        
        # Testcheck（）
        from rule_engine.context import RuleContext
        context = RuleContext(
            code="test code",
            file_path="test.kt",
            language="kotlin"
        )
        findings = rule.check(context)
        self.assertEqual(findings, [])
        
        # Test
        rule.on_register()
        rule.on_unregister()
        
        # TestCalculate
        deduction = rule.get_score_deduction(RuleSeverity.MINOR)
        self.assertEqual(deduction, 5)
        
        deduction = rule.get_score_deduction(RuleSeverity.MAJOR)
        self.assertEqual(deduction, 10)
        
        deduction = rule.get_score_deduction(RuleSeverity.CRITICAL)
        self.assertEqual(deduction, 20)
        
        deduction = rule.get_score_deduction(RuleSeverity.BLOCKER)
        self.assertEqual(deduction, 100)
        
        deduction = rule.get_score_deduction(RuleSeverity.INFO)
        self.assertEqual(deduction, 0)
    
    def test_custom_score_deduction(self):
        """Tests"""
        class CustomRule(Rule):
            @property
            def metadata(self):
                return RuleMetadata(
                    id="custom_rule",
                    name="Rule",
                    description="Rule",
                    severity=RuleSeverity.MINOR,
                    category=RuleCategory.CORRECTNESS,
                    min_score_deduction=2,
                    max_score_deduction=8
                )
            
            def check(self, context):
                return []
        
        rule = CustomRule()
        
        # Test
        deduction = rule.get_score_deduction(RuleSeverity.MINOR)  # 5，2-8
        self.assertEqual(deduction, 5)
        
        deduction = rule.get_score_deduction(RuleSeverity.INFO)  # 0，2
        self.assertEqual(deduction, 2)
        
        deduction = rule.get_score_deduction(RuleSeverity.BLOCKER)  # 100，8
        self.assertEqual(deduction, 8)


if __name__ == "__main__":
    unittest.main()