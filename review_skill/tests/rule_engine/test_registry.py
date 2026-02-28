"""
测试规则注册表
"""
import unittest
from rule_engine.registry import RuleRegistry
from rule_engine.interfaces import Rule, RuleMetadata, RuleSeverity, RuleCategory


class TestRuleRegistry(unittest.TestCase):
    """测试规则注册表"""
    
    def setUp(self):
        self.registry = RuleRegistry()
        
        # 创建测试规则
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
        # 清空注册表，避免测试间干扰
        self.registry.clear()
    
    def test_register_rule(self):
        """测试注册规则"""
        self.registry.register(self.test_rule1)
        self.assertIn("test_rule_1", self.registry.get_all_rule_ids())
        self.assertTrue(self.test_rule1.registered)
        
        # 验证规则可以通过ID获取
        rule = self.registry.get_rule("test_rule_1")
        self.assertIsNotNone(rule)
        self.assertEqual(rule.metadata.id, "test_rule_1")
    
    def test_duplicate_registration(self):
        """测试重复注册"""
        self.registry.register(self.test_rule1)
        with self.assertRaises(ValueError):
            self.registry.register(self.test_rule1)
    
    def test_unregister_rule(self):
        """测试注销规则"""
        self.registry.register(self.test_rule1)
        self.registry.unregister("test_rule_1")
        
        self.assertNotIn("test_rule_1", self.registry.get_all_rule_ids())
        self.assertTrue(self.test_rule1.unregistered)
        
        # 验证规则无法再获取
        rule = self.registry.get_rule("test_rule_1")
        self.assertIsNone(rule)
    
    def test_unregister_nonexistent_rule(self):
        """测试注销不存在的规则"""
        with self.assertRaises(ValueError):
            self.registry.unregister("nonexistent_rule")
    
    def test_get_rules_by_category(self):
        """测试按分类获取规则"""
        self.registry.register(self.test_rule1)
        self.registry.register(self.test_rule2)
        
        rules = self.registry.get_rules_by_category(RuleCategory.CORRECTNESS)
        self.assertEqual(len(rules), 2)
        
        # 测试只获取启用的规则
        disabled_rule = self.TestRule("test_rule_3", enabled=False)
        self.registry.register(disabled_rule)
        
        enabled_rules = self.registry.get_rules_by_category(RuleCategory.CORRECTNESS, enabled_only=True)
        self.assertEqual(len(enabled_rules), 2)  # 只有前两个规则是启用的
        
        all_rules = self.registry.get_rules_by_category(RuleCategory.CORRECTNESS, enabled_only=False)
        self.assertEqual(len(all_rules), 3)  # 包括禁用的规则
    
    def test_get_rules_by_tag(self):
        """测试按标签获取规则"""
        # 创建一个带特定标签的规则
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
        
        # 获取带有android标签的规则
        android_rules = self.registry.get_rules_by_tag("android")
        self.assertEqual(len(android_rules), 2)
        
        # 获取带有kotlin标签的规则
        kotlin_rules = self.registry.get_rules_by_tag("kotlin")
        self.assertEqual(len(kotlin_rules), 1)
        self.assertEqual(kotlin_rules[0].metadata.id, "tagged_1")
        
        # 获取不存在的标签
        nonexistent_rules = self.registry.get_rules_by_tag("nonexistent")
        self.assertEqual(len(nonexistent_rules), 0)
    
    def test_get_rules_by_severity(self):
        """测试按严重级别获取规则"""
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
        """测试启用/禁用规则"""
        self.registry.register(self.test_rule1)
        
        # 初始状态应该是启用的
        self.assertTrue(self.registry.is_rule_enabled("test_rule_1"))
        
        # 禁用规则
        self.registry.disable_rule("test_rule_1")
        self.assertFalse(self.registry.is_rule_enabled("test_rule_1"))
        
        # 重新启用规则
        self.registry.enable_rule("test_rule_1")
        self.assertTrue(self.registry.is_rule_enabled("test_rule_1"))
    
    def test_enable_disable_nonexistent_rule(self):
        """测试启用/禁用不存在的规则"""
        # 这些操作应该静默失败（不抛出异常）
        self.registry.enable_rule("nonexistent_rule")
        self.registry.disable_rule("nonexistent_rule")
        
        # 检查不存在的规则应该返回False
        self.assertFalse(self.registry.is_rule_enabled("nonexistent_rule"))
    
    def test_get_all_rules(self):
        """测试获取所有规则"""
        self.registry.register(self.test_rule1)
        self.registry.register(self.test_rule2)
        
        all_rules = self.registry.get_all_rules(enabled_only=False)
        self.assertEqual(len(all_rules), 2)
        
        # 禁用一个规则
        self.registry.disable_rule("test_rule_1")
        
        enabled_rules = self.registry.get_all_rules(enabled_only=True)
        self.assertEqual(len(enabled_rules), 1)
        self.assertEqual(enabled_rules[0].metadata.id, "test_rule_2")
    
    def test_get_all_categories(self):
        """测试获取所有分类"""
        # 清理注册表，确保没有其他规则干扰
        self.registry.clear()
        
        # 创建不同分类的规则
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
        
        # 检查我们添加的分类存在
        self.assertIn(RuleCategory.CORRECTNESS, categories)
        self.assertIn(RuleCategory.PERFORMANCE, categories)
        
        # 由于单例模式，可能还有其他分类存在
        # 所以不检查精确长度
    
    def test_get_all_tags(self):
        """测试获取所有标签"""
        # 获取注册表实例后立即清空，确保测试独立
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
        
        # 检查包含预期的标签
        self.assertIn("android", tags)
        self.assertIn("kotlin", tags)
        self.assertIn("compose", tags)
        
        # 由于单例模式，可能有其他标签存在，但我们只关心包含的标签
        # 所以不检查长度，只检查是否包含预期的标签
    
    def test_count_rules(self):
        """测试统计规则数量"""
        self.assertEqual(self.registry.count_rules(), 0)
        
        self.registry.register(self.test_rule1)
        self.assertEqual(self.registry.count_rules(), 1)
        
        self.registry.register(self.test_rule2)
        self.assertEqual(self.registry.count_rules(), 2)
        
        self.registry.unregister("test_rule_1")
        self.assertEqual(self.registry.count_rules(), 1)
    
    def test_get_statistics(self):
        """测试获取统计信息"""
        self.registry.register(self.test_rule1)
        self.registry.register(self.test_rule2)
        
        stats = self.registry.get_statistics()
        
        self.assertEqual(stats["total_rules"], 2)
        self.assertEqual(stats["enabled_rules"], 2)
        
        # 验证分类统计
        self.assertIn("correctness", stats["categories"])
        self.assertEqual(stats["categories"]["correctness"], 2)
        
        # 验证标签统计
        self.assertIn("test", stats["tags"])
        self.assertEqual(stats["tags"]["test"], 2)
        
        # 验证严重级别统计
        self.assertIn("minor", stats["severities"])
        self.assertEqual(stats["severities"]["minor"], 2)
    
    def test_clear(self):
        """测试清空注册表"""
        # 确保注册表是干净的
        self.registry.clear()
        
        # 重新创建测试规则，因为clear会触发on_unregister
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
        """测试监听器"""
        events = []
        
        def listener(event_type, rule):
            events.append((event_type, rule.metadata.id))
        
        self.registry.add_listener(listener)
        
        # 注册规则应该触发监听器
        self.registry.register(self.test_rule1)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0], ("register", "test_rule_1"))
        
        # 注销规则应该触发监听器
        self.registry.unregister("test_rule_1")
        self.assertEqual(len(events), 2)
        self.assertEqual(events[1], ("unregister", "test_rule_1"))
        
        # 移除监听器
        self.registry.remove_listener(listener)
        
        # 注册新规则不应该触发已移除的监听器
        self.registry.register(self.test_rule2)
        self.assertEqual(len(events), 2)  # 没有增加


if __name__ == "__main__":
    unittest.main()