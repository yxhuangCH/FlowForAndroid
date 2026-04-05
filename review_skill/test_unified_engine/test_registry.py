"""Tests for unified_engine/registry.py"""

import unittest
from typing import List

from unified_engine import (
    UnifiedRegistry,
    UnifiedRule,
    ExecutionMode,
    unified_rule,
    RuleMetadata,
    Finding,
    RuleSeverity,
    RuleCategory,
)
from unified_engine.context import UnifiedContext


class TestRule(UnifiedRule):
    """测试规则"""

    execution_mode = ExecutionMode.HYBRID

    def __init__(self, rule_id: str = "test_rule"):
        self._id = rule_id
        self._metadata = RuleMetadata(
            id=rule_id,
            name="Test Rule",
            description="A test rule",
            severity=RuleSeverity.MAJOR,
            category=RuleCategory.BEST_PRACTICE,
            tags=["test", "example"],
        )

    @property
    def metadata(self) -> RuleMetadata:
        return self._metadata

    def check(self, context: UnifiedContext) -> List[Finding]:
        return []


class FastRule(UnifiedRule):
    """快速规则"""

    execution_mode = ExecutionMode.FAST

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="fast_rule",
            name="Fast Rule",
            description="A fast rule",
            severity=RuleSeverity.INFO,
            category=RuleCategory.STYLE,
            tags=["fast"],
        )

    def check(self, context: UnifiedContext) -> List[Finding]:
        return []


class PreciseRule(UnifiedRule):
    """精确规则"""

    execution_mode = ExecutionMode.PRECISE

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="precise_rule",
            name="Precise Rule",
            description="A precise rule",
            severity=RuleSeverity.CRITICAL,
            category=RuleCategory.SECURITY,
            tags=["precise"],
        )

    def check(self, context: UnifiedContext) -> List[Finding]:
        return []


class TestUnifiedRegistry(unittest.TestCase):
    """测试 UnifiedRegistry"""

    def setUp(self):
        """每个测试前清理注册表"""
        registry = UnifiedRegistry()
        registry.clear()

    def tearDown(self):
        """每个测试后清理注册表"""
        registry = UnifiedRegistry()
        registry.clear()

    def test_singleton(self):
        """测试单例模式"""
        registry1 = UnifiedRegistry()
        registry2 = UnifiedRegistry()
        self.assertIs(registry1, registry2)

    def test_register_and_get_rule(self):
        """测试注册和获取规则"""
        registry = UnifiedRegistry()
        rule = TestRule()

        registry.register(rule)

        retrieved = registry.get_rule("test_rule")
        self.assertIs(retrieved, rule)

    def test_register_duplicate_id_raises(self):
        """测试重复 ID 注册抛出异常"""
        registry = UnifiedRegistry()
        rule1 = TestRule("duplicate_id")
        rule2 = TestRule("duplicate_id")

        registry.register(rule1)
        with self.assertRaises(ValueError) as ctx:
            registry.register(rule2)
        self.assertIn("duplicate_id", str(ctx.exception))

    def test_register_empty_id_raises(self):
        """测试空 ID 注册抛出异常"""
        registry = UnifiedRegistry()

        # 创建一个 mock 规则，其 metadata.id 为空字符串
        class EmptyIdRule(UnifiedRule):
            execution_mode = ExecutionMode.FAST

            @property
            def metadata(self) -> RuleMetadata:
                # 创建一个 metadata 对象并手动设置 id 为空
                m = RuleMetadata(
                    id="dummy",  # 先用一个非空值
                    name="Empty ID Rule",
                    description="Rule with empty id",
                    severity=RuleSeverity.INFO,
                    category=RuleCategory.STYLE,
                )
                # 绕过验证直接修改 id
                object.__setattr__(m, 'id', '')
                return m

            def check(self, context: UnifiedContext) -> List[Finding]:
                return []

        rule = EmptyIdRule()

        with self.assertRaises(ValueError) as ctx:
            registry.register(rule)
        self.assertIn("empty", str(ctx.exception).lower())

    def test_unregister(self):
        """测试注销规则"""
        registry = UnifiedRegistry()
        rule = TestRule("to_remove")

        registry.register(rule)
        self.assertIsNotNone(registry.get_rule("to_remove"))

        removed = registry.unregister("to_remove")
        self.assertIs(removed, rule)
        self.assertIsNone(registry.get_rule("to_remove"))

    def test_unregister_nonexistent(self):
        """测试注销不存在的规则"""
        registry = UnifiedRegistry()
        removed = registry.unregister("nonexistent")
        self.assertIsNone(removed)

    def test_has_rule(self):
        """测试检查规则存在"""
        registry = UnifiedRegistry()
        rule = TestRule("exists")

        self.assertFalse(registry.has_rule("exists"))
        registry.register(rule)
        self.assertTrue(registry.has_rule("exists"))

    def test_get_all_rules(self):
        """测试获取所有规则"""
        registry = UnifiedRegistry()
        registry.register(TestRule("rule1"))
        registry.register(TestRule("rule2"))

        all_rules = registry.get_all_rules()
        self.assertEqual(len(all_rules), 2)

    def test_get_all_rules_enabled_only(self):
        """测试只获取启用的规则"""
        registry = UnifiedRegistry()
        rule1 = TestRule("enabled_rule")
        rule2 = TestRule("disabled_rule")

        registry.register(rule1)
        registry.register(rule2)
        registry.disable_rule("disabled_rule")

        all_rules = registry.get_all_rules(enabled_only=True)
        self.assertEqual(len(all_rules), 1)
        self.assertEqual(all_rules[0].metadata.id, "enabled_rule")

    def test_get_rules_by_mode(self):
        """测试按执行模式获取规则"""
        registry = UnifiedRegistry()
        registry.register(FastRule())
        registry.register(PreciseRule())

        fast_rules = registry.get_rules_by_mode(ExecutionMode.FAST)
        self.assertEqual(len(fast_rules), 1)
        self.assertEqual(fast_rules[0].metadata.id, "fast_rule")

        precise_rules = registry.get_rules_by_mode(ExecutionMode.PRECISE)
        self.assertEqual(len(precise_rules), 1)

    def test_get_rules_by_category(self):
        """测试按分类获取规则"""
        registry = UnifiedRegistry()
        registry.register(TestRule("rule1"))

        rules = registry.get_rules_by_category(RuleCategory.BEST_PRACTICE)
        self.assertEqual(len(rules), 1)

    def test_get_rules_by_tag(self):
        """测试按标签获取规则"""
        registry = UnifiedRegistry()
        registry.register(TestRule("rule1"))

        rules = registry.get_rules_by_tag("test")
        self.assertEqual(len(rules), 1)

        rules = registry.get_rules_by_tag("nonexistent")
        self.assertEqual(len(rules), 0)

    def test_get_rules_by_severity(self):
        """测试按严重程度获取规则"""
        registry = UnifiedRegistry()
        registry.register(TestRule("rule1"))  # WARNING
        registry.register(PreciseRule())  # CRITICAL

        major_rules = registry.get_rules_by_severity(RuleSeverity.MAJOR)
        self.assertEqual(len(major_rules), 1)

        critical_rules = registry.get_rules_by_severity(RuleSeverity.CRITICAL)
        self.assertEqual(len(critical_rules), 1)

    def test_get_rules_by_ids(self):
        """测试按 ID 列表获取规则"""
        registry = UnifiedRegistry()
        registry.register(TestRule("rule1"))
        registry.register(TestRule("rule2"))

        rules = registry.get_rules_by_ids(["rule1", "rule2", "nonexistent"])
        self.assertEqual(len(rules), 2)

    def test_enable_disable_rule(self):
        """测试启用/禁用规则"""
        registry = UnifiedRegistry()
        rule = TestRule("toggle_rule")
        registry.register(rule)

        # 禁用
        self.assertTrue(registry.disable_rule("toggle_rule"))
        self.assertFalse(rule.metadata.enabled)

        # 启用
        self.assertTrue(registry.enable_rule("toggle_rule"))
        self.assertTrue(rule.metadata.enabled)

        # 操作不存在的规则
        self.assertFalse(registry.disable_rule("nonexistent"))
        self.assertFalse(registry.enable_rule("nonexistent"))

    def test_enable_disable_rules_by_category(self):
        """测试批量启用/禁用规则"""
        registry = UnifiedRegistry()
        registry.register(TestRule("rule1"))
        registry.register(TestRule("rule2"))

        count = registry.disable_rules_by_category(RuleCategory.BEST_PRACTICE)
        self.assertEqual(count, 2)

        count = registry.enable_rules_by_category(RuleCategory.BEST_PRACTICE)
        self.assertEqual(count, 2)

    def test_listeners(self):
        """测试注册表监听器"""
        registry = UnifiedRegistry()
        events = []

        def listener(rule_id, rule, event):
            events.append((rule_id, event))

        registry.add_listener(listener)

        rule = TestRule("listened_rule")
        registry.register(rule)
        self.assertEqual(events, [("listened_rule", "registered")])

        registry.unregister("listened_rule")
        self.assertEqual(
            events, [("listened_rule", "registered"), ("listened_rule", "unregistered")]
        )

        # 移除监听器
        registry.remove_listener(listener)
        registry.register(TestRule("another_rule"))
        self.assertEqual(len(events), 2)  # 没有新事件

    def test_get_statistics(self):
        """测试获取统计信息"""
        registry = UnifiedRegistry()
        registry.register(FastRule())
        registry.register(PreciseRule())

        stats = registry.get_statistics()
        self.assertEqual(stats["total_rules"], 2)
        self.assertEqual(stats["by_mode"]["fast"], 1)
        self.assertEqual(stats["by_mode"]["precise"], 1)

    def test_get_all_tags(self):
        """测试获取所有标签"""
        registry = UnifiedRegistry()
        registry.register(TestRule("rule1"))

        tags = registry.get_all_tags()
        self.assertIn("test", tags)
        self.assertIn("example", tags)

    def test_get_all_categories(self):
        """测试获取所有分类"""
        registry = UnifiedRegistry()
        registry.register(TestRule("rule1"))

        categories = registry.get_all_categories()
        self.assertIn(RuleCategory.BEST_PRACTICE, categories)

    def test_len_and_contains(self):
        """测试 __len__ 和 __contains__"""
        registry = UnifiedRegistry()
        self.assertEqual(len(registry), 0)
        self.assertNotIn("rule1", registry)

        registry.register(TestRule("rule1"))
        self.assertEqual(len(registry), 1)
        self.assertIn("rule1", registry)

    def test_clear(self):
        """测试清空注册表"""
        registry = UnifiedRegistry()
        registry.register(TestRule("rule1"))
        registry.register(TestRule("rule2"))

        self.assertEqual(len(registry), 2)
        registry.clear()
        self.assertEqual(len(registry), 0)


class TestUnifiedRuleDecorator(unittest.TestCase):
    """测试 unified_rule 装饰器"""

    def tearDown(self):
        """清理注册表"""
        UnifiedRegistry().clear()

    def test_decorator_registers_rule(self):
        """测试装饰器自动注册规则"""

        @unified_rule
        class AutoRegisteredRule(UnifiedRule):
            execution_mode = ExecutionMode.FAST

            @property
            def metadata(self) -> RuleMetadata:
                return RuleMetadata(
                    id="auto_rule",
                    name="Auto Rule",
                    description="Auto registered",
                    severity=RuleSeverity.INFO,
                    category=RuleCategory.STYLE,
                )

            def check(self, context: UnifiedContext) -> List[Finding]:
                return []

        registry = UnifiedRegistry()
        self.assertIsNotNone(registry.get_rule("auto_rule"))

    def test_decorator_preserves_class(self):
        """测试装饰器保留原类"""

        @unified_rule
        class MyRule(UnifiedRule):
            execution_mode = ExecutionMode.FAST

            @property
            def metadata(self) -> RuleMetadata:
                return RuleMetadata(
                    id="my_rule",
                    name="My Rule",
                    description="My rule",
                    severity=RuleSeverity.INFO,
                    category=RuleCategory.STYLE,
                )

            def check(self, context: UnifiedContext) -> List[Finding]:
                return []

            def custom_method(self):
                return "custom"

        # 类应该保持原样
        self.assertTrue(hasattr(MyRule, "custom_method"))
        instance = MyRule()
        self.assertEqual(instance.custom_method(), "custom")


if __name__ == "__main__":
    unittest.main()
