"""Tests"""
import unittest
from rule_engine.registry import RuleRegistry
from rule_engine.interfaces import Rule, RuleMetadata, RuleSeverity, RuleCategory


class TestRuleRegistry(unittest.TestCase):
    """Tests"""
    
    def setUp(self):
        self.registry = RuleRegistry()
        
        # TestRule
        class TestRule(Rule):
            def __init__(self, rule_id, enabled=True):
                self._metadata = RuleMetadata(
                    id=rule_id,
                    name=f"Test Rule {rule_id}",
                    description=f"Test description for {rule_id}",
                    severity=RuleSeverity.MINOR,
                    category=RuleCategory.CORRECTNESS,
                    enabled=enabled,
                    tags=["test"]
                )
                self.registered = False
                self.unregistered = False
            
            @property
            def metadata(self):
                return self._metadata
            
            def check(self, context):
                return []
            
            def on_register(self):
                self.registered = True
            
            def on_unregister(self):
                self.unregistered = True
        
        self.TestRule = TestRule
        self.test_rule1 = TestRule("test_rule_1")
        self.test_rule2 = TestRule("test_rule_2")
    
    def tearDown(self):
        # ClearRegister，Test
        self.registry.clear()
    
    def test_register_rule(self):
        """Tests"""
        self.registry.register(self.test_rule1)
        self.assertIn("test_rule_1", self.registry.get_all_rule_ids())
        self.assertTrue(self.test_rule1.registered)
        
        # VerifyRuleIDGet
        rule = self.registry.get_rule("test_rule_1")
        self.assertIsNotNone(rule)
        self.assertEqual(rule.metadata.id, "test_rule_1")
    
    def test_duplicate_registration(self):
        """Tests"""
        self.registry.register(self.test_rule1)
        with self.assertRaises(ValueError):
            self.registry.register(self.test_rule1)
    
    def test_unregister_rule(self):
        """Tests"""
        self.registry.register(self.test_rule1)
        self.registry.unregister("test_rule_1")
        
        self.assertNotIn("test_rule_1", self.registry.get_all_rule_ids())
        self.assertTrue(self.test_rule1.unregistered)
        
        # VerifyRuleGet
        rule = self.registry.get_rule("test_rule_1")
        self.assertIsNone(rule)
    
    def test_unregister_nonexistent_rule(self):
        """Tests"""
        with self.assertRaises(ValueError):
            self.registry.unregister("nonexistent_rule")
    
    def test_get_rules_by_category(self):
        """Tests"""
        self.registry.register(self.test_rule1)
        self.registry.register(self.test_rule2)
        
        rules = self.registry.get_rules_by_category(RuleCategory.CORRECTNESS)
        self.assertEqual(len(rules), 2)
        
        # TestGetEnableRule
        disabled_rule = self.TestRule("test_rule_3", enabled=False)
        self.registry.register(disabled_rule)
        
        enabled_rules = self.registry.get_rules_by_category(RuleCategory.CORRECTNESS, enabled_only=True)
        self.assertEqual(len(enabled_rules), 2)  # RuleEnable
        
        all_rules = self.registry.get_rules_by_category(RuleCategory.CORRECTNESS, enabled_only=False)
        self.assertEqual(len(all_rules), 3)  # DisableRule
    
    def test_get_rules_by_tag(self):
        """Tests"""
        # Rule
        class TaggedRule(Rule):
            def __init__(self, rule_id, tags):
                self._metadata = RuleMetadata(
                    id=rule_id,
                    name=f"Tagged Rule {rule_id}",
                    description=f"Tagged rule {rule_id}",
                    severity=RuleSeverity.MINOR,
                    category=RuleCategory.CORRECTNESS,
                    tags=tags
                )
            
            @property
            def metadata(self):
                return self._metadata
            
            def check(self, context):
                return []
        
        tagged_rule1 = TaggedRule("tagged_1", ["android", "kotlin"])
        tagged_rule2 = TaggedRule("tagged_2", ["android", "compose"])
        
        self.registry.register(tagged_rule1)
        self.registry.register(tagged_rule2)
        
        # GetandroidRule
        android_rules = self.registry.get_rules_by_tag("android")
        self.assertEqual(len(android_rules), 2)
        
        # GetkotlinRule
        kotlin_rules = self.registry.get_rules_by_tag("kotlin")
        self.assertEqual(len(kotlin_rules), 1)
        self.assertEqual(kotlin_rules[0].metadata.id, "tagged_1")
        
        # Get
        nonexistent_rules = self.registry.get_rules_by_tag("nonexistent")
        self.assertEqual(len(nonexistent_rules), 0)
    
    def test_get_rules_by_severity(self):
        """Tests"""
        class MajorRule(Rule):
            def __init__(self, rule_id):
                self._metadata = RuleMetadata(
                    id=rule_id,
                    name=f"Major Rule {rule_id}",
                    description=f"Major rule {rule_id}",
                    severity=RuleSeverity.MAJOR,
                    category=RuleCategory.CORRECTNESS
                )
            
            @property
            def metadata(self):
                return self._metadata
            
            def check(self, context):
                return []
        
        major_rule = MajorRule("major_rule")
        self.registry.register(self.test_rule1)  # MINOR severity
        self.registry.register(major_rule)  # MAJOR severity
        
        minor_rules = self.registry.get_rules_by_severity(RuleSeverity.MINOR)
        self.assertEqual(len(minor_rules), 1)
        self.assertEqual(minor_rules[0].metadata.id, "test_rule_1")
        
        major_rules = self.registry.get_rules_by_severity(RuleSeverity.MAJOR)
        self.assertEqual(len(major_rules), 1)
        self.assertEqual(major_rules[0].metadata.id, "major_rule")
        
        critical_rules = self.registry.get_rules_by_severity(RuleSeverity.CRITICAL)
        self.assertEqual(len(critical_rules), 0)
    
    def test_enable_disable_rule(self):
        """Tests"""
        self.registry.register(self.test_rule1)
        
        # Enable
        self.assertTrue(self.registry.is_rule_enabled("test_rule_1"))
        
        # DisableRule
        self.registry.disable_rule("test_rule_1")
        self.assertFalse(self.registry.is_rule_enabled("test_rule_1"))
        
        # EnableRule
        self.registry.enable_rule("test_rule_1")
        self.assertTrue(self.registry.is_rule_enabled("test_rule_1"))
    
    def test_enable_disable_nonexistent_rule(self):
        """Tests"""
        # （）
        self.registry.enable_rule("nonexistent_rule")
        self.registry.disable_rule("nonexistent_rule")
        
        # CheckRuleFalse
        self.assertFalse(self.registry.is_rule_enabled("nonexistent_rule"))
    
    def test_get_all_rules(self):
        """Tests"""
        self.registry.register(self.test_rule1)
        self.registry.register(self.test_rule2)
        
        all_rules = self.registry.get_all_rules(enabled_only=False)
        self.assertEqual(len(all_rules), 2)
        
        # DisableRule
        self.registry.disable_rule("test_rule_1")
        
        enabled_rules = self.registry.get_all_rules(enabled_only=True)
        self.assertEqual(len(enabled_rules), 1)
        self.assertEqual(enabled_rules[0].metadata.id, "test_rule_2")
    
    def test_get_all_categories(self):
        """Tests"""
        # TeardownRegister，Rule
        self.registry.clear()
        
        # Rule
        class PerformanceRule(Rule):
            def __init__(self, rule_id):
                self._metadata = RuleMetadata(
                    id=rule_id,
                    name=f"Performance Rule {rule_id}",
                    description=f"Performance rule {rule_id}",
                    severity=RuleSeverity.MINOR,
                    category=RuleCategory.PERFORMANCE
                )
            
            @property
            def metadata(self):
                return self._metadata
            
            def check(self, context):
                return []
        
        performance_rule = PerformanceRule("performance_rule")
        
        self.registry.register(self.test_rule1)  # CORRECTNESS
        self.registry.register(performance_rule)  # PERFORMANCE
        
        categories = self.registry.get_all_categories()
        
        # CheckAdd
        self.assertIn(RuleCategory.CORRECTNESS, categories)
        self.assertIn(RuleCategory.PERFORMANCE, categories)
        
        # ，
        # Check
    
    def test_get_all_tags(self):
        """Tests"""
        # GetRegisterClear，Test
        self.registry.clear()
        
        class TaggedRule(Rule):
            def __init__(self, rule_id, tags):
                self._metadata = RuleMetadata(
                    id=rule_id,
                    name=f"Tagged Rule {rule_id}",
                    description=f"Tagged rule {rule_id}",
                    severity=RuleSeverity.MINOR,
                    category=RuleCategory.CORRECTNESS,
                    tags=tags
                )
            
            @property
            def metadata(self):
                return self._metadata
            
            def check(self, context):
                return []
        
        tagged_rule1 = TaggedRule("tagged_1", ["android", "kotlin"])
        tagged_rule2 = TaggedRule("tagged_2", ["android", "compose"])
        
        self.registry.register(tagged_rule1)
        self.registry.register(tagged_rule2)
        
        tags = self.registry.get_all_tags()
        
        # Check
        self.assertIn("android", tags)
        self.assertIn("kotlin", tags)
        self.assertIn("compose", tags)
        
        # ，，
        # Check，Check
    
    def test_count_rules(self):
        """Tests"""
        self.assertEqual(self.registry.count_rules(), 0)
        
        self.registry.register(self.test_rule1)
        self.assertEqual(self.registry.count_rules(), 1)
        
        self.registry.register(self.test_rule2)
        self.assertEqual(self.registry.count_rules(), 2)
        
        self.registry.unregister("test_rule_1")
        self.assertEqual(self.registry.count_rules(), 1)
    
    def test_get_statistics(self):
        """Tests"""
        self.registry.register(self.test_rule1)
        self.registry.register(self.test_rule2)
        
        stats = self.registry.get_statistics()
        
        self.assertEqual(stats["total_rules"], 2)
        self.assertEqual(stats["enabled_rules"], 2)
        
        # VerifyCount
        self.assertIn("correctness", stats["categories"])
        self.assertEqual(stats["categories"]["correctness"], 2)
        
        # VerifyCount
        self.assertIn("test", stats["tags"])
        self.assertEqual(stats["tags"]["test"], 2)
        
        # VerifyCount
        self.assertIn("minor", stats["severities"])
        self.assertEqual(stats["severities"]["minor"], 2)
    
    def test_clear(self):
        """Tests"""
        # Register
        self.registry.clear()
        
        # TestRule，clearon_unregister
        self.test_rule1 = self.TestRule("test_rule_1")
        self.test_rule2 = self.TestRule("test_rule_2")
        
        self.registry.register(self.test_rule1)
        self.registry.register(self.test_rule2)
        
        self.assertEqual(self.registry.count_rules(), 2)
        
        self.registry.clear()
        
        self.assertEqual(self.registry.count_rules(), 0)
        self.assertEqual(len(self.registry.get_all_rule_ids()), 0)
        self.assertTrue(self.test_rule1.unregistered)
        self.assertTrue(self.test_rule2.unregistered)
    
    def test_listener(self):
        """Tests"""
        events = []
        
        def listener(event_type, rule):
            events.append((event_type, rule.metadata.id))
        
        self.registry.add_listener(listener)
        
        # RegisterRule
        self.registry.register(self.test_rule1)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0], ("register", "test_rule_1"))
        
        # UnregisterRule
        self.registry.unregister("test_rule_1")
        self.assertEqual(len(events), 2)
        self.assertEqual(events[1], ("unregister", "test_rule_1"))
        
        # Remove
        self.registry.remove_listener(listener)
        
        # Register new rulesRemove
        self.registry.register(self.test_rule2)
        self.assertEqual(len(events), 2)  # 


if __name__ == "__main__":
    unittest.main()