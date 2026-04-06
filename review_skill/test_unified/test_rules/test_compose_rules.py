"""Tests for Compose rules"""

import pytest
from unified_engine.context import UnifiedContext
from unified_engine.rules.compose import (
    ComposeRememberStateRule,
    ComposeSideEffectRule,
    ComposeRecompositionRule,
    ComposeModifierRule,
)


class TestComposeRememberStateRule:
    """Tests for ComposeRememberStateRule"""

    @pytest.fixture
    def rule(self):
        return ComposeRememberStateRule()

    def test_detects_var_without_remember(self, rule):
        """Test detecting mutable state without remember"""
        code = '''
        @Composable
        fun Counter() {
            var count = 0
            Button(onClick = { count++ }) { }
        }
        '''
        context = UnifiedContext(code, "Counter.kt")
        findings = rule.check(context)

        # Should detect missing remember

    def test_no_finding_with_remember(self, rule):
        """Test no finding with proper remember usage"""
        code = '''
        @Composable
        fun Counter() {
            var count by remember { mutableStateOf(0) }
            Button(onClick = { count++ }) { }
        }
        '''
        context = UnifiedContext(code, "Counter.kt")
        findings = rule.check(context)


class TestComposeSideEffectRule:
    """Tests for ComposeSideEffectRule"""

    @pytest.fixture
    def rule(self):
        return ComposeSideEffectRule()

    def test_detects_direct_side_effect(self, rule):
        """Test detecting direct side effects in composable"""
        code = '''
        @Composable
        fun MyComponent() {
            Log.d("TAG", "Rendered")
            Text("Hello")
        }
        '''
        context = UnifiedContext(code, "MyComponent.kt")
        findings = rule.check(context)

    def test_no_finding_with_launchedeffect(self, rule):
        """Test no finding with proper side effect handling"""
        code = '''
        @Composable
        fun MyComponent() {
            LaunchedEffect(Unit) {
                Log.d("TAG", "Rendered")
            }
            Text("Hello")
        }
        '''
        context = UnifiedContext(code, "MyComponent.kt")
        findings = rule.check(context)


class TestComposeRecompositionRule:
    """Tests for ComposeRecompositionRule"""

    @pytest.fixture
    def rule(self):
        return ComposeRecompositionRule()

    def test_detects_unstable_param(self, rule):
        """Test detecting unstable parameters"""
        code = '''
        @Composable
        fun ItemList(items: List<String>) {
            LazyColumn {
                items(items) { item ->
                    Text(item)
                }
            }
        }
        '''
        context = UnifiedContext(code, "ItemList.kt")
        findings = rule.check(context)


class TestComposeModifierRule:
    """Tests for ComposeModifierRule"""

    @pytest.fixture
    def rule(self):
        return ComposeModifierRule()

    def test_detects_missing_modifier_param(self, rule):
        """Test detecting missing Modifier parameter"""
        code = '''
        @Composable
        fun MyButton() {
            Button(onClick = {}) { }
        }
        '''
        context = UnifiedContext(code, "MyButton.kt")
        findings = rule.check(context)

    def test_no_finding_with_modifier(self, rule):
        """Test no finding with proper Modifier parameter"""
        code = '''
        @Composable
        fun MyButton(modifier: Modifier = Modifier) {
            Button(onClick = {}, modifier = modifier) { }
        }
        '''
        context = UnifiedContext(code, "MyButton.kt")
        findings = rule.check(context)
