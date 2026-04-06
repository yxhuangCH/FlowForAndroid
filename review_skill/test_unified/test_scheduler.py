"""Tests for RuleScheduler"""

import pytest
import time
from unified_engine.scheduler import RuleScheduler
from unified_engine.interfaces import ExecutionMode
from unified_engine.strategy import ExecutionStrategy


class TestRuleScheduler:
    """Tests for rule scheduler"""

    def test_create_execution_plan(self, scheduler, sample_rules):
        """Test execution plan creation"""
        plan = scheduler.create_execution_plan(
            file_size=5000,
            line_count=100
        )

        assert plan.total_rules == len(sample_rules)
        assert len(plan.fast_rules) > 0
        assert len(plan.hybrid_rules) > 0

    def test_rule_classification(self, scheduler, fast_rules, hybrid_rules, precise_rules):
        """Test rules are classified by execution mode"""
        plan = scheduler.create_execution_plan()

        for rule in plan.fast_rules:
            assert rule.execution_mode == ExecutionMode.FAST
        for rule in plan.hybrid_rules:
            assert rule.execution_mode == ExecutionMode.HYBRID
        for rule in plan.precise_rules:
            assert rule.execution_mode == ExecutionMode.PRECISE

    def test_adaptive_strategy_small_file(self, scheduler):
        """Test small file uses standard strategy"""
        plan = scheduler.create_execution_plan(
            file_size=5_000,
            line_count=100
        )
        assert plan.strategy == ExecutionStrategy.STANDARD

    def test_adaptive_strategy_medium_file(self, scheduler):
        """Test medium file uses optimized strategy"""
        plan = scheduler.create_execution_plan(
            file_size=50_000,
            line_count=500
        )
        assert plan.strategy == ExecutionStrategy.OPTIMIZED

    def test_adaptive_strategy_large_file(self, scheduler):
        """Test large file uses reduced strategy"""
        plan = scheduler.create_execution_plan(
            file_size=300_000,
            line_count=3000
        )
        assert plan.strategy == ExecutionStrategy.REDUCED

    def test_adaptive_strategy_very_large_file(self, scheduler):
        """Test very large file uses minimal strategy"""
        plan = scheduler.create_execution_plan(
            file_size=600_000,
            line_count=5000
        )
        assert plan.strategy == ExecutionStrategy.MINIMAL

    def test_large_file_rule_reduction(self, scheduler, sample_rules):
        """Test large files have reduced rule count"""
        small_plan = scheduler.create_execution_plan(
            file_size=5_000,
            line_count=100
        )
        large_plan = scheduler.create_execution_plan(
            file_size=600_000,
            line_count=5000
        )

        assert large_plan.total_rules < small_plan.total_rules

    def test_rules_sorted_by_severity(self, scheduler):
        """Test rules are sorted by severity"""
        plan = scheduler.create_execution_plan()

        severity_order = {
            "blocker": 0,
            "critical": 1,
            "major": 2,
            "minor": 3,
            "info": 4,
        }

        for rules_list in [plan.fast_rules, plan.hybrid_rules, plan.precise_rules]:
            severities = [severity_order.get(r.metadata.severity.value, 5) for r in rules_list]
            assert severities == sorted(severities)

    def test_needs_ast_parsing(self, scheduler):
        """Test plan correctly indicates AST parsing needs"""
        # Plan with only FAST rules
        class MockRule:
            execution_mode = ExecutionMode.FAST

        # Create plan and check needs_ast_parsing
        plan = scheduler.create_execution_plan()

        # Should need AST if there are hybrid or precise rules
        expected = len(plan.hybrid_rules) > 0 or len(plan.precise_rules) > 0
        assert plan.needs_ast_parsing == expected

    def test_execute_single_rule(self, scheduler, sample_context):
        """Test executing a single rule"""
        from unified_engine.rules import NoGlobalScopeRule

        rule = NoGlobalScopeRule()
        findings, elapsed_ms = scheduler.execute_single("no_globalscope", sample_context)

        assert isinstance(findings, list)
        assert elapsed_ms >= 0

    def test_execute_single_rule_not_found(self, scheduler, sample_context):
        """Test executing non-existent rule raises error"""
        with pytest.raises(ValueError, match="Rule 'nonexistent' not found"):
            scheduler.execute_single("nonexistent", sample_context)

    def test_warmup(self, scheduler):
        """Test warmup functionality"""
        from unified_engine.context import UnifiedContext

        contexts = [
            UnifiedContext("class Test {}", "Test1.kt"),
            UnifiedContext("class Test {}", "Test2.kt"),
        ]

        # Should not raise exception
        scheduler.warmup(contexts)

    def test_shutdown(self, scheduler):
        """Test shutdown releases resources"""
        scheduler.shutdown()

    def test_context_manager(self):
        """Test scheduler as context manager"""
        with RuleScheduler() as scheduler:
            assert scheduler is not None

    def test_performance_report(self, scheduler, sample_context):
        """Test performance report generation"""
        plan = scheduler.create_execution_plan()
        scheduler.execute(sample_context, plan)

        report = scheduler.get_performance_report()

        assert "summary" in report
        assert "slow_rules" in report

    def test_monitor_integration(self, scheduler):
        """Test monitor is created when enabled"""
        assert scheduler.monitor is not None

    def test_adaptive_strategy_integration(self, scheduler):
        """Test adaptive strategy is created when enabled"""
        assert scheduler.adaptive_strategy is not None
