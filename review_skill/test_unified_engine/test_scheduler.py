"""Tests for unified_engine/scheduler.py"""

import unittest
from typing import List

from unified_engine import (
    RuleScheduler,
    UnifiedRegistry,
    UnifiedRule,
    ExecutionMode,
    RuleMetadata,
    Finding,
    RuleSeverity,
    RuleCategory,
)
from unified_engine.context import UnifiedContext


class SimpleRule(UnifiedRule):
    """简单测试规则"""

    execution_mode = ExecutionMode.FAST

    def __init__(self, rule_id: str, pattern: str = "test"):
        self._id = rule_id
        self._pattern = pattern
        self.call_count = 0

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id=self._id,
            name=f"Rule {self._id}",
            description="A test rule",
            severity=RuleSeverity.MAJOR,
            category=RuleCategory.BEST_PRACTICE,
        )

    def check(self, context: UnifiedContext) -> List[Finding]:
        self.call_count += 1
        findings = []
        if context.contains_pattern(self._pattern):
            findings.append(
                Finding(
                    rule_id=self._id,
                    message=f"Found {self._pattern}",
                    severity=self.metadata.severity,
                )
            )
        return findings


class HybridTestRule(UnifiedRule):
    """混合模式测试规则"""

    execution_mode = ExecutionMode.HYBRID

    def __init__(self, rule_id: str):
        self._id = rule_id
        self.call_count = 0

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id=self._id,
            name=f"Hybrid Rule {self._id}",
            description="A hybrid test rule",
            severity=RuleSeverity.MAJOR,
            category=RuleCategory.PERFORMANCE,
        )

    def check(self, context: UnifiedContext) -> List[Finding]:
        self.call_count += 1
        # 使用正则筛选
        if not context.contains_pattern("GlobalScope"):
            return []
        # 使用 AST 验证
        if context.ast_available:
            return [
                Finding(
                    rule_id=self._id,
                    message="Found with AST",
                    severity=self.metadata.severity,
                )
            ]
        return []


class PreciseTestRule(UnifiedRule):
    """精确模式测试规则"""

    execution_mode = ExecutionMode.PRECISE

    def __init__(self, rule_id: str):
        self._id = rule_id
        self.call_count = 0

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id=self._id,
            name=f"Precise Rule {self._id}",
            description="A precise test rule",
            severity=RuleSeverity.CRITICAL,
            category=RuleCategory.SECURITY,
        )

    def check(self, context: UnifiedContext) -> List[Finding]:
        self.call_count += 1
        # 必须使用 AST
        if context.ast_available:
            nodes = context.find_nodes_by_type(
                None
            )  # 使用 query_ast 需要正确的节点类型
            return [
                Finding(
                    rule_id=self._id,
                    message=f"Found {len(nodes)} nodes",
                    severity=self.metadata.severity,
                )
            ]
        return []


class TestRuleScheduler(unittest.TestCase):
    """测试 RuleScheduler"""

    def setUp(self):
        """设置测试环境"""
        self.registry = UnifiedRegistry()
        self.registry.clear()

    def tearDown(self):
        """清理"""
        self.registry.clear()

    def test_create_execution_plan(self):
        """测试创建执行计划"""
        self.registry.register(SimpleRule("fast1"))
        self.registry.register(HybridTestRule("hybrid1"))
        self.registry.register(PreciseTestRule("precise1"))

        scheduler = RuleScheduler(self.registry)
        plan = scheduler.create_execution_plan()

        self.assertEqual(plan.total_rules, 3)
        self.assertEqual(len(plan.fast_rules), 1)
        self.assertEqual(len(plan.hybrid_rules), 1)
        self.assertEqual(len(plan.precise_rules), 1)
        self.assertTrue(plan.needs_ast_parsing)

    def test_execution_plan_sorting(self):
        """测试执行计划按严重程度排序"""

        class MinorRule(UnifiedRule):
            execution_mode = ExecutionMode.FAST

            @property
            def metadata(self) -> RuleMetadata:
                return RuleMetadata(
                    id="minor_rule",
                    name="Minor Rule",
                    description="Minor",
                    severity=RuleSeverity.MINOR,
                    category=RuleCategory.STYLE,
                )

            def check(self, context: UnifiedContext) -> List[Finding]:
                return []

        class CriticalRule(UnifiedRule):
            execution_mode = ExecutionMode.FAST

            @property
            def metadata(self) -> RuleMetadata:
                return RuleMetadata(
                    id="critical_rule",
                    name="Critical Rule",
                    description="Critical",
                    severity=RuleSeverity.CRITICAL,
                    category=RuleCategory.SECURITY,
                )

            def check(self, context: UnifiedContext) -> List[Finding]:
                return []

        self.registry.register(MinorRule())
        self.registry.register(CriticalRule())

        scheduler = RuleScheduler(self.registry)
        plan = scheduler.create_execution_plan()

        # 严重程度高的应该排在前面
        self.assertEqual(plan.fast_rules[0].metadata.id, "critical_rule")
        self.assertEqual(plan.fast_rules[1].metadata.id, "minor_rule")

    def test_execute_single_rule(self):
        """测试执行单条规则"""
        rule = SimpleRule("test_rule", pattern="GlobalScope")
        self.registry.register(rule)

        scheduler = RuleScheduler(self.registry)
        context = UnifiedContext(
            code="GlobalScope.launch { }",
            file_path="/test/Test.kt",
        )

        findings, elapsed_ms = scheduler.execute_single("test_rule", context)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].rule_id, "test_rule")
        self.assertGreater(elapsed_ms, 0)
        self.assertEqual(rule.call_count, 1)

    def test_execute_single_nonexistent_rule(self):
        """测试执行不存在的规则"""
        scheduler = RuleScheduler(self.registry)
        context = UnifiedContext(code="", file_path="/test/Test.kt")

        with self.assertRaises(ValueError) as ctx:
            scheduler.execute_single("nonexistent", context)
        self.assertIn("nonexistent", str(ctx.exception))

    def test_execute_all_rules(self):
        """测试执行所有规则"""
        rule1 = SimpleRule("rule1", pattern="test")
        rule2 = SimpleRule("rule2", pattern="other")
        self.registry.register(rule1)
        self.registry.register(rule2)

        scheduler = RuleScheduler(self.registry, enable_parallel=False)
        context = UnifiedContext(
            code="test function",
            file_path="/test/Test.kt",
        )

        findings, stats = scheduler.execute(context)

        self.assertEqual(len(findings), 1)  # 只有 rule1 匹配
        self.assertEqual(findings[0].rule_id, "rule1")
        self.assertEqual(rule1.call_count, 1)
        self.assertEqual(rule2.call_count, 1)  # rule2 也被执行了，但没有发现
        self.assertEqual(len(stats.rule_times), 2)
        self.assertGreater(stats.total_time_ms, 0)

    def test_execute_with_plan(self):
        """测试使用指定执行计划"""
        rule1 = SimpleRule("rule1")
        rule2 = SimpleRule("rule2")
        self.registry.register(rule1)
        self.registry.register(rule2)

        scheduler = RuleScheduler(self.registry)
        context = UnifiedContext(code="", file_path="/test/Test.kt")

        # 创建只包含 rule1 的计划
        from unified_engine.interfaces import ExecutionPlan

        plan = ExecutionPlan(fast_rules=[rule1])

        findings, stats = scheduler.execute(context, plan)

        self.assertEqual(rule1.call_count, 1)
        self.assertEqual(rule2.call_count, 0)  # rule2 不在计划中

    def test_execution_stats(self):
        """测试执行统计"""
        self.registry.register(SimpleRule("rule1"))
        self.registry.register(SimpleRule("rule2"))

        scheduler = RuleScheduler(self.registry, enable_parallel=False)
        context = UnifiedContext(
            code="test",
            file_path="/test/Test.kt",
        )

        findings, stats = scheduler.execute(context)

        self.assertEqual(stats.rule_count, 2)
        self.assertGreater(stats.total_time_ms, 0)
        self.assertEqual(len(stats.get_slowest_rules(5)), 2)

    def test_parallel_execution(self):
        """测试并行执行"""
        # 创建多个规则
        for i in range(5):
            self.registry.register(SimpleRule(f"rule{i}"))

        scheduler = RuleScheduler(self.registry, enable_parallel=True, max_workers=3)
        context = UnifiedContext(
            code="test content",
            file_path="/test/Test.kt",
        )

        findings, stats = scheduler.execute(context)

        self.assertEqual(len(stats.rule_times), 5)

    def test_progress_callback(self):
        """测试进度回调"""
        self.registry.register(SimpleRule("rule1"))
        self.registry.register(SimpleRule("rule2"))

        progress_calls = []

        def progress_callback(current, total, rule_id):
            progress_calls.append((current, total, rule_id))

        scheduler = RuleScheduler(self.registry, enable_parallel=False)
        context = UnifiedContext(code="test", file_path="/test/Test.kt")

        scheduler.execute(context, progress_callback=progress_callback)

        # 应该有进度回调调用
        self.assertGreater(len(progress_calls), 0)

    def test_warmup(self):
        """测试预热功能"""
        self.registry.register(HybridTestRule("hybrid1"))

        scheduler = RuleScheduler(self.registry)
        contexts = [
            UnifiedContext(code="GlobalScope.launch {}", file_path=f"/test/{i}.kt")
            for i in range(3)
        ]

        scheduler.warmup(contexts)

        # 预热后，所有上下文的 AST 应该已经被解析
        for context in contexts:
            self.assertTrue(context.ast_available)

    def test_rule_filter(self):
        """测试规则过滤"""
        self.registry.register(SimpleRule("rule1"))
        self.registry.register(SimpleRule("rule2"))

        scheduler = RuleScheduler(self.registry)
        plan = scheduler.create_execution_plan(
            rule_filter=lambda r: r.metadata.id == "rule1"
        )

        self.assertEqual(plan.total_rules, 1)
        self.assertEqual(plan.fast_rules[0].metadata.id, "rule1")

    def test_sequential_vs_parallel(self):
        """测试顺序和并行执行结果一致"""
        self.registry.register(SimpleRule("rule1", pattern="test"))
        self.registry.register(SimpleRule("rule2", pattern="other"))

        context = UnifiedContext(
            code="test other",
            file_path="/test/Test.kt",
        )

        # 顺序执行
        scheduler1 = RuleScheduler(self.registry, enable_parallel=False)
        findings1, _ = scheduler1.execute(context)

        # 并行执行
        scheduler2 = RuleScheduler(self.registry, enable_parallel=True)
        findings2, _ = scheduler2.execute(context)

        # 结果应该相同（不考虑顺序）
        self.assertEqual(len(findings1), len(findings2))


if __name__ == "__main__":
    unittest.main()
