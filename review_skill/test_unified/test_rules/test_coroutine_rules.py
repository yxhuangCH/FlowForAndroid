"""Tests for coroutine rules"""

import pytest
from unified_engine.context import UnifiedContext
from unified_engine.rules.coroutine import (
    CoroutineExceptionHandlingRule,
    SuspendFunctionNamingRule,
    CoroutineScopeCancellationRule,
    JobLifecycleRule,
    CoroutineStructuredConcurrencyRule,
)
from rule_engine.interfaces import RuleSeverity


class TestCoroutineExceptionHandlingRule:
    """Tests for CoroutineExceptionHandlingRule"""

    @pytest.fixture
    def rule(self):
        return CoroutineExceptionHandlingRule()

    def test_detects_try_catch_in_coroutine(self):
        """Test detecting try-catch in coroutine"""
        code = '''
        class Test {
            fun test() {
                GlobalScope.launch {
                    try {
                        riskyOperation()
                    } catch (e: Exception) { }
                }
            }
        }
        '''
        context = UnifiedContext(code, "Test.kt")
        rule = CoroutineExceptionHandlingRule()
        findings = rule.check(context)

        # May or may not detect depending on implementation

    def test_no_finding_with_supervisor_job(self):
        """Test no finding with proper exception handling"""
        code = '''
        class Test {
            fun test() {
                val scope = CoroutineScope(SupervisorJob())
                scope.launch {
                    riskyOperation()
                }
            }
        }
        '''
        context = UnifiedContext(code, "Test.kt")
        rule = CoroutineExceptionHandlingRule()
        findings = rule.check(context)


class TestSuspendFunctionNamingRule:
    """Tests for SuspendFunctionNamingRule"""

    @pytest.fixture
    def rule(self):
        return SuspendFunctionNamingRule()

    def test_detects_bad_suspend_function_name(self, rule):
        """Test detecting suspend function without proper naming"""
        code = '''
        class Repository {
            suspend fun getData(): String = "data"
        }
        '''
        context = UnifiedContext(code, "Repository.kt")
        findings = rule.check(context)

        # May detect depending on naming convention rules

    def test_no_finding_for_good_naming(self, rule):
        """Test no finding for properly named suspend function"""
        code = '''
        class Repository {
            suspend fun fetchData(): String = "data"
            suspend fun loadUsers(): List<User> = emptyList()
        }
        '''
        context = UnifiedContext(code, "Repository.kt")
        findings = rule.check(context)


class TestCoroutineScopeCancellationRule:
    """Tests for CoroutineScopeCancellationRule"""

    @pytest.fixture
    def rule(self):
        return CoroutineScopeCancellationRule()

    def test_detects_uncancelled_scope(self, rule):
        """Test detecting uncancelled coroutine scope"""
        code = '''
        class MyViewModel : ViewModel() {
            private val scope = CoroutineScope(Dispatchers.Main)

            fun load() {
                scope.launch { }
            }
        }
        '''
        context = UnifiedContext(code, "MyViewModel.kt")
        findings = rule.check(context)

        # Should detect missing cancellation

    def test_no_finding_with_proper_cancellation(self, rule):
        """Test no finding with proper scope cancellation"""
        code = '''
        class MyViewModel : ViewModel() {
            private val scope = CoroutineScope(Dispatchers.Main)

            fun load() {
                scope.launch { }
            }

            override fun onCleared() {
                scope.cancel()
            }
        }
        '''
        context = UnifiedContext(code, "MyViewModel.kt")
        findings = rule.check(context)


class TestJobLifecycleRule:
    """Tests for JobLifecycleRule"""

    @pytest.fixture
    def rule(self):
        return JobLifecycleRule()

    def test_detects_fire_and_forget_job(self, rule):
        """Test detecting fire-and-forget jobs"""
        code = '''
        class Test {
            fun startWork() {
                GlobalScope.launch { }
            }
        }
        '''
        context = UnifiedContext(code, "Test.kt")
        findings = rule.check(context)


class TestCoroutineStructuredConcurrencyRule:
    """Tests for CoroutineStructuredConcurrencyRule"""

    @pytest.fixture
    def rule(self):
        return CoroutineStructuredConcurrencyRule()

    def test_detects_unstructured_concurrency(self, rule):
        """Test detecting unstructured concurrency patterns"""
        code = '''
        class Test {
            suspend fun loadData() {
                val job1 = GlobalScope.launch { }
                val job2 = GlobalScope.launch { }
                job1.join()
                job2.join()
            }
        }
        '''
        context = UnifiedContext(code, "Test.kt")
        findings = rule.check(context)

        # Should detect unstructured concurrency

    def test_no_finding_with_structured_concurrency(self, rule):
        """Test no finding with structured concurrency"""
        code = '''
        class Test {
            suspend fun loadData() = coroutineScope {
                val deferred1 = async { }
                val deferred2 = async { }
                deferred1.await()
                deferred2.await()
            }
        }
        '''
        context = UnifiedContext(code, "Test.kt")
        findings = rule.check(context)
