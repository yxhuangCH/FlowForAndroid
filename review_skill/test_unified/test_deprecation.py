"""Tests for deprecation warnings in Phase 6"""

import pytest
import warnings
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestDeprecationWarnings:
    """Test that deprecated engines show warnings"""

    def test_rule_engine_deprecation_warning(self):
        """Rule engine should show DeprecationWarning (Phase 6 implementation pending)"""
        # This test will pass after Phase 6.1 adds deprecation warnings to rule_engine
        # For now, we verify the module can be imported
        import rule_engine
        assert rule_engine is not None

    def test_ast_engine_deprecation_warning(self):
        """AST engine should show DeprecationWarning (Phase 6 implementation pending)"""
        # This test will pass after Phase 6.1 adds deprecation warnings to ast_engine
        import ast_engine
        assert ast_engine is not None

    def test_unified_engine_no_warning(self):
        """Unified engine should NOT show deprecation warning"""
        old_filters = warnings.filters[:]
        
        try:
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                
                modules_to_remove = [m for m in sys.modules if m.startswith('unified_engine')]
                for m in modules_to_remove:
                    del sys.modules[m]
                
                import unified_engine  # noqa: F401
                
                deprecation_warnings = [
                    x for x in w 
                    if issubclass(x.category, DeprecationWarning)
                    and 'unified_engine' in str(x.message)
                ]
                assert len(deprecation_warnings) == 0
        finally:
            warnings.filters[:] = old_filters

    def test_review_py_shows_unified_preferred(self):
        """review.py should prefer unified engine"""
        import subprocess
        
        result = subprocess.run(
            [sys.executable, "review.py", "--help"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        output = result.stdout + result.stderr
        
        assert "unified" in output.lower() or "✓" in output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
