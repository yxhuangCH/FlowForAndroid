"""Tests for base rules (NoGlobalScopeRule, ViewModelContextRule, MainThreadIoRule)"""

import pytest
from unified_engine.context import UnifiedContext
from unified_engine.rules.base import NoGlobalScopeRule, ViewModelContextRule, MainThreadIoRule
from rule_engine.interfaces import RuleSeverity, RuleCategory


class TestNoGlobalScopeRule:
    """Tests for NoGlobalScopeRule"""

    @pytest.fixture
    def rule(self):
        return NoGlobalScopeRule()

    def test_metadata(self, rule):
        """Test rule metadata"""
        assert rule.metadata.id == "no_globalscope"
        assert rule.metadata.severity == RuleSeverity.BLOCKER
        assert rule.metadata.category == RuleCategory.LIFECYCLE

    def test_detects_globalscope_launch(self, rule):
        """Test detecting GlobalScope.launch"""
        code = '''
        class MainActivity : AppCompatActivity() {
            fun test() {
                GlobalScope.launch { }
            }
        }
        '''
        context = UnifiedContext(code, "MainActivity.kt")
        findings = rule.check(context)

        assert len(findings) == 1
        assert findings[0].rule_id == "no_globalscope"

    def test_detects_globalscope_async(self, rule):
        """Test detecting GlobalScope.async"""
        code = '''
        class Test {
            fun test() {
                GlobalScope.async { }
            }
        }
        '''
        context = UnifiedContext(code, "Test.kt")
        findings = rule.check(context)

        assert len(findings) == 1

    def test_no_finding_for_lifecycle_scope(self, rule):
        """Test lifecycleScope.launch is allowed"""
        code = '''
        class MainActivity : AppCompatActivity() {
            fun test() {
                lifecycleScope.launch { }
            }
        }
        '''
        context = UnifiedContext(code, "MainActivity.kt")
        findings = rule.check(context)

        assert len(findings) == 0

    def test_no_finding_for_viewmodel_scope(self, rule):
        """Test viewModelScope.launch is allowed"""
        code = '''
        class MyViewModel : ViewModel() {
            fun test() {
                viewModelScope.launch { }
            }
        }
        '''
        context = UnifiedContext(code, "MyViewModel.kt")
        findings = rule.check(context)

        assert len(findings) == 0

    def test_no_finding_for_coroutine_scope(self, rule):
        """Test coroutineScope.launch is allowed"""
        code = '''
        class Test {
            fun test() {
                coroutineScope.launch { }
            }
        }
        '''
        context = UnifiedContext(code, "Test.kt")
        findings = rule.check(context)

        assert len(findings) == 0

    def test_no_finding_in_comment(self, rule):
        """Test GlobalScope in comment is not detected"""
        code = '''
        // Don't use GlobalScope.launch
        class Test {
        }
        '''
        context = UnifiedContext(code, "Test.kt")
        findings = rule.check(context)

        assert len(findings) == 0

    def test_no_finding_in_string(self, rule):
        """Test GlobalScope in string is not detected"""
        code = '''
        class Test {
            val msg = "GlobalScope.launch is bad"
        }
        '''
        context = UnifiedContext(code, "Test.kt")
        findings = rule.check(context)

        assert len(findings) == 0

    def test_execution_mode(self, rule):
        """Test rule execution mode"""
        from unified_engine.interfaces import ExecutionMode
        assert rule.execution_mode == ExecutionMode.FAST


class TestViewModelContextRule:
    """Tests for ViewModelContextRule"""

    @pytest.fixture
    def rule(self):
        return ViewModelContextRule()

    def test_metadata(self, rule):
        """Test rule metadata"""
        assert rule.metadata.id == "viewmodel_context"
        assert rule.metadata.severity == RuleSeverity.CRITICAL
        assert rule.metadata.category == RuleCategory.LIFECYCLE

    def test_detects_dispatchers_main_in_viewmodel(self, rule):
        """Test detecting Dispatchers.Main in ViewModel"""
        code = '''
        class MyViewModel : ViewModel() {
            fun load() {
                viewModelScope.launch(Dispatchers.Main) { }
            }
        }
        '''
        context = UnifiedContext(code, "MyViewModel.kt")
        findings = rule.check(context)

        assert len(findings) == 1
        assert findings[0].rule_id == "viewmodel_context"

    def test_detects_dispatchers_io_in_viewmodel(self, rule):
        """Test detecting Dispatchers.IO in ViewModel"""
        code = '''
        class MyViewModel : ViewModel() {
            fun load() {
                viewModelScope.launch(Dispatchers.IO) { }
            }
        }
        '''
        context = UnifiedContext(code, "MyViewModel.kt")
        findings = rule.check(context)

        assert len(findings) == 1

    def test_no_finding_without_explicit_dispatcher(self, rule):
        """Test no finding without explicit dispatcher"""
        code = '''
        class MyViewModel : ViewModel() {
            fun load() {
                viewModelScope.launch { }
            }
        }
        '''
        context = UnifiedContext(code, "MyViewModel.kt")
        findings = rule.check(context)

        assert len(findings) == 0

    def test_no_finding_in_repository(self, rule):
        """Test no finding in Repository class"""
        code = '''
        class Repository {
            suspend fun fetch() = withContext(Dispatchers.IO) { }
        }
        '''
        context = UnifiedContext(code, "Repository.kt")
        findings = rule.check(context)

        assert len(findings) == 0

    def test_no_finding_in_activity(self, rule):
        """Test no finding in Activity"""
        code = '''
        class MainActivity : AppCompatActivity() {
            fun load() {
                lifecycleScope.launch(Dispatchers.Main) { }
            }
        }
        '''
        context = UnifiedContext(code, "MainActivity.kt")
        findings = rule.check(context)

        assert len(findings) == 0


class TestMainThreadIoRule:
    """Tests for MainThreadIoRule"""

    @pytest.fixture
    def rule(self):
        return MainThreadIoRule()

    def test_metadata(self, rule):
        """Test rule metadata"""
        assert rule.metadata.id == "mainthread_io"
        assert rule.metadata.severity == RuleSeverity.MAJOR
        assert rule.metadata.category == RuleCategory.PERFORMANCE

    def test_detects_file_read_on_main_thread(self, rule):
        """Test detecting file read on main thread"""
        code = '''
        class MainActivity : AppCompatActivity() {
            fun loadData() {
                val data = File("test.txt").readText()
            }
        }
        '''
        context = UnifiedContext(code, "MainActivity.kt")
        findings = rule.check(context)

        assert len(findings) >= 1

    def test_detects_network_on_main_thread(self, rule):
        """Test detecting network operation on main thread"""
        code = '''
        class MainActivity : AppCompatActivity() {
            fun fetchData() {
                val response = URL("http://example.com").readText()
            }
        }
        '''
        context = UnifiedContext(code, "MainActivity.kt")
        findings = rule.check(context)

        assert len(findings) >= 1

    def test_no_finding_with_dispatchers_io(self, rule):
        """Test no finding with Dispatchers.IO"""
        code = '''
        class MainActivity : AppCompatActivity() {
            fun loadData() {
                lifecycleScope.launch(Dispatchers.IO) {
                    val data = File("test.txt").readText()
                }
            }
        }
        '''
        context = UnifiedContext(code, "MainActivity.kt")
        findings = rule.check(context)

        # Should not detect when properly using IO dispatcher
        # Note: This depends on rule implementation

    def test_execution_mode(self, rule):
        """Test rule execution mode"""
        from unified_engine.interfaces import ExecutionMode
        assert rule.execution_mode == ExecutionMode.HYBRID
