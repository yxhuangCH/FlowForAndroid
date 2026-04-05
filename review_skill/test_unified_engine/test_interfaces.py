"""Tests for unified_engine/interfaces.py"""

import unittest
from typing import List

from unified_engine import (
    UnifiedRule,
    ExecutionMode,
    ExecutionPlan,
    ExecutionStats,
    RuleExecutionTime,
    RuleMetadata,
    Finding,
    RuleSeverity,
    RuleCategory,
)
from unified_engine.context import UnifiedContext


class TestExecutionMode(unittest.TestCase):
    """测试 ExecutionMode 枚举"""

    def test_execution_mode_values(self):
        """测试枚举值"""
        self.assertEqual(ExecutionMode.FAST.value, "fast")
        self.assertEqual(ExecutionMode.PRECISE.value, "precise")
        self.assertEqual(ExecutionMode.HYBRID.value, "hybrid")


class TestUnifiedRule(unittest.TestCase):
    """测试 UnifiedRule 基类"""

    def test_default_execution_mode(self):
        """测试默认执行模式是 HYBRID"""

        class TestRule(UnifiedRule):
            @property
            def metadata(self) -> RuleMetadata:
                return RuleMetadata(
                    id="test_rule",
                    name="Test Rule",
                    description="A test rule",
                    severity=RuleSeverity.INFO,
                    category=RuleCategory.STYLE,
                )

            def check(self, context: UnifiedContext) -> List[Finding]:
                return []

        rule = TestRule()
        self.assertEqual(rule.execution_mode, ExecutionMode.HYBRID)

    def test_custom_execution_mode(self):
        """测试自定义执行模式"""

        class FastRule(UnifiedRule):
            execution_mode = ExecutionMode.FAST

            @property
            def metadata(self) -> RuleMetadata:
                return RuleMetadata(
                    id="fast_rule",
                    name="Fast Rule",
                    description="A fast rule",
                    severity=RuleSeverity.INFO,
                    category=RuleCategory.STYLE,
                )

            def check(self, context: UnifiedContext) -> List[Finding]:
                return []

        rule = FastRule()
        self.assertEqual(rule.execution_mode, ExecutionMode.FAST)

    def test_get_score_deduction(self):
        """测试扣分计算"""

        class TestRule(UnifiedRule):
            @property
            def metadata(self) -> RuleMetadata:
                return RuleMetadata(
                    id="test_rule",
                    name="Test Rule",
                    description="A test rule",
                    severity=RuleSeverity.MAJOR,
                    category=RuleCategory.STYLE,
                )

            def check(self, context: UnifiedContext) -> List[Finding]:
                return []

        rule = TestRule()
        self.assertEqual(rule.get_score_deduction(RuleSeverity.INFO), 0)
        self.assertEqual(rule.get_score_deduction(RuleSeverity.MINOR), 5)
        self.assertEqual(rule.get_score_deduction(RuleSeverity.MAJOR), 10)
        self.assertEqual(rule.get_score_deduction(RuleSeverity.CRITICAL), 20)
        self.assertEqual(rule.get_score_deduction(RuleSeverity.BLOCKER), 100)

    def test_get_score_deduction_with_custom_range(self):
        """测试自定义扣分范围"""

        class CustomRule(UnifiedRule):
            @property
            def metadata(self) -> RuleMetadata:
                return RuleMetadata(
                    id="custom_rule",
                    name="Custom Rule",
                    description="A custom rule",
                    severity=RuleSeverity.MAJOR,
                    category=RuleCategory.STYLE,
                    min_score_deduction=3,
                    max_score_deduction=15,
                )

            def check(self, context: UnifiedContext) -> List[Finding]:
                return []

        rule = CustomRule()
        # MAJOR 默认是 10，在 3-15 范围内，应该返回 10
        self.assertEqual(rule.get_score_deduction(RuleSeverity.MAJOR), 10)
        # BLOCKER 默认是 100，超过上限 15，应该返回 15
        self.assertEqual(rule.get_score_deduction(RuleSeverity.BLOCKER), 15)
        # MINOR 默认是 5，在范围内，应该返回 5
        self.assertEqual(rule.get_score_deduction(RuleSeverity.MINOR), 5)


class TestExecutionPlan(unittest.TestCase):
    """测试 ExecutionPlan"""

    def test_empty_plan(self):
        """测试空执行计划"""
        plan = ExecutionPlan()
        self.assertEqual(plan.total_rules, 0)
        self.assertFalse(plan.needs_ast_parsing)

    def test_plan_with_rules(self):
        """测试包含规则的执行计划"""

        class FastRule(UnifiedRule):
            execution_mode = ExecutionMode.FAST

            @property
            def metadata(self) -> RuleMetadata:
                return RuleMetadata(
                    id="fast_rule",
                    name="Fast Rule",
                    description="Fast",
                    severity=RuleSeverity.INFO,
                    category=RuleCategory.STYLE,
                )

            def check(self, context: UnifiedContext) -> List[Finding]:
                return []

        class PreciseRule(UnifiedRule):
            execution_mode = ExecutionMode.PRECISE

            @property
            def metadata(self) -> RuleMetadata:
                return RuleMetadata(
                    id="precise_rule",
                    name="Precise Rule",
                    description="Precise",
                    severity=RuleSeverity.INFO,
                    category=RuleCategory.STYLE,
                )

            def check(self, context: UnifiedContext) -> List[Finding]:
                return []

        plan = ExecutionPlan(
            fast_rules=[FastRule()],
            precise_rules=[PreciseRule()],
        )
        self.assertEqual(plan.total_rules, 2)
        self.assertTrue(plan.needs_ast_parsing)


class TestExecutionStats(unittest.TestCase):
    """测试 ExecutionStats"""

    def test_initial_state(self):
        """测试初始状态"""
        stats = ExecutionStats()
        self.assertEqual(stats.total_time_ms, 0.0)
        self.assertEqual(stats.ast_parse_time_ms, 0.0)
        self.assertEqual(stats.cache_hits, 0)
        self.assertEqual(stats.cache_misses, 0)
        self.assertEqual(stats.cache_hit_rate, 0.0)

    def test_add_rule_time(self):
        """测试添加规则执行时间"""
        stats = ExecutionStats()
        stats.add_rule_time("rule1", ExecutionMode.FAST, 10.5, 2)
        stats.add_rule_time("rule2", ExecutionMode.HYBRID, 25.0, 1)

        self.assertEqual(len(stats.rule_times), 2)
        self.assertEqual(stats.rule_times[0].rule_id, "rule1")
        self.assertEqual(stats.rule_times[0].elapsed_ms, 10.5)
        self.assertEqual(stats.rule_times[0].findings_count, 2)

    def test_cache_stats(self):
        """测试缓存统计"""
        stats = ExecutionStats()
        stats.record_cache_hit()
        stats.record_cache_hit()
        stats.record_cache_miss()

        self.assertEqual(stats.cache_hits, 2)
        self.assertEqual(stats.cache_misses, 1)
        self.assertEqual(stats.cache_hit_rate, 2 / 3)

    def test_get_slowest_rules(self):
        """测试获取最慢规则"""
        stats = ExecutionStats()
        stats.add_rule_time("fast", ExecutionMode.FAST, 5.0, 0)
        stats.add_rule_time("medium", ExecutionMode.HYBRID, 15.0, 0)
        stats.add_rule_time("slow", ExecutionMode.PRECISE, 50.0, 0)

        slowest = stats.get_slowest_rules(2)
        self.assertEqual(len(slowest), 2)
        self.assertEqual(slowest[0].rule_id, "slow")
        self.assertEqual(slowest[1].rule_id, "medium")

    def test_to_dict(self):
        """测试转换为字典"""
        stats = ExecutionStats()
        stats.total_time_ms = 100.0
        stats.ast_parse_time_ms = 30.0
        stats.record_cache_hit()
        stats.add_rule_time("rule1", ExecutionMode.FAST, 10.0, 1)

        d = stats.to_dict()
        self.assertEqual(d["total_time_ms"], 100.0)
        self.assertEqual(d["ast_parse_time_ms"], 30.0)
        self.assertEqual(d["cache_hits"], 1)
        self.assertEqual(d["rule_count"], 1)
        self.assertIn("slowest_rules", d)


if __name__ == "__main__":
    unittest.main()
