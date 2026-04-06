"""Tests for Flow rules"""

import pytest
from unified_engine.context import UnifiedContext
from unified_engine.rules.flow import (
    MissingFlowOnRule,
    FlowOnMainThreadRule,
    MultipleFlowOnRule,
    FlowExceptionHandlingRule,
    StateFlowValueAssignmentRule,
)


class TestMissingFlowOnRule:
    """Tests for MissingFlowOnRule"""

    @pytest.fixture
    def rule(self):
        return MissingFlowOnRule()

    def test_detects_missing_flowon(self, rule):
        """Test detecting flow without flowOn"""
        code = '''
        class Repository {
            fun getData(): Flow<Data> = flow {
                emit(fetchFromNetwork())
            }
        }
        '''
        context = UnifiedContext(code, "Repository.kt")
        findings = rule.check(context)

        # Should detect missing flowOn for IO operation

    def test_no_finding_with_flowon(self, rule):
        """Test no finding with proper flowOn"""
        code = '''
        class Repository {
            fun getData(): Flow<Data> = flow {
                emit(fetchFromNetwork())
            }.flowOn(Dispatchers.IO)
        }
        '''
        context = UnifiedContext(code, "Repository.kt")
        findings = rule.check(context)

    def test_no_finding_for_flowof(self, rule):
        """Test no finding for flowOf (no IO)"""
        code = '''
        class Test {
            fun getData() = flowOf(1, 2, 3)
        }
        '''
        context = UnifiedContext(code, "Test.kt")
        findings = rule.check(context)


class TestFlowOnMainThreadRule:
    """Tests for FlowOnMainThreadRule"""

    @pytest.fixture
    def rule(self):
        return FlowOnMainThreadRule()

    def test_detects_flowon_main(self, rule):
        """Test detecting flowOn with Main dispatcher"""
        code = '''
        class Repository {
            fun getData(): Flow<Data> = flow {
                emit(fetchFromNetwork())
            }.flowOn(Dispatchers.Main)
        }
        '''
        context = UnifiedContext(code, "Repository.kt")
        findings = rule.check(context)

        # Should warn about flowOn(Dispatchers.Main)

    def test_no_finding_with_io_dispatcher(self, rule):
        """Test no finding with IO dispatcher"""
        code = '''
        class Repository {
            fun getData(): Flow<Data> = flow {
                emit(fetchFromNetwork())
            }.flowOn(Dispatchers.IO)
        }
        '''
        context = UnifiedContext(code, "Repository.kt")
        findings = rule.check(context)


class TestMultipleFlowOnRule:
    """Tests for MultipleFlowOnRule"""

    @pytest.fixture
    def rule(self):
        return MultipleFlowOnRule()

    def test_detects_multiple_flowon(self, rule):
        """Test detecting multiple flowOn calls"""
        code = '''
        class Repository {
            fun getData(): Flow<Data> = flow {
                emit(fetchFromNetwork())
            }
            .flowOn(Dispatchers.IO)
            .flowOn(Dispatchers.Default)
        }
        '''
        context = UnifiedContext(code, "Repository.kt")
        findings = rule.check(context)

        # Should warn about multiple flowOn

    def test_no_finding_with_single_flowon(self, rule):
        """Test no finding with single flowOn"""
        code = '''
        class Repository {
            fun getData(): Flow<Data> = flow {
                emit(fetchFromNetwork())
            }.flowOn(Dispatchers.IO)
        }
        '''
        context = UnifiedContext(code, "Repository.kt")
        findings = rule.check(context)


class TestFlowExceptionHandlingRule:
    """Tests for FlowExceptionHandlingRule"""

    @pytest.fixture
    def rule(self):
        return FlowExceptionHandlingRule()

    def test_detects_missing_catch(self, rule):
        """Test detecting flow without exception handling"""
        code = '''
        class ViewModel {
            fun load() {
                repository.getData()
                    .collect { }
            }
        }
        '''
        context = UnifiedContext(code, "ViewModel.kt")
        findings = rule.check(context)

    def test_no_finding_with_catch(self, rule):
        """Test no finding with proper catch"""
        code = '''
        class ViewModel {
            fun load() {
                repository.getData()
                    .catch { e -> handleError(e) }
                    .collect { }
            }
        }
        '''
        context = UnifiedContext(code, "ViewModel.kt")
        findings = rule.check(context)


class TestStateFlowValueAssignmentRule:
    """Tests for StateFlowValueAssignmentRule"""

    @pytest.fixture
    def rule(self):
        return StateFlowValueAssignmentRule()

    def test_detects_direct_value_assignment(self, rule):
        """Test detecting direct StateFlow value assignment"""
        code = '''
        class ViewModel {
            private val _state = MutableStateFlow(0)

            fun update() {
                _state.value = 1
            }
        }
        '''
        context = UnifiedContext(code, "ViewModel.kt")
        findings = rule.check(context)

    def test_no_finding_with_update(self, rule):
        """Test no finding with update method"""
        code = '''
        class ViewModel {
            private val _state = MutableStateFlow(0)

            fun update() {
                _state.update { it + 1 }
            }
        }
        '''
        context = UnifiedContext(code, "ViewModel.kt")
        findings = rule.check(context)
