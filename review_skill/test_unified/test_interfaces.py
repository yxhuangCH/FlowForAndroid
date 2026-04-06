"""Tests for unified engine interfaces"""

import pytest
from unified_engine.interfaces import (
    ExecutionMode,
    ExecutionPlan,
    ExecutionStats,
    RuleExecutionTime,
    UnifiedRule,
)
from rule_engine.interfaces import RuleMetadata, RuleSeverity, RuleCategory


class TestExecutionMode:
    """Tests for ExecutionMode enum"""

    def test_execution_mode_values(self):
        """Test execution mode enum values"""
        assert ExecutionMode.FAST.value == "fast"
        assert ExecutionMode.PRECISE.value == "precise"
        assert ExecutionMode.HYBRID.value == "hybrid"


class TestExecutionPlan:
    """Tests for ExecutionPlan dataclass"""

    def test_empty_plan(self):
        """Test empty execution plan"""
        plan = ExecutionPlan()

        assert plan.total_rules == 0
        assert plan.needs_ast_parsing is False
        assert plan.fast_rules == []
        assert plan.hybrid_rules == []
        assert plan.precise_rules == []

    def test_plan_with_rules(self, sample_rules):
        """Test execution plan with rules"""
        fast_rules = [r for r in sample_rules if r.execution_mode.value == "fast"]
        hybrid_rules = [r for r in sample_rules if r.execution_mode.value == "hybrid"]

        plan = ExecutionPlan(
            fast_rules=fast_rules,
            hybrid_rules=hybrid_rules,
            precise_rules=[]
        )

        assert plan.total_rules == len(fast_rules) + len(hybrid_rules)
        assert plan.needs_ast_parsing is True  # Hybrid rules need AST

    def test_needs_ast_parsing_with_only_fast(self):
        """Test plan with only fast rules doesn't need AST"""
        plan = ExecutionPlan(
            fast_rules=[],
            hybrid_rules=[],
            precise_rules=[]
        )

        assert plan.needs_ast_parsing is False


class TestExecutionStats:
    """Tests for ExecutionStats dataclass"""

    def test_empty_stats(self):
        """Test empty execution stats"""
        stats = ExecutionStats()

        assert stats.total_time_ms == 0.0
        assert stats.ast_parse_time_ms == 0.0
        assert stats.cache_hits == 0
        assert stats.cache_misses == 0
        assert stats.rule_count == 0

    def test_add_rule_time(self):
        """Test adding rule execution time"""
        stats = ExecutionStats()

        stats.add_rule_time("rule1", ExecutionMode.FAST, 10.0, findings_count=2)

        assert stats.rule_count == 1
        assert len(stats.rule_times) == 1
        assert stats.rule_times[0].rule_id == "rule1"
        assert stats.rule_times[0].elapsed_ms == 10.0
        assert stats.rule_times[0].findings_count == 2

    def test_cache_hit_rate(self):
        """Test cache hit rate calculation"""
        stats = ExecutionStats()

        assert stats.cache_hit_rate == 0.0  # No requests yet

        stats.record_cache_hit()
        stats.record_cache_miss()

        assert stats.cache_hit_rate == 0.5

    def test_get_slowest_rules(self):
        """Test getting slowest rules"""
        stats = ExecutionStats()

        stats.add_rule_time("fast_rule", ExecutionMode.FAST, 5.0, 0)
        stats.add_rule_time("slow_rule", ExecutionMode.PRECISE, 50.0, 1)
        stats.add_rule_time("medium_rule", ExecutionMode.HYBRID, 20.0, 2)

        slowest = stats.get_slowest_rules(n=2)

        assert len(slowest) == 2
        assert slowest[0].rule_id == "slow_rule"
        assert slowest[1].rule_id == "medium_rule"

    def test_to_dict(self):
        """Test converting stats to dict"""
        stats = ExecutionStats()
        stats.total_time_ms = 100.0
        stats.ast_parse_time_ms = 50.0
        stats.record_cache_hit()
        stats.add_rule_time("rule1", ExecutionMode.FAST, 10.0, 1)

        data = stats.to_dict()

        assert data["total_time_ms"] == 100.0
        assert data["cache_hits"] == 1
        assert "slowest_rules" in data


class TestRuleExecutionTime:
    """Tests for RuleExecutionTime dataclass"""

    def test_creation(self):
        """Test creating execution time record"""
        record = RuleExecutionTime(
            rule_id="test_rule",
            execution_mode=ExecutionMode.FAST,
            elapsed_ms=10.5,
            findings_count=2
        )

        assert record.rule_id == "test_rule"
        assert record.execution_mode == ExecutionMode.FAST
        assert record.elapsed_ms == 10.5
        assert record.findings_count == 2


class TestUnifiedRule:
    """Tests for UnifiedRule base class"""

    def test_default_execution_mode(self):
        """Test default execution mode is HYBRID"""
        class TestRule(UnifiedRule):
            @property
            def metadata(self):
                return RuleMetadata(
                    id="test",
                    name="Test Rule",
                    description="Test",
                    severity=RuleSeverity.INFO,
                    category=RuleCategory.STYLE
                )

            def check(self, context):
                return []

        rule = TestRule()
        assert rule.execution_mode == ExecutionMode.HYBRID

    def test_custom_execution_mode(self):
        """Test custom execution mode"""
        class FastRule(UnifiedRule):
            execution_mode = ExecutionMode.FAST

            @property
            def metadata(self):
                return RuleMetadata(
                    id="test",
                    name="Test Rule",
                    description="Test",
                    severity=RuleSeverity.INFO,
                    category=RuleCategory.STYLE
                )

            def check(self, context):
                return []

        rule = FastRule()
        assert rule.execution_mode == ExecutionMode.FAST

    def test_get_score_deduction(self):
        """Test score deduction calculation"""
        class TestRule(UnifiedRule):
            @property
            def metadata(self):
                return RuleMetadata(
                    id="test",
                    name="Test Rule",
                    description="Test",
                    severity=RuleSeverity.CRITICAL,
                    category=RuleCategory.STYLE
                )

            def check(self, context):
                return []

        rule = TestRule()

        # CRITICAL should deduct 20 points
        assert rule.get_score_deduction(RuleSeverity.CRITICAL) == 20

        # BLOCKER should deduct 100 points
        assert rule.get_score_deduction(RuleSeverity.BLOCKER) == 100

    def test_custom_score_deduction_range(self):
        """Test custom score deduction range"""
        class TestRule(UnifiedRule):
            @property
            def metadata(self):
                return RuleMetadata(
                    id="test",
                    name="Test Rule",
                    description="Test",
                    severity=RuleSeverity.MAJOR,
                    category=RuleCategory.STYLE,
                    min_score_deduction=5,
                    max_score_deduction=15
                )

            def check(self, context):
                return []

        rule = TestRule()

        # Should be clamped to custom range
        assert rule.get_score_deduction(RuleSeverity.BLOCKER) == 15
        assert rule.get_score_deduction(RuleSeverity.INFO) == 5

    def test_on_register_unregister(self):
        """Test register/unregister callbacks"""
        class TestRule(UnifiedRule):
            registered = False
            unregistered = False

            @property
            def metadata(self):
                return RuleMetadata(
                    id="test",
                    name="Test Rule",
                    description="Test",
                    severity=RuleSeverity.INFO,
                    category=RuleCategory.STYLE
                )

            def check(self, context):
                return []

            def on_register(self):
                self.registered = True

            def on_unregister(self):
                self.unregistered = True

        rule = TestRule()

        rule.on_register()
        assert rule.registered is True

        rule.on_unregister()
        assert rule.unregistered is True

    def test_repr(self):
        """Test rule string representation"""
        class TestRule(UnifiedRule):
            execution_mode = ExecutionMode.FAST

            @property
            def metadata(self):
                return RuleMetadata(
                    id="test_rule",
                    name="Test Rule",
                    description="Test",
                    severity=RuleSeverity.INFO,
                    category=RuleCategory.STYLE
                )

            def check(self, context):
                return []

        rule = TestRule()
        repr_str = repr(rule)

        assert "UnifiedRule" in repr_str
        assert "test_rule" in repr_str
        assert "fast" in repr_str
