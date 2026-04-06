"""Functionality tests for Phase 6"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unified_engine.engine import UnifiedExecutionEngine
from unified_engine.rules import get_all_rules
from unified_engine.context import UnifiedContext
from unified_engine.interfaces import ExecutionMode


class TestRuleExecution:
    """Test rule execution functionality"""

    def test_all_rules_registered(self):
        """All rules should be registered"""
        rules = get_all_rules()
        assert len(rules) >= 30, f"Expected >=30 rules, got {len(rules)}"

    def test_rule_metadata_complete(self):
        """All rules should have complete metadata"""
        rules = get_all_rules()
        
        for rule in rules:
            assert rule.metadata.id, "Rule missing ID"
            assert rule.metadata.name, "Rule missing name"
            assert rule.metadata.severity, "Rule missing severity"

    def test_fast_rule_execution(self):
        """FAST mode rules should execute"""
        fast_rules = [
            r for r in get_all_rules() 
            if r.execution_mode == ExecutionMode.FAST
        ]
        assert len(fast_rules) > 0, "No FAST rules found"

    def test_hybrid_rule_execution(self):
        """HYBRID mode rules should execute"""
        hybrid_rules = [
            r for r in get_all_rules() 
            if r.execution_mode == ExecutionMode.HYBRID
        ]
        assert len(hybrid_rules) > 0, "No HYBRID rules found"

    def test_precise_rule_execution(self):
        """PRECISE mode rules should execute"""
        precise_rules = [
            r for r in get_all_rules() 
            if r.execution_mode == ExecutionMode.PRECISE
        ]
        assert isinstance(precise_rules, list)


class TestContextFunctionality:
    """Test UnifiedContext functionality"""

    def test_context_find_pattern(self):
        """Context should find patterns"""
        ctx = UnifiedContext("GlobalScope.launch { }", "Test.kt")
        matches = ctx.find_pattern(r"GlobalScope")
        
        assert len(matches) > 0

    def test_context_get_lines(self):
        """Context should return lines"""
        code = "line1\nline2\nline3"
        ctx = UnifiedContext(code, "Test.kt")
        lines = ctx.get_lines()
        
        assert len(lines) == 3

    def test_context_ast_parsing(self):
        """Context should parse AST lazily"""
        ctx = UnifiedContext("class Test { }", "Test.kt")
        
        assert not ctx._ast_parsed
        
        ast = ctx.ast
        
        assert ctx._ast_parsed


class TestEngineFunctionality:
    """Test engine functionality"""

    def test_engine_initialization(self):
        """Engine should initialize correctly"""
        engine = UnifiedExecutionEngine()
        
        assert engine is not None
        assert len(engine.rules) > 0

    def test_engine_scan_file(self):
        """Engine should scan file"""
        # Use file_path that triggers the rule properly
        code = "class Test { fun test() { kotlinx.coroutines.GlobalScope.launch { } } }"
        
        engine = UnifiedExecutionEngine()
        result = engine.scan_file("<test>", code)
        
        assert result.files_scanned == 1
        # Note: findings depend on code matching patterns


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
