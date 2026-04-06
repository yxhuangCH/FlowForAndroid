"""Regression tests - prevent known issues from recurring"""

import pytest
import os
from unified_engine.context import UnifiedContext
from unified_engine.rules import get_all_rules
from unified_engine.engine import UnifiedExecutionEngine


class TestRegression:
    """Regression tests for known fixed issues"""

    KNOWN_ISSUES = [
        {
            "id": "REG-001",
            "description": "GlobalScope in comment should not be detected",
            "code": "// GlobalScope.launch is bad practice",
            "rule": "no_globalscope",
            "expected_findings": 0
        },
        {
            "id": "REG-002",
            "description": "GlobalScope in string literal should not be detected",
            'code': 'val msg = "Don\'t use GlobalScope"',
            "rule": "no_globalscope",
            "expected_findings": 0
        },
        {
            "id": "REG-003",
            "description": "Empty file should not crash any rule",
            "code": "",
            "rule": None,  # All rules
            "should_not_crash": True
        },
        {
            "id": "REG-004",
            "description": "Whitespace-only file should not crash any rule",
            "code": "   \n\n\t  ",
            "rule": None,
            "should_not_crash": True
        },
        {
            "id": "REG-005",
            "description": "Repository can use Dispatchers.IO",
            "code": '''
class Repository {
    suspend fun fetch() = withContext(Dispatchers.IO) { }
}
''',
            "rule": "viewmodel_context",
            "expected_findings": 0
        },
        {
            "id": "REG-006",
            "description": "flowOf doesn't need flowOn",
            "code": '''
class Test {
    fun numbers() = flowOf(1, 2, 3)
}
''',
            "rule": "missing_flowon",
            "expected_findings": 0
        },
    ]

    @pytest.mark.parametrize("issue", KNOWN_ISSUES)
    def test_known_issue_fixed(self, issue):
        """Test that known issues are still fixed"""
        context = UnifiedContext(issue["code"], "Test.kt")

        if issue.get("should_not_crash"):
            # Test that no rule crashes on this input
            for rule in get_all_rules():
                try:
                    findings = rule.check(context)
                    assert isinstance(findings, list)
                except Exception as e:
                    pytest.fail(
                        f"Regression: {issue['id']} - Rule {rule.metadata.id} crashed: {e}"
                    )
        else:
            # Test specific rule behavior
            rule = None
            for r in get_all_rules():
                if r.metadata.id == issue["rule"]:
                    rule = r
                    break

            if rule is None:
                pytest.skip(f"Rule {issue['rule']} not found")

            findings = rule.check(context)

            expected = issue.get("expected_findings", 0)
            actual = len(findings)

            assert actual == expected, (
                f"Regression: {issue['id']} - {issue['description']}\n"
                f"Expected {expected} findings, got {actual}\n"
                f"Findings: {[f.message for f in findings]}"
            )


class TestV3Compatibility:
    """Tests ensuring backward compatibility with v3 interfaces"""

    def test_engine_api_compatibility(self):
        """Test engine API matches expected interface"""
        engine = UnifiedExecutionEngine()

        # These methods should exist
        assert hasattr(engine, 'scan_file')
        assert hasattr(engine, 'scan_files')
        assert hasattr(engine, 'scan_code')
        assert hasattr(engine, 'get_changed_files')
        assert hasattr(engine, 'mark_scanned')
        assert hasattr(engine, 'get_performance_report')
        assert hasattr(engine, 'print_performance_report')
        assert hasattr(engine, 'reset_stats')
        assert hasattr(engine, 'cleanup')

    def test_scan_code_returns_result(self):
        """Test scan_code returns proper ScanResult"""
        engine = UnifiedExecutionEngine()
        result = engine.scan_code("class Test {}", "Test.kt")

        assert hasattr(result, 'findings')
        assert hasattr(result, 'execution_time')
        assert hasattr(result, 'files_scanned')
        assert hasattr(result, 'rules_executed')
        assert isinstance(result.findings, list)
        assert isinstance(result.execution_time, float)
        assert isinstance(result.files_scanned, int)
        assert isinstance(result.rules_executed, int)

    def test_scan_files_returns_dict(self):
        """Test scan_files returns dict of results"""
        engine = UnifiedExecutionEngine()
        results = engine.scan_codes({
            "a.kt": "class A {}",
            "b.kt": "class B {}"
        })

        assert isinstance(results, dict)
        assert len(results) == 2

    def test_old_environment_variable_ignored(self):
        """Test old environment variable doesn't break new engine"""
        original = os.environ.get("USE_AST_ENGINE")

        try:
            os.environ["USE_AST_ENGINE"] = "true"

            engine = UnifiedExecutionEngine()
            result = engine.scan_code("class Test {}", "Test.kt")

            assert result is not None
            assert result.files_scanned == 1
        finally:
            if original is not None:
                os.environ["USE_AST_ENGINE"] = original
            elif "USE_AST_ENGINE" in os.environ:
                del os.environ["USE_AST_ENGINE"]

    def test_get_all_rules_returns_list(self):
        """Test get_all_rules returns proper list"""
        from unified_engine.rules import get_all_rules

        rules = get_all_rules()

        assert isinstance(rules, list)
        assert len(rules) > 0

        for rule in rules:
            assert hasattr(rule, 'metadata')
            assert hasattr(rule, 'check')
            assert hasattr(rule, 'execution_mode')


class TestInterfaceStability:
    """Tests ensuring public interfaces remain stable"""

    def test_unified_rule_interface(self):
        """Test UnifiedRule interface stability"""
        from unified_engine.interfaces import UnifiedRule

        required_attrs = ['metadata', 'execution_mode', 'check']
        optional_methods = ['on_register', 'on_unregister', 'get_score_deduction']

        for attr in required_attrs:
            assert hasattr(UnifiedRule, attr), f"UnifiedRule missing {attr}"

        for method in optional_methods:
            assert hasattr(UnifiedRule, method), f"UnifiedRule missing {method}"

    def test_execution_mode_values(self):
        """Test ExecutionMode enum values are stable"""
        from unified_engine.interfaces import ExecutionMode

        assert ExecutionMode.FAST.value == "fast"
        assert ExecutionMode.HYBRID.value == "hybrid"
        assert ExecutionMode.PRECISE.value == "precise"

    def test_execution_plan_structure(self):
        """Test ExecutionPlan structure is stable"""
        from unified_engine.interfaces import ExecutionPlan

        plan = ExecutionPlan()

        assert hasattr(plan, 'fast_rules')
        assert hasattr(plan, 'hybrid_rules')
        assert hasattr(plan, 'precise_rules')
        assert hasattr(plan, 'strategy')
        assert hasattr(plan, 'total_rules')
        assert hasattr(plan, 'needs_ast_parsing')

    def test_execution_stats_structure(self):
        """Test ExecutionStats structure is stable"""
        from unified_engine.interfaces import ExecutionStats

        stats = ExecutionStats()

        assert hasattr(stats, 'add_rule_time')
        assert hasattr(stats, 'record_ast_parse_time')
        assert hasattr(stats, 'record_cache_hit')
        assert hasattr(stats, 'record_cache_miss')
        assert hasattr(stats, 'rule_count')
        assert hasattr(stats, 'cache_hit_rate')
        assert hasattr(stats, 'to_dict')

    def test_unified_context_interface(self):
        """Test UnifiedContext interface stability"""
        from unified_engine.context import UnifiedContext

        ctx = UnifiedContext("class Test {}", "Test.kt")

        assert hasattr(ctx, 'code')
        assert hasattr(ctx, 'file_path')
        assert hasattr(ctx, 'find_pattern')
        assert hasattr(ctx, 'find_pattern_with_lines')
        assert hasattr(ctx, 'ast_available')
        assert hasattr(ctx, 'ast')


class TestDataIntegrity:
    """Tests ensuring data integrity across operations"""

    def test_finding_data_integrity(self):
        """Test Finding objects have required fields"""
        from rule_engine.interfaces import Finding, RuleSeverity, RuleCategory

        finding = Finding(
            rule_id="test_rule",
            message="Test message",
            severity=RuleSeverity.INFO,
            category=RuleCategory.CODE_STYLE,
            line=1,
            column=1,
            file_path="Test.kt"
        )

        assert finding.rule_id == "test_rule"
        assert finding.message == "Test message"
        assert finding.severity == RuleSeverity.INFO
        assert finding.category == RuleCategory.CODE_STYLE
        assert finding.line == 1
        assert finding.file_path == "Test.kt"

    def test_rule_metadata_integrity(self):
        """Test RuleMetadata has required fields"""
        from rule_engine.interfaces import RuleMetadata, RuleSeverity, RuleCategory

        metadata = RuleMetadata(
            id="test_id",
            name="Test Name",
            description="Test description",
            severity=RuleSeverity.MAJOR,
            category=RuleCategory.BEST_PRACTICE
        )

        assert metadata.id == "test_id"
        assert metadata.name == "Test Name"
        assert metadata.description == "Test description"
        assert metadata.severity == RuleSeverity.MAJOR
        assert metadata.category == RuleCategory.BEST_PRACTICE

    def test_cache_key_consistency(self, tmp_path):
        """Test cache keys are consistent across operations"""
        from unified_engine.cache import UnifiedCache

        cache = UnifiedCache(disk_cache_dir=str(tmp_path / "cache"))

        code = "class Test {}"

        # Put and get with same key
        cache.put("key1", {"data": "value"})
        result = cache.get("key1")

        assert result == {"data": "value"}

        # Different key should not return same value
        assert cache.get("key2") is None
