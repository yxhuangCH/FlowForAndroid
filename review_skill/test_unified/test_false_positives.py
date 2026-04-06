"""False positive tests - ensure rules don't report incorrect findings"""

import pytest
from unified_engine.context import UnifiedContext
from unified_engine.rules import get_all_rules


class TestFalsePositives:
    """False positive tests for all rules"""

    # Test cases: (code, rule_id, description)
    FALSE_POSITIVE_CASES = [
        # GlobalScope rule
        (
            '''
            // This is a comment mentioning GlobalScope.launch
            class Test {}
            ''',
            "no_globalscope",
            "GlobalScope in comment should not be detected"
        ),
        (
            '''
            class Test {
                val text = "GlobalScope.launch is bad"
            }
            ''',
            "no_globalscope",
            "GlobalScope in string should not be detected"
        ),
        (
            '''
            class Test {
                fun explain() {
                    println("Don't use GlobalScope")
                }
            }
            ''',
            "no_globalscope",
            "GlobalScope in println should not be detected"
        ),
        (
            '''
            /**
             * Uses GlobalScope.launch for background work
             * @deprecated Use lifecycleScope instead
             */
            class Test {}
            ''',
            "no_globalscope",
            "GlobalScope in KDoc should not be detected"
        ),

        # ViewModel Context rule
        (
            '''
            class Repository {
                suspend fun fetch() = withContext(Dispatchers.IO) { }
            }
            ''',
            "viewmodel_context",
            "Dispatchers.IO in Repository should be allowed"
        ),
        (
            '''
            class DataSource {
                fun load() {
                    CoroutineScope(Dispatchers.IO).launch { }
                }
            }
            ''',
            "viewmodel_context",
            "Dispatchers in non-ViewModel class should be allowed"
        ),
        (
            '''
            class MainActivity : AppCompatActivity() {
                fun load() {
                    lifecycleScope.launch(Dispatchers.Main) { }
                }
            }
            ''',
            "viewmodel_context",
            "Dispatchers.Main in Activity should be allowed"
        ),

        # Flow rules
        (
            '''
            class Test {
                fun numbers() = flowOf(1, 2, 3)
            }
            ''',
            "missing_flowon",
            "flowOf doesn't need flowOn"
        ),
        (
            '''
            class Test {
                fun numbers() = emptyFlow<Int>()
            }
            ''',
            "missing_flowon",
            "emptyFlow doesn't need flowOn"
        ),
        (
            '''
            class Test {
                fun interval() = tickerFlow(1000)
            }
            ''',
            "missing_flowon",
            "tickerFlow doesn't need flowOn"
        ),

        # Compose rules
        (
            '''
            @Composable
            fun StaticComponent() {
                Text("Hello")  // No state needed
            }
            ''',
            "compose_remember_state",
            "Stateless composable should not require remember"
        ),
        (
            '''
            @Composable
            fun ButtonWithCallback(onClick: () -> Unit) {
                Button(onClick = onClick) { }
            }
            ''',
            "compose_side_effect",
            "Callback parameter is not a side effect"
        ),
    ]

    @pytest.mark.parametrize("code,rule_id,description", FALSE_POSITIVE_CASES)
    def test_no_false_positives(self, code, rule_id, description):
        """Test that rules don't produce false positives"""
        context = UnifiedContext(code, "Test.kt")

        # Find the rule by ID
        rule = None
        for r in get_all_rules():
            if r.metadata.id == rule_id:
                rule = r
                break

        if rule is None:
            pytest.skip(f"Rule {rule_id} not found")

        findings = rule.check(context)

        assert len(findings) == 0, f"False positive: {description}\nFound {len(findings)} unexpected findings"


class TestEdgeCases:
    """Edge case tests"""

    def test_empty_file(self):
        """Test all rules handle empty files"""
        context = UnifiedContext("", "Test.kt")

        for rule in get_all_rules():
            try:
                findings = rule.check(context)
                assert isinstance(findings, list)
            except Exception as e:
                pytest.fail(f"Rule {rule.metadata.id} failed on empty file: {e}")

    def test_whitespace_only(self):
        """Test all rules handle whitespace-only files"""
        context = UnifiedContext("   \n\n   \t\n", "Test.kt")

        for rule in get_all_rules():
            try:
                findings = rule.check(context)
                assert isinstance(findings, list)
            except Exception as e:
                pytest.fail(f"Rule {rule.metadata.id} failed on whitespace file: {e}")

    def test_comment_only(self):
        """Test all rules handle comment-only files"""
        code = '''
        // Single line comment
        /* Multi-line
           comment */
        /**
         * KDoc comment
         */
        '''
        context = UnifiedContext(code, "Test.kt")

        for rule in get_all_rules():
            try:
                findings = rule.check(context)
                assert isinstance(findings, list)
            except Exception as e:
                pytest.fail(f"Rule {rule.metadata.id} failed on comment file: {e}")

    def test_minimal_class(self):
        """Test all rules handle minimal class"""
        code = "class A { }"
        context = UnifiedContext(code, "Test.kt")

        for rule in get_all_rules():
            try:
                findings = rule.check(context)
                assert isinstance(findings, list)
            except Exception as e:
                pytest.fail(f"Rule {rule.metadata.id} failed on minimal class: {e}")

    def test_minimal_function(self):
        """Test all rules handle minimal function"""
        code = "fun foo() { }"
        context = UnifiedContext(code, "Test.kt")

        for rule in get_all_rules():
            try:
                findings = rule.check(context)
                assert isinstance(findings, list)
            except Exception as e:
                pytest.fail(f"Rule {rule.metadata.id} failed on minimal function: {e}")

    def test_special_characters(self):
        """Test all rules handle special characters"""
        code = '''
        class Test {
            val unicode = "Hello 世界 🌍"
            val special = "\\n\\t\\r"
            val template = "Value: ${value}"
        }
        '''
        context = UnifiedContext(code, "Test.kt")

        for rule in get_all_rules():
            try:
                findings = rule.check(context)
                assert isinstance(findings, list)
            except Exception as e:
                pytest.fail(f"Rule {rule.metadata.id} failed on special chars: {e}")

    def test_very_long_line(self):
        """Test all rules handle very long lines"""
        code = "class Test { val x = \"" + "a" * 10000 + "\" }"
        context = UnifiedContext(code, "Test.kt")

        for rule in get_all_rules():
            try:
                findings = rule.check(context)
                assert isinstance(findings, list)
            except Exception as e:
                pytest.fail(f"Rule {rule.metadata.id} failed on long line: {e}")

    def test_deeply_nested(self):
        """Test all rules handle deeply nested code"""
        code = '''
        class A {
            class B {
                class C {
                    class D {
                        class E {
                            fun deeplyNested() {
                                if (true) {
                                    if (true) {
                                        if (true) {
                                            println("deep")
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        '''
        context = UnifiedContext(code, "Test.kt")

        for rule in get_all_rules():
            try:
                findings = rule.check(context)
                assert isinstance(findings, list)
            except Exception as e:
                pytest.fail(f"Rule {rule.metadata.id} failed on nested code: {e}")


class TestKnownFalsePositives:
    """Tests for previously reported false positives"""

    KNOWN_ISSUES = [
        {
            "id": "FP-001",
            "description": "GlobalScope in string template",
            "code": '''
                fun errorMessage() = "Don't use ${GlobalScope::class.simpleName}"
            ''',
            "rule": "no_globalscope",
            "expected": 0
        },
        {
            "id": "FP-002",
            "description": "Dispatchers in documentation",
            "code": '''
                /**
                 * Use Dispatchers.IO for IO operations
                 */
                class Repository { }
            ''',
            "rule": "viewmodel_context",
            "expected": 0
        },
    ]

    @pytest.mark.parametrize("issue", KNOWN_ISSUES)
    def test_known_false_positive_fixed(self, issue):
        """Test that known false positives are fixed"""
        context = UnifiedContext(issue["code"], "Test.kt")

        rule = None
        for r in get_all_rules():
            if r.metadata.id == issue["rule"]:
                rule = r
                break

        if rule is None:
            pytest.skip(f"Rule {issue['rule']} not found")

        findings = rule.check(context)

        assert len(findings) == issue["expected"], \
            f"Known false positive not fixed: {issue['id']} - {issue['description']}"
